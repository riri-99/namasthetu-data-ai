import json
import re
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("data_fetch/corridor_indore/indore_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

print(f"Total Indore elements loaded: {len(elements)}")

INDORE_DEVELOPERS = [
    ("Brilliant Group", ["Brilliant", "Solitaire"]),
    ("Skye Earth Developers", ["Skye", "Skye Luxuria", "Skye Earth"]),
    ("Apollo Group", ["Apollo", "Apollo DB City", "Apollo Premier"]),
    ("Chordia Group / Treasure", ["Treasure", "Treasure Fantasy", "Treasure Vihar"]),
    ("Omaxe Limited", ["Omaxe", "Omaxe City", "Omaxe Hills"]),
    ("Silver Springs", ["Silver Springs"]),
    ("BCM Group", ["BCM", "BCM Heights", "BCM Paradise", "BCM Park"]),
    ("Kalindi Developers", ["Kalindi", "Kalindi Gold", "Kalindi Mid Town"]),
    ("Shreeram Builders", ["Shreeram", "Shreeram Sharan"]),
    ("DB Group", ["DB Pride", "DB City"]),
    ("Sarthak Singapore Group", ["Singapore", "Singapore Township", "Singapore City"]),
    ("Casa Greens", ["Casa Greens", "Casa"]),
    ("Royal Amar Group", ["Royal Amar", "Royal Amar Greens"]),
    ("Shalimar Group", ["Shalimar", "Shalimar Township", "Shalimar Palms"]),
    ("Pinnacle Group", ["Pinnacle", "Pinnacle D Dreams"]),
]

has_name = 0
dev_counts = Counter()
sample_societies = []

for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name:en") or tags.get("name", "").strip()
    if not name:
        continue
    has_name += 1
    
    dev_match = None
    for dname, aliases in INDORE_DEVELOPERS:
        for alias in aliases:
            if re.search(rf'(?i)\b{re.escape(alias)}\b', name):
                dev_match = dname
                break
        if dev_match:
            break
            
    if dev_match:
        dev_counts[dev_match] += 1
        
    if len(sample_societies) < 25:
        sample_societies.append((name, dev_match, tags.get("building:levels", "N/A")))

print(f"Elements with valid name: {has_name} / {len(elements)}")
print(f"Societies with developer brand: {sum(dev_counts.values())}")
print("\nTop Developer Brands in Indore:")
for d, c in dev_counts.most_common(10):
    print(f" - {d:<26}: {c}")

print("\nSample Societies & Townships in Indore:")
for name, dev, lvl in sample_societies:
    dev_str = f" [Dev: {dev}]" if dev else ""
    print(f" - {name:<40}{dev_str}")
