# Photo Analysis Module (PAM)

**Namasthetu · Embedded AI Service #2 · Owner: AI/ML Track**  
**Spec Reference:** Namasthetu × Hue Cycle Launch Scope v1.0 (HYC-SCO-2026-3841, §12.1–§12.4, §03.M02, §05.8)  
**Implementation Plan:** [`DOCS/PAM_implementation_plan.md`](../DOCS/PAM_implementation_plan.md)  
**Database Schema Adherence:** 100% compliant with [`src/db/schema.prisma`](../src/db/schema.prisma) without modifying the schema.

---

## 1. Overview & Architectural Role

The **Photo Analysis Module (PAM)** is the computer vision AI service inline with the field inspection flow. It processes geotagged inspection photos captured during the 80-point physical inspection to extract room categories, detect condition defects, localize fixtures, and compute multi-axis condition scores:

- **Room Classification:** Classifies photos into the 10 canonical `RoomCategory` enums (Living Room, Bedrooms, Kitchen, Bathroom, Balcony, Utility, Lobby, Parking, Facade Exterior). Reconciles inspector-provided hints (`CONFIRMED` vs `OVERRIDDEN`).
- **Defect Detection & Bounding Boxes:** Localizes seepage, wall cracks, hollow tiles, and exposed wiring with normalized `[ymin, xmin, ymax, xmax]` bounding boxes and severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Anti-Spoofing & Geotag Verification:** Parses EXIF GPS and timestamps, validating against the property's cadastral boundary within the **25-meter anti-spoof gate** (Doc 05 §8).
- **Condition Scoring:** Calculates 0–100 scores across Structural, Plumbing, Electrical, Finishes, and Exterior categories. Automatically flags `seepageDetected` for property listings and PIP.
- **Digital Twin Integration:** Exports candidate 3D defect pins (`InspectionDefectPin`) for interactive 3D rendering in `digital_twin/DynamicThreeTwinViewer.tsx`.
- **PIP Payload Generation:** Populates public/authenticated PIP inspection read models (`scores_by_category`, `inspection.defects[]`).

---

## 2. Database Schema Alignment (`src/db/schema.prisma`)

PAM strictly adheres to the database contract in `src/db/schema.prisma` without modifying a single line:

### Model `InspectionPhoto` (Lines 964–994)

| Column | Type | PAM Field Mapping |
| :--- | :--- | :--- |
| `roomCategory` | `RoomCategory` | Top classified category (10-state enum). |
| `latitude` / `longitude` | `Float` | Decimal coordinates extracted from EXIF GPS. |
| `exifTimestamp` | `DateTime` | Verified image capture timestamp from EXIF. |
| `isGeotagValid` | `Boolean` | Validated against property cadastral anchor within 25 meters. |
| `hasDefect` | `Boolean` | `True` if any defect detected in photo. |
| `defectSeverity` | `DefectSeverity?` | Highest severity detected (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). |
| `defectType` | `String?` | Primary defect type string (`"seepage"`, `"wall_crack"`, `"hollow_tile"`, `"exposed_wiring"`). |
| `defectBoundingBoxJson` | `Json?` | Normalized bounding box `{ymin, xmin, ymax, xmax}`. |

### Model `Inspection` (Lines 900–960)

| Column | Type | PAM Field Mapping |
| :--- | :--- | :--- |
| `scoreOverall` | `Int?` | Composite 0–100 condition score. |
| `scoreStructural` | `Int?` | 0–100 structural condition sub-score. |
| `scorePlumbing` | `Int?` | 0–100 plumbing condition sub-score. |
| `scoreElectrical` | `Int?` | 0–100 electrical condition sub-score. |
| `scoreFinishes` | `Int?` | 0–100 finishes condition sub-score. |
| `seepageDetected` | `Boolean?` | Aggregated flag (`True` if seepage observed in any photo). |
| `keyFindings` | `Json?` | Headline findings `[{ category, status: "PASS"\|"OPTIMAL"\|"ATTENTION", detail }]`. |
| `status` | `InspectionStatus` | `QA_PASSED` (if score $\ge 70$ and no critical defects) or `QA_PENDING`. |

---

## 3. Digital Twin & PIP Integration

### Digital Twin 3D Defect Pins (`DynamicThreeTwinViewer.tsx`)
PAM automatically generates 3D defect pins matching `InspectionDefectPin`:
```json
{
  "id": "pin_photo_102_0",
  "roomId": "master_bedroom_1",
  "roomName": "Master Bedroom",
  "type": "wall_crack",
  "severity": "HIGH",
  "position": [0.35, 1.45, 0.0],
  "color": "#EF4444",
  "description": "Hairline masonry crack detected across partition plaster.",
  "floorLevel": 1
}
```

### PIP Inspection Payload (`HYC-SCO-2026-3841 §12`)
PAM exports the read model payload:
```json
{
  "inspection_id": "insp_018f3a2b",
  "score_overall": 88,
  "scores_by_category": {
    "structural": 95,
    "plumbing": 75,
    "electrical": 90,
    "finishes": 92
  },
  "seepage_detected": true,
  "photos_count": 24,
  "defects_count": 2,
  "defects": [
    {
      "category": "PLUMBING",
      "severity": "MEDIUM",
      "defect_type": "seepage",
      "photo_url": "s3://namasthetu-inspections/insp_018f3a2b/p_04.jpg",
      "note": "Discoloration and dampness patch observed along bathroom junction."
    }
  ]
}
```

---

## 4. Quick Start & Execution

### Run Unit Tests (12 Automated Tests Covering All Phases)
```bash
python -m unittest pam.test_pam.test_pam_pipeline
```

### Drop-In Dataset Evaluation & Retraining CLI (`pam/train_and_eval.py`)
No mock data is kept in the repository. Whenever you have your real inspection photo dataset ready, point directly to your folder:

#### 1. Evaluate Vision Model on Real Images
Recursively scans your image directory (`.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.tiff`), evaluates room classification, defect detection, and latency:
```bash
python pam/train_and_eval.py --mode eval --data-dir "path/to/inspection_photos"
```

#### 2. Bootstrap Pseudo-Labels for Unannotated Photos
Runs high-confidence inference ($\ge 0.80$) and generates ground-truth candidate JSONs:
```bash
python pam/train_and_eval.py --mode bootstrap --data-dir "path/to/inspection_photos" --out-dir "pam_output/annotations"
```

#### 3. Export Fine-Tuning JSONL for CLIP / ResNet Training
Formats verified and bootstrapped photos into standard contrastive text-image pairs:
```bash
python pam/train_and_eval.py --mode export-finetune --out-dir "pam_output/annotations" --out-file "pam_output/finetuning_pairs.jsonl"
```

---

## 5. Python API Usage

```python
from pam import pam_pipeline, RoomCategory

# Single Photo Analysis
result = pam_pipeline.analyze_photo(
    image_input="path/to/inspection_photo.jpg",
    inspection_id="insp-101",
    photo_url="https://s3.amazonaws.com/inspections/photo_101.jpg",
    room_label_hint="Living Room",
    target_coords=(12.9716, 77.5946), # Cadastral property anchor
)

print(result.room_category)           # RoomCategory.LIVING_ROOM
print(result.is_geotag_valid)         # True (within 25m gate)
print(result.has_defect)              # False or True
print(result.to_prisma_inspection_photo()) # Dictionary ready for db upsert
```
