import json
from collections import Counter

EXPANDED_PUNE_MARKETS = {
    # Ultra Prime & Heritage Central
    "Koregaon Park":             (18.5300, 73.8800, 18.5520, 73.9120),
    "Boat Club Road":            (18.5250, 73.8700, 18.5450, 73.8950),
    "Kalyani Nagar":             (18.5400, 73.8950, 18.5620, 73.9200),
    "Sopan Baug & BT Kawade":    (18.5050, 73.8900, 18.5250, 73.9200),
    "Prabhat Road & Erandwane":  (18.5000, 73.8200, 18.5250, 73.8450),
    "Bhandarkar & Law College":  (18.5150, 73.8250, 18.5300, 73.8450),
    "Model Colony & Shivaji Ngr":(18.5250, 73.8300, 18.5450, 73.8550),
    "Senapati Bapat Road":       (18.5250, 73.8200, 18.5450, 73.8400),
    "Camp & Pune Cantonment":    (18.5000, 73.8650, 18.5250, 73.8900),
    "Salisbury Park & Gultekdi": (18.4850, 73.8600, 18.5050, 73.8850),
    "Mukund Nagar & Swargate":   (18.4900, 73.8450, 18.5100, 73.8650),

    # Prime Western Corridors
    "Aundh & Sindh Society":     (18.5500, 73.7950, 18.5750, 73.8350),
    "Baner & Pan Card Club Rd":  (18.5400, 73.7650, 18.5750, 73.8050),
    "Balewadi & High Street":    (18.5650, 73.7600, 18.5900, 73.7950),
    "Bavdhan & Chandani Chowk":  (18.4950, 73.7600, 18.5300, 73.7950),
    "Kothrud & Paud Road":       (18.4900, 73.7900, 18.5250, 73.8300),
    "Pashan & Sus Road":         (18.5300, 73.7600, 18.5550, 73.7950),
    "Hinjewadi (Phases 1-3)":    (18.5750, 73.6950, 18.6150, 73.7500),
    "Wakad":                     (18.5850, 73.7450, 18.6150, 73.7850),
    "Pimple Saudagar & Rahatani":(18.5850, 73.7850, 18.6150, 73.8150),
    "Pimple Nilakh & Vishal Ngr":(18.5650, 73.7800, 18.5850, 73.8050),
    "Thergaon & Kalewadi":       (18.6050, 73.7700, 18.6250, 73.8000),
    "Tathawade & Punawale":      (18.6100, 73.7350, 18.6350, 73.7750),
    "Ravet & Kiwale":            (18.6300, 73.7250, 18.6650, 73.7650),

    # Prime Eastern Corridors
    "Kharadi & EON IT Corridor": (18.5400, 73.9250, 18.5700, 73.9700),
    "Viman Nagar":               (18.5550, 73.9000, 18.5780, 73.9300),
    "Wadgaon Sheri & Kalyani Ext":(18.5400, 73.9150, 18.5600, 73.9350),
    "Keshav Nagar & Mundhwa":    (18.5250, 73.9150, 18.5450, 73.9550),
    "Magarpatta City & Hadapsar":(18.4950, 73.9150, 18.5300, 73.9600),
    "Amanora Park Town":         (18.5100, 73.9300, 18.5250, 73.9500),
    "Wagholi & Bakori Road":     (18.5650, 73.9700, 18.6100, 74.0200),

    # Northern Corridors
    "Dhanori, Lohegaon & Porwal":(18.5750, 73.8800, 18.6200, 73.9350),
    "Tingre Nagar & Vishrantwadi":(18.5600, 73.8650, 18.5850, 73.8900),
    "Dighi & Alandi Road":       (18.6050, 73.8600, 18.6400, 73.8950),
    "Bhosari & Indrayani Nagar": (18.6150, 73.8350, 18.6500, 73.8700),
    "Pimpri & Chinchwad Station":(18.6200, 73.7850, 18.6450, 73.8350),
    "Nigdi & Pradhikaran":       (18.6400, 73.7500, 18.6750, 73.7900),

    # Southern & Hills Corridors
    "Wanowrie & Fatima Nagar":   (18.4850, 73.8850, 18.5150, 73.9150),
    "NIBM Road & Undri":         (18.4600, 73.8800, 18.4950, 73.9350),
    "Kondhwa & Lullanagar":      (18.4700, 73.8700, 18.4950, 73.8950),
    "Bibwewadi & Market Yard":   (18.4650, 73.8500, 18.4900, 73.8750),
    "Sinhagad Road & Manik Baug":(18.4700, 73.8150, 18.5000, 73.8450),
    "Dhayari & Narhe":           (18.4350, 73.8050, 18.4700, 73.8350),
}

with open("data_fetch/pune_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

counts = Counter()
unassigned = 0

for el in elements:
    lat = el.get("lat") or (el.get("center", {}).get("lat"))
    lon = el.get("lon") or (el.get("center", {}).get("lon"))
    matched = None
    for name, (s, w, n, e) in EXPANDED_PUNE_MARKETS.items():
        if s <= lat <= n and w <= lon <= e:
            matched = name
            break
    if matched:
        counts[matched] += 1
    else:
        unassigned += 1

print(f"Total: {len(elements)}")
print(f"Matched with expanded markets: {sum(counts.values())} ({sum(counts.values())/len(elements)*100:.1f}%)")
print(f"Unassigned: {unassigned}")
