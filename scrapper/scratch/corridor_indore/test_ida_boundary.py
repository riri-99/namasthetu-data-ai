import httpx

query = """[out:json][timeout:60];
(
  nwr["place"~"neighbourhood|suburb|quarter|village|hamlet"](22.50,75.70,22.92,76.10);
  nwr["landuse"="residential"]["name"](22.50,75.70,22.92,76.10);
  nwr["residential"]["name"](22.50,75.70,22.92,76.10);
  nwr["building"]["name"](22.50,75.70,22.92,76.10);
  nwr["name"~"Nagar|Colony|Township|City|Enclave|Villas|Heights|Apartments|Residency|Parisar|Kunj|Srishti|Vihar|Pride|Greens|Palace|Estates|Paradise|Park|Scheme|Sector|Garden|Avenue|Meadows|Springs|Shree|Shri|Dham|Complex|Square|Clarks|County|Nest|Horizon|Palm|Oasis|Crown|Heritage|Vatika|Grah|Kuteer|Kunj|Lawn|Tower",i](22.50,75.70,22.92,76.10);
);
out count;
"""

headers = {"User-Agent": "AmberstoneIndorePipeline/1.0"}
resp = httpx.post("https://maps.mail.ru/osm/tools/overpass/api/interpreter", data={"data": query}, headers=headers, timeout=45.0)
print("Expanded IDA boundary count status:", resp.status_code)
if resp.status_code == 200:
    print(resp.json())
