import json
import math
from collections import defaultdict
import sys
sys.path.append(r"C:\Users\JSC\namasthetu-ai-workers")
from scratch.test_expanded_markets import EXPANDED_PUNE_MARKETS
from scratch.test_dev_attribution import detect_developer

def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2)**2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def normalize_key(name: str):
    import re
    clean = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    return clean

with open("data_fetch/pune_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

societies = []
seen = []

for el in elements:
    lat = el.get("lat") or (el.get("center", {}).get("lat"))
    lon = el.get("lon") or (el.get("center", {}).get("lon"))
    tags = el.get("tags", {})
    raw_name = tags.get("name", "").strip()
    if not raw_name or not lat or not lon:
        continue
    
    # Determine market
    market = "Greater Pune"
    for mname, (s, w, n, e) in EXPANDED_PUNE_MARKETS.items():
        if s <= lat <= n and w <= lon <= e:
            market = mname
            break
            
    norm_k = normalize_key(raw_name)
    levels = tags.get("building:levels")
    street = tags.get("addr:street", "")
    postcode = tags.get("addr:postcode", "")
    dev = detect_developer(raw_name)
    btype = tags.get("building", tags.get("landuse", "residential"))
    
    # Check duplicate
    is_dup = False
    for existing in seen:
        if existing["market"] == market and existing["norm_key"] == norm_k:
            if haversine(lat, lon, existing["lat"], existing["lon"]) < 300.0:
                is_dup = True
                # Merge levels/street if missing
                if not existing["levels"] and levels:
                    existing["levels"] = levels
                if not existing["street"] and street:
                    existing["street"] = street
                if not existing["postcode"] and postcode:
                    existing["postcode"] = postcode
                existing["wings_count"] = existing.get("wings_count", 1) + 1
                break
                
    if not is_dup:
        rec = {
            "name": raw_name,
            "norm_key": norm_k,
            "developer": dev,
            "market": market,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "levels": levels,
            "street": street,
            "postcode": postcode,
            "building_type": btype,
            "wings_count": 1,
            "osm_id": f"{el.get('type')}/{el.get('id')}"
        }
        seen.append(rec)

print(f"Total raw elements: {len(elements)}")
print(f"Total deduplicated unique societies: {len(seen)}")
print(f"Unique societies in recognized micro-markets: {len([s for s in seen if s['market'] != 'Greater Pune'])}")
print(f"Unique societies with developer attributed: {len([s for s in seen if s['developer']])}")
