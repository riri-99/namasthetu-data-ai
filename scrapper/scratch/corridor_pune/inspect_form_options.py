import httpx
from lxml import html

url = "https://maharera.maharashtra.gov.in/projects-search-result"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

r = httpx.get(url, headers=headers, timeout=15.0)
tree = html.fromstring(r.content)

districts = tree.xpath("//select[@name='project_district']/option")
for opt in districts:
    val = opt.get("value")
    text = opt.text_content().strip()
    if "pune" in text.lower():
        print(f"District option: {val} -> {text}")

types = tree.xpath("//select[@name='project_type']/option")
for opt in types:
    print(f"Type option: {opt.get('value')} -> {opt.text_content().strip()}")
