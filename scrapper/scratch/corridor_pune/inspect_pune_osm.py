import json
from collections import Counter

with open("data_fetch/pune_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

print(f"Total elements loaded: {len(elements)}")

tag_keys = Counter()
building_types = Counter()
has_levels = 0
has_street = 0
has_city = 0
has_postcode = 0
has_name = 0

sample_names = []

for el in elements:
    tags = el.get("tags", {})
    for k in tags.keys():
        tag_keys[k] += 1
    
    btype = tags.get("building") or tags.get("landuse") or tags.get("residential")
    building_types[btype] += 1
    
    if "name" in tags:
        has_name += 1
        if len(sample_names) < 15:
            sample_names.append(tags["name"])
    if "building:levels" in tags:
        has_levels += 1
    if "addr:street" in tags:
        has_street += 1
    if "addr:city" in tags:
        has_city += 1
    if "addr:postcode" in tags:
        has_postcode += 1

print(f"Has name: {has_name}")
print(f"Has levels: {has_levels}")
print(f"Has street: {has_street}")
print(f"Has city: {has_city}")
print(f"Has postcode: {has_postcode}")
print("\nTop 10 building types:", building_types.most_common(10))
print("\nTop 15 tag keys:", tag_keys.most_common(15))
print("\nSample names:")
for n in sample_names:
    print(" -", n)
