import httpx
from lxml import html

try:
    r = httpx.get("https://maharera.maharashtra.gov.in/", timeout=15.0, headers={"User-Agent": "Mozilla/5.0"})
    tree = html.fromstring(r.content)
    for a in tree.xpath("//a[@href]"):
        href = a.get("href", "")
        text = a.text_content().strip()
        if any(w in text.lower() or w in href.lower() for w in ["search", "project", "registered", "pune", "dataset"]):
            print(f"Text: {text} | Href: {href}")
except Exception as e:
    print("Error:", e)
