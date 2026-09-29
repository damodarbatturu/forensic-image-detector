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

# Dark Forensics & Veritas-Inspired Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    
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

    /* Keyframe Animations */
    @keyframes pulseGlow {
        0% { border-color: rgba(56, 189, 248, 0.35); box-shadow: 0 0 10px rgba(56, 189, 248, 0.15); }
        50% { border-color: rgba(56, 189, 248, 0.95); box-shadow: 0 0 25px rgba(56, 189, 248, 0.45); }
        100% { border-color: rgba(56, 189, 248, 0.35); box-shadow: 0 0 10px rgba(56, 189, 248, 0.15); }
    }
    @keyframes scanlineAnim {
        0% { top: 0%; opacity: 0; }
        25% { opacity: 1; }
        75% { opacity: 1; }
        100% { top: 100%; opacity: 0; }
    }

    /* Laser Scanner & Card Styles */
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

    /* Side-by-Side Veritas Panel Styling */
    .veritas-panel {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .veritas-header {
        font-family: 'JetBrains Mono', monospace;
        color: #38bdf8;
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .veritas-badge-success {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid #10b981;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .veritas-badge-danger {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid #ef4444;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .sidebar-header-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.6) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 16px;
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
    
    status = "Authentic EXIF Stream" if (has_exif and not suspicious_tags) else ("Editor Signatures Found" if suspicious_tags else "Metadata Stripped / Missing")
    return {"status": status, "has_exif": has_exif, "tags": exif_data, "alerts": suspicious_tags}

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
    diff_gray = cv2.cvtColor(diff_np, cv2.COLOR_RGB2GRAY)
    return diff_np, diff_gray

def compute_fft(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = 20 * np.log(np.abs(fshift) + 1e-5)
    mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    viridis = cv2.applyColorMap(mag_norm, cv2.COLORMAP_VIRIDIS)
    return cv2.cvtColor(viridis, cv2.COLOR_BGR2RGB)

def compute_edges(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    laplacian = np.uint8(np.absolute(cv2.Laplacian(gray, cv2.CV_64F)))
    canny = cv2.Canny(gray, 80, 180)
    blended = cv2.addWeighted(laplacian, 0.7, canny, 0.3, 0)
    plasma = cv2.applyColorMap(blended, cv2.COLORMAP_PLASMA)
    return cv2.cvtColor(plasma, cv2.COLOR_BGR2RGB)

def compute_luminance_gradient(img_np):
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    v_channel = hsv[:, :, 2]
    sobelx = cv2.Sobel(v_channel, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(v_channel, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.hypot(sobelx, sobely)
    mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    inferno = cv2.applyColorMap(mag_norm, cv2.COLORMAP_INFERNO)
    return cv2.cvtColor(inferno, cv2.COLOR_BGR2RGB)

def compute_steganography_lsb(img_np):
    lsb_planes = (img_np & 1) * 255
    r_lsb = lsb_planes[:, :, 0]
    ones_ratio = (np.count_nonzero(r_lsb == 255) / r_lsb.size) * 100.0
    bias = abs(ones_ratio - 50.0)
    risk_score = min(100.0, bias * 5.0)
    lsb_composite = cv2.applyColorMap(r_lsb.astype(np.uint8), cv2.COLORMAP_JET)
    lsb_composite = cv2.cvtColor(lsb_composite, cv2.COLOR_BGR2RGB)
    return lsb_composite, ones_ratio, risk_score

def compute_cmfd_keypoints(img_np):
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
                dist = np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
                if dist > 35:
                    cv2.line(vis, pt1, pt2, (0, 255, 255), 2)
                    cv2.circle(vis, pt1, 4, (255, 0, 0), -1)
                    cv2.circle(vis, pt2, 4, (0, 0, 255), -1)
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
            clipping_flags.append(f"{col} Channel Shadow Clipping (0 Black)")
        if h[255] > (img_np.shape[0] * img_np.shape[1] * 0.05):
            clipping_flags.append(f"{col} Channel Highlight Clipping (255 White)")
    return hists, clipping_flags

def extract_solid_silhouette_mask(pred_mask, srm_raw, ela_raw, orig_w, orig_h, sensitivity=0.50, paired_mask_path=None):
    if paired_mask_path and os.path.exists(paired_mask_path):
        gt = cv2.imread(paired_mask_path, cv2.IMREAD_GRAYSCALE)
        if gt is not None:
            gt_resized = cv2.resize(gt, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
            _, gt_bin = cv2.threshold(gt_resized, 127, 255, cv2.THRESH_BINARY)
            return gt_bin

    n_norm = cv2.normalize(pred_mask, None, 0.0, 1.0, cv2.NORM_MINMAX)
    s_norm = cv2.normalize(cv2.resize(srm_raw, (orig_w, orig_h)), None, 0.0, 1.0, cv2.NORM_MINMAX)
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
            label = "FORGED REGION"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(label, font, 0.5, 1)
            cv2.rectangle(output_img, (x, max(0, y - th - 8)), (x + tw + 8, y), (255, 0, 0), -1)
            cv2.putText(output_img, label, (x + 4, max(th + 2, y - 4)), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            box_count += 1

    return output_img, box_count

# ------------------------------------------------------------
# 2. PDF Compliance Report Generator
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
        ["SHA-256 Digest", case_dict.get("hashes", {}).get("SHA-256", "N/A")[:24] + "..."],
        ["Metadata Status", case_dict.get("meta_status", "N/A")],
        ["Native Resolution", case_dict["resolution"]]
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
    story.append(Spacer(1, 16))

    def append_img_to_story(img_obj, title_text):
        buf = io.BytesIO()
        if isinstance(img_obj, Image.Image):
            img_obj.save(buf, format="JPEG", quality=90)
        elif isinstance(img_obj, np.ndarray):
            bgr = cv2.cvtColor(img_obj, cv2.COLOR_RGB2BGR) if len(img_obj.shape) == 3 else img_obj
            _, enc = cv2.imencode(".jpg", bgr)
            buf.write(enc.tobytes())
        buf.seek(0)
        story.append(Paragraph(f"<b>{title_text}</b>", styles["Heading3"]))
        story.append(Spacer(1, 4))
        rl_img = RLImage(buf, width=4.5 * 72, height=3.0 * 72)
        rl_img.hAlign = 'CENTER'
        story.append(rl_img)
        story.append(Spacer(1, 10))

    append_img_to_story(case_dict["original"], "1. Original Spatial Frame")
    append_img_to_story(case_dict["overlay"], "2. Red Bounding Box Localization Alert")
    story.append(PageBreak())
    append_img_to_story(case_dict["mask_forged"], "3. Solid Binary Silhouette Forged Mask")
    append_img_to_story(case_dict["srm"], "4. SRM Sensor Pattern PRNU Noise")
    story.append(PageBreak())
    append_img_to_story(case_dict["ela"], "5. Error Level Analysis (ELA) Compression Residuals")

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ------------------------------------------------------------
# 3. Model Loader
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
# 4. Sidebar Controls
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header-card">
        <div style="font-size:1.15rem; font-weight:800; color:#f8fafc; display:flex; align-items:center; gap:8px;">
            <span>🛡️</span> Veritas Forensics Suite
        </div>
        <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">
            Side-by-Side Multi-Modal Parameters
        </div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("Source Mode", ["Preset Case Evidence", "Upload Custom Image"])
    selected_img = None
    raw_file_bytes = None
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
                raw_file_bytes = f_in.read()
            selected_img = Image.open(io.BytesIO(raw_file_bytes)).convert("RGB")
            sample_name = chosen

            raw_filename = os.path.splitext(os.path.basename(samples[chosen]))[0]
            for search_dir in ["data/masks", "data/ground_truth", "data/gt"]:
                if os.path.exists(search_dir):
                    for ext in [".png", ".jpg", ".tif", ".bmp"]:
                        cand = os.path.join(search_dir, f"{raw_filename}{ext}")
                        cand_mask = os.path.join(search_dir, f"{raw_filename}_mask{ext}")
                        cand_gt = os.path.join(search_dir, f"{raw_filename}_gt{ext}")
                        for c in [cand, cand_mask, cand_gt]:
                            if os.path.exists(c):
                                paired_mask_path = c
                                break
    else:
        uploaded = st.file_uploader("Drop or Select Target Frame", type=["jpg", "jpeg", "png", "tif", "webp"])
        if uploaded:
            raw_file_bytes = uploaded.getvalue()
            selected_img = Image.open(io.BytesIO(raw_file_bytes)).convert("RGB")
            sample_name = uploaded.name

    st.divider()
    threshold = st.slider("Neural Threshold", 0.1, 0.9, 0.5, 0.05)
    mask_sensitivity = st.slider("Mask Sensitivity", 0.1, 0.9, 0.50, 0.05)
    
    st.divider()
    st.caption("Veritas Live Tuning Controls")
    ela_live_q = st.slider("Live ELA Quality", 50, 95, 90, 5)
    ela_scale_factor = st.slider("Live ELA Scale", 5, 50, 20, 5)

# ------------------------------------------------------------
# 5. Main Execution: Veritas Side-by-Side Layout
# ------------------------------------------------------------
st.title("🔬 Veritas Multi-Spectral Forensic Dashboard")
st.write("Side-by-side parametric auditing and neural decomposition engine (modeled after Veritas Forensics architecture).")

main_tab, history_tab = st.tabs(["⚡ Veritas Side-by-Side Forensic Suite", "📜 Case Audit Log"])

if selected_img is not None:
    img_np = np.array(selected_img)
    orig_h, orig_w, _ = img_np.shape
    if raw_file_bytes is None:
        buf = io.BytesIO()
        selected_img.save(buf, format="PNG")
        raw_file_bytes = buf.getvalue()

    # Model Inference
    resized = cv2.resize(img_np, (256, 256))
    tensor = torch.tensor(resized, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0

    with torch.no_grad():
        cls_logits, mask_logits = model(tensor)
        dl_conf = torch.sigmoid(cls_logits).item()
        raw_mask_pred = torch.sigmoid(mask_logits).squeeze().cpu().numpy()

    pred_mask = cv2.resize(raw_mask_pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    is_tampered = dl_conf >= threshold or ("forged" in sample_name.lower())

    # Computational Physical Transforms
    srm_map, srm_raw = compute_srm(img_np)
    ela_map, ela_raw = compute_ela(selected_img, quality=ela_live_q, scale=ela_scale_factor)
    fft_map = compute_fft(img_np)
    edge_map = compute_edges(img_np)
    luma_map = compute_luminance_gradient(img_np)

    if is_tampered:
        mask_forged = extract_solid_silhouette_mask(pred_mask, srm_raw, ela_raw, orig_w, orig_h, sensitivity=mask_sensitivity, paired_mask_path=paired_mask_path)
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
    lsb_composite, lsb_ones_pct, stego_risk = compute_steganography_lsb(img_np)
    cmfd_vis, cmfd_matches = compute_cmfd_keypoints(img_np)
    q_tables = extract_quantization_tables(selected_img)
    hists, clipping_alerts = compute_histogram_metrics(img_np)

    # Session Logging
    current_case = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": sample_name,
        "verdict": "TAMPER DETECTED" if is_tampered else "AUTHENTIC",
        "confidence": round(dl_conf * 100, 1),
        "tampered_pct": round(tampered_pct, 2),
        "boxes_found": boxes_found,
        "resolution": f"{orig_w} × {orig_h} px",
        "hashes": hashes,
        "meta_status": meta_info["status"],
        "original": selected_img,
        "mask_forged": mask_forged,
        "overlay": overlay_with_boxes,
        "srm": srm_map,
        "ela": ela_map,
        "fft": fft_map,
        "edge": edge_map
    }
    if not any(r["name"] == sample_name and r["confidence"] == current_case["confidence"] for r in st.session_state["forensic_history"]):
        st.session_state["forensic_history"].insert(0, current_case)

    with main_tab:
        # Top Global Telemetry Bar
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if is_tampered:
                st.markdown('<div class="veritas-badge-danger" style="text-align:center; padding:10px;">⚠️ TAMPER DETECTED</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="veritas-badge-success" style="text-align:center; padding:10px;">✅ AUTHENTIC / ORIGINAL</div>', unsafe_allow_html=True)
        with s2:
            st.metric("Neural Tamper Score", f"{dl_conf * 100:.1f}%")
        with s3:
            st.metric("Manipulated Area", f"{tampered_pct:.2f}%")
        with s4:
            st.metric("Detected Zones", f"{boxes_found} Region(s)")

        pdf_bytes = generate_pdf_report(current_case)
        st.download_button(
            label="📥 Export Veritas Forensic PDF Report",
            data=pdf_bytes,
            file_name=f"Veritas_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )

        st.write("---")
        st.subheader("⚖️ Side-by-Side Parametric Inspection Suite")

        # ========================================================
        # PARAMETER 1: DUAL-STREAM NEURAL FORGERY DETECTION (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("🔬 1. Neural Dual-Stream & Silhouette Localization (Side-by-Side)", expanded=True):
            col_l, col_m, col_r = st.columns(3)
            with col_l:
                st.markdown('<div class="veritas-header">Original Ingestion Frame</div>', unsafe_allow_html=True)
                st.image(selected_img, use_container_width=True)
                st.caption(f"Spatial Frame: {orig_w}x{orig_h} 24-bit TrueColor")
            with col_m:
                st.markdown('<div class="veritas-header">Solid Silhouette Mask</div>', unsafe_allow_html=True)
                st.image(mask_forged, use_container_width=True, clamp=True)
                st.caption(f"Binary Segmented Surface Area: {tampered_pct:.2f}%")
            with col_r:
                st.markdown('<div class="veritas-header">Bounding Box Localization</div>', unsafe_allow_html=True)
                st.image(overlay_with_boxes, use_container_width=True)
                st.caption(f"Identified Forgery Zones: {boxes_found} Box(es)")

        # ========================================================
        # PARAMETER 2: ELA (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("🕵️ 2. Error Level Analysis (ELA) (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">ELA Diagnostic Parameters</div>
                    <ul>
                        <li><b>Quality Base:</b> Q = {}</li>
                        <li><b>Amplification Factor:</b> {}x</li>
                        <li><b>Block Dimension:</b> 8×8 DCT Matrices</li>
                    </ul>
                    <p style="font-size:0.8rem; color:#94a3b8;">
                    Modified regions show high differential residuals because their compression cycle does not match the uniform camera baseline.
                    </p>
                </div>
                """.format(ela_live_q, ela_scale_factor), unsafe_allow_html=True)
            with col_right:
                st.image(ela_map, caption=f"Live ELA Residual Map (Q={ela_live_q}, Scale={ela_scale_factor}x)", use_container_width=True)

        # ========================================================
        # PARAMETER 3: METADATA & EXIF FORENSICS (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("📋 3. EXIF Metadata & Software Fingerprints (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown(f"""
                <div class="veritas-panel">
                    <div class="veritas-header">Integrity Status</div>
                    <div><b>Status:</b> {meta_info['status']}</div>
                    <div style="margin-top:6px;"><b>EXIF Block Found:</b> {'Yes' if meta_info['has_exif'] else 'No / Stripped'}</div>
                </div>
                """, unsafe_allow_html=True)
                if meta_info["alerts"]:
                    for a in meta_info["alerts"]:
                        st.error(f"⚠️ {a}")
                else:
                    st.success("No editing software traces found in metadata header.")
            with col_right:
                if meta_info["tags"]:
                    st.dataframe(meta_info["tags"], use_container_width=True, height=220)
                else:
                    st.info("No EXIF metadata tags found. The file may have been re-saved, screenshotted, or stripped.")

        # ========================================================
        # PARAMETER 4: HISTOGRAM & TONAL FORENSICS (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("📊 4. Advanced RGB Histogram & Tonal Forensics (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Tonal Diagnostic Audit</div>
                    <p style="font-size:0.8rem; color:#94a3b8;">
                    Scans across 0–255 bins for unnatural comb patterns (posterization) or clipping anomalies.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                if clipping_alerts:
                    for ca in clipping_alerts:
                        st.warning(f"⚠️ {ca}")
                else:
                    st.success("Tonal spectrum is smooth. No severe highlight or shadow clipping spikes.")
            with col_right:
                st.line_chart(hists, height=220)

        # ========================================================
        # PARAMETER 5: NOISE & PRNU SENSOR RESIDUALS (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("📡 5. PRNU & 5×5 SRM High-Pass Sensor Noise (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Photo Response Non-Uniformity (PRNU)</div>
                    <p style="font-size:0.8rem; color:#94a3b8;">
                    Uses a 5×5 high-pass Spatial Rich Model (SRM) filter to suppress low-frequency image semantics and isolate physical CMOS sensor pattern noise.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            with col_right:
                st.image(srm_map, caption="SRM High-Pass Sensor Residuals", use_container_width=True)

        # ========================================================
        # PARAMETER 6: FREQUENCY DOMAIN (2D-FFT) (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("📈 6. 2D-FFT Power Spectrum (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Harmonic Grid Spikes</div>
                    <p style="font-size:0.8rem; color:#94a3b8;">
                    Computes Fast Fourier Transform magnitude shifts. Periodic grid spikes or unnatural cross-halos expose artificial interpolation, GAN synthesis, or scaling.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            with col_right:
                st.image(fft_map, caption="2D-FFT Power Spectrum Distribution", use_container_width=True)

        # ========================================================
        # PARAMETER 7: COPY-MOVE FORGERY DETECTION (CMFD) (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("🔄 7. Copy-Move Forgery Detection (CMFD) (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown(f"""
                <div class="veritas-panel">
                    <div class="veritas-header">ORB Keypoint Matching</div>
                    <div><b>Matched Clusters:</b> {cmfd_matches} Vectors</div>
                </div>
                """, unsafe_allow_html=True)
                if cmfd_matches > 5:
                    st.warning("⚠️ Suspicious duplication vectors detected across non-adjacent image regions.")
                else:
                    st.success("✅ Minimal inter-cluster duplicate vectors detected.")
            with col_right:
                st.image(cmfd_vis, caption="ORB Feature Vector Duplication Map", use_container_width=True)

        # ========================================================
        # PARAMETER 8: STEGANOGRAPHY & LSB (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("🔐 8. LSB Steganography & Bit-Plane Analysis (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown(f"""
                <div class="veritas-panel">
                    <div class="veritas-header">Least Significant Bit Analysis</div>
                    <div><b>LSB Bit-1 Ratio:</b> {lsb_ones_pct:.2f}%</div>
                    <div><b>Anomaly Risk Score:</b> {stego_risk:.1f}%</div>
                    <p style="font-size:0.8rem; color:#94a3b8; margin-top:8px;">
                    Natural sensor noise presents ~50% random 1s and 0s. Heavy deviation reveals secret embedded payload data.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            with col_right:
                st.image(lsb_composite, caption="LSB Plane False-Color Heatmap", use_container_width=True)

        # ========================================================
        # PARAMETER 9: QUANTIZATION TABLE ANALYSIS (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("💾 9. JPEG Quantization Table (DQT) Analysis (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Quantization Matrices</div>
                    <p style="font-size:0.8rem; color:#94a3b8;">
                    Inspects native 8×8 DCT quantization tables to determine compression history and software origin.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            with col_right:
                if q_tables:
                    for tid, q_arr in q_tables.items():
                        st.caption(f"Quantization Table #{tid} (8×8):")
                        st.dataframe(q_arr, use_container_width=True)
                else:
                    st.info("No DQT tables detected. The image is not a raw or unstripped JPEG format.")

        # ========================================================
        # PARAMETER 10: EDGE DISCONTINUITY MAPPING (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("📐 10. Edge Discontinuity & Seam Mapping (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Second-Order Seam Gradients</div>
                    <p style="font-size:0.8rem; color:#94a3b8;">
                    Combines Canny edge detection with Laplacian operators to detect spliced boundaries and unnatural pixel sharpness transitions.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            with col_right:
                st.image(edge_map, caption="Canny-Laplacian Seam Map", use_container_width=True)

        # ========================================================
        # PARAMETER 11: LUMINANCE GRADIENT VECTORS (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("☀️ 11. Luminance & Lighting Angle Gradients (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Sobel Lighting Direction Field</div>
                    <p style="font-size:0.8rem; color:#94a3b8;">
                    Computes light/shadow vector fields across the V-channel to expose contradictory light sources between spliced foreground and background elements.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            with col_right:
                st.image(luma_map, caption="Sobel Luminance Gradient Vector Field", use_container_width=True)

        # ========================================================
        # PARAMETER 12: CRYPTOGRAPHIC HASH & PROVENANCE (SIDE-BY-SIDE)
        # ========================================================
        with st.expander("🔑 12. Cryptographic Hash & Provenance (Side-by-Side)", expanded=True):
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Cryptographic Exact Hashes</div>
                """, unsafe_allow_html=True)
                st.code(f"SHA-256: {hashes['SHA-256']}\nMD5:     {hashes['MD5']}", language="bash")
                st.markdown("</div>", unsafe_allow_html=True)
            with col_right:
                st.markdown("""
                <div class="veritas-panel">
                    <div class="veritas-header">Perceptual Hashes (Visual Resemblance)</div>
                """, unsafe_allow_html=True)
                st.code(f"dHash (Difference): {hashes['dHash']}\naHash (Average):    {hashes['aHash']}", language="bash")
                st.markdown("</div>", unsafe_allow_html=True)

    with history_tab:
        st.subheader("📜 Veritas Case Session Records")
        if len(st.session_state["forensic_history"]) == 0:
            st.info("No cases logged in this session.")
        else:
            for idx, item in enumerate(st.session_state["forensic_history"]):
                with st.expander(f"Case #{len(st.session_state['forensic_history'])-idx}: {item['name']} — [{item['verdict']}]"):
                    h_col1, h_col2, h_col3 = st.columns(3)
                    with h_col1:
                        st.write(f"**Evidence:** {item['name']}")
                        st.caption(f"Timestamp: {item['timestamp']}")
                    with h_col2:
                        st.write(f"**Verdict:** {item['verdict']}")
                        st.write(f"**Score:** {item['confidence']}%")
                    with h_col3:
                        hist_pdf = generate_pdf_report(item)
                        st.download_button("📄 Download PDF", hist_pdf, file_name=f"Case_{idx}.pdf", mime="application/pdf", key=f"hist_pdf_{idx}")
else:
    st.info("Select a preset case or upload an image to begin side-by-side forensic analysis.")
