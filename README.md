# AgriDoctor — SIH26131
Early detection and management of crop diseases and pest infestations.
Govt of Maharashtra | Software | Agriculture, FoodTech & Rural Development

## Stack
- Frontend: Next.js 14 (App Router) + Tailwind + TypeScript
- Backend: FastAPI (Python) — `/predict`, `/diseases`, `/history`
- ML: MobileNetV2 transfer learning (PlantVillage / PlantDoc), ONNX-ready
- DB/Auth/Storage: Supabase (Postgres + Auth + Storage) — schema in `supabase/schema.sql`
- Deploy: Vercel (frontend) + Render / HF Spaces (backend)

## Quick start

### Backend
```powershell
cd agri-doctor/backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
# health: http://localhost:8000/health
```

### Frontend
```powershell
cd agri-doctor/frontend
npm install
copy .env.local.example .env.local
npm run dev
# app: http://localhost:3000  (proxies to http://localhost:8000)
```

### ML training (optional for MVP — mock mode works without it)
```powershell
cd agri-doctor/ml
pip install -r requirements.txt
# download PlantVillage: https://www.kaggle.com/datasets/mohitsingh1804/plantvillage
# expected layout: data/plantvillage/<class>/*.jpg
python train.py --data data/plantvillage --epochs 5 --out ../backend/model
```

Without a trained model, backend runs in MOCK mode and returns plausible demo predictions so UI can be built end-to-end.

## Project structure
```
agri-doctor/
  frontend/   Next.js UI (upload, result, history, i18n stub)
  backend/    FastAPI + advisory JSON + mock/real inference
  ml/         training + export scripts
  supabase/   schema.sql for Postgres
```

## 4-week plan
- Wk1: data pipeline + base model + Supabase schema + auth
- Wk2: FastAPI serving + frontend upload/predict flow
- Wk3: advisory content + history dashboard + Hindi/Marathi + weather
- Wk4: field testing, README, demo video, deploy

## API contract
- `GET /health` -> {status, mode: mock|real}
- `POST /predict` (multipart `file`) -> {predictions:[{label, confidence}], advisory:{...}, inference_ms}
- `GET /diseases` -> list of advisory entries
- `GET /diseases/{label}` -> single advisory
