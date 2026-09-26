import httpx
import json
import time
from pathlib import Path

# Mumbai Metropolitan Region bounding box
# 18.89 to 19.32 lat, 72.77 to 73.08 lon
query = """[out:json][timeout:90];
(
  nwr["building"="apartments"]["name"](18.89,72.77,19.32,73.08);
  nwr["building"="residential"]["name"](18.89,72.77,19.32,73.08);
  nwr["residential"="gated_community"]["name"](18.89,72.77,19.32,73.08);
  nwr["landuse"="residential"]["name"](18.89,72.77,19.32,73.08);
);
out center tags;
"""

headers = {"User-Agent": "AmberstoneMumbaiPipeline/1.0 (contact@amberstone.com)"}
mirrors = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

output_path = Path("data_fetch/corridor_mumbai/mumbai_osm_raw.json")
output_path.parent.mkdir(parents=True, exist_ok=True)

data = None
for mirror in mirrors:
    try:
        print(f"Querying {mirror} for Mumbai residential societies & towers...")
        t0 = time.time()
        resp = httpx.post(mirror, data={"data": query}, headers=headers, timeout=90.0)
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
