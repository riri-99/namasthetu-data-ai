import json
import re
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("data_fetch/corridor_indore/indore_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

DISCARD_TERMS = {
    "police", "station", "post office", "parking", "store", "traders", "hospital",
    "clinic", "dental", "school", "college", "bus stop", "ibus", "railway", "chowk",
    "square", "temple", "mandir", "masjid", "dargah", "petrol", "fuel", "atm",
    "bank", "hotel", "restaurant", "cafe", "dhaba", "hall", "gate", "garden - main",
    "stadium", "market", "bazaar"
}

def is_residential_indore(name: str, tags: dict) -> bool:
    lower = name.lower()
    if any(b in lower for b in DISCARD_TERMS):
        return False
    if tags.get("amenity") in ["hospital", "clinic", "school", "police", "place_of_worship", "bank", "fuel"]:
        return False
    if tags.get("shop"):
        return False
    # Check if place=neighbourhood/suburb or building=apartments/residential
    if tags.get("place") in ["neighbourhood", "suburb", "quarter"]:
        return True
    if tags.get("building") in ["apartments", "residential", "yes", "house"]:
        return True
    if tags.get("landuse") == "residential":
        return True
    # Or matches residential name keywords
    res_pattern = r'(?i)\b(nagar|colony|township|city|enclave|villas?|heights|apartments?|residency|parisar|kunj|srishti|vihar|pride|greens|palace|estates?|paradise|park|scheme\s*\d+|sector|avenue|meadows|springs|dham|complex|homes?|oaks|sharan|county|bliss)\b'
    return bool(re.search(res_pattern, lower))

clean_societies = []
for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name:en") or tags.get("name", "").strip()
    if not name:
        continue
    if is_residential_indore(name, tags):
        clean_societies.append((name, el.get("lat") or el.get("center", {}).get("lat"), el.get("lon") or el.get("center", {}).get("lon")))

print(f"Total elements: {len(elements)}")
print(f"Clean residential societies/colonies: {len(clean_societies)}")
print("\nSample Clean Indore Societies:")
for n, lat, lon in clean_societies[:20]:
    print(f" - {n:<45} ({lat:.4f}, {lon:.4f})")
