# MIE — Market Intelligence Engine
### Pipeline Extraction & Implementation Plan
Source: Namasthetu × Hue Cycle, Full Launch Scope v1.0 (HYC-SCO-2026-3841), § 12 "Embedded ML / AI"

---

## 1. What MIE Is (as defined in the scope doc)

| Attribute | Value |
|---|---|
| Full name | Market Intelligence Engine |
| One-line definition | "Time-series + aggregation pipeline" (glossary, p.1) |
| Function | Trend charts, demand heatmaps, anomalies |
| Model / stack | Python 3.13 + Prophet + Pandas ("custom aggregations") |
| Inputs | All platform transaction data |
| Outputs | Trend charts, demand heatmaps, anomalies |
| Latency | **Batch (daily)** — the only one of the six AI services with no real-time/near-real-time latency target |
| Where it runs | Not given an explicit row in the § 12.2 "Where Inference Lives" placement table (see § 6.1 — a documentation gap worth flagging) |
| Build phase | P07 (Technology Integration & AI, W10–W17); explicit milestone: **W16 — "AI: market intelligence baseline"** |
| Owning bounded context | **Intelligence** (same context as VIE/AVM and LQA) — "AVM, comparables, demand signals, listing audit, market intel" |
| Feature-table home | § 03.M09 "Intelligence & Analytics Engine" |

MIE is one of six embedded AI services (DEE, PAM, VIE/AVM, SSE, LQA, MIE) and the **last to land** in the build timeline (W16, after DEE/PAM/SSE and after VIE/AVM's scaffold). It is also structurally different from the other five: it is a **batch aggregation/forecasting pipeline over the platform's own transaction data**, not a per-request inference service — nothing calls MIE synchronously; it produces artifacts (charts, heatmaps, anomaly flags, reports) that other surfaces read.

---

## 2. End-to-End Pipeline (reconstructed from the doc)

```
SOURCE DATA: "All platform transaction data"
  - TransactionCompleted events (Transaction Service)
  - Listing activity (ListingActivated, PriceUpdated, Relisted —
    Property context)
  - Inquiry/search activity feeding demand signals (SearchExecuted,
    PropertyViewed — Discovery context)
  - Time-series storage: TimescaleDB extension on PostgreSQL 17,
    explicitly named for "Price history, market intelligence"
   │
   ▼
DAILY BATCH JOB (Python 3.13 + Prophet + Pandas)
   - Time-series decomposition / forecasting: Prophet models trend +
     seasonality on price history per locality/micro-market
   - Custom aggregations (Pandas): demand density, transaction
     velocity, volume deltas — "custom aggregations" per tech-stack
     table, exact metrics not enumerated beyond named outputs
   ▼
THREE OUTPUT ARTIFACT TYPES
   ┌────────────────────┬─────────────────────────────────────────┐
   │ Trend charts        │ Feeds: Price trend graphs (5/10/20-yr    │
   │                     │ where historical data exists, 2-yr        │
   │                     │ trailing fallback); 12-month price        │
   │                     │ forecast (90% confidence band)            │
   ├────────────────────┼─────────────────────────────────────────┤
   │ Demand heatmaps     │ Per-city · inquiry density · transaction  │
   │                     │ velocity (Web surface, P1)                │
   ├────────────────────┼─────────────────────────────────────────┤
   │ Anomalies           │ Sudden price drop · unusual volume ·      │
   │                     │ flagged to ops (Admin surface, P1)        │
   └────────────────────┴─────────────────────────────────────────┘
   ▼
WRITE-BACK / DISTRIBUTION
  - Aggregated data persisted to TimescaleDB (queryable time-series
    store shared with VIE/AVM's price-history use)
  - Event emitted: MarketReportGenerated (Intelligence context)
  - Anomaly alerts routed to Ops/Admin console
  - Weekly digest compiled for "Market intel digest" (P2, auto-
    generated city report via email)
   ▼
CONSUMERS
  - PIP "AI insight panel": price, market position, demand signal,
    narrative — "daily refresh" (this cadence lines up with MIE's
    daily batch, suggesting the PIP panel's demand-signal component
    is a direct MIE read, alongside VIE/AVM's valuation component)
  - Owner dashboard: "Demand signal for owners" (real-time label of
    cool/warm/hot — despite MIE's own batch-only cadence, implying
    the owner-facing "real-time" framing is really "as fresh as the
    last daily batch," not truly live — worth clarifying, see § 6)
  - Owner dashboard: "Search demand index" (per-micromarket buyer
    search volume matching property)
  - Investor journey ("Scan" stage): dashboard + digest, "Anomaly
    alerts" as the named signal for weekly review
  - VIE/AVM: demand_signal and neighbourhood growth score features
    likely sourced from MIE's aggregation output (per VIE/AVM's own
    plan, § 6.4 of that document, flagging MIE as a feature-input
    dependency with a sequencing gap — MIE lands W16, five weeks
    after AVM training data assembly at W11)
  - Admin/Ops: anomaly alerts queue
```

### Where MIE sits in the platform topology
```
SERVICES (bounded contexts): ... Property ... Discovery ... Transaction ...
AI layer:  AI: DEE   AI: PAM   AI: AVM   AI: SSE   AI: LQA
                                                                    │
                                              (MIE not shown as a distinct
                                               box in the reviewed topology
                                               diagram — folded into
                                               "Intelligence" generally)
```
Per the bounded-context table, MIE lives inside the same **Intelligence** context as VIE/AVM and LQA:
- **Publishes** (as part of Intelligence): `ValuationPublished`, `ListingScored`, `MarketReportGenerated`
- **Consumes** (as part of Intelligence): `PropertyRegistered`, `ListingActivated`, `PriceUpdated`, `InspectionCompleted`

Notably, `TransactionCompleted` — the event most obviously central to MIE's "all platform transaction data" input — is not listed among Intelligence's explicit consumed-events in the bounded-context table excerpt reviewed (only VIE/AVM's latency-table row explicitly ties `TransactionCompleted` to "Intelligence (comparable update)"). This is likely just an aggregation-table omission rather than a real gap, but worth confirming against the full event catalogue.

---

## 3. Data Model Touchpoints

- **TimescaleDB extension** (PostgreSQL 17 / Aurora) — the explicit backing store for "Price history, market intelligence," shared with VIE/AVM's multi-year price trend graphs. MIE and VIE/AVM likely read/write overlapping time-series tables — schema ownership should be clarified (see § 6).
- **MarketReportGenerated event** — no payload shape is given in the event table excerpt reviewed (unlike `ValuationPublished` or `ListingScored`, which have explicit field lists) — this needs to be defined during build (likely: `report_id`, `city`/`locality`, `period`, `report_url` or embedded summary, `generated_at`).
- **PIP `ai_insights.demand_signal`** (`cool | warm | hot` enum, per VIE/AVM's plan) — MIE is the most likely source of this field's underlying data (inquiry density, transaction velocity), even though the doc's PIP payload description attributes the field generically to `ai_insights` without naming which service computes it.
- **Anomaly records** — "flagged to ops," implying some persisted anomaly entity/queue exists for Ops consumption, though no dedicated ERD entity for anomalies is named in the sections reviewed — likely reuses or extends the `FRAUD_FLAG`-style generic flagging pattern seen elsewhere in the doc, or is a distinct, undocumented entity (flag as open question).
- **Neighbourhood growth score** (0–100, "based on construction, transit, infra spend") — sits in the Intelligence feature table alongside MIE's other outputs; the doc doesn't explicitly say MIE computes this vs. it being a separately-sourced score, but its inputs (construction/transit/infra) look like classic aggregation-pipeline territory consistent with MIE's stack.

---

## 4. Modules & Services MIE Affects or Depends On

| Module | Relationship to MIE | Why it matters for planning |
|---|---|---|
| **Transaction Service** | `TransactionCompleted` is MIE's foundational input ("all platform transaction data") — every closed sale/rental is a data point for trend, velocity, and anomaly computation. | MIE's output quality is directly bounded by transaction volume — a cold-start problem at launch nearly identical to VIE/AVM's own comparables cold-start issue (see VIE/AVM plan § 6.2), since both draw from the same thin early-transaction pool. |
| **Discovery Service** | Search/inquiry activity (`SearchExecuted`, `PropertyViewed`) is the natural source for "inquiry density" in demand heatmaps and the demand signal — not explicitly named as a direct MIE input in the doc, but implied by the demand-heatmap feature description. | Confirm whether MIE reads Discovery's event stream directly, or whether Discovery pre-aggregates and MIE only consumes a rollup — affects data-pipeline design and potential double-aggregation risk. |
| **VIE/AVM (Valuation)** | VIE/AVM's own plan already flags MIE as a likely upstream feature provider for `demand_signal` and neighbourhood growth score in its 13-feature LightGBM model. | Creates a **bidirectional-looking but actually one-directional dependency**: MIE → VIE/AVM (not the reverse), and the build-timeline sequencing gap (MIE at W16 vs. AVM training data assembled at W11) means early VIE/AVM iterations must either launch without these features or backfill them once MIE lands — a concrete cross-team sequencing risk shared by both plans. |
| **LQA (Listing Quality Auditor)** | LQA's plan (§ 6.3 of that document) already flags a dependency on VIE/AVM's price baseline for its "suspicious price" flag; MIE is one step further upstream as a contributor to that baseline via demand/market signals. | Not a direct LQA dependency, but a second-order one worth being aware of when debugging why a price-anomaly flag behaves unexpectedly in early weeks. |
| **PIP / AI insight panel** | "Price · market position · demand signal · narrative · daily refresh" — the *daily* cadence matches MIE's daily batch exactly, strongly suggesting this panel's demand-signal component reads directly from MIE's latest batch output. | Confirms an SLA: the AI insight panel's demand-signal freshness is capped at "as of last night's batch," not live — should be reflected accurately in UI copy/expectations rather than implying real-time. |
| **Owner Dashboard** | Two named features directly: "Demand signal for owners" (cool/warm/hot, labelled "Real-time" in the feature table) and "Search demand index" (per-micromarket buyer search volume). | The feature table's own "Real-time" label for demand signal appears to conflict with MIE's stated batch-only cadence — this is worth resolving explicitly (see § 6.2) before it becomes a mismatched user expectation. |
| **Investor Dashboard / Journey** | "Anomaly alerts" is the named signal at the Investor's "Scan" journey stage (weekly review cadence); portfolio-level "Yield · gain estimates" at the "Portfolio" stage also plausibly draw on MIE's trend data. | MIE's daily batch feeding a weekly investor review cadence is a comfortable fit latency-wise — no tension here, unlike the owner-dashboard "real-time" framing. |
| **Notification Service** | Weekly "Market intel digest" (P2, email) and presumably anomaly-alert notifications to Ops are downstream consumers of MIE's output. | Confirm delivery mechanism/ownership: does MIE itself trigger the digest email, or does it just produce the report artifact that Notification Service picks up on a schedule? |
| **Admin / Ops Console** | Anomaly alerts ("sudden price drop, unusual volume") are explicitly "flagged to ops." | Needs a defined ops workflow: severity levels, triage queue, and whether an anomaly can auto-suspend a listing/trigger a FRAUD_FLAG (mirrors the same undefined-escalation pattern already flagged in the LQA plan § 6.4 for LQA→FRAUD_FLAG). |
| **Infrastructure/DevOps (P08)** | Daily batch job scheduling/orchestration — not explicitly named in the doc (no Airflow/cron/Kubeflow reference specific to MIE, unlike the Continuous Learning Loop's Kubeflow/Metaflow for model retraining). | MIE's batch orchestration tooling needs to be decided — reuse the same Kubeflow/Metaflow infra named for the continuous learning loop (§ 12.3), or a simpler scheduled job (e.g., Kubernetes CronJob) since MIE's Prophet/Pandas pipeline isn't described as a continuously-retrained ML model in the same sense as VIE/AVM's LightGBM or PAM's CLIP/ResNet. |

---

## 5. Build Sequencing (from the master timeline)

| Week | Milestone relevant to MIE |
|---|---|
| W09 | AI gateway, AVM service scaffold begin |
| W10 | DEE implemented |
| W11 | AVM training data assembled |
| W12 | PAM in production |
| W14 | Infra: EKS clusters live; AI: SSE production with embeddings |
| **W16** | **"AI: market intelligence baseline"** — MIE's explicit production milestone, paired in the same stage with "Mobile: parity with web," "Performance optimisation begins," and "WhatsApp [integration, per truncated excerpt]" |
| — | LQA in production (bundled with transaction/escrow layer — timing relative to W16 not fully resolved in excerpts reviewed) |
| W17 | Feature-complete milestone, all modules functional, code freeze |
| W18–19 | QA cycle, security audit, performance testing, UAT |
| W21 | Go-live |

MIE is the **last** of the four "AI services baseline" items (DEE, AVM, SSE, LQA — note MIE itself isn't named in that specific W7-stage grouping, "AI services baseline (DEE, AVM, SSE, LQA), 20 days, Stage 5" — **MIE is conspicuously absent from that named baseline group**, consistent with it landing later at W16 as its own separate milestone) to reach production. This has a direct consequence: any feature depending on MIE (VIE/AVM's demand_signal feature, owner dashboard's demand signal, investor anomaly alerts) either launches degraded or launches late relative to the rest of the AI service suite.

**Gate for phase P07 (AI):** ML lead sign-off — "models in production with monitoring."

---

## 6. Open Questions / Risks to Resolve Before Building

1. **MIE has no row in § 12.2 "Where Inference Lives"**: that table names 7 placement decisions (search ranking, fraud/spam scoring, document extraction, photo analysis, valuation, listing audit, embeddings refresh) but never places MIE — likely because "batch daily" doesn't need the same latency-driven placement reasoning as the others, but this should be confirmed rather than assumed; at minimum, MIE's batch job's *compute placement* (which cluster/queue it runs on) needs to be decided even if latency isn't the driver.
2. **"Real-time" label conflicts with batch cadence**: the Owner Dashboard feature table explicitly labels "Demand signal for owners" as a real-time signal ("cool/warm/hot"), but MIE — its most likely source — runs daily batch only. Either (a) there's a separate, faster demand-signal computation this doc doesn't fully describe, or (b) the "real-time" label is aspirational/imprecise and should be corrected to "daily" before it ships as a user-facing claim.
3. **MIE conspicuously excluded from the "AI services baseline" grouping**: Stage 5 of the timeline names "AI services baseline (DEE, AVM, SSE, LQA)" as a single 20-day workstream — MIE is not in that list and lands separately at W16. Confirm this is intentional sequencing (MIE genuinely depends on more mature transaction volume/data before it's useful) rather than an oversight in resourcing/planning.
4. **`TransactionCompleted` not explicitly listed as an Intelligence-consumed event**: the bounded-context table's "Consumes" column for Intelligence lists `PropertyRegistered, ListingActivated, PriceUpdated, InspectionCompleted` — not `TransactionCompleted`, even though MIE's core stated input is "all platform transaction data" and VIE/AVM's own latency-table row explicitly ties `TransactionCompleted` to Intelligence. Reconcile this apparent inconsistency in the event catalogue before building the consumer.
5. **`MarketReportGenerated` payload undefined**: unlike other Intelligence events (`ValuationPublished`, `ListingScored`), no field list is given — needs to be specced.
6. **Anomaly entity/workflow undefined**: no ERD entity is named for anomalies; the ops workflow (triage, severity, whether it can escalate to FRAUD_FLAG or auto-suspend a listing) is unspecified — same category of gap already flagged for LQA's fraud-escalation question (LQA plan § 6.4), suggesting a platform-wide need for a unified "AI flag → ops action" escalation framework rather than three ad hoc ones (LQA, MIE anomalies, Trust's FRAUD_FLAG).
7. **Cold-start data problem**: like VIE/AVM (T-04 in the risk register), MIE's trend/anomaly/demand outputs are only meaningful with sufficient transaction and inquiry volume — the doc's risk register doesn't name a MIE-specific risk entry, but the underlying cause (thin early data) is identical to the one already formally tracked for VIE/AVM. Worth explicitly extending T-04's mitigation language ("comparable-rich micro-markets only" disclosure) to cover MIE-derived trend charts, heatmaps, and anomaly detection with the same honesty-about-confidence approach.

---

## 7. Suggested Immediate Next Steps

1. **Resolve the "real-time" vs. "daily batch" discrepancy** for owner-facing demand signal — either specify a faster-path computation or correct the feature-table language/UI copy before build.
2. **Batch orchestration decision**: choose the scheduling/orchestration tool for MIE's daily Prophet/Pandas job (Kubeflow/Metaflow reuse vs. simpler CronJob) and get it on the infra roadmap ahead of W16.
3. **Event catalogue reconciliation**: confirm with whoever owns the master event catalogue whether `TransactionCompleted` is (or should be) an explicit Intelligence-consumed event, resolving the inconsistency in § 6.4.
4. **Spec `MarketReportGenerated`**: define its payload shape now, since Notification Service (digest emails) and Admin Console (anomaly alerts) both need to consume it.
5. **Unified AI-flag escalation framework**: propose a single, shared "AI signal → ops action" pattern that LQA's flags, MIE's anomalies, and Trust's FRAUD_FLAG can all plug into, rather than building three bespoke escalation paths independently — flagged as a cross-cutting recommendation across the LQA and MIE plans.
6. **Cold-start disclosure extension**: explicitly extend the T-04 risk mitigation ("comparable-rich micro-markets only" disclosure, confidence stated in narrative) to MIE's trend charts and demand heatmaps for launch, so early users see appropriately caveated market intelligence rather than over-confident output on thin data.
7. **Confirm MIE's exclusion from the AI-baseline grouping is intentional**: raise with the program/PM owner to make sure MIE's later W16 landing is a deliberate sequencing choice (data-maturity dependency) and not simply an under-resourced afterthought relative to the other five AI services.

---

*Compiled from Namasthetu × Hue Cycle Full Launch Scope v1.0, primarily § 12 (Embedded ML/AI), with cross-references to the Intelligence & Analytics feature table (§ 03.M09), Owner Dashboard and Investor Journey sections, bounded-context/event table, tech-stack rationale, master timeline, and — where relevant for shared dependencies — the companion VIE/AVM and LQA pipeline plans produced earlier in this series.*