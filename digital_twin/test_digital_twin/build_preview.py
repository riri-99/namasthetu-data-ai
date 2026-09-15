"""
Generates digital_twin/test_digital_twin/preview.html with pre-embedded blueprints
and an interactive declarative schema-to-3D testing workshop.
Includes in-memory procedural spatial synthesis (zero JSON/disk files required)
mirroring DeclarativeSchemaTwinViewer.tsx and digital_twin_engine.py.
"""

import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BLUEPRINTS_FILE = os.path.join(CURRENT_DIR, "flagship_blueprints.json")

blueprints_json = "{}"
if os.path.exists(BLUEPRINTS_FILE):
    with open(BLUEPRINTS_FILE, "r", encoding="utf-8") as f:
        blueprints_json = f.read()

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sovereign 3D Digital Twin Visualizer · Declarative Schema-to-3D</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Inter', sans-serif;
      overflow: hidden;
      user-select: none;
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: rgba(28, 25, 23, 0.6);
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: rgba(120, 113, 108, 0.5);
      border-radius: 9999px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: rgba(217, 119, 6, 0.7);
    }
  </style>
</head>
<body class="bg-stone-950 text-stone-100 h-screen w-screen flex flex-col antialiased">

  <!-- Top Navigation Header -->
  <header class="h-16 border-b border-stone-800 bg-stone-900/95 backdrop-blur-md px-4 flex items-center justify-between z-30 shrink-0 shadow-lg">
    <div class="flex items-center gap-3">
      <div class="h-9 w-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-extrabold text-sm shadow-inner">
        3D
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-sm font-bold tracking-tight text-white" id="headerTitle">Declarative Schema-to-3D Twin</h1>
          <span id="headerBadge" class="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            Zero-File Pipeline (In-Memory)
          </span>
        </div>
        <p class="text-xs text-stone-300" id="headerSubtitle">Procedural geometry synthesized directly from DB schema</p>
      </div>
    </div>

    <!-- Center / Right Header Controls -->
    <div class="flex items-center gap-2">
      <!-- Property Preset Switcher -->
      <div class="flex items-center bg-stone-950/80 border border-stone-700/80 rounded-xl px-2 py-1 shadow-inner">
        <span class="text-[10px] uppercase font-semibold text-stone-400 mr-2">Preset:</span>
        <select id="presetSelect" class="bg-transparent text-xs text-amber-300 font-medium focus:outline-none cursor-pointer pr-1">
          <option value="custom_penthouse">4 BHK Penthouse (Sea View + Jacuzzi + Seepage Pin)</option>
          <option value="custom_villa_g2">5 BHK Sovereign Villa (G+2 + Pool Deck)</option>
          <option value="custom_bare_shell">3 BHK Bare Shell (Unfurnished + Vitrified)</option>
          <option value="the-balmoral-estates-3bhk-1">Balmoral Estates 3BHK (Pre-Calibrated)</option>
          <option value="goodwill-enclave-4-5bhk-191">Goodwill Enclave 5BHK Villa (Pre-Calibrated)</option>
        </select>
      </div>

      <!-- Editable Schema Drawer Button -->
      <button id="btnTogglePromptDrawer" class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-500 text-stone-950 hover:bg-amber-400 shadow-lg shadow-amber-500/20 transition-all">
        <span>⚙️</span> Schema & Prompt
      </button>

      <!-- Staging Toggle -->
      <button id="btnToggleStaging" class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-stone-800/90 border border-stone-700 text-stone-300 hover:text-white transition-all">
        <span id="stagingText">🛋️ Furnished</span>
      </button>

      <!-- Cutaway Plan Toggle -->
      <button id="btnToggleCutaway" class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-stone-800/90 border border-stone-700 text-stone-300 hover:text-white transition-all">
        <span id="cutawayText">📐 Cutaway</span>
      </button>

      <!-- Fullscreen Toggle -->
      <button id="btnFullscreen" class="h-8 w-8 rounded-xl bg-stone-800/90 border border-stone-700 flex items-center justify-center text-stone-300 hover:text-white transition-all" title="Toggle Fullscreen">
        ⛶
      </button>
    </div>
  </header>

  <!-- Main View Area -->
  <div class="flex-1 flex overflow-hidden relative">

    <!-- 3D Three.js Canvas Container -->
    <main id="threeContainer" class="flex-1 h-full w-full relative overflow-hidden bg-stone-950 cursor-grab active:cursor-grabbing">
      <div id="canvasMount" class="w-full h-full"></div>

      <!-- Top Overlay: Multi-Floor Filter (For Multi-Level Villas) -->
      <div id="floorFilterOverlay" class="absolute top-4 left-4 z-10 hidden">
        <div class="flex items-center rounded-xl bg-stone-900/90 p-1 border border-stone-700/80 backdrop-blur-md shadow-xl text-xs gap-1">
          <span class="text-[10px] uppercase font-semibold text-stone-400 px-2">Floor:</span>
          <button data-floor="-1" class="floor-btn px-2.5 py-1 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all">All Levels</button>
          <button data-floor="0" class="floor-btn px-2.5 py-1 rounded-lg text-stone-300 hover:text-white transition-all">Ground</button>
          <button data-floor="1" class="floor-btn px-2.5 py-1 rounded-lg text-stone-300 hover:text-white transition-all">1st Floor</button>
          <button data-floor="2" class="floor-btn px-2.5 py-1 rounded-lg text-stone-300 hover:text-white transition-all">2nd Floor</button>
        </div>
      </div>

      <!-- Top Overlay Right: Camera Modes -->
      <div class="absolute top-4 right-4 z-10">
        <div class="flex items-center rounded-xl bg-stone-900/90 p-1 border border-stone-700/80 backdrop-blur-md shadow-xl text-xs gap-1">
          <button id="btnModeOrbit" class="px-3 py-1.5 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all flex items-center gap-1.5">
            <span>🌐</span> Orbit
          </button>
          <button id="btnModeWalk" class="px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5">
            <span>🚶</span> Walk
          </button>
          <button id="btnModeTour" class="px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5">
            <span>🎬</span> Auto-Tour
          </button>
        </div>
      </div>

      <!-- Bottom Overlay: Room Selection Pills -->
      <div class="absolute bottom-4 left-4 right-4 z-10 pointer-events-none">
        <div class="pointer-events-auto flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none max-w-full">
          <button id="btnRoomAll" class="room-pill px-3 py-1.5 rounded-xl bg-white text-stone-950 font-bold text-xs whitespace-nowrap shadow-lg border border-white">
            Full Residence
          </button>
          <div id="roomPillsContainer" class="flex items-center gap-1.5"></div>
        </div>
      </div>

      <!-- Tour Label Banner -->
      <div id="tourBanner" class="absolute top-16 left-1/2 -translate-x-1/2 z-10 pointer-events-none hidden">
        <div class="flex items-center gap-2 px-4 py-1.5 rounded-full bg-black/85 border border-amber-500/40 text-amber-300 font-semibold text-xs shadow-2xl backdrop-blur-md">
          <span class="h-2 w-2 rounded-full bg-amber-400 animate-ping"></span>
          <span id="tourLabelText">Touring...</span>
        </div>
      </div>

      <!-- Walkthrough Keyboard Hints -->
      <div id="walkInstructions" class="absolute bottom-16 left-1/2 -translate-x-1/2 z-10 pointer-events-none hidden">
        <div class="px-4 py-2 rounded-xl bg-black/80 border border-stone-700 text-stone-300 text-xs shadow-xl backdrop-blur-md flex items-center gap-3">
          <span>🎮 <strong>W/A/S/D</strong> or <strong>Arrows</strong> to walk</span>
          <span>·</span>
          <span><strong>Click + Drag</strong> to look around</span>
        </div>
      </div>

      <!-- Verified Listing Schema & BIM Metrics Card (Right Side) -->
      <div id="aboutNotesCard" class="absolute right-4 top-16 bottom-16 w-80 rounded-2xl bg-stone-900/95 p-4 border border-stone-800 shadow-2xl backdrop-blur-xl flex flex-col justify-between overflow-y-auto z-10 transition-all custom-scrollbar">
        <div class="space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-stone-800">
            <h3 class="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
              <span>📐</span> Schema & BIM Specs
            </h3>
            <button id="btnCloseNotes" class="text-stone-400 hover:text-stone-200 text-xs px-1.5 py-0.5 rounded hover:bg-stone-800">✕</button>
          </div>

          <div class="rounded-xl bg-stone-950/80 p-2.5 border border-stone-800 text-xs text-stone-300 leading-relaxed" id="aboutTextContent">
            Loading architectural model...
          </div>

          <div class="space-y-1.5 text-xs">
            <div class="text-[11px] font-semibold text-stone-400 uppercase tracking-wide">Architectural Conformance</div>
            
            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Suite Count:</span>
              <span id="cardBedrooms" class="font-bold text-emerald-400">4 Physical Suites</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Living : Kitchen Ratio:</span>
              <span id="cardRatio" class="font-bold text-amber-300">3.00 : 1 (Calibrated)</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Elevation Levels:</span>
              <span id="cardLevels" class="font-bold text-stone-200">1 Floor</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">BIM Elements:</span>
              <span id="cardBim" class="font-mono text-stone-300">23 Walls · 6 Doors</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Flooring Specification:</span>
              <span id="cardFlooring" class="font-medium text-amber-200">Italian Statuario Marble</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Furnishing State:</span>
              <span id="cardFurnishing" class="font-medium text-stone-200">Turnkey Staged</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Civil Defect Status:</span>
              <span id="cardDefect" class="font-semibold text-emerald-400">Zero Ingress</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Solar Vector & Temp:</span>
              <span id="cardSunlight" class="font-mono text-xs text-amber-300">East · 5000K</span>
            </div>
          </div>
        </div>

        <div class="pt-2 border-t border-stone-800 text-[11px] text-stone-500 flex items-center justify-between">
          <span class="font-mono text-[10px] text-emerald-400">⚡ In-Memory RAM &lt; 2ms</span>
          <button onclick="document.getElementById('btnTogglePromptDrawer').click()" class="text-amber-400 hover:underline font-semibold">Tweak Schema ✏️</button>
        </div>
      </div>
    </main>

    <!-- SLIDE-OUT EDITABLE PROMPT & SCHEMA WORKSHOP (Left Side) -->
    <aside id="promptDrawer" class="absolute left-0 top-0 bottom-0 w-96 bg-stone-900/98 border-r border-stone-800 shadow-2xl backdrop-blur-2xl z-40 transform -translate-x-full transition-transform duration-300 flex flex-col custom-scrollbar overflow-y-auto">
      <div class="p-4 space-y-4">
        <!-- Drawer Header -->
        <div class="flex items-center justify-between pb-3 border-b border-stone-800">
          <div class="flex items-center gap-2">
            <span class="text-lg">⚙️</span>
            <div>
              <h2 class="text-xs font-bold uppercase tracking-wider text-white">Declarative Schema Controller</h2>
              <p class="text-[10px] text-stone-400">Moulds 3D twin in RAM directly from DB schema context</p>
            </div>
          </div>
          <button id="btnClosePromptDrawer" class="text-stone-400 hover:text-white px-2 py-1 rounded-lg hover:bg-stone-800 text-xs">✕</button>
        </div>

        <!-- Prompt Textarea -->
        <div class="space-y-1.5">
          <label class="text-[11px] font-semibold text-amber-400 flex items-center justify-between">
            <span>Property Prompt / Listing Notes</span>
            <span id="promptCharCount" class="text-[10px] text-stone-500 font-mono">0 chars</span>
          </label>
          <textarea
            id="promptField"
            rows="4"
            class="w-full bg-stone-950 border border-stone-700 rounded-xl p-2.5 text-xs text-stone-100 placeholder-stone-600 focus:outline-none focus:border-amber-500 font-sans leading-relaxed resize-y custom-scrollbar"
            placeholder="Type property notes here (e.g. 4BHK Penthouse with Italian marble and sea view jacuzzi)..."
          ></textarea>
        </div>

        <!-- Prisma Schema Attribute Selectors -->
        <div class="rounded-xl border border-stone-800 bg-stone-950/70 p-3 space-y-3">
          <div class="text-[11px] font-semibold text-stone-300 flex items-center justify-between">
            <span>🏛️ Prisma Schema Fields</span>
            <span class="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">schema.prisma</span>
          </div>

          <!-- Configuration & Archetype -->
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Configuration</label>
              <select id="fieldBHK" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="1">1 BHK</option>
                <option value="2">2 BHK</option>
                <option value="3">3 BHK</option>
                <option value="4" selected>4 BHK</option>
                <option value="5">5 BHK</option>
              </select>
            </div>

            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Property Type</label>
              <select id="fieldArchetype" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="APARTMENT">Apartment (1 Level)</option>
                <option value="PENTHOUSE" selected>Penthouse (Jacuzzi + High Ceiling)</option>
                <option value="VILLA_G1">Villa G+1 (2 Levels)</option>
                <option value="VILLA_G2">Villa G+2 (3 Levels + Pool)</option>
              </select>
            </div>
          </div>

          <!-- Flooring Type & Furnishing Status -->
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">FlooringType</label>
              <select id="fieldFlooring" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="ITALIAN_MARBLE" selected>Italian Marble</option>
                <option value="MARBLE">White Marble</option>
                <option value="WOODEN">Hardwood Oak</option>
                <option value="GRANITE">Honed Granite</option>
                <option value="VITRIFIED_TILES">Vitrified Tiles</option>
                <option value="CERAMIC_TILES">Ceramic Tiles</option>
                <option value="CONCRETE">Concrete Screed</option>
              </select>
            </div>

            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">FurnishingStatus</label>
              <select id="fieldFurnishing" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="FULLY_FURNISHED" selected>Fully Furnished</option>
                <option value="SEMI_FURNISHED">Semi-Furnished (Joinery)</option>
                <option value="UNFURNISHED">Bare Shell (Unfurnished)</option>
              </select>
            </div>
          </div>

          <!-- Facing Direction & Property View -->
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">FacingDirection</label>
              <select id="fieldFacing" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="EAST" selected>East (Morning Sun)</option>
                <option value="NORTH_EAST">North-East (Soft Daylight)</option>
                <option value="WEST">West (Sunset Golden Hour)</option>
                <option value="NORTH">North (Cool Daylight)</option>
                <option value="SOUTH">South (Midday Zenith)</option>
              </select>
            </div>

            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">PropertyView</label>
              <select id="fieldView" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="SEA" selected>Sea / Ocean View</option>
                <option value="GARDEN">Garden & Pool Deck</option>
                <option value="CITY">City Skyline</option>
                <option value="COMMUNITY">Community / Park</option>
              </select>
            </div>
          </div>

          <!-- Carpet Area & Defect Pin -->
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Carpet Area (sq.ft)</label>
              <input type="number" id="fieldCarpet" value="3200" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500" />
            </div>

            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Civil Inspection Pin</label>
              <select id="fieldDefect" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-amber-300 font-medium focus:border-amber-500">
                <option value="NONE">No Defects (Clean)</option>
                <option value="SEEPAGE" selected>⚠️ Seepage Pin (Wall Dampness)</option>
                <option value="CRACK">⚠️ Hairline Crack Pin</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Quick Architecture Presets -->
        <div class="space-y-1.5">
          <label class="text-[10px] font-semibold text-stone-400 uppercase tracking-wider block">Quick Presets</label>
          <div class="grid grid-cols-3 gap-1.5">
            <button type="button" id="btnPresetPenthouse" class="p-2 rounded-lg bg-stone-800/80 hover:bg-stone-700 text-[11px] font-medium text-stone-200 border border-stone-700 text-center transition-all">
              Penthouse
            </button>
            <button type="button" id="btnPresetVilla" class="p-2 rounded-lg bg-stone-800/80 hover:bg-stone-700 text-[11px] font-medium text-stone-200 border border-stone-700 text-center transition-all">
              Villa G+2
            </button>
            <button type="button" id="btnPresetBareShell" class="p-2 rounded-lg bg-stone-800/80 hover:bg-stone-700 text-[11px] font-medium text-stone-200 border border-stone-700 text-center transition-all">
              Bare Shell
            </button>
          </div>
        </div>

        <!-- Recompile & Update Button -->
        <button
          id="btnApplyPrompt"
          class="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-stone-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          <span>⚡</span> Synthesize 3D Twin (In-Memory)
        </button>

        <p class="text-[10px] text-stone-500 leading-relaxed text-center">
          Zero disk I/O · Procedural WebGL geometry generated in RAM &lt; 2ms.
        </p>
      </div>
    </aside>

  </div>

  <script>
    // PRELOADED BLUEPRINTS (Embedded for instant baseline reference)
    const PRELOADED_BLUEPRINTS = __BLUEPRINTS_JSON__;

    // SCHEMA SPECIFICATION CONSTANTS
    const FLOOR_PALETTES = {
      ITALIAN_MARBLE: { floorColor: 0xf4f1ea, floorType: "Italian Statuario & Botticino Marble", wallColor: 0xfaf8f5, roughness: 0.15 },
      MARBLE: { floorColor: 0xfbf9f5, floorType: "Greek Thassos White Marble", wallColor: 0xffffff, roughness: 0.20 },
      WOODEN: { floorColor: 0xc9a275, floorType: "Engineered German Oak Hardwood", wallColor: 0xeae7df, roughness: 0.65 },
      GRANITE: { floorColor: 0x263238, floorType: "Honed Nero Impala Granite & Quartzite", wallColor: 0xf8f8f8, roughness: 0.40 },
      VITRIFIED_TILES: { floorColor: 0xece9e2, floorType: "Matte Vitrified Architectural Tiles (1200x600mm)", wallColor: 0xf1eee7, roughness: 0.55 },
      CERAMIC_TILES: { floorColor: 0xe8ecef, floorType: "Glazed Ceramic Tiles", wallColor: 0xf5f5f3, roughness: 0.50 },
      CONCRETE: { floorColor: 0x8c8c8c, floorType: "Polished Architectural Concrete Screed", wallColor: 0xeceae4, roughness: 0.70 }
    };

    const SUNLIGHT_VECTORS = {
      EAST: { pos: [22, 16, 18], color: 0xfff2de, label: "East · 5000K (Morning Sunrise)" },
      NORTH_EAST: { pos: [16, 18, 16], color: 0xfff5e4, label: "North-East · 5500K (Soft Daylight)" },
      WEST: { pos: [-22, 12, 18], color: 0xffd4a0, label: "West · 3200K (Golden Sunset)" },
      NORTH: { pos: [0, 22, -18], color: 0xe8f0fe, label: "North · 6500K (Cool Diffuse Daylight)" },
      SOUTH: { pos: [8, 26, 8], color: 0xfffee5, label: "South · 5800K (High Zenith Midday)" }
    };

    // Global State
    let currentBlueprint = null;
    let activeMode = 'orbit';
    let isStaged = true;
    let isTopDown = false;
    let currentFloorFilter = -1;

    // Three.js instances
    let scene, camera, renderer, sunLight, hemiLight;
    let animId = null;
    let stagedGroup, structuralGroup, defectGroup;

    // Camera animation targets
    let curT = [0, 1.4, 0], tgtT = [0, 1.4, 0];
    let curTh = 0.72, tgtTh = 0.72;
    let curPhi = 1.05, tgtPhi = 1.05;
    let curR = 28.0, tgtR = 28.0;

    // Tour state
    let tourIdx = 0, tourSubT = 0;

    // Mouse controls
    let isDragging = false, prevMouseX = 0, prevMouseY = 0;
    const keysPressed = {};

    // DOM Elements
    const presetSelect = document.getElementById('presetSelect');
    const headerTitle = document.getElementById('headerTitle');
    const headerSubtitle = document.getElementById('headerSubtitle');
    const aboutTextContent = document.getElementById('aboutTextContent');
    const cardBedrooms = document.getElementById('cardBedrooms');
    const cardRatio = document.getElementById('cardRatio');
    const cardLevels = document.getElementById('cardLevels');
    const cardBim = document.getElementById('cardBim');
    const cardFlooring = document.getElementById('cardFlooring');
    const cardFurnishing = document.getElementById('cardFurnishing');
    const cardDefect = document.getElementById('cardDefect');
    const cardSunlight = document.getElementById('cardSunlight');
    const roomPillsContainer = document.getElementById('roomPillsContainer');
    const floorFilterOverlay = document.getElementById('floorFilterOverlay');
    const tourBanner = document.getElementById('tourBanner');
    const tourLabelText = document.getElementById('tourLabelText');
    const walkInstructions = document.getElementById('walkInstructions');

    const promptDrawer = document.getElementById('promptDrawer');
    const btnTogglePromptDrawer = document.getElementById('btnTogglePromptDrawer');
    const btnClosePromptDrawer = document.getElementById('btnClosePromptDrawer');
    const promptField = document.getElementById('promptField');
    const promptCharCount = document.getElementById('promptCharCount');
    const fieldBHK = document.getElementById('fieldBHK');
    const fieldArchetype = document.getElementById('fieldArchetype');
    const fieldFlooring = document.getElementById('fieldFlooring');
    const fieldFurnishing = document.getElementById('fieldFurnishing');
    const fieldFacing = document.getElementById('fieldFacing');
    const fieldView = document.getElementById('fieldView');
    const fieldCarpet = document.getElementById('fieldCarpet');
    const fieldDefect = document.getElementById('fieldDefect');
    const btnApplyPrompt = document.getElementById('btnApplyPrompt');

    // Material Library
    let M = {};

    function initMaterials() {
      M = {
        ground: new THREE.MeshLambertMaterial({ color: 0xc4beaf }),
        road: new THREE.MeshLambertMaterial({ color: 0xded9cf }),
        cream: new THREE.MeshLambertMaterial({ color: 0xf1eee7 }),
        cream2: new THREE.MeshLambertMaterial({ color: 0xe7e3da }),
        slab: new THREE.MeshLambertMaterial({ color: 0xece9e2 }),
        wood: new THREE.MeshLambertMaterial({ color: 0xb9824e }),
        wood2: new THREE.MeshLambertMaterial({ color: 0xa87042 }),
        woodFloor: new THREE.MeshLambertMaterial({ color: 0xc9a275 }),
        walnut: new THREE.MeshLambertMaterial({ color: 0x5d4037 }),
        glass: new THREE.MeshPhongMaterial({ color: 0x1e242b, transparent: true, opacity: 0.42, shininess: 95 }),
        rail: new THREE.MeshPhongMaterial({ color: 0xdfe4e6, transparent: true, opacity: 0.35, shininess: 90 }),
        pool: new THREE.MeshPhongMaterial({ color: 0x0f2b36, transparent: true, opacity: 0.85, shininess: 100 }),
        water: new THREE.MeshPhongMaterial({ color: 0x207289, transparent: true, opacity: 0.75, shininess: 120 }),
        dark: new THREE.MeshLambertMaterial({ color: 0x2b2e35 }),
        sofa: new THREE.MeshLambertMaterial({ color: 0xd9d1c0 }),
        bed: new THREE.MeshLambertMaterial({ color: 0xf4f1ea }),
        accent: new THREE.MeshLambertMaterial({ color: 0xc9a66b }),
        rug: new THREE.MeshLambertMaterial({ color: 0xcabfa8 }),
        counter: new THREE.MeshLambertMaterial({ color: 0x8d6f50 }),
        white: new THREE.MeshLambertMaterial({ color: 0xfbf9f5 }),
        leaf: new THREE.MeshLambertMaterial({ color: 0x8e9c74 }),
        trunk: new THREE.MeshLambertMaterial({ color: 0x84745c }),
        grey1: new THREE.MeshLambertMaterial({ color: 0xd8d4cb }),
        grey2: new THREE.MeshLambertMaterial({ color: 0xcbc6bc }),
        conduit: new THREE.MeshLambertMaterial({ color: 0xd97706 }),
        plumbing: new THREE.MeshLambertMaterial({ color: 0x0284c7 }),
        defectRed: new THREE.MeshBasicMaterial({ color: 0xef4444 }),
        defectPulse: new THREE.MeshBasicMaterial({ color: 0xf87171, wireframe: true, transparent: true, opacity: 0.8 })
      };
    }

    function createBox(w, h, d, mat, x, y, z, ry = 0, parent = scene) {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
      mesh.position.set(x, y, z);
      if (ry) mesh.rotation.y = ry;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      parent.add(mesh);
      return mesh;
    }

    function initThreeScene() {
      const mount = document.getElementById('canvasMount');
      const w = mount.clientWidth || window.innerWidth;
      const h = mount.clientHeight || (window.innerHeight - 64);

      scene = new THREE.Scene();
      const fogColor = 0xd5cfc4;
      scene.background = new THREE.Color(fogColor);
      scene.fog = new THREE.Fog(fogColor, 50, 160);

      camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 400);

      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.0;

      mount.innerHTML = '';
      mount.appendChild(renderer.domElement);

      hemiLight = new THREE.HemisphereLight(0xfff5e6, 0xa39b8d, 0.75);
      scene.add(hemiLight);

      sunLight = new THREE.DirectionalLight(0xffeed6, 1.1);
      sunLight.position.set(22, 28, 20);
      sunLight.castShadow = true;
      sunLight.shadow.mapSize.set(1024, 1024);
      Object.assign(sunLight.shadow.camera, { left: -45, right: 45, top: 45, bottom: -45, far: 150 });
      scene.add(sunLight);

      initMaterials();

      stagedGroup = new THREE.Group();
      structuralGroup = new THREE.Group();
      defectGroup = new THREE.Group();
      scene.add(stagedGroup);
      scene.add(structuralGroup);
      scene.add(defectGroup);

      // Ground Plane & Road
      const g = new THREE.Mesh(new THREE.PlaneGeometry(280, 280), M.ground);
      g.rotation.x = -Math.PI / 2;
      g.receiveShadow = true;
      scene.add(g);

      const r = new THREE.Mesh(new THREE.PlaneGeometry(16, 280), M.road);
      r.rotation.x = -Math.PI / 2;
      r.position.set(0, 0.02, 0);
      r.rotation.z = Math.PI / 2;
      r.receiveShadow = true;
      scene.add(r);

      // Surrounding Landscaping Trees
      for (let t = 0; t < 16; t++) {
        const a = (t / 16) * Math.PI * 2 + 0.1;
        const rad = 24 + (t % 4) * 6;
        const x = Math.cos(a) * rad;
        const z = Math.sin(a) * rad;
        const th = 1.0 + (t % 3) * 0.4;
        const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, th, 6), M.trunk);
        tr.position.set(x, th / 2, z);
        scene.add(tr);
        const cr = new THREE.Mesh(new THREE.SphereGeometry(0.85 + (t % 3) * 0.35, 10, 8), M.leaf);
        cr.position.set(x, th + 0.65, z);
        scene.add(cr);
      }

      setupEventListeners(renderer.domElement);
      startAnimationLoop();
    }

    function setupEventListeners(dom) {
      dom.addEventListener('mousedown', (e) => {
        if (activeMode === 'tour') return;
        isDragging = true;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      });

      window.addEventListener('mousemove', (e) => {
        if (!isDragging || activeMode === 'tour') return;
        const dx = e.clientX - prevMouseX;
        const dy = e.clientY - prevMouseY;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;

        if (isTopDown) {
          tgtT[0] -= dx * 0.04;
          tgtT[2] -= dy * 0.04;
        } else {
          tgtTh -= dx * 0.007;
          tgtPhi = Math.max(0.15, Math.min(Math.PI / 2 - 0.05, tgtPhi + dy * 0.005));
        }
      });

      window.addEventListener('mouseup', () => { isDragging = false; });

      dom.addEventListener('wheel', (e) => {
        e.preventDefault();
        if (activeMode === 'tour') return;
        tgtR = Math.max(5, Math.min(70, tgtR + e.deltaY * 0.035));
      }, { passive: false });

      window.addEventListener('keydown', (e) => { keysPressed[e.key.toLowerCase()] = true; });
      window.addEventListener('keyup', (e) => { keysPressed[e.key.toLowerCase()] = false; });

      window.addEventListener('resize', () => {
        const mount = document.getElementById('canvasMount');
        if (!mount || !renderer) return;
        const nw = mount.clientWidth;
        const nh = mount.clientHeight;
        camera.aspect = nw / nh;
        camera.updateProjectionMatrix();
        renderer.setSize(nw, nh);
      });
    }

    function startAnimationLoop() {
      let pulseCounter = 0;

      const animate = () => {
        animId = requestAnimationFrame(animate);

        stagedGroup.visible = isStaged;

        pulseCounter += 0.05;
        if (defectGroup.children.length > 0) {
          const s = 1.0 + Math.sin(pulseCounter * 2) * 0.25;
          defectGroup.children.forEach(c => {
            if (c.userData && c.userData.isPulseRing) {
              c.scale.set(s, s, s);
            }
          });
        }

        if (activeMode === 'walk') {
          const walkSpeed = 0.12;
          const forward = new THREE.Vector3();
          camera.getWorldDirection(forward);
          forward.y = 0;
          forward.normalize();

          const right = new THREE.Vector3();
          right.crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

          if (keysPressed['w'] || keysPressed['arrowup']) {
            tgtT[0] += forward.x * walkSpeed;
            tgtT[2] += forward.z * walkSpeed;
          }
          if (keysPressed['s'] || keysPressed['arrowdown']) {
            tgtT[0] -= forward.x * walkSpeed;
            tgtT[2] -= forward.z * walkSpeed;
          }
          if (keysPressed['a'] || keysPressed['arrowleft']) {
            tgtT[0] -= right.x * walkSpeed;
            tgtT[2] -= right.z * walkSpeed;
          }
          if (keysPressed['d'] || keysPressed['arrowright']) {
            tgtT[0] += right.x * walkSpeed;
            tgtT[2] -= right.z * walkSpeed;
          }
        }

        if (activeMode === 'tour' && currentBlueprint && currentBlueprint.waypoints) {
          const wps = currentBlueprint.waypoints;
          tourSubT += 0.0035;
          if (tourSubT >= 1.0) {
            tourSubT = 0;
            tourIdx = (tourIdx + 1) % wps.length;
            tourLabelText.textContent = wps[tourIdx].label || 'Cinematic Tour';
          }

          const currWp = wps[tourIdx] || wps[0];
          const nextWp = wps[(tourIdx + 1) % wps.length] || wps[0];

          const factor = (1 - Math.cos(tourSubT * Math.PI)) / 2;
          const px = currWp.p[0] + (nextWp.p[0] - currWp.p[0]) * factor;
          const py = currWp.p[1] + (nextWp.p[1] - currWp.p[1]) * factor;
          const pz = currWp.p[2] + (nextWp.p[2] - currWp.p[2]) * factor;

          const lx = currWp.l[0] + (nextWp.l[0] - currWp.l[0]) * factor;
          const ly = currWp.l[1] + (nextWp.l[1] - currWp.l[1]) * factor;
          const lz = currWp.l[2] + (nextWp.l[2] - currWp.l[2]) * factor;

          camera.position.set(px, py, pz);
          camera.lookAt(lx, ly, lz);
        } else {
          curT[0] += (tgtT[0] - curT[0]) * 0.08;
          curT[1] += (tgtT[1] - curT[1]) * 0.08;
          curT[2] += (tgtT[2] - curT[2]) * 0.08;

          curTh += (tgtTh - curTh) * 0.08;
          curPhi += (tgtPhi - curPhi) * 0.08;
          curR += (tgtR - curR) * 0.08;

          const camX = curT[0] + curR * Math.sin(curPhi) * Math.sin(curTh);
          const camY = curT[1] + curR * Math.cos(curPhi);
          const camZ = curT[2] + curR * Math.sin(curPhi) * Math.cos(curTh);

          camera.position.set(camX, camY, camZ);
          camera.lookAt(curT[0], curT[1], curT[2]);
        }

        renderer.render(scene, camera);
      };

      animate();
    }

    // ========================================================================
    // DECLARATIVE IN-MEMORY PROCEDURAL COMPILER (ZERO-FILE PIPELINE)
    // ========================================================================
    function synthesizeDigitalTwinInRAM(schema) {
      const bhk = parseInt(schema.bhk) || 3;
      const archetype = schema.archetype || 'APARTMENT';
      const flooringKey = schema.flooring || 'ITALIAN_MARBLE';
      const furnishing = schema.furnishing || 'FULLY_FURNISHED';
      const facing = schema.facing || 'EAST';
      const view = schema.view || 'SEA';
      const defect = schema.defect || 'NONE';
      const carpetArea = parseInt(schema.carpetArea) || 2800;

      const floorPalette = FLOOR_PALETTES[flooringKey] || FLOOR_PALETTES.ITALIAN_MARBLE;
      const hexFloor = "#" + floorPalette.floorColor.toString(16).padStart(6, '0');
      const hexWall = "#" + floorPalette.wallColor.toString(16).padStart(6, '0');

      const isPenthouse = archetype === 'PENTHOUSE';
      const isVillaG1 = archetype === 'VILLA_G1';
      const isVillaG2 = archetype === 'VILLA_G2';
      const isMultiFloor = isVillaG1 || isVillaG2;
      const levelsCount = isVillaG2 ? 3 : (isVillaG1 ? 2 : 1);

      const wallHeight = isPenthouse ? 3.6 : 3.0;

      const rooms = [];
      const structuralWalls = [];
      const doors = [];
      const windows = [];
      const balconies = [];
      const glassPanels = [];
      const focalTargets = {};
      const waypoints = [];

      // Calibrated Layout Dimensions (Strict 3:1 Living:Kitchen Ratio)
      // Living Room: 6.8m x 5.0m (34 sqm ~ 366 sqft)
      // Kitchen: 3.4m x 3.3m (11.2 sqm ~ 120 sqft) -> Ratio 366/120 = 3.05:1
      const livingW = 6.8, livingD = 5.0;
      const kitchenW = 3.4, kitchenD = 3.3;

      // 1. Living & Dining Grand Salon
      const livingFurniture = [];
      if (furnishing === 'FULLY_FURNISHED') {
        livingFurniture.push(
          { id: 'f_sofa_main', name: 'Italian Sectional Sofa', size: [2.8, 0.75, 1.1], position: [-1.2, 0.45, 0.8], materialKey: 'sofa' },
          { id: 'f_sofa_chaise', name: 'Chaise Extension', size: [1.0, 0.65, 1.6], position: [0.6, 0.45, 1.1], materialKey: 'sofa' },
          { id: 'f_coffee_table', name: 'Marble Coffee Table', size: [1.4, 0.38, 0.8], position: [-0.6, 0.25, 0.8], materialKey: 'slab' },
          { id: 'f_tv_console', name: 'Low Profile Media Credenza', size: [3.0, 0.45, 0.45], position: [-0.8, 0.3, -1.9], materialKey: 'dark' },
          { id: 'f_dining_table', name: 'Oak Dining Table 8-Seater', size: [2.2, 0.76, 1.1], position: [1.8, 0.45, -0.6], materialKey: 'wood' },
          { id: 'f_dining_chair1', name: 'Dining Chair Set', size: [2.2, 0.85, 0.45], position: [1.8, 0.5, -1.25], materialKey: 'dark' },
          { id: 'f_dining_chair2', name: 'Dining Chair Set', size: [2.2, 0.85, 0.45], position: [1.8, 0.5, 0.05], materialKey: 'dark' }
        );
      } else if (furnishing === 'SEMI_FURNISHED') {
        livingFurniture.push(
          { id: 'f_tv_backpanel', name: 'Architectural Fluted TV Wall Paneling', size: [3.4, 2.6, 0.12], position: [-0.8, 1.3, -2.0], materialKey: 'wood2' }
        );
      } else {
        livingFurniture.push(
          { id: 'f_conduit_trace', name: 'Ceiling Electrical Conduit Run', size: [4.5, 0.06, 0.06], position: [0, wallHeight - 0.1, 0], materialKey: 'conduit' },
          { id: 'f_floor_junction', name: 'Floor Utility Terminal Box', size: [0.3, 0.08, 0.3], position: [-0.8, 0.2, -1.5], materialKey: 'dark' }
        );
      }

      rooms.push({
        id: 'living',
        name: 'Grand Salon & Dining',
        carpetSqft: 366,
        floorLevel: 0,
        floorColor: hexFloor,
        wallColor: hexWall,
        bounds: { x: 0, y: 0, z: 0, w: livingW, d: livingD, h: wallHeight },
        furniture: livingFurniture,
        lights: [
          { type: 'ambient', color: '#fff5e6', intensity: 0.9, position: [0, wallHeight - 0.3, 0] },
          { type: 'point', color: '#ffeed6', intensity: 0.8, distance: 12, position: [1.8, wallHeight - 0.4, -0.6] }
        ]
      });

      focalTargets['living'] = { target: [0, 1.2, 0], theta: 0.72, phi: 1.05, radius: 14, walk: [0, 1.65, 2.8] };

      // 2. Chef's Modular Kitchen (Ratio Calibrated 3.05 : 1)
      const kitchenFurniture = [];
      if (furnishing !== 'UNFURNISHED') {
        kitchenFurniture.push(
          { id: 'f_kitchen_counter', name: 'Quartz Breakfast Counter', size: [kitchenW - 0.4, 0.92, 0.75], position: [4.4, 0.52, -1.9], materialKey: 'counter' },
          { id: 'f_kitchen_island', name: 'Modular Island Unit', size: [1.6, 0.9, 0.9], position: [4.4, 0.52, -0.4], materialKey: 'dark' }
        );
      } else {
        kitchenFurniture.push(
          { id: 'f_plumbing_chase', name: 'Rough-in Drainage & Water Risers', size: [0.4, 1.2, 0.3], position: [4.6, 0.6, -2.0], materialKey: 'plumbing' }
        );
      }

      rooms.push({
        id: 'kitchen',
        name: "Chef's Modular Kitchen",
        carpetSqft: 120,
        floorLevel: 0,
        floorColor: hexFloor,
        wallColor: hexWall,
        bounds: { x: 4.4, y: 0, z: -1.0, w: kitchenW, d: kitchenD, h: wallHeight },
        furniture: kitchenFurniture,
        lights: [{ type: 'point', color: '#ffffff', intensity: 0.9, distance: 8, position: [4.4, wallHeight - 0.3, -1.0] }]
      });

      focalTargets['kitchen'] = { target: [4.4, 1.0, -1.0], theta: 0.9, phi: 0.95, radius: 9, walk: [3.2, 1.65, -0.5] };

      // 3. Master Suite & Bedrooms
      const bedroomConfigs = [
        { id: 'master_bedroom', name: 'Primary Royal Suite', x: -4.8, z: 0.5, w: 4.2, d: 4.4, sqft: 280, lvl: 0 },
        { id: 'bedroom_2', name: 'Executive Guest Suite', x: -4.8, z: -3.8, w: 3.8, d: 3.6, sqft: 210, lvl: (isMultiFloor ? 1 : 0) },
        { id: 'bedroom_3', name: 'Courtyard Bedroom', x: 4.4, z: 2.2, w: 3.4, d: 3.6, sqft: 185, lvl: (isMultiFloor ? 1 : 0) },
        { id: 'bedroom_4', name: 'Garden Suite', x: 0, z: 4.4, w: 4.0, d: 3.4, sqft: 195, lvl: (isVillaG2 ? 2 : (isMultiFloor ? 1 : 0)) },
        { id: 'bedroom_5', name: 'Penthouse / Sky Suite', x: -4.0, z: 4.4, w: 3.8, d: 3.4, sqft: 180, lvl: (isVillaG2 ? 2 : 0) }
      ];

      for (let i = 0; i < Math.min(bhk, bedroomConfigs.length); i++) {
        const bc = bedroomConfigs[i];
        const bf = [];
        if (furnishing === 'FULLY_FURNISHED') {
          bf.push(
            { id: `f_bed_${bc.id}`, name: 'King Platform Bed', size: [2.1, 0.7, 2.0], position: [bc.x, 0.42, bc.z - 0.5], materialKey: 'bed' },
            { id: `f_wardrobe_${bc.id}`, name: 'Fluted Glass Wardrobe', size: [2.4, 2.4, 0.65], position: [bc.x + bc.w / 2 - 0.4, 1.25, bc.z + 0.8], materialKey: 'dark' }
          );
        } else if (furnishing === 'SEMI_FURNISHED') {
          bf.push(
            { id: `f_wardrobe_built_${bc.id}`, name: 'Full-Height Built-in Modular Joinery', size: [2.4, wallHeight - 0.2, 0.6], position: [bc.x + bc.w / 2 - 0.35, wallHeight / 2, bc.z + 0.8], materialKey: 'wood2' }
          );
        } else {
          bf.push(
            { id: `f_conduit_${bc.id}`, name: 'HVAC & Lighting Rough-in Conduit', size: [2.2, 0.06, 0.06], position: [bc.x, wallHeight - 0.1, bc.z], materialKey: 'conduit' }
          );
        }

        rooms.push({
          id: bc.id,
          name: bc.name,
          carpetSqft: bc.sqft,
          floorLevel: bc.lvl,
          floorColor: hexFloor,
          wallColor: hexWall,
          bounds: { x: bc.x, y: bc.lvl * 3.4, z: bc.z, w: bc.w, d: bc.d, h: wallHeight },
          furniture: bf,
          lights: [{ type: 'point', color: '#ffeed6', intensity: 0.8, distance: 9, position: [bc.x, bc.lvl * 3.4 + wallHeight - 0.3, bc.z] }]
        });

        focalTargets[bc.id] = { target: [bc.x, bc.lvl * 3.4 + 1.2, bc.z], theta: 0.6, phi: 1.0, radius: 10, walk: [bc.x + 1.2, bc.lvl * 3.4 + 1.65, bc.z + 1.2] };
      }

      // 4. Sky Terrace / Plunge Pool / Jacuzzi for Penthouse & Villas
      if (isPenthouse || view === 'SEA') {
        balconies.push({
          id: 'balc_sky_terrace',
          floorLevel: 0,
          bounds: { x: 0, y: 0, z: -3.8, w: 6.8, d: 2.2, h: 0.25 },
          railings: [
            { position: [0, 0.55, -4.85], size: [6.8, 1.1], rotationY: 0, handrail: true },
            { position: [-3.35, 0.55, -3.8], size: [2.2, 1.1], rotationY: Math.PI / 2, handrail: true },
            { position: [3.35, 0.55, -3.8], size: [2.2, 1.1], rotationY: Math.PI / 2, handrail: true }
          ]
        });

        // Sky Jacuzzi
        rooms.push({
          id: 'sky_jacuzzi',
          name: 'Infinity Horizon Sky Jacuzzi',
          carpetSqft: 150,
          floorLevel: 0,
          floorColor: '#0f2b36',
          wallColor: hexWall,
          bounds: { x: 2.0, y: 0.1, z: -3.8, w: 2.2, d: 1.8, h: 0.7 },
          furniture: [
            { id: 'f_jacuzzi_water', name: 'Heated Hydrotherapy Jacuzzi', size: [2.0, 0.5, 1.6], position: [2.0, 0.35, -3.8], materialKey: 'water' }
          ],
          lights: [{ type: 'point', color: '#38bdf8', intensity: 1.2, distance: 6, position: [2.0, 1.2, -3.8] }]
        });
        focalTargets['sky_jacuzzi'] = { target: [2.0, 0.5, -3.8], theta: 1.2, phi: 0.9, radius: 7, walk: [0.5, 1.65, -3.2] };
      } else if (isVillaG2 || isVillaG1 || view === 'GARDEN') {
        balconies.push({
          id: 'balc_pool_deck',
          floorLevel: 0,
          bounds: { x: 0, y: 0, z: -4.4, w: 8.0, d: 3.2, h: 0.25 },
          railings: [
            { position: [0, 0.55, -5.95], size: [8.0, 1.1], rotationY: 0, handrail: true }
          ]
        });

        // Swimming Pool
        rooms.push({
          id: 'pool_deck',
          name: 'Sunken Azure Pool Deck',
          carpetSqft: 260,
          floorLevel: 0,
          floorColor: '#0f2b36',
          wallColor: hexWall,
          bounds: { x: 0, y: 0.05, z: -4.4, w: 5.2, d: 2.4, h: 0.4 },
          furniture: [
            { id: 'f_pool_water', name: 'Crystal Lap Pool', size: [5.0, 0.3, 2.2], position: [0, 0.2, -4.4], materialKey: 'water' }
          ],
          lights: [{ type: 'point', color: '#0284c7', intensity: 1.1, distance: 10, position: [0, 1.5, -4.4] }]
        });
        focalTargets['pool_deck'] = { target: [0, 0.4, -4.4], theta: 0.72, phi: 0.9, radius: 10, walk: [0, 1.65, -2.8] };
      }

      // 5. Structural BIM Walls
      structuralWalls.push(
        { position: [0, wallHeight / 2, 2.5], size: [livingW, wallHeight, 0.2], floorLevel: 0, isExterior: true, materialKey: 'cream2' },
        { position: [-livingW / 2, wallHeight / 2, 0], size: [0.2, wallHeight, livingD], floorLevel: 0, isExterior: false, materialKey: 'cream' },
        { position: [livingW / 2, wallHeight / 2, 0.8], size: [0.2, wallHeight, 3.4], floorLevel: 0, isExterior: false, materialKey: 'cream' },
        { position: [4.4, wallHeight / 2, -2.65], size: [kitchenW, wallHeight, 0.2], floorLevel: 0, isExterior: true, materialKey: 'cream2' },
        { position: [4.4 + kitchenW / 2, wallHeight / 2, -1.0], size: [0.2, wallHeight, kitchenD], floorLevel: 0, isExterior: true, materialKey: 'cream2' },
        { position: [-4.8, wallHeight / 2, 2.7], size: [4.2, wallHeight, 0.2], floorLevel: 0, isExterior: true, materialKey: 'cream2' },
        { position: [-6.9, wallHeight / 2, 0.5], size: [0.2, wallHeight, 4.4], floorLevel: 0, isExterior: true, materialKey: 'cream2' }
      );

      if (isMultiFloor) {
        structuralWalls.push(
          { position: [-4.8, 3.4 + wallHeight / 2, -3.8], size: [3.8, wallHeight, 0.2], floorLevel: 1, isExterior: true, materialKey: 'cream2' },
          { position: [4.4, 3.4 + wallHeight / 2, 2.2], size: [3.4, wallHeight, 0.2], floorLevel: 1, isExterior: true, materialKey: 'cream2' }
        );
      }
      if (isVillaG2) {
        structuralWalls.push(
          { position: [0, 6.8 + wallHeight / 2, 4.4], size: [4.0, wallHeight, 0.2], floorLevel: 2, isExterior: true, materialKey: 'cream2' }
        );
      }

      // 6. Doors & Sliders
      doors.push(
        { position: [0, 1.2, -2.5], size: [2.6, 2.4, 0.12], floorLevel: 0, doorType: 'sliding', openAngle: 0.8 },
        { position: [-3.4, 1.1, 0.2], size: [0.95, 2.2, 0.1], floorLevel: 0, doorType: 'hinged', openAngle: 0.45 },
        { position: [3.4, 1.1, -1.0], size: [1.2, 2.2, 0.1], floorLevel: 0, doorType: 'pocket', openAngle: 0.6 }
      );

      // 7. Panoramic Windows
      windows.push(
        { position: [-1.8, 1.4, 2.5], size: [2.8, 2.2, 0.15], floorLevel: 0, rotationY: 0, hasMullions: true },
        { position: [-4.8, 1.4, 2.7], size: [2.4, 2.0, 0.15], floorLevel: 0, rotationY: 0, hasMullions: true }
      );

      // 8. Civil Inspection Defect Pin
      const defects = [];
      if (defect === 'SEEPAGE') {
        defects.push({
          id: 'defect_seepage_01',
          type: 'SEEPAGE',
          severity: 'MODERATE',
          description: 'Capillary water ingress trace detected on North-East partition wall',
          position: [-3.3, 1.4, -0.4],
          roomId: 'master_bedroom'
        });
        focalTargets['defect_seepage_01'] = { target: [-3.3, 1.4, -0.4], theta: 0.45, phi: 1.1, radius: 4.5, walk: [-2.2, 1.65, -0.4] };
      } else if (defect === 'CRACK') {
        defects.push({
          id: 'defect_crack_01',
          type: 'WALL_CRACK',
          severity: 'LOW',
          description: 'Hairline plaster shrinkage crack along column junction',
          position: [3.3, 1.6, 0.8],
          roomId: 'living'
        });
        focalTargets['defect_crack_01'] = { target: [3.3, 1.6, 0.8], theta: 1.1, phi: 1.0, radius: 4.5, walk: [2.2, 1.65, 0.8] };
      }

      // Waypoints for Auto-Tour
      waypoints.push(
        { p: [0, 1.6, 3.2], l: [0, 1.2, 0], label: 'Grand Salon & Dining Area' },
        { p: [3.2, 1.6, -0.5], l: [4.4, 1.1, -1.2], label: "Chef's Modular Kitchen (3:1 Ratio)" },
        { p: [-3.2, 1.6, 0.5], l: [-4.8, 1.2, 0.5], label: 'Primary Royal Bedroom Suite' }
      );
      if (defects.length > 0) {
        waypoints.push({ p: [defects[0].position[0] + 1.2, 1.5, defects[0].position[2]], l: defects[0].position, label: `Civil Audit Defect: ${defects[0].type}` });
      }

      focalTargets['all'] = { target: [0, 1.5, 0], theta: 0.72, phi: 1.05, radius: 26, walk: [0, 1.65, 3.5] };

      return {
        propertyTitle: `${bhk} BHK ${archetype.replace('_', ' ')} · ${floorPalette.floorType}`,
        propertyType: archetype,
        configuration: `${bhk} BHK`,
        bhkCount: bhk,
        carpetSqft: carpetArea,
        orientation: `${facing}-Facing`,
        archetype: archetype,
        levelsCount: levelsCount,
        flooringType: flooringKey,
        furnishingStatus: furnishing,
        facingDirection: facing,
        defects: defects,
        aboutSummary: schema.prompt || `Procedural spatial model compiled dynamically from Prisma schema with ${floorPalette.floorType}, ${furnishing.replace('_', ' ').toLowerCase()} staging, and facing ${facing.toLowerCase()}.`,
        rooms: rooms,
        structuralWalls: structuralWalls,
        doors: doors,
        windows: windows,
        balconies: balconies,
        glassPanels: glassPanels,
        focalTargets: focalTargets,
        waypoints: waypoints
      };
    }

    // ========================================================================
    // RENDER BLUEPRINT SCENE GRAPH
    // ========================================================================
    function renderBlueprintInScene(bp) {
      currentBlueprint = bp;

      while (stagedGroup.children.length > 0) stagedGroup.remove(stagedGroup.children[0]);
      while (structuralGroup.children.length > 0) structuralGroup.remove(structuralGroup.children[0]);
      while (defectGroup.children.length > 0) defectGroup.remove(defectGroup.children[0]);

      if (!bp || !bp.rooms || bp.rooms.length === 0) return;

      // Adjust Dynamic Sun Lighting according to FacingDirection
      const facingKey = bp.facingDirection || 'EAST';
      const sunSpec = SUNLIGHT_VECTORS[facingKey] || SUNLIGHT_VECTORS.EAST;
      if (sunLight) {
        sunLight.position.set(sunSpec.pos[0], sunSpec.pos[1], sunSpec.pos[2]);
        sunLight.color.setHex(sunSpec.color);
      }

      // 1. Foundation Slab
      let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
      bp.rooms.forEach(r => {
        const b = r.bounds;
        minX = Math.min(minX, b.x - b.w / 2);
        maxX = Math.max(maxX, b.x + b.w / 2);
        minZ = Math.min(minZ, b.z - b.d / 2);
        maxZ = Math.max(maxZ, b.z + b.d / 2);
      });
      const totalW = Math.max(22, maxX - minX + 4);
      const totalD = Math.max(16, maxZ - minZ + 4);
      const centerX = (minX + maxX) / 2;
      const centerZ = (minZ + maxZ) / 2;

      createBox(totalW, 0.4, totalD, M.slab, centerX, 0.2, centerZ, 0, structuralGroup);

      // 2. Room Floors & Furniture
      bp.rooms.forEach(r => {
        const b = r.bounds;
        const hex = parseInt(r.floorColor.replace("#", ""), 16) || 0xf4f1ea;
        const roomFloorMat = new THREE.MeshLambertMaterial({ color: hex });

        const floorMesh = createBox(b.w, 0.28, b.d, roomFloorMat, b.x, b.y + 0.14, b.z, 0, structuralGroup);
        floorMesh.userData = { floorLevel: r.floorLevel ?? 0, type: 'floor', roomId: r.id };

        // Skirting
        const skirtH = 0.08, skirtT = 0.04;
        createBox(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z - b.d / 2 + skirtT / 2, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
        createBox(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z + b.d / 2 - skirtT / 2, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
        createBox(skirtT, skirtH, b.d, M.cream2, b.x - b.w / 2 + skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
        createBox(skirtT, skirtH, b.d, M.cream2, b.x + b.w / 2 - skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };

        // Furniture / Stage
        r.furniture?.forEach(item => {
          const [w, h, d] = item.size;
          const [x, y, z] = item.position;
          const mat = M[item.materialKey] || M.cream;
          const fMesh = createBox(w, h, d, mat, x, y, z, item.rotationY || 0, stagedGroup);
          fMesh.userData = { floorLevel: r.floorLevel ?? 0, type: 'furniture' };
        });

        // Room Lights
        r.lights?.forEach(light => {
          const col = parseInt(light.color.replace("#", ""), 16) || 0xffd9a0;
          const pl = new THREE.PointLight(col, light.intensity || 0.85, light.distance || 12);
          pl.position.set(light.position[0], light.position[1], light.position[2]);
          pl.userData = { floorLevel: r.floorLevel ?? 0 };
          structuralGroup.add(pl);
        });
      });

      // 3. BIM Walls
      bp.structuralWalls?.forEach(w => {
        const [sx, sy, sz] = w.size;
        const [px, py, pz] = w.position;
        const mat = w.isExterior ? M.cream2 : (M[w.materialKey] || M.cream);
        const wallMesh = createBox(sx, sy, sz, mat, px, py, pz, 0, structuralGroup);
        wallMesh.userData = { floorLevel: w.floorLevel ?? 0, type: 'wall', isExterior: w.isExterior };
      });

      // 4. Doors & Sliders
      bp.doors?.forEach(d => {
        const [dx, dy, dz] = d.position;
        const [dw, dh, dd] = d.size;
        const rotY = d.rotationY || 0;
        const doorGroup = new THREE.Group();
        doorGroup.position.set(dx, dy, dz);
        doorGroup.rotation.y = rotY;
        doorGroup.userData = { floorLevel: d.floorLevel ?? 0, type: 'door' };

        if (d.doorType === 'sliding') {
          const frameMat = M.dark;
          createBox(dw, 0.08, 0.12, frameMat, 0, dh / 2 - 0.04, 0, 0, doorGroup);
          createBox(dw, 0.08, 0.12, frameMat, 0, -dh / 2 + 0.04, 0, 0, doorGroup);
          createBox(0.08, dh, 0.12, frameMat, -dw / 2 + 0.04, 0, 0, 0, doorGroup);
          createBox(0.08, dh, 0.12, frameMat, dw / 2 - 0.04, 0, 0, 0, doorGroup);

          const panelW = dw / 2.0 - 0.04;
          const g1 = new THREE.Mesh(new THREE.PlaneGeometry(panelW, dh - 0.16), M.glass);
          g1.position.set(-dw / 4, 0, -0.02);
          doorGroup.add(g1);
          const g2 = new THREE.Mesh(new THREE.PlaneGeometry(panelW, dh - 0.16), M.glass);
          g2.position.set(dw / 4, 0, 0.02);
          doorGroup.add(g2);
        } else {
          const frameMat = M.dark;
          createBox(0.06, dh, dd * 1.1, frameMat, -dw / 2 + 0.03, 0, 0, 0, doorGroup);
          createBox(0.06, dh, dd * 1.1, frameMat, dw / 2 - 0.03, 0, 0, 0, doorGroup);
          createBox(dw, 0.06, dd * 1.1, frameMat, 0, dh / 2 - 0.03, 0, 0, doorGroup);

          const leafW = dw - 0.12;
          const leafH = dh - 0.08;
          const leafGroup = new THREE.Group();
          leafGroup.position.set(-dw / 2 + 0.06, 0, 0);
          leafGroup.rotation.y = d.openAngle || 0.45;

          const leafMesh = createBox(leafW, leafH, 0.04, M.wood2, leafW / 2, 0, 0, 0, leafGroup);
          leafMesh.castShadow = true;

          const handle = createBox(0.04, 0.12, 0.08, M.accent, leafW - 0.08, 0, 0.04, 0, leafGroup);
          handle.castShadow = true;
          doorGroup.add(leafGroup);
        }

        structuralGroup.add(doorGroup);
      });

      // 5. Windows
      bp.windows?.forEach(win => {
        const [wx, wy, wz] = win.position;
        const [ww, wh] = win.size;
        const rotY = win.rotationY || 0;
        const winGroup = new THREE.Group();
        winGroup.position.set(wx, wy, wz);
        winGroup.rotation.y = rotY;
        winGroup.userData = { floorLevel: win.floorLevel ?? 0, type: 'window' };

        const frameMat = M.dark;
        createBox(ww, 0.06, 0.16, frameMat, 0, wh / 2 - 0.03, 0, 0, winGroup);
        createBox(ww, 0.08, 0.22, M.cream2, 0, -wh / 2 + 0.04, 0.03, 0, winGroup);
        createBox(0.06, wh, 0.16, frameMat, -ww / 2 + 0.03, 0, 0, 0, winGroup);
        createBox(0.06, wh, 0.16, frameMat, ww / 2 - 0.03, 0, 0, 0, winGroup);

        if (win.hasMullions) {
          createBox(0.04, wh, 0.14, frameMat, 0, 0, 0, 0, winGroup);
          createBox(ww, 0.04, 0.14, frameMat, 0, wh * 0.15, 0, 0, winGroup);
        }

        const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(ww - 0.12, wh - 0.12), M.glass);
        winGroup.add(glassMesh);
        structuralGroup.add(winGroup);
      });

      // 6. Balconies & Decks
      bp.balconies?.forEach(balc => {
        const b = balc.bounds;
        const deckMesh = createBox(b.w, b.h, b.d, M.wood2, b.x, b.y + b.h / 2, b.z, 0, structuralGroup);
        deckMesh.userData = { floorLevel: balc.floorLevel, type: 'balcony' };

        balc.railings?.forEach(rail => {
          const [rx, ry, rz] = rail.position;
          const [rw, rh] = rail.size;
          const rRotY = rail.rotationY || 0;
          const rGroup = new THREE.Group();
          rGroup.position.set(rx, ry, rz);
          rGroup.rotation.y = rRotY;
          rGroup.userData = { floorLevel: balc.floorLevel, type: 'railing' };

          const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(rw, rh), M.rail);
          rGroup.add(glassMesh);

          if (rail.handrail) {
            createBox(rw, 0.05, 0.08, M.dark, 0, rh / 2 - 0.025, 0, 0, rGroup);
            createBox(0.04, rh, 0.04, M.dark, -rw / 2 + 0.02, 0, 0, 0, rGroup);
            createBox(0.04, rh, 0.04, M.dark, rw / 2 - 0.02, 0, 0, 0, rGroup);
          }

          structuralGroup.add(rGroup);
        });
      });

      // 7. Civil Inspection Defect Pins (Pulsating 3D Beacons)
      bp.defects?.forEach(def => {
        const [px, py, pz] = def.position;
        const pinGroup = new THREE.Group();
        pinGroup.position.set(px, py, pz);

        const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), M.defectRed);
        pinGroup.add(sphere);

        const ring = new THREE.Mesh(new THREE.SphereGeometry(0.36, 12, 8), M.defectPulse);
        ring.userData = { isPulseRing: true };
        pinGroup.add(ring);

        const pinStem = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.4), M.dark);
        pinStem.position.set(0, -0.2, 0);
        pinGroup.add(pinStem);

        defectGroup.add(pinGroup);
      });

      updateUI(bp);
      focusRoom('all');
    }

    function updateUI(bp) {
      headerTitle.textContent = bp.propertyTitle || "Sovereign Digital Twin";
      headerSubtitle.textContent = `${bp.configuration || "3 BHK"} · ${bp.levelsCount || 1} Level · ${bp.carpetSqft ? bp.carpetSqft.toLocaleString() : "2,500"} sq.ft · ${bp.orientation || "East-Facing"}`;
      aboutTextContent.textContent = bp.aboutSummary || "Spatial model compiled from verified listing data.";

      cardBedrooms.textContent = `${bp.bhkCount || 3} Physical Suites`;
      
      const living = bp.rooms?.find(r => r.id === 'living');
      const kitchen = bp.rooms?.find(r => r.id === 'kitchen');
      if (living && kitchen && kitchen.carpetSqft > 0) {
        const ratio = (living.carpetSqft / kitchen.carpetSqft).toFixed(2);
        cardRatio.textContent = `${ratio} : 1 (Calibrated)`;
      } else {
        cardRatio.textContent = "3.00 : 1";
      }

      cardLevels.textContent = `${bp.levelsCount || 1} Level (${bp.archetype || "Apartment"})`;
      const defectCount = bp.defects?.length || 0;
      cardBim.textContent = `${bp.structuralWalls?.length || 0} Walls · ${bp.doors?.length || 0} Doors · ${defectCount} Defects`;

      const floorInfo = FLOOR_PALETTES[bp.flooringType] || FLOOR_PALETTES.ITALIAN_MARBLE;
      cardFlooring.textContent = floorInfo.floorType.split('&')[0].trim();
      cardFurnishing.textContent = (bp.furnishingStatus || 'FULLY_FURNISHED').replace('_', ' ');

      if (defectCount > 0) {
        cardDefect.className = "font-bold text-rose-400 flex items-center gap-1";
        cardDefect.innerHTML = `<span>⚠️</span> ${bp.defects[0].type} (${bp.defects[0].severity})`;
      } else {
        cardDefect.className = "font-semibold text-emerald-400";
        cardDefect.textContent = "Zero Ingress (Audited)";
      }

      const sunSpec = SUNLIGHT_VECTORS[bp.facingDirection || 'EAST'] || SUNLIGHT_VECTORS.EAST;
      cardSunlight.textContent = sunSpec.label;

      if (bp.levelsCount > 1) {
        floorFilterOverlay.classList.remove('hidden');
      } else {
        floorFilterOverlay.classList.add('hidden');
      }

      // Room Pills
      roomPillsContainer.innerHTML = '';
      bp.rooms?.forEach((room) => {
        const pill = document.createElement('button');
        pill.className = 'room-pill px-3 py-1.5 rounded-xl bg-stone-900/85 text-stone-300 hover:bg-stone-800 text-xs font-medium whitespace-nowrap shadow border border-stone-700/70 transition-all';
        pill.textContent = room.name;
        pill.addEventListener('click', () => {
          document.querySelectorAll('.room-pill').forEach(p => {
            p.classList.remove('bg-amber-500', 'text-stone-950', 'font-bold', 'border-amber-400');
            p.classList.add('bg-stone-900/85', 'text-stone-300');
          });
          pill.classList.remove('bg-stone-900/85', 'text-stone-300');
          pill.classList.add('bg-amber-500', 'text-stone-950', 'font-bold', 'border-amber-400');
          focusRoom(room.id);
        });
        roomPillsContainer.appendChild(pill);
      });

      // Defect Pin Pills
      bp.defects?.forEach((def) => {
        const defPill = document.createElement('button');
        defPill.className = 'room-pill px-3 py-1.5 rounded-xl bg-rose-500/20 text-rose-300 border border-rose-500/50 hover:bg-rose-500/30 text-xs font-bold whitespace-nowrap shadow transition-all flex items-center gap-1';
        defPill.innerHTML = `<span>⚠️</span> ${def.type}`;
        defPill.addEventListener('click', () => {
          document.querySelectorAll('.room-pill').forEach(p => {
            p.classList.remove('bg-amber-500', 'text-stone-950', 'font-bold', 'border-amber-400');
            p.classList.add('bg-stone-900/85', 'text-stone-300');
          });
          defPill.classList.add('bg-amber-500', 'text-stone-950');
          focusRoom(def.id);
        });
        roomPillsContainer.appendChild(defPill);
      });

      // Synchronize drawer controls
      promptField.value = bp.aboutSummary || "";
      promptCharCount.textContent = `${promptField.value.length} chars`;
      if (bp.bhkCount) fieldBHK.value = bp.bhkCount.toString();
      if (bp.archetype) fieldArchetype.value = bp.archetype;
      if (bp.carpetSqft) fieldCarpet.value = bp.carpetSqft;
      if (bp.flooringType) fieldFlooring.value = bp.flooringType;
      if (bp.furnishingStatus) fieldFurnishing.value = bp.furnishingStatus;
      if (bp.facingDirection) fieldFacing.value = bp.facingDirection;
      if (defectCount > 0) {
        fieldDefect.value = bp.defects[0].type === 'SEEPAGE' ? 'SEEPAGE' : 'CRACK';
      } else {
        fieldDefect.value = 'NONE';
      }
    }

    function focusRoom(roomId) {
      if (!currentBlueprint) return;
      const targets = currentBlueprint.focalTargets || {};
      const focal = targets[roomId] || targets['all'] || { target: [0, 1.5, 0], theta: 0.72, phi: 1.05, radius: 24, walk: [0, 1.65, 3.5] };

      if (activeMode === 'walk') {
        tgtT = [focal.walk[0], focal.walk[1], focal.walk[2]];
        tgtR = 4.5;
        tgtPhi = Math.PI / 2 - 0.05;
      } else {
        tgtT = [focal.target[0], focal.target[1], focal.target[2]];
        tgtTh = focal.theta;
        tgtPhi = focal.phi;
        tgtR = focal.radius;
      }
    }

    function applyFloorFilter(floorIdx) {
      currentFloorFilter = floorIdx;
      document.querySelectorAll('.floor-btn').forEach(btn => {
        if (parseInt(btn.dataset.floor) === floorIdx) {
          btn.className = 'floor-btn px-2.5 py-1 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all';
        } else {
          btn.className = 'floor-btn px-2.5 py-1 rounded-lg text-stone-300 hover:text-white transition-all';
        }
      });

      const filterActive = floorIdx >= 0;
      scene.traverse(obj => {
        if (obj.userData && obj.userData.floorLevel !== undefined) {
          obj.visible = filterActive ? obj.userData.floorLevel === floorIdx : true;
        }
      });
    }

    // Switch presets
    presetSelect.addEventListener('change', () => {
      const val = presetSelect.value;
      if (val === 'custom_penthouse') {
        applyPresetPenthouse();
      } else if (val === 'custom_villa_g2') {
        applyPresetVilla();
      } else if (val === 'custom_bare_shell') {
        applyPresetBareShell();
      } else if (PRELOADED_BLUEPRINTS[val]) {
        renderBlueprintInScene(PRELOADED_BLUEPRINTS[val]);
      }
    });

    function applyPresetPenthouse() {
      fieldBHK.value = '4';
      fieldArchetype.value = 'PENTHOUSE';
      fieldFlooring.value = 'ITALIAN_MARBLE';
      fieldFurnishing.value = 'FULLY_FURNISHED';
      fieldFacing.value = 'EAST';
      fieldView.value = 'SEA';
      fieldCarpet.value = '3400';
      fieldDefect.value = 'SEEPAGE';
      promptField.value = '4 BHK Sea View Penthouse with Italian statuario marble, heated sky jacuzzi, and capillary seepage pin on north wall.';
      btnApplyPrompt.click();
    }

    function applyPresetVilla() {
      fieldBHK.value = '5';
      fieldArchetype.value = 'VILLA_G2';
      fieldFlooring.value = 'ITALIAN_MARBLE';
      fieldFurnishing.value = 'FULLY_FURNISHED';
      fieldFacing.value = 'NORTH_EAST';
      fieldView.value = 'GARDEN';
      fieldCarpet.value = '4200';
      fieldDefect.value = 'NONE';
      promptField.value = '5 BHK Sovereign Villa G+2 with double-height salon, private pool deck, and Italian marble throughout.';
      btnApplyPrompt.click();
    }

    function applyPresetBareShell() {
      fieldBHK.value = '3';
      fieldArchetype.value = 'APARTMENT';
      fieldFlooring.value = 'VITRIFIED_TILES';
      fieldFurnishing.value = 'UNFURNISHED';
      fieldFacing.value = 'WEST';
      fieldView.value = 'CITY';
      fieldCarpet.value = '2100';
      fieldDefect.value = 'NONE';
      promptField.value = '3 BHK Bare Shell Unfurnished with 1200x600 vitrified tiles and exposed electrical rough-in conduit traces.';
      btnApplyPrompt.click();
    }

    document.getElementById('btnPresetPenthouse').addEventListener('click', applyPresetPenthouse);
    document.getElementById('btnPresetVilla').addEventListener('click', applyPresetVilla);
    document.getElementById('btnPresetBareShell').addEventListener('click', applyPresetBareShell);

    // Prompt Drawer open/close
    btnTogglePromptDrawer.addEventListener('click', () => {
      promptDrawer.classList.toggle('-translate-x-full');
    });

    btnClosePromptDrawer.addEventListener('click', () => {
      promptDrawer.classList.add('-translate-x-full');
    });

    document.getElementById('btnCloseNotes').addEventListener('click', () => {
      document.getElementById('aboutNotesCard').classList.toggle('hidden');
    });

    promptField.addEventListener('input', () => {
      promptCharCount.textContent = `${promptField.value.length} chars`;
    });

    // Staging toggle
    document.getElementById('btnToggleStaging').addEventListener('click', () => {
      isStaged = !isStaged;
      document.getElementById('stagingText').textContent = isStaged ? '🛋️ Furnished' : '🪵 Bare Shell';
    });

    // Cutaway top-down toggle
    document.getElementById('btnToggleCutaway').addEventListener('click', () => {
      isTopDown = !isTopDown;
      if (isTopDown) {
        tgtPhi = 0.04;
        tgtR = 38;
      } else {
        tgtPhi = 1.05;
        tgtR = 26;
      }
    });

    // Fullscreen toggle
    document.getElementById('btnFullscreen').addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });

    // Camera Mode Switchers
    document.getElementById('btnModeOrbit').addEventListener('click', () => {
      activeMode = 'orbit';
      isTopDown = false;
      tourBanner.classList.add('hidden');
      walkInstructions.classList.add('hidden');
      document.getElementById('btnModeOrbit').className = 'px-3 py-1.5 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all flex items-center gap-1.5';
      document.getElementById('btnModeWalk').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      document.getElementById('btnModeTour').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      focusRoom('all');
    });

    document.getElementById('btnModeWalk').addEventListener('click', () => {
      activeMode = 'walk';
      isTopDown = false;
      tourBanner.classList.add('hidden');
      walkInstructions.classList.remove('hidden');
      document.getElementById('btnModeWalk').className = 'px-3 py-1.5 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all flex items-center gap-1.5';
      document.getElementById('btnModeOrbit').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      document.getElementById('btnModeTour').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      focusRoom('living');
    });

    document.getElementById('btnModeTour').addEventListener('click', () => {
      activeMode = 'tour';
      isTopDown = false;
      tourIdx = 0;
      tourSubT = 0;
      tourBanner.classList.remove('hidden');
      walkInstructions.classList.add('hidden');
      document.getElementById('btnModeTour').className = 'px-3 py-1.5 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all flex items-center gap-1.5';
      document.getElementById('btnModeOrbit').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      document.getElementById('btnModeWalk').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
    });

    document.getElementById('btnRoomAll').addEventListener('click', () => {
      document.querySelectorAll('.room-pill').forEach(p => {
        p.classList.remove('bg-amber-500', 'text-stone-950', 'font-bold', 'border-amber-400');
        p.classList.add('bg-stone-900/85', 'text-stone-300');
      });
      document.getElementById('btnRoomAll').className = 'room-pill px-3 py-1.5 rounded-xl bg-white text-stone-950 font-bold text-xs whitespace-nowrap shadow-lg border border-white';
      focusRoom('all');
    });

    document.querySelectorAll('.floor-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        applyFloorFilter(parseInt(btn.dataset.floor));
      });
    });

    // In-Memory Declarative Compilation Execution (Zero-File)
    btnApplyPrompt.addEventListener('click', () => {
      const customPrompt = promptField.value.trim();
      const selectedBHK = fieldBHK.value;
      const selectedArchetype = fieldArchetype.value;
      const selectedFlooring = fieldFlooring.value;
      const selectedFurnishing = fieldFurnishing.value;
      const selectedFacing = fieldFacing.value;
      const selectedView = fieldView.value;
      const selectedCarpet = fieldCarpet.value;
      const selectedDefect = fieldDefect.value;

      const t0 = performance.now();
      const synthesizedBlueprint = synthesizeDigitalTwinInRAM({
        prompt: customPrompt,
        bhk: selectedBHK,
        archetype: selectedArchetype,
        flooring: selectedFlooring,
        furnishing: selectedFurnishing,
        facing: selectedFacing,
        view: selectedView,
        carpetArea: selectedCarpet,
        defect: selectedDefect
      });
      const t1 = performance.now();

      renderBlueprintInScene(synthesizedBlueprint);
      promptDrawer.classList.add('-translate-x-full');

      console.log(`Synthesized Declarative 3D Twin in ${(t1 - t0).toFixed(2)}ms with ZERO disk I/O.`);
    });

    // Initialize on DOM Ready
    window.addEventListener('DOMContentLoaded', () => {
      initThreeScene();
      applyPresetPenthouse();
    });
  </script>
</body>
</html>
"""

html_content = HTML_TEMPLATE.replace("__BLUEPRINTS_JSON__", blueprints_json)

output_html = os.path.join(CURRENT_DIR, "preview.html")
with open(output_html, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Generated self-contained declarative preview app at: {output_html} ({len(html_content):,} bytes)")
