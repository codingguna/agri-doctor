import io
from PIL import Image
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def _img(w=300, h=300):
    img = Image.new("RGB", (w, h), (0, 128, 0))
    b = io.BytesIO()
    img.save(b, format="JPEG")
    b.seek(0)
    return b


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_diseases_include_pests():
    r = client.get("/diseases")
    assert r.status_code == 200
    labels = [d["label"] for d in r.json()]
    assert any("Bollworm" in x for x in labels)
    assert all("plant" in d and "category" in d for d in r.json())


def test_predict_returns_plant_category():
    r = client.post("/predict", files={"file": ("leaf.jpg", _img(), "image/jpeg")})
    assert r.status_code == 200
    j = r.json()
    assert "plant" in j and "category" in j and "unknown" in j
    assert "predictions" in j
    h = client.get("/history?limit=5")
    assert len(h.json()) >= 1
    assert client.get("/stats").json()["total"] >= 1


def test_reject_non_image():
    r = client.post("/predict", files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")})
    assert r.status_code == 400
