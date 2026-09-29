import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from dataset import ForgeryDataset
from model import DualStreamForgeryDetector

def dice_loss(pred, target, smooth=1e-5):
    pred = torch.sigmoid(pred)
    intersection = (pred * target).sum(dim=(2, 3))
    union = pred.sum(dim=(2, 3)) + target.sum(dim=(2, 3))
    return 1 - ((2.0 * intersection + smooth) / (union + smooth)).mean()

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")

    dataset = ForgeryDataset("data/authentic", "data/forged", "data/masks")
    if len(dataset) == 0:
        print("Error: No images found. Ensure data/authentic and data/forged contain images.")
        return

    loader = DataLoader(dataset, batch_size=8, shuffle=True)
    model = DualStreamForgeryDetector().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-3)
    bce = nn.BCEWithLogitsLoss()

    epochs = 10
    print(f"Starting training on {len(dataset)} images for {epochs} epochs...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0

        for images, masks, labels in loader:
            images, masks, labels = images.to(device), masks.to(device), labels.to(device)
            optimizer.zero_grad()

            cls_pred, mask_pred = model(images)
            l_cls = bce(cls_pred, labels)
            l_mask = bce(mask_pred, masks) + dice_loss(mask_pred, masks)
            loss = l_cls + (0.5 * l_mask)

            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        print(f"Epoch [{epoch+1}/{epochs}] - Loss: {total_loss / len(loader):.4f}")

    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/srm_dual_stream.pth")
    print("Training finished! Saved weights to models/srm_dual_stream.pth")

if __name__ == "__main__":
    train()
