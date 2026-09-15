# Namasthetu Prisma Schema — Architecture Overview

**Spec reference:** HYC-SCO-2026-3841 (Docs 01–07) · **DB:** PostgreSQL 17 (Aurora) with PostGIS (pgvector planned, not yet enabled)

This is the schema for a real-estate "Property Intelligence" platform (India + UAE), covering property listing, KYC/verification, field inspection, AI valuation, escrow transactions, messaging, billing, and geo/market reference data. It has **13 logical sections**, ~60 models, and ~55 enums.

---

## 1. High-level module map

| # | Section | Purpose |
|---|---------|---------|
| 1 | State-machine enums | The "closed graph governance" statuses driving every lifecycle |
| 2 | Domain enums & attributes | Property/document/media descriptive enums |
| 3 | Master core entities | Users, Properties, Inspections, Documents, Listings, Transactions, Valuations, Audit log |
| 6 | Entitlements & legal evidence | Paid unlocks, KYC verification records |
| 7 | Reputation & communication | Reviews, Conversations, Messages, Inquiries |
| 8 | Billing, engagement, vault access | Invoices, saved searches, favorites, document sharing/access logs, notifications, payouts |
| 9 | PIP provenance & locality | Price forecasts, deed history timeline, neighbourhood intelligence |
| 10 | Display exchange rates | Currency conversion snapshots (display-only) |
| 11 | Locality reference data | POIs, commute hubs, amenity catalogue |
| 12 | Projects/developers/market data | Developer, Society (project), Locality, market rates, registered transactions |
| 13 | GIS reference layers | Raw OSM/Geofabrik ingestion tables (PostGIS) |

---

## 2. The central entity: `Property`

Everything essentially radiates from **`Property`**. Key facts:
- Owned by a `User` (role `PropertyOwner`), one-to-many.
- Carries physical attributes (type, config, area, floor, facing), address + PostGIS `geom` point, pricing in **minor units** (paise/fils/cents) tagged by a `currency` enum field, and denormalized "search-card snapshot" fields (`verifiedOwnerBadge`, `lastInspectedAt`, `avmDifferencePct`, etc.) that are refreshed by background jobs rather than computed at query time (avoids join-heavy search queries).
- Optionally linked to a `Society` (the building/project) and a `Locality` (neighbourhood) — both by FK **and** by denormalized string snapshot columns (`locality`, `city`) for the same "read on every search row" reason.
- Fans out to almost every other domain: `DigitalTwin` (1:1 3D scan), `Inspection[]`, `LegalDocument[]`, `Listing[]`, `Transaction[]`, `AiValuation[]`, `LqaAudit[]`, `PipUnlock[]`, `Review[]`, `Conversation[]`, `Inquiry[]`, `Favorite[]`, `PriceForecast[]`, `DeedHistoryEvent[]`, `NeighbourhoodIntelligence` (1:1), `PropertyAmenity[]`, `RegisteredTransaction[]`, `LocalityReview[]`, `MediaAsset[]`.

```
User (owner) ──< Property >── Society ── Developer
                    │             │
                    │             └── Locality
                    ├──< DigitalTwin (1:1)
                    ├──< Inspection ──< InspectionPhoto
                    ├──< LegalDocument ──< DeedHistoryEvent / DocumentShareLink / DocumentAccessLog
                    ├──< Listing ──< Transaction ──< Invoice / Conversation / Review
                    ├──< AiValuation
                    ├──< LqaAudit
                    ├──< PipUnlock
                    ├──< NeighbourhoodIntelligence (1:1)
                    ├──< PropertyAmenity >── AmenityDefinition
                    ├──< MediaAsset
                    └──< RegisteredTransaction
```

---

## 3. People & identity

- **`AdminUser`** — internal back-office staff (`AdminRole`: SUPER_ADMIN, OPS_LEAD, LEGAL_VERIFIER, DISPATCH_MANAGER, ARBITRATOR, SUPPORT_AGENT). Referenced from many models via **named relations** for accountability trails: `LqaReviewer`, `ArbitratedTransactions`, `RegistrationAttestor`, `SuspendedUsers`, `AdminActor`.
- **`User`** — the platform citizen (`UserRole`: OWNER, BUYER, INSPECTOR, NRI_OWNER, INVESTOR, LENDER_PARTNER, GOVT_PARTNER). Tracks a 6-state KYC lifecycle (`UserKycStatus`), masked Aadhaar/PAN identity tokens, a suspension sub-flow (with `priorKycStatus` to restore on lift), and currency/consent preferences.
  - Has optional 1:1 sub-profiles: **`OwnerProfile`** (bank/escrow payout details, NRI flags) and **`InspectorProfile`** (license, service pincodes, rating, dispatch fields).
  - Fans out into almost every "user did X" table: transactions (as buyer/seller/disputant), reviews (authored/received), conversations (buyer/seller side), messages, inquiries, invoices, saved searches, favorites, notifications, document share links/access logs, pip unlocks, kyc verifications.

A recurring pattern: **named relations** (`@relation("X")`) are used whenever a model has two or more FKs to the *same* target table that mean different things (e.g. `Transaction.buyer` vs `Transaction.seller`, both `User`).

---

## 4. Core lifecycle models (Section 3)

| Model | Role | Key relations |
|---|---|---|
| `DigitalTwin` | 3D/gITF walkthrough for a property (1:1) | `Property` |
| `Inspection` | 80-point field audit by an `InspectorProfile` | `Property`, `InspectorProfile` (`InspectorAssignments`), has `InspectionPhoto[]` |
| `InspectionPhoto` | Photos per inspection, tagged by `RoomCategory`, defect severity | `Inspection` |
| `LegalDocument` | Uploaded deed/certificate in the S3 WORM vault, with AI OCR extraction fields | `Property`; has `DocumentShareLink[]`, `DocumentAccessLog[]`, `DeedHistoryEvent[]` |
| `Listing` | The marketplace-facing activation of a property (LQA-gated) | `Property`; has `Transaction[]`, `Inquiry[]` |
| `LqaAudit` | Listing Quality Auditor score/audit trail | `Property`, `AdminUser` (reviewer) |
| `Transaction` | Escrow deal (Razorpay) between buyer/seller, with dispute/arbitration and government registration attestation fields | `Property`, `Listing`, `User`×3 (buyer/seller/disputant), `AdminUser`×2 (arbitrator/attestor); has `Review[]`, `Conversation` (1:1), `Invoice[]` |
| `AiValuation` | AVM valuation snapshot (estimate, risk scores, comparables) | `Property` |
| `AdminAuditLog` | Immutable admin action log (CERT-In/DPDPA compliance) | `AdminUser` |

**Lifecycle enums governing these:** `PropertyStatus` (13 states, DRAFT→ARCHIVED), `InspectionStatus` (7), `DocumentStatus` (7), `ListingStatus` (6), `TransactionStatus` (8), `LqaStatus` (5), `UserKycStatus` (6), `VerificationStatus` (8, used by KYC checks in section 6).

---

## 5. Entitlements & legal evidence (Section 6)

- **`PipUnlock`** — a *paid* record of a user's access to a property's "Deep Intelligence" report (single property or nationwide `TRUST_PASS`). Deliberately durable in Postgres (comment explains this replaced a Valkey-only cache that silently lost paid entitlements on eviction/restart). Renewals create new rows rather than mutating expiry, preserving billing history.
- **`KycVerification`** — one row per identity check (`KycProvider`: DIGILOCKER, UIDAI_AUA, NSDL_PAN, MANUAL_OPS; `KycCheckType`; `KycCheckStatus`), linked to `User`.

---

## 6. Reputation & communication (Section 7)

- **`Review`** — deal review tied to a `Transaction`, with author/target `User` (named relations `ReviewAuthor` / `ReviewSubject`), moderated via `ReviewStatus` (PUBLISHED/FLAGGED/REMOVED).
- **`Conversation`** — 1:1 with `Transaction`, buyer/seller `User`s (named relations), status (`OPEN`/`ARCHIVED`/`BLOCKED`); has `Message[]`.
- **`Message`** — belongs to a `Conversation` and a sender `User`.
- **`Inquiry`** — a lead/contact-form style inquiry tied to a `Listing`/`Property` and a `User`, with `InquiryStatus` (OPEN/RESPONDED/CLOSED/SPAM).

---

## 7. Billing, engagement, vault access, delivery (Section 8)

| Model | Purpose |
|---|---|
| `Invoice` | Billing document (`InvoiceKind`: TOKEN_FEE, TRUST_PASS, PIP_UNLOCK, INSPECTION_FEE, COMMISSION), linked to `User`/`Transaction` |
| `SavedSearch` | User's saved search filters |
| `Favorite` | User's saved/liked properties |
| `DocumentShareLink` | Shareable link to a `LegalDocument`, revocable |
| `DocumentAccessLog` | Audit trail of view/download/share actions on documents (`DocumentAccessAction`) |
| `Notification` | Multi-channel (`NotificationChannel`: WHATSAPP/SMS/EMAIL/PUSH) delivery record with retry/dead-letter status |
| `InspectorPayout` | Payout to an inspector for completed work (`PayoutStatus`) |
| `PriceForecast` | Predicted future price trend for a property |

---

## 8. PIP provenance & locality intelligence (Section 9)

- **`DeedHistoryEvent`** — the property's title-chain timeline (sale/gift/khata transfer/encumbrance/mortgage release/etc., via `DeedEventType`/`DeedEventStatus`), optionally backed by a `LegalDocument`.
- **`NeighbourhoodIntelligence`** — 1:1 side table per property holding computed "Around this locality" data: metro/airport distance, water/flood/air-quality indices. Contains legacy JSON blobs (`commuteMatrixJson`, `schoolsNearby`) explicitly marked in comments as superseded by the live `Poi`/`CommuteHub` tables below.

## 9. Display exchange rates (Section 10)

- **`ExchangeRate`** — daily snapshot per currency pair, **display-only** (never used for actual settlement — Razorpay settles in INR, and per-currency amounts are stored in their own minor units).

## 10. Locality reference data (Section 11)

- **`Poi`** ("point of interest": schools, hospitals, banks, metro stations, etc.) — sourced from OSM or manual ops entry, geo-indexed (`Gist`), classified by `PoiCategory`/`PoiSource`; linked to the import run that last confirmed it.
- **`PoiImportRun`** — tracks each OSM/Geofabrik ingestion batch; a POI is only "retired" after two consecutive runs miss it (protects against source-data glitches wiping a whole city).
- **`CommuteHub`** — curated destinations ("major hubs") used for the property's commute-time widget (`CommuteHubCategory`: FINANCE, AIRPORT, TECH, etc.).
- **`AmenityDefinition`** — the fixed catalogue of amenities (icon, category, filterable flag) referenced by both `PropertyAmenity` and `SocietyAmenity`.
- **`PropertyAmenity`** / **`SocietyAmenity`** — join tables recording whether a specific property/society has a given amenity, and its verification provenance (`AmenityStatus`: CLAIMED/VERIFIED/NOT_FOUND), tied back to the `Inspection` that confirmed it.

## 11. Projects, developers, localities, market data (Section 12)

- **`Developer`** — builder/company; has many `Society` projects.
- **`Society`** — a building/project (many properties can belong to one); links to `Developer` and `Locality`, carries project-level facts (units, towers, RERA numbers, price range) and its own amenities/unit types/media/market rates.
- **`SocietyUnitType`** — one configuration a project offers (e.g. "2 BHK, 1,180–1,345 sqft") with floor plan and price band.
- **`Locality`** — neighbourhood/area page: ratings, boundary polygon (PostGIS `MultiPolygon`), rank-in-city; has many `Property`, `Society`, `LocalityReview`, `MarketRate`, `RegisteredTransaction`.
- **`LocalityReview`** — a resident's rating of a locality (separate from deal `Review`, since a resident may not have a `Transaction`); can be backed by a `Property` as proof of residence.
- **`MarketRate`** — aggregated market statistics (asking rate, registered rate, rent) scoped to city/locality/society over a period.
- **`RegisteredTransaction`** — a government-registered sale deed record (IGR/DLD source), optionally matched to a listed `Property`; deliberately **never stores buyer/seller names** even though the source registry extract has them (privacy-by-design comment in the code).
- **`MediaAsset`** — gallery item (photo/video/floor plan/brochure) owned by exactly one of `Property` or `Society`.

## 12. GIS reference layers (Section 13)

Raw ingestion tables for the whole-of-India OSM/Geofabrik dataset, loaded by an external script (`scripts/ingest-osm-gpkg.ts`), modeled in Prisma purely so `prisma migrate` doesn't treat them as drift:
- `OsmPoi`, `OsmTransport`, `OsmPlace` (seeds `localities`), `OsmWaterBody`, `OsmLanduse` — all keyed by `osm_id`, geo-indexed via PostGIS `Gist`. Notably, `latitude`/`longitude` on point tables are **database-generated columns** (`GENERATED ALWAYS AS ST_Y(geom)/ST_X(geom) STORED`) — Prisma can't express this natively, so they're marked as `dbgenerated()` defaults and the comments warn never to write to them directly.

---

## 13. Cross-cutting design patterns worth knowing

1. **Money as minor units + explicit currency.** Every property-scoped monetary column is a `BigInt` in minor units (paise/fils/cents) paired with a `CurrencyCode` enum on the same row — avoids parallel `*Fils`/`*Paise` columns per currency. A few older columns (`Transaction`, `PipUnlock`, `Invoice`, payouts) are still named `*Paise` because those always settle in INR via Razorpay regardless of the property's original currency.
2. **Denormalized "card snapshot" fields.** Search-result and card-rendering fields (badges, last-inspected date, price trend %) are copied onto `Property`/`Society` rows and refreshed by background jobs, instead of being computed via joins on every search — a deliberate performance tradeoff called out repeatedly in comments.
3. **Durable ledgers over cache-only state.** `PipUnlock` explicitly replaced a Valkey-only TTL key because that risked silently losing paid entitlements; Postgres is now "the record of sale," Valkey just a rebuildable read cache.
4. **Provenance/evidence columns instead of bare booleans.** E.g. `Transaction.isRegisteredWithGovt` used to be a flag with no backing evidence; the schema now also stores `registeredDeedNumber`, `registrationVolume`, `sroOffice`, and the attesting admin — so a legal claim always has supporting data next to it.
5. **Verification requires a named source.** Amenity and inspection-derived facts (`PropertyAmenity`, `SocietyAmenity`) can only be marked VERIFIED/NOT_FOUND if tied to a specific `Inspection` id (enforced via DB `CHECK` constraints noted in comments, since Prisma can't express conditional requireds).
6. **PII minimization by design.** Aadhaar/PAN are stored masked + token-hashed, never raw; `RegisteredTransaction` explicitly omits buyer/seller names from government deed data even though the source has them.
7. **Named relations for multi-FK-to-same-model cases.** Used heavily wherever a table references `User` or `AdminUser` more than once with different meanings (buyer/seller, reviewer/actor/arbitrator/attestor, etc.).
8. **Legacy fields kept but superseded.** Several JSON/array columns (`Property.amenities`, `NeighbourhoodIntelligence.commuteMatrixJson`/`schoolsNearby`) are explicitly marked as legacy, replaced by normalized tables (`PropertyAmenity`, `Poi`/`CommuteHub`), and slated for removal after backfill.
9. **PostGIS throughout**, `geometry` (raw degrees) for the bulk-ingested OSM layers vs. `geography` (metre-accurate) for user-facing property/society/locality points — schema comments warn against casting between them inside hot query paths because it skips the GIST index.
10. **A known infra bug is documented inline**: the `datasource` block's original `pgvector` extension name is invalid (the extension is actually named `vector`), which broke `prisma db push`/`docker compose up`; it's currently removed until the embedding column (doc 06) is ready and the Docker image is updated to ship both PostGIS and pgvector.