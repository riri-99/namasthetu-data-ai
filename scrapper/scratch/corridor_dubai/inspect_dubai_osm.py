import json
from collections import Counter

with open("data_fetch/corridor_dubai/dubai_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

print(f"Total Dubai elements loaded: {len(elements)}")

tag_keys = Counter()
building_types = Counter()
has_levels = 0
has_street = 0
has_name = 0
has_coords = 0
sample_names = []

for el in elements:
    tags = el.get("tags", {})
    for k in tags.keys():
        tag_keys[k] += 1
    
    btype = tags.get("building") or tags.get("landuse") or tags.get("residential")
    building_types[btype] += 1
    
    if "name" in tags:
        has_name += 1
        if len(sample_names) < 25:
            sample_names.append((tags["name"], tags.get("building:levels", "N/A"), tags.get("addr:street", "")))
    if "building:levels" in tags:
        has_levels += 1
    if "addr:street" in tags:
        has_street += 1
    lat = el.get("lat") or (el.get("center", {}).get("lat"))
    lon = el.get("lon") or (el.get("center", {}).get("lon"))
    if lat and lon:
        has_coords += 1

print(f"Has name: {has_name}")
print(f"Has coordinates: {has_coords} ({has_coords/len(elements)*100:.1f}%)")
print(f"Has levels/floors: {has_levels}")
print(f"Has street: {has_street}")
print("\nTop 10 building types:", building_types.most_common(10))
print("\nTop 15 tag keys:", tag_keys.most_common(15))
print("\nSample names:")
for name, lvl, st in sample_names:
    print(f" - {name:<35} | Levels: {lvl:<4} | Street: {st}")
