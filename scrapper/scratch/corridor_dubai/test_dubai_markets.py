import json
import sys
import re
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUBAI_MICRO_MARKETS = {
    # Ultra-Prime & Waterfront Enclaves
    "Palm Jumeirah":             (25.0950, 55.1150, 25.1550, 55.1700),
    "Bluewaters Island":         (25.0750, 55.1150, 25.0900, 55.1300),
    "Jumeirah Bay Island":       (25.2150, 55.2400, 25.2350, 55.2600),
    "Dubai Marina":              (25.0650, 55.1200, 25.0980, 55.1550),
    "JBR (Jumeirah Beach Res.)": (25.0720, 55.1250, 25.0880, 55.1420),
    "Port De La Mer & Pearl Jumeirah": (25.2400, 55.2500, 25.2750, 55.2750),
    "Madinat Jumeirah Living & Umm Suqeim": (25.1300, 55.1800, 25.1700, 55.2250),
    "Jumeirah (1, 2, 3)":        (25.1700, 55.2200, 25.2400, 55.2700),

    # Downtown, Financial & Central Luxury
    "Downtown Dubai":            (25.1800, 55.2600, 25.2100, 55.2950),
    "DIFC":                      (25.2000, 55.2700, 25.2250, 55.2950),
    "Business Bay":              (25.1700, 55.2500, 25.1950, 55.2850),
    "City Walk & Al Wasl":       (25.1950, 55.2500, 25.2150, 55.2750),
    "Za'abeel & Wasl1":          (25.2150, 55.2850, 25.2400, 55.3150),
    "Dubai Creek Harbour":       (25.1850, 55.3400, 25.2150, 55.3750),
    "Dubai Water Canal & Al Safa": (25.1750, 55.2350, 25.1950, 55.2600),

    # Golf & Master Gated Enclaves
    "Emirates Hills":            (25.0650, 55.1500, 25.0950, 55.1850),
    "The Views, Greens & Lakes": (25.0850, 55.1600, 25.1050, 55.1850),
    "The Meadows & Springs":     (25.0450, 55.1550, 25.0800, 55.1900),
    "Dubai Hills Estate":        (25.0900, 55.2350, 25.1300, 55.2750),
    "District One (MBR City)":   (25.1500, 55.2800, 25.1850, 55.3200),
    "Sobha Hartland & Meydan":   (25.1600, 55.2950, 25.1900, 55.3350),
    "Jumeirah Golf Estates":     (25.0150, 55.1900, 25.0500, 55.2300),
    "Al Barari":                 (25.0900, 55.3050, 25.1200, 55.3400),
    "Tilal Al Ghaf":             (25.0150, 55.2200, 25.0450, 55.2550),
    "Arabian Ranches (I, II, III)": (25.0450, 55.2500, 25.0900, 55.3300),
    "Damac Hills & Lagoons":     (24.9900, 55.2300, 25.0450, 55.2800),

    # High-Density Prime & Coastal Towers
    "Jumeirah Lake Towers (JLT)":(25.0650, 55.1350, 25.0880, 55.1600),
    "Al Sufouh & Media City":    (25.0950, 55.1550, 25.1250, 55.1950),
    "Jumeirah Village Circle (JVC)": (25.0450, 55.1950, 25.0750, 55.2250),
    "Jumeirah Village Triangle (JVT)": (25.0350, 55.1750, 25.0600, 55.2050),
    "Dubai Sports City & Motor City": (25.0300, 55.2100, 25.0550, 55.2450),
    "Al Furjan & Discovery Gardens": (25.0250, 55.1250, 25.0550, 55.1600),
    "Dubai Silicon Oasis & Liwan": (25.1100, 55.3650, 25.1450, 55.4050),
    "Dubai Festival City & Culture Village": (25.2100, 55.3200, 25.2400, 55.3700),
    "Bur Dubai & Deira Waterfront": (25.2400, 55.2800, 25.2800, 55.3400),
}

with open("data_fetch/corridor_dubai/dubai_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

def is_valid_name(name):
    if len(name) < 3:
        return False
    if re.match(r'(?i)^[a-z]{1,2}\s*\d+$', name):
        return False
    if re.match(r'(?i)^building\s+\d+', name):
        return False
    return True

market_counts = Counter()
unassigned = 0

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
            
    if matched:
        market_counts[matched] += 1
    else:
        unassigned += 1

print(f"Total valid societies: {sum(market_counts.values()) + unassigned}")
print(f"Matched to prime Dubai micro-markets: {sum(market_counts.values())} ({sum(market_counts.values())/(sum(market_counts.values())+unassigned)*100:.1f}%)")
print(f"Unassigned / Greater Dubai: {unassigned}")
print("\nDubai Micro-Market Breakdown:")
for m, c in market_counts.most_common():
    print(f" - {m:<38}: {c}")
