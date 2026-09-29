# 🛡️ ForensiScan Ultra — Multi-Spectral Image Forensics Platform

An advanced deep-learning and physical multi-spectral image forensic platform designed for detecting digital tampering, splicing, content removal, and generative anomalies.

## 🚀 Live Demo
Access the live deployment: **[Streamlit Web Application](https://damodarbatturu-forensic-image-detector.streamlit.app)** *(replace with your exact URL)*

---

## 🔬 Core Forensic Architecture

The suite executes simultaneous **8-stage decomposition** and **12-modality diagnostic audits**:

1. **Dual-Stream CNN Architecture:** Spatial RGB feature maps fused with 5×5 SRM (Spatial Rich Model) high-pass convolution residuals.
2. **Error Level Analysis (ELA):** Differential JPEG compression analysis at variable quality baselines.
3. **2D-FFT Power Spectrum Analysis:** Detects periodic frequency lattice spikes from interpolation and GAN generators.
4. **Boundary Discontinuity Mapping:** Blended second-order Canny edge detectors and Laplacian operators.
5. **Luminance Gradient Vectors:** Sobel direction vectors to isolate inconsistent illumination angles.
6. **Solid Silhouette Mask Synthesis:** Fused convex-hull extraction isolating tampered boundaries.
7. **Automated Audit PDF Reports:** ReportLab-generated forensic compliance documentation with telemetry and image proof strips.

---

## 🛠️ Local Installation & Setup

```bash
# Clone the repository
git clone [https://github.com/damodarbatturu/forensic-image-detector.git](https://github.com/damodarbatturu/forensic-image-detector.git)
cd forensic-image-detector

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit application
streamlit run app.py
