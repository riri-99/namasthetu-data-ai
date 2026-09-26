# LQA — Listing Quality Auditor
### Pipeline Extraction & Implementation Plan
Source: Namasthetu × Hue Cycle, Full Launch Scope v1.0 (HYC-SCO-2026-3841), § 12 "Embedded ML / AI"

---

## 1. What LQA Is (as defined in the scope doc)

| Attribute | Value |
|---|---|
| Full name | Listing Quality Auditor |
| One-line definitions | "LLM-based listing transparency scorer" (glossary, p.1); "LLM-based service that scores listing transparency and flags issues" (glossary, p.1) |
| Function | Score 0–100 + categorised flags + suggestions, on every listing submission |
| Model / stack | Rule engine + Claude API (Python 3.13 + Claude API, per tech-stack table) |
| Inputs | Listing draft (text, price, photos-present metadata, disclosures) |
| Outputs | Score 0–100, flags, suggestions |
| Latency target (P95) | 5–15 s async |
| Where it runs | Background queue + Claude API — "Latency-tolerant; result attached to PIP event log" |
| Build phase | P07 (Technology Integration & AI, W10–W17); explicit milestone: **"LQA in production"** alongside the W-stage that lands the Transaction/escrow layer and Admin console KYC queue |
| Owning bounded context | **Intelligence** (same context that owns AVM, comparables, demand signals, market intel — *not* the Trust context, despite the doc's obvious fraud-adjacent framing) |
| Feature-table home | § 03.M09 "Intelligence & Analytics Engine" — listed alongside AVM, comparable sales engine, price forecasts, rather than under § 03.M10 "Reputation & Trust System" |

LQA is one of six embedded AI services (DEE, PAM, VIE/AVM, SSE, LQA, MIE). It is the **gatekeeper of the listing lifecycle**: no listing reaches public searchability without passing through it. Unlike PAM/VIE/SSE, which enrich or rank content already visible, LQA is a **hard state-machine gate** — a failing score structurally blocks the listing.

---

## 2. End-to-End Pipeline (reconstructed from the doc)

```
Owner composes listing (draft state — "Listing being composed; never published")
   │
   │ Owner submits
   ▼
LISTING STATUS → pending_approval
   ("Submitted; awaiting LQA review + ops approval")
   ▼
Event/job enqueued → Background queue (SQS/Kafka-style)
   ▼
LQA SERVICE (Python 3.13 + Claude API, async, 5–15s P95)
   - Rule engine pass: structural/heuristic checks
     (missing photos, incomplete fields, price sanity)
   - Claude API pass: LLM evaluation of transparency/honesty
     — "flags incomplete · dishonest framing · missing photos"
   - Combined into: lqa_score (0–100) + categorised flags
     (photos, price, disclosure, language) + suggestions
   ▼
SCORING DECISION (§ 8.8 state machine: queued → scoring → scored →
                   approved | rejected)
   ├─ Score ≥ 90        → auto-approved, skips ops review entirely
   ├─ Score 72–89        → approved, but MAY route to ops queue for
   │                        spot-check
   ├─ Score < 72          → rejected — returns to 'draft' with
   │                        structured, categorised feedback
   └─ Owner revises (unlimited revisions) → re-queues → previous
        score/flags shown side-by-side with current on re-score
   ▼
Event emitted: ListingScored
   (property_id, listing_id, lqa_score, flags)
   ▼
LISTING STATUS TRANSITION
   - Score ≥ 72 AND ops approval (where required) → 'active'
     (live, publicly searchable)
   - Score < 72 → back to 'draft'
   ▼
Consumers of ListingScored:
   - Ops (if below threshold) — routes into fraud/quality review queue
   - Discovery — listing only becomes searchable/indexable once
     'active'; SSE's corpus effectively excludes anything that
     hasn't cleared LQA
   ▼
Separately, if content patterns suggest fraud rather than just poor
quality (undisclosed defects, duplicate-content patterns, suspicious
>30%-off-market pricing):
   FRAUD_FLAG may be created (subject_type=property/listing,
   reason, confidence, source=AI|manual ops|user report)
   → FraudFlagged event → Ops, Audit
   (FRAUD_FLAG is a Trust-context entity that "attaches to any
    subject" — property, user, inspector, review — so LQA-triggered
    flags and Trust-context fraud detection share the same downstream
    sink even though LQA itself lives in Intelligence)
```

### Where LQA sits in the platform topology
```
SERVICES (bounded contexts): ... Property ... Discovery ... Trust ...
AI layer:  AI: DEE   AI: PAM   AI: AVM   AI: SSE   AI: LQA
                                                                │
                                          Listing draft reads / events / cache
```
Per the bounded-context table, LQA lives inside the **Intelligence** context:
- **Publishes** (as part of Intelligence): `ValuationPublished`, `ListingScored`, `MarketReportGenerated`
- **Consumes** (as part of Intelligence): `PropertyRegistered`, `ListingActivated`, `PriceUpdated`, `InspectionCompleted`

It sits adjacent to, but structurally separate from, the **Trust** context, which owns `FraudFlagged`, reviews, moderation, and reputation scoring — the doc explicitly gives Trust its own, more heuristic/pattern-based fraud detection for **reviews** ("Claude API + heuristics · paid review detection · IP · patterns"), distinct from LQA's listing-transparency scoring. These are two separate LLM-assisted anti-fraud surfaces in the platform, not one.

---

## 3. Data Model Touchpoints

- **LISTING** state machine (§ 8.8, 5 states: `queued → scoring → scored → approved | rejected`; separately, the Listing lifecycle itself has `draft → pending_approval → active → paused/expired/closed`) — LQA is the mechanism that moves a listing from `pending_approval` toward `active`; `Quality gate` note explicitly: *"pending_approval requires LQA score ≥ 72/100 to reach active. Below 72 returns to draft with structured feedback."*
- **ListingScored event payload** — `property_id`, `listing_id`, `lqa_score`, `flags` — this is the canonical write-back contract; any UI surface displaying LQA results (owner-facing feedback, ops queue) should consume this shape directly.
- **FRAUD_FLAG entity** (Trust context ERD) — `flag_id` PK, `subject_type` enum, `subject_id`, `reason` enum, `confidence` float, `source` enum, `flagged_at` — the doc notes *"Multiple sources: AI, manual ops, user reports. Confidence + source recorded"* — LQA is a plausible `source=AI` contributor to FRAUD_FLAG when its flags rise to fraud-level severity (vs. ordinary quality issues), though the doc doesn't explicitly wire an automatic LQA→FRAUD_FLAG trigger — **flag as an open integration question** (§ 6).
- **Revision history** — "previous score and flags shown side-by-side with current" implies LQA (or the Listing aggregate) must retain prior scoring runs per listing, not just the latest — a versioned/append-only scoring log, not a single mutable field.
- **PIP event log** — "result attached to PIP event log" (§ 12.2 "Where Inference Lives" table) — LQA's async result is written into the same event-log mechanism used elsewhere in the doc for traceable AI outputs.

---

## 4. Modules & Services LQA Affects or Depends On

| Module | Relationship to LQA | Why it matters for planning |
|---|---|---|
| **Property Service** | Owns the Listing/PIP aggregate; `ListingActivated`, `PriceUpdated` are events Intelligence (and thus LQA's context) consumes. | LQA's scoring gate is enforced at the Property/Listing state-machine level — the transition logic (`pending_approval` → `active`) must call out to or await LQA's async result before allowing activation; confirm this is modeled as a saga/process manager given LQA's 5–15s async latency. |
| **Discovery Service / SSE** | Listings only become searchable once `active`; LQA is upstream of the entire Discovery/SSE corpus. | A listing stuck in `pending_approval` or bounced to `draft` is invisible to SSE by construction — no separate "hide from search" logic is needed, but this dependency should be tested explicitly (does SSE's embeddings-refresh correctly *exclude* anything not yet `active`?). |
| **Document Service** | Listing drafts likely reference uploaded photos/disclosures managed by Document Service. | LQA's "missing photos" flag category needs read access to photo upload state — confirm whether LQA checks photo *count/presence* only, or defers photo *quality* judgments to PAM (division of labor between LQA and PAM on photo-related flags is not explicit in the doc — see § 6). |
| **PAM (Photo Analysis)** | Both LQA and PAM touch listing photos, but for different purposes (PAM: room class/defect/condition scoring from image content; LQA: presence/completeness/flagging of photos as part of listing transparency). | Needs an explicit contract: does LQA call PAM's output as an input feature (e.g., "photos exist but don't match claimed room count") or does LQA only check photo *count/metadata* independently? Not specified. |
| **VIE/AVM (Valuation)** | LQA's "Suspicious price (>30% off market)" flag category requires a market-price baseline — this is exactly what VIE/AVM computes. | Establishes a **direct dependency**: LQA needs VIE/AVM's estimate (or at minimum a comparable-based price band) available *before* it can flag price anomalies — sequencing/data-availability question for listings in markets VIE/AVM doesn't yet cover (cold-start markets per VIE/AVM's own T-04 risk). |
| **Ops & Governance context** | Owns queue management, fraud review, audit log, RBAC. Consumes `ListingScored` (for below-threshold cases) directly. | Scores 72–89 "may route to ops queue for spot-check" — the actual routing rule (all of them? a sample? risk-weighted?) isn't specified; Ops tooling/staffing plan needs this defined. |
| **Trust context (FRAUD_FLAG, reputation)** | Structurally separate from LQA (Intelligence context) but shares the same downstream fraud-review consumers and the same `FRAUD_FLAG` entity shape. | Needs an explicit decision on whether/when an LQA rejection or repeated-low-score pattern should escalate into a `FRAUD_FLAG` (vs. staying a routine listing-quality rejection) — currently these look like two parallel systems that could silently diverge without a defined handoff rule. |
| **Admin Console** | Timeline explicitly pairs "LQA in production" with "Admin console: KYC queue" work — ops reviewers need a UI for the 72–89 spot-check band and for rejected-listing feedback. | LQA's UI surface (ops queue, owner-facing structured feedback with categorised flags) is a concrete build item, not just a backend service — needs to ship alongside the scoring service, not after. |
| **Notification Service** | Not explicitly named as an LQA consumer in the event table, but a rejected listing with structured feedback plausibly needs an owner-facing notification. | Confirm whether owner notification-on-rejection is LQA's responsibility (via an event) or handled purely synchronously in the owner-facing UI when they check listing status — gap to close. |
| **AI Gateway** (§ 12.4) | Central routing/caching/rate-limiting/observability for Claude API calls. | LQA is one of three services (with DEE, VIE/AVM) explicitly noted to call Claude — should route through AI Gateway from day one for cost governance, prompt versioning, and fallback handling, consistent with the documented pattern. |
| **Continuous Learning Loop** (§ 12.3) | Generic MLOps pipeline: event capture → Feast → retraining → MLflow → shadow deploy → A/B → auto-rollback. | LQA's "rule engine" component is presumably deterministic/versioned code (not retrained), but the Claude-based transparency judgment could benefit from prompt/few-shot iteration informed by ops override outcomes (spot-check overturns LQA's approve/reject) as a feedback signal — worth scoping whether this loop applies to LQA's LLM component specifically. |
| **Infrastructure/DevOps (P08)** | Background queue (SQS/Kafka), Claude API access, general async pipeline infra shared with DEE's OCR pipeline. | LQA shares its async-queue-plus-Claude-API pattern almost exactly with DEE (§12.2: both are "background queue + Claude API" or "async pipeline... Claude worker") — likely shares infra/tooling, and possibly even code patterns; coordinate build sequencing with DEE's team. |

---

## 5. Build Sequencing (from the master timeline)

| Week | Milestone relevant to LQA |
|---|---|
| W09 | AI gateway, AVM service scaffold begin |
| W10 | DEE implemented |
| W11 | AVM training data assembled |
| W12 | PAM in production |
| W14 | Infra: EKS clusters live; AI: SSE production with embeddings |
| W16 | AI: market intelligence baseline (MIE) |
| — | **"LQA in production"** — stated alongside "Transaction layer: Razorpay escrow + agreement drafting. Admin console: KYC queue..." (i.e., LQA's production milestone is bundled into the same stage as escrow/transaction go-live and admin KYC tooling, not given its own isolated week number in the excerpts reviewed — worth confirming the exact week against the full timeline table) |
| W17 | Feature-complete milestone, all modules functional, code freeze |
| W18–19 | QA cycle, security audit, performance testing, UAT |
| W21 | Go-live |

LQA is the **last** of the four AI-services-baseline items (DEE, AVM, SSE, LQA) to reach an explicitly named production milestone in the excerpts reviewed — it lands alongside transaction/escrow infrastructure, which makes sense given listings must be quality-gated before any transaction flow can begin against them.

**Gate for phase P07 (AI):** ML lead sign-off — "models in production with monitoring."

---

## 6. Open Questions / Risks to Resolve Before Building

1. **Ops routing rule for the 72–89 band is unspecified**: "may route to ops queue for spot-check" — need to define the actual sampling/routing logic (percentage-based, risk-weighted by flag category, new-owner-only, etc.) before Ops can be staffed/trained against it.
2. **LQA ↔ PAM division of labor on photos**: both services touch listing photos but for different judgments (presence/completeness vs. content/condition). Undefined whether LQA calls PAM as an input or operates independently on photo metadata only — risks duplicated or contradictory photo-related flags to the owner.
3. **LQA ↔ VIE/AVM price-anomaly dependency**: the "suspicious price" flag category needs a market baseline that only VIE/AVM can provide — and VIE/AVM itself has a documented cold-start risk (T-04) in non-Tier-1 markets. Confirm what LQA does for price-flagging in markets where VIE/AVM has low confidence or no data (skip the flag? use a wider heuristic threshold?).
4. **LQA ↔ Trust/FRAUD_FLAG handoff undefined**: no explicit rule links LQA rejections/patterns to Trust context's `FRAUD_FLAG` entity — repeated low scores or specific flag categories (e.g. duplicate-content patterns) seem like natural fraud signals, but the doc keeps LQA (Intelligence) and fraud flagging (Trust) as parallel systems. Needs an explicit escalation contract, or a documented decision that they intentionally stay separate.
5. **Owner notification on rejection**: not explicitly modeled as an event-driven Notification Service trigger — confirm this is intentional (synchronous UI-only) or a gap.
6. **Revision-loop cost**: "No limit on revisions" combined with a 5–15s async Claude-API-backed scoring run per submission — for adversarial or careless owners repeatedly resubmitting, this is an uncapped LLM cost surface. Worth a rate-limit or cost-governance policy even though the doc doesn't flag it as a named risk.
7. **Rule engine vs. LLM split**: the tech stack says "Rule engine + Claude API" but doesn't specify which flag categories are rule-based (deterministic, cheap, fast) vs. LLM-judged (transparency, "dishonest framing," language quality). This split materially affects both cost and the 5–15s latency budget — needs an explicit design doc before implementation.

---

## 7. Suggested Immediate Next Steps

1. **Define the rule engine / LLM split explicitly**: enumerate which of the four flag categories (photos, price, disclosure, language) are deterministic rule-engine checks vs. Claude-API judgments, and get a latency/cost budget for each.
2. **Ops spot-check routing spec**: define the actual routing rule for the 72–89 score band before Admin Console UI/staffing work begins, since it's explicitly bundled into the same build stage.
3. **Cross-service contracts**: formalize LQA's read dependency on VIE/AVM (price baseline) and the (currently unconfirmed) dependency on PAM (photo content) as explicit API/event contracts, including fallback behavior when either upstream service has low/no confidence for a given listing.
4. **FRAUD_FLAG escalation policy**: decide with the Trust-context owner whether/how LQA outcomes feed FRAUD_FLAG, and implement the trigger (e.g., N consecutive rejections, or specific flag categories, auto-creates a FRAUD_FLAG with `source=AI`).
5. **Revision-loop cost governance**: set a rate limit or cost cap per listing/owner for repeated LQA re-scoring, and route through AI Gateway's caching where the draft hasn't materially changed.
6. **Owner-facing feedback UI**: build the structured, categorised feedback surface (flags + suggestions, with side-by-side previous-vs-current on revision) as a first-class deliverable alongside the backend scoring service.
7. **Confirm exact production week**: cross-check the full timeline table (beyond the excerpts reviewed) to pin down LQA's exact production milestone week, since it wasn't given an isolated week number like PAM (W12) or SSE (W14) in the sections reviewed.

---

*Compiled from Namasthetu × Hue Cycle Full Launch Scope v1.0, primarily § 12 (Embedded ML/AI) and § 8.8 (Listing Quality Audit state machine), with cross-references to the Intelligence & Analytics feature table (§ 03.M09), Reputation & Trust feature table (§ 03.M10), data model (ERD: LISTING, FRAUD_FLAG, REPUTATION_SCORE), event/bounded-context table, and master timeline.*