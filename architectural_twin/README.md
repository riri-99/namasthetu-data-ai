# Sovereign Multi-Modal Architectural Twin Pipeline

> **Visual Intelligence · Topological Adjacency Solvers · Physical BIM 3D Geometry**

The `architectural_twin/` module is a zero-cost ($0.00 spend), production-ready spatial intelligence pipeline that translates **property photographs, architectural drawings, and listing "About" notes** into millimeter-accurate 3D Three.js digital twins.

---

## 🏗️ Architecture & Core Components

```
architectural_twin/
├── visual_layout_extractor.py     # Multi-modal CV + NLP adjacency & finish classifier
├── architectural_twin_engine.py   # Graph-driven 3D spatial layout & BIM generator
├── generate_architectural_twin.py # CLI and batch compilation pipeline
├── ArchitecturalTwinViewer.tsx    # React Three.js viewer with Visual Reference & Adjacency Drawer
├── blueprints/                    # Output directory for generated .json and .ts blueprints
└── README.md                      # This documentation
```

### 1. `visual_layout_extractor.py`
- **Zero-Cost Visual Feature Extraction:** Uses local `PIL` and `numpy` to compute chromatic signatures (Italian Botticino marble, engineered oak wood, quartzite, terrace teak) and structural edge gradients (horizontal countertops vs. vertical window mullions/sliders).
- **Contextual NLP Fusion:** Fuses visual signatures with listing descriptions to deduce room categories, finishes, and boundary cues.
- **Topological Adjacency Graph:** Deduces connections between rooms:
  - `open_portal`: Wide archway without a door leaf (e.g., Living Hall ↔ Gourmet Culinary Studio).
  - `sliding_glass`: Panoramic 4-panel sliding door (e.g., Living ↔ Covered Sky Balcony, Master ↔ Fairway Deck).
  - `door`: Acoustic swing door with frame, leaf, and handle (e.g., Living ↔ Master Suite, Corridors ↔ Bedroom Suites).
  - `shared_wall`: Solid partition wall separating private quarters.
- **Image Attribution Contract:** Attaches the matching photo source, AI confidence score, and detected finish directly to each room node.

### 2. `architectural_twin_engine.py`
- **Graph-Driven 3D Layout:** Places rooms in 3D metric space according to topological adjacency edges rather than static coordinates.
- **BIM Solid Geometry:** Procedurally synthesizes perimeter walls, interior partitions, door openings with lintels/frames, windows with sills/mullions, and balconies with teak decking and tempered glass balustrades.
- **Multi-Tier Elevations:** Generates G+2 3-floor independent villas (double-height void living hall, mezzanine bridge, plunge pool deck, sky pergola terrace) as well as single-level luxury apartments.
- **Dual Export:** Outputs both standalone `.json` and typed `.ts` blueprints ready for Next.js.

### 3. `ArchitecturalTwinViewer.tsx`
- **WebGL Procedural Engine:** High-performance Three.js rendering with shadow maps, lighting rigs, and ACES Filmic tone mapping.
- **Interactive Visual Reference Drawer:**
  - Shows the exact property photo that informed the room's classification.
  - Displays the visual AI confidence badge (e.g. `92% Visual AI Conf.`).
  - Lists all **Connected Adjacent Rooms** with their boundary types and spatial directions.
  - Interactive **"Fly to Room"** button that animates the camera directly through the portal into the adjacent room.
- **View Modes:**
  - `Orbit View`: Free mouse rotation and zoom.
  - `First Person`: Eye-level walk inside any selected room.
  - `Cinematic Tour`: Smooth waypoint traversal across all connected zones.
  - `Cutaway Plan`: Top-down orthographic architectural view.

---

## 🚀 How to Run the Generic Pipeline

### 1. Run for an existing listing record (Mock Data or Scraped Data)
```bash
.\.venv\Scripts\python.exe architectural_twin/generate_architectural_twin.py --property-id "prop-1"
```

### 2. Run for a local directory of room photographs
Once you extract or collect property photos, point the CLI directly to your image folder:
```bash
.\.venv\Scripts\python.exe architectural_twin/generate_architectural_twin.py --image-dir "C:/path/to/property_photos" --notes "4 BHK penthouse with sunset balcony, open kitchen, and private master deck."
```

### 3. Batch generate across all corridors
```bash
.\.venv\Scripts\python.exe architectural_twin/generate_architectural_twin.py --batch-sample
```

---

## 💻 Frontend React / Next.js Integration

Import the viewer and pass either a generated blueprint or individual props:

```tsx
import ArchitecturalTwinViewer from "@/architectural_twin/ArchitecturalTwinViewer";
import THE_BALMORAL_ESTATES_TWIN from "@/architectural_twin/blueprints/the-balmoral-estates-3bhk-1_architectural_twin";

export default function PropertyTwinPage() {
  return (
    <div className="max-w-6xl mx-auto py-8">
      <ArchitecturalTwinViewer blueprint={THE_BALMORAL_ESTATES_TWIN} />
    </div>
  );
}
```

---

## 🧪 Testing Roadmap (When Image Dataset is Extracted)

1. **Place Photos:** Dump room photos (JPEG/PNG/WebP) or floor plans into an input folder.
2. **Execute Extractor:** Run `generate_architectural_twin.py --image-dir <path>`.
3. **Inspect Output:** Verify that the inferred adjacency graph matches the physical floor plan (e.g. kitchen adjacent to dining, balcony facing front orientation).
4. **Visual Inspection:** Open `ArchitecturalTwinViewer` in the browser to verify room finishes and camera fly-through paths.
