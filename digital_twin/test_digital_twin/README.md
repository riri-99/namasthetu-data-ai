# Digital Twin Testing Suite & Interactive Prompt Workshop

> **Isolated Testing Directory:** [`digital_twin/test_digital_twin/`](file:///C:/Users/JSC/namasthetu-ai-workers/digital_twin/test_digital_twin/)

This self-contained testing environment allows paired testing of the sovereign 3D digital twin spatial pipeline with **editable user prompts**, real-time BIM compilation, and interactive 3D WebGL rendering.

---

## 📂 File Structure

```
digital_twin/test_digital_twin/
├── preview.html        # Interactive 3D WebGL test preview with editable prompt (zero-server standalone)
├── test_workflow.py    # Automated CLI test suite validating BHK allocation, 3:1 ratio, and BIM mesh
├── build_preview.py    # Generator script for preview.html and embedded flagship blueprints
├── flagship_blueprints.json # Pre-compiled flagship property blueprints (5 BHK Villa, 3 BHK Apts, Dubai)
├── output/             # Output directory storing compiled test blueprints (.json & .ts)
└── README.md           # This documentation
```

---

## 🚀 1. Interactive Visual Prompt Testing in Browser (Zero Server Required)

Simply open [`preview.html`](preview.html) directly in any modern web browser (Chrome, Edge, Firefox, Safari):

```powershell
Start-Process "digital_twin/test_digital_twin/preview.html"
```

- **Features in the Test Interface:**
  - **✏️ Editable Input Prompt Drawer:** Click "Edit Prompt" to open the slide-out workshop drawer. Modify property descriptions in natural language with real-time character count.
  - **Fine-Tune Architectural Overrides:** Adjust BHK count (2, 3, 4, 5 BHK), property archetype (Apartment vs. G+2 Villa), carpet area, primary facing, and amenities (Plunge Pool, Sky Terrace).
  - **Real-Time Client-Side Recompiler:** Click **"⚡ Recompile & Render 3D Twin"** to recompute the BIM geometry and render the 3D scene in milliseconds without requiring any backend server.
  - **Quick Presets:** Switch between pre-compiled flagship properties:
    - *Goodwill Enclave (5 BHK G+2 Villa)*
    - *The Balmoral Estates (3 BHK Apartment)*
    - *Raheja Vistas (3 BHK Apartment)*
    - *Blue Waves Residence (3 BHK Dubai)*
  - **3D Navigation Modes:**
    - **🌐 Orbit Mode:** Free 360° mouse rotation, pan, and zoom.
    - **🚶 Walk Mode:** First-person walkthrough using `W/A/S/D` or Arrow keys.
    - **🎬 Auto-Tour:** Cinematic automated camera path traveling room-by-room.
    - **📐 Cutaway Plan:** Orthographic top-down architectural layout view.
  - **Multi-Level Villa Filter:** For multi-tier properties, toggle between `All Levels`, `Ground`, `1st Floor`, and `2nd Floor`.
  - **Live Verification Badge:** Displays physical bedroom count, verified 3:1 living-to-kitchen ratio, level count, and BIM wall/door/window counts.

---

## 🧪 2. Running the Automated Workflow Test Suite

To run the automated verification suite from the terminal:

```powershell
.\.venv\Scripts\python.exe digital_twin/test_digital_twin/test_workflow.py
```

This tests and verifies:
1. Exact $N$-BHK physical room allocation ($N$ bedrooms matching $N$-BHK specification).
2. Area calibration enforcing the strict 3.0:1 to 3.3:1 Living Hall to Kitchen ratio.
3. Multi-tier G+2 vertical villa elevation levels.
4. Physical BIM wall segments with door openings, sliding glass panels, window sills/mullions, and balconies.
5. Exporting validated blueprints into [`output/`](file:///C:/Users/JSC/namasthetu-ai-workers/digital_twin/test_digital_twin/output/).
