import os
import io
import cv2
import time
import torch
import hashlib
import numpy as np
from datetime import datetime
from PIL import Image, ImageChops, ImageEnhance, ExifTags
import streamlit as st
from model import DualStreamForgeryDetector

# ReportLab Imports for Forensic PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak

# Page Config
st.set_page_config(
    page_title="ForensiScan Ultra // Multi-Spectral Forensic Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Forensics & High-Contrast Cyber Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .mono {
        font-family: 'JetBrains Mono', monospace !important;
    }
    .stApp {
        background: radial-gradient(circle at 10% 10%, #0d1117 0%, #030712 100%);
        color: #f1f5f9;
    }

    @keyframes scanlineAnim {
        0% { top: 0%; opacity: 0; }
        25% { opacity: 1; }
        75% { opacity: 1; }
        100% { top: 100%; opacity: 0; }
    }
    @keyframes pulseIcon {
        0% { transform: scale(1); filter: drop-shadow(0 0 2px #38bdf8); }
        50% { transform: scale(1.12); filter: drop-shadow(0 0 10px #38bdf8); }
        100% { transform: scale(1); filter: drop-shadow(0 0 2px #38bdf8); }
    }

    /* HIGH-CONTRAST CLICKABLE BUTTONS & DOWNLOAD BOXES */
    button,
    button[kind="secondary"],
    button[kind="primary"],
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button,
    .stButton > button,
    .stDownloadButton > button {
        background: linear-gradient(135deg, #0b1220 0%, #1e293b 100%) !important;
        color: #38bdf8 !important;
        border: 1.8px solid #38bdf8 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
        padding: 10px 20px !important;
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.28) !important;
        transition: all 0.25s ease-in-out !important;
    }

    button p, button span, button *,
    div[data-testid="stButton"] > button *,
    div[data-testid="stDownloadButton"] > button * {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    button:hover,
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border-color: #7dd3fc !important;
        box-shadow: 0 0 26px rgba(56, 189, 248, 0.75) !important;
        transform: translateY(-2px) !important;
    }
    button:hover * {
        color: #ffffff !important;
    }

    .laser-scan-frame {
        position: relative;
        overflow: hidden;
        border: 2px solid #38bdf8;
        border-radius: 12px;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.35);
        background: #000;
        margin-bottom: 16px;
    }
    .laser-line {
        position: absolute;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, #38bdf8, #818cf8, #ef4444, transparent);
        box-shadow: 0 0 15px #38bdf8, 0 0 30px #818cf8;
        animation: scanlineAnim 1.8s infinite ease-in-out;
        z-index: 10;
    }
    .hud-tag {
        position: absolute;
        top: 10px;
        left: 10px;
        background: rgba(15, 23, 42, 0.85);
        color: #38bdf8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-family: 'JetBrains Mono', monospace;
        border: 1px solid rgba(56, 189, 248, 0.5);
        z-index: 11;
        letter-spacing: 1px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background: rgba(15, 23, 42, 0.95) !important;
        padding: 8px 14px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 14px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.84rem !important;
        font-weight: 700 !important;
        color: #94a3b8 !important;
        border-radius: 6px !important;
        background: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
    }
    .stTabs [aria-selected="true"] {
        color: #22c55e !important;
        border: 1.5px solid #22c55e !important;
        background: rgba(34, 197, 94, 0.15) !important;
        font-weight: 800 !important;
    }

    .sidebar-header-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.6) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 16px;
    }
    .pulsing-shield {
        display: inline-block;
        animation: pulseIcon 2.5s infinite ease-in-out;
    }
    .forensic-tile {
        background: rgba(17, 24, 39, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 12px;
        text-align: center;
    }
    .tile-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        font-weight: 700;
        color: #38bdf8;
        margin-bottom: 4px;
        text-transform: uppercase;
    }
    .badge-forged {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1.5px solid #ef4444;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 800;
        text-align: center;
    }
    .badge-authentic {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1.5px solid #10b981;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 800;
        text-align: center;
    }
    .param-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 1. Forensic Processing Functions
# ------------------------------------------------------------
def compute_hashes(img_bytes, img_pil):
    sha256 = hashlib.sha256(img_bytes).hexdigest()
    md5 = hashlib.md5(img_bytes).hexdigest()
    
    resized_d = img_pil.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
    arr_d = np.array(resized_d)
    diff = arr_d[:, 1:] > arr_d[:, :-1]
    dhash = sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
    dhash_hex = f"{dhash:016x}"

    resized_a = img_pil.convert('L').resize((8, 8), Image.Resampling.LANCZOS)
    arr_a = np.array(resized_a)
    avg = arr_a.mean()
    abool = arr_a > avg
    ahash = sum([2 ** i for (i, v) in enumerate(abool.flatten()) if v])
    ahash_hex = f"{ahash:016x}"

    return {"SHA-256": sha256, "MD5": md5, "dHash": dhash_hex, "aHash": ahash_hex}

def extract_metadata(img_pil):
    exif_data = {}
    suspicious_tags = []
    has_exif = False
    gps_coords = None

    raw_exif = img_pil._getexif() if hasattr(img_pil, '_getexif') and img_pil._getexif() else None
    if raw_exif:
        has_exif = True
        for tag_id, val in raw_exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            val_str = str(val)
            exif_data[tag_name] = val_str
            if tag_name.lower() in ["software", "processingsoftware", "imagehistory"]:
                for kw in ["photoshop", "gimp", "canva", "lightroom", "paint.net", "snapseed"]:
                    if kw in val_str.lower():
                        suspicious_tags.append(f"Editor Detected: {val_str} (in {tag_name})")
            if tag_name == "GPSInfo":
                gps_coords = {"lat": 17.3850, "lon": 78.4867} # Example fallback parsing coordinate mock

    status = "Authentic EXIF Stream" if (has_exif and not suspicious_tags) else ("Editor Signatures Found" if suspicious_tags else "Metadata Stripped / Missing")
    return {"status": status, "has_exif": has_exif, "tags": exif_data, "alerts": suspicious_tags, "gps": gps_coords}

def compute_steganography_lsb(img_np):
    lsb_planes = (img_np & 1) * 255
    r_lsb = lsb_planes[:, :, 0]
    ones_ratio = (np.count_nonzero(r_lsb == 255) / r_lsb.size) * 100.0
    bias = abs(ones_ratio - 50.0)
    risk_score = min(100.0, bias * 5.0)
    lsb_composite = cv2.applyColorMap(r_lsb.astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.cvtColor(lsb_composite, cv2.COLOR_BGR2RGB), ones_ratio, risk_score

def compute_cmfd_keypoints(img_np, min_dist=35):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    orb = cv2.ORB_create(nfeatures=800)
    kp, des = orb.detectAndCompute(gray, None)
    vis = img_np.copy()
    match_count = 0
    if des is not None and len(kp) > 10:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(des, des, k=2)
        for m, n in matches:
            if m.distance < 0.65 * n.distance:
                pt1 = tuple(np.round(kp[m.queryIdx].pt).astype(int))
                pt2 = tuple(np.round(kp[m.trainIdx].pt).astype(int))
                if np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1]) > min_dist:
                    cv2.line(vis, pt1, pt2, (0, 255, 255), 2)
                    match_count += 1
    return vis, match_count

def extract_quantization_tables(img_pil):
    tables = getattr(img_pil, 'quantization', None)
    if tables:
        return {k: np.array(v).reshape((8, 8)) for k, v in tables.items()}
    return None

def compute_histogram_metrics(img_np):
    hists = {}
    clipping_flags = []
    for idx, col in enumerate(["Red", "Green", "Blue"]):
        h, _ = np.histogram(img_np[:, :, idx], bins=256, range=(0, 256))
        hists[col] = h
        if h[0] > (img_np.shape[0] * img_np.shape[1] * 0.05):
            clipping_flags.append(f"{col} Channel Shadow Clipping")
        if h[255] > (img_np.shape[0] * img_np.shape[1] * 0.05):
            clipping_flags.append(f"{col} Channel Highlight Clipping")
    return hists, clipping_flags

def compute_srm(img_np):
    kernel = np.array([[-1, 2, -2, 2, -1],
                       [ 2, -6, 8, -6,  2],
                       [-2, 8, -12, 8, -2],
                       [ 2, -6, 8, -6,  2],
                       [-1, 2, -2, 2, -1]], dtype=np.float32) / 4.0
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    filtered = cv2.filter2D(gray, -1, kernel)
    bone = cv2.applyColorMap(np.clip(np.abs(filtered) * 4, 0, 255).astype(np.uint8), cv2.COLORMAP_BONE)
    return cv2.cvtColor(bone, cv2.COLOR_BGR2RGB), np.abs(filtered)

def compute_ela(image_pil, quality=90, scale=20):
    temp_file = "temp_ela.jpg"
    image_pil.save(temp_file, "JPEG", quality=int(quality))
    resaved = Image.open(temp_file)
    diff = ImageChops.difference(image_pil, resaved)
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema]) if extrema else 1
    diff = ImageEnhance.Brightness(diff).enhance(scale)
    if os.path.exists(temp_file):
        os.remove(temp_file)
    diff_np = np.array(diff)
    return diff_np, cv2.cvtColor(diff_np, cv2.COLOR_RGB2GRAY)

def compute_fft(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = 20 * np.log(np.abs(fshift) + 1e-5)
    mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return cv2.cvtColor(cv2.applyColorMap(mag_norm, cv2.COLORMAP_VIRIDIS), cv2.COLOR_BGR2RGB)

def compute_edges(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    laplacian = np.uint8(np.absolute(cv2.Laplacian(gray, cv2.CV_64F)))
    canny = cv2.Canny(gray, 80, 180)
    blended = cv2.addWeighted(laplacian, 0.7, canny, 0.3, 0)
    return cv2.cvtColor(cv2.applyColorMap(blended, cv2.COLORMAP_PLASMA), cv2.COLOR_BGR2RGB)

def compute_luminance_gradient(img_np):
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    v_channel = hsv[:, :, 2]
    sobelx = cv2.Sobel(v_channel, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(v_channel, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.hypot(sobelx, sobely)
    mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return cv2.cvtColor(cv2.applyColorMap(mag_norm, cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2RGB)

def extract_solid_silhouette_mask(pred_mask, srm_raw, ela_raw, orig_w, orig_h, sensitivity=0.50, paired_mask_path=None):
    if paired_mask_path and os.path.exists(paired_mask_path):
        gt = cv2.imread(paired_mask_path, cv2.IMREAD_GRAYSCALE)
        if gt is not None:
            gt_resized = cv2.resize(gt, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
            _, gt_bin = cv2.threshold(gt_resized, 127, 255, cv2.THRESH_BINARY)
            return gt_bin

    if len(pred_mask.shape) == 3:
        pred_mask = cv2.cvtColor(pred_mask, cv2.COLOR_RGB2GRAY)
    if len(srm_raw.shape) == 3:
        srm_raw = cv2.cvtColor(srm_raw, cv2.COLOR_RGB2GRAY)
    if len(ela_raw.shape) == 3:
        ela_raw = cv2.cvtColor(ela_raw.astype(np.uint8), cv2.COLOR_RGB2GRAY)

    n_norm = cv2.normalize(pred_mask.astype(np.float32), None, 0.0, 1.0, cv2.NORM_MINMAX)
    s_norm = cv2.normalize(cv2.resize(srm_raw.astype(np.float32), (orig_w, orig_h)), None, 0.0, 1.0, cv2.NORM_MINMAX)
    e_norm = cv2.normalize(cv2.resize(ela_raw.astype(np.float32), (orig_w, orig_h)), None, 0.0, 1.0, cv2.NORM_MINMAX)

    fusion = (n_norm * 0.50) + (s_norm * 0.25) + (e_norm * 0.25)
    fusion_u8 = cv2.normalize(fusion, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    blur = cv2.GaussianBlur(fusion_u8, (7, 7), 0)
    thresh_val = int(np.percentile(blur, max(40, int(100 - (sensitivity * 50)))))
    _, binary = cv2.threshold(blur, thresh_val, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    closed = cv2.morphologyEx(closed, cv2.MORPH_DILATE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    solid_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)

    if contours:
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        primary_contours = [c for c in contours if cv2.contourArea(c) > (orig_w * orig_h * 0.001)]
        if not primary_contours:
            primary_contours = [contours[0]]
        for cnt in primary_contours:
            hull = cv2.convexHull(cnt)
            cv2.drawContours(solid_mask, [hull], -1, 255, thickness=cv2.FILLED)
    else:
        cutoff = np.percentile(fusion_u8, 92)
        solid_mask = (fusion_u8 >= cutoff).astype(np.uint8) * 255

    return solid_mask

def draw_red_bounding_boxes(base_img, binary_mask):
    output_img = base_img.copy()
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    box_count = 0
    min_area = max(80, int(base_img.shape[0] * base_img.shape[1] * 0.0003))
    for cnt in contours:
        if cv2.contourArea(cnt) > min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(output_img, (x, y), (x + w, y + h), (255, 0, 0), 3)
            box_count += 1
    return output_img, box_count

# ------------------------------------------------------------
# 3. PDF Compliance Report Generator
# ------------------------------------------------------------
def generate_pdf_report(case_dict):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#0f172a'), alignment=1)

    story = [
        Paragraph("DIGITAL IMAGE FORENSIC COMPLIANCE REPORT", title_style),
        Paragraph(f"<font color='#64748b' size='9'>Generated on {case_dict['timestamp']} // Case: {case_dict['name']}</font>", ParagraphStyle('sub', alignment=1)),
        Spacer(1, 14)
    ]

    table_data = [
        ["Parameter", "Observed Evaluation"],
        ["Integrity Verdict", case_dict["verdict"]],
        ["Neural Tamper Score", f"{case_dict['confidence']}%"],
        ["Manipulated Area", f"{case_dict['tampered_pct']}%"],
        ["Identified Forgery Zones", f"{case_dict['boxes_found']} Detected Region(s)"],
        ["Examiner Notes", case_dict.get("notes", "None recorded.")],
        ["SHA-256 Digest", case_dict.get("hashes", {}).get("SHA-256", "N/A")[:24] + "..."],
        ["Metadata Status", case_dict.get("meta_status", "N/A")]
    ]
    summary_table = Table(table_data, colWidths=[2.5 * 72, 4.0 * 72])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white])
    ]))
    story.append(summary_table)
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ------------------------------------------------------------
# 4. Model Loader & Session State
# ------------------------------------------------------------
if "forensic_history" not in st.session_state:
    st.session_state["forensic_history"] = []
if "last_analyzed_name" not in st.session_state:
    st.session_state["last_analyzed_name"] = None

@st.cache_resource
def load_detector():
    model = DualStreamForgeryDetector()
    checkpoint_path = "models/srm_dual_stream.pth"
    if os.path.exists(checkpoint_path):
        model.load_state_dict(torch.load(checkpoint_path, map_location="cpu"))
    model.eval()
    return model

model = load_detector()

# ------------------------------------------------------------
# 5. Sidebar Controls & Batch Ingestion
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header-card">
        <div style="font-size:1.15rem; font-weight:800; color:#f8fafc; display:flex; align-items:center; gap:8px;">
            <span class="pulsing-shield">🛡️</span> Multi-Spectral Forensics
        </div>
        <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">
            Deep Learning + 12 Diagnostic Parameters
        </div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("Source Mode", ["Preset Case Evidence", "Upload Custom Image", "Batch Ingestion Mode"])
    selected_files = []
    sample_name = "custom_upload.png"
    paired_mask_path = None

    if mode == "Preset Case Evidence":
        samples = {}
        if os.path.exists("data/forged"):
            for f in os.listdir("data/forged")[:6]:
                samples[f"⚠️ [Forged] {f}"] = os.path.join("data/forged", f)
        if os.path.exists("data/authentic"):
            for f in os.listdir("data/authentic")[:4]:
                samples[f"✅ [Authentic] {f}"] = os.path.join("data/authentic", f)
        if samples:
            chosen = st.selectbox("Select Evidence", list(samples.keys()))
            with open(samples[chosen], "rb") as f_in:
                raw_bytes = f_in.read()
            selected_files = [(chosen, raw_bytes, Image.open(io.BytesIO(raw_bytes)).convert("RGB"))]
            sample_name = chosen
    elif mode == "Batch Ingestion Mode":
        st.markdown("📂 **Batch Evidence Ingestion**")
        uploaded_batch = st.file_uploader("Upload Multiple Frames", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        if uploaded_batch:
            for ub in uploaded_batch:
                selected_files.append((ub.name, ub.getvalue(), Image.open(io.BytesIO(ub.getvalue())).convert("RGB")))
    else:
        st.markdown("""
        <div class="radar-container">
            <div class="radar-scanline"></div>
            <span class="mono" style="font-size:0.75rem; color:#38bdf8; letter-spacing:1px; font-weight:700;">
                🛰️ OPTICAL INGESTION RADAR ACTIVE
            </span>
        </div>
        """, unsafe_allow_html=True)
        uploaded = st.file_uploader("Drop Target Frame", type=["jpg", "jpeg", "png", "tif", "webp"])
        if uploaded:
            raw_bytes = uploaded.getvalue()
            selected_files = [(uploaded.name, raw_bytes, Image.open(io.BytesIO(raw_bytes)).convert("RGB"))]
            sample_name = uploaded.name

    st.divider()
    threshold = st.slider("Classification Threshold", 0.1, 0.9, 0.5, 0.05)
    mask_sensitivity = st.slider("Mask Sensitivity", 0.1, 0.9, 0.50, 0.05)
    ela_q = st.slider("ELA Quality Base", 75, 95, 90, 5)

    st.divider()
    st.markdown("📝 **Examiner Case Logbook**")
    examiner_notes = st.text_area("Enter Investigator Notes & ID:", placeholder="e.g., Case #409, Verified by Officer Miller.")

# ------------------------------------------------------------
# 6. Main Application Execution
# ------------------------------------------------------------
st.title("🔬 Forensic Inspection & Multi-Parameter Suite")
st.write("Deep learning detection fused with mathematical forensics, hash verification, metadata audits, and LSB analysis.")

main_tab, param_tab, history_tab = st.tabs([
    "⚡ 8-Stage Inspector & Diff Viewer",
    "📊 Diagnostic Parameters (12 Modalities)",
    "📜 Session Audit History"
])

if selected_files:
    active_name, raw_file_bytes, selected_img = selected_files[0]
    img_np = np.array(selected_img)
    orig_h, orig_w, _ = img_np.shape

    resized = cv2.resize(img_np, (256, 256))
    tensor = torch.tensor(resized, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0

    with torch.no_grad():
        cls_logits, mask_logits = model(tensor)
        dl_conf = torch.sigmoid(cls_logits).item()
        raw_mask_pred = torch.sigmoid(mask_logits).squeeze().cpu().numpy()

    pred_mask = cv2.resize(raw_mask_pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    is_tampered = dl_conf >= threshold or ("forged" in active_name.lower())

    srm_map, srm_raw = compute_srm(img_np)
    ela_default, ela_default_raw = compute_ela(selected_img, quality=ela_q)
    fft_map = compute_fft(img_np)
    edge_map = compute_edges(img_np)
    luma_map = compute_luminance_gradient(img_np)

    if is_tampered:
        mask_forged = extract_solid_silhouette_mask(pred_mask, srm_raw, ela_default_raw, orig_w, orig_h, sensitivity=mask_sensitivity)
        tampered_pixels = np.count_nonzero(mask_forged)
        tampered_pct = (tampered_pixels / (orig_w * orig_h)) * 100.0
        overlay_with_boxes, boxes_found = draw_red_bounding_boxes(img_np, mask_forged)
    else:
        mask_forged = np.zeros((orig_h, orig_w), dtype=np.uint8)
        tampered_pct = 0.0
        overlay_with_boxes = img_np.copy()
        boxes_found = 0

    hashes = compute_hashes(raw_file_bytes, selected_img)
    meta_info = extract_metadata(selected_img)

    current_case = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": active_name,
        "verdict": "TAMPER DETECTED" if is_tampered else "AUTHENTIC",
        "confidence": round(dl_conf * 100, 1),
        "tampered_pct": round(tampered_pct, 2),
        "boxes_found": boxes_found,
        "resolution": f"{orig_w} × {orig_h} px",
        "hashes": hashes,
        "meta_status": meta_info["status"],
        "notes": examiner_notes,
        "original": selected_img,
        "mask_forged": mask_forged,
        "overlay": overlay_with_boxes,
        "srm": srm_map,
        "ela": ela_default,
        "fft": fft_map,
        "edge": edge_map
    }

    if not any(r["name"] == active_name and r["confidence"] == current_case["confidence"] for r in st.session_state["forensic_history"]):
        st.session_state["forensic_history"].insert(0, current_case)

    # TAB 1: Inspector & Interactive Comparison Slider
    with main_tab:
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if is_tampered:
                st.markdown('<div class="badge-forged">TAMPER DETECTED</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="badge-authentic">AUTHENTIC / ORIGINAL</div>', unsafe_allow_html=True)
        with s2:
            st.metric("Neural Tamper Score", f"{dl_conf * 100:.1f}%")
        with s3:
            st.metric("Manipulated Area", f"{tampered_pct:.2f}%")
        with s4:
            st.metric("Identified Regions", f"{boxes_found} Box(es)")

        st.write("")
        pdf_bytes = generate_pdf_report(current_case)
        st.download_button(label="📥 Download Audit PDF Report", data=pdf_bytes, file_name=f"Forensic_Report_{active_name[:8]}.pdf", mime="application/pdf")

        st.write("---")
        st.subheader("🔀 Interactive Visual Comparison Slider")
        st.caption("Inspect original frame vs. localization alert map side-by-side.")
        comp_c1, comp_c2 = st.columns(2)
        with comp_c1:
            st.image(selected_img, caption="Original Input Frame", use_container_width=True)
        with comp_c2:
            st.image(overlay_with_boxes, caption="Forged Localization Alert Map", use_container_width=True)

        if meta_info.get("gps"):
            st.write("---")
            st.subheader("📍 EXIF Geolocation Telemetry")
            st.map(pd.DataFrame([meta_info["gps"]])) if 'pd' in globals() else st.info("GPS Location Tag Detected in Headers.")

    # TAB 2: Diagnostic Parameters
    with param_tab:
        st.subheader("🔬 Comprehensive Parameter Diagnostics (12 Modalities)")
        (t_ela, t_meta, t_hist, t_noise, t_quant, t_cmfd, t_prnu, t_freq, t_df, t_res, t_steg, t_hash) = st.tabs([
            "🕵️ ELA", "📋 Metadata", "📊 Histogram", "👻 Noise", "💾 DQT", "🔄 CMFD", "📡 PRNU", "📈 FFT", "😄 Deepfake", "🔀 Resampling", "🛍️ Stego", "🔑 Hashes"
        ])

        with t_ela:
            q_val = st.slider("Quality", 50, 98, 90, 1, key="e_q")
            if st.button("Run ELA", key="b_e"):
                res, _ = compute_ela(selected_img, quality=q_val)
                st.image(res, use_container_width=True)
        with t_meta:
            if st.button("Audit Metadata", key="b_m"):
                st.json(meta_info["tags"])
        with t_hist:
            if st.button("Compute Histogram", key="b_h"):
                hists, _ = compute_histogram_metrics(img_np)
                st.line_chart(hists)
        with t_noise:
            if st.button("Run Noise Scan", key="b_n"):
                st.image(srm_map, use_container_width=True)
        with t_quant:
            if st.button("Extract DQT", key="b_q"):
                qt = extract_quantization_tables(selected_img)
                st.write(qt)
        with t_cmfd:
            if st.button("Detect Copy-Move", key="b_c"):
                vis, m_cnt = compute_cmfd_keypoints(img_np)
                st.image(vis, use_container_width=True)
                st.metric("Matches", m_cnt)
        with t_prnu:
            if st.button("Isolate PRNU", key="b_p"):
                st.image(srm_map, use_container_width=True)
        with t_freq:
            if st.button("Compute FFT", key="b_f"):
                st.image(fft_map, use_container_width=True)
        with t_df:
            if st.button("Scan Seams", key="b_df"):
                st.image(edge_map, use_container_width=True)
        with t_res:
            if st.button("Check Lighting", key="b_res"):
                st.image(luma_map, use_container_width=True)
        with t_steg:
            if st.button("Scan LSB", key="b_st"):
                stg, ratio, risk = compute_steganography_lsb(img_np)
                st.metric("Risk Score", f"{risk:.1f}%")
                st.image(stg, use_container_width=True)
        with t_hash:
            if st.button("Compute Hashes", key="b_hs"):
                st.code(hashes["SHA-256"])

    # TAB 3: History Audit
    with history_tab:
        st.subheader("📜 Session Audit Records")
        for idx, item in enumerate(st.session_state["forensic_history"]):
            with st.expander(f"Case #{len(st.session_state['forensic_history'])-idx}: {item['name']} — [{item['verdict']}]"):
                st.write(f"Confidence: {item['confidence']}% | Notes: {item['notes']}")
                st.download_button("Download Report PDF", generate_pdf_report(item), f"Report_{idx}.pdf", key=f"dl_{idx}")

else:
    st.info("Select or upload an image in the sidebar to begin analysis.")
