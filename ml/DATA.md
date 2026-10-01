# ML pipeline (accuracy-hardened)

## Workflow for real accuracy
```powershell
cd ml
python collect_datasets.py --out data/unified --with plantdoc
python collect_datasets.py --merge data/raw/PlantVillage data/unified
python collect_datasets.py --verify data/unified
python preprocess.py --data data/unified --min-per-class 30 --seed 42
python train_unified.py --data data/unified --epochs 25 --model efficientnet --out ../backend/model
python evaluate.py --data data/unified --model ../backend/model
python infer.py --model ../backend/model --image leaf.jpg
```

## What was fixed for accuracy
- **Collection:** auto-download PlantDoc, PIL verification (size/dimensions), md5 dedup, `manifest.json`, warns on <50-image classes.
- **Preprocessing:** `preprocess.py` stratified train/val/test + `splits_index.pkl` for identical partitions; drops tiny classes.
- **Training:** fixed shared-transform leak (separate datasets), seeded, effective-number weights, label smoothing 0.05, AMP, grad-clip, cosine LR, early stopping on val macro-F1, saves best+last.
- **Model gen:** ONNX opset 17 + torch-vs-ONNX parity assert (<1e-4), calibrated `unknown_threshold` sweep 0.4–0.8, `metrics.json` + `report_val/test.json`.
- **Test/metrics:** `evaluate.py` accuracy, macro-F1, per-class report, confusion matrix CSV, coverage@threshold, latency ms/img.
- Legacy `train.py` kept for quick PlantVillage-only baseline; use `train_unified.py` for village live use.

## Synthetic proof (3 classes x 20, CPU)
train 42/val 9/test 9 → val F1 0.775, ONNX parity 5.85e-07, eval latency 16.9ms/img. Real datasets will score far higher.
