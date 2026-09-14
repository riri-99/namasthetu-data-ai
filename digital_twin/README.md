# Sovereign 3D Digital Twin Module

The `digital_twin/` directory is a self-contained spatial computing module for **Sovereign Luxury Real Estate**. It automatically translates property listing metadata, civil inspection audits, and "About" descriptions into interactive, high-fidelity Three.js 3D architectural digital twins with physical **BIM (Building Information Modeling)** geometry.

---

## Key Capabilities

1. **Universal Compilation from Any Property Listing:**
   - Automatically parses property configuration, carpet area, floor descriptions, civil inspection reports, and verified specifications for any property listing.
2. **Strict Physical Bedroom Allocation ($N$-BHK = $N$ Distinct Rooms):**
   - Allocates $N$ distinct 3D bedrooms (Master Suite + Junior Suite + Guest/Children Suite + Sky Study) with individual world-space boundaries, beds, nightstands, and dressing alcoves.
3. **Calibrated 3:1 Living Hall to Kitchen Ratio:**
   - Balances public entertainment hall ($\sim 32-35\%$ of carpet area) with an ergonomic culinary studio ($\sim 10-11\%$).
4. **Multi-Floor Vertical Villa Levels (G+2 Architecture):**
   - Renders multi-tier independent villas (e.g. Prestige Golfshire G+2) across distinct elevations with 22ft double-height living hall voids, mezzanine lounges, plunge pool decks, and rooftop pergolas.
5. **Full BIM Architectural Geometry:**
   - **Structural Walls:** Interior partition walls (0.18m) and exterior perimeter walls (0.22m) with architectural baseboard skirting.
   - **Engineered Doors:** Teak door frames, wood leaves angled ajar into rooms, metallic brass lever handles, sliding glass doors, and grand foyer entry doors.
   - **Acoustic Windows:** Bronze frames, marble sills, cross divider mullions, and double-glazed translucent glass.
   - **Bounded Balconies:** Teak composite decking with 3-sided safety glass balustrades and continuous metallic top handrails.

---

## Generic Core Files

| File | Purpose |
| :--- | :--- |
| **[`digital_twin_engine.py`](digital_twin_engine.py)** | Universal BIM spatial layout compiler engine (`DigitalTwinEngine`) that converts any property listing into 3D spatial coordinate blueprints. |
| **[`DynamicThreeTwinViewer.tsx`](DynamicThreeTwinViewer.tsx)** | Production Next.js / React Three.js component that dynamically renders any `DigitalTwinBlueprint` with orbit, walk, auto-tour, and floor filtering. |
| **[`generate_listing_twin.py`](generate_listing_twin.py)** | Universal CLI and batch pipeline tool to compile digital twins for any property listing ID or text description. |

---

## Generic Usage

### 1. Python Engine API
```python
from digital_twin.digital_twin_engine import engine

# Compile any property listing dictionary
blueprint = engine.compile_from_property({
    "id": "prop-101",
    "title": "Raheja Mahal 4BHK Sky Mansion",
    "propertyType": "Apartment",
    "configuration": "4 BHK",
    "carpetAreaSqft": 2850,
    "floor": "32nd Floor",
    "facing": "West",
    "city": "Mumbai",
    "trustScore": 98,
})

# Export as JSON or TypeScript
engine.export_json(blueprint, "path/to/blueprint.json")
engine.export_typescript(blueprint, "path/to/blueprint.ts")
```

### 2. CLI Usage
```bash
# Compile a twin for any property ID from properties database
python digital_twin/generate_listing_twin.py --property-id "prop-1"

# Compile a twin from any natural language description
python digital_twin/generate_listing_twin.py --prompt "4 BHK luxury fairway villa in Bengaluru with 3800 sqft, double-height ceiling, private heated plunge pool, and rooftop sky pergola."
```

### 3. React / Next.js Component Usage
```tsx
import DynamicThreeTwinViewer from "@/digital_twin/DynamicThreeTwinViewer";

export default function PropertyTwinPage({ propertyBlueprint }) {
  return (
    <div className="w-full max-w-7xl mx-auto p-6">
      <DynamicThreeTwinViewer blueprint={propertyBlueprint} />
    </div>
  );
}
```

---

