import httpx
from lxml import html

url = "https://maharera.maharashtra.gov.in/projects-search-result"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

r = httpx.get(url, headers=headers, timeout=15.0)
tree = html.fromstring(r.content)

sel = tree.xpath("//select[@id='edit-project-district']")
if sel:
    for opt in sel[0].xpath(".//option"):
        print(opt.get("value"), "->", opt.text_content().strip())
