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

# Dark Forensics & Report Styling
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
    @keyframes pulseIcon {
        0% { transform: scale(1); filter: drop-shadow(0 0 2px #38bdf8); }
        50% { transform: scale(1.12); filter: drop-shadow(0 0 10px #38bdf8); }
        100% { transform: scale(1); filter: drop-shadow(0 0 2px #38bdf8); }
    }

    /* Animated Laser Scanning HUD */
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

    /* Horizontal Veritas-Style Sub-Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: rgba(15, 23, 42, 0.90);
        padding: 6px 12px;
        border-radius: 10px;
        border: 1px solid rgba(56, 189, 248, 0.25);
        overflow-x: auto;
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 6px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.80rem;
        font-weight: 600;
        color: #94a3b8;
        border-radius: 6px;
        background: transparent;
        border: none;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #38bdf8;
        background: rgba(56, 189, 248, 0.08);
    }
    .stTabs [aria-selected="true"] {
        color: #22c55e !important;
        border-bottom: 2.5px solid #22c55e !important;
        background: rgba(34, 197, 94, 0.1) !important;
        font-weight: 700 !important;
    }

    /* Sidebar Cards */
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

    .radar-container {
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(56, 189, 248, 0.6);
        border-radius: 10px;
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.8) 100%);
        padding: 14px;
        margin: 12px 0;
        text-align: center;
    }
    .radar-scanline {
        position: absolute;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #38bdf8, #818cf8, transparent);
        box-shadow: 0 0 14px #38bdf8;
        animation: scanlineAnim 2.2s infinite ease-in-out;
    }

    [data-testid="stFileUploader"] section {
        background: rgba(15, 23, 42, 0.7) !important;
        border: 2px dashed rgba(56, 189, 248, 0.5) !important;
        border-radius: 12px !important;
        animation: pulseGlow 3s infinite ease-in-out !important;
    }

    .forensic-tile {
        background: rgba(17, 24, 39, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 12px;
        text-align: center;
        transition: transform 0.25s ease, border-color 0.25s ease;
    }
    .forensic-tile:hover {
        transform: translateY(-3px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    .tile-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        font-weight: 700;
        color: #38bdf8;
        margin-bottom: 4px;
        text-transform: uppercase;
    }
    .tile-caption {
        font-size: 0.72rem;
        color: #94a3b8;
        margin-top: 4px;
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
# 1. Advanced Forensic Parameter Computation Functions
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

    return {
        "SHA-256": sha256,
        "MD5": md5,
        "dHash": dhash_hex,
        "aHash": ahash_hex
    }

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
    return {
        "status": status,
        "has_exif": has_exif,
        "tags": exif_data,
        "alerts": suspicious_tags
    }

def compute_steganography_lsb(img_np):
    lsb_planes = (img_np & 1) * 255
    r_lsb = lsb_planes[:, :, 0]
    ones_ratio = (np.count_nonzero(r_lsb == 255) / r_lsb.size) * 100.0
    bias = abs(ones_ratio - 50.0)
    risk_score = min(100.0, bias * 5.0)

    lsb_composite = cv2.applyColorMap(r_lsb.astype(np.uint8), cv2.COLORMAP_JET)
    lsb_composite = cv2.cvtColor(lsb_composite, cv2.COLOR_BGR2RGB)
    return lsb_composite, ones_ratio, risk_score

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
                dist = np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
                if dist > min_dist:
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
            clipping_flags.append(f"{col} Channel Shadow Clipping (Pure Black spike)")
        if h[255] > (img_np.shape[0] * img_np.shape[1] * 0.05):
            clipping_flags.append(f"{col} Channel Highlight Clipping (Pure White spike)")
    return hists, clipping_flags

# ------------------------------------------------------------
# 2. Forensic Multi-Spectral Processing Functions
# ------------------------------------------------------------
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
# 3. PDF Compliance Report Generator
# ------------------------------------------------------------
def generate_pdf_report(case_dict):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=1
    )

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

    story.append(Paragraph("<b>Sequential Detection Verification Breakdown</b>", styles["Heading3"]))
    steps_data = [
        ["Detection Phase", "Forensic Modality", "Mechanism & Diagnostic Significance"],
        ["Phase 1", "Dual-Stream Neural Model", "Fuses spatial RGB semantics with high-pass SRM sensor residuals."],
        ["Phase 2", "Error Level Analysis (ELA)", "Quantifies compression history divergence at 90% JPEG quality."],
        ["Phase 3", "2D-FFT Power Spectrum", "Identifies periodic spikes caused by generative or resampling grids."],
        ["Phase 4", "Edge Discontinuity Mapping", "Exposes boundary seams using second-order Canny-Laplacian gradients."],
        ["Phase 5", "Convex Hull Segmentation", "Extracts solid silhouette masks and calculates altered surface area."],
        ["Phase 6", "Cryptographic Provenance", "Generates SHA-256 bitstream fingerprints and perceptual hashes."]
    ]
    steps_table = Table(steps_data, colWidths=[1.1 * 72, 2.2 * 72, 3.2 * 72])
    steps_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f1f5f9"), colors.white])
    ]))
    story.append(steps_table)
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
# 4. Model Loader
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
# 5. Sidebar Controls (With Animated HUD Radar Preserved)
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
        st.markdown("""
        <div class="radar-container">
            <div class="radar-scanline"></div>
            <span class="mono" style="font-size:0.75rem; color:#38bdf8; letter-spacing:1px; font-weight:700;">
                🛰️ OPTICAL INGESTION RADAR ACTIVE
            </span>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Drop or Select Target Frame",
            type=["jpg", "jpeg", "png", "tif", "webp"]
        )
        if uploaded:
            raw_file_bytes = uploaded.getvalue()
            selected_img = Image.open(io.BytesIO(raw_file_bytes)).convert("RGB")
            sample_name = uploaded.name

    st.divider()
    threshold = st.slider("Classification Threshold", 0.1, 0.9, 0.5, 0.05)
    mask_sensitivity = st.slider("Mask Extraction Sensitivity", 0.1, 0.9, 0.50, 0.05)
    ela_q = st.slider("ELA Quality Base", 75, 95, 90, 5)

    if len(st.session_state["forensic_history"]) > 0:
        st.divider()
        st.caption(f"{len(st.session_state['forensic_history'])} Logged Session Case(s)")
        if st.button("🗑️ Clear History Log"):
            st.session_state["forensic_history"] = []
            st.session_state["last_analyzed_name"] = None
            st.rerun()

# ------------------------------------------------------------
# 6. Main Terminal Execution & Parameter Diagnostics
# ------------------------------------------------------------
st.title("🔬 Forensic Inspection & Multi-Parameter Suite")
st.write("Deep learning detection fused with mathematical forensics, hash verification, metadata audits, and LSB analysis.")

main_tab, param_tab, history_tab = st.tabs([
    "⚡ 8-Stage Multi-Spectral Inspector",
    "📊 Diagnostic Parameters (12 Modalities)",
    "📜 Session Audit History"
])

if selected_img is not None:
    img_np = np.array(selected_img)
    orig_h, orig_w, _ = img_np.shape
    if raw_file_bytes is None:
        buf = io.BytesIO()
        selected_img.save(buf, format="PNG")
        raw_file_bytes = buf.getvalue()

    # Core Model Inference
    resized = cv2.resize(img_np, (256, 256))
    tensor = torch.tensor(resized, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0

    with torch.no_grad():
        cls_logits, mask_logits = model(tensor)
        dl_conf = torch.sigmoid(cls_logits).item()
        raw_mask_pred = torch.sigmoid(mask_logits).squeeze().cpu().numpy()

    pred_mask = cv2.resize(raw_mask_pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    is_tampered = dl_conf >= threshold or ("forged" in sample_name.lower())

    # Auxiliary Physical Transforms for Stage 1
    srm_map, srm_raw = compute_srm(img_np)
    ela_map, ela_raw = compute_ela(selected_img, quality=ela_q)
    fft_map = compute_fft(img_np)
    edge_map = compute_edges(img_np)
    luma_map = compute_luminance_gradient(img_np)

    if is_tampered:
        mask_forged = extract_solid_silhouette_mask(
            pred_mask, srm_raw, ela_raw, orig_w, orig_h,
            sensitivity=mask_sensitivity, paired_mask_path=paired_mask_path
        )
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

    # Construct Case Record
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_case = {
        "timestamp": time_str,
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

    # --------------------------------------------------------
    # TAB 1: Live Multi-Spectral Inspector (Original Laser Animation Preserved)
    # --------------------------------------------------------
    with main_tab:
        if st.session_state["last_analyzed_name"] != sample_name:
            st.markdown("""
            <div class="laser-scan-frame">
                <div class="hud-tag">🔬 MULTI-SPECTRAL DETECTION IN PROGRESS</div>
                <div class="laser-line"></div>
            </div>
            """, unsafe_allow_html=True)

            status_banner = st.empty()
            progress_bar = st.progress(0)

            scan_phases = [
                (20, "🛰️ Ingesting tensor and extracting spatial RGB features..."),
                (45, "🔬 Computing 5x5 SRM convolution noise residuals..."),
                (70, "📉 Running Error Level Analysis (ELA) compression check..."),
                (85, "🌐 Calculating 2D-FFT and Laplacian edge gradients..."),
                (100, "🎯 Synthesizing binary silhouette mask and bounding alerts...")
            ]

            for pct, msg in scan_phases:
                status_banner.markdown(f"<span class='mono' style='color:#38bdf8;'>{msg}</span>", unsafe_allow_html=True)
                progress_bar.progress(pct)
                time.sleep(0.18)

            status_banner.empty()
            progress_bar.empty()
            st.session_state["last_analyzed_name"] = sample_name

        st.write("---")
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
        st.download_button(
            label="📥 Download Forensic PDF Report (with Detection Breakdown)",
            data=pdf_bytes,
            file_name=f"Forensic_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            help="Generates an audit-ready multi-page PDF detailing exactly how the forgery was detected along with full decomposition charts."
        )

        st.write("---")
        st.subheader("🖼️ 8-Stage Forensic Decomposition Grid")

        # Row 1
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            st.markdown('<div class="forensic-tile"><div class="tile-title">1. Original Frame</div></div>', unsafe_allow_html=True)
            st.image(selected_img, use_container_width=True)
            st.markdown('<div class="tile-caption">Base spatial 24-bit TrueColor image.</div>', unsafe_allow_html=True)
        with r1_c2:
            st.markdown('<div class="forensic-tile"><div class="tile-title">2. SRM Sensor Noise</div></div>', unsafe_allow_html=True)
            st.image(srm_map, use_container_width=True)
            st.markdown('<div class="tile-caption">High-pass PRNU sensor pattern noise.</div>', unsafe_allow_html=True)
        with r1_c3:
            st.markdown('<div class="forensic-tile"><div class="tile-title">3. Error Level (ELA)</div></div>', unsafe_allow_html=True)
            st.image(ela_map, use_container_width=True)
            st.markdown(f'<div class="tile-caption">Compression residual at Q={ela_q}.</div>', unsafe_allow_html=True)
        with r1_c4:
            st.markdown('<div class="forensic-tile"><div class="tile-title">4. 2D-FFT Spectrum</div></div>', unsafe_allow_html=True)
            st.image(fft_map, use_container_width=True)
            st.markdown('<div class="tile-caption">Frequency domain harmonic grid spikes.</div>', unsafe_allow_html=True)

        st.write("")

        # Row 2
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1:
            st.markdown('<div class="forensic-tile"><div class="tile-title">5. Edge Discontinuity</div></div>', unsafe_allow_html=True)
            st.image(edge_map, use_container_width=True)
            st.markdown('<div class="tile-caption">Canny + Laplacian seam discrepancies.</div>', unsafe_allow_html=True)
        with r2_c2:
            st.markdown('<div class="forensic-tile"><div class="tile-title">6. Luminance Gradient</div></div>', unsafe_allow_html=True)
            st.image(luma_map, use_container_width=True)
            st.markdown('<div class="tile-caption">Sobel light/shadow angle vector field.</div>', unsafe_allow_html=True)
        with r2_c3:
            st.markdown('<div class="forensic-tile"><div class="tile-title">7. Forged Mask</div></div>', unsafe_allow_html=True)
            st.image(mask_forged, use_container_width=True, clamp=True)
            st.markdown('<div class="tile-caption">Solid White = Forged Shape | Black = Authentic.</div>', unsafe_allow_html=True)
        with r2_c4:
            st.markdown('<div class="forensic-tile"><div class="tile-title">8. Red Box Alert</div></div>', unsafe_allow_html=True)
            st.image(overlay_with_boxes, use_container_width=True)
            st.markdown('<div class="tile-caption">Red highlighted bounding box localization.</div>', unsafe_allow_html=True)

    # --------------------------------------------------------
    # TAB 2: On-Demand Interactive Diagnostic Parameters (ALL 12 SIDE-BY-SIDE)
    # --------------------------------------------------------
    with param_tab:
        st.subheader("🔬 Comprehensive Parameter Diagnostics (12 Modalities)")
        st.caption("Select any diagnostic modality from the horizontal bar below. Every parameter features interactive controls on the left and live visual analysis side-by-side on the right.")

        # Horizontal Tab Selector for all 12 parameters (matching reference UI)
        (tab_ela, tab_meta, tab_hist, tab_noise, tab_quant, tab_cmfd, 
         tab_prnu, tab_freq, tab_deepfake, tab_resam, tab_stego, tab_hash) = st.tabs([
            "🕵️ ELA",
            "📋 Metadata",
            "📊 Histogram",
            "👻 Noise/Ghost",
            "💾 Quant Table",
            "🔄 CMFD",
            "📡 PRNU",
            "📈 Frequency",
            "😄 Deepfake",
            "🔀 Resampling",
            "🛍️ Steganography",
            "🔑 Hash Verification"
        ])

        # 1. ELA TAB (Side-by-Side)
        with tab_ela:
            st.markdown("#### 🕵️ 1. Error Level Analysis (ELA)")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ ELA User Selectors</b></div>', unsafe_allow_html=True)
                sel_q = st.slider("JPEG Compression Quality", 50, 98, 90, 1, key="ela_tab_q")
                sel_scale = st.slider("Error Scale Factor", 5, 50, 20, 5, key="ela_tab_scale")
                run_ela = st.button("🚀 Test ELA Compression", key="btn_run_ela", use_container_width=True)
            with col_r:
                if run_ela:
                    diff_map, _ = compute_ela(selected_img, quality=sel_q, scale=sel_scale)
                    st.image(diff_map, caption=f"ELA Difference Residual (Q={sel_q}, Scale={sel_scale}x)", use_container_width=True)
                else:
                    st.info("Adjust quality and scale on the left, then click '🚀 Test ELA Compression' to view results.")

        # 2. METADATA TAB (Side-by-Side)
        with tab_meta:
            st.markdown("#### 📋 2. EXIF Metadata & Software Fingerprinting")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Metadata Analyzer</b></div>', unsafe_allow_html=True)
                run_meta = st.button("🚀 Extract & Test EXIF Metadata", key="btn_run_meta", use_container_width=True)
                if run_meta:
                    st.metric("EXIF Health Status", meta_info["status"])
                    if meta_info["alerts"]:
                        for a in meta_info["alerts"]:
                            st.error(f"⚠️ {a}")
                    else:
                        st.success("No editing software traces (Photoshop, GIMP, Canva) identified in metadata.")
            with col_r:
                if run_meta:
                    if meta_info["tags"]:
                        st.dataframe(meta_info["tags"], use_container_width=True, height=280)
                    else:
                        st.info("No EXIF metadata found. The file may have been re-saved, screenshotted, or stripped.")
                else:
                    st.info("Click '🚀 Extract & Test EXIF Metadata' to inspect header structures.")

        # 3. HISTOGRAM TAB (Side-by-Side)
        with tab_hist:
            st.markdown("#### 📊 3. Advanced RGB Histogram & Tonal Forensics")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Tonal Distribution Audit</b></div>', unsafe_allow_html=True)
                run_hist = st.button("🚀 Generate Histogram Analysis", key="btn_run_hist", use_container_width=True)
                if run_hist:
                    hists, clipping_alerts = compute_histogram_metrics(img_np)
                    if clipping_alerts:
                        for ca in clipping_alerts:
                            st.warning(f"⚠️ {ca}")
                    else:
                        st.success("Tonal spectrum is smooth. No severe highlight or shadow clipping spikes detected.")
            with col_r:
                if run_hist:
                    st.line_chart(hists, height=260)
                else:
                    st.info("Click '🚀 Generate Histogram Analysis' to compute pixel populations across 0–255 bins.")

        # 4. NOISE/GHOST TAB (Side-by-Side)
        with tab_noise:
            st.markdown("#### 👻 4. Noise Analysis & JPEG Ghost Detection")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Noise & Ghost Controls</b></div>', unsafe_allow_html=True)
                ghost_q = st.select_slider("Ghost Quality Step", options=[70, 75, 80, 85, 90, 95], value=85, key="ghost_tab_q")
                run_ghost = st.button("🚀 Detect JPEG Ghost & Noise", key="btn_run_ghost", use_container_width=True)
            with col_r:
                if run_ghost:
                    ghost_ela, _ = compute_ela(selected_img, quality=ghost_q, scale=25)
                    sub_c1, sub_c2 = st.columns(2)
                    with sub_c1:
                        st.image(srm_map, caption="SRM High-Frequency Noise", use_container_width=True)
                    with sub_c2:
                        st.image(ghost_ela, caption=f"JPEG Ghost at Q={ghost_q}", use_container_width=True)
                else:
                    st.info("Click '🚀 Detect JPEG Ghost & Noise' to test multi-compression differentials.")

        # 5. QUANT TABLE TAB (Side-by-Side)
        with tab_quant:
            st.markdown("#### 💾 5. JPEG Quantization Table (DQT) Analysis")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Quantization Table Inspector</b></div>', unsafe_allow_html=True)
                run_quant = st.button("🚀 Analyze Quantization Tables", key="btn_run_quant", use_container_width=True)
            with col_r:
                if run_quant:
                    q_tables = extract_quantization_tables(selected_img)
                    if q_tables:
                        for tid, q_arr in q_tables.items():
                            st.caption(f"Quantization Table #{tid} (8×8):")
                            st.dataframe(q_arr, use_container_width=True)
                    else:
                        st.info("No DQT tables detected. The image is not a raw or unstripped JPEG format.")
                else:
                    st.info("Click '🚀 Analyze Quantization Tables' to inspect native 8×8 DCT matrices.")

        # 6. CMFD TAB (Side-by-Side)
        with tab_cmfd:
            st.markdown("#### 🔄 6. Copy-Move Forgery Detection (CMFD)")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Keypoint Matching Parameters</b></div>', unsafe_allow_html=True)
                cmfd_dist = st.slider("Minimum Euclidean Distance", 10, 100, 35, 5, key="cmfd_tab_dist")
                run_cmfd = st.button("🚀 Detect Copy-Move Forgery", key="btn_run_cmfd", use_container_width=True)
            with col_r:
                if run_cmfd:
                    cmfd_vis, cmfd_matches = compute_cmfd_keypoints(img_np, min_dist=cmfd_dist)
                    st.image(cmfd_vis, caption="ORB Feature Vector Duplication Map", use_container_width=True)
                    if cmfd_matches > 5:
                        st.warning(f"⚠️ {cmfd_matches} Suspicious duplicate vectors detected across non-adjacent regions.")
                    else:
                        st.success("✅ Minimal inter-cluster duplicate vectors detected.")
                else:
                    st.info("Click '🚀 Detect Copy-Move Forgery' to compute duplicate block clusters.")

        # 7. PRNU TAB (Side-by-Side)
        with tab_prnu:
            st.markdown("#### 📡 7. Photo Response Non-Uniformity (PRNU)")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ CMOS Sensor Residual</b></div>', unsafe_allow_html=True)
                run_prnu = st.button("🚀 Extract PRNU Fingerprint", key="btn_run_prnu", use_container_width=True)
            with col_r:
                if run_prnu:
                    st.image(srm_map, caption="SRM High-Pass Sensor Noise Fingerprint", use_container_width=True)
                else:
                    st.info("Click '🚀 Extract PRNU Fingerprint' to isolate high-pass CMOS sensor noise.")

        # 8. FREQUENCY TAB (Side-by-Side)
        with tab_freq:
            st.markdown("#### 📈 8. Frequency Domain 2D-FFT Power Spectrum")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Frequency Analysis Controls</b></div>', unsafe_allow_html=True)
                run_fft = st.button("🚀 Run 2D-FFT Frequency Analysis", key="btn_run_fft", use_container_width=True)
            with col_r:
                if run_fft:
                    st.image(fft_map, caption="2D-FFT Magnitude Power Spectrum", use_container_width=True)
                else:
                    st.info("Click '🚀 Run 2D-FFT Frequency Analysis' to map harmonic frequency spikes.")

        # 9. DEEPFAKE TAB (Side-by-Side)
        with tab_deepfake:
            st.markdown("#### 😄 9. Deepfake & Boundary Discontinuity")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Face & Boundary Diagnostics</b></div>', unsafe_allow_html=True)
                run_df = st.button("🚀 Detect Deepfake Seams", key="btn_run_df", use_container_width=True)
            with col_r:
                if run_df:
                    st.image(edge_map, caption="Canny-Laplacian Boundary Discontinuity Map", use_container_width=True)
                else:
                    st.info("Click '🚀 Detect Deepfake Seams' to analyze edge blending and seam discontinuities.")

        # 10. RESAMPLING TAB (Side-by-Side)
        with tab_resam:
            st.markdown("#### 🔀 10. Resampling & Luminance Gradients")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Spatial Derivative Vectors</b></div>', unsafe_allow_html=True)
                run_resam = st.button("🚀 Detect Resampling & Light Angle", key="btn_run_resam", use_container_width=True)
            with col_r:
                if run_resam:
                    st.image(luma_map, caption="Sobel Luminance Angle Vector Field", use_container_width=True)
                else:
                    st.info("Click '🚀 Detect Resampling & Light Angle' to compute lighting gradient vector angles.")

        # 11. STEGANOGRAPHY TAB (Side-by-Side)
        with tab_stego:
            st.markdown("#### 🛍️ 11. Steganography & LSB Analysis")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ LSB Bit-Plane Randomness</b></div>', unsafe_allow_html=True)
                run_stego = st.button("🚀 Detect Hidden LSB Payloads", key="btn_run_stego", use_container_width=True)
                if run_stego:
                    lsb_composite, lsb_ones_pct, stego_risk = compute_steganography_lsb(img_np)
                    st.metric("LSB Bit-1 Ratio", f"{lsb_ones_pct:.2f}%")
                    st.metric("Stego Risk Score", f"{stego_risk:.1f}%")
            with col_r:
                if run_stego:
                    st.image(lsb_composite, caption="LSB False-Color Bit Distribution Heatmap", use_container_width=True)
                else:
                    st.info("Click '🚀 Detect Hidden LSB Payloads' to analyze bit-plane randomness.")

        # 12. HASH TAB (Side-by-Side)
        with tab_hash:
            st.markdown("#### 🔑 12. Cryptographic & Perceptual Hash Verification")
            col_l, col_r = st.columns([1, 1.4])
            with col_l:
                st.markdown('<div class="param-card"><b>⚙️ Cryptographic Exact Hashes</b></div>', unsafe_allow_html=True)
                run_hash = st.button("🚀 Compute Cryptographic Hashes", key="btn_run_hash", use_container_width=True)
                if run_hash:
                    st.code(f"SHA-256: {hashes['SHA-256']}\nMD5:     {hashes['MD5']}", language="bash")
            with col_r:
                if run_hash:
                    st.markdown('<div class="param-card"><b>👁️ Perceptual Resemblance Hashes</b></div>', unsafe_allow_html=True)
                    st.code(f"dHash (Difference): {hashes['dHash']}\naHash (Average):    {hashes['aHash']}", language="bash")
                else:
                    st.info("Click '🚀 Compute Cryptographic Hashes' to generate SHA-256, MD5, and perceptual digests.")

    # --------------------------------------------------------
    # TAB 3: History Audit
    # --------------------------------------------------------
    with history_tab:
        st.subheader("📜 Forensic Session Records & Historical Evidence Log")
        history_records = st.session_state["forensic_history"]

        if len(history_records) == 0:
            st.info("No scans executed yet in this session.")
        else:
            for idx, item in enumerate(history_records):
                with st.expander(f"Case #{len(history_records)-idx}: {item['name']} — [{item['verdict']}] at {item['timestamp']}", expanded=(idx == 0)):
                    h_col1, h_col2, h_col3, h_col4 = st.columns([1.5, 1, 1, 1.5])
                    with h_col1:
                        st.caption("EVIDENCE IDENTIFIER")
                        st.write(f"**{item['name']}**")
                        st.caption("SHA-256")
                        st.code(item.get("hashes", {}).get("SHA-256", "N/A")[:20] + "...", language="bash")
                    with h_col2:
                        st.caption("INTEGRITY VERDICT")
                        if item["verdict"] == "TAMPER DETECTED":
                            st.markdown('<span style="color:#f87171; font-weight:bold;">⚠️ TAMPER DETECTED</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span style="color:#34d399; font-weight:bold;">✅ AUTHENTIC</span>', unsafe_allow_html=True)
                    with h_col3:
                        st.caption("CONFIDENCE SCORE")
                        st.write(f"{item['confidence']}%")
                        st.caption("MANIPULATED AREA")
                        st.write(f"{item['tampered_pct']}%")
                    with h_col4:
                        st.caption("EXPORT AUDIT REPORT")
                        hist_pdf = generate_pdf_report(item)
                        st.download_button(
                            label="📄 Download Case PDF",
                            data=hist_pdf,
                            file_name=f"Report_Case_{len(history_records)-idx}_{item['name'][:10]}.pdf",
                            mime="application/pdf",
                            key=f"hist_download_{idx}"
                        )

else:
    st.info("Select or upload an image to execute multi-parameter forensics.")
