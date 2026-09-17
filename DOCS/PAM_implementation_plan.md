# PAM — Photo Analysis Module
### Pipeline Extraction & Implementation Plan
Source: Namasthetu × Hue Cycle, Full Launch Scope v1.0 (HYC-SCO-2026-3841), § 12 "Embedded ML / AI"

---

## 1. What PAM Is (as defined in the scope doc)

| Attribute | Value |
|---|---|
| Full name | Photo Analysis Module |
| One-line definition | CV pipeline for inspection photo classification (glossary, p.1) |
| Function | Room classification, defect detection (§ Tech stack table) |
| Tech stack | Python 3.13 + FastAPI + PyTorch (CLIP fine-tuned + ResNet) |
| Inputs | Inspection photos (geotagged) |
| Outputs | Room class, condition scores, fixture detection |
| Latency target (P95) | 200–800 ms |
| Where it runs | GPU pool on EKS (g5.xlarge instances), KEDA-scaled queue |
| Why there | Bursty workload; GPU economics drive batching |
| Build phase | P07 (Technology Integration & AI, W10–W17); production milestone at **W12** |

PAM is one of six embedded AI services (DEE, PAM, VIE/AVM, SSE, LQA, MIE) that the platform treats as **substrate, not a bolted-on feature** — i.e. it is expected to sit inline in the inspection flow, not be called out-of-band by a user action.

---

## 2. End-to-End Pipeline (reconstructed from the doc)

```
Inspector (mobile app, offline-first)
   │
   │ 1. Captures room-by-room photos during 80-point inspection
   │    — per-room photo, geotag, timestamp, anti-spoof check
   ▼
Document/Media upload → S3 (via Document Service, Node.js + S3 SDK)
   │    - encryption, access control, audit log
   ▼
INSPECTION_PHOTO record created
   - photo_id (PK), report_id (FK), s3_key, room_label,
     geotag, captured_at
   ▼
Event: photo ready for analysis → queue (SQS/Kafka-style, KEDA-scaled)
   ▼
PAM Service (Python 3.13 + FastAPI, GPU pool EKS g5.xlarge)
   - CLIP (fine-tuned) → room classification
   - ResNet → condition scoring / fixture detection
   - Runs as bursty, batched inference on KEDA-scaled queue consumers
   ▼
Outputs written back:
   - room_label (confirms/corrects inspector-entered label)
   - condition scores (cross-checked against inspector's 1–10 score
     per category: structural, electrical, plumbing, finishes,
     exterior, neighbourhood)
   - fixture / defect detection candidates
   ▼
DEFECT record created/updated (Inspection Service)
   - defect_id (PK), report_id (FK), category, severity,
     photo_id (FK — evidence link), notes
   ▼
Event emitted: DefectFlagged (published by Inspection bounded context)
   ▼
Consumed downstream by:
   - INSPECTION_REPORT (score_overall, category_scores jsonb) → PDF report generation
   - PIP (Property Intelligence Profile) → inspection.defects[], scores_by_category
   - AI insights layer → risk_score.overall / risk_score.* on PIP
   - Digital Twin → TWIN_TAG entries (defect as a tagged 3D point, AC unit/fixture/defect)
   - Notification service → owner/buyer alerts on defect flagged
   - Admin/QA → qa_status gating (pending → passed/failed; failed triggers re-inspection)
   - Continuous learning loop → PredictionFeedback events feed back as training labels
```

### Where PAM sits in the platform topology (§ system diagram)
```
SERVICES (bounded contexts):  ... Inspection ... Document ...
AI layer:  AI: DEE   AI: PAM   AI: AVM   AI: SSE   AI: LQA
                 │
        CV photo reads / events / cache
```
PAM reads from the photo/event store and writes back into the Inspection bounded context's event stream — it is not a standalone context, it's a service consumed by Inspection.

---

## 3. Data Model Touchpoints

PAM reads and writes against these entities (ERD, § data model):

- **INSPECTION_PHOTO** (`photo_id` PK, `report_id` FK, `s3_key`, `room_label`, `geotag`, `captured_at`) — PAM's primary input; `room_label` may be inspector-supplied and PAM-corrected, or PAM-only.
- **DEFECT** (`defect_id` PK, `report_id` FK, `category`, `severity`, `photo_id` FK, `notes`) — PAM's primary output; every DEFECT references an INSPECTION_PHOTO as evidence.
- **CHECKLIST_ITEM** (`item_id` PK, `report_id` FK, `category`, `description`, `score`, `notes`) — condition scores from PAM should reconcile against inspector-entered `score` per category (structural/electrical/plumbing/finishes/exterior/neighbourhood).
- **INSPECTION_REPORT** (`report_id` PK, `score_overall`, `category_scores` jsonb, `qa_status`) — aggregates PAM output into overall and category scores; `qa_status` gates whether a failed report triggers re-inspection.
- **TWIN_TAG** (within DIGITAL_TWIN, 1..1 with PROPERTY) — tagged 3D points (AC unit, defect, fixture) with 3D coordinates; PAM's defect/fixture detections are candidates for auto-tagging the digital twin, though the doc doesn't specify this link is automated — **flag as an open integration question** (see § 6).
- **PIP payload** (`inspection` object) — `defects: [{category, severity, photo_url, note}]`, `photos_count`, `scores_by_category` — this is the public/authenticated read model that ultimately surfaces PAM's output to buyers/owners.

---

## 4. Modules & Services PAM Affects or Depends On

| Module | Relationship to PAM | Why it matters for planning |
|---|---|---|
| **Inspection Service** (Node.js 22 + NestJS) | Owns dispatch, scheduling, scoring, payouts. Publishes `InspectionScheduled`, `InspectionCompleted`, `DefectFlagged`, `ReportSubmitted`. PAM's output feeds into `DefectFlagged` and the report's `category_scores`. | PAM cannot be built in isolation — it needs a contract with Inspection Service for how/when it's invoked (sync inline vs async post-upload) and how results are written back. |
| **Document Service / S3** | Stores photos with encryption, access control, audit log. | PAM needs read access to S3 photo objects (`s3_key`) — access pattern, presigned URLs, and IAM scoping need definition. |
| **Mobile Inspector App** (React Native, offline-first) | Captures photos with geotag/timestamp/anti-spoof; may upload in batches on reconnect (WorkManager/BGTaskScheduler background sync). | PAM's trigger event must tolerate delayed/batched uploads, not assume real-time single-photo arrival. |
| **AI Gateway** (§ 12.4) | Central routing/caching/rate-limiting/observability for LLM calls (Portkey-style). PAM uses PyTorch models directly (CLIP/ResNet), not an LLM call — **clarify whether PAM routes through the AI Gateway at all**, or only DEE/VIE/LQA (which explicitly use Claude) do. | Determines whether PAM needs its own observability/cost-governance path outside the AI Gateway pattern. |
| **Continuous Learning Loop** (§ 12.3) | Event capture → Feast feature store → weekly retraining (Kubeflow/Metaflow) → MLflow registry → shadow deployment → A/B ramp (Argo Rollouts) → auto-rollback → feedback loop. | PAM's model lifecycle must plug into this generic MLOps pipeline: it needs labeled training data (verified photo corpus), a retraining cadence, and a feedback signal (e.g., inspector/QA overrides of PAM's room-class or defect calls feeding back as `PredictionFeedback` events). |
| **QA Gating** (`qa_status`: pending → passed/failed) | Failed reports trigger re-inspection with a new inspector; rating impact on original inspector. | Need to decide whether PAM's confidence score is an input to QA gating (e.g., low-confidence PAM output flags a report for manual QA review) or purely advisory. |
| **Report PDF generation** | Auto-generated 12–20 page report with photos, scores, defects, AI summary (System-owned, P1 feature). | PAM output (defects, scores) is a direct input to the report generation pipeline — needs to be finalized before report assembly, so pipeline ordering/latency SLAs matter. |
| **Digital Twin / TWIN_TAG** | 3D tagged points for AC units, defects, fixtures with coordinates (Matterport/NeRF/photogrammetry capture). | Potential future integration: PAM-detected defects/fixtures could auto-populate TWIN_TAG entries, but this mapping (2D photo → 3D coordinate) is **not specified** in the doc — needs its own design spike. |
| **PIP (Property Intelligence Profile)** | The canonical, publicly/authenticated-viewable record; `inspection.defects[]`, `scores_by_category` surface directly from PAM's output (via Inspection Report). | PAM's output format must match the PIP API payload schema exactly (`category`, `severity`, `photo_url`, `note`). |
| **Notification Service** | Sends alerts (email/SMS/push/WhatsApp) — e.g. on defect flagged, doc verified. | Determine whether every PAM-flagged defect triggers an owner/buyer notification, or only above a severity threshold. |
| **Risk scoring (AI insights)** | PIP's `ai_insights.risk_score` object includes an implicit structural/condition risk contribution. | PAM's defect severity data likely feeds this composite score — dependency to confirm with whoever owns `risk_score` aggregation logic. |
| **Fraud/anti-spoof checks** | Photo geotag + timestamp anti-spoofing is mentioned as a mobile capture feature, separate from PAM's CV analysis. | Clarify division of responsibility: is anti-spoof a pre-check before PAM even runs, or does PAM itself validate photo authenticity (e.g., detect staged/stock photos)? |
| **Infrastructure/DevOps (P08)** | EKS clusters, KEDA autoscaling, GPU pool provisioning, MLflow registry, CI/CD via GitHub Actions + ArgoCD. | PAM's GPU pool (g5.xlarge) and KEDA queue scaling must be live before PAM can go to production — sequencing dependency on P08's EKS milestone. |

---

## 5. Build Sequencing (from the master timeline)

| Week | Milestone relevant to PAM |
|---|---|
| W09 | AI gateway, AVM service scaffold begin |
| W10 | DEE (document extraction) implemented — first AI service live, sets pattern PAM will likely follow |
| W11 | AVM training data assembled; Matterport SDK integrated (digital twin capture pipeline stood up) |
| **W12** | **PAM (photo analysis) in production** — alongside PIP page, document vault |
| W14 | Infra: EKS clusters live (note: this is *after* PAM's stated production week — worth flagging as a possible sequencing risk; see § 6) |
| W17 | Feature-complete milestone, all modules functional, code freeze |
| W18–19 | QA cycle, security audit, performance testing, UAT |
| W21 | Go-live |

**Gate for phase P07 (AI):** ML lead sign-off — "models in production with monitoring."

---

## 6. Open Questions / Risks to Resolve Before Building

1. **EKS timing conflict**: PAM is scheduled for production at W12, but "Infrastructure: EKS clusters live" is listed at W14. PAM's stated runtime is GPU pool on EKS — confirm whether a subset of EKS (GPU pool specifically) is provisioned earlier, or whether the W12 PAM milestone runs on a temporary/different environment first.
2. **AI Gateway scope**: Does PAM route through the AI Gateway (caching, rate limiting, observability) like DEE/VIE/LQA, or does it bypass it since it doesn't call an LLM? Needs an explicit decision — affects whether PAM needs its own OpenTelemetry instrumentation path.
3. **Sync vs async invocation**: Given the 200–800ms P95 latency target, is PAM called synchronously in the upload flow (blocking the inspector's next action) or asynchronously post-upload with results streamed back (similar to DEE's SSE-streamed OCR status)? The doc doesn't say explicitly for PAM.
4. **PAM confidence vs inspector authority**: When PAM's room classification/condition score disagrees with the inspector's manual entry, what's the resolution rule? Does it just get logged for QA review, auto-flag for re-inspection, or is inspector input authoritative?
5. **Digital Twin integration**: Is there a planned (even if post-MVP) path for PAM defect/fixture detections to auto-populate TWIN_TAG 3D coordinates, or is that manual/separate today?
6. **Training data sourcing for launch**: The continuous learning loop assumes a growing labeled photo corpus, but at launch there's no historical data — confirm what pretrained/public datasets or vendor-labeled data bootstrap the initial CLIP fine-tune and ResNet model before real inspection volume accrues.
7. **Anti-spoof boundary**: Confirm PAM's remit does not include anti-spoof/geotag validation (owned by mobile capture) unless explicitly extended.

---

## 7. Suggested Immediate Next Steps

1. **Contract definition**: Write the formal API/event contract between Inspection Service ↔ PAM (request schema: `photo_id`, `s3_key`, `room_label` (hint); response schema: `room_class`, `condition_scores`, `fixture_detections`, `defect_candidates`, `confidence`).
2. **Model selection spike**: Validate CLIP fine-tuning approach for room classification (likely transfer learning on top of pretrained CLIP) and ResNet-based defect/fixture detection — decide if this is one fine-tuned multi-task model or two separate models chained.
3. **Infra dependency check**: Confirm with Platform/DevOps (P08 owner) that GPU pool (EKS g5.xlarge) + KEDA queue scaling is available by W12, resolving the timing conflict in § 6.1.
4. **Data pipeline for bootstrap training set**: Source/label an initial photo dataset (public real estate condition datasets + any pilot inspection photos) since the continuous learning loop needs seed data.
5. **QA/feedback loop design**: Define how inspector/QA overrides of PAM output become `PredictionFeedback` events per the § 12.3 loop.
6. **Schema alignment**: Ensure PAM's output maps 1:1 into the `DEFECT` table and the PIP JSON payload's `inspection.defects[]` shape (`category`, `severity`, `photo_url`, `note`) with no translation layer needed downstream.
7. **Observability decision**: Decide monitoring stack for PAM specifically (Prometheus/Grafana via OpenTelemetry, per platform-wide observability standard) and whether it needs AI-Gateway-style cost/latency dashboards even without LLM calls.

---

*Compiled from Namasthetu × Hue Cycle Full Launch Scope v1.0, primarily § 12 (Embedded ML/AI), with cross-references to the data model (ERD), system topology diagram, event/bounded-context table, feature list, and master timeline.*