"""
Generate Listing Digital Twin CLI & Batch Pipeline
Compiles structured 3D BIM digital twin blueprints directly from property listing records
matching exact bedroom counts, 3:1 kitchen-to-hall ratios, and multi-floor villa levels.
"""

import os
import sys
import argparse
import json
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from digital_twin_engine import engine

DEFAULT_BLUEPRINTS_DIR = os.path.join(CURRENT_DIR, "blueprints")

def generate_twin_for_property(property_data: dict, output_dir: str = None) -> dict:
    """
    Synthesizes an authoritative digital twin blueprint directly from property listing data.
    """
    blueprint = engine.compile_from_property(property_data)
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        slug = property_data.get("slug", property_data.get("id", "twin"))
        json_path = os.path.join(output_dir, f"{slug}_twin.json")
        ts_path = os.path.join(output_dir, f"{slug}_twin.ts")
        engine.export_json(blueprint, json_path)
        engine.export_typescript(blueprint, ts_path, export_name="PROPERTY_DIGITAL_TWIN")
        
    return blueprint

def main():
    parser = argparse.ArgumentParser(description="Digital Twin Spatial Generator CLI")
    parser.add_argument("--prompt", type=str, help="Text description of the property to compile into 3D twin")
    parser.add_argument("--property-id", type=str, help="Property ID from mock_properties_all.json to compile")
    parser.add_argument("--batch-sample", action="store_true", help="Generate digital twins for flagship sample properties across corridors")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_BLUEPRINTS_DIR, help="Output directory for generated blueprints")

    args = parser.parse_args()

    print("=" * 70)
    print("🏢 SOVEREIGN DIGITAL TWIN SPATIAL COMPILER PIPELINE")
    print("=" * 70)

    if args.prompt:
        print(f"\n📝 Compiling from text prompt:\n   \"{args.prompt}\"")
        blueprint = engine.compile(args.prompt)
        os.makedirs(args.output_dir, exist_ok=True)
        json_out = os.path.join(args.output_dir, "custom_prompt_twin.json")
        ts_out = os.path.join(args.output_dir, "custom_prompt_twin.ts")
        engine.export_json(blueprint, json_out)
        engine.export_typescript(blueprint, ts_out, export_name="CUSTOM_PROMPT_TWIN")
        print(f"\n✅ Custom Digital Twin successfully compiled with {len(blueprint['rooms'])} rooms!")
        return

    # Check for master properties file in multiple possible paths
    possible_paths = [
        os.path.join(PROJECT_ROOT, "scrapper", "data_fetch", "mock_data", "mock_properties_all.json"),
        os.path.join(PROJECT_ROOT, "scrapper", "data_fetch", "mock_properties_all.json"),
        os.path.join(PROJECT_ROOT, "data_fetch", "mock_properties_all.json"),
        os.path.join(PROJECT_ROOT, "DOCS", "mock_properties_all.json"),
    ]
    master_json = next((p for p in possible_paths if os.path.exists(p)), None)
    if not master_json:
        print("❌ Error: mock_properties_all.json not found in expected directories. Please ensure properties are generated first.")
        return

    print(f"📂 Loading properties from: {os.path.relpath(master_json, PROJECT_ROOT)}")
    with open(master_json, "r", encoding="utf-8") as f:
        properties = json.load(f)

    if args.property_id:
        prop = next((p for p in properties if p["id"] == args.property_id), None)
        if not prop:
            print(f"❌ Property with ID '{args.property_id}' not found.")
            return
        print(f"\n🔍 Compiling Digital Twin for: {prop['title']} ({prop['id']}) ...")
        blueprint = generate_twin_for_property(prop, args.output_dir)
        print(f"✅ Digital Twin generated with {len(blueprint['rooms'])} rooms and {len(blueprint['waypoints'])} tour waypoints!")
        return

    # Default or --batch-sample: Pick 2 flagship properties from each corridor
    print("\n📦 Generating Flagship Digital Twins across Pune, Dubai, Mumbai, and Indore ...")
    corridors = ["Pune", "Dubai", "Mumbai", "Indore"]
    sample_twins = []

    for city in corridors:
        city_props = [p for p in properties if p.get("city") == city]
        if not city_props:
            continue
        selected = city_props[:2]
        for p in selected:
            city_dir = os.path.join(args.output_dir, f"corridor_{city.lower()}")
            print(f"   Compiling: [{city}] {p['title'][:45]} ...")
            bp = generate_twin_for_property(p, city_dir)
            sample_twins.append(bp)

    print(f"\n🎯 Successfully generated {len(sample_twins)} Digital Twins across all 4 corridors in:\n   {args.output_dir}")

if __name__ == "__main__":
    main()
