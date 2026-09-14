# Google Cloud & Maps Platform Architecture, Pricing & Strategic Feasibility Study
**Project:** Amberstone Real Estate Discovery Web OS & Institutional Clearinghouse (`namasethu-frontend-web`, `namasethu-admin`, `namasthetu-core-api`)  
**Scope:** Google Maps Platform, Google Cloud Document AI, Vertex AI (Gemini 1.5 & 2.0), Google Earth Engine, Cloud Run, Cloud CDN, Cloud Identity, Cloud KMS/HSM, and BigQuery  
**Market Corridors:** India (Mumbai, Bengaluru, Pune, NCR) and United Arab Emirates (Dubai, Abu Dhabi)  
**Document Version:** 1.0.0 · Production Architecture Evaluation  
**Reference In-Repo Location:** [`namasthetu-core-api/docs/08-Google-Services-and-Infrastructure-Pricing-Research.md`](file:///C:/Freelance/namasthetu-core-api/docs/08-Google-Services-and-Infrastructure-Pricing-Research.md)

---

## 1. Executive Summary & Architectural Context

Amberstone is an **ultra-prime cross-border real estate discovery Web OS and institutional clearinghouse console** bridging the India–UAE investment corridor. Unlike traditional advertising portals that monetize lead volume, Amberstone enforces an authoritative, closed-graph state machine:
1. **Zero-Brokerage, Owner-Only & Direct-Developer Inventory:** Enforced via cryptographic deed matching and government registry anchors (14-digit ULPIN in India; DLD Title Deeds & Makani numbers in Dubai).
2. **Deterministic Verification Moat:** 80-point civil engineer on-site inspections, legal encumbrance deed chains, and physical asset validation.
3. **Immersive Spatial Intelligence:** Interactive 3D Digital Twin walkthroughs (`ThreeTwinViewer.tsx`), macro-urban photorealistic skylines, and environmental security metrics (`NeighbourhoodIntelligence.tsx`).
4. **Institutional Clearinghouse & Escrow Settlement:** Digital contracts, automated trust deed attestations, and compliant escrow disbursements.

---

## 2. Core Service Analysis & Pricing Breakdown

```
+-------------------------------------------------------------------------------------------------------------+
| SERVICE PILLAR                    | GOOGLE SERVICE                      | AMBERSTONE TOUCHPOINT             |
+-----------------------------------+-------------------------------------+-----------------------------------+
| 1. Spatial Discovery & Location   | Google Maps Places API (New)        | Search Bar, Locality POI Layer    |
|                                   | Address Validation API              | Listing Onboarding, Deed Check    |
|                                   | Map Tiles: Photorealistic 3D Tiles  | Macro 3D Skyline Canvas           |
|                                   | Aerial View API                     | Trophy Asset Cinematic Flyovers   |
|                                   | Routes API & Distance Matrix        | Neighbourhood Commute Matrix      |
| 2. Legal & Document Ingestion     | Google Cloud Document AI            | Deed Chain OCR & Extractor        |
| 3. Generative Reasoning & AI      | Vertex AI (Gemini 1.5 & 2.0 Flash)  | LQA, AVM Narrative, Multimodal AI |
| 4. Environmental Intelligence     | Google Earth Engine (GEE)           | Water & Flood Security Indices    |
| 5. Serverless Compute & Delivery  | Cloud Run & Cloud CDN               | Microservices & 3D Asset Cache    |
| 6. Cryptography & Vault Security  | Cloud KMS / Cloud HSM & Identity    | PIP Attestations & KYC Encryption |
| 7. Clearinghouse Data Warehouse   | Google BigQuery                     | Municipal Comps & Risk Analytics  |
+-------------------------------------------------------------------------------------------------------------+
```

---

### 2.1 Google Maps Platform — Places API (New)
* **Amberstone-Specific Use Case:** Fast, predictive autocomplete in search navigation (`ExpandablePillSearch.tsx`, `search/page.tsx`) for luxury enclaves (*Worli Sea Face, Malabar Hill, Palm Jumeirah, Downtown Dubai, DIFC*); luxury POI enrichment in `NeighbourhoodIntelligence.tsx`.
* **Official Google Pricing:**
  * Shared $200.00/month recurring Google Maps credit per billing account.
  * Autocomplete Session: **$17.00 USD per 1,000 sessions** (up to 12 keystrokes + 1 Place Details call).
  * Place Details Essentials: **$17.00 USD / 1,000 requests**; Atmosphere/Enterprise: **$22.00 – $25.00 / 1k**.
* **Best-in-Class Option:** Client-side session tokens with strict HTTP Field Masking (`X-Goog-FieldMask: places.id,places.displayName,places.location,places.formattedAddress`) keeping all requests strictly at the **Essentials** SKU ($17/1k).
* **Cheapest / Cost-Effective Alternative:**
  * **Pre-Indexed PostGIS Master Table + Mapbox Search Fallback:** Pre-index the top 5,000 luxury societies and towers across Mumbai and Dubai in PostgreSQL with `PostGIS` (serves 80% of searches at **$0.00**). Use Mapbox Search ($0.75/1k vs. Google's $17.00/1k — **95.6% cost reduction**) for uncached tail addresses.
* **Monthly Cost Projections:**
  * **MVP (3k sessions):** Pure Google: **$51.00** | Hybrid Alternative: **$0.00**
  * **10k MAU (50k sessions):** Pure Google: **$850.00** | Hybrid Alternative: **$7.50** (~₹630)
  * **100k MAU (800k sessions):** Pure Google: **$13,600.00** | Hybrid Alternative: **$120.00** (~₹10,080)

---

### 2.2 Google Maps Platform — Address Validation API
* **Amberstone-Specific Use Case:** Validates exact cadastral addresses during onboarding (`list-property/page.tsx`); parses unstructured Indian and Dubai addresses into structured sub-premises (building, wing, floor, unit) to verify parity with registered deeds.
* **Official Google Pricing:** Tier 1 (0–100k): **$17.00 USD per 1,000 requests** ($0.017/call). Eligible for $200 credit.
* **Best-in-Class Option:** Automated pipeline validating sub-premise granularity. If confidence < `ROOFTOP`, prompt owner for utility bill verification.
* **Cheapest / Cost-Effective Alternative:**
  * **Dubai Makani Open API ($0.00) + Indian Postal PIN DB + Gemini Flash Normalizer:** Use Dubai Municipality's official open Makani API (1-meter rooftop accuracy for all Dubai buildings at **$0.00**). For India, parse with `libpostal` and Department of Posts PIN directory, running Gemini 1.5 Flash ($0.0001/call) to clean lines before calling external geocoders.
* **Monthly Cost Projections:**
  * **MVP (250 requests):** Pure Google: **$4.25** | Hybrid Alternative: **$0.05**
  * **10k MAU (2.5k requests):** Pure Google: **$42.50** | Hybrid Alternative: **$0.50** (~₹42)
  * **100k MAU (20k requests):** Pure Google: **$340.00** | Hybrid Alternative: **$4.00** (~₹336)

---

### 2.3 Google Maps Platform — Map Tiles API: Photorealistic 3D Tiles
* **Amberstone-Specific Use Case:** Macro-urban 3D visualizer transitioning from city skyline down to property perimeter in Dubai (*Downtown, Palm Jumeirah, Marina*) before handing off to unit-level Three.js BIM tours (`ThreeTwinViewer.tsx`).
* **Official Google Pricing:** Root Tileset Request: **$6.00 USD per 1,000 requests**. Streamed 3D child tiles are bundled.
* **Best-in-Class Option:** Stream via `@loaders.gl/3d-tiles` or CesiumJS with strict frustum culling and 1.5 km fog clipping to prevent streaming unused distant meshes.
* **Cheapest / Cost-Effective Alternative (Indian Geospatial Policy Compliance):**
  * **MapLibre GL OSM 3D Extrusions + Custom Drone Photogrammetry / 3D Gaussian Splats on Cloudflare R2:** Under India’s **National Geospatial Policy 2022**, Google does not have sub-meter photorealistic 3D meshes for Mumbai or Bengaluru. Render base urban layout via OpenStreetMap 3D extrusions ($0.00); host custom drone photogrammetry / Gaussian Splats for trophy towers on Cloudflare R2 (zero egress fees).
* **Monthly Cost Projections:**
  * **MVP (1.5k sessions):** Pure Google: **$9.00** | Hybrid Alternative: **$0.00**
  * **10k MAU (25k sessions):** Pure Google: **$150.00** | Hybrid Alternative: **$15.00** (~₹1,260)
  * **100k MAU (350k sessions):** Pure Google: **$2,100.00** | Hybrid Alternative: **$60.00** (~₹5,040)

---

### 2.4 Google Maps Platform — Aerial View API
* **Amberstone-Specific Use Case:** Automated cinematic 4K drone-quality orbital videos of penthouses and estates without waiting 3–6 weeks for DGCA/DCAA flight clearances.
* **Official Google Pricing:** Video Lookup: **$4.00 / 1k**; Video Playback: **$50.00 USD per 1,000 streams** ($0.05/view); On-demand Synthetic Render: **$4.00 – $10.00 / video**.
* **Best-in-Class Option:** Check existing Aerial View metadata once during verification. If available, trigger render once and stream via official player.
* **Cheapest / Cost-Effective Alternative (100% Legal & Superior Quality):**
  * **Civil Inspector Drone Capture + Cloudflare Stream:** Civil engineers capture 4K orbital video during the mandatory 80-point inspection using sub-249g drones (DJI Mini 4 Pro, permit-exempt in open zones). Amberstone owns 100% of the video footage (zero Google TOS liability). Stream via Cloudflare Stream ($5/mo storage + $1/1k mins viewed — **98% cost reduction**).
* **Monthly Cost Projections:**
  * **MVP (800 plays):** Pure Google: **$140.00** | Inspector + Stream: **$10.00** (~₹840)
  * **10k MAU (12k plays):** Pure Google: **$1,200.00** | Inspector + Stream: **$35.00** (~₹2,940)
  * **100k MAU (150k plays):** Pure Google: **$9,500.00** | Inspector + Stream: **$180.00** (~₹15,120)

---

### 2.5 Google Maps Platform — Routes API & Distance Matrix API
* **Amberstone-Specific Use Case:** Live commute times to commercial hubs (BKC, Nariman Point, Airport, DIFC, Downtown Dubai) in `NeighbourhoodIntelligence.tsx`.
* **Official Google Pricing:** Basic Distance Matrix: **$5.00 / 1k**; Advanced (traffic-aware, two-wheeler): **$10.00 USD per 1,000 elements**.
* **Best-in-Class Option:** Batch commute calculations into morning (`09:00`) and evening (`18:30`) runs. Cache in Valkey for 7 days per `(locality_quadrant_id, hub_id)`.
* **Cheapest / Cost-Effective Alternative:**
  * **Micro-Market Spatial Quadrant Clustering (Zero-Cost Optimization):** Group properties into 250 micro-markets. 250 quadrants × 10 destination hubs × 2 peak times × 4 weekly refreshes = **20,000 elements/month** ($200 gross, **100% offset by the $200 credit = $0.00 net cost**). Alternatively, self-host OSRM on Cloud Run ($15/mo).
* **Monthly Cost Projections:**
  * **MVP (6k elements):** Pure Google: **$60.00** | Spatial Cluster / OSRM: **$0.00**
  * **10k MAU (80k elements):** Pure Google: **$800.00** | Spatial Cluster / OSRM: **$0.00**
  * **100k MAU (1.2M elements):** Pure Google: **$12,000.00** | Spatial Cluster / OSRM: **$0.00** (or $30.00)

---

### 2.6 Google Cloud Document AI
* **Amberstone-Specific Use Case:** Automated ingestion of 30-year deed chains, Index II extracts, 7/12 land records, mutation entries, Khata certificates, and DLD title deeds in `EncumbranceDeedChain.tsx`.
* **Official Google Pricing:** OCR: **$1.50 / 1k pages**; Form Parser: **$30.00 / 1k pages**; Custom Document Extractor: **$65.00 / 1k pages**.
* **Best-in-Class Option:** Document AI Form Parser ($30/1k) coupled with Vertex AI Gemini 1.5 Flash for entity linking.
* **Cheapest / Cost-Effective Alternative:**
  * **DLD Cryptographic QR Validation ($0.00) + Surya / PaddleOCR + Gemini 1.5 Flash:**
    - 100% of modern Dubai Land Department (DLD) deeds have an official cryptographic QR code linking directly to `dubailand.gov.ae`. Scanning the QR code validates the authentic title deed at **$0.00 cost** without OCR.
    - For Indian regional deeds (Marathi Devanagari, Kannada, Hindi): Self-host Surya / PaddleOCR on Cloud Run ($0.00/page) to extract layout bounding boxes, then pass structured text into **Gemini 1.5 Flash** ($0.075 per 1M input tokens). A 20-page deed costs **$0.0045 total** vs. $1.30 on Document AI CDE (**99.6% cost reduction**).
* **Monthly Cost Projections:**
  * **MVP (2.5k pages):** Document AI: **$120.00** | DLD QR + Surya + Flash: **$2.50** (~₹210)
  * **10k MAU (35k pages):** Document AI: **$2,275.00** | DLD QR + Surya + Flash: **$32.00** (~₹2,688)
  * **100k MAU (300k pages):** Document AI: **$19,500.00** | DLD QR + Surya + Flash: **$260.00** (~₹21,840)

---

### 2.7 Google Cloud Vertex AI & Gemini Models (1.5 Flash, 2.0 Flash, 1.5 Pro)
* **Amberstone-Specific Use Case:** Listing Quality Auditor (`lqa-queue`), Valuation Intelligence Engine (AVM narratives), Multimodal civil audit assistant, and FEMA/Golden Visa regulatory advisory.
* **Official Google Pricing:**
  * **Gemini 1.5 Flash:** Input: **$0.075 / 1M tokens**; Output: **$0.30 / 1M tokens**; Context Caching: **$0.01875 / 1M tokens/hr**.
  * **Gemini 2.0 Flash:** Input: **~$0.10 / 1M**; Output: **~$0.40 / 1M tokens**.
  * **Gemini 1.5 Pro:** Input: **$1.25 / 1M**; Output: **$5.00 / 1M tokens**.
* **Best-in-Class Option:** Route 92% of queries to **Gemini 1.5 / 2.0 Flash** with Context Caching on state RERA and DLD rules; reserve **Gemini 1.5 Pro** strictly for complex 100-page deed chain fraud investigations and escrow disputes.
* **Cheapest / Cost-Effective Alternative:** Gemini 1.5 Flash as universal worker + aggressive semantic caching in Valkey (65% prompt hit rate for recurring neighborhood and comps queries).
* **Monthly Cost Projections:**
  * **MVP (25M in / 5M out tokens):** Vertex AI: **$12.50** | Cached Flash: **$4.00** (~₹336)
  * **10k MAU (350M in / 70M out tokens):** Vertex AI: **$165.00** | Cached Flash: **$55.00** (~₹4,620)
  * **100k MAU (4B in / 800M out tokens):** Vertex AI: **$1,850.00** | Cached Flash: **$620.00** (~₹52,080)

---

### 2.8 Google Earth Engine (GEE)
* **Amberstone-Specific Use Case:** Environmental Intelligence in `NeighbourhoodIntelligence.tsx`: Macro flood risk topography (post-storm Dubai floods and Mumbai monsoons), urban heat island indices, and regional green canopy (NDVI).
* **Official Google Pricing:** Commercial Basic Plan: **$500.00 USD / month** (includes 500 EECU hours + 1 TB storage).
* **Best-in-Class Option:** Pre-aggregated monthly batch pipeline: Process regional raster layers during off-peak hours, normalize scores (0–100) into BigQuery and Valkey. Zero live user queries.
* **Cheapest / Cost-Effective Alternative:** Free European Space Agency (ESA) **Sentinel-2 multispectral imagery** via AWS Open Data Registry processed with Python `rasterio`, `geopandas`, and `xarray` inside a scheduled Cloud Run container ($0.00/month in licenses).
* **Monthly Cost Projections:**
  * **MVP (50 grids):** GEE Commercial: **$500.00** | Sentinel-2 on Cloud Run: **$0.00**
  * **10k MAU (250 grids):** GEE Commercial: **$500.00** | Sentinel-2 on Cloud Run: **$12.00** (~₹1,008)
  * **100k MAU (1.5k grids):** GEE Commercial: **$750.00** | Sentinel-2 on Cloud Run: **$45.00** (~₹3,780)

---

### 2.9 Google Cloud Run & Cloud CDN
* **Amberstone-Specific Use Case:** Serverless microservice execution (`namasthetu-core-api`, Next.js 15 apps) and global edge delivery of 100MB glTF digital twins and 8K equirectangular room panoramas (`/panoramas/pano_1.jpg`).
* **Official Google Pricing:**
  * Cloud Run Free Tier: 2M requests, 360k vCPU-sec, 180k GiB-sec free every month.
  * Cloud CDN Egress: **$0.06 – $0.08 per GB** (APAC/Middle East).
* **Best-in-Class Option:** Dual-region Cloud Run in `asia-south1` (Mumbai) and `me-central1` (Doha / UAE Edge) fronted by Cloud Load Balancing, Cloud CDN, and Cloud Armor WAF.
* **Cheapest / Cost-Effective Alternative:**
  * **Cloud Run Free Tier + Cloudflare R2 Object Storage + Cloudflare Pro CDN ($20/mo flat):** Store large 3D glTF models and 8K panoramas in **Cloudflare R2** (S3-compatible, **$0.00 egress bandwidth fees**). Run API compute on Cloud Run's free tier.
* **Monthly Cost Projections:**
  * **MVP (1.5M reqs, 150 GB egress):** Cloud Run + CDN: **$12.00** | Cloud Run + Cloudflare R2: **$0.00**
  * **10k MAU (18M reqs, 2.5 TB egress):** Cloud Run + CDN: **$210.00** | Cloud Run + Cloudflare R2: **$25.00** (~₹2,100)
  * **100k MAU (220M reqs, 35 TB egress):** Cloud Run + CDN: **$2,850.00** | Cloud Run + Cloudflare R2: **$140.00** (~₹11,760)

---

### 2.10 Google Cloud Identity & Cloud KMS / Cloud HSM
* **Amberstone-Specific Use Case:** Asymmetric cryptographic signing of PIP certificates; envelope encryption of citizen KYC PII (Aadhaar XML, PAN, UAE Pass ID, bank details); enterprise SSO & hardware FIDO2 MFA for clearinghouse staff (`namasethu-admin/staff`).
* **Official Google Pricing:**
  * Cloud Identity Free: **$0.00 for up to 50 users**. Premium: **$6.00 / user / month**.
  * Cloud KMS Software: **$0.06 per key / month**; $0.03 / 10k ops. Cloud HSM: **$1.00 per key / month**.
* **Best-in-Class Option:** Cloud HSM asymmetric RSA-4096 keys for public deed verification + Cloud Identity Premium with device certificate policies for all administrative operators.
* **Cheapest / Cost-Effective Alternative:** Cloud Identity Free (up to 50 seats) + Standard Cloud KMS Software Keys ($0.06/key/mo). Beyond 50 seats, provision external field inspectors via self-hosted Keycloak on Cloud Run.
* **Monthly Cost Projections:**
  * **MVP (6 seats, 15k ops):** Google HSM + Prem: **$37.50** | KMS Soft + Identity Free: **$0.50** (~₹42)
  * **10k MAU (25 seats, 120k ops):** Google HSM + Prem: **$151.50** | KMS Soft + Identity Free: **$2.50** (~₹210)
  * **100k MAU (80 seats, 1.5M ops):** Google HSM + Prem: **$485.50** | KMS Soft + Keycloak IdP: **$15.00** (~₹1,260)

---

### 2.11 Google BigQuery
* **Amberstone-Specific Use Case:** Institutional clearinghouse data lake storing historical municipal transactions (Maharashtra Index II, Karnataka IGR, Dubai Land Department official sales); BigQuery GIS cadastral polygon intersection; AVM training dataset.
* **Official Google Pricing:** Active Storage: First 10 GB free/mo, then **$0.02 / GB / month**; On-Demand Analysis: First **1.0 TB query processing free every month**, then **$6.25 / TB**.
* **Best-in-Class Option:** Partitioned tables (monthly by transaction date) clustered by `country`, `city`, and `micro_market_id`. Query on-demand during MVP/growth stages.
* **Cheapest / Cost-Effective Alternative:** Free Tier BigQuery (10 GB storage + 1.0 TB queries free) + Local PostgreSQL `TimescaleDB` / DuckDB for operational aggregations.
* **Monthly Cost Projections:**
  * **MVP (1.5 GB storage, 250 GB queries):** Pure Google: **$0.00** (Free Tier) | Free Tier + DuckDB: **$0.00**
  * **10k MAU (15 GB storage, 2.5 TB queries):** Pure Google: **$9.45** (~₹794) | Free Tier + DuckDB: **$0.50** (~₹42)
  * **100k MAU (120 GB storage, 25 TB queries):** Pure Google: **$152.25** (~₹12,790) | Free Tier + DuckDB: **$15.00** (~₹1,260)

---

## 3. Reconciled Total Cost of Ownership (TCO) Master Matrix

*Note: The $200.00 USD monthly free credit is deducted once from the total pooled Google Maps Platform expenditure.*

| Service Line Item | Stage 1: MVP (1k MAU)<br/>Pure Google \| Hybrid | Stage 2: Growth (10k MAU)<br/>Pure Google \| Hybrid | Stage 3: Scale (100k MAU)<br/>Pure Google \| Hybrid |
|---|:---:|:---:|:---:|
| **1. Places API (New)** | $51.00 \| $0.00 | $850.00 \| $7.50 | $13,600.00 \| $120.00 |
| **2. Address Validation API** | $4.25 \| $0.05 | $42.50 \| $0.50 | $340.00 \| $4.00 |
| **3. Photorealistic 3D Tiles** | $9.00 \| $0.00 | $150.00 \| $15.00 | $2,100.00 \| $60.00 |
| **4. Aerial View API** | $140.00 \| $10.00 | $1,200.00 \| $35.00 | $9,500.00 \| $180.00 |
| **5. Routes & Distance Matrix** | $60.00 \| $0.00 | $800.00 \| $0.00 | $12,000.00 \| $0.00 |
| *Subtotal: Gross Google Maps* | *$264.25 \| $10.05* | *$3,042.50 \| $58.00* | *$37,540.00 \| $364.00* |
| *Less: Single $200 Monthly Credit* | *-$200.00 \| -$0.00* | *-$200.00 \| -$0.00* | *-$200.00 \| -$0.00* |
| **Net Google Maps Platform Cost** | **$64.25 \| $10.05** | **$2,842.50 \| $58.00** | **$37,340.00 \| $364.00** |
| **6. Cloud Document AI** | $120.00 \| $2.50 | $2,275.00 \| $32.00 | $19,500.00 \| $260.00 |
| **7. Vertex AI (Gemini Flash/Pro)** | $12.50 \| $4.00 | $165.00 \| $55.00 | $1,850.00 \| $620.00 |
| **8. Earth Engine Commercial** | $500.00 \| $0.00 | $500.00 \| $12.00 | $750.00 \| $45.00 |
| **9. Cloud Run & Cloud CDN / R2** | $12.00 \| $0.00 | $210.00 \| $25.00 | $2,850.00 \| $140.00 |
| **10. KMS / HSM & Identity** | $37.50 \| $0.50 | $151.50 \| $2.50 | $485.50 \| $15.00 |
| **11. BigQuery Analytics (On-Demand)** | $0.00 \| $0.00 | $9.45 \| $0.50 | $152.25 \| $15.00 |
| **TOTAL MONTHLY COST (USD)** | **$746.25 \| $17.05** | **$6,153.45 \| $185.00** | **$62,927.75 \| $1,459.00** |
| **TOTAL MONTHLY COST (INR @ ₹84)** | **~₹62,685 \| ~₹1,430** | **~₹5,16,890 \| ~₹15,540** | **~₹52,85,930 \| ~₹1,22,550** |
| **NET COST SAVINGS PERCENTAGE** | **97.7% Savings** | **97.0% Savings** | **97.7% Savings** |

---

## 4. Strategic Recommendations for Amberstone

1. **Deploy the "Decoupled Sovereign Geo Stack":**
   - Use MapLibre GL / OpenStreetMap for base discovery mapping.
   - Pre-index the top 5,000 luxury societies in PostgreSQL `PostGIS` for $0.00 autocomplete.
   - For Dubai, use the open Dubai Makani API ($0.00) for 1-meter rooftop verification.
   - For high-resolution 3D immersion, deploy custom drone photogrammetry / 3D Gaussian Splats stored on Cloudflare R2, bypassing both Google 3D tile licensing fees and Indian National Geospatial Policy foreign mesh prohibitions.
2. **Implement DLD Cryptographic QR Code Verification:**
   - Eliminate Document AI for Dubai properties entirely. Reading the embedded DLD QR code provides authentic, instant title verification directly from the Dubai Land Department for $0.00.
3. **Surya OCR + Gemini 1.5 Flash for Indian Land Records:**
   - Replace Document AI Custom Document Extractor ($65/1k pages) with self-hosted Surya OCR on Cloud Run coupled directly with multimodal Gemini 1.5 Flash ($0.0045 per 20-page deed).
4. **Cloudflare R2 for Large 3D Digital Twin Assets:**
   - Store all 100MB glTF files and 8K equirectangular panoramas in Cloudflare R2 with zero egress bandwidth fees, avoiding Google Cloud's punitive $0.08–$0.12/GB egress charges.
