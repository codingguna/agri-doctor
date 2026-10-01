"""Robust collector: download + verify + clean + merge into data/unified/<Plant>___<Condition>/.

Examples:
  python collect_datasets.py --out data/unified --with plantdoc
  python collect_datasets.py --merge data/raw/PlantVillage data/unified
  python collect_datasets.py --verify data/unified
"""
import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image

TARGETS = {
    "plantdoc": "https://github.com/pratikkayal/PlantDoc-Dataset/archive/refs/heads/master.zip",
    "dangerous_insects": "kaggle:tarundalal/dangerous-insects-dataset (474MB, CC0, 15 classes)",
}
VALID_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MIN_SIZE = 8000  # bytes — below this is usually corrupt/thumbnail
MIN_DIM = 64


def is_good_image(p: Path) -> bool:
    try:
        if p.stat().st_size < MIN_SIZE:
            return False
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            im.convert("RGB")
            if min(im.size) < MIN_DIM:
                return False
        return True
    except Exception:
        return False


def file_hash(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    return dest


def merge_folder(src: Path, dst: Path) -> int:
    n = 0
    for cls in sorted(src.iterdir()):
        if not cls.is_dir():
            continue
        # Normalize: spaces -> _, keep Plant___Condition casing
        cname = cls.name.strip().replace(" ", "_")
        d = dst / cname
        d.mkdir(parents=True, exist_ok=True)
        for img in cls.iterdir():
            if not img.is_file() or img.suffix.lower() not in VALID_EXT:
                continue
            if not is_good_image(img):
                continue
            target = d / img.name
            if target.exists():
                # dedup by content hash
                if file_hash(img) == file_hash(target):
                    continue
                target = d / f"{img.stem}_{file_hash(img)[:8]}{img.suffix.lower()}"
            shutil.copy(img, target)
            n += 1
    return n


def verify_dataset(root: Path) -> dict:
    report = {"classes": {}, "bad_removed": 0, "total": 0}
    for cls in sorted(root.iterdir()):
        if not cls.is_dir():
            continue
        kept = 0
        for img in list(cls.iterdir()):
            if not img.is_file():
                continue
            if img.suffix.lower() not in VALID_EXT or not is_good_image(img):
                img.unlink(missing_ok=True)
                report["bad_removed"] += 1
                continue
            kept += 1
        report["classes"][cls.name] = kept
        report["total"] += kept
    # warn on tiny classes — main cause of poor accuracy
    tiny = {k: v for k, v in report["classes"].items() if v < 50}
    if tiny:
        print(f"WARNING: {len(tiny)} classes have <50 images and will generalize poorly: {tiny}")
        print("Add PlantDoc/field images or augmentation for these classes.")
    (root / "manifest.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/unified")
    p.add_argument("--with", dest="datasets", nargs="*", default=[])
    p.add_argument("--merge", nargs=2, metavar=("SRC", "DST"), default=None)
    p.add_argument("--verify", default=None)
    args = p.parse_args()

    if args.merge:
        src, dst = Path(args.merge[0]), Path(args.merge[1])
        n = merge_folder(src, dst)
        print(f"merged {n} verified images {src} -> {dst}")
        print(json.dumps(verify_dataset(dst), indent=2)[:2000])

    if args.verify:
        print(json.dumps(verify_dataset(Path(args.verify)), indent=2))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in args.datasets:
        if name == "plantdoc":
            z = Path("data/raw/plantdoc.zip")
            if not z.exists():
                download(TARGETS["plantdoc"], z)
            with zipfile.ZipFile(z) as zf:
                zf.extractall("data/raw/plantdoc_ex")
            # PlantDoc nests images under various subfolders — collect all jpgs by parent class
            print("extracted plantdoc; run --merge data/raw/plantdoc_ex data/unified after checking class folders")
        elif name == "plantvillage":
            print("PlantVillage needs Kaggle auth: python -m kaggle datasets download -d mohitsingh1804/plantvillage -p data/raw --unzip")
            print("then: python collect_datasets.py --merge data/raw/PlantVillage data/unified --verify data/unified")
        elif name == "dangerous_insects":
            print("Dangerous insects (15 classes, 474MB, CC0): python -m kaggle datasets download -d tarundalal/dangerous-insects-dataset -p data/raw --unzip")
            print("then: python collect_datasets.py --merge data/raw/dangerous-insects-dataset data/unified --verify data/unified")
            print("see ml/dangerous_insects_ANALYSIS.md; needs ~/.kaggle/kaggle.json")
        elif name == "ip102_sample":
            print("IP102 manual (75k): https://github.com/xpwu95/IP102 — map to <Crop>___<Pest>, start with 6 pests")
        elif name:
            print(f"unknown dataset: {name}")
    print(f"Unified root: {out.resolve()}  format: <Plant>___<Condition>")


if __name__ == "__main__":
    main()
