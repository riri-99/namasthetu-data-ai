import json
import sys
from collections import Counter
sys.path.append(r"C:\Users\JSC\namasthetu-ai-workers")
from scratch.classify_pune_markets import find_market

with open("data_fetch/pune_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

unassigned_samples = []
suburbs = Counter()

for el in elements:
    lat = el.get("lat") or (el.get("center", {}).get("lat"))
    lon = el.get("lon") or (el.get("center", {}).get("lon"))
    tags = el.get("tags", {})
    name = tags.get("name", "")
    
    if not find_market(lat, lon):
        sub = tags.get("addr:suburb") or tags.get("addr:district") or tags.get("addr:street")
        if sub:
            suburbs[sub] += 1
        if len(unassigned_samples) < 20:
            unassigned_samples.append((name, lat, lon, tags.get('addr:street', '')))

print(f"Top mentioned suburbs/streets in unassigned:")
for s, c in suburbs.most_common(15):
    print(f" - {s}: {c}")

print("\nSample unassigned:")
for name, lat, lon, street in unassigned_samples[:10]:
    print(f" - {name} ({lat:.4f}, {lon:.4f}) | Street: {street}")
