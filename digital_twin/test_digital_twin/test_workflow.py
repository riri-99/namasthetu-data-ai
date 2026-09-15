"""
Automated Digital Twin Workflow & Schema Verification Script
Validates the entire compilation and spatial layout flow:
  1. Compiling from customizable user/DB text prompts.
  2. Compiling from property listing records adhering to Prisma schema.
  3. Verifying exact bedroom count allocation (N-BHK = N physical rooms).
  4. Verifying calibrated 3:1 Living Hall to Kitchen area ratio.
  5. Verifying BIM geometry (walls, openings, doors, windows, balconies, furniture).
  6. Verifying schema moulding: FlooringType, FurnishingStatus, FacingDirection, Views, Inspection defects.
  7. Verifying exact Prisma DigitalTwin model DB shape export (spatialRooms + spatialMetadataJson).
  8. Exporting verified test blueprints to digital_twin/test_digital_twin/output/.
"""

import os
import sys
import json
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DIGITAL_TWIN_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

sys.path.insert(0, DIGITAL_TWIN_DIR)
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from digital_twin_engine import (
    engine,
    PropertyType,
    FlooringType,
    FurnishingStatus,
    FacingDirection,
    PropertyView,
    DefectSeverity
)

OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_workflow_test():
    print("=" * 80)
    print("🧪 RUNNING SOVEREIGN DIGITAL TWIN PRISMA SCHEMA CONFORMANCE TEST SUITE")
    print(f"📁 Output Directory: {OUTPUT_DIR}")
    print("=" * 80)

    test_cases = [
        {
            "name": "Custom Editable Prompt: 4 BHK Independent G+2 Villa",
            "prompt": "Magnificent 4 BHK G+2 Independent Villa with 4,200 sqft, East facing. Features double-height living room with 22ft ceiling, private heated plunge pool, open chef kitchen with 3:1 ratio, presidential master suite with private sunset balcony, mezzanine family lounge bridge, and rooftop sky pergola terrace.",
            "meta": {
                "title": "Golfshire Fairway Presidential Villa",
                "id": "test-villa-4bhk",
                "configuration": "4 BHK",
                "propertyType": "Villa",
                "carpetAreaSqft": 4200,
                "floor": "G + 2 Villa (3 Floors)",
                "facing": "East",
                "flooring": "ITALIAN_MARBLE",
                "furnishing": "FULLY_FURNISHED",
            },
            "expected_bhk": 4,
            "expected_levels": 3,
            "min_ratio": 2.8,
            "max_ratio": 3.4,
            "expected_flooring": "ITALIAN_MARBLE",
            "expected_furnishing": "FULLY_FURNISHED",
        },
        {
            "name": "Custom Editable Prompt: 3 BHK Luxury Apartment with Sunrise Balcony",
            "prompt": "Ultra-luxury 3 BHK apartment with panoramic sunrise facing sky balcony, Italian Botticino marble living hall, open-concept chef studio, presidential master suite with private corridor, and secondary bedrooms.",
            "meta": {
                "title": "The Balmoral Estates Sunrise Residence",
                "id": "test-apt-3bhk",
                "configuration": "3 BHK",
                "propertyType": "Apartment",
                "carpetAreaSqft": 1904,
                "floor": "14th Floor",
                "facing": "North-East",
                "flooring": "ITALIAN_MARBLE",
                "furnishing": "FULLY_FURNISHED",
            },
            "expected_bhk": 3,
            "expected_levels": 1,
            "min_ratio": 2.8,
            "max_ratio": 3.3,
            "expected_flooring": "ITALIAN_MARBLE",
            "expected_furnishing": "FULLY_FURNISHED",
        },
        {
            "name": "Custom Editable Prompt: 2 BHK Compact Luxury Suite",
            "prompt": "Boutique 2 BHK luxury residence with open kitchen island, Italian marble living room, master suite, and sunset balcony.",
            "meta": {
                "title": "Blue Waves Residence",
                "id": "test-apt-2bhk",
                "configuration": "2 BHK",
                "propertyType": "Apartment",
                "carpetAreaSqft": 1400,
                "floor": "8th Floor",
                "facing": "East",
                "flooring": "VITRIFIED_TILES",
                "furnishing": "FULLY_FURNISHED",
            },
            "expected_bhk": 2,
            "expected_levels": 1,
            "min_ratio": 2.8,
            "max_ratio": 3.3,
            "expected_flooring": "VITRIFIED_TILES",
            "expected_furnishing": "FULLY_FURNISHED",
        },
        {
            "name": "DB Moulded Penthouse: 4 BHK Sea View with Jacuzzi & Physical Seepage Pin",
            "prompt": "4 BHK Penthouse in Worli Mumbai, 3600 sqft, Italian marble flooring, fully furnished, direct sea and pool views, 3 balconies, 4 bathrooms, facing West. Inspection noted active seepage on master bathroom wall.",
            "meta": {
                "title": "Raheja Oceancrest Sky Penthouse",
                "id": "test-penthouse-4bhk",
                "propertyType": "PENTHOUSE",
                "configuration": "4 BHK",
                "carpetAreaSqft": 3600,
                "floor": "Top Floor Penthouse",
                "facing": "WEST",
                "flooring": "ITALIAN_MARBLE",
                "furnishing": "FULLY_FURNISHED",
                "views": ["SEA", "POOL"],
                "seepageDetected": True,
            },
            "expected_bhk": 4,
            "expected_levels": 1,
            "min_ratio": 2.8,
            "max_ratio": 3.4,
            "expected_flooring": "ITALIAN_MARBLE",
            "expected_furnishing": "FULLY_FURNISHED",
            "expected_defects": 1,
        },
        {
            "name": "DB Moulded Bare Shell: 3 BHK Unfurnished with Vitrified Tile Flooring",
            "prompt": "3 BHK Builder Floor in Gurgaon, 2100 sqft, vitrified tile flooring, unfurnished bare shell handover condition, facing North with clean electrical rough-ins.",
            "meta": {
                "title": "DLF Cyber City Builder Floor",
                "id": "test-unfurnished-3bhk",
                "propertyType": "BUILDER_FLOOR",
                "configuration": "3 BHK",
                "carpetAreaSqft": 2100,
                "floor": "2nd Floor",
                "facing": "NORTH",
                "flooring": "VITRIFIED_TILES",
                "furnishing": "UNFURNISHED",
            },
            "expected_bhk": 3,
            "expected_levels": 1,
            "min_ratio": 2.8,
            "max_ratio": 3.3,
            "expected_flooring": "VITRIFIED_TILES",
            "expected_furnishing": "UNFURNISHED",
        }
    ]

    all_passed = True

    for idx, tc in enumerate(test_cases, 1):
        print(f"\n▶ Test Case {idx}: {tc['name']}")
        t0 = time.time()
        blueprint = engine.compile(prompt=tc["prompt"], meta=tc["meta"])
        elapsed = time.time() - t0

        bhk = blueprint.get("bhkCount")
        levels = blueprint.get("levelsCount")
        rooms = blueprint.get("rooms", [])
        walls = blueprint.get("structuralWalls", [])
        doors = blueprint.get("doors", [])
        windows = blueprint.get("windows", [])
        balconies = blueprint.get("balconies", [])
        flooring = blueprint.get("flooring")
        furnishing = blueprint.get("furnishing")
        defects = blueprint.get("defects", [])

        # Bedroom Count Verification
        bedroom_rooms = [r for r in rooms if "master" in r["id"] or "bedroom" in r["id"]]
        bhk_ok = len(bedroom_rooms) == tc["expected_bhk"]

        # 3:1 Ratio Verification
        living = next((r for r in rooms if "living" in r["id"].lower()), None)
        kitchen = next((r for r in rooms if "kitchen" in r["id"].lower()), None)
        ratio = round(living["carpetSqft"] / max(1, kitchen["carpetSqft"]), 2) if living and kitchen else 0.0
        ratio_ok = tc["min_ratio"] <= ratio <= tc["max_ratio"]

        # Levels verification
        levels_ok = levels == tc["expected_levels"]

        # BIM Geometry verification
        bim_ok = len(walls) > 10 and len(doors) >= 2 and len(windows) >= 1 and len(balconies) >= 1

        # Flooring & Furnishing verification
        floor_ok = flooring == tc["expected_flooring"]
        furn_ok = furnishing == tc["expected_furnishing"]

        # Defect verification if expected
        defect_ok = True
        if "expected_defects" in tc:
            defect_ok = len(defects) >= tc["expected_defects"]

        # Unfurnished state verification
        if furnishing == "UNFURNISHED":
            total_furniture = sum(len(r.get("furniture", [])) for r in rooms)
            furn_ok = furn_ok and (total_furniture == 0)

        # Test Prisma DB Shape Generation
        db_twin = engine.compile_to_db_shape(tc["meta"], prompt=tc["prompt"])
        db_shape_ok = (
            "id" in db_twin and
            "publicId" in db_twin and
            "propertyId" in db_twin and
            "modelUrl" in db_twin and
            "spatialRooms" in db_twin and
            "spatialMetadataJson" in db_twin and
            len(db_twin["spatialRooms"]) == len(rooms)
        )

        print(f"   ⏱️ Compiled in {elapsed*1000:.1f}ms")
        print(f"   🛏️ Bedrooms: {len(bedroom_rooms)} rooms mapped (Expected: {tc['expected_bhk']}) -> {'✅ PASS' if bhk_ok else '❌ FAIL'}")
        print(f"   ⚖️ Living : Kitchen Ratio: {ratio}:1 (Expected: {tc['min_ratio']}-{tc['max_ratio']}:1) -> {'✅ PASS' if ratio_ok else '❌ FAIL'}")
        print(f"   🏢 Floor Levels: {levels} levels (Expected: {tc['expected_levels']}) -> {'✅ PASS' if levels_ok else '❌ FAIL'}")
        print(f"   🧱 BIM Solid Mesh: {len(walls)} walls, {len(doors)} doors, {len(windows)} windows, {len(balconies)} balconies -> {'✅ PASS' if bim_ok else '❌ FAIL'}")
        print(f"   🪵 Schema Moulding: Flooring={flooring} ({'✅ PASS' if floor_ok else '❌ FAIL'}), Furnishing={furnishing} ({'✅ PASS' if furn_ok else '❌ FAIL'}), Defects={len(defects)} ({'✅ PASS' if defect_ok else '❌ FAIL'})")
        print(f"   🗄️ Prisma DB Shape: publicId={db_twin['publicId']}, {len(db_twin['spatialRooms'])} spatial rooms -> {'✅ PASS' if db_shape_ok else '❌ FAIL'}")

        # Save output test blueprints
        json_out = os.path.join(OUTPUT_DIR, f"{tc['meta']['id']}_blueprint.json")
        ts_out = os.path.join(OUTPUT_DIR, f"{tc['meta']['id']}_blueprint.ts")
        engine.export_json(blueprint, json_out)
        engine.export_typescript(blueprint, ts_out, export_name=f"{tc['meta']['id'].replace('-', '_').upper()}_BLUEPRINT")

        if not (bhk_ok and ratio_ok and levels_ok and bim_ok and floor_ok and furn_ok and defect_ok and db_shape_ok):
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL WORKFLOW & PRISMA SCHEMA TESTS PASSED CLEANLY (100% SUCCESS)")
        print(f"📁 Verified blueprints exported to: {OUTPUT_DIR}")
    else:
        print("⚠️ SOME WORKFLOW TESTS FAILED. CHECK LOGS ABOVE.")
    print("=" * 80)

if __name__ == "__main__":
    run_workflow_test()
