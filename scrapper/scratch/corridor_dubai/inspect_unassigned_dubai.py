import sys
import json
sys.path.append(r"C:\Users\JSC\namasthetu-ai-workers")
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("data_fetch/corridor_dubai/dubai_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

from scrapper.scratch.corridor_dubai.test_dubai_markets import is_valid_name, DUBAI_MICRO_MARKETS

unassigned_samples = []
for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name:en") or tags.get("name", "").strip()
    if not is_valid_name(name):
        continue
    lat = el.get("lat") or (el.get("center", {}).get("lat"))
    lon = el.get("lon") or (el.get("center", {}).get("lon"))
    
    matched = None
    for mname, (s, w, n, e) in DUBAI_MICRO_MARKETS.items():
        if s <= lat <= n and w <= lon <= e:
            matched = mname
            break
    if not matched and len(unassigned_samples) < 25:
        unassigned_samples.append((name, lat, lon, tags.get("addr:street", ""), tags.get("addr:suburb", "")))

print("Unassigned samples:")
for n, lat, lon, st, sub in unassigned_samples:
    print(f" - {n:<35} ({lat:.4f}, {lon:.4f}) | Street: {st:<20} | Suburb: {sub}")
