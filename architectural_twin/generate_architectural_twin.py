"""
Generate Architectural Digital Twin CLI & Batch Pipeline
Fuses property photographs, floor plan drawings, and listing "About" notes
to compile topological room adjacencies and BIM-accurate 3D Three.js blueprints.
"""

import os
import sys
import argparse
import json
import glob
from typing import Dict, Any, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from architectural_twin_engine import engine
from visual_layout_extractor import extractor as visual_extractor

DEFAULT_BLUEPRINTS_DIR = os.path.join(CURRENT_DIR, "blueprints")

def find_master_properties_file() -> str:
    possible_paths = [
        os.path.join(PROJECT_ROOT, "scrapper", "data_fetch", "mock_data", "mock_properties_all.json"),
        os.path.join(PROJECT_ROOT, "scrapper", "data_fetch", "mock_properties_all.json"),
        os.path.join(PROJECT_ROOT, "data_fetch", "mock_properties_all.json"),
        os.path.join(PROJECT_ROOT, "DOCS", "mock_properties_all.json"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return ""

def generate_architectural_twin_for_property(property_data: dict, output_dir: str = None) -> dict:
    """
    Compiles an image-referenced architectural twin blueprint with topological room adjacencies.
    """
    blueprint = engine.compile(property_data)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        slug = property_data.get("slug", property_data.get("id", "arch_twin"))
        json_path = os.path.join(output_dir, f"{slug}_architectural_twin.json")
        ts_path = os.path.join(output_dir, f"{slug}_architectural_twin.ts")
        engine.export_json(blueprint, json_path)
        engine.export_typescript(blueprint, ts_path, export_name="ARCHITECTURAL_TWIN_BLUEPRINT")

    return blueprint

def generate_from_image_directory(image_dir: str, notes: str = "", output_dir: str = None) -> dict:
    """
    Compiles an architectural twin from a local directory of room photographs and notes.
    """
    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    image_paths = []
    for ext in exts:
        image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
        image_paths.extend(glob.glob(os.path.join(image_dir, ext.upper())))

    if not image_paths:
        print(f"⚠️ No image files found in directory: {image_dir}")
        image_paths = ["https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=80"]

    dirname = os.path.basename(os.path.abspath(image_dir))
    prop_data = {
        "id": f"custom-dir-{dirname}",
        "title": f"Custom Architecture Residence ({dirname.replace('_', ' ').title()})",
        "locality": "Architectural Studio Gallery",
        "city": "Mumbai",
        "state": "Maharashtra",
        "propertyType": "Apartment",
        "configuration": "3 BHK",
        "carpetAreaSqft": 2400,
        "floor": "Upper Penthouse",
        "facing": "East",
        "about": notes or "Bespoke architectural residence with open plan living, gourmet kitchen, and panoramic balconies.",
        "images": image_paths,
    }

    return generate_architectural_twin_for_property(prop_data, output_dir)

def print_twin_summary(blueprint: dict):
    print("\n" + "-" * 70)
    print(f"🏛️  ARCHITECTURAL TWIN BLUEPRINT SUMMARY: {blueprint['propertyTitle']}")
    print("-" * 70)
    print(f"📍 Location: {blueprint['city']} · Archetype: {blueprint['archetype']} · Layout: {blueprint['configuration']}")
    print(f"📐 Carpet Area: {blueprint['carpetSqft']:,} sq.ft · Elevation Floors: {blueprint['levelsCount']}")
    print(f"🧭 Primary View Orientation: {blueprint['orientation']}")
    print(f"📸 Image References Analyzed: {len(blueprint.get('analyzedImages', []))}")
    print(f"🚪 BIM Geometry: {len(blueprint['rooms'])} Rooms, {len(blueprint['structuralWalls'])} Walls, {len(blueprint['doors'])} Doors, {len(blueprint['windows'])} Windows, {len(blueprint['balconies'])} Balconies")

    print("\n🔗 TOPOLOGICAL ROOM ADJACENCIES INFERRED:")
    edges = blueprint.get("adjacencyGraph", {}).get("edges", [])
    for edge in edges:
        from_name = edge['from'].upper()
        to_name = edge['to'].upper()
        b_type = edge.get('boundaryType', 'door').replace('_', ' ').title()
        direction = edge.get('relativeDirection', '')
        print(f"   • [{from_name}] ↔ [{to_name}] via {b_type} ({direction})")
        if edge.get("reason"):
            print(f"     └─ Visual/Spatial Cues: {edge['reason']}")

    print("\n🛋️ ROOMS & VISUAL ATTRIBUTIONS:")
    for room in blueprint["rooms"]:
        ref = room.get("imageReference")
        finish = room.get("floorType", "Vitrified Tile")
        img_info = f"Photo Ref ({ref['category']} - {int(ref['confidence']*100)}% conf)" if ref else "Default Archetype"
        connected = [conn["neighborName"] for conn in room.get("adjacentRooms", [])]
        conn_str = ", ".join(connected) if connected else "Self-contained"
        print(f"   • [{room['id'].upper()}] {room['name']}")
        print(f"     Finish: {finish} | Visual Attrib: {img_info}")
        print(f"     Adjacencies: {conn_str}")
    print("-" * 70)

def main():
    parser = argparse.ArgumentParser(description="Architectural Digital Twin CLI & Batch Pipeline")
    parser.add_argument("--property-id", type=str, help="Property ID from mock_properties_all.json to compile")
    parser.add_argument("--image-dir", type=str, help="Directory containing room photos to analyze and build twin from")
    parser.add_argument("--notes", type=str, default="", help="Listing notes or description for image directory")
    parser.add_argument("--batch-sample", action="store_true", help="Compile flagship architectural twins across corridors")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_BLUEPRINTS_DIR, help="Output directory for blueprints")

    args = parser.parse_args()

    print("=" * 75)
    print("🏢 SOVEREIGN MULTI-MODAL ARCHITECTURAL TWIN COMPILER")
    print("   Visual Intelligence · Topological Adjacencies · Physical BIM Geometry")
    print("=" * 75)

    if args.image_dir:
        print(f"\n📸 Extracting visual context from directory: {args.image_dir}")
        blueprint = generate_from_image_directory(args.image_dir, args.notes, args.output_dir)
        print_twin_summary(blueprint)
        print(f"\n✅ Blueprint generated in: {args.output_dir}")
        return

    master_file = find_master_properties_file()
    if not master_file:
        print("❌ Error: mock_properties_all.json not found in repository.")
        return

    print(f"📂 Loading property repository: {os.path.relpath(master_file, PROJECT_ROOT)}")
    with open(master_file, "r", encoding="utf-8") as f:
        properties = json.load(f)

    if args.property_id:
        prop = next((p for p in properties if p.get("id") == args.property_id), None)
        if not prop:
            print(f"❌ Property with ID '{args.property_id}' not found.")
            return
        print(f"\n🔍 Analyzing property photos and About notes for: '{prop['title']}' ({prop['id']}) ...")
        blueprint = generate_architectural_twin_for_property(prop, args.output_dir)
        print_twin_summary(blueprint)
        print(f"\n✅ Architectural Twin successfully compiled into: {args.output_dir}")
        return

    # Default or --batch-sample: Pick sample villa and sample apartments
    print("\n📦 Generating Flagship Architectural Twins across Corridors ...")
    corridors = ["Pune", "Dubai", "Mumbai", "Indore"]
    twins_generated = 0

    for city in corridors:
        city_props = [p for p in properties if p.get("city") == city]
        if not city_props:
            continue
        selected = city_props[:2]
        for p in selected:
            city_dir = os.path.join(args.output_dir, f"corridor_{city.lower()}")
            print(f"   Compiling: [{city}] {p['title'][:45]} ...")
            bp = generate_architectural_twin_for_property(p, city_dir)
            twins_generated += 1

    print(f"\n🎯 Successfully compiled {twins_generated} Architectural Twins across all corridors into:\n   {args.output_dir}")

if __name__ == "__main__":
    main()
