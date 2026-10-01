"""Preprocess + stratified split manifest for accurate training.

Checks: corrupt/small/dup removal (see collect --verify), min-per-class, stratified
train/val/test split saved to splits.json so training and evaluation use identical partitions.

Usage: python preprocess.py --data data/unified --out data/unified --val 0.15 --test 0.15 --min-per-class 30 --seed 42
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from sklearn.model_selection import StratifiedShuffleSplit

VALID_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--val", type=float, default=0.15)
    p.add_argument("--test", type=float, default=0.15)
    p.add_argument("--min-per-class", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    root = Path(args.data)
    items = []  # (path, class)
    for cls in sorted(root.iterdir()):
        if not cls.is_dir():
            continue
        for img in cls.iterdir():
            if img.is_file() and img.suffix.lower() in VALID_EXT:
                items.append((str(img), cls.name))

    cnt = Counter(c for _, c in items)
    print(f"classes={len(cnt)} images={len(items)}")
    small = {k: v for k, v in cnt.items() if v < args.min_per_class}
    if small:
        print(f"WARNING: dropping {len(small)} classes below min-per-class={args.min_per_class}: {small}")
        items = [(pt, c) for pt, c in items if cnt[c] >= args.min_per_class]
    if len({c for _, c in items}) < 2:
        raise SystemExit("Need >=2 classes with enough images. Collect more data first (see DATA_SOURCES.md).")

    import numpy as np

    X = np.arange(len(items))
    y = np.array([c for _, c in items])
    s1 = StratifiedShuffleSplit(n_splits=1, test_size=args.test, random_state=args.seed)
    tr_val_idx, te_idx = next(s1.split(X, y))
    s2 = StratifiedShuffleSplit(n_splits=1, test_size=args.val / (1 - args.test), random_state=args.seed)
    tr_idx_rel, va_idx_rel = next(s2.split(tr_val_idx, y[tr_val_idx]))
    tr_idx, va_idx = tr_val_idx[tr_idx_rel], tr_val_idx[va_idx_rel]

    splits = {
        "train": [items[i] for i in tr_idx],
        "val": [items[i] for i in va_idx],
        "test": [items[i] for i in te_idx],
        "seed": args.seed,
    }
    out = Path(args.out or args.data)
    summary = {k: {"n": len(v), "classes": dict(Counter(c for _, c in v))}
               for k, v in splits.items() if isinstance(v, list)}
    summary["seed"] = args.seed
    (out / "splits.json").write_text(json.dumps(summary, indent=2))
    # Save full index lists for reproducible training
    import pickle
    with open(out / "splits_index.pkl", "wb") as f:
        pickle.dump({k: splits[k] for k in ["train", "val", "test"]}, f)
    print(f"train={len(tr_idx)} val={len(va_idx)} test={len(te_idx)} -> {out/'splits.json'}")


if __name__ == "__main__":
    main()
