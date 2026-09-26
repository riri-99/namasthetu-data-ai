import httpx
import json
import time

query = """[out:json][timeout:60];
(
  nwr["building"="apartments"]["name"](18.40,73.70,18.68,74.02);
  nwr["building"="residential"]["name"](18.40,73.70,18.68,74.02);
  nwr["residential"="gated_community"]["name"](18.40,73.70,18.68,74.02);
  nwr["landuse"="residential"]["name"](18.40,73.70,18.68,74.02);
);
out center tags;
"""

headers = {"User-Agent": "AmberstoneDataPipeline/1.0 (contact@amberstone.com)"}
mirrors = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

data = None
for mirror in mirrors:
    try:
        print(f"Querying {mirror} for Pune residential elements...")
        t0 = time.time()
        resp = httpx.post(mirror, data={"data": query}, headers=headers, timeout=60.0)
        print(f"Status: {resp.status_code} in {time.time()-t0:.2f}s")
        if resp.status_code == 200:
            data = resp.json()
            break
    except Exception as e:
        print(f"Mirror {mirror} error: {e}")

if data:
    elements = data.get("elements", [])
    print(f"Total elements retrieved: {len(elements)}")
    with open("data_fetch/pune_osm_raw.json", "w", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print("Saved to data_fetch/pune_osm_raw.json")
else:
    print("Failed to fetch from all mirrors.")
