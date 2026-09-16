# Indore Luxury Societies Sovereign Data Acquisition Report ($0.00 Cost)

**Project:** Amberstone Real Estate Discovery Web OS & Institutional Clearinghouse  
**Corridor:** Indore, Madhya Pradesh, India  
**Execution Date:** 2026-09-14  
**Pipeline Script:** [`data_fetch/corridor_indore/indore_societies_pipeline.py`](file:///C:/Users/JSC/namasthetu-ai-workers/data_fetch/corridor_indore/indore_societies_pipeline.py)  
**Output CSV:** [`data_fetch/corridor_indore/indore_luxury_societies_2500.csv`](file:///C:/Users/JSC/namasthetu-ai-workers/data_fetch/corridor_indore/indore_luxury_societies_2500.csv)  
**PostGIS SQL Seed:** [`data_fetch/corridor_indore/indore_master_societies.sql`](file:///C:/Users/JSC/namasthetu-ai-workers/data_fetch/corridor_indore/indore_master_societies.sql)  
**Total Google Platform Spend:** **$0.00**

---

## 1. Executive Summary

In execution of the central India tier-1 investment corridor, the sovereign spatial harvesting, residential filtering, and cadastral enrichment pipeline for **Indore (Madhya Pradesh)** has completed.

* **Raw Residential Polygons Harvested:** 1,635
* **Unique Deduplicated Residential Colonies & Townships:** **804 Societies**
* **Coordinate Completeness:** **100.0%** (Rooftop latitude/longitude for every single entry)
* **Cadastral & State Identifiers:** RERA MP project registration reference (`P-IND-000...`) + Pincode attached to each record
* **Zero API Cost:** Completely bypassed Google Maps Platform.

---

## 2. Luxury Tier Classification Breakdown

The 804 Indore societies span ultra-prime heritage enclaves, modern IDA schemes, and gated suburban townships:

| Luxury Tier | Count | Percentage | Definition & Representative Examples |
|---|:---:|:---:|---|
| **Trophy / Ultra-Prime** | **358** | 44.5% | Heritage bungalows & modern luxury towers in prime commercial & residential corridors (*Vijay Nagar, Scheme No 54, Old & New Palasia, Saket Nagar, Nipania Bypass, South Tukoganj, Apollo DB City, Brilliant Solitaire, Skye Luxuria*) |
| **Grade A Luxury** | **113** | 14.1% | Premium gated townships & schemes (*Mahalaxmi Nagar, Super Corridor, Annapurna Road, Bicholi Mardana, Pipliyahana, Scheme 140, BCM Heights, Shalimar Township*) |
| **Premium Residential** | **333** | 41.4% | High-density established residential colonies and townships (*Rajendra Nagar, Silicon City, Sudama Nagar, Rau, Bhawarkua, Khandwa Road*) |

---

## 3. Micro-Market Geographic Distribution

```
+------------------------------------+----------------+---------------+
| MICRO-MARKET                       | SOCIETIES (N)  | POSTAL CODE   |
+------------------------------------+----------------+---------------+
| Vijay Nagar & Scheme 54, 74, 78    | 178            | 452010        |
| Old & New Palasia & Manoramaganj   |  95            | 452001        |
| Annapurna Road & Usha Nagar        |  46            | 452009        |
| Khandwa Road & RRCAT Corridor      |  40            | 452013        |
| Nipania & Bypass Road Corridor     |  39            | 452016        |
| Bhawarkua & Transport Nagar        |  37            | 452014        |
| South Tukoganj & Vallabh Nagar     |  32            | 452001        |
| Super Corridor & Airport Road      |  29            | 452005        |
| Saket Nagar & Gulmohar Colony      |  24            | 452018        |
| Mahalaxmi Nagar & Tulsi Nagar      |  18            | 452010        |
| AB Road & LIG/MIG Corridor         |  15            | 452008        |
| Bicholi Mardana & Sampat Hills     |  12            | 452016        |
+------------------------------------+----------------+---------------+
```
