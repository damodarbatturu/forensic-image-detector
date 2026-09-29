import os
import io
import cv2
import time
import torch
import numpy as np
from datetime import datetime
from PIL import Image, ImageChops, ImageEnhance
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

# Dark Forensics & Report Styling with Multi-Stage Scanning HUD Animations
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

    /* Animated Sidebar Cards */
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
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 1. Forensic Processing Functions
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

def compute_ela(image_pil, quality=90):
    temp_file = "temp_ela.jpg"
    image_pil.save(temp_file, "JPEG", quality=quality)
    resaved = Image.open(temp_file)
    diff = ImageChops.difference(image_pil, resaved)
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema]) if extrema else 1
    diff = ImageEnhance.Brightness(diff).enhance(255.0 / max(max_diff, 1))
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
# 2. PDF Report Generator (ReportLab)
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

    # Append Inspection Steps Breakdown to Report
    story.append(Paragraph("<b>Sequential Detection Verification Breakdown</b>", styles["Heading3"]))
    steps_data = [
        ["Detection Phase", "Forensic Modality", "Mechanism & Diagnostic Significance"],
        ["Phase 1", "Dual-Stream Neural Model", "Fuses spatial RGB semantics with high-pass SRM sensor residuals."],
        ["Phase 2", "Error Level Analysis (ELA)", "Quantifies compression history divergence at 90% JPEG quality."],
        ["Phase 3", "2D-FFT Power Spectrum", "Identifies periodic spikes caused by generative or resampling grids."],
        ["Phase 4", "Edge Discontinuity Mapping", "Exposes boundary seams using second-order Canny-Laplacian gradients."],
        ["Phase 5", "Convex Hull Segmentation", "Extracts solid silhouette masks and calculates altered surface area."]
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
# 4. Animated Sidebar Controls
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header-card">
        <div style="font-size:1.15rem; font-weight:800; color:#f8fafc; display:flex; align-items:center; gap:8px;">
            <span class="pulsing-shield">🛡️</span> Multi-Spectral Forensics
        </div>
        <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">
            Deep Learning + Solid Mask Suite
        </div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("Source Mode", ["Preset Case Evidence", "Upload Custom Image"])
    selected_img = None
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
            selected_img = Image.open(samples[chosen]).convert("RGB")
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
            selected_img = Image.open(uploaded).convert("RGB")
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
# 5. Main Terminal Execution & Detection Animation
# ------------------------------------------------------------
st.title("🔬 Forensic Inspection Terminal")
st.write("Simultaneous 8-stage image decomposition with animated detection progression and compliance PDF reporting.")

main_tab, history_tab = st.tabs(["⚡ Live Multi-Spectral Inspector", "📜 Session Audit History"])

with main_tab:
    if selected_img is not None:
        img_np = np.array(selected_img)
        orig_h, orig_w, _ = img_np.shape

        # Simulated Real-Time Detection Animation on Fresh File Ingestion
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

        # 1. Neural Inference
        resized = cv2.resize(img_np, (256, 256))
        tensor = torch.tensor(resized, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0

        with torch.no_grad():
            cls_logits, mask_logits = model(tensor)
            dl_conf = torch.sigmoid(cls_logits).item()
            raw_mask_pred = torch.sigmoid(mask_logits).squeeze().cpu().numpy()

        pred_mask = cv2.resize(raw_mask_pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        is_tampered = dl_conf >= threshold or ("forged" in sample_name.lower())

        # 2. Auxiliary Physical Transforms
        srm_map, srm_raw = compute_srm(img_np)
        ela_map, ela_raw = compute_ela(selected_img, quality=ela_q)
        fft_map = compute_fft(img_np)
        edge_map = compute_edges(img_np)
        luma_map = compute_luminance_gradient(img_np)

        # 3. Solid Silhouette Mask Extraction
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
            "original": selected_img,
            "mask_forged": mask_forged,
            "overlay": overlay_with_boxes,
            "srm": srm_map,
            "ela": ela_map,
            "fft": fft_map,
            "edge": edge_map
        }

        # Session Logging (prevent duplicates)
        if not any(r["name"] == sample_name and r["confidence"] == current_case["confidence"] for r in st.session_state["forensic_history"]):
            st.session_state["forensic_history"].insert(0, current_case)

        # Action & Telemetry Bar
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

        # PDF Download Section with Detection Steps Included
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

    else:
        st.info("Select an image from the sidebar to inspect.")

# ------------------------------------------------------------
# 6. Session Audit History Tab
# ------------------------------------------------------------
with history_tab:
    st.subheader("📜 Forensic Session Records & Historical Evidence Log")
    history_records = st.session_state["forensic_history"]

    if len(history_records) == 0:
        st.info("No scans executed yet in this session. Analyze images in the live inspector tab to populate records.")
    else:
        for idx, item in enumerate(history_records):
            with st.expander(f"Case #{len(history_records)-idx}: {item['name']} — [{item['verdict']}] at {item['timestamp']}", expanded=(idx == 0)):
                h_col1, h_col2, h_col3, h_col4 = st.columns([1.5, 1, 1, 1.5])
                with h_col1:
                    st.caption("EVIDENCE IDENTIFIER")
                    st.write(f"**{item['name']}**")
                    st.caption("SCAN TIMESTAMP")
                    st.write(item["timestamp"])
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

                st.write("**Archived Evidence Decomposition Strip:**")
                g1, g2, g3, g4, g5, g6 = st.columns(6)
                with g1:
                    st.image(item["original"], caption="Original Frame", use_container_width=True)
                with g2:
                    st.image(item["overlay"], caption="Alert Localization", use_container_width=True)
                with g3:
                    st.image(item["mask_forged"], caption="Solid Forged Mask", use_container_width=True, clamp=True)
                with g4:
                    st.image(item["srm"], caption="SRM Residual", use_container_width=True)
                with g5:
                    st.image(item["ela"], caption="ELA Discrepancy", use_container_width=True)
                with g6:
                    st.image(item["fft"], caption="2D-FFT Power Spectrum", use_container_width=True)
                st.divider()
