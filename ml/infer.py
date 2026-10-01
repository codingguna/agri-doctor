"""Live-image inference CLI with plant/category + unknown gate.

Usage:
  python infer.py --model ../backend/model --image leaf.jpg [--topk 3]
  python infer.py --model ../backend/model --dir field_photos/
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def load_session(mdir: Path):
    import onnxruntime as ort

    sess = ort.InferenceSession(str(mdir / "model.onnx"))
    labels = json.loads((mdir / "labels.json").read_text())
    thr = 0.55
    if (mdir / "metrics.json").exists():
        thr = float(json.loads((mdir / "metrics.json").read_text()).get("unknown_threshold", 0.55))
    return sess, labels, thr


def predict(sess, labels, thr, path: Path, topk: int):
    img = Image.open(path).convert("RGB").resize((224, 224))
    arr = (np.asarray(img).astype("float32") / 255.0 - np.array([0.485, 0.456, 0.406], dtype="float32")) / np.array(
        [0.229, 0.224, 0.225], dtype="float32")
    arr = np.transpose(arr, (2, 0, 1))[None, :]
    out = sess.run(None, {sess.get_inputs()[0].name: arr})[0][0]
    e = np.exp(out - out.max())
    pr = e / e.sum()
    top = pr.argsort()[::-1][:topk]
    best, conf = labels[int(top[0])], float(pr[int(top[0])])
    plant = best.split("___")[0] if "___" in best else "Unknown"
    unknown = conf < thr
    return {"file": str(path), "plant": plant, "label": best, "confidence": round(conf, 4),
            "unknown": unknown, "topk": [(labels[int(i)], round(float(pr[int(i)]), 4)) for i in top]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--image", default=None)
    p.add_argument("--dir", default=None)
    p.add_argument("--topk", type=int, default=3)
    args = p.parse_args()

    sess, labels, thr = load_session(Path(args.model))
    paths = [Path(args.image)] if args.image else sorted(Path(args.dir).glob("*.*")) if args.dir else []
    for path in paths:
        if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        r = predict(sess, labels, thr, path, args.topk)
        if r["unknown"]:
            print(f"{r['file']}: UNKNOWN (top {r['label']} {r['confidence']}) — retake in daylight, fill frame")
        else:
            print(f"{r['file']}: {r['plant']} | {r['label']} {r['confidence']} | {r['topk']}")


if __name__ == "__main__":
    main()
