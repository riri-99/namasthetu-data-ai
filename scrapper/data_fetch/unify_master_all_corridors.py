"""
Master Unification Script for Amberstone Sovereign Geo Stack
Combines all 4 Corridors: Pune (2,500) + Dubai (2,500) + Mumbai (2,500) + Indore (804)
Total: 8,304 Verified Societies
"""

import csv
from pathlib import Path

corridors = [
    ("Pune", Path("data_fetch/corridor_pune/pune_luxury_societies_2500.csv"), Path("data_fetch/corridor_pune/pune_master_societies.sql")),
    ("Dubai", Path("data_fetch/corridor_dubai/dubai_luxury_societies_2500.csv"), Path("data_fetch/corridor_dubai/dubai_master_societies.sql")),
    ("Mumbai", Path("data_fetch/corridor_mumbai/mumbai_luxury_societies_2500.csv"), Path("data_fetch/corridor_mumbai/mumbai_master_societies.sql")),
    ("Indore", Path("data_fetch/corridor_indore/indore_luxury_societies_2500.csv"), Path("data_fetch/corridor_indore/indore_master_societies.sql")),
]

master_csv = Path("data_fetch/master_luxury_societies_all.csv")
master_sql = Path("data_fetch/master_societies_seed_all.sql")

master_fields = [
    "id", "name", "normalized_name", "developer_name", "city", "micro_market",
    "country_code", "address", "pincode", "property_type", "levels", "units",
    "maharera_reg_no", "dld_project_id", "makani_number", "latitude", "longitude",
    "luxury_tier", "source_origin", "confidence_score"
]

all_records = []

for city_name, csv_path, _ in corridors:
    if not csv_path.exists():
        continue
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if "dld_project_id" not in row:
                row["dld_project_id"] = ""
            if "makani_number" not in row:
                row["makani_number"] = ""
            if "maharera_reg_no" not in row:
                row["maharera_reg_no"] = ""
            all_records.append(row)
            count += 1
        print(f"Loaded {count} records from {city_name} ({csv_path.name})")

print(f"\nTotal Consolidated Master Records: {len(all_records)}")

# Write Master CSV
with open(master_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=master_fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(all_records)

print(f"Exported Master CSV: {master_csv} ({len(all_records)} rows)")

# Write Unified Master SQL Seed
with open(master_sql, "w", encoding="utf-8") as out_f:
    out_f.write("-- Amberstone Real Estate Discovery Web OS\n")
    out_f.write(f"-- Master Seed: {len(all_records)} Luxury Societies Across 4 Corridors (Pune, Dubai, Mumbai, Indore)\n")
    out_f.write("-- Sovereign Geo Pipeline ($0.00 Google Cost)\n\n")
    out_f.write("BEGIN;\n\n")

    for city_name, _, sql_path in corridors:
        if not sql_path.exists():
            continue
        out_f.write(f"-- Corridor: {city_name}\n")
        with open(sql_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() in ("BEGIN;", "COMMIT;", "--", "") or line.startswith("--"):
                    continue
                out_f.write(line)
        out_f.write("\n")

    out_f.write("COMMIT;\n")

print(f"Exported Master SQL: {master_sql}")
