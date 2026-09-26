import json
import sys
import re
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("data_fetch/corridor_dubai/dubai_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

print(f"Total Dubai elements loaded: {len(elements)}")

# Check developer keywords in Dubai
DUBAI_DEVELOPERS = [
    ("Emaar Properties", ["Emaar", "Burj", "The Address", "Vida", "Downtown", "Dubai Hills", "Arabian Ranches", "Creek Horizon"]),
    ("DAMAC Properties", ["Damac", "Damac Hills", "Akoya", "Paramount"]),
    ("Sobha Realty", ["Sobha", "Sobha Hartland", "Hartland"]),
    ("Omniyat", ["Omniyat", "The Opus", "One Palm", "Ava", "Vela", "Dorchester"]),
    ("Meraas", ["Meraas", "City Walk", "Bluewaters", "Port De La Mer", "Nikki Beach", "Bvlgari", "Bulgari"]),
    ("Nakheel", ["Nakheel", "Palm Jumeirah", "Jumeirah Islands", "Discovery Gardens", "Jumeirah Park"]),
    ("Select Group", ["Select Group", "Marina Gate", "Jumeirah Living Marina Gate", "Peninsula", "The Residence"]),
    ("Ellington Properties", ["Ellington", "Belgravia", "DT1", "Wilton", "Oakwood", "Somerset"]),
    ("Binghatti Developers", ["Binghatti", "Burj Binghatti", "Jacob & Co"]),
    ("Danube Properties", ["Danube", "Glitz", "Miraclz", "Jewelz", "Wavez", "Opalz", "Petalz"]),
    ("MAG Property Development", ["MAG", "MAG 214", "MAG 5", "MAG Eye"]),
    ("Seven Tides", ["Seven Tides", "Seven Palm", "Anantara Residences"]),
    ("Deyaar", ["Deyaar", "Midtown", "Mont Rose", "The Atria", "Ruby"]),
    ("Aldar", ["Aldar"]),
    ("Wasl Properties", ["Wasl", "Wasl1", "Park Gate", "1 Residences"]),
    ("Azizi Developments", ["Azizi", "Riviera", "Mina", "Aliyah", "Farishta"]),
    ("Al Futtaim", ["Al Futtaim", "Al Badia", "Marsa Plaza"]),
]

def is_valid_dubai_society(name: str) -> bool:
    name_clean = name.strip()
    if len(name_clean) < 3:
        return False
    # Reject pure code patterns like "EB 1", "SB 3", "F06", "JB 8", "Building 186"
    if re.match(r'(?i)^[a-z]{1,2}\s*\d+$', name_clean):
        return False
    if re.match(r'(?i)^building\s+\d+', name_clean):
        return False
    return True

valid_count = 0
dev_counts = Counter()
sample_luxury = []

for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name:en") or tags.get("name", "").strip()
    if not is_valid_dubai_society(name):
        continue
    valid_count += 1
    
    # Detect developer
    matched_dev = None
    for dev_name, aliases in DUBAI_DEVELOPERS:
        for alias in aliases:
            if re.search(rf'(?i)\b{re.escape(alias)}\b', name):
                matched_dev = dev_name
                break
        if matched_dev:
            break
            
    if matched_dev:
        dev_counts[matched_dev] += 1
        if len(sample_luxury) < 20:
            sample_luxury.append((name, matched_dev, tags.get("building:levels", "N/A")))

print(f"Valid residential societies/towers: {valid_count} / {len(elements)}")
print(f"Societies with attributed developer brands: {sum(dev_counts.values())}")
print("\nTop Developer Brands in Dubai:")
for d, c in dev_counts.most_common(15):
    print(f" - {d:<26}: {c}")

print("\nSample Developer-Attributed Luxury Towers:")
for name, dev, lvl in sample_luxury:
    print(f" - {name:<40} | Dev: {dev:<20} | Levels: {lvl}")
