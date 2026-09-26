import json
from collections import Counter

# Define Pune micro-market bounding boxes with buffer
PUNE_MICRO_MARKETS = {
    "Koregaon Park":             (18.5300, 73.8800, 18.5520, 73.9120),
    "Boat Club Road":            (18.5250, 73.8700, 18.5450, 73.8950),
    "Kalyani Nagar":             (18.5400, 73.8950, 18.5620, 73.9200),
    "Sopan Baug & BT Kawade":    (18.5050, 73.8900, 18.5250, 73.9200),
    "Prabhat Road & Erandwane":  (18.5000, 73.8200, 18.5250, 73.8450),
    "Bhandarkar & Law College":  (18.5150, 73.8250, 18.5300, 73.8450),
    "Model Colony & Shivaji Ngr":(18.5250, 73.8300, 18.5450, 73.8550),
    "Senapati Bapat Road":       (18.5250, 73.8200, 18.5450, 73.8400),
    "Salisbury Park & Gultekdi": (18.4850, 73.8600, 18.5050, 73.8850),
    "Aundh & Sindh Society":     (18.5500, 73.7950, 18.5750, 73.8250),
    "Baner & Pan Card Club Rd":  (18.5450, 73.7700, 18.5750, 73.8050),
    "Balewadi & High Street":    (18.5650, 73.7650, 18.5900, 73.7950),
    "Bavdhan & Chandani Chowk":  (18.5000, 73.7600, 18.5300, 73.7900),
    "Kothrud & Paud Road":       (18.4900, 73.7950, 18.5200, 73.8300),
    "Hinjewadi (Phases 1-3)":    (18.5750, 73.6950, 18.6150, 73.7500),
    "Wakad":                     (18.5850, 73.7500, 18.6150, 73.7850),
    "Pimple Saudagar & Rahatani":(18.5850, 73.7850, 18.6100, 73.8150),
    "Kharadi & EON IT Corridor": (18.5400, 73.9300, 18.5700, 73.9700),
    "Viman Nagar":               (18.5550, 73.9050, 18.5780, 73.9300),
    "Magarpatta City & Hadapsar":(18.4950, 73.9150, 18.5300, 73.9550),
    "Amanora Park Town":         (18.5100, 73.9300, 18.5250, 73.9500),
    "NIBM Road & Undri":         (18.4600, 73.8850, 18.4950, 73.9350),
    "Wanowrie & Fatima Nagar":   (18.4900, 73.8850, 18.5150, 73.9100),
    "Pashan & Sus Road":         (18.5300, 73.7650, 18.5550, 73.7950),
    "Tathawade & Punawale":      (18.6100, 73.7400, 18.6350, 73.7750),
    "Ravet & Kiwale":            (18.6300, 73.7300, 18.6650, 73.7650),
    "Moshi & Alandi Road":       (18.6500, 73.8400, 18.6850, 73.8800),
}

with open("data_fetch/pune_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

market_counts = Counter()
unassigned = 0

def find_market(lat, lon):
    for name, (s, w, n, e) in PUNE_MICRO_MARKETS.items():
        if s <= lat <= n and w <= lon <= e:
            return name
    return None

for el in elements:
    lat = el.get("lat") or (el.get("center", {}).get("lat"))
    lon = el.get("lon") or (el.get("center", {}).get("lon"))
    tags = el.get("tags", {})
    
    market = find_market(lat, lon)
    if not market:
        # Check if addr:street or addr:district mentions anything
        addr = f"{tags.get('addr:street', '')} {tags.get('addr:district', '')} {tags.get('addr:suburb', '')}"
        for m in PUNE_MICRO_MARKETS.keys():
            if m.lower() in addr.lower():
                market = m
                break
    
    if market:
        market_counts[market] += 1
    else:
        unassigned += 1

print(f"Total elements: {len(elements)}")
print(f"Assigned to Prime Micro-Markets: {sum(market_counts.values())} ({sum(market_counts.values())/len(elements)*100:.1f}%)")
print(f"Unassigned / Greater Pune: {unassigned}")
print("\nMicro-Market Breakdown:")
for m, c in market_counts.most_common():
    print(f" - {m:<28}: {c}")
