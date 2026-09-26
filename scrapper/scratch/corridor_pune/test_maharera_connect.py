import httpx

urls = [
    "https://maharera.maharashtra.gov.in/",
    "https://maharerait.mahaonline.gov.in/SearchList/Search"
]

for u in urls:
    try:
        r = httpx.get(u, timeout=10.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        print(f"{u} -> {r.status_code}")
    except Exception as e:
        print(f"{u} -> Error: {e}")
