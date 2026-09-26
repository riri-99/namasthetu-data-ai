import httpx

query = """[out:json][timeout:60];
(
  nwr["place"~"neighbourhood|suburb|quarter|village"](22.55,75.72,22.88,76.05);
  nwr["landuse"="residential"]["name"](22.55,75.72,22.88,76.05);
  nwr["residential"]["name"](22.55,75.72,22.88,76.05);
  nwr["building"]["name"](22.55,75.72,22.88,76.05);
  nwr["name"~"Nagar|Colony|Township|City|Enclave|Villas|Heights|Apartments|Residency|Parisar|Kunj|Srishti|Vihar|Pride|Greens|Palace|Estates|Paradise|Park|Scheme|Sector|Garden|Avenue|Meadows|Springs|Shree|Shri|Dham|Complex|Square|Clarks|County|Nest|Horizon|Palm|Oasis|Crown|Heritage",i](22.55,75.72,22.88,76.05);
);
out count;
"""

headers = {"User-Agent": "AmberstoneIndoreResearch/1.0"}
resp = httpx.post("https://maps.mail.ru/osm/tools/overpass/api/interpreter", data={"data": query}, headers=headers, timeout=60.0)
print("Indore expanded query status:", resp.status_code)
if resp.status_code == 200:
    print("Response:", resp.json())
