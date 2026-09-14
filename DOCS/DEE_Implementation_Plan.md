# Document Extraction Engine (DEE) — Implementation Plan
**Namasthetu · AI/ML Track · Owner: You (AI/ML + Python)**
**Source: Namasthetu Scope v1.0 FINAL, §12.1–§12.4, §03.M02, §07.5, §16.2**

---

## 1. What DEE Is, In One Paragraph

DEE is the first of six embedded AI services (§12.1). It takes a PDF or image of a legal
property document (sale deed, gift deed, partition deed, allotment letter, or Encumbrance
Certificate) and turns it into structured, queryable data: owner name, survey number, area,
dates, and encumbrance entries. It is **not** a standalone AI feature — it is the mechanism
that makes Identity & Ownership Verification (§03.M02) possible, because a human ops
reviewer cannot read thousands of deeds by hand. Every property's verification badge,
ownership-chain reconstruction, and encumbrance flag downstream of DEE.

This is the correct first service to build: nothing else in the verification module or the
Property Intelligence Profile (PIP) can go live without it.

---

## 2. Where DEE Sits in the System (Context, Not Isolation)

```
Owner uploads doc (web/mobile)
        │
        ▼
S3 multipart upload ──► SQS dispatch ──► FastAPI worker (DEE) ──► Claude entity extraction
        │                                       │
        │                                       ▼
        │                              DOC_EXTRACTION row written
        │                              (entities_json, confidence, ai_summary)
        ▼
DOCUMENT_VERSION (file pointer, SHA-256)          confidence < threshold?
        │                                               │
        ▼                                               ▼
SSE stream: extraction status to owner UI      Manual ops review queue (Admin)
                                                         │
                                                         ▼
                                          Ownership chain reconstruction (cross-refs
                                          EC + sale deed + tax) → Verification badge
```

Two other services (§12.1) consume DEE's output directly:
- **Listing Auditor (LQA)** — checks that extracted entities match the listing draft.
- **Valuation (VIE)** — uses extracted area/dates as model features.

**Exception to note:** the source doc treats DEE, AVM, SSE, LQA as one 20-day "AI services
baseline" work item (line: *"AI services baseline (DEE, AVM, SSE, LQA) — 20 days, Stage 5"*),
and elsewhere says DEE specifically gets implemented in a later week alongside RERA
integration. That means your DEE work will not be reviewed in isolation — it needs to expose
clean interfaces early so AVM/SSE/LQA teams (or future-you) aren't blocked.

---

## 3. Exact Spec, As Written In The Document

| Attribute | Value (from §12.1 / §12.2) |
|---|---|
| Inputs | PDF or image of a legal document |
| Outputs | Structured JSON: `owner`, `survey_no`, `area`, `dates`, `encumbrances` |
| Latency (P95, launch) | 3–10 s, **async** |
| Latency (P95, Year 1) | tighter, but still async — not a live-request-path service |
| Model stack | Tesseract (OCR) + Claude (entity extraction) |
| Where it runs | Async pipeline: S3 → SQS → FastAPI worker → Claude |
| Why async | "User-visible delay acceptable; complex pipeline; status streamed via SSE" |
| Status delivery | Server-Sent Events, reconnects via `last-event-id` |
| Success metric (SLA) | **97%** successful extractions / total (§ Ops metrics table) |
| End-to-end user-facing budget | "Document upload → extract" = 4s launch / 1.5s Year-1 (§11.1) — **note this is narrower than the 3–10s DEE latency figure; see Exceptions §7.1** |

### 3.1 Database contract you must honor (§07.5 ERD)
DEE writes to `DOC_EXTRACTION`, not `DOCUMENT` or `DOCUMENT_VERSION` — those are owned by
the upload/versioning service, not by you.

```
DOC_EXTRACTION
  PK extract_id      UUID
  FK version_id      UUID        -- links to DOCUMENT_VERSION, not DOCUMENT
  entities_json      jsonb       -- your structured output
  ai_summary         text        -- Claude's human-readable summary
  confidence         float       -- drives the ops-review routing decision
  extracted_at       ts
```
Relationship: `DOCUMENT_VERSION` **produces (1..1)** `DOC_EXTRACTION`. One extraction row per
document *version*, not per document — if an owner re-uploads a corrected deed, that's a new
version and a new extraction, and the old one is retained for audit (versioning is immutable
by design, §07.5).

### 3.2 Confidence threshold behavior (§03.M02, "Manual ops review queue")
> "Auto-unverifiable docs → ops queue with AI confidence + suggested resolution"

This means DEE is not just "extract and return" — it must also decide, per document, whether
its own output is trustworthy enough to auto-proceed. Below-threshold documents route to a
human admin queue, and your service must supply *why* it's unsure (a suggested resolution),
not just a low number.

---

## 4. Build Plan — Phased

### Phase 0 — Interface lock (before writing extraction logic)
- Define the exact `entities_json` schema (owner, survey_no, area, dates[], encumbrances[])
  with field-level types, since LQA and VIE will consume this later and you don't want to
  break their contract mid-build.
- Confirm the SQS message contract with whoever owns the upload service (S3 key, document
  type, property_id, version_id) — this is a cross-team dependency, not something you can
  infer.
- Decide the confidence threshold value and what "suggested resolution" strings look like
  (e.g., "photo too dark, re-scan p.2", "survey number ambiguous between two matches").

### Phase 1 — OCR layer (Tesseract)
- Ingest PDF/image from S3, normalize (deskew, denoise, PDF-to-image render for scanned
  legal docs — these are frequently low-quality scans, not born-digital PDFs).
- Run Tesseract; retain raw OCR text + per-word confidence for later escalation logic.
- Handle the known regional-document failure mode explicitly (see §6, O-07 below) — don't
  assume clean English-language typed text.

### Phase 2 — Entity extraction (Claude)
- Prompt Claude against the raw OCR text to extract: owner name(s), survey number, plot/unit
  area, relevant dates (execution date, registration date), and encumbrance entries (type,
  amount, holder, date) if the doc is an EC.
- Structure the prompt so document *type* (sale deed / gift deed / partition deed / allotment
  letter / EC) changes the extraction schema slightly — an EC has encumbrance-specific fields
  a sale deed doesn't.
- Follow the AI Gateway pattern (§12.4) rather than calling Claude directly: this gets you
  response caching, cost governance, safety/PII filtering, and fallback for free, and it's
  described as mandatory for *every* LLM call in the system, not optional infrastructure.
- Version prompts in git per §12.4 ("prompts treated as code: reviewed, versioned, A/B
  tested") — this is a real requirement here, not boilerplate advice, because DEE prompts
  will need retuning as regional document formats surface (§6).

### Phase 3 — Confidence scoring & routing
- Compute a confidence score from OCR word-confidence + Claude's own extraction certainty
  (e.g., ask Claude to self-report per-field confidence, don't just take a single scalar).
- Write `DOC_EXTRACTION` row (entities_json, ai_summary, confidence, extracted_at).
- If confidence < threshold: emit an ops-queue event with the suggested resolution text, per
  §03.M02.
- If confidence ≥ threshold: emit the event that lets the ownership-chain reconstruction
  service proceed.

### Phase 4 — Status streaming
- Emit SSE events at each pipeline stage (queued → OCR done → extraction done → routed) so
  the owner's UI shows live progress, per §11.3's SSE mechanism table. Support
  `last-event-id` reconnect — the doc explicitly calls this out as the failure-mode handling
  for this exact use case ("Document extraction status ... Auto-reconnect with last-event-id").

### Phase 5 — Feed the continuous learning loop (§12.3)
- Emit a labeled event on every extraction (success, ops-override, correction) to
  Kafka → S3 archive — this is the "Event capture" step of the continuous learning loop and
  DEE is one of its inputs.
- When an ops reviewer corrects an extraction, that correction is the ground-truth feedback
  signal for future retraining (§12.3 step 8) — make sure the correction path writes back in
  a format the weekly retraining pipeline can consume, even if you're not building that
  pipeline yet.

### Phase 6 — Testing & rollout
- Target the 97% success-rate SLA explicitly as a test gate, not an aspirational number.
- Test against realistic degraded input: low-resolution phone photos, skewed scans, regional
  scripts, handwritten annotations on printed deeds — these are named risks, not edge cases
  (§6).
- Load-test the async pipeline against the 4s (launch) / 1.5s (Year-1) *upload → extract*
  budget from §11.1 even though DEE's own stated latency is 3–10s — reconcile this before
  committing to a number (see Exceptions, §7.1).

---

## 5. Non-Negotiables Carried Over From the Wider Architecture

These aren't DEE-specific, but the doc is explicit that no service gets a pass on them:

1. **AI Gateway only** — never call Claude directly from the worker; route through the
   gateway for caching, cost ceilings, safety filtering, and fallback (§12.4).
2. **Weekly retrain cadence** — DEE is one of six services expected to participate in the
   weekly Kubeflow/Metaflow retraining pipeline once enough labeled data exists (§12.3).
3. **Shadow deployment before traffic ramp** — any updated extraction model runs in shadow
   for a week before A/B ramp, with automatic rollback on regression (§12.3, steps 5–7).
4. **PII handling** — Aadhaar/PAN references are tokenized elsewhere in the system and "never
   raw" (§07 identity ERD notes); DEE must not leak raw PII into logs, prompts sent to
   third-party providers without gateway redaction, or `ai_summary` text shown to
   unauthorized users.

---

## 6. Named Exceptions & Risks (Do Not Discover These Yourself Later — They're Already Flagged)

| ID | Risk | Directly relevant to DEE? | Mitigation per doc |
|---|---|---|---|
| **O-07** | "Document AI extraction fails on regional docs" | **Yes — this is DEE by name.** | Manual review queue (you're building this routing) · regional template training · partner with state-specific OCR vendors |
| T-01 | DigiLocker API approval delayed by UIDAI bureaucracy | Indirect — DEE processes uploaded docs regardless of whether they arrived via DigiLocker or manual upload, so DEE is not blocked by this, but the **volume and cleanliness** of input documents changes depending on which path is live | OTP-based fallback path; doesn't change your extraction logic |
| T-04 | AI valuation accuracy below threshold at launch | Indirect — VIE depends partly on DEE-extracted area/dates as features; a DEE accuracy problem could quietly become "someone else's" valuation problem | Doc explicitly separates disclosure/confidence messaging for VIE — worth flagging cross-team if you see systematic DEE weaknesses |

**Read O-07 carefully — it is the single most important exception for your specific
workstream.** The document is telling you, in advance, that regional-language and
non-standard-format documents *will* break extraction at some rate, and the answer isn't
"improve the model until it doesn't" — it's a three-part mitigation (manual review queue +
regional template training + state-specific OCR vendor partnerships). Your Phase 3 routing
logic *is* the first of these three mitigations. The other two (template training, vendor
partnerships) are likely product/ops decisions above your scope, but you should design
`entities_json` and the confidence signal so that adding a regional template later doesn't
require a schema rewrite.

---

## 7. Use-Case Shifts & Ambiguities to Resolve Before/During Build

### 7.1 Latency figures disagree — reconcile, don't guess
- §11.1 states the *user-visible* "Document upload → extract" operation must hit **4s
  (launch) / 1.5s (Year-1)**.
- §12.1 states DEE itself has a P95 latency of **3–10s, async**.
- These are not necessarily contradictory (the 4s/1.5s figure may cover only the "upload +
  queue accepted" acknowledgment, with actual extraction continuing async and reported via
  SSE) — but the document does not spell this out explicitly, and treating them as the same
  number will produce a plan you can't hit. **Action: clarify with whoever owns §11 SLOs
  whether "upload → extract" means "extraction fully complete" or "extraction job accepted
  and streaming begun" before you commit to an architecture.**

### 7.2 Document-type polymorphism isn't fully specified
The doc lists five document types feeding DEE (sale deed, gift deed, partition deed,
allotment letter, EC) but only gives one shared output shape (`owner, survey_no, area,
dates, encumbrances`). In practice an allotment letter and an EC don't share a schema — an EC
is fundamentally about *encumbrance history*, not ownership transfer. **You will need to
either:**
(a) design `entities_json` as a superset schema with type-conditional optional fields, or
(b) treat "encumbrance extraction" as a semi-distinct sub-flow within DEE.
The doc doesn't dictate which; this is a design decision within your scope.

### 7.3 Ownership-chain reconstruction is a separate feature, but eats DEE's output raw
§03.M02 lists "Ownership chain reconstruction" as its own P1 feature: *"AI cross-refs EC +
sale deed + tax to build 3-txn chain · flags gaps."* This is not part of DEE itself in the
service map (§12.1 only lists 6 named AI services, and chain reconstruction isn't one of
them) — but it clearly consumes multiple DEE outputs (EC + sale deed extractions) across
*multiple* documents for the same property. **Clarify whether this cross-document
reconstruction logic is your responsibility as an extension of DEE, or a separate
verification-service task that merely calls DEE's stored output.** The doc's own service map
is silent on ownership of this step — flag it rather than assume.

### 7.4 "Suggested resolution" text generation is underspecified
§03.M02 requires the ops queue to receive "AI confidence + suggested resolution" but nowhere
does the doc define what a suggested resolution looks like structurally (free text? enum +
detail? actionable link?). Recommend treating this as a short free-text field from Claude
initially (cheap to build, easy to read), with a note to formalize into a taxonomy once ops
has used it for a few weeks and you see what resolutions recur.

---

## 8. Definition of Done for DEE (v1 / Launch)

- [ ] Async pipeline live: S3 upload event → SQS → FastAPI worker → Tesseract → Claude (via
      AI Gateway) → `DOC_EXTRACTION` row written.
- [ ] SSE status stream implemented with `last-event-id` reconnect support.
- [ ] Confidence scoring implemented; below-threshold docs correctly routed to the ops
      review queue with a suggested-resolution string.
- [ ] `entities_json` schema documented and shared with AVM/SSE/LQA/ownership-chain owners.
- [ ] 97% extraction success rate hit on a representative test corpus (include regional/
      low-quality scans, not just clean typed PDFs).
- [ ] Event emission to Kafka for the continuous learning loop wired, even if the weekly
      retraining pipeline itself isn't built yet.
- [ ] No raw PII (Aadhaar/PAN numbers) persisted in logs or passed ungated to any LLM
      provider.
- [ ] Latency ambiguity (§7.1) resolved and documented with the SLO owner, not assumed.

---

## 9. Open Questions to Raise Before Starting Phase 1

1. Does "upload → extract" in §11.1's SLO table mean job-accepted or extraction-complete?
2. Who owns ownership-chain reconstruction (§03.M02) — is cross-document logic in DEE's
   scope or a downstream verification-service task?
3. Is there an existing sample corpus of Indian sale deeds / ECs (ideally including regional
   scripts) to test against before real user uploads arrive?
4. What confidence threshold value is acceptable to Ops for the manual-review split — this
   materially affects reviewer headcount planning, so it shouldn't be a number you pick alone.
5. Is the AI Gateway (§12.4) already scaffolded, or does DEE's build block on it existing
   first? (Timeline note: doc lists "Backend: AI gateway, AVM service scaffold" as a Week-8ish
   item and "DEE (document extraction) implemented" slightly later — suggesting gateway
   should exist before you need it, but confirm sequencing.)
