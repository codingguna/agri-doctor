"""Accurate unified training: plant + disease + pest, field-robust for village live images.

Fixes vs v1: stratified seeded splits, separate train/val datasets (no shared-transform
leak), corrupt filtering, effective-number class weights, label smoothing, AMP, early
stopping, per-class F1, ONNX parity check, unknown-threshold calibration.

Usage:
  python preprocess.py --data data/unified
  python train_unified.py --data data/unified --epochs 25 --model efficientnet --out ../backend/model
Layout: data/unified/<Plant>___<Condition>/*.jpg
"""
import argparse
import json
import os
import pickle
import random
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


def seed_all(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


FIELD_TRAIN = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomResizedCrop(224, scale=(0.6, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(25),
    transforms.ColorJitter(brightness=0.35, contrast=0.35, saturation=0.25, hue=0.04),
    transforms.RandomGrayscale(p=0.03),
    transforms.GaussianBlur(3, sigma=(0.1, 1.5)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
FIELD_VAL = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def build_model(name: str, num_classes: int):
    name = name.lower()
    if name == "efficientnet":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, num_classes)
    elif name == "mobilenetv2":
        m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.last_channel, num_classes)
    else:
        m = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, num_classes)
    return m


def load_split_lists(data: Path):
    """Use splits_index.pkl when present (from preprocess.py), else stratified fallback."""
    pkl = data / "splits_index.pkl"
    if pkl.exists():
        with open(pkl, "rb") as f:
            d = pickle.load(f)
        return d["train"], d["val"], d["test"]
    return None


class ListDataset(torch.utils.data.Dataset):
    def __init__(self, items, classes, transform):
        self.items = items
        self.cls_to_idx = {c: i for i, c in enumerate(classes)}
        self.transform = transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        from PIL import Image as PILImage

        path, cls = self.items[i]
        with PILImage.open(path) as im:
            img = im.convert("RGB")
            if self.transform:
                img = self.transform(img)
        return img, self.cls_to_idx[cls]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--model", default="efficientnet", choices=["mobilenetv3", "efficientnet", "mobilenetv2"])
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--patience", type=int, default=6)
    p.add_argument("--out", default="../backend/model")
    args = p.parse_args()

    seed_all(args.seed)
    data = Path(args.data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Class list from folder names (stable sorted order)
    probe = datasets.ImageFolder(str(data))
    classes = probe.classes
    print(f"classes={len(classes)}")

    split = load_split_lists(data)
    if split:
        tr_items, va_items, te_items = split
        print(f"using splits_index.pkl: train={len(tr_items)} val={len(va_items)} test={len(te_items)}")
    else:
        # Stratified fallback with separate dataset objects (no shared-transform bug)
        from sklearn.model_selection import StratifiedShuffleSplit
        all_items = [(str(p), c) for p, c in zip(probe.samples, [classes[t] for _, t in probe.samples])]
        y = np.array([c for _, c in all_items])
        idx = np.arange(len(all_items))
        s1 = StratifiedShuffleSplit(n_splits=1, test_size=0.15, random_state=args.seed)
        tr_va, te = next(s1.split(idx, y))
        s2 = StratifiedShuffleSplit(n_splits=1, test_size=0.176, random_state=args.seed)
        tr_r, va_r = next(s2.split(tr_va, y[tr_va]))
        tr_items = [all_items[i] for i in tr_va[tr_r]]
        va_items = [all_items[i] for i in tr_va[va_r]]
        te_items = [all_items[i] for i in te]

    train_ds = ListDataset(tr_items, classes, FIELD_TRAIN)
    val_ds = ListDataset(va_items, classes, FIELD_VAL)
    test_ds = ListDataset(te_items, classes, FIELD_VAL)
    # num_workers=0 for Windows spawn safety + village laptops; set 2 on Linux server
    nw = 0 if os.name == "nt" else 2
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=nw)
    val_loader = DataLoader(val_ds, batch_size=args.batch, num_workers=nw)
    test_loader = DataLoader(test_ds, batch_size=args.batch, num_workers=nw)

    # Effective-number class weights (Cui et al.) — gentler than 1/count for rare pests
    from collections import Counter
    cnt = Counter(c for _, c in tr_items)
    beta = 0.999
    eff = {c: (1 - beta ** max(n, 1)) / (1 - beta) for c, n in cnt.items()}
    w = torch.tensor([sum(eff.values()) / len(eff) / eff[c] for c in classes], dtype=torch.float)
    print("class balance:", {c: cnt.get(c, 0) for c in classes[:5]}, "...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(args.model, len(classes)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    loss_fn = nn.CrossEntropyLoss(weight=w.to(device), label_smoothing=0.05)
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")

    best_f1, bad, best_ep = 0.0, 0, 0
    for epoch in range(args.epochs):
        model.train()
        tot = cor = ls = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            with torch.amp.autocast("cuda", enabled=device == "cuda"):
                o = model(x)
                l = loss_fn(o, y)
            scaler.scale(l).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            scaler.step(opt)
            scaler.update()
            ls += l.item() * len(x)
            tot += len(x)
            cor += (o.argmax(1) == y).sum().item()
        sched.step()

        # Val macro-F1 (better than accuracy for imbalanced pests)
        from sklearn.metrics import f1_score
        model.eval()
        yp, yt = [], []
        with torch.no_grad():
            for x, y in val_loader:
                yp += model(x.to(device)).argmax(1).cpu().tolist()
                yt += y.tolist()
        f1 = f1_score(yt, yp, average="macro", zero_division=0)
        acc = sum(a == b for a, b in zip(yp, yt)) / max(len(yt), 1)
        print(f"epoch {epoch+1}/{args.epochs} loss={ls/max(tot,1):.4f} train={cor/max(tot,1):.3f} val_acc={acc:.3f} val_F1={f1:.3f}")
        if f1 > best_f1:
            best_f1, best_ep, bad = f1, epoch, 0
            torch.save(model.state_dict(), out / "model.pt")
        else:
            bad += 1
            if bad >= args.patience:
                print(f"early stop at epoch {epoch+1} (best F1={best_f1:.3f} ep {best_ep+1})")
                break
    torch.save(model.state_dict(), out / "last.pt")

    # Test report + threshold calibration on val
    model.load_state_dict(torch.load(out / "model.pt", map_location=device))
    model.eval()
    from sklearn.metrics import classification_report, f1_score
    for name, loader in (("val", val_loader), ("test", test_loader)):
        yp, yt, conf = [], [], []
        with torch.no_grad():
            for x, y in loader:
                o = model(x.to(device))
                pr = torch.softmax(o, 1)
                cf, prd = pr.max(1)
                yp += prd.cpu().tolist()
                yt += y.tolist()
                conf += cf.cpu().tolist()
        rep = classification_report(yt, yp, target_names=classes, zero_division=0, output_dict=True)
        print(f"[{name}] acc={rep['accuracy']:.3f} macroF1={rep['macro avg']['f1-score']:.3f}")
        with open(out / f"report_{name}.json", "w") as f:
            json.dump(rep, f, indent=2)
        if name == "val":
            # Calibrate unknown threshold: sweep 0.4..0.8, pick best (acc on kept + 0.5*coverage)
            best_t, best_s = 0.55, -1.0
            for thr in [0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]:
                kept = [(a == b) for a, b, c in zip(yp, yt, conf) if c >= thr]
                cov = len(kept) / max(len(yp), 1)
                s = (sum(kept) / max(len(kept), 1) if kept else 0) * 0.7 + cov * 0.3
                if s > best_s:
                    best_s, best_t = s, thr
            print(f"calibrated unknown_threshold={best_t}")
            with open(out / "labels.json", "w") as f:
                json.dump(classes, f, indent=2)
            import shutil
            tax = Path(__file__).parent / "unified_taxonomy.json"
            if tax.exists():
                shutil.copy(tax, out / "taxonomy.json")
            with open(out / "metrics.json", "w") as f:
                json.dump({"best_val_F1": best_f1, "best_epoch": best_ep + 1, "classes": len(classes),
                           "model": args.model, "seed": args.seed, "unknown_threshold": best_t,
                           "test_report": f"report_test.json"}, f, indent=2)

    # ONNX export (opset 17) + torch-vs-onnx parity check
    model.eval()
    dummy = torch.randn(1, 3, 224, 224).to(device)
    torch.onnx.export(model, dummy, out / "model.onnx", input_names=["input"], output_names=["logits"],
                      dynamic_axes={"input": {0: "batch"}}, opset_version=17)
    sess = ort.InferenceSession(str(out / "model.onnx"))
    arr = dummy.cpu().numpy()
    with torch.no_grad():
        t_out = model(dummy).cpu().numpy()
    o_out = sess.run(None, {"input": arr})[0]
    diff = float(np.abs(t_out - o_out).max())
    print(f"onnx parity max-diff={diff:.2e} (must be <1e-4)")
    assert diff < 1e-4, "ONNX export mismatch — check opset/torch versions"
    print(f"saved to {out}")


if __name__ == "__main__":
    main()
