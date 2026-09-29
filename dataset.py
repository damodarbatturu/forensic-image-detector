import os
import cv2
import torch
from torch.utils.data import Dataset

class ForgeryDataset(Dataset):
    def __init__(self, authentic_dir, forged_dir, mask_dir, img_size=(256, 256)):
        self.img_size = img_size
        self.samples = []

        if os.path.exists(authentic_dir):
            for fname in os.listdir(authentic_dir):
                if fname.lower().endswith(('.jpg', '.png', '.tif')):
                    self.samples.append((os.path.join(authentic_dir, fname), None, 0.0))

        if os.path.exists(forged_dir):
            for fname in os.listdir(forged_dir):
                if fname.lower().endswith(('.jpg', '.png', '.tif')):
                    mask_name = os.path.splitext(fname)[0] + ".png"
                    mask_path = os.path.join(mask_dir, mask_name)
                    self.samples.append((os.path.join(forged_dir, fname), mask_path, 1.0))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, mask_path, label = self.samples[idx]
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, self.img_size)
        img_tensor = torch.tensor(img, dtype=torch.float32).permute(2, 0, 1) / 255.0

        if mask_path and os.path.exists(mask_path):
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            mask = cv2.resize(mask, self.img_size)
            mask = (mask > 128).astype("float32")
        else:
            mask = torch.zeros(self.img_size, dtype=torch.float32).numpy()

        mask_tensor = torch.tensor(mask, dtype=torch.float32).unsqueeze(0)
        label_tensor = torch.tensor([label], dtype=torch.float32)

        return img_tensor, mask_tensor, label_tensor
