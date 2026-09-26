import httpx
from lxml import html

url = "https://maharera.maharashtra.gov.in/projects-search-result"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

try:
    r = httpx.get(url, headers=headers, timeout=15.0)
    print("Status:", r.status_code)
    tree = html.fromstring(r.content)
    # Check forms and inputs
    forms = tree.xpath("//form")
    print(f"Found {len(forms)} forms")
    for f in forms:
        print("Action:", f.get("action"))
        inputs = f.xpath(".//input | .//select")
        print("Inputs:", [i.get("name") for i in inputs if i.get("name")])
except Exception as e:
    print("Error:", e)
