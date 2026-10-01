# AgriDoctor — Personal Project (Ultimate village-ready build)
Early detection of plant disease + insect pests from live leaf photos.
Full-stack + ML crop advisory app with field-robust training.

## Ultimate goal
One photo in the village → answers: **what plant, what disease/pest, what to do**.
- Live camera (`LiveCamera.tsx`) + file upload, works on phones in daylight
- Unified label space `<Plant>___<Condition>`: diseases + pests + healthy (19 now, 38+ after full train)
- Unknown rejection at 0.55 confidence → asks to retake instead of wrong spray advice
- Village guide in simple words + trilingual UI (EN/HI/MR) + spray weather

## Open-source data pool (see ml/DATA_SOURCES.md)
- PlantVillage 54k/38, PlantDoc 2.5k field, Pathology, Rice/Cotton/Wheat sets
- IP102 75k/102 pests, Pest24 detection, Farm Insects, IPM Bugwood
- Collect: `cd ml; python collect_datasets.py --out data/unified --with plantvillage plantdoc`
- Train field-robust: `python train_unified.py --data data/unified --epochs 12 --model mobilenetv3 --out ../backend/model`

## Quick start
```powershell
cd agri-doctor/backend
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
python -m pytest -q

cd ../frontend
npm install
copy .env.local.example .env.local
npm run dev
```

## API
- `POST /predict` -> {plant, category, predictions[3], advisory{village_advice}, unknown, retake_guide}
- `GET /diseases?crop=&q=` `GET /stats` `GET /history` `GET /weather`
