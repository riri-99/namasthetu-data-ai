"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Layers,
  Maximize2,
  Minimize2,
  Navigation,
  ShieldCheck,
  CheckCircle2,
  Footprints,
  Grid,
  Box as BoxIcon,
  Building2,
  Bed,
  FileText,
  DoorClosed,
  Eye,
  Camera,
  Compass,
  ArrowRight,
  Sparkles,
  Link2,
  Info,
  ChevronRight,
  ExternalLink,
  Sliders,
} from "lucide-react";
import * as THREE from "three";

export interface SpatialBox {
  x: number;
  y: number;
  z: number;
  w: number;
  d: number;
  h: number;
}

export interface ImageReference {
  source: string;
  category: string;
  confidence: number;
  detectedFinish: string;
  caption: string;
}

export interface AdjacentRoomConnection {
  neighborId: string;
  neighborName: string;
  boundaryType: string;
  relativeDirection: string;
  reason: string;
}

export interface StagedFurniture {
  id: string;
  name: string;
  type: string;
  position: [number, number, number];
  size: [number, number, number];
  materialKey: string;
  color?: string;
  rotationY?: number;
}

export interface ArchitecturalTwinRoom {
  id: string;
  name: string;
  dimensions: string;
  carpetSqft: number;
  highlight: string;
  floorType: string;
  floorColor: string;
  wallColor: string;
  floorLevel?: number;
  bounds: SpatialBox;
  furniture: StagedFurniture[];
  imageReference?: ImageReference;
  adjacentRooms?: AdjacentRoomConnection[];
  lights?: Array<{ position: [number, number, number]; color: string; intensity: number; distance: number }>;
}

export interface StructuralWall {
  id: string;
  position: [number, number, number];
  size: [number, number, number];
  materialKey: string;
  isExterior?: boolean;
  floorLevel?: number;
}

export interface DoorSpecification {
  id: string;
  name: string;
  position: [number, number, number];
  size: [number, number, number];
  rotationY: number;
  floorLevel: number;
  doorType: string;
  openAngle?: number;
  panelsCount?: number;
  frameMaterial: string;
  leafMaterial?: string;
}

export interface WindowSpecification {
  id: string;
  name: string;
  position: [number, number, number];
  size: [number, number];
  rotationY: number;
  sillHeight: number;
  floorLevel: number;
  hasMullions: boolean;
  frameMaterial: string;
}

export interface BalconySpecification {
  id: string;
  name: string;
  floorLevel: number;
  bounds: SpatialBox;
  deckMaterial: string;
  railings: Array<{
    id: string;
    position: [number, number, number];
    size: [number, number];
    rotationY: number;
    type: string;
    handrail?: boolean;
  }>;
}

export interface GlassPanel {
  id: string;
  position: [number, number, number];
  size: [number, number];
  rotationY?: number;
  floorLevel?: number;
  handrail?: boolean;
}

export interface CameraFocalTarget {
  target: [number, number, number];
  theta: number;
  phi: number;
  radius: number;
  walk: [number, number, number];
}

export interface TourWaypoint {
  p: [number, number, number];
  l: [number, number, number];
  label: string;
}

export interface FloorLevelSpec {
  id: string;
  name: string;
  elevation: number;
  roomIds: string[];
}

export interface AdjacencyEdge {
  from: string;
  to: string;
  boundaryType: string;
  relativeDirection: string;
  reason: string;
}

export interface AdjacencyGraph {
  nodes: Array<{ id: string; name: string; type: string; floorLevel: number; imageReference?: ImageReference }>;
  edges: AdjacencyEdge[];
  viewOrientation: string;
  inferredLayoutSummary: string;
}

export interface ArchitecturalTwinBlueprint {
  propertyId: string;
  propertyTitle: string;
  locality?: string;
  city: string;
  state: string;
  propertyType?: string;
  configuration?: string;
  bhkCount?: number;
  conditionScore: number;
  carpetSqft: number;
  builtUpSqft: number;
  floor?: string;
  floorHeight: string;
  efficiency: number;
  orientation: string;
  archetype?: string;
  levelsCount?: number;
  aboutSummary?: string;
  environmentalTheme: string;
  adjacencyGraph?: AdjacencyGraph;
  analyzedImages?: any[];
  floors?: FloorLevelSpec[];
  rooms: ArchitecturalTwinRoom[];
  structuralWalls: StructuralWall[];
  doors?: DoorSpecification[];
  windows?: WindowSpecification[];
  balconies?: BalconySpecification[];
  glassPanels: GlassPanel[];
  focalTargets: Record<string, CameraFocalTarget>;
  waypoints: TourWaypoint[];
  fixtures: Array<{ item: string; detail: string; included: boolean }>;
}

export interface ArchitecturalTwinViewerProps {
  blueprint?: ArchitecturalTwinBlueprint;
  propertyTitle?: string;
  conditionScore?: number;
  carpetSqft?: number;
  builtUpSqft?: number;
  floorHeight?: string;
  efficiency?: number;
  orientation?: string;
}

type TwinMode = "orbit" | "walk" | "tour";

const DEFAULT_FOCAL_TARGETS: Record<string, CameraFocalTarget> = {
  living: { target: [0, 1.4, 0], theta: 0.75, phi: 1.08, radius: 14, walk: [0, 1.65, 2.6] },
  kitchen: { target: [6.8, 1.4, -1.0], theta: 1.2, phi: 1.15, radius: 10, walk: [5.2, 1.65, -1.0] },
  master: { target: [-6.8, 1.5, 0.5], theta: 0.35, phi: 1.08, radius: 13, walk: [-5.4, 1.65, 2.2] },
  bedroom_2: { target: [6.9, 1.5, 4.6], theta: 1.85, phi: 1.08, radius: 12, walk: [5.5, 1.65, 3.6] },
  balcony: { target: [1.8, 1.2, 5.2], theta: 2.35, phi: 1.05, radius: 12, walk: [0.8, 1.65, 4.4] },
  all: { target: [0, 2.8, 0], theta: 0.72, phi: 1.05, radius: 32, walk: [0, 1.65, 12] },
};

const DEFAULT_WAYPOINTS: TourWaypoint[] = [
  { p: [4.0, 3.5, 18.0], l: [0, 2.5, 0], label: "Approach · Architectural Facade" },
  { p: [0.0, 1.65, 2.6], l: [0.0, 1.2, -2.0], label: "Grand Living & Dining Pavilion" },
  { p: [5.2, 1.65, -1.0], l: [7.8, 1.4, -1.0], label: "Gourmet Culinary Studio (3:1 Area Ratio)" },
  { p: [-5.4, 1.65, 2.2], l: [-7.8, 1.1, -0.6], label: "Presidential Master Suite" },
  { p: [0.8, 1.65, 4.4], l: [2.8, 1.4, 6.5], label: "Covered Sky Balcony & Deck" },
  { p: [18, 16, 18], l: [0, 3.0, 0], label: "Aerial · Full Spatial Adjacency Twin" },
];

export const ArchitecturalTwinViewer: React.FC<ArchitecturalTwinViewerProps> = ({
  blueprint,
  propertyTitle: propTitle = "Sovereign Architectural Residence",
  conditionScore: propCondition = 9.6,
  carpetSqft: propCarpet = 2200,
  builtUpSqft: propBuiltUp = 2800,
  floorHeight: propFloorHeight = "10.5 ft",
  efficiency: propEfficiency = 84,
  orientation: propOrientation = "East-Facing",
}) => {
  const propertyTitle = blueprint?.propertyTitle || propTitle;
  const conditionScore = blueprint?.conditionScore ?? propCondition;
  const carpetSqft = blueprint?.carpetSqft ?? propCarpet;
  const floorHeight = blueprint?.floorHeight || propFloorHeight;
  const orientation = blueprint?.orientation || propOrientation;
  const fixtures = blueprint?.fixtures || [];
  const bhkCount = blueprint?.bhkCount || 3;
  const levelsCount = blueprint?.levelsCount || (blueprint?.floors ? blueprint.floors.length : 1);
  const propertyType = blueprint?.propertyType || "Apartment";
  const floorDesc = blueprint?.floor || "Typical Floor";
  const aboutSummary = blueprint?.aboutSummary || `Synthesized architectural spatial blueprint for ${propertyTitle}.`;
  const adjacencyGraph = blueprint?.adjacencyGraph;

  // Active rooms list
  const activeRooms = blueprint?.rooms || [];

  const focalTargets = blueprint?.focalTargets || DEFAULT_FOCAL_TARGETS;
  const waypoints = blueprint?.waypoints || DEFAULT_WAYPOINTS;

  // UI state
  const [activeMode, setActiveMode] = useState<TwinMode>("orbit");
  const [activeRoomIndex, setActiveRoomIndex] = useState<number>(-1);
  const [activeFloorFilter, setActiveFloorFilter] = useState<number>(-1);
  const [isStaged, setIsStaged] = useState<boolean>(true);
  const [isTopDown, setIsTopDown] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isSceneReady, setIsSceneReady] = useState<boolean>(false);
  const [sceneFailed, setSceneFailed] = useState<boolean>(false);
  const [currentTourLabel, setCurrentTourLabel] = useState<string>("Approach · Facade");
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);

  const sectionRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const modeRef = useRef<TwinMode>(activeMode);
  modeRef.current = activeMode;

  const stagedRef = useRef<boolean>(isStaged);
  stagedRef.current = isStaged;

  const topDownRef = useRef<boolean>(isTopDown);
  topDownRef.current = isTopDown;

  const floorFilterRef = useRef<number>(activeFloorFilter);
  floorFilterRef.current = activeFloorFilter;

  const cameraControlRef = useRef<{
    focusRoom: (roomId: string) => void;
    setTopDown: (topDown: boolean) => void;
    applyFloorFilter: (floorIdx: number) => void;
  } | null>(null);

  const activeRoom: ArchitecturalTwinRoom | null =
    activeRoomIndex >= 0 && activeRooms[activeRoomIndex]
      ? activeRooms[activeRoomIndex]
      : null;

  const handleSelectRoom = (index: number) => {
    setActiveRoomIndex(index);
    const room = activeRooms[index];
    if (room && cameraControlRef.current) {
      cameraControlRef.current.focusRoom(room.id);
    }
    setIsDrawerOpen(true);
  };

  const handleSelectRoomById = (roomId: string) => {
    const idx = activeRooms.findIndex((r) => r.id === roomId);
    if (idx >= 0) {
      handleSelectRoom(idx);
    } else if (cameraControlRef.current) {
      cameraControlRef.current.focusRoom(roomId);
    }
  };

  const handleSelectWholeProperty = () => {
    setActiveRoomIndex(-1);
    if (cameraControlRef.current) {
      cameraControlRef.current.focusRoom("all");
    }
  };

  const handleSetFloorFilter = (floorIdx: number) => {
    setActiveFloorFilter(floorIdx);
    if (cameraControlRef.current) {
      cameraControlRef.current.applyFloorFilter(floorIdx);
    }
  };

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      sectionRef.current?.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
    setIsFullscreen((v) => !v);
  };

  const toggleTopDownCutaway = () => {
    const nextVal = !isTopDown;
    setIsTopDown(nextVal);
    if (activeMode !== "orbit") {
      setActiveMode("orbit");
    }
    if (cameraControlRef.current) {
      cameraControlRef.current.setTopDown(nextVal);
    }
  };

  // Three.js Scene Setup Effect
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let animId = 0;
    let renderer: THREE.WebGLRenderer | null = null;

    try {
      const width = container.clientWidth || 800;
      const height = container.clientHeight || 560;

      const scene = new THREE.Scene();
      const fogColor = 0xd5cfc4;
      scene.background = new THREE.Color(fogColor);
      scene.fog = new THREE.Fog(fogColor, 50, 150);

      const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 350);
      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 0.98;

      while (container.firstChild) container.removeChild(container.firstChild);
      container.appendChild(renderer.domElement);

      // Lighting Rig
      scene.add(new THREE.HemisphereLight(0xfff5e6, 0xa39b8d, 0.72));
      const sun = new THREE.DirectionalLight(0xffeed6, 0.98);
      sun.position.set(30, 48, 22);
      sun.castShadow = true;
      sun.shadow.mapSize.set(1024, 1024);
      Object.assign(sun.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, far: 140 });
      scene.add(sun);

      // Materials Library
      const M: Record<string, THREE.Material> = {
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
      };

      const stagedGroup = new THREE.Group();
      scene.add(stagedGroup);

      const structuralGroup = new THREE.Group();
      scene.add(structuralGroup);

      function box(
        w: number,
        h: number,
        d: number,
        mat: THREE.Material,
        x: number,
        y: number,
        z: number,
        ry = 0,
        parent: THREE.Object3D = scene
      ) {
        const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
        m.position.set(x, y, z);
        if (ry) m.rotation.y = ry;
        m.castShadow = true;
        m.receiveShadow = true;
        parent.add(m);
        return m;
      }

      // Ground plane & Road
      const g = new THREE.Mesh(new THREE.PlaneGeometry(260, 260), M.ground);
      g.rotation.x = -Math.PI / 2;
      g.receiveShadow = true;
      scene.add(g);

      const r1 = new THREE.Mesh(new THREE.PlaneGeometry(16, 260), M.road);
      r1.rotation.x = -Math.PI / 2;
      r1.position.set(0, 0.02, 0);
      r1.rotation.z = Math.PI / 2;
      r1.receiveShadow = true;
      scene.add(r1);

      // Surrounding Context & Landscape
      const nb = [
        { x: -36, z: -26, w: 12, d: 14, h: 10, mat: M.grey1 },
        { x: -38, z: 8, w: 10, d: 9, h: 8, mat: M.grey2 },
        { x: 34, z: -26, w: 14, d: 14, h: 11, mat: M.grey2 },
        { x: 42, z: 6, w: 11, d: 9, h: 14, mat: M.grey1 },
      ];
      nb.forEach((n) => box(n.w, n.h, n.d, n.mat, n.x, n.h / 2, n.z));

      for (let t = 0; t < 16; t++) {
        const a = (t / 16) * Math.PI * 2 + 0.2;
        const r = 20 + (t % 4) * 6;
        const x = Math.cos(a) * r;
        const z = Math.sin(a) * r;
        const th = 1.0 + (t % 3) * 0.4;
        const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, th, 6), M.trunk);
        tr.position.set(x, th / 2, z);
        scene.add(tr);
        const cr = new THREE.Mesh(new THREE.SphereGeometry(0.85 + (t % 3) * 0.35, 10, 8), M.leaf);
        cr.position.set(x, th + 0.65, z);
        scene.add(cr);
      }

      // ========================================================
      // PROCEDURAL ARCHITECTURAL BLUEPRINT RENDERING
      // ========================================================
      if (blueprint && blueprint.rooms && blueprint.rooms.length > 0) {
        // Foundation Podium Slab
        let minX = Infinity,
          maxX = -Infinity,
          minZ = Infinity,
          maxZ = -Infinity;
        blueprint.rooms.forEach((r) => {
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

        box(totalW, 0.4, totalD, M.slab, centerX, 0.2, centerZ, 0, structuralGroup);

        // Rooms (Floors, Skirting, Furniture, Lights)
        blueprint.rooms.forEach((r) => {
          const b = r.bounds;
          const hexCol = parseInt(r.floorColor.replace("#", ""), 16) || 0xf4f1ea;
          const roomFloorMat = new THREE.MeshLambertMaterial({ color: hexCol });

          // Room Floor Slab
          const floorMesh = box(b.w, 0.28, b.d, roomFloorMat, b.x, b.y + 0.14, b.z, 0, structuralGroup);
          floorMesh.userData = { floorLevel: r.floorLevel ?? 0, type: "floor", roomId: r.id };

          // Skirting Baseboard
          const skirtH = 0.08, skirtT = 0.04;
          box(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z - b.d / 2 + skirtT / 2, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
          box(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z + b.d / 2 - skirtT / 2, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
          box(skirtT, skirtH, b.d, M.cream2, b.x - b.w / 2 + skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
          box(skirtT, skirtH, b.d, M.cream2, b.x + b.w / 2 - skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };

          // Furniture
          r.furniture?.forEach((item) => {
            const [w, h, d] = item.size;
            const [x, y, z] = item.position;
            const mat = M[item.materialKey] || M.cream;
            const fMesh = box(w, h, d, mat, x, y, z, item.rotationY || 0, stagedGroup);
            fMesh.userData = { floorLevel: r.floorLevel ?? 0, type: "furniture" };
          });

          // Lights
          r.lights?.forEach((light) => {
            const col = parseInt(light.color.replace("#", ""), 16) || 0xffd9a0;
            const pl = new THREE.PointLight(col, light.intensity || 0.85, light.distance || 12);
            pl.position.set(light.position[0], light.position[1], light.position[2]);
            pl.userData = { floorLevel: r.floorLevel ?? 0 };
            structuralGroup.add(pl);
          });
        });

        // Structural Perimeter & Partition Walls
        blueprint.structuralWalls?.forEach((w) => {
          const [sx, sy, sz] = w.size;
          const [px, py, pz] = w.position;
          const mat = w.isExterior ? M.cream2 : (M[w.materialKey] || M.cream);
          const wallMesh = box(sx, sy, sz, mat, px, py, pz, 0, structuralGroup);
          wallMesh.userData = { floorLevel: w.floorLevel ?? 0, type: "wall", isExterior: w.isExterior };
        });

        // Doors & Sliders
        blueprint.doors?.forEach((d) => {
          const [dx, dy, dz] = d.position;
          const [dw, dh, dd] = d.size;
          const rotY = d.rotationY || 0;
          const doorGroup = new THREE.Group();
          doorGroup.position.set(dx, dy, dz);
          doorGroup.rotation.y = rotY;
          doorGroup.userData = { floorLevel: d.floorLevel ?? 0, type: "door" };

          if (d.doorType === "sliding") {
            const frameMat = M.dark;
            box(dw, 0.08, 0.12, frameMat, 0, dh / 2 - 0.04, 0, 0, doorGroup);
            box(dw, 0.08, 0.12, frameMat, 0, -dh / 2 + 0.04, 0, 0, doorGroup);
            box(0.08, dh, 0.12, frameMat, -dw / 2 + 0.04, 0, 0, 0, doorGroup);
            box(0.08, dh, 0.12, frameMat, dw / 2 - 0.04, 0, 0, 0, doorGroup);

            const panelW = dw / 2.0 - 0.04;
            const g1 = new THREE.Mesh(new THREE.PlaneGeometry(panelW, dh - 0.16), M.glass);
            g1.position.set(-dw / 4, 0, -0.02);
            doorGroup.add(g1);
            const g2 = new THREE.Mesh(new THREE.PlaneGeometry(panelW, dh - 0.16), M.glass);
            g2.position.set(dw / 4, 0, 0.02);
            doorGroup.add(g2);
          } else {
            const frameMat = M.dark;
            box(0.06, dh, dd * 1.1, frameMat, -dw / 2 + 0.03, 0, 0, 0, doorGroup);
            box(0.06, dh, dd * 1.1, frameMat, dw / 2 - 0.03, 0, 0, 0, doorGroup);
            box(dw, 0.06, dd * 1.1, frameMat, 0, dh / 2 - 0.03, 0, 0, doorGroup);

            const leafW = dw - 0.12;
            const leafH = dh - 0.08;
            const leafGroup = new THREE.Group();
            leafGroup.position.set(-dw / 2 + 0.06, 0, 0);
            leafGroup.rotation.y = d.openAngle || 0.45;

            const leafMesh = box(leafW, leafH, 0.04, M.wood2, leafW / 2, 0, 0, 0, leafGroup);
            leafMesh.castShadow = true;

            const handle = box(0.04, 0.12, 0.08, M.accent, leafW - 0.08, 0, 0.04, 0, leafGroup);
            handle.castShadow = true;
            doorGroup.add(leafGroup);
          }

          structuralGroup.add(doorGroup);
        });

        // Windows
        blueprint.windows?.forEach((win) => {
          const [wx, wy, wz] = win.position;
          const [ww, wh] = win.size;
          const rotY = win.rotationY || 0;
          const winGroup = new THREE.Group();
          winGroup.position.set(wx, wy, wz);
          winGroup.rotation.y = rotY;
          winGroup.userData = { floorLevel: win.floorLevel ?? 0, type: "window" };

          const frameMat = M.dark;
          box(ww, 0.06, 0.16, frameMat, 0, wh / 2 - 0.03, 0, 0, winGroup);
          box(ww, 0.08, 0.22, M.cream2, 0, -wh / 2 + 0.04, 0.03, 0, winGroup); // Sill
          box(0.06, wh, 0.16, frameMat, -ww / 2 + 0.03, 0, 0, 0, winGroup);
          box(0.06, wh, 0.16, frameMat, ww / 2 - 0.03, 0, 0, 0, winGroup);

          if (win.hasMullions) {
            box(0.04, wh, 0.14, frameMat, 0, 0, 0, 0, winGroup);
            box(ww, 0.04, 0.14, frameMat, 0, wh * 0.15, 0, 0, winGroup);
          }

          const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(ww - 0.12, wh - 0.12), M.glass);
          winGroup.add(glassMesh);

          structuralGroup.add(winGroup);
        });

        // Balconies
        blueprint.balconies?.forEach((balc) => {
          const b = balc.bounds;
          const deckMat = M.wood2;
          const deckMesh = box(b.w, b.h, b.d, deckMat, b.x, b.y + b.h / 2, b.z, 0, structuralGroup);
          deckMesh.userData = { floorLevel: balc.floorLevel, type: "balcony" };

          balc.railings?.forEach((rail) => {
            const [rx, ry, rz] = rail.position;
            const [rw, rh] = rail.size;
            const rRotY = rail.rotationY || 0;
            const rGroup = new THREE.Group();
            rGroup.position.set(rx, ry, rz);
            rGroup.rotation.y = rRotY;
            rGroup.userData = { floorLevel: balc.floorLevel, type: "railing" };

            const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(rw, rh), M.rail);
            rGroup.add(glassMesh);

            if (rail.handrail) {
              box(rw, 0.05, 0.08, M.dark, 0, rh / 2 - 0.025, 0, 0, rGroup);
              box(0.04, rh, 0.04, M.dark, -rw / 2 + 0.02, 0, 0, 0, rGroup);
              box(0.04, rh, 0.04, M.dark, rw / 2 - 0.02, 0, 0, 0, rGroup);
            }

            structuralGroup.add(rGroup);
          });
        });

        // Glass Panels
        blueprint.glassPanels?.forEach((gp) => {
          const [gx, gy, gz] = gp.position;
          const [gw, gh] = gp.size;
          const gRotY = gp.rotationY || 0;
          const gpGroup = new THREE.Group();
          gpGroup.position.set(gx, gy, gz);
          gpGroup.rotation.y = gRotY;
          gpGroup.userData = { floorLevel: gp.floorLevel ?? 0, type: "glass_panel" };

          const gMesh = new THREE.Mesh(new THREE.PlaneGeometry(gw, gh), M.rail);
          gpGroup.add(gMesh);

          if (gp.handrail) {
            box(gw, 0.05, 0.08, M.dark, 0, gh / 2 - 0.025, 0, 0, gpGroup);
          }

          structuralGroup.add(gpGroup);
        });
      }

      // Camera Animation State
      let curT = [0, 1.4, 0];
      let curTh = 0.72;
      let curPhi = 1.05;
      let curR = 28.0;

      let tgtT = [0, 1.4, 0];
      let tgtTh = 0.72;
      let tgtPhi = 1.05;
      let tgtR = 28.0;

      // Tour animation tracking
      let tourIdx = 0;
      let tourSubT = 0;

      // Mouse drag controls
      let isDragging = false;
      let prevMouseX = 0;
      let prevMouseY = 0;

      const dom = renderer.domElement;

      const onMouseDown = (e: MouseEvent) => {
        if (modeRef.current === "tour") return;
        isDragging = true;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      };

      const onMouseMove = (e: MouseEvent) => {
        if (!isDragging || modeRef.current === "tour") return;
        const dx = e.clientX - prevMouseX;
        const dy = e.clientY - prevMouseY;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;

        if (topDownRef.current) {
          tgtT[0] -= dx * 0.04;
          tgtT[2] -= dy * 0.04;
        } else {
          tgtTh -= dx * 0.007;
          tgtPhi = Math.max(0.15, Math.min(Math.PI / 2 - 0.05, tgtPhi + dy * 0.005));
        }
      };

      const onMouseUp = () => {
        isDragging = false;
      };

      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        if (modeRef.current === "tour") return;
        tgtR = Math.max(6, Math.min(65, tgtR + e.deltaY * 0.035));
      };

      dom.addEventListener("mousedown", onMouseDown);
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
      dom.addEventListener("wheel", onWheel, { passive: false });

      // Camera Control Methods Hook
      cameraControlRef.current = {
        focusRoom: (roomId: string) => {
          const focal = focalTargets[roomId] || focalTargets["all"] || DEFAULT_FOCAL_TARGETS["all"];
          if (modeRef.current === "walk") {
            tgtT = [focal.walk[0], focal.walk[1], focal.walk[2]];
            tgtR = 4.5;
            tgtPhi = Math.PI / 2 - 0.05;
          } else {
            tgtT = [focal.target[0], focal.target[1], focal.target[2]];
            tgtTh = focal.theta;
            tgtPhi = focal.phi;
            tgtR = focal.radius;
          }
        },
        setTopDown: (topDown: boolean) => {
          if (topDown) {
            tgtPhi = 0.04;
            tgtR = 38;
          } else {
            tgtPhi = 1.05;
            tgtR = 26;
          }
        },
        applyFloorFilter: (floorIdx: number) => {
          const filterActive = floorIdx >= 0;
          scene.traverse((obj) => {
            if (obj.userData && obj.userData.floorLevel !== undefined) {
              if (!filterActive) {
                obj.visible = true;
              } else {
                obj.visible = obj.userData.floorLevel === floorIdx;
              }
            }
          });
        },
      };

      // Animation Loop
      const animate = () => {
        animId = requestAnimationFrame(animate);

        // Staging toggle
        stagedGroup.visible = stagedRef.current;

        // Cinematic Tour Path
        if (modeRef.current === "tour") {
          tourSubT += 0.0035;
          if (tourSubT >= 1.0) {
            tourSubT = 0;
            tourIdx = (tourIdx + 1) % waypoints.length;
            setCurrentTourLabel(waypoints[tourIdx]?.label || "Touring");
          }

          const currWp = waypoints[tourIdx] || waypoints[0];
          const nextWp = waypoints[(tourIdx + 1) % waypoints.length] || waypoints[0];

          // Smooth cosine interpolation
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
          // Orbit / Walk Damping
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

        renderer?.render(scene, camera);
      };

      animId = requestAnimationFrame(animate);
      setIsSceneReady(true);

      const onResize = () => {
        if (!container || !renderer) return;
        const nw = container.clientWidth;
        const nh = container.clientHeight;
        camera.aspect = nw / nh;
        camera.updateProjectionMatrix();
        renderer.setSize(nw, nh);
      };

      window.addEventListener("resize", onResize);

      return () => {
        cancelAnimationFrame(animId);
        window.removeEventListener("resize", onResize);
        dom.removeEventListener("mousedown", onMouseDown);
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        dom.removeEventListener("wheel", onWheel);
        renderer?.dispose();
      };
    } catch (err) {
      console.error("Three.js Architectural Twin Render Error:", err);
      setSceneFailed(true);
    }
  }, [blueprint]);

  return (
    <section
      ref={sectionRef}
      className={`relative w-full overflow-hidden rounded-2xl border border-stone-200 bg-stone-900 text-stone-100 shadow-2xl transition-all ${
        isFullscreen ? "fixed inset-0 z-50 h-screen w-screen rounded-none" : "min-h-[640px]"
      }`}
    >
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} className="relative h-[640px] w-full cursor-grab active:cursor-grabbing" />

      {/* Top Header Bar */}
      <div className="pointer-events-none absolute left-0 right-0 top-0 flex items-center justify-between p-4 bg-gradient-to-b from-black/70 via-black/30 to-transparent">
        <div className="pointer-events-auto flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 border border-amber-500/40 backdrop-blur-md">
            <Building2 className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-wide text-white">{propertyTitle}</span>
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-300 border border-emerald-500/30">
                Visual Adjacency BIM Twin
              </span>
            </div>
            <p className="text-xs text-stone-300">
              {propertyType} · {floorDesc} · {carpetSqft.toLocaleString()} sq.ft · {orientation}
            </p>
          </div>
        </div>

        {/* Top Controls */}
        <div className="pointer-events-auto flex items-center gap-2">
          {/* Floor Level Filter (for Villas or Multi-Tier Properties) */}
          {levelsCount > 1 && (
            <div className="flex items-center rounded-lg bg-stone-900/80 p-0.5 border border-stone-700 backdrop-blur-md text-xs">
              <button
                onClick={() => handleSetFloorFilter(-1)}
                className={`px-2 py-1 rounded-md transition-all ${
                  activeFloorFilter === -1 ? "bg-amber-500 text-stone-950 font-semibold" : "text-stone-300 hover:text-white"
                }`}
              >
                All Levels
              </button>
              {Array.from({ length: levelsCount }).map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSetFloorFilter(idx)}
                  className={`px-2 py-1 rounded-md transition-all ${
                    activeFloorFilter === idx ? "bg-amber-500 text-stone-950 font-semibold" : "text-stone-300 hover:text-white"
                  }`}
                >
                  L{idx}
                </button>
              ))}
            </div>
          )}

          {/* Staging Toggle */}
          <button
            onClick={() => setIsStaged((v) => !v)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium backdrop-blur-md border transition-all ${
              isStaged
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : "bg-stone-900/80 text-stone-400 border-stone-700 hover:text-stone-200"
            }`}
          >
            <BoxIcon className="h-3.5 w-3.5" />
            {isStaged ? "Furnished" : "Bare Shell"}
          </button>

          {/* Top-Down Cutaway Toggle */}
          <button
            onClick={toggleTopDownCutaway}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium backdrop-blur-md border transition-all ${
              isTopDown
                ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/40"
                : "bg-stone-900/80 text-stone-400 border-stone-700 hover:text-stone-200"
            }`}
          >
            <Grid className="h-3.5 w-3.5" />
            {isTopDown ? "3D Perspective" : "Cutaway Plan"}
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={toggleFullscreen}
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-900/80 text-stone-300 border border-stone-700 backdrop-blur-md hover:text-white transition-all"
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Bottom Mode Navigation Bar */}
      <div className="pointer-events-none absolute bottom-4 left-4 right-4 flex items-end justify-between">
        {/* Left: Mode Switcher & Room Pills */}
        <div className="pointer-events-auto flex flex-col gap-2 max-w-[70%]">
          {/* Mode Tabs */}
          <div className="flex items-center gap-1 rounded-xl bg-stone-900/90 p-1 border border-stone-700/80 backdrop-blur-md shadow-lg w-fit">
            <button
              onClick={() => {
                setActiveMode("orbit");
                setIsTopDown(false);
                if (cameraControlRef.current) cameraControlRef.current.setTopDown(false);
              }}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                activeMode === "orbit" && !isTopDown ? "bg-amber-500 text-stone-950 font-semibold shadow" : "text-stone-300 hover:text-white"
              }`}
            >
              <Navigation className="h-3.5 w-3.5" />
              Orbit View
            </button>
            <button
              onClick={() => {
                setActiveMode("walk");
                setIsTopDown(false);
                if (activeRoom) {
                  cameraControlRef.current?.focusRoom(activeRoom.id);
                } else {
                  cameraControlRef.current?.focusRoom("living");
                }
              }}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                activeMode === "walk" ? "bg-amber-500 text-stone-950 font-semibold shadow" : "text-stone-300 hover:text-white"
              }`}
            >
              <Footprints className="h-3.5 w-3.5" />
              First Person
            </button>
            <button
              onClick={() => {
                setActiveMode("tour");
                setIsTopDown(false);
              }}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                activeMode === "tour" ? "bg-amber-500 text-stone-950 font-semibold shadow" : "text-stone-300 hover:text-white"
              }`}
            >
              <Camera className="h-3.5 w-3.5" />
              Cinematic Tour
            </button>
          </div>

          {/* Room Selection Carousel */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            <button
              onClick={handleSelectWholeProperty}
              className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-all border backdrop-blur-md ${
                activeRoomIndex === -1
                  ? "bg-stone-100 text-stone-950 border-white font-semibold shadow"
                  : "bg-stone-900/85 text-stone-300 border-stone-700/70 hover:bg-stone-800"
              }`}
            >
              Full Residence
            </button>
            {activeRooms.map((room, idx) => {
              const isSelected = activeRoomIndex === idx;
              return (
                <button
                  key={room.id}
                  onClick={() => handleSelectRoom(idx)}
                  className={`flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-all border backdrop-blur-md ${
                    isSelected
                      ? "bg-amber-500 text-stone-950 border-amber-400 font-semibold shadow"
                      : "bg-stone-900/85 text-stone-300 border-stone-700/70 hover:bg-stone-800"
                  }`}
                >
                  <span>{room.name}</span>
                  {room.imageReference && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" title="Photo Reference Attached" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Drawer Toggle Button if closed */}
        {!isDrawerOpen && (
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="pointer-events-auto flex items-center gap-2 rounded-xl bg-stone-900/90 px-3 py-2 text-xs font-medium text-amber-300 border border-amber-500/40 shadow-xl backdrop-blur-md hover:bg-stone-800 transition-all"
          >
            <Sparkles className="h-4 w-4" />
            Visual Adjacency Drawer
          </button>
        )}
      </div>

      {/* Interactive Visual Reference & Adjacency Drawer (Right Side) */}
      {isDrawerOpen && (
        <aside className="pointer-events-auto absolute right-4 top-16 bottom-16 w-80 rounded-2xl bg-stone-900/95 p-4 border border-stone-700/80 shadow-2xl backdrop-blur-xl flex flex-col justify-between overflow-y-auto">
          <div>
            {/* Drawer Header */}
            <div className="flex items-center justify-between pb-3 border-b border-stone-800">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-400" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-200">
                  {activeRoom ? "Room Visual Intelligence" : "Topological Adjacency Graph"}
                </h3>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="text-stone-400 hover:text-stone-200 text-xs px-1.5 py-0.5 rounded hover:bg-stone-800"
              >
                ✕
              </button>
            </div>

            {/* Content: Active Room Details */}
            {activeRoom ? (
              <div className="mt-3 space-y-3">
                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-white">{activeRoom.name}</h4>
                    <span className="text-[11px] font-mono text-stone-400">{activeRoom.dimensions}</span>
                  </div>
                  <p className="text-xs text-stone-300 mt-0.5">{activeRoom.highlight}</p>
                </div>

                {/* Reference Photograph Attributed to this Room */}
                <div className="rounded-xl overflow-hidden border border-stone-700/70 bg-stone-950/80 p-2 space-y-2">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-stone-400 flex items-center gap-1">
                      <Camera className="h-3 w-3 text-amber-400" /> Photo Reference
                    </span>
                    {activeRoom.imageReference ? (
                      <span className="text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        {Math.round(activeRoom.imageReference.confidence * 100)}% Visual AI Conf.
                      </span>
                    ) : (
                      <span className="text-stone-400">Architectural Cadence</span>
                    )}
                  </div>

                  {activeRoom.imageReference?.source ? (
                    <div className="relative h-28 w-full rounded-lg overflow-hidden bg-stone-800">
                      {/* Image render with error fallback */}
                      <img
                        src={activeRoom.imageReference.source}
                        alt={activeRoom.name}
                        className="h-full w-full object-cover"
                        onError={(e) => {
                          // Fallback to stylized vector graphic if URL is unreachable
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-stone-950/80 via-transparent to-transparent flex items-end p-2">
                        <span className="text-[10px] text-stone-200 font-medium truncate">
                          {activeRoom.imageReference.detectedFinish}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-24 w-full flex-col items-center justify-center rounded-lg bg-stone-800/60 p-2 text-center text-xs text-stone-400">
                      <Building2 className="h-6 w-6 text-stone-500 mb-1" />
                      Pending user image extraction
                    </div>
                  )}

                  <div className="text-[11px] text-stone-300 bg-stone-900/60 p-1.5 rounded-md border border-stone-800">
                    <span className="font-semibold text-amber-300">Surface Finish: </span>
                    {activeRoom.floorType}
                  </div>
                </div>

                {/* Connected Adjacency Boundaries */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1 text-[11px] font-semibold text-stone-400 uppercase tracking-wide">
                    <Link2 className="h-3 w-3 text-indigo-400" />
                    Connected Adjacent Rooms ({activeRoom.adjacentRooms?.length || 0})
                  </div>

                  {activeRoom.adjacentRooms && activeRoom.adjacentRooms.length > 0 ? (
                    <div className="space-y-1.5">
                      {activeRoom.adjacentRooms.map((conn, cIdx) => (
                        <div
                          key={cIdx}
                          className="rounded-lg bg-stone-800/70 p-2 border border-stone-700/60 text-xs hover:border-amber-500/50 transition-all flex items-center justify-between group"
                        >
                          <div className="pr-2">
                            <div className="font-medium text-stone-200 group-hover:text-amber-300 transition-colors">
                              {conn.neighborName}
                            </div>
                            <div className="text-[10px] text-stone-400 flex items-center gap-1 mt-0.5">
                              <span className="capitalize text-amber-400/90">{conn.boundaryType.replace("_", " ")}</span>
                              <span>·</span>
                              <span>{conn.relativeDirection}</span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleSelectRoomById(conn.neighborId)}
                            className="flex h-7 w-7 items-center justify-center rounded-md bg-stone-700/80 text-stone-300 group-hover:bg-amber-500 group-hover:text-stone-950 transition-all shrink-0"
                            title="Fly to this adjacent room"
                          >
                            <ArrowRight className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-stone-400 italic">No direct partition openings</p>
                  )}
                </div>
              </div>
            ) : (
              // Overview Adjacency Graph State (When full residence is selected)
              <div className="mt-3 space-y-3">
                <div className="rounded-xl bg-stone-950/70 p-2.5 border border-stone-800 space-y-2">
                  <div className="text-xs text-stone-300 leading-relaxed">
                    {adjacencyGraph?.inferredLayoutSummary || aboutSummary}
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-stone-800/80 text-[11px]">
                    <div>
                      <span className="text-stone-400">Primary Facing:</span>
                      <div className="font-semibold text-amber-300">{orientation}</div>
                    </div>
                    <div>
                      <span className="text-stone-400">Total Rooms:</span>
                      <div className="font-semibold text-white">{activeRooms.length} Zones</div>
                    </div>
                  </div>
                </div>

                {/* Inferred Topological Connections List */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold text-stone-400 uppercase tracking-wide flex items-center gap-1">
                    <Compass className="h-3 w-3 text-amber-400" />
                    Spatial Boundary Matrix
                  </div>
                  <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1 scrollbar-thin">
                    {(adjacencyGraph?.edges || []).map((edge, eIdx) => (
                      <div key={eIdx} className="rounded-lg bg-stone-800/60 p-2 border border-stone-700/50 text-xs">
                        <div className="flex items-center justify-between font-medium text-stone-200">
                          <span className="capitalize">{edge.from}</span>
                          <span className="text-amber-400 text-[10px]">↔</span>
                          <span className="capitalize">{edge.to}</span>
                        </div>
                        <div className="text-[10px] text-stone-400 mt-0.5 flex items-center justify-between">
                          <span className="capitalize text-stone-300">{edge.boundaryType.replace("_", " ")}</span>
                          <span className="text-[9px] text-stone-500">{edge.relativeDirection}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Drawer Footer Actions */}
          <div className="pt-3 border-t border-stone-800 flex items-center justify-between text-[11px] text-stone-400">
            <span>BIM Specification v2.1</span>
            <button
              onClick={handleSelectWholeProperty}
              className="text-amber-400 hover:underline flex items-center gap-1 font-medium"
            >
              Reset Camera
            </button>
          </div>
        </aside>
      )}

      {/* Cinematic Tour Label Pill (When Tour Mode is Active) */}
      {activeMode === "tour" && (
        <div className="pointer-events-none absolute left-1/2 top-16 -translate-x-1/2 rounded-full bg-black/85 px-4 py-1.5 text-xs font-semibold text-amber-300 border border-amber-500/40 shadow-xl backdrop-blur-md flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping" />
          {currentTourLabel}
        </div>
      )}
    </section>
  );
};

export default ArchitecturalTwinViewer;
