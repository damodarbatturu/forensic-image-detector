import torch
import torch.nn as nn
import torchvision.models as models

class SRMConv2D(nn.Module):
    def __init__(self):
        super().__init__()
        q = [
            [[0, 0, 0, 0, 0], [0, -1, 2, -1, 0], [0, 2, -4, 2, 0], [0, -1, 2, -1, 0], [0, 0, 0, 0, 0]],
            [[-1, 2, -2, 2, -1], [2, -6, 8, -6, 2], [-2, 8, -12, 8, -2], [2, -6, 8, -6, 2], [-1, 2, -2, 2, -1]],
            [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 1, -2, 1, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
        ]
        kernel = torch.tensor(q, dtype=torch.float32).unsqueeze(1).repeat(1, 3, 1, 1) / 4.0
        self.conv = nn.Conv2d(3, 3, kernel_size=5, stride=1, padding=2, bias=False)
        self.conv.weight = nn.Parameter(kernel, requires_grad=False)

    def forward(self, x):
        return self.conv(x)

class DualStreamForgeryDetector(nn.Module):
    def __init__(self):
        super().__init__()
        self.srm = SRMConv2D()

        # RGB Stream
        base_rgb = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.rgb_encoder = nn.Sequential(*list(base_rgb.children())[:-2])

        # Forensic SRM Noise Stream
        base_noise = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.noise_encoder = nn.Sequential(*list(base_noise.children())[:-2])

        # Feature Fusion
        self.fusion = nn.Sequential(
            nn.Conv2d(1024, 512, kernel_size=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True)
        )

        # Classifier Head (Authentic vs Forged)
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(128, 1)
        )

        # Pixel Localization Decoder Head
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(512, 256, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(32, 1, kernel_size=4, stride=2, padding=1)
        )

    def forward(self, x):
        rgb_feat = self.rgb_encoder(x)
        noise_feat = self.noise_encoder(self.srm(x))
        fused = self.fusion(torch.cat([rgb_feat, noise_feat], dim=1))

        cls_out = self.classifier(self.gap(fused).flatten(1))
        mask_out = self.decoder(fused)
        return cls_out, mask_out
