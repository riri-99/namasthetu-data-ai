import httpx
import json
import time
from pathlib import Path

# Indore IDA Metropolitan Master Plan boundary
query = """[out:json][timeout:90];
(
  nwr["place"~"neighbourhood|suburb|quarter|village|hamlet"](22.50,75.70,22.92,76.10);
  nwr["landuse"="residential"]["name"](22.50,75.70,22.92,76.10);
  nwr["residential"]["name"](22.50,75.70,22.92,76.10);
  nwr["building"]["name"](22.50,75.70,22.92,76.10);
  nwr["name"~"Nagar|Colony|Township|City|Enclave|Villas|Heights|Apartments|Residency|Parisar|Kunj|Srishti|Vihar|Pride|Greens|Palace|Estates|Paradise|Park|Scheme|Sector|Garden|Avenue|Meadows|Springs|Shree|Shri|Dham|Complex|Square|Clarks|County|Nest|Horizon|Palm|Oasis|Crown|Heritage|Vatika|Grah|Kuteer|Kunj|Lawn|Tower",i](22.50,75.70,22.92,76.10);
);
out center tags;
"""

headers = {"User-Agent": "AmberstoneIndorePipeline/1.0 (contact@amberstone.com)"}
mirrors = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

output_path = Path("data_fetch/corridor_indore/indore_osm_raw.json")
output_path.parent.mkdir(parents=True, exist_ok=True)

data = None
for mirror in mirrors:
    try:
        print(f"Querying {mirror} for Indore residential elements...")
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
