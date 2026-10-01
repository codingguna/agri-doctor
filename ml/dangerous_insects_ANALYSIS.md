# Dangerous Insects Dataset — analysis (tarundalal/dangerous-insects-dataset)

Verified via Kaggle API 2026-09-24 (no MCP/browser needed — both unavailable in this runtime).

## Facts
- Title: Dangerous Farm Insects Dataset, creator Tarun R Jain, 474,013,398 bytes (~474MB)
- License: CC0 Public Domain — free for personal + commercial use, best license in registry
- Content: 15 harmful farm-insect classes, multiple high-quality images per class (colors/patterns)
- Purpose (author): pest ID, crop protection, education, ML/CV training
- Usability: rated farm-insect task; transfer-learning notebooks exist (e.g. MobileNetV2/Xception)

## Fit for AgriDoctor (ultimate pest detector)
- Directly replaces dead `computervision/farm-insects` (403) entry.
- Maps to unified labels as `Insect/<Name>` for pure-insect photos, or `<Crop>___<Pest>` when crop known.
  Start: Aphids, Bollworm, Armyworm, Whitefly, Thrips + 10 more after listing folders.
- 474MB is phone-friendly vs IP102 3.1GB — train dangerous-insects first, IP102 second.

## Download (requires one-time Kaggle login — no anonymous download)
1. Kaggle > avatar > Account > Create New Token → saves `kaggle.json`
2. Move to `C:\Users\<you>\.kaggle\kaggle.json`
3. Run:
```powershell
cd agri-doctor/ml
python -m kaggle datasets download -d tarundalal/dangerous-insects-dataset -p data/raw --unzip
python collect_datasets.py --merge data/raw/dangerous-insects-dataset data/unified
python collect_datasets.py --verify data/unified
python preprocess.py --data data/unified --min-per-class 30
```
4. Class names = subfolder names after unzip. If folders are flat, run `--merge` then rename to `Insect/<Name>`.

## Caveats
- File list API returns [] without auth, so exact 15 names confirmed only after download.
  Expect common farm pests (aphid/bollworm/armyworm/whitefly/thrips/beetle/weevil/caterpillar).
- Field photos vary in background — keep unknown threshold 0.55 until val calibration.
- CC0 needs no attribution, but credit author in README anyway.
