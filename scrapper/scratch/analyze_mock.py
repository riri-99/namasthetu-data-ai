import re

with open("DOCS/mockProperties.ts", "r", encoding="utf-8") as f:
    content = f.read()

# Find property objects (level 1 id: "prop-...")
props = re.findall(r'id:\s*"(prop-[^"]+)"', content)
print(f"Total properties: {len(props)}")
print(f"Prop IDs: {props}")

# Extract keys of property objects
# Let's see unique top-level keys
lines = content.splitlines()
in_prop = False
keys = set()
for line in lines:
    m = re.match(r'^\s\s\s\s([a-zA-Z0-9_]+):', line)
    if m:
        keys.add(m.group(1))

print(f"Top-level keys ({len(keys)}): {sorted(list(keys))}")
