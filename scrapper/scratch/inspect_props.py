import json
import re

with open("DOCS/mockProperties.ts", "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect properties 5, 6, 7, 8 as well
print("--- Check listingMode and categories across all 8 ---")
for m in re.finditer(r'id:\s*"(prop-\d+)",\s*slug:\s*"([^"]+)",\s*title:\s*"([^"]+)",.*?listingMode:\s*"([^"]+)",', text, re.DOTALL):
    print(m.groups())
