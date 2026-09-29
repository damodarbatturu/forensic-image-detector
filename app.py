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

    /* Sidebar Components */
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

    /* Technique Description Box */
    .technique-modal-box {
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid #38bdf8;
        border-radius: 10px;
        padding: 14px;
        margin-top: 12px;
        box-shadow: 0 4px 20px rgba(56, 189, 248, 0.2);
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
if "selected_tech" not in st.session_state:
    st.session_state["selected_tech"] = None

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
# 4. Comprehensive Technique Knowledge Base
# ------------------------------------------------------------
TECHNIQUE_DATA = {
    "ELA": {
        "title": "🕵️ Error Level Analysis (ELA)",
        "content": """
**What is ELA?**
Error Level Analysis is like a detective looking for touch-ups in a photograph. When you edit a digital image and save it as JPEG, the edited areas compress differently than the original areas. ELA highlights these compression differences to reveal potential manipulations.
Think of it like this: Imagine a painting where some areas have been repainted. The new paint (edited regions) will look slightly different from the old paint (original regions) under special lighting. ELA is that "special lighting" for digital images.

**What Does ELA Measure?**
* Compression inconsistencies across the image
* Difference in error levels between original and edited regions
* Block-level anomalies in 8×8 JPEG compression blocks
* Noise patterns that deviate from camera sensor characteristics

**How to Interpret Results:**
* **✅ Normal Patterns (Likely Authentic):** Uniform brightness across the entire ELA image, consistent error levels in similar texture regions, natural noise distribution matching camera characteristics, low overall error scores (typically < 20).
* **⚠️ Suspicious Patterns (Possible Manipulation):** Bright spots or regions standing out dramatically, sharp boundaries between high and low error areas, inconsistent compression in regions that should be similar, geometric shapes with different error levels than surroundings, high error scores (> 30) in specific regions.

**Common Artifacts Detected:**
* **Copy-Paste Forgeries:** Pasted regions show different compression levels; bright outlines appear around inserted objects.
* **Content Addition/Removal:** Edited areas glow brighter than untouched regions ("halo effects").
* **Splicing Attacks:** Images combined from multiple sources show distinct error level boundaries.
* **Enhancement Filters:** Sharpening, blurring, or color adjustments create elevated error patterns.
* **Cloning/Stamp Tool:** Cloned regions show different error levels than source with repeating variations.

**Visual Analogy:**
Imagine you have a document that's been photocopied multiple times:
* Original text (never edited) = uniform, consistent quality
* Whited-out and retyped sections = obvious differences in ink darkness
* Cut-and-paste sections = visible boundaries and quality mismatches

**Limitations & Best Practices:**
* Text overlays and high-contrast edges often glow bright naturally.
* Highly textured areas (grass, fabric) show naturally elevated error levels.
* Always compare ELA with metadata, noise analysis, and copy-move detection.
"""
    },
    "Metadata": {
        "title": "📋 Metadata Analysis",
        "content": """
**What is Metadata?**
Metadata is the "birth certificate" of a digital image – hidden information embedded in the file that tells the story of how, when, and where the photo was created. This data is automatically recorded by cameras and editing software but can reveal tampering.
Think of metadata like invisible ink on the back of a photograph recording camera settings, timestamps, GPS coordinates, and software tags.

**What Does Metadata Measure?**
* **EXIF Data:** Camera settings (ISO, aperture, shutter speed, focal length).
* **Device Information:** Camera make, model, serial number.
* **Timestamps:** Creation date, modification date, digitization date.
* **GPS Coordinates:** Location where photo was taken.
* **Software Tags:** Editing tools that processed the image (Photoshop, GIMP, Canva).
* **Thumbnail Data:** Embedded preview image comparisons.

**How to Interpret Results:**
* **✅ Normal Patterns:** Consistent timestamps (creation = modification time), full camera manufacturer data present, valid GPS, and thumbnail matching the main frame.
* **⚠️ Suspicious Patterns:** Completely stripped metadata, software signatures from photo editors, timestamp anomalies (modified before created), impossible camera parameters (ISO 0), or visual mismatch between thumbnail and main frame.

**Limitations & Best Practices:**
* Metadata can be faked or manually altered by sophisticated tools.
* Social media platforms routinely strip metadata for user privacy.
* Screenshots and messaging apps naturally lack original camera EXIF data.
* Cross-reference metadata with visual scene lighting, shadows, and weather.
"""
    },
    "Histogram": {
        "title": "📊 Histogram Analysis",
        "content": """
**What is Histogram Analysis?**
A histogram is like a "census of pixels" – it counts how many pixels in an image have each brightness or color level. By analyzing these distributions, we can detect unnatural patterns created by image manipulation.
Natural photos have smooth, bell-curve-like distributions, while edited photos introduce gaps, spikes, or unnatural cutoffs.

**What Does Histogram Analysis Measure?**
* Pixel distribution across brightness levels (0–255).
* Color channel balance (Red, Green, Blue separately).
* Histogram gaps (missing brightness values) and spikes.
* Comb patterns (regular gaps suggesting heavy editing/posterization).
* Clipping at extremes (pure black 0 or pure white 255).

**How to Interpret Results:**
* **✅ Normal Patterns:** Smooth, continuous curves across the spectrum; balanced RGB channels.
* **⚠️ Suspicious Patterns:**
  * **Comb Pattern:** Regular vertical gaps indicating aggressive levels/curves adjustment or repeated re-saving.
  * **Spikes at Specific Values:** Tall, narrow peaks from contrast stretching or cloning.
  * **Clipping:** Histogram slamming into 0 or 255, losing detail.
  * **Bimodal Distributions:** Two distinct peaks suggesting splicing from different sources.

**Limitations & Best Practices:**
* High-contrast scenes (sunsets, spotlights) naturally produce unusual distributions.
* Check all three color channels (R, G, B) rather than brightness alone.
"""
    },
    "Noise": {
        "title": "👻 Noise Analysis & JPEG Ghost Detection",
        "content": """
**What is Noise Analysis?**
Digital noise is the "fingerprint" of a camera sensor – every sensor produces a unique pattern of random pixel variations. When content is added from different sources, the noise patterns will not match, revealing the forgery.
JPEG Ghost Detection looks for faint outlines that appear when an image is saved across multiple compression qualities.

**What Does It Measure?**
* Sensor noise consistency and local noise variance across different regions.
* Quality mismatches between foreground and background.
* Ghost boundaries where new elements were inserted.
* Double-compression signatures.

**How to Interpret Results:**
* **✅ Normal Patterns:** Uniform noise distribution, consistent noise in similar lighting, higher noise in shadows and lower in highlights, minimal ghosting.
* **⚠️ Suspicious Patterns:** Regions that are unnaturally smooth (denoised or AI-generated), dark areas with less noise than bright areas, and visible ghost outlines appearing at specific JPEG quality re-compressions.

**Common Artifacts Detected:**
* Splicing and composite images with mismatched grain.
* Content-aware fill creating unnaturally smooth, noise-free patches.
* AI-generated content displaying mathematically uniform noise signatures.
"""
    },
    "Quantization": {
        "title": "💾 Quantization Table Analysis",
        "content": """
**What is a Quantization Table?**
The quantization table is the "recipe" JPEG uses to compress images. It is an 8×8 grid of numbers that tells the compression algorithm how much to simplify different frequencies. Every camera brand and software editor uses unique recipes.

**What Does It Measure?**
* 8×8 quantization matrix coefficients.
* JPEG quality level estimation (0–100).
* Single vs. double compression history.
* Software signatures matching known camera or software profiles.

**How to Interpret Results:**
* **✅ Normal Patterns:** Clean quantization table matching camera manufacturer, single compression signature, and quality level appropriate for the capture device.
* **⚠️ Suspicious Patterns:**
  * **Double Compression:** Evidence of two overlapping quantization tables (e.g., Canon EOS Q=95 re-saved in Photoshop at Q=85).
  * **Software Mismatch:** Table points to Photoshop/GIMP despite claims of an unedited camera capture.
  * **Inconsistent Tables:** Different parts of the image show differing quantization tables, indicating splicing.

**Practical Tips:**
* Lower table numbers = less compression (higher quality).
* Double compression is one of the strongest technical indicators of post-processing.
"""
    },
    "CMFD": {
        "title": "🔄 Copy-Move Forgery Detection (CMFD)",
        "content": """
**What is Copy-Move Forgery Detection?**
Copy-move forgery occurs when one part of an image is copied and pasted elsewhere within the same frame to hide, duplicate, or alter content. CMFD compares 8×8 blocks and keypoint descriptors (SIFT/ORB) to find suspiciously identical regions.

**What Does CMFD Measure?**
* Block similarities across 8×8 pixel grids.
* Feature matching and spatial relationships between matching regions.
* Rotated, scaled, or skewed duplicate copies.
* DCT coefficient matching for JPEG images.

**How to Interpret Results:**
* **✅ Normal Patterns:** No matching block clusters; natural, random variations in repetitive textures (leaves, tiles, brickwork).
* **⚠️ Suspicious Patterns:** Exact duplicate block matches, large geometric clusters of matching features, and sharp boundary discontinuities around cloned objects.

**Limitations & Best Practices:**
* Natural scene repetitions (brick patterns, repeating waves) can trigger false positives.
* Look for unnatural clustering and edge blurring around the pasted elements.
"""
    },
    "PRNU": {
        "title": "📡 PRNU Analysis (Photo Response Non-Uniformity)",
        "content": """
**What is PRNU Analysis?**
PRNU is the physical fingerprint of a camera sensor. Microscopic manufacturing defects in silicon create a unique, invisible pattern in every photo taken by that sensor. It is the digital equivalent of ballistic striations on a bullet.

**What Does PRNU Measure?**
* Physical sensor manufacturing imperfections.
* Pixel-level light sensitivity variations.
* Hardware-specific noise patterns extracted via high-pass filtering (e.g., 5×5 SRM filters).
* Device matching against reference image databases.

**How to Interpret Results:**
* **✅ Normal Patterns:** Strong correlation score (> 0.010) matching a single camera sensor across the entire frame.
* **⚠️ Suspicious Patterns:** Multiple distinct PRNU patterns in different regions (composite images from different cameras), low overall correlation (< 0.005), or pasted content lacking sensor fingerprinting.

**Practical Considerations:**
* RAW images and high-resolution camera originals preserve PRNU best.
* Social media compression and aggressive downscaling severely degrade sensor fingerprint signals.
"""
    },
    "Frequency": {
        "title": "📈 Frequency Domain Analysis (FFT & DCT)",
        "content": """
**What is Frequency Domain Analysis?**
Frequency analysis examines images in frequency space rather than pixel space:
* **FFT (Fast Fourier Transform):** Breaks down an image into frequency components, measuring the balance between smooth areas and sharp detail.
* **DCT (Discrete Cosine Transform):** Analyzes 8×8 JPEG compression blocks and coefficient distributions.

**What Does It Measure?**
* High-frequency content (edges, fine detail, noise) vs. low-frequency content (smooth gradients).
* Spectral uniformity and periodic spikes caused by artificial resampling.
* Block-level quantization consistency.

**How to Interpret Results:**
* **✅ Normal Patterns:** Natural balance of high and low frequencies; smooth energy distribution without isolated spikes; authenticity score > 75.
* **⚠️ Suspicious Patterns:**
  * **Excessive High Frequencies:** Starburst or spiky halos indicating artificial over-sharpening.
  * **Unnatural Smoothness:** Abnormally low high-frequency content characteristic of AI generation.
  * **Periodic Grid Spikes:** Symmetrical frequency spikes indicating interpolation, upscaling, or GAN generation lattices.
"""
    },
    "Deepfake": {
        "title": "😄 Deepfake & Face Forensics",
        "content": """
**What is Deepfake Detection?**
Deepfake detection analyzes facial landmarks, corneal reflections, texture coherence, and biological consistency to identify AI-generated or manipulated faces.

**What Does It Measure?**
* Facial feature symmetry and biological feasibility.
* Eye reflection consistency (corneal highlight alignment).
* Skin micro-texture (presence of pores vs. plastic AI smoothness).
* Edge blending and boundary artifacts around the jawline and hairline.
* In video: blink rate, gaze tracking, and temporal flickering.

**How to Interpret Results:**
* **✅ Normal Patterns:** Natural skin texture with pores and wrinkles, matching light reflections in both pupils, biologically plausible facial proportions.
* **⚠️ Suspicious Patterns:** Unnaturally smooth, plastic-like skin texture, mismatched pupil reflections, warping around facial contours, and boundary blur along the jawline or hair.

**Best Practices:**
* Evaluate facial feature proportions against natural anatomical ranges.
* Combine facial analysis with frequency domain checks to detect generative artifacts.
"""
    },
    "Resampling": {
        "title": "🔀 Resampling & Interpolation Detection",
        "content": """
**What is Resampling Detection?**
Resampling occurs when an image or patch is scaled up, down, or rotated. Interpolation algorithms (nearest neighbor, bilinear, bicubic) create new pixels in mathematically predictable periodic patterns.

**What Does It Measure?**
* Periodic pixel interpolation derivatives (via Radon transforms / p-map analysis).
* Scaling and rotation factors applied to image patches.
* Directional interpolation artifacts (horizontal vs. vertical stretching).

**How to Interpret Results:**
* **✅ Normal Patterns:** Absence of periodic derivative artifacts; uniform resolution across all image regions.
* **⚠️ Suspicious Patterns:**
  * **Region-Specific Resampling:** Foreground object shows upscaling artifacts while the background is at native resolution.
  * **Directional Artifacts:** Horizontal or vertical periodic patterns indicating non-uniform stretching.
  * **Blocky Nearest-Neighbor Artifacts:** Visible stair-stepping on enlarged low-resolution elements.

**Limitations:**
* Subsequent JPEG compressions and blur filters can partially mask resampling patterns.
"""
    },
    "Steganography": {
        "title": "🛍️ Steganography Analysis",
        "content": """
**What is Steganography?**
Steganography is the practice of concealing secret data inside ordinary files. Unlike encryption, which scrambles data, steganography hides the very existence of the data by altering the Least Significant Bits (LSB) of pixels.

**What Does It Measure?**
* LSB plane bit-distribution across RGB channels.
* Chi-square statistical randomness tests.
* Block-based entropy deviations.

**How to Interpret Results:**
* **✅ Normal Patterns:** Natural LSB distributions (~50/50 ratio with expected variance); p-value > 0.05.
* **⚠️ Suspicious Patterns:** Uneven bit distributions, localized high-entropy regions, sharp chi-square p-value drops (< 0.05), or one color channel behaving drastically differently from the others.

**Key Caveats:**
* Heavy JPEG compression destroys LSB payloads.
* This tool assesses statistical likelihood of hidden payloads; extracting the underlying message requires the corresponding cryptographic key and extraction algorithm.
"""
    },
    "Hash": {
        "title": "🔑 Cryptographic & Perceptual Hash Verification",
        "content": """
**What is Hash Verification?**
Hash verification creates unique digital signatures to evaluate file integrity:
* **Cryptographic Hash (SHA-256):** Produces a 64-character hexadecimal digest. Modifying even a single pixel completely alters the output.
* **Perceptual Hash (pHash, dHash, aHash):** Generates structural fingerprints resilient to minor resizing or compression.

**What Does It Measure?**
* **SHA-256:** Byte-for-byte exact file integrity.
* **Hamming Distance:** Bit difference between perceptual hashes:
  * 0–5 bits: Nearly identical image (minor compression/resize).
  * 6–10 bits: Moderate edits or slight cropping.
  * 11–15 bits: Significant structural alteration.
  * 16+ bits: Substantially different image.

**Best Practices:**
* Use SHA-256 for legal chain of custody and bitstream verification.
* Use perceptual hashes to match resized, format-converted, or slightly compressed variants of registered evidence.
"""
    }
}

# ------------------------------------------------------------
# 5. Animated Sidebar Controls
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

    # Technique Descriptions Section
    st.divider()
    with st.expander("📚 Technique Descriptions", expanded=False):
        st.caption("Learn about each forensic analysis method")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🕵️ ELA", use_container_width=True):
                st.session_state["selected_tech"] = "ELA"
            if st.button("📊 Histogr...", use_container_width=True):
                st.session_state["selected_tech"] = "Histogram"
            if st.button("💾 Quanti...", use_container_width=True):
                st.session_state["selected_tech"] = "Quantization"
            if st.button("📡 PRNU", use_container_width=True):
                st.session_state["selected_tech"] = "PRNU"
            if st.button("😄 Deepfake", use_container_width=True):
                st.session_state["selected_tech"] = "Deepfake"
            if st.button("🛍️ Stegan...", use_container_width=True):
                st.session_state["selected_tech"] = "Steganography"

        with col_b:
            if st.button("📋 Metadata", use_container_width=True):
                st.session_state["selected_tech"] = "Metadata"
            if st.button("👻 Noise/...", use_container_width=True):
                st.session_state["selected_tech"] = "Noise"
            if st.button("🔄 CMFD", use_container_width=True):
                st.session_state["selected_tech"] = "CMFD"
            if st.button("📈 Freque...", use_container_width=True):
                st.session_state["selected_tech"] = "Frequency"
            if st.button("🔀 Resam...", use_container_width=True):
                st.session_state["selected_tech"] = "Resampling"
            if st.button("🔑 Hash V...", use_container_width=True):
                st.session_state["selected_tech"] = "Hash"

        if st.session_state["selected_tech"]:
            active_info = TECHNIQUE_DATA[st.session_state["selected_tech"]]
            st.markdown(f"""
            <div class="technique-modal-box">
                <div style="font-weight:700; color:#38bdf8; font-size:0.9rem; margin-bottom:6px;">{active_info['title']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(active_info["content"])
            if st.button("✖ Close Description", use_container_width=True):
                st.session_state["selected_tech"] = None
                st.rerun()

    if len(st.session_state["forensic_history"]) > 0:
        st.divider()
        st.caption(f"{len(st.session_state['forensic_history'])} Logged Session Case(s)")
        if st.button("🗑️ Clear History Log"):
            st.session_state["forensic_history"] = []
            st.session_state["last_analyzed_name"] = None
            st.rerun()

# ------------------------------------------------------------
# 6. Main Terminal Execution & Detection Animation
# ------------------------------------------------------------
st.title("🔬 Forensic Inspection Terminal")
st.write("Simultaneous 8-stage image decomposition with animated detection progression and compliance PDF reporting.")

main_tab, history_tab = st.tabs(["⚡ Live Multi-Spectral Inspector", "📜 Session Audit History"])

with main_tab:
    if selected_img is not None:
        img_np = np.array(selected_img)
        orig_h, orig_w, _ = img_np.shape

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

        # Session Logging
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

        # PDF Download Section
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
# 7. Session Audit History Tab
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
