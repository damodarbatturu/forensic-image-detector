import os
import shutil
import kagglehub

print("Downloading CASIA 2.0 / Defacto sample from Kaggle...")
path = kagglehub.dataset_download("sophatvathana/casia-dataset")

print(f"Dataset downloaded to cache at: {path}")

dest_auth = "data/authentic"
dest_forged = "data/forged"
dest_masks = "data/masks"

os.makedirs(dest_auth, exist_ok=True)
os.makedirs(dest_forged, exist_ok=True)
os.makedirs(dest_masks, exist_ok=True)

sample_limit = 200

for root, _, files in os.walk(path):
    for f in files:
        src_path = os.path.join(root, f)
        if "Au" in root and f.lower().endswith(('.jpg', '.png')) and len(os.listdir(dest_auth)) < sample_limit:
            shutil.copy(src_path, os.path.join(dest_auth, f))
        elif "Tp" in root and f.lower().endswith(('.jpg', '.png')) and len(os.listdir(dest_forged)) < sample_limit:
            shutil.copy(src_path, os.path.join(dest_forged, f))

print(f"Setup complete! Authentic: {len(os.listdir(dest_auth))}, Forged: {len(os.listdir(dest_forged))}")
