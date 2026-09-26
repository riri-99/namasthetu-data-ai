"""
Corridor Real Estate Listings & Database Seed Generator
Reads society datasets from data_fetch/corridor_* folders and master_luxury_societies_all.csv
Generates:
  1. TypeScript property listing files (*.ts) matching DOCS/mockProperties.ts data shape
  2. SQL database seed files (*.sql) for PostgreSQL / PostGIS
  3. Clean JSON seed files (*.json)
"""

import os
import sys
import json
import time
import pandas as pd
from typing import List, Dict, Any
from scrapper.data_fetch.listing_generator import generate_property_from_row

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_FETCH_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(os.path.dirname(DATA_FETCH_DIR), "DOCS")

CORRIDORS = [
    {
        "name": "Pune",
        "folder": os.path.join(DATA_FETCH_DIR, "corridor_pune"),
        "csv_file": "pune_luxury_societies_2500.csv",
        "ts_prefix": "pune",
        "export_var": "PUNE_MOCK_PROPERTIES",
    },
    {
        "name": "Dubai",
        "folder": os.path.join(DATA_FETCH_DIR, "corridor_dubai"),
        "csv_file": "dubai_luxury_societies_2500.csv",
        "ts_prefix": "dubai",
        "export_var": "DUBAI_MOCK_PROPERTIES",
    },
    {
        "name": "Mumbai",
        "folder": os.path.join(DATA_FETCH_DIR, "corridor_mumbai"),
        "csv_file": "mumbai_luxury_societies_2500.csv",
        "ts_prefix": "mumbai",
        "export_var": "MUMBAI_MOCK_PROPERTIES",
    },
    {
        "name": "Indore",
        "folder": os.path.join(DATA_FETCH_DIR, "corridor_indore"),
        "csv_file": "indore_luxury_societies_2500.csv",
        "ts_prefix": "indore",
        "export_var": "INDORE_MOCK_PROPERTIES",
    },
]

SQL_DDL_HEADER = """-- ====================================================================
-- Amberstone Sovereign Real Estate Discovery Web OS
-- Target Table: property_listings (PostgreSQL + PostGIS)
-- ====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS property_listings (
    id VARCHAR(64) PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,
    society_id UUID,
    title VARCHAR(500) NOT NULL,
    locality VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326),
    listing_mode VARCHAR(20) NOT NULL,
    category JSONB NOT NULL,
    property_type VARCHAR(100) NOT NULL,
    configuration VARCHAR(50) NOT NULL,
    bathrooms INT NOT NULL,
    carpet_area_sqft INT NOT NULL,
    super_built_up_area_sqft INT NOT NULL,
    floor VARCHAR(100) NOT NULL,
    facing VARCHAR(50) NOT NULL,
    water_supply VARCHAR(255) NOT NULL,
    price_paise VARCHAR(50) NOT NULL,
    formatted_price VARCHAR(100) NOT NULL,
    price_per_sqft VARCHAR(100) NOT NULL,
    maintenance_monthly_paise VARCHAR(50) NOT NULL,
    stamp_duty_estimate VARCHAR(100),
    registration_estimate VARCHAR(100),
    images JSONB NOT NULL,
    has_3d_tour BOOLEAN NOT NULL DEFAULT true,
    spatial_rooms JSONB NOT NULL,
    trust_score INT NOT NULL,
    verified_owner_badge BOOLEAN NOT NULL DEFAULT true,
    top_badge VARCHAR(100) NOT NULL,
    ulpin VARCHAR(100) NOT NULL,
    rera_number VARCHAR(100),
    available_from VARCHAR(100) NOT NULL,
    inspection JSONB NOT NULL,
    valuation JSONB NOT NULL,
    deed_history JSONB NOT NULL,
    owner JSONB NOT NULL,
    amenities JSONB NOT NULL,
    neighbourhood JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_property_listings_city ON property_listings(city);
CREATE INDEX IF NOT EXISTS idx_property_listings_locality ON property_listings(locality);
CREATE INDEX IF NOT EXISTS idx_property_listings_mode ON property_listings(listing_mode);
CREATE INDEX IF NOT EXISTS idx_property_listings_type ON property_listings(property_type);
CREATE INDEX IF NOT EXISTS idx_property_listings_geom ON property_listings USING GIST(geom);

BEGIN;
"""

def escape_sql(val: Any) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dict, list)):
        s = json.dumps(val, ensure_ascii=False)
        return "'" + s.replace("'", "''") + "'::jsonb"
    s = str(val)
    return "'" + s.replace("'", "''") + "'"

def write_ts_file(filepath: str, export_var: str, properties: List[Dict[str, Any]]):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('import { PropertyListing } from "@/types/property";\n\n')
        f.write(f'export const {export_var}: PropertyListing[] = ')
        json.dump(properties, f, indent=2, ensure_ascii=False)
        f.write(";\n\n")
        f.write(f"export const MOCK_PROPERTIES = {export_var};\n")
        f.write(f"export default {export_var};\n")

def write_sql_file(filepath: str, title: str, properties: List[Dict[str, Any]]):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"-- Corridor: {title} ({len(properties)} Listings)\n")
        f.write(SQL_DDL_HEADER)
        f.write("\n")
        
        for prop in properties:
            coords = prop["coordinates"]
            lat = coords["lat"]
            lng = coords["lng"]
            geom_expr = f"ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326)"
            
            stmt = (
                f"INSERT INTO property_listings ("
                f"id, slug, society_id, title, locality, city, state, latitude, longitude, geom, "
                f"listing_mode, category, property_type, configuration, bathrooms, "
                f"carpet_area_sqft, super_built_up_area_sqft, floor, facing, water_supply, "
                f"price_paise, formatted_price, price_per_sqft, maintenance_monthly_paise, "
                f"stamp_duty_estimate, registration_estimate, images, has_3d_tour, spatial_rooms, "
                f"trust_score, verified_owner_badge, top_badge, ulpin, rera_number, available_from, "
                f"inspection, valuation, deed_history, owner, amenities, neighbourhood"
                f") VALUES (\n"
                f"    {escape_sql(prop['id'])}, {escape_sql(prop['slug'])}, {escape_sql(prop.get('societyId'))}::uuid, "
                f"{escape_sql(prop['title'])}, {escape_sql(prop['locality'])}, {escape_sql(prop['city'])}, {escape_sql(prop['state'])}, "
                f"{lat}, {lng}, {geom_expr}, {escape_sql(prop['listingMode'])}, {escape_sql(prop['category'])}, "
                f"{escape_sql(prop['propertyType'])}, {escape_sql(prop['configuration'])}, {prop['bathrooms']}, "
                f"{prop['carpetAreaSqft']}, {prop['superBuiltUpAreaSqft']}, {escape_sql(prop['floor'])}, {escape_sql(prop['facing'])}, "
                f"{escape_sql(prop['waterSupply'])}, {escape_sql(prop['pricePaise'])}, {escape_sql(prop['formattedPrice'])}, "
                f"{escape_sql(prop['pricePerSqft'])}, {escape_sql(prop['maintenanceMonthlyPaise'])}, {escape_sql(prop.get('stampDutyEstimate'))}, "
                f"{escape_sql(prop.get('registrationEstimate'))}, {escape_sql(prop['images'])}, {escape_sql(prop['has3dTour'])}, "
                f"{escape_sql(prop['spatialRooms'])}, {prop['trustScore']}, {escape_sql(prop['verifiedOwnerBadge'])}, "
                f"{escape_sql(prop['topBadge'])}, {escape_sql(prop['ulpin'])}, {escape_sql(prop.get('reraNumber'))}, "
                f"{escape_sql(prop['availableFrom'])}, {escape_sql(prop['inspection'])}, {escape_sql(prop['valuation'])}, "
                f"{escape_sql(prop['deedHistory'])}, {escape_sql(prop['owner'])}, {escape_sql(prop['amenities'])}, "
                f"{escape_sql(prop['neighbourhood'])}\n"
                f") ON CONFLICT (id) DO UPDATE SET\n"
                f"    title = EXCLUDED.title,\n"
                f"    formatted_price = EXCLUDED.formatted_price,\n"
                f"    inspection = EXCLUDED.inspection;\n"
            )
            f.write(stmt)
            
        f.write("\nCOMMIT;\n")

def write_json_file(filepath: str, properties: List[Dict[str, Any]]):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(properties, f, indent=2, ensure_ascii=False)

def main():
    start_time = time.time()
    print("=" * 70)
    print("🚀 SOVEREIGN CORRIDOR PROPERTY LISTINGS & SEED GENERATOR")
    print("   Data Shape Source: DOCS/mockProperties.ts (PropertyListing)")
    print("=" * 70)

    all_properties = []
    global_counter = 0
    corridor_summaries = {}

    for corr in CORRIDORS:
        corr_name = corr["name"]
        corr_folder = corr["folder"]
        csv_path = os.path.join(corr_folder, corr["csv_file"])

        if not os.path.exists(csv_path):
            print(f"❌ Warning: {csv_path} not found. Skipping {corr_name}.")
            continue

        print(f"\n📂 Processing Corridor: {corr_name} ...")
        df = pd.read_csv(csv_path)
        print(f"   Loaded {len(df)} societies from {os.path.basename(csv_path)}")

        corr_properties = []
        for idx, row in df.iterrows():
            prop = generate_property_from_row(row, global_counter)
            corr_properties.append(prop)
            all_properties.append(prop)
            global_counter += 1

        # 1. Write Corridor TypeScript file
        ts_filename = f"{corr['ts_prefix']}_mock_properties.ts"
        ts_filepath = os.path.join(corr_folder, ts_filename)
        print(f"   Generating TypeScript: {ts_filename} ...")
        write_ts_file(ts_filepath, corr["export_var"], corr_properties)

        # 2. Write Corridor SQL Seed file
        sql_filename = f"{corr['ts_prefix']}_properties_seed.sql"
        sql_filepath = os.path.join(corr_folder, sql_filename)
        print(f"   Generating SQL Seed: {sql_filename} ...")
        write_sql_file(sql_filepath, corr_name, corr_properties)

        # 3. Write Corridor JSON file
        json_filename = f"{corr['ts_prefix']}_mock_properties.json"
        json_filepath = os.path.join(corr_folder, json_filename)
        print(f"   Generating JSON Seed: {json_filename} ...")
        write_json_file(json_filepath, corr_properties)

        ts_size = os.path.getsize(ts_filepath) / (1024 * 1024)
        sql_size = os.path.getsize(sql_filepath) / (1024 * 1024)
        json_size = os.path.getsize(json_filepath) / (1024 * 1024)

        corridor_summaries[corr_name] = {
            "count": len(corr_properties),
            "ts_file": ts_filepath,
            "ts_size_mb": round(ts_size, 2),
            "sql_file": sql_filepath,
            "sql_size_mb": round(sql_size, 2),
            "json_file": json_filepath,
            "json_size_mb": round(json_size, 2),
        }
        print(f"   ✅ Corridor {corr_name} Complete: {len(corr_properties)} listings (TS: {ts_size:.2f}MB, SQL: {sql_size:.2f}MB, JSON: {json_size:.2f}MB)")

    # Consolidated Master files for all 8,304 properties
    print(f"\n🌐 Generating Consolidated Master Datasets (Total: {len(all_properties)} properties) ...")
    
    # Master TS
    master_ts_path = os.path.join(DATA_FETCH_DIR, "mock_properties_master_8304.ts")
    print(f"   Generating Master TypeScript: {os.path.basename(master_ts_path)} ...")
    write_ts_file(master_ts_path, "MASTER_8304_PROPERTIES", all_properties)

    # Master SQL
    master_sql_path = os.path.join(DATA_FETCH_DIR, "mock_properties_seed_all.sql")
    print(f"   Generating Master SQL Seed: {os.path.basename(master_sql_path)} ...")
    write_sql_file(master_sql_path, "All Corridors Master", all_properties)

    # Master JSON
    master_json_path = os.path.join(DATA_FETCH_DIR, "mock_properties_all.json")
    print(f"   Generating Master JSON: {os.path.basename(master_json_path)} ...")
    write_json_file(master_json_path, all_properties)

    # Also write master files to DOCS directory as requested
    print(f"\n📂 Syncing Master Datasets to DOCS/ folder ...")
    docs_ts_path = os.path.join(DOCS_DIR, "mock_properties_master_8304.ts")
    docs_sql_path = os.path.join(DOCS_DIR, "mock_properties_seed_8304.sql")
    print(f"   Writing {docs_ts_path} ...")
    write_ts_file(docs_ts_path, "MASTER_8304_PROPERTIES", all_properties)
    print(f"   Writing {docs_sql_path} ...")
    write_sql_file(docs_sql_path, "All Corridors Master (8,304 Listings)", all_properties)

    master_ts_size = os.path.getsize(master_ts_path) / (1024 * 1024)
    master_sql_size = os.path.getsize(master_sql_path) / (1024 * 1024)
    master_json_size = os.path.getsize(master_json_path) / (1024 * 1024)

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    print(f"🎯 ALL GENERATION COMPLETE IN {elapsed}s!")
    print(f"   Total Properties Generated: {len(all_properties)}")
    print(f"   Master TS Size:   {master_ts_size:.2f} MB")
    print(f"   Master SQL Size:  {master_sql_size:.2f} MB")
    print(f"   Master JSON Size: {master_json_size:.2f} MB")
    print("=" * 70)

if __name__ == "__main__":
    main()
