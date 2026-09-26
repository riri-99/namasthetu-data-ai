"""
Master Unification Script for Amberstone Sovereign Geo Stack
Combines 2,500 Pune Societies + 2,500 Dubai Societies into 5,000 Master Dataset
"""

import csv
from pathlib import Path

pune_csv = Path("data_fetch/corridor_pune/pune_luxury_societies_2500.csv")
dubai_csv = Path("data_fetch/corridor_dubai/dubai_luxury_societies_2500.csv")

pune_sql = Path("data_fetch/corridor_pune/pune_master_societies.sql")
dubai_sql = Path("data_fetch/corridor_dubai/dubai_master_societies.sql")

master_csv = Path("data_fetch/master_luxury_societies_5000.csv")
master_sql = Path("data_fetch/master_societies_seed.sql")

master_fields = [
    "id", "name", "normalized_name", "developer_name", "city", "micro_market",
    "country_code", "address", "pincode", "property_type", "levels", "units",
    "maharera_reg_no", "dld_project_id", "makani_number", "latitude", "longitude",
    "luxury_tier", "source_origin", "confidence_score"
]

all_records = []

# Read Pune
with open(pune_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        row["dld_project_id"] = ""
        row["makani_number"] = ""
        all_records.append(row)

# Read Dubai
with open(dubai_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        row["maharera_reg_no"] = ""
        all_records.append(row)

print(f"Total Unified Records: {len(all_records)}")

# Write Master CSV
with open(master_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=master_fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(all_records)

print(f"Exported Master CSV: {master_csv} ({len(all_records)} rows)")

# Write Unified Master SQL Seed
with open(master_sql, "w", encoding="utf-8") as out_f:
    out_f.write("-- Amberstone Real Estate Discovery Web OS\n")
    out_f.write("-- Master Seed: 5,000 Luxury Societies (2,500 Pune + 2,500 Dubai)\n")
    out_f.write("-- Sovereign Geo Pipeline ($0.00 Cost)\n\n")
    out_f.write("BEGIN;\n\n")

    # Read Pune statements (skip BEGIN and COMMIT)
    with open(pune_sql, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() in ("BEGIN;", "COMMIT;", "--", "") or line.startswith("--"):
                continue
            out_f.write(line)

    out_f.write("\n")

    # Read Dubai statements (skip BEGIN and COMMIT)
    with open(dubai_sql, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() in ("BEGIN;", "COMMIT;", "--", "") or line.startswith("--"):
                continue
            out_f.write(line)

    out_f.write("\nCOMMIT;\n")

print(f"Exported Master SQL: {master_sql}")
