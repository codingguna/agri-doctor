# Ultimate Open-Source Plant Infection Datasets (village live-use)

All sources are open for research. Check license before redistributing. Target layout after collect:
`ml/data/unified/<Plant>___<Condition>/*.jpg` e.g. `ml/data/unified/Tomato___Early_blight/*.jpg`

## A. Leaf disease classification (lab + field)
1. **PlantVillage** — 54k, 38 classes, 14 crops. Lab background. https://www.kaggle.com/datasets/mohitsingh1804/plantvillage | https://github.com/spMohanty/PlantVillage-Dataset
2. **PlantDoc** — 2.5k field images, 13 crops, real backgrounds. Essential for village accuracy. https://github.com/pratikkayal/PlantDoc-Dataset
3. **Plant Pathology 2020/2021 (FGVC)** — Apple leaves, scab/rust/healthy. https://www.kaggle.com/c/plant-pathology-2020-fgvc7
4. **Rice Disease Image Dataset** — Bacterial blight, Brown spot, Leaf smut, Tungro. https://www.kaggle.com/datasets/minhhuy2810/rice-diseases-image-dataset
5. **Cotton Disease** — Bacterial blight, Curl virus, Fussarium. https://www.kaggle.com/datasets/janmejaybhoi/cotton-disease-dataset
6. **Wheat Rust / Wheat Disease** — Yellow/brown rust, Septoria. https://www.kaggle.com/datasets/olyadget/wheat-leaf-dataset
7. **Maize / Corn Disease** — Common rust, Gray leaf spot, Blight. In PlantVillage + https://www.kaggle.com/datasets/smaranjitghose/corn-or-maize-leaf-disease-dataset
8. **Cassava Disease (iCassava)** — CMD, CBSD. Useful for smallholder template. https://www.kaggle.com/c/cassava-disease
9. **Citrus / Mango / Grape field sets** — search Kaggle `mango disease`, `grape disease` for regional fruits.

## B. Insect / pest (what plant + what insect)
10. **Dangerous Farm Insects (NEW, verified)** — 15 classes, 474MB, CC0. Replaces dead farm-insects. `tarundalal/dangerous-insects-dataset` — see `ml/dangerous_insects_ANALYSIS.md`.
11. **IP102** — 102 pest classes, 75k images. GitHub https://github.com/xpwu95/IP102 (live) + Kaggle `rtlmhjbn/ip02-dataset` (3.1GB, live).
12. **Pest24 (FIXED)** — old GitHub `JiajunLongZeSheng/Pest24` is 404. Use Kaggle `vuanhkhoi/pest24` (mirror) or `boatshuai/pest24`, official http://aisys.iim.ac.cn/zhibao.html. 24 classes, 25k field trap images, bboxes.
13. **IPM Images (Bugwood)** — Reference pest/damage photos with CC license. https://www.ipmimages.org | https://bugwood.org
14. **Wheat (FIXED)** — old slug `olyadget/wheat-leaf-dataset` was wrong (403). Correct: `olyadgetch/wheat-leaf-dataset` (407 imgs, stripe rust/septoria) + alt `jayaprakashpondy/wheat-leaf-disease` (5 classes, 5597 imgs).
15. REMOVED: `computervision/farm-insects` — 403 dead, replaced by dangerous-insects above.

## C. How we unify for village live images
- Merge A+B into single label space: `<Plant>___<Disease|Pest|healthy>` e.g. `Cotton___Bollworm`, `Rice___Brown_spot`, `Tomato___healthy`.
- Keep `plant` separate head: parse before `___` → answers "what plant".
- Category mapping in `ml/unified_taxonomy.json`: disease | pest | healthy | unknown.
- Field robustness: train 70% PlantVillage + 30% PlantDoc/field + heavy augmentation (sun glare, shadow, soil background, motion blur, low-light). See `ml/train_unified.py`.
- Live rule: if top confidence < 0.55 → return `Unknown — retake in daylight, fill frame`, don't guess. Prevents wrong spray advice.

## Quick collect
```powershell
cd ml
pip install -r requirements.txt
python collect_datasets.py --out data/unified --with plantvillage plantdoc ip102_sample
python train_unified.py --data data/unified --epochs 12 --model mobilenetv3 --out ../backend/model
```
Without downloads, backend stays in mock mode. With downloads, export ONNX + `labels.json` enables real live detection.
