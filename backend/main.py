"""AgriDoctor backend — full version with SQLite history, stats, weather proxy."""
import io
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

load_dotenv()

BASE = Path(__file__).parent
ADVISORY_PATH = BASE / "advisory_data.json"
MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE / "model"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
DB_PATH = Path(os.getenv("DB_PATH", BASE / "history.db"))
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "")

with open(ADVISORY_PATH, encoding="utf-8") as f:
    ADVISORY_DB = json.load(f)

PEST_WORDS = ("bollworm", "borer", "armyworm", "aphid", "whitefly", "thrips", "mite", "beetle", "weevil", "caterpillar", "hopper", "folder", "moth")

def enrich(entry: dict) -> dict:
    e = dict(entry)
    label = e.get("label", "")
    plant = e.get("plant") or (label.split("___")[0] if "___" in label else e.get("crop", "Unknown"))
    e["plant"] = plant
    cond = e.get("condition") or e.get("disease", label.split("___")[-1].replace("_", " "))
    e["condition"] = cond
    if not e.get("category"):
        ll = (label + " " + cond).lower()
        e["category"] = "healthy" if "healthy" in ll else ("pest" if any(w in ll for w in PEST_WORDS) else "disease")
    if not e.get("village_advice"):
        e["village_advice"] = f"This looks like {plant} — {cond}. {e.get('prevention', '')}"
    return e

ADVISORY_DB = [enrich(d) for d in ADVISORY_DB]

UNKNOWN_THRESHOLD = float(os.getenv("UNKNOWN_THRESHOLD", "0.55"))

LABELS = [d["label"] for d in ADVISORY_DB]

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


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute(
        """CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        top_label TEXT NOT NULL,
        confidence REAL NOT NULL,
        all_predictions TEXT NOT NULL,
        advisory_snapshot TEXT,
        created_at TEXT NOT NULL)"""
    )
    return con


app = FastAPI(title="AgriDoctor API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryIn(BaseModel):
    top_label: str
    confidence: float
    all_predictions: list
    advisory_snapshot: dict | None = None


def mock_predict(image: Image.Image):
    w, h = image.size
    idx = (w * h) % len(ADVISORY_DB)
    ordered = ADVISORY_DB[idx:] + ADVISORY_DB[:idx]
    confs = [0.72, 0.18, 0.07]
    return [{"label": ordered[i]["label"], "confidence": confs[i]} for i in range(min(3, len(ordered)))]


def save_record(top_label: str, confidence: float, preds: list, advisory: dict | None) -> int:
    con = get_db()
    cur = con.execute(
        "INSERT INTO predictions (top_label, confidence, all_predictions, advisory_snapshot, created_at) VALUES (?,?,?,?,?)",
        (top_label, confidence, json.dumps(preds), json.dumps(advisory) if advisory else None,
         datetime.now(timezone.utc).isoformat()),
    )
    con.commit()
    rid = cur.lastrowid or 0
    con.close()
    return rid


@app.get("/health")
def health():
    return {"status": "ok", "mode": INFERENCE_MODE, "labels": len(LABELS), "diseases": len(ADVISORY_DB)}


@app.get("/diseases")
def list_diseases(crop: str | None = None, q: str | None = None):
    out = ADVISORY_DB
    if crop:
        out = [d for d in out if d["crop"].lower() == crop.lower()]
    if q:
        ql = q.lower()
        out = [d for d in out if ql in d["label"].lower() or ql in d["disease"].lower() or ql in d["crop"].lower()]
    return out


@app.get("/diseases/{label}")
def get_disease(label: str):
    for d in ADVISORY_DB:
        if d["label"].lower() == label.lower():
            return d
    raise HTTPException(status_code=404, detail="Disease not found")


@app.post("/predict")
async def predict(file: UploadFile = File(...), save: bool = True):
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
        predictions = [{"label": LABELS[i], "confidence": round(float(probs[i]), 4)} for i in top]
    else:
        predictions = mock_predict(image)
    ms = round((time.perf_counter() - t0) * 1000, 1)

    top_label = predictions[0]["label"]
    top_conf = predictions[0]["confidence"]
    advisory = next((d for d in ADVISORY_DB if d["label"] == top_label), None)
    # Village safety: low confidence -> Unknown, ask to retake instead of wrong spray advice
    unknown = top_conf < UNKNOWN_THRESHOLD
    plant = (advisory or {}).get("plant") or (top_label.split("___")[0] if "___" in top_label else "Unknown")
    category = (advisory or {}).get("category", "disease")
    result_advisory = None if unknown else advisory
    record_id = save_record(top_label, predictions[0]["confidence"], predictions, advisory) if save else None
    return {"predictions": predictions, "advisory": result_advisory, "plant": plant, "category": category,
            "unknown": unknown, "unknown_threshold": UNKNOWN_THRESHOLD,
            "retake_guide": ("Low confidence. Retake in daylight: fill frame with one leaf, no shadow, no hand, wipe lens." if unknown else None),
            "inference_ms": ms, "mode": INFERENCE_MODE, "record_id": record_id}


@app.get("/history")
def history(limit: int = Query(20, le=100)):
    con = get_db()
    rows = con.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return [
        {"id": r["id"], "top_label": r["top_label"], "confidence": r["confidence"],
         "all_predictions": json.loads(r["all_predictions"]),
         "advisory_snapshot": json.loads(r["advisory_snapshot"]) if r["advisory_snapshot"] else None,
         "created_at": r["created_at"]} for r in rows
    ]


@app.post("/history")
def add_history(item: HistoryIn):
    advisory = item.advisory_snapshot or next((d for d in ADVISORY_DB if d["label"] == item.top_label), None)
    rid = save_record(item.top_label, item.confidence, item.all_predictions, advisory)
    return {"id": rid}


@app.delete("/history")
def clear_history():
    con = get_db()
    con.execute("DELETE FROM predictions")
    con.commit()
    con.close()
    return {"status": "cleared"}


@app.get("/stats")
def stats():
    con = get_db()
    total = con.execute("SELECT COUNT(*) c FROM predictions").fetchone()["c"]
    rows = con.execute("SELECT top_label, COUNT(*) c FROM predictions GROUP BY top_label ORDER BY c DESC LIMIT 10").fetchall()
    con.close()
    healthy = sum(r["c"] for r in rows if "healthy" in r["top_label"].lower())
    diseased = total - healthy
    return {"total": total, "healthy": healthy, "diseased": diseased,
            "by_disease": [{"label": r["top_label"], "count": r["c"]} for r in rows], "labels": len(LABELS)}


@app.get("/weather")
async def weather(lat: float = 19.07, lon: float = 72.87):
    """Proxy OpenWeather when key set, else deterministic mock for demo."""
    if OPENWEATHER_KEY:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get("https://api.openweathermap.org/data/2.5/weather",
                                     params={"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "metric"})
                r.raise_for_status()
                j = r.json()
                return {"temp_c": j["main"]["temp"], "humidity": j["main"]["humidity"],
                        "desc": j["weather"][0]["description"], "source": "openweather",
                        "place": j.get("name", ""), "lat": lat, "lon": lon,
                        "spray_advisory": "Avoid spraying if rain expected in 6h." if "rain" in str(j).lower() else "Suitable for spraying morning/evening."}
        except Exception as e:
            return {"temp_c": 31.2, "humidity": 68, "desc": "scattered clouds (demo fallback)",
                    "source": "mock-fallback", "place": "", "lat": lat, "lon": lon,
                    "spray_advisory": "Suitable for spraying morning/evening. Set valid OPENWEATHER_KEY for live data.",
                    "warning": f"live weather failed: {type(e).__name__}"}
    return {"temp_c": 31.2, "humidity": 68, "desc": "scattered clouds (demo)",
            "source": "mock", "place": "", "lat": lat, "lon": lon,
            "spray_advisory": "Suitable for spraying morning/evening. Set OPENWEATHER_KEY for live data."}


@app.get("/geocode")
async def geocode(q: str = Query(..., min_length=2), limit: int = 5):
    """City/village name -> lat/lon via OpenWeather geocoding. Requires OPENWEATHER_KEY."""
    if not OPENWEATHER_KEY:
        raise HTTPException(status_code=400, detail="Server missing OPENWEATHER_KEY")
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get("http://api.openweathermap.org/geo/1.0/direct",
                             params={"q": q, "limit": limit, "appid": OPENWEATHER_KEY})
        r.raise_for_status()
        return [{"name": x.get("name", ""), "state": x.get("state", ""), "country": x.get("country", ""),
                 "lat": x["lat"], "lon": x["lon"]} for x in r.json()]
