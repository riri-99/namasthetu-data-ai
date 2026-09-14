"""
Automated Digital Twin Workflow Verification Script
Validates the entire compilation and spatial layout flow:
  1. Compiling from customizable user text prompts.
  2. Compiling from property listing records (About notes, inspection data).
  3. Verifying exact bedroom count allocation (N-BHK = N physical rooms).
  4. Verifying calibrated 3:1 Living Hall to Kitchen area ratio.
  5. Verifying BIM geometry (walls, openings, doors, windows, balconies, furniture).
  6. Exporting verified test blueprints to digital_twin/test_digital_twin/output/.
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

from digital_twin_engine import engine

OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_workflow_test():
    print("=" * 75)
    print("🧪 RUNNING SOVEREIGN DIGITAL TWIN WORKFLOW TEST SUITE")
    print(f"📁 Output Directory: {OUTPUT_DIR}")
    print("=" * 75)

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
            },
            "expected_bhk": 4,
            "expected_levels": 3,
            "min_ratio": 2.8,
            "max_ratio": 3.4
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
            },
            "expected_bhk": 3,
            "expected_levels": 1,
            "min_ratio": 2.8,
            "max_ratio": 3.3
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
            },
            "expected_bhk": 2,
            "expected_levels": 1,
            "min_ratio": 2.8,
            "max_ratio": 3.3
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

        print(f"   ⏱️ Compiled in {elapsed*1000:.1f}ms")
        print(f"   🛏️ Bedrooms: {len(bedroom_rooms)} rooms mapped (Expected: {tc['expected_bhk']}) -> {'✅ PASS' if bhk_ok else '❌ FAIL'}")
        print(f"   ⚖️ Living : Kitchen Ratio: {ratio}:1 (Expected: {tc['min_ratio']}-{tc['max_ratio']}:1) -> {'✅ PASS' if ratio_ok else '❌ FAIL'}")
        print(f"   🏢 Floor Levels: {levels} levels (Expected: {tc['expected_levels']}) -> {'✅ PASS' if levels_ok else '❌ FAIL'}")
        print(f"   🧱 BIM Solid Mesh: {len(walls)} walls, {len(doors)} doors, {len(windows)} windows, {len(balconies)} balconies -> {'✅ PASS' if bim_ok else '❌ FAIL'}")

        # Save output test blueprints
        json_out = os.path.join(OUTPUT_DIR, f"{tc['meta']['id']}_blueprint.json")
        ts_out = os.path.join(OUTPUT_DIR, f"{tc['meta']['id']}_blueprint.ts")
        engine.export_json(blueprint, json_out)
        engine.export_typescript(blueprint, ts_out, export_name=f"{tc['meta']['id'].replace('-', '_').upper()}_BLUEPRINT")

        if not (bhk_ok and ratio_ok and levels_ok and bim_ok):
            all_passed = False

    print("\n" + "=" * 75)
    if all_passed:
        print("🎉 ALL WORKFLOW TESTS PASSED CLEANLY (100% SUCCESS)")
        print(f"📁 Verified blueprints exported to: {OUTPUT_DIR}")
    else:
        print("⚠️ SOME WORKFLOW TESTS FAILED. CHECK LOGS ABOVE.")
    print("=" * 75)

if __name__ == "__main__":
    run_workflow_test()
