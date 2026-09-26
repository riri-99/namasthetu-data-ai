import json

with open("data_fetch/pune_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

has_coords = 0
for el in elements:
    lat = el.get("lat") or (el.get("center", {}).get("lat"))
    lon = el.get("lon") or (el.get("center", {}).get("lon"))
    if lat and lon:
        has_coords += 1

print(f"Elements with valid coordinates: {has_coords} / {len(elements)} ({has_coords/len(elements)*100:.1f}%)")
