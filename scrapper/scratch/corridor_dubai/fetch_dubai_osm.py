import httpx
import json
import time
from pathlib import Path

# Bounding box for Dubai Emirate urban corridor
# 24.80 to 25.35 lat, 54.95 to 55.60 lon
query = """[out:json][timeout:60];
(
  nwr["building"="apartments"]["name"](24.80,54.95,25.35,55.60);
  nwr["building"="residential"]["name"](24.80,54.95,25.35,55.60);
  nwr["residential"="gated_community"]["name"](24.80,54.95,25.35,55.60);
  nwr["landuse"="residential"]["name"](24.80,54.95,25.35,55.60);
);
out center tags;
"""

headers = {"User-Agent": "AmberstoneDubaiDataPipeline/1.0 (contact@amberstone.com)"}
mirrors = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

output_path = Path("data_fetch/corridor_dubai/dubai_osm_raw.json")
output_path.parent.mkdir(parents=True, exist_ok=True)

data = None
for mirror in mirrors:
    try:
        print(f"Querying {mirror} for Dubai residential towers & communities...")
        t0 = time.time()
        resp = httpx.post(mirror, data={"data": query}, headers=headers, timeout=75.0)
        print(f"Status: {resp.status_code} in {time.time()-t0:.2f}s")
        if resp.status_code == 200:
            data = resp.json()
            break
    except Exception as e:
        print(f"Mirror {mirror} error: {e}")

if data:
    elements = data.get("elements", [])
    print(f"Total elements retrieved: {len(elements)}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_path}")
else:
    print("Failed to fetch from all mirrors.")
