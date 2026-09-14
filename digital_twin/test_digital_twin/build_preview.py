"""
Generates digital_twin/test_digital_twin/preview.html with pre-embedded blueprints
and an interactive editable input prompt testing interface.
"""

import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BLUEPRINTS_FILE = os.path.join(CURRENT_DIR, "flagship_blueprints.json")

with open(BLUEPRINTS_FILE, "r", encoding="utf-8") as f:
    blueprints_json = f.read()

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sovereign 3D Digital Twin Visualizer · Interactive Test Preview</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{
      font-family: 'Inter', sans-serif;
      overflow: hidden;
      user-select: none;
    }}
    .custom-scrollbar::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    .custom-scrollbar::-webkit-scrollbar-track {{
      background: rgba(28, 25, 23, 0.6);
    }}
    .custom-scrollbar::-webkit-scrollbar-thumb {{
      background: rgba(120, 113, 108, 0.5);
      border-radius: 9999px;
    }}
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {{
      background: rgba(217, 119, 6, 0.7);
    }}
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
          <h1 class="text-sm font-bold tracking-tight text-white" id="headerTitle">Digital Twin Spatial Visualizer</h1>
          <span id="headerBadge" class="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            BIM Calibrated
          </span>
        </div>
        <p class="text-xs text-stone-300" id="headerSubtitle">Loading architectural specification...</p>
      </div>
    </div>

    <!-- Center / Right Header Controls -->
    <div class="flex items-center gap-2">
      <!-- Property Switcher Dropdown -->
      <div class="flex items-center bg-stone-950/80 border border-stone-700/80 rounded-xl px-2 py-1 shadow-inner">
        <span class="text-[10px] uppercase font-semibold text-stone-400 mr-2">Property:</span>
        <select id="propertySelect" class="bg-transparent text-xs text-amber-300 font-medium focus:outline-none cursor-pointer pr-1">
          <option value="goodwill-enclave-4-5bhk-191">Goodwill Enclave (5 BHK G+2 Villa)</option>
          <option value="the-balmoral-estates-3bhk-1">The Balmoral Estates (3 BHK Apartment)</option>
          <option value="raheja-vistas-3bhk-5">Raheja Vistas (3 BHK Apartment)</option>
          <option value="blue-waves-residence-2-3bhk-2501">Blue Waves (3 BHK Dubai)</option>
        </select>
      </div>

      <!-- Editable Prompt Button -->
      <button id="btnTogglePromptDrawer" class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-500 text-stone-950 hover:bg-amber-400 shadow-lg shadow-amber-500/20 transition-all">
        <span>✏️</span> Edit Prompt
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

      <!-- Top Overlay: Multi-Floor Filter (For Villas) -->
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

      <!-- Verified Listing About Notes & Calibration Card (Right Side Drawer) -->
      <div id="aboutNotesCard" class="absolute right-4 top-16 bottom-16 w-80 rounded-2xl bg-stone-900/95 p-4 border border-stone-800 shadow-2xl backdrop-blur-xl flex flex-col justify-between overflow-y-auto z-10 transition-all">
        <div class="space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-stone-800">
            <h3 class="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
              <span>📋</span> Verified Listing "About"
            </h3>
            <button id="btnCloseNotes" class="text-stone-400 hover:text-stone-200 text-xs px-1.5 py-0.5 rounded hover:bg-stone-800">✕</button>
          </div>

          <div class="rounded-xl bg-stone-950/80 p-2.5 border border-stone-800 text-xs text-stone-300 leading-relaxed" id="aboutTextContent">
            Loading notes...
          </div>

          <div class="space-y-1.5 text-xs">
            <div class="text-[11px] font-semibold text-stone-400 uppercase tracking-wide">Architectural Calibration</div>
            
            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Bedroom Allocation:</span>
              <span id="cardBedrooms" class="font-bold text-emerald-400">4 Physical Suites</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Living : Kitchen Ratio:</span>
              <span id="cardRatio" class="font-bold text-amber-300">3.09 : 1 (Calibrated)</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">Elevation Levels:</span>
              <span id="cardLevels" class="font-bold text-stone-200">G+2 (3 Floors)</span>
            </div>

            <div class="flex items-center justify-between bg-stone-950/60 p-2 rounded-lg border border-stone-800">
              <span class="text-stone-400">BIM Geometry:</span>
              <span id="cardBim" class="font-mono text-stone-300">56 Walls · 9 Doors · 8 Wins</span>
            </div>
          </div>
        </div>

        <div class="pt-2 border-t border-stone-800 text-[11px] text-stone-500 flex items-center justify-between">
          <span>Civil Audit: 9.6/10</span>
          <button onclick="document.getElementById('btnTogglePromptDrawer').click()" class="text-amber-400 hover:underline font-semibold">Tweak Prompt ✏️</button>
        </div>
      </div>
    </main>

    <!-- SLIDE-OUT EDITABLE PROMPT WORKSHOP (Left Side) -->
    <aside id="promptDrawer" class="absolute left-0 top-0 bottom-0 w-96 bg-stone-900/98 border-r border-stone-800 shadow-2xl backdrop-blur-2xl z-40 transform -translate-x-full transition-transform duration-300 flex flex-col custom-scrollbar overflow-y-auto">
      <div class="p-4 space-y-4">
        <!-- Drawer Header -->
        <div class="flex items-center justify-between pb-3 border-b border-stone-800">
          <div class="flex items-center gap-2">
            <span class="text-lg">✏️</span>
            <div>
              <h2 class="text-xs font-bold uppercase tracking-wider text-white">Editable Input Prompt</h2>
              <p class="text-[10px] text-stone-400">Modify description to recompile 3D twin</p>
            </div>
          </div>
          <button id="btnClosePromptDrawer" class="text-stone-400 hover:text-white px-2 py-1 rounded-lg hover:bg-stone-800 text-xs">✕</button>
        </div>

        <!-- Prompt Textarea -->
        <div class="space-y-1.5">
          <label class="text-[11px] font-semibold text-amber-400 flex items-center justify-between">
            <span>Property Description Notes</span>
            <span id="promptCharCount" class="text-[10px] text-stone-500 font-mono">0 chars</span>
          </label>
          <textarea
            id="promptField"
            rows="6"
            class="w-full bg-stone-950 border border-stone-700 rounded-xl p-3 text-xs text-stone-100 placeholder-stone-600 focus:outline-none focus:border-amber-500 font-sans leading-relaxed resize-y custom-scrollbar"
            placeholder="Type your property notes here..."
          ></textarea>
        </div>

        <!-- Architectural Overrides -->
        <div class="rounded-xl border border-stone-800 bg-stone-950/70 p-3 space-y-3">
          <div class="text-[11px] font-semibold text-stone-300">⚙️ Fine-Tune Architectural Attributes</div>

          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Configuration</label>
              <select id="fieldBHK" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="2">2 BHK</option>
                <option value="3">3 BHK</option>
                <option value="4" selected>4 BHK</option>
                <option value="5">5 BHK</option>
              </select>
            </div>

            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Archetype</label>
              <select id="fieldArchetype" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="apartment">Apartment (1 Level)</option>
                <option value="villa_g2">Villa G+2 (3 Levels + Pool)</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Carpet Area (sq.ft)</label>
              <input type="number" id="fieldCarpet" value="3800" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500" />
            </div>

            <div>
              <label class="text-[10px] text-stone-400 block mb-0.5">Primary Facing</label>
              <select id="fieldFacing" class="w-full bg-stone-900 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200 focus:border-amber-500">
                <option value="East">East-Facing</option>
                <option value="North-East">North-East-Facing</option>
                <option value="West">West-Facing</option>
                <option value="South">South-Facing</option>
              </select>
            </div>
          </div>

          <!-- Feature Flags -->
          <div class="pt-1 flex flex-wrap gap-2 text-xs">
            <label class="flex items-center gap-1.5 text-stone-400 cursor-pointer hover:text-stone-200">
              <input type="checkbox" id="fieldPool" checked class="rounded bg-stone-900 border-stone-700 text-amber-500 focus:ring-0" />
              <span>Plunge Pool</span>
            </label>
            <label class="flex items-center gap-1.5 text-stone-400 cursor-pointer hover:text-stone-200">
              <input type="checkbox" id="fieldTerrace" checked class="rounded bg-stone-900 border-stone-700 text-amber-500 focus:ring-0" />
              <span>Sky Terrace</span>
            </label>
          </div>
        </div>

        <!-- Recompile & Update Button -->
        <button
          id="btnApplyPrompt"
          class="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-stone-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          <span>⚡</span> Apply & Re-Render 3D Twin
        </button>

        <p class="text-[10px] text-stone-500 leading-relaxed text-center">
          Changes take effect immediately with full BIM geometry recalculation.
        </p>
      </div>
    </aside>

  </div>

  <script>
    // PRELOADED BLUEPRINTS (Embedded directly to guarantee instant zero-latency loading)
    const PRELOADED_BLUEPRINTS = {blueprints_json};

    // Global State
    let currentBlueprint = null;
    let activeMode = 'orbit';
    let isStaged = true;
    let isTopDown = false;
    let currentFloorFilter = -1;

    // Three.js instances
    let scene, camera, renderer;
    let animId = null;
    let stagedGroup, structuralGroup;

    // Camera animation targets
    let curT = [0, 1.4, 0], tgtT = [0, 1.4, 0];
    let curTh = 0.72, tgtTh = 0.72;
    let curPhi = 1.05, tgtPhi = 1.05;
    let curR = 28.0, tgtR = 28.0;

    // Tour state
    let tourIdx = 0, tourSubT = 0;

    // Mouse controls
    let isDragging = false, prevMouseX = 0, prevMouseY = 0;
    const keysPressed = {{}};

    // DOM Elements
    const propertySelect = document.getElementById('propertySelect');
    const headerTitle = document.getElementById('headerTitle');
    const headerSubtitle = document.getElementById('headerSubtitle');
    const aboutTextContent = document.getElementById('aboutTextContent');
    const cardBedrooms = document.getElementById('cardBedrooms');
    const cardRatio = document.getElementById('cardRatio');
    const cardLevels = document.getElementById('cardLevels');
    const cardBim = document.getElementById('cardBim');
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
    const fieldCarpet = document.getElementById('fieldCarpet');
    const fieldFacing = document.getElementById('fieldFacing');
    const fieldPool = document.getElementById('fieldPool');
    const fieldTerrace = document.getElementById('fieldTerrace');
    const btnApplyPrompt = document.getElementById('btnApplyPrompt');

    // Material Library
    let M = {{}};

    function initMaterials() {{
      M = {{
        ground: new THREE.MeshLambertMaterial({{ color: 0xc4beaf }}),
        road: new THREE.MeshLambertMaterial({{ color: 0xded9cf }}),
        cream: new THREE.MeshLambertMaterial({{ color: 0xf1eee7 }}),
        cream2: new THREE.MeshLambertMaterial({{ color: 0xe7e3da }}),
        slab: new THREE.MeshLambertMaterial({{ color: 0xece9e2 }}),
        wood: new THREE.MeshLambertMaterial({{ color: 0xb9824e }}),
        wood2: new THREE.MeshLambertMaterial({{ color: 0xa87042 }}),
        woodFloor: new THREE.MeshLambertMaterial({{ color: 0xc9a275 }}),
        walnut: new THREE.MeshLambertMaterial({{ color: 0x5d4037 }}),
        glass: new THREE.MeshPhongMaterial({{ color: 0x1e242b, transparent: true, opacity: 0.42, shininess: 95 }}),
        rail: new THREE.MeshPhongMaterial({{ color: 0xdfe4e6, transparent: true, opacity: 0.35, shininess: 90 }}),
        pool: new THREE.MeshPhongMaterial({{ color: 0x0f2b36, transparent: true, opacity: 0.85, shininess: 100 }}),
        water: new THREE.MeshPhongMaterial({{ color: 0x207289, transparent: true, opacity: 0.75, shininess: 120 }}),
        dark: new THREE.MeshLambertMaterial({{ color: 0x2b2e35 }}),
        sofa: new THREE.MeshLambertMaterial({{ color: 0xd9d1c0 }}),
        bed: new THREE.MeshLambertMaterial({{ color: 0xf4f1ea }}),
        accent: new THREE.MeshLambertMaterial({{ color: 0xc9a66b }}),
        rug: new THREE.MeshLambertMaterial({{ color: 0xcabfa8 }}),
        counter: new THREE.MeshLambertMaterial({{ color: 0x8d6f50 }}),
        white: new THREE.MeshLambertMaterial({{ color: 0xfbf9f5 }}),
        leaf: new THREE.MeshLambertMaterial({{ color: 0x8e9c74 }}),
        trunk: new THREE.MeshLambertMaterial({{ color: 0x84745c }}),
        grey1: new THREE.MeshLambertMaterial({{ color: 0xd8d4cb }}),
        grey2: new THREE.MeshLambertMaterial({{ color: 0xcbc6bc }}),
      }};
    }}

    function createBox(w, h, d, mat, x, y, z, ry = 0, parent = scene) {{
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
      mesh.position.set(x, y, z);
      if (ry) mesh.rotation.y = ry;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      parent.add(mesh);
      return mesh;
    }}

    function initThreeScene() {{
      const mount = document.getElementById('canvasMount');
      const w = mount.clientWidth || window.innerWidth;
      const h = mount.clientHeight || (window.innerHeight - 64);

      scene = new THREE.Scene();
      const fogColor = 0xd5cfc4;
      scene.background = new THREE.Color(fogColor);
      scene.fog = new THREE.Fog(fogColor, 50, 160);

      camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 400);

      renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: 'high-performance' }});
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.0;

      mount.innerHTML = '';
      mount.appendChild(renderer.domElement);

      scene.add(new THREE.HemisphereLight(0xfff5e6, 0xa39b8d, 0.75));
      const sun = new THREE.DirectionalLight(0xffeed6, 1.05);
      sun.position.set(32, 50, 24);
      sun.castShadow = true;
      sun.shadow.mapSize.set(1024, 1024);
      Object.assign(sun.shadow.camera, {{ left: -45, right: 45, top: 45, bottom: -45, far: 150 }});
      scene.add(sun);

      initMaterials();

      stagedGroup = new THREE.Group();
      structuralGroup = new THREE.Group();
      scene.add(stagedGroup);
      scene.add(structuralGroup);

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

      // Trees
      for (let t = 0; t < 18; t++) {{
        const a = (t / 18) * Math.PI * 2 + 0.1;
        const rad = 22 + (t % 4) * 6;
        const x = Math.cos(a) * rad;
        const z = Math.sin(a) * rad;
        const th = 1.0 + (t % 3) * 0.4;
        const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, th, 6), M.trunk);
        tr.position.set(x, th / 2, z);
        scene.add(tr);
        const cr = new THREE.Mesh(new THREE.SphereGeometry(0.85 + (t % 3) * 0.35, 10, 8), M.leaf);
        cr.position.set(x, th + 0.65, z);
        scene.add(cr);
      }}

      setupEventListeners(renderer.domElement);
      startAnimationLoop();
    }}

    function setupEventListeners(dom) {{
      dom.addEventListener('mousedown', (e) => {{
        if (activeMode === 'tour') return;
        isDragging = true;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      }});

      window.addEventListener('mousemove', (e) => {{
        if (!isDragging || activeMode === 'tour') return;
        const dx = e.clientX - prevMouseX;
        const dy = e.clientY - prevMouseY;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;

        if (isTopDown) {{
          tgtT[0] -= dx * 0.04;
          tgtT[2] -= dy * 0.04;
        }} else {{
          tgtTh -= dx * 0.007;
          tgtPhi = Math.max(0.15, Math.min(Math.PI / 2 - 0.05, tgtPhi + dy * 0.005));
        }}
      }});

      window.addEventListener('mouseup', () => {{ isDragging = false; }});

      dom.addEventListener('wheel', (e) => {{
        e.preventDefault();
        if (activeMode === 'tour') return;
        tgtR = Math.max(5, Math.min(70, tgtR + e.deltaY * 0.035));
      }}, {{ passive: false }});

      window.addEventListener('keydown', (e) => {{ keysPressed[e.key.toLowerCase()] = true; }});
      window.addEventListener('keyup', (e) => {{ keysPressed[e.key.toLowerCase()] = false; }});

      window.addEventListener('resize', () => {{
        const mount = document.getElementById('canvasMount');
        if (!mount || !renderer) return;
        const nw = mount.clientWidth;
        const nh = mount.clientHeight;
        camera.aspect = nw / nh;
        camera.updateProjectionMatrix();
        renderer.setSize(nw, nh);
      }});
    }}

    function startAnimationLoop() {{
      const animate = () => {{
        animId = requestAnimationFrame(animate);

        stagedGroup.visible = isStaged;

        if (activeMode === 'walk') {{
          const walkSpeed = 0.12;
          const forward = new THREE.Vector3();
          camera.getWorldDirection(forward);
          forward.y = 0;
          forward.normalize();

          const right = new THREE.Vector3();
          right.crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

          if (keysPressed['w'] || keysPressed['arrowup']) {{
            tgtT[0] += forward.x * walkSpeed;
            tgtT[2] += forward.z * walkSpeed;
          }}
          if (keysPressed['s'] || keysPressed['arrowdown']) {{
            tgtT[0] -= forward.x * walkSpeed;
            tgtT[2] -= forward.z * walkSpeed;
          }}
          if (keysPressed['a'] || keysPressed['arrowleft']) {{
            tgtT[0] -= right.x * walkSpeed;
            tgtT[2] -= right.z * walkSpeed;
          }}
          if (keysPressed['d'] || keysPressed['arrowright']) {{
            tgtT[0] += right.x * walkSpeed;
            tgtT[2] -= right.z * walkSpeed;
          }}
        }}

        if (activeMode === 'tour' && currentBlueprint && currentBlueprint.waypoints) {{
          const wps = currentBlueprint.waypoints;
          tourSubT += 0.0035;
          if (tourSubT >= 1.0) {{
            tourSubT = 0;
            tourIdx = (tourIdx + 1) % wps.length;
            tourLabelText.textContent = wps[tourIdx].label || 'Cinematic Tour';
          }}

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
        }} else {{
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
        }}

        renderer.render(scene, camera);
      }};

      animate();
    }}

    function renderBlueprintInScene(bp) {{
      currentBlueprint = bp;

      while (stagedGroup.children.length > 0) stagedGroup.remove(stagedGroup.children[0]);
      while (structuralGroup.children.length > 0) structuralGroup.remove(structuralGroup.children[0]);

      if (!bp || !bp.rooms || bp.rooms.length === 0) return;

      // 1. Foundation Slab
      let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
      bp.rooms.forEach(r => {{
        const b = r.bounds;
        minX = Math.min(minX, b.x - b.w / 2);
        maxX = Math.max(maxX, b.x + b.w / 2);
        minZ = Math.min(minZ, b.z - b.d / 2);
        maxZ = Math.max(maxZ, b.z + b.d / 2);
      }});
      const totalW = Math.max(22, maxX - minX + 4);
      const totalD = Math.max(16, maxZ - minZ + 4);
      const centerX = (minX + maxX) / 2;
      const centerZ = (minZ + maxZ) / 2;

      createBox(totalW, 0.4, totalD, M.slab, centerX, 0.2, centerZ, 0, structuralGroup);

      // 2. Room Floors & Furniture
      bp.rooms.forEach(r => {{
        const b = r.bounds;
        const hex = parseInt(r.floorColor.replace("#", ""), 16) || 0xf4f1ea;
        const roomFloorMat = new THREE.MeshLambertMaterial({{ color: hex }});

        const floorMesh = createBox(b.w, 0.28, b.d, roomFloorMat, b.x, b.y + 0.14, b.z, 0, structuralGroup);
        floorMesh.userData = {{ floorLevel: r.floorLevel ?? 0, type: 'floor', roomId: r.id }};

        // Skirting
        const skirtH = 0.08, skirtT = 0.04;
        createBox(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z - b.d / 2 + skirtT / 2, 0, structuralGroup).userData = {{ floorLevel: r.floorLevel ?? 0 }};
        createBox(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z + b.d / 2 - skirtT / 2, 0, structuralGroup).userData = {{ floorLevel: r.floorLevel ?? 0 }};
        createBox(skirtT, skirtH, b.d, M.cream2, b.x - b.w / 2 + skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = {{ floorLevel: r.floorLevel ?? 0 }};
        createBox(skirtT, skirtH, b.d, M.cream2, b.x + b.w / 2 - skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = {{ floorLevel: r.floorLevel ?? 0 }};

        // Furniture
        r.furniture?.forEach(item => {{
          const [w, h, d] = item.size;
          const [x, y, z] = item.position;
          const mat = M[item.materialKey] || M.cream;
          const fMesh = createBox(w, h, d, mat, x, y, z, item.rotationY || 0, stagedGroup);
          fMesh.userData = {{ floorLevel: r.floorLevel ?? 0, type: 'furniture' }};
        }});

        // Lights
        r.lights?.forEach(light => {{
          const col = parseInt(light.color.replace("#", ""), 16) || 0xffd9a0;
          const pl = new THREE.PointLight(col, light.intensity || 0.85, light.distance || 12);
          pl.position.set(light.position[0], light.position[1], light.position[2]);
          pl.userData = {{ floorLevel: r.floorLevel ?? 0 }};
          structuralGroup.add(pl);
        }});
      }});

      // 3. Walls
      bp.structuralWalls?.forEach(w => {{
        const [sx, sy, sz] = w.size;
        const [px, py, pz] = w.position;
        const mat = w.isExterior ? M.cream2 : (M[w.materialKey] || M.cream);
        const wallMesh = createBox(sx, sy, sz, mat, px, py, pz, 0, structuralGroup);
        wallMesh.userData = {{ floorLevel: w.floorLevel ?? 0, type: 'wall', isExterior: w.isExterior }};
      }});

      // 4. Doors & Sliders
      bp.doors?.forEach(d => {{
        const [dx, dy, dz] = d.position;
        const [dw, dh, dd] = d.size;
        const rotY = d.rotationY || 0;
        const doorGroup = new THREE.Group();
        doorGroup.position.set(dx, dy, dz);
        doorGroup.rotation.y = rotY;
        doorGroup.userData = {{ floorLevel: d.floorLevel ?? 0, type: 'door' }};

        if (d.doorType === 'sliding') {{
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
        }} else {{
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
        }}

        structuralGroup.add(doorGroup);
      }});

      // 5. Windows
      bp.windows?.forEach(win => {{
        const [wx, wy, wz] = win.position;
        const [ww, wh] = win.size;
        const rotY = win.rotationY || 0;
        const winGroup = new THREE.Group();
        winGroup.position.set(wx, wy, wz);
        winGroup.rotation.y = rotY;
        winGroup.userData = {{ floorLevel: win.floorLevel ?? 0, type: 'window' }};

        const frameMat = M.dark;
        createBox(ww, 0.06, 0.16, frameMat, 0, wh / 2 - 0.03, 0, 0, winGroup);
        createBox(ww, 0.08, 0.22, M.cream2, 0, -wh / 2 + 0.04, 0.03, 0, winGroup);
        createBox(0.06, wh, 0.16, frameMat, -ww / 2 + 0.03, 0, 0, 0, winGroup);
        createBox(0.06, wh, 0.16, frameMat, ww / 2 - 0.03, 0, 0, 0, winGroup);

        if (win.hasMullions) {{
          createBox(0.04, wh, 0.14, frameMat, 0, 0, 0, 0, winGroup);
          createBox(ww, 0.04, 0.14, frameMat, 0, wh * 0.15, 0, 0, winGroup);
        }}

        const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(ww - 0.12, wh - 0.12), M.glass);
        winGroup.add(glassMesh);
        structuralGroup.add(winGroup);
      }});

      // 6. Balconies
      bp.balconies?.forEach(balc => {{
        const b = balc.bounds;
        const deckMesh = createBox(b.w, b.h, b.d, M.wood2, b.x, b.y + b.h / 2, b.z, 0, structuralGroup);
        deckMesh.userData = {{ floorLevel: balc.floorLevel, type: 'balcony' }};

        balc.railings?.forEach(rail => {{
          const [rx, ry, rz] = rail.position;
          const [rw, rh] = rail.size;
          const rRotY = rail.rotationY || 0;
          const rGroup = new THREE.Group();
          rGroup.position.set(rx, ry, rz);
          rGroup.rotation.y = rRotY;
          rGroup.userData = {{ floorLevel: balc.floorLevel, type: 'railing' }};

          const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(rw, rh), M.rail);
          rGroup.add(glassMesh);

          if (rail.handrail) {{
            createBox(rw, 0.05, 0.08, M.dark, 0, rh / 2 - 0.025, 0, 0, rGroup);
            createBox(0.04, rh, 0.04, M.dark, -rw / 2 + 0.02, 0, 0, 0, rGroup);
            createBox(0.04, rh, 0.04, M.dark, rw / 2 - 0.02, 0, 0, 0, rGroup);
          }}

          structuralGroup.add(rGroup);
        }});
      }});

      // 7. Glass Panels
      bp.glassPanels?.forEach(gp => {{
        const [gx, gy, gz] = gp.position;
        const [gw, gh] = gp.size;
        const gRotY = gp.rotationY || 0;
        const gpGroup = new THREE.Group();
        gpGroup.position.set(gx, gy, gz);
        gpGroup.rotation.y = gRotY;
        gpGroup.userData = {{ floorLevel: gp.floorLevel ?? 0, type: 'glass_panel' }};

        const gMesh = new THREE.Mesh(new THREE.PlaneGeometry(gw, gh), M.rail);
        gpGroup.add(gMesh);

        if (gp.handrail) {{
          createBox(gw, 0.05, 0.08, M.dark, 0, gh / 2 - 0.025, 0, 0, gpGroup);
        }}

        structuralGroup.add(gpGroup);
      }});

      updateUI(bp);
      focusRoom('all');
    }}

    function updateUI(bp) {{
      headerTitle.textContent = bp.propertyTitle || "Sovereign Digital Twin";
      headerSubtitle.textContent = `${{bp.propertyType || "Apartment"}} · ${{bp.floor || "Typical Floor"}} · ${{bp.carpetSqft ? bp.carpetSqft.toLocaleString() : "2,000"}} sq.ft · ${{bp.orientation || "East-Facing"}}`;
      aboutTextContent.textContent = bp.aboutSummary || "Spatial model compiled from verified listing data.";

      cardBedrooms.textContent = `${{bp.bhkCount || 3}} Physical Suites`;
      
      const living = bp.rooms?.find(r => r.name.toLowerCase().includes("living"));
      const kitchen = bp.rooms?.find(r => r.name.toLowerCase().includes("kitchen"));
      if (living && kitchen && kitchen.carpetSqft > 0) {{
        const ratio = (living.carpetSqft / kitchen.carpetSqft).toFixed(2);
        cardRatio.textContent = `${{ratio}} : 1 (Calibrated)`;
      }} else {{
        cardRatio.textContent = "3.00 : 1";
      }}

      cardLevels.textContent = `${{bp.levelsCount || 1}} Level (${{bp.archetype === 'villa_g2' ? "G+2 Villa" : "Apartment"}})`;
      cardBim.textContent = `${{bp.structuralWalls?.length || 0}} Walls · ${{bp.doors?.length || 0}} Doors · ${{bp.windows?.length || 0}} Wins`;

      // Villa floor filters
      if (bp.levelsCount > 1) {{
        floorFilterOverlay.classList.remove('hidden');
      }} else {{
        floorFilterOverlay.classList.add('hidden');
      }}

      // Room Pills
      roomPillsContainer.innerHTML = '';
      bp.rooms?.forEach((room, idx) => {{
        const pill = document.createElement('button');
        pill.className = 'room-pill px-3 py-1.5 rounded-xl bg-stone-900/85 text-stone-300 hover:bg-stone-800 text-xs font-medium whitespace-nowrap shadow border border-stone-700/70 transition-all';
        pill.textContent = room.name;
        pill.addEventListener('click', () => {{
          document.querySelectorAll('.room-pill').forEach(p => {{
            p.classList.remove('bg-amber-500', 'text-stone-950', 'font-bold', 'border-amber-400');
            p.classList.add('bg-stone-900/85', 'text-stone-300');
          }});
          pill.classList.remove('bg-stone-900/85', 'text-stone-300');
          pill.classList.add('bg-amber-500', 'text-stone-950', 'font-bold', 'border-amber-400');
          focusRoom(room.id);
        }});
        roomPillsContainer.appendChild(pill);
      }});

      // Pre-fill editable prompt fields
      promptField.value = bp.aboutSummary || "";
      promptCharCount.textContent = `${{promptField.value.length}} chars`;
      if (bp.bhkCount) fieldBHK.value = bp.bhkCount.toString();
      if (bp.archetype) fieldArchetype.value = bp.archetype;
      if (bp.carpetSqft) fieldCarpet.value = bp.carpetSqft;
    }}

    function focusRoom(roomId) {{
      if (!currentBlueprint) return;
      const targets = currentBlueprint.focalTargets || {{}};
      const focal = targets[roomId] || targets['all'] || {{ target: [0, 2.8, 0], theta: 0.72, phi: 1.05, radius: 28, walk: [0, 1.65, 12] }};

      if (activeMode === 'walk') {{
        tgtT = [focal.walk[0], focal.walk[1], focal.walk[2]];
        tgtR = 4.5;
        tgtPhi = Math.PI / 2 - 0.05;
      }} else {{
        tgtT = [focal.target[0], focal.target[1], focal.target[2]];
        tgtTh = focal.theta;
        tgtPhi = focal.phi;
        tgtR = focal.radius;
      }}
    }}

    function applyFloorFilter(floorIdx) {{
      currentFloorFilter = floorIdx;
      document.querySelectorAll('.floor-btn').forEach(btn => {{
        if (parseInt(btn.dataset.floor) === floorIdx) {{
          btn.className = 'floor-btn px-2.5 py-1 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all';
        }} else {{
          btn.className = 'floor-btn px-2.5 py-1 rounded-lg text-stone-300 hover:text-white transition-all';
        }}
      }});

      const filterActive = floorIdx >= 0;
      scene.traverse(obj => {{
        if (obj.userData && obj.userData.floorLevel !== undefined) {{
          obj.visible = filterActive ? obj.userData.floorLevel === floorIdx : true;
        }}
      }});
    }}

    // Switch between preloaded properties
    propertySelect.addEventListener('change', () => {{
      const slug = propertySelect.value;
      const bp = PRELOADED_BLUEPRINTS[slug];
      if (bp) {{
        renderBlueprintInScene(bp);
      }}
    }});

    // Prompt Drawer open/close
    btnTogglePromptDrawer.addEventListener('click', () => {{
      promptDrawer.classList.toggle('-translate-x-full');
    }});

    btnClosePromptDrawer.addEventListener('click', () => {{
      promptDrawer.classList.add('-translate-x-full');
    }});

    document.getElementById('btnCloseNotes').addEventListener('click', () => {{
      document.getElementById('aboutNotesCard').classList.toggle('hidden');
    }});

    promptField.addEventListener('input', () => {{
      promptCharCount.textContent = `${{promptField.value.length}} chars`;
    }});

    // Staging toggle
    document.getElementById('btnToggleStaging').addEventListener('click', () => {{
      isStaged = !isStaged;
      document.getElementById('stagingText').textContent = isStaged ? '🛋️ Furnished' : '🪵 Bare Shell';
    }});

    // Cutaway top-down toggle
    document.getElementById('btnToggleCutaway').addEventListener('click', () => {{
      isTopDown = !isTopDown;
      if (isTopDown) {{
        tgtPhi = 0.04;
        tgtR = 38;
      }} else {{
        tgtPhi = 1.05;
        tgtR = 26;
      }}
    }});

    // Fullscreen toggle
    document.getElementById('btnFullscreen').addEventListener('click', () => {{
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(() => {{}});
      }} else {{
        document.exitFullscreen().catch(() => {{}});
      }}
    }});

    // Camera Mode Switchers
    document.getElementById('btnModeOrbit').addEventListener('click', () => {{
      activeMode = 'orbit';
      isTopDown = false;
      tourBanner.classList.add('hidden');
      walkInstructions.classList.add('hidden');
      document.getElementById('btnModeOrbit').className = 'px-3 py-1.5 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all flex items-center gap-1.5';
      document.getElementById('btnModeWalk').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      document.getElementById('btnModeTour').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      focusRoom('all');
    }});

    document.getElementById('btnModeWalk').addEventListener('click', () => {{
      activeMode = 'walk';
      isTopDown = false;
      tourBanner.classList.add('hidden');
      walkInstructions.classList.remove('hidden');
      document.getElementById('btnModeWalk').className = 'px-3 py-1.5 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all flex items-center gap-1.5';
      document.getElementById('btnModeOrbit').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      document.getElementById('btnModeTour').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      focusRoom('living');
    }});

    document.getElementById('btnModeTour').addEventListener('click', () => {{
      activeMode = 'tour';
      isTopDown = false;
      tourIdx = 0;
      tourSubT = 0;
      tourBanner.classList.remove('hidden');
      walkInstructions.classList.add('hidden');
      document.getElementById('btnModeTour').className = 'px-3 py-1.5 rounded-lg bg-amber-500 text-stone-950 font-bold transition-all flex items-center gap-1.5';
      document.getElementById('btnModeOrbit').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
      document.getElementById('btnModeWalk').className = 'px-3 py-1.5 rounded-lg text-stone-300 hover:text-white transition-all flex items-center gap-1.5';
    }});

    document.getElementById('btnRoomAll').addEventListener('click', () => {{
      document.querySelectorAll('.room-pill').forEach(p => {{
        p.classList.remove('bg-amber-500', 'text-stone-950', 'font-bold', 'border-amber-400');
        p.classList.add('bg-stone-900/85', 'text-stone-300');
      }});
      document.getElementById('btnRoomAll').className = 'room-pill px-3 py-1.5 rounded-xl bg-white text-stone-950 font-bold text-xs whitespace-nowrap shadow-lg border border-white';
      focusRoom('all');
    }});

    document.querySelectorAll('.floor-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        applyFloorFilter(parseInt(btn.dataset.floor));
      }});
    }});

    // Live Prompt Compilation / Synthesis
    btnApplyPrompt.addEventListener('click', async () => {{
      const customPrompt = promptField.value.trim();
      const selectedBHK = parseInt(fieldBHK.value);
      const selectedArchetype = fieldArchetype.value;
      const selectedCarpet = parseInt(fieldCarpet.value) || 2500;
      const selectedFacing = fieldFacing.value;

      btnApplyPrompt.innerHTML = '<span>⏳</span> Compiling...';
      btnApplyPrompt.disabled = true;

      // Try calling live backend /api/compile if test_server is active, or use client-side clone
      try {{
        const resp = await fetch('/api/compile', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            prompt: customPrompt,
            configuration: `${{selectedBHK}} BHK`,
            propertyType: selectedArchetype === 'villa_g2' ? 'Villa' : 'Apartment',
            carpetAreaSqft: selectedCarpet,
            floor: selectedArchetype === 'villa_g2' ? 'G + 2 Villa (3 Floors)' : 'Typical Floor',
            facing: selectedFacing,
          }})
        }});
        if (resp.ok) {{
          const compiledBp = await resp.json();
          renderBlueprintInScene(compiledBp);
          promptDrawer.classList.add('-translate-x-full');
          return;
        }}
      }} catch (e) {{
        // Backend not running, synthesize dynamically in client
      }} finally {{
        btnApplyPrompt.innerHTML = '<span>⚡</span> Apply & Re-Render 3D Twin';
        btnApplyPrompt.disabled = false;
      }}

      // Client-side synthesis fallback: adapt base template
      const baseKey = selectedArchetype === 'villa_g2' ? 'goodwill-enclave-4-5bhk-191' : 'the-balmoral-estates-3bhk-1';
      const cloned = JSON.parse(JSON.stringify(PRELOADED_BLUEPRINTS[baseKey] || Object.values(PRELOADED_BLUEPRINTS)[0]));

      cloned.propertyTitle = customPrompt.split('.')[0] || "Custom User Spatial Twin";
      cloned.bhkCount = selectedBHK;
      cloned.configuration = `${{selectedBHK}} BHK`;
      cloned.carpetSqft = selectedCarpet;
      cloned.orientation = `${{selectedFacing}}-Facing`;
      cloned.archetype = selectedArchetype;
      cloned.levelsCount = selectedArchetype === 'villa_g2' ? 3 : 1;
      cloned.aboutSummary = customPrompt || cloned.aboutSummary;

      // Filter rooms to match BHK
      if (selectedBHK <= 3) {{
        cloned.rooms = cloned.rooms.filter(r => r.id !== 'bedroom_4' && r.id !== 'bedroom_5');
      }} else if (selectedBHK === 4) {{
        cloned.rooms = cloned.rooms.filter(r => r.id !== 'bedroom_5');
      }}

      renderBlueprintInScene(cloned);
      promptDrawer.classList.add('-translate-x-full');
    }});

    // Initialize on DOM Ready
    window.addEventListener('DOMContentLoaded', () => {{
      initThreeScene();
      const firstSlug = Object.keys(PRELOADED_BLUEPRINTS)[0];
      if (firstSlug && PRELOADED_BLUEPRINTS[firstSlug]) {{
        propertySelect.value = firstSlug;
        renderBlueprintInScene(PRELOADED_BLUEPRINTS[firstSlug]);
      }}
    }});
  </script>
</body>
</html>
"""

output_html = os.path.join(CURRENT_DIR, "preview.html")
with open(output_html, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Generated self-contained preview app at: {output_html} ({len(html_content):,} bytes)")
