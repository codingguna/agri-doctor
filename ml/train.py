"""Train MobileNetV2 on PlantVillage-style folder dataset and export ONNX."""
import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True, help="data/plantvillage root with <class>/*.jpg")
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--out", default="../backend/model")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tfm_train = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomResizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    tfm_val = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    full = datasets.ImageFolder(args.data, transform=tfm_train)
    n_val = max(1, int(len(full) * 0.15))
    n_train = len(full) - n_val
    train_ds, val_ds = torch.utils.data.random_split(full, [n_train, n_val])
    val_ds.dataset.transform = tfm_val  # type: ignore

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=args.batch, num_workers=2)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.last_channel, len(full.classes))
    model.to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        model.train()
        total, correct, loss_sum = 0, 0, 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            out_logits = model(x)
            loss = loss_fn(out_logits, y)
            loss.backward()
            opt.step()
            loss_sum += loss.item() * len(x)
            total += len(x)
            correct += (out_logits.argmax(1) == y).sum().item()
        model.eval()
        v_correct, v_total = 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                v_correct += (model(x).argmax(1) == y).sum().item()
                v_total += len(x)
        print(f"epoch {epoch+1}/{args.epochs} loss={loss_sum/max(total,1):.4f} "
              f"train_acc={correct/max(total,1):.3f} val_acc={v_correct/max(v_total,1):.3f}")

    torch.save(model.state_dict(), out / "model.pt")
    with open(out / "labels.json", "w", encoding="utf-8") as f:
        json.dump(full.classes, f, indent=2)

    # Export ONNX for FastAPI runtime (no torch needed in prod)
    model.eval()
    dummy = torch.randn(1, 3, 224, 224).to(device)
    torch.onnx.export(model, dummy, out / "model.onnx", input_names=["input"],
                      output_names=["logits"], dynamic_axes={"input": {0: "batch"}})
    print(f"saved to {out}")


if __name__ == "__main__":
    main()
