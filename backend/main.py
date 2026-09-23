"""AgriDoctor backend — FastAPI serving mock + real inference."""
import io
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

load_dotenv()

BASE = Path(__file__).parent
ADVISORY_PATH = BASE / "advisory_data.json"
MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE / "model"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

with open(ADVISORY_PATH, encoding="utf-8") as f:
    ADVISORY_DB = json.load(f)

LABELS = [d["label"] for d in ADVISORY_DB]

# Try to load a real model if present (model/model.onnx or model.pt).
INFERENCE_MODE = "mock"
_ort_session = None
try:
    onnx_path = MODEL_DIR / "model.onnx"
    labels_path = MODEL_DIR / "labels.json"
    if onnx_path.exists():
        import onnxruntime as ort  # type: ignore

        _ort_session = ort.InferenceSession(str(onnx_path))
        if labels_path.exists():
            with open(labels_path, encoding="utf-8") as f:
                LABELS = json.load(f)
        INFERENCE_MODE = "real-onnx"
except Exception:
    INFERENCE_MODE = "mock"

app = FastAPI(title="AgriDoctor API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def mock_predict(image: Image.Image):
    """Deterministic stub so UI works before training. Uses image size hash."""
    w, h = image.size
    idx = (w * h) % len(ADVISORY_DB)
    ordered = ADVISORY_DB[idx:] + ADVISORY_DB[:idx]
    # Fake confidences that sum ~1.0
    confs = [0.72, 0.18, 0.07]
    return [
        {"label": ordered[i]["label"], "confidence": confs[i]}
        for i in range(min(3, len(ordered)))
    ]


@app.get("/health")
def health():
    return {"status": "ok", "mode": INFERENCE_MODE, "labels": len(LABELS)}


@app.get("/diseases")
def list_diseases():
    return ADVISORY_DB


@app.get("/diseases/{label}")
def get_disease(label: str):
    for d in ADVISORY_DB:
        if d["label"].lower() == label.lower():
            return d
    raise HTTPException(status_code=404, detail="Disease not found")


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload an image file")
    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 8MB)")
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")

    t0 = time.perf_counter()
    if _ort_session is not None:
        # Real ONNX inference path — preprocess to 224x224, normalize ImageNet.
        import numpy as np

        img = image.resize((224, 224))
        arr = (np.asarray(img).astype("float32") / 255.0 - np.array([0.485, 0.456, 0.406], dtype="float32")) / np.array(
            [0.229, 0.224, 0.225], dtype="float32"
        )
        arr = np.transpose(arr, (2, 0, 1))[None, :]
        out = _ort_session.run(None, {_ort_session.get_inputs()[0].name: arr})[0][0]
        exp = np.exp(out - out.max())
        probs = exp / exp.sum()
        top = probs.argsort()[::-1][:3]
        predictions = [
            {"label": LABELS[i], "confidence": round(float(probs[i]), 4)} for i in top
        ]
    else:
        predictions = mock_predict(image)
    ms = round((time.perf_counter() - t0) * 1000, 1)

    top_label = predictions[0]["label"]
    advisory = next((d for d in ADVISORY_DB if d["label"] == top_label), None)
    return {
        "predictions": predictions,
        "advisory": advisory,
        "inference_ms": ms,
        "mode": INFERENCE_MODE,
    }
