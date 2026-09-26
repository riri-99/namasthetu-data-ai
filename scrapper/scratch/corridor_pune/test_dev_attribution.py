import json
import re
import unicodedata
from collections import Counter

PUNE_DEVELOPERS = [
    # Tier 1 Ultra-Luxury Developers
    ("Panchshil", ["Panchshil", "Trump Tower", "Trump Towers", "Yoo Pune", "One North", "Waterfront"]),
    ("Marvel", ["Marvel", "Marvel Realtors"]),
    ("Kasturi", ["Kasturi", "The Balmoral", "Balmoral Estate", "Apostrophe"]),
    ("Rohan", ["Rohan", "Rohan Builders"]),
    ("Gera", ["Gera", "Gera Developments"]),
    ("Kolte-Patil", ["Kolte-Patil", "Kolte Patil", "24K", "Glitterati", "Life Republic"]),
    ("K Raheja Corp", ["Raheja", "K Raheja"]),
    ("Kalpataru", ["Kalpataru"]),
    ("Godrej", ["Godrej", "Godrej Properties"]),
    ("Vascon", ["Vascon", "Vascon Engineers", "Windermere"]),
    ("BramhaCorp", ["BramhaCorp", "Bramha", "Bramha SunCity", "F-Residences"]),
    ("Amanora", ["Amanora", "Gateway Towers", "Sweet Water"]),
    ("Pride Group", ["Pride", "Pride Purple", "Pride World City"]),
    ("VTP Realty", ["VTP", "VTP Realty"]),
    ("Nyati", ["Nyati", "Nyati Group"]),
    ("Kumar Properties", ["Kumar", "Kumar Properties", "Kumar Privie"]),
    ("Paranjape", ["Paranjape", "Blue Ridge", "Megapolis"]),
    ("Shapoorji Pallonji", ["Shapoorji", "Joyville"]),
    ("Sobha", ["Sobha"]),
    ("Mahindra Lifespaces", ["Mahindra", "Mahindra Lifespaces"]),
    ("Lunkad", ["Lunkad", "Lunkad Realty"]),
    ("Goel Ganga", ["Goel Ganga", "Ganga"]),
    ("Phadnis", ["Phadnis", "Eastern Meadows"]),
    ("Mont Vert", ["Mont Vert"]),
    ("Kundan", ["Kundan Spaces"]),
    ("Bhandari", ["Bhandari Associates"]),
    ("Mittal", ["Mittal Brothers"]),
    ("Choice Group", ["Choice Group", "Goodrich"]),
    ("Runwal", ["Runwal"]),
    ("Karia", ["Karia Builders", "Konark"]),
]

def clean_society_name(raw_name: str) -> str:
    """Cleans suffixes like CHS, Co-op Housing Society Ltd, Wing A, etc."""
    name = raw_name.strip()
    # Remove Marathi / regional script if English name exists in tag or mixed
    # Normalize common suffixes
    name = re.sub(r'(?i)\b(co[\s\-\.]*operative|co[\s\-\.]*op)\b.*$', '', name)
    name = re.sub(r'(?i)\b(c\.?h\.?s\.?l?|c\.?h\.?s\.?)\b.*$', '', name)
    name = re.sub(r'(?i)\b(housing\s+society)\b.*$', '', name)
    name = re.sub(r'(?i)\b(society\s+ltd\.?|society)\b.*$', '', name)
    name = re.sub(r'(?i)\s+wing[\s\-\_]*[a-z0-9]+', '', name)
    name = re.sub(r'(?i)\s+tower[\s\-\_]*[a-z0-9]+', '', name)
    name = re.sub(r'(?i)\s+building[\s\-\_]*[a-z0-9]+', '', name)
    name = re.sub(r'(?i)\s+phase[\s\-\_]*[ivx0-9]+', '', name)
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name)
    name = re.sub(r'\s+', ' ', name).strip(' ,.-')
    return name or raw_name.strip()

def detect_developer(name: str):
    for dev_name, aliases in PUNE_DEVELOPERS:
        for alias in aliases:
            pattern = rf'(?i)\b{re.escape(alias)}\b'
            if re.search(pattern, name):
                return dev_name
    return None

with open("data_fetch/pune_osm_raw.json", "r", encoding="utf-8") as f:
    elements = json.load(f)

dev_counter = Counter()
cleaned_names = []

for el in elements:
    raw_name = el.get("tags", {}).get("name", "")
    c_name = clean_society_name(raw_name)
    dev = detect_developer(raw_name) or detect_developer(c_name)
    if dev:
        dev_counter[dev] += 1
    cleaned_names.append((raw_name, c_name, dev))

print(f"Total elements: {len(elements)}")
print(f"Societies with attributed prominent developers: {sum(dev_counter.values())}")
print("\nTop Developer Breakdown:")
for d, c in dev_counter.most_common(20):
    print(f" - {d:<24}: {c}")

print("\nSample Cleaned Names:")
for r, c, d in cleaned_names[:15]:
    dev_str = f" [Developer: {d}]" if d else ""
    print(f" - '{r}' -> '{c}'{dev_str}")
