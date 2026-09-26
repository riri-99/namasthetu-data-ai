import httpx

query = """[out:json][timeout:60];
(
  area["name:en"="Indore"]->.searchArea;
  nwr["place"](area.searchArea);
  nwr["landuse"="residential"](area.searchArea);
  nwr["building"](area.searchArea);
);
out count;
"""

headers = {"User-Agent": "AmberstoneIndorePipeline/1.0"}
resp = httpx.post("https://maps.mail.ru/osm/tools/overpass/api/interpreter", data={"data": query}, headers=headers, timeout=45.0)
print("Indore area query status:", resp.status_code)
if resp.status_code == 200:
    print(resp.json())
