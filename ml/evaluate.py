"""Evaluate a trained model dir on held-out test split.

Usage: python evaluate.py --data data/unified --model ../backend/model
Reads splits_index.pkl for identical test partition, runs ONNX, writes confusion matrix + report.
"""
import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image


def load_items(data: Path):
    with open(data / "splits_index.pkl", "rb") as f:
        return pickle.load(f)["test"]


def preprocess(p: str):
    img = Image.open(p).convert("RGB").resize((256, 256)).crop((16, 16, 240, 240)).resize((224, 224))
    arr = (np.asarray(img).astype("float32") / 255.0 - np.array([0.485, 0.456, 0.406], dtype="float32")) / np.array(
        [0.229, 0.224, 0.225], dtype="float32")
    return np.transpose(arr, (2, 0, 1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    data, mdir = Path(args.data), Path(args.model)
    labels = json.loads((mdir / "labels.json").read_text())
    metrics = json.loads((mdir / "metrics.json").read_text()) if (mdir / "metrics.json").exists() else {}
    thr = float(metrics.get("unknown_threshold", 0.55))
    sess = ort.InferenceSession(str(mdir / "model.onnx"))
    idx = {c: i for i, c in enumerate(labels)}

    items = load_items(data)
    if args.limit:
        items = items[: args.limit]
    yp, yt, conf = [], [], []
    import time
    t0 = time.perf_counter()
    for path, cls in items:
        x = preprocess(path)[None, :]
        out = sess.run(None, {"input": x})[0][0]
        e = np.exp(out - out.max())
        pr = e / e.sum()
        i = int(pr.argmax())
        yp.append(i)
        yt.append(idx.get(cls, -1))
        conf.append(float(pr[i]))
    dt = (time.perf_counter() - t0) * 1000 / max(len(items), 1)

    from sklearn.metrics import classification_report, confusion_matrix
    mask = [t_ >= 0 for t_ in yt]
    yp_f = [yp[i] for i, m in enumerate(mask) if m]
    yt_f = [yt[i] for i, m in enumerate(mask) if m]
    rep = classification_report(yt_f, yp_f, target_names=[labels[i] for i in sorted(set(yt_f))],
                                zero_division=0, output_dict=True)
    cm = confusion_matrix(yt_f, yp_f).tolist()
    kept = sum(c >= thr for c in conf)
    print(f"n={len(items)} acc={rep['accuracy']:.3f} macroF1={rep['macro avg']['f1-score']:.3f} "
          f"coverage@{thr}={kept/len(items):.2f} latency={dt:.1f}ms/img")
    (mdir / "eval_report.json").write_text(json.dumps(
        {"n": len(items), "accuracy": rep["accuracy"], "macroF1": rep["macro avg"]["f1-score"],
         "coverage_at_thr": kept / max(len(items), 1), "threshold": thr,
         "latency_ms": round(dt, 2), "per_class": rep}, indent=2))
    import csv
    with open(mdir / "confusion_matrix.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["true/pred"] + labels)
        for i, row in enumerate(cm):
            w.writerow([labels[i]] + row)
    print(f"wrote eval_report.json + confusion_matrix.csv to {mdir}")


if __name__ == "__main__":
    main()
