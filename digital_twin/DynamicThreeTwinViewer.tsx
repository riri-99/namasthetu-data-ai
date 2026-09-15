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
} from "lucide-react";
import * as THREE from "three";
import { SpatialRoom } from "@/types/property";

export interface SpatialBox {
  x: number;
  y: number;
  z: number;
  w: number;
  d: number;
  h: number;
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
export interface InspectionDefectPin {
  id: string;
  roomId: string;
  roomName: string;
  type: string;
  severity: string;
  position: [number, number, number];
  color: string;
  description: string;
  floorLevel: number;
}

export interface DigitalTwinRoom {
  id: string;
  name: string;
  category?: string;
  dimensions: string;
  carpetSqft: number;
  highlight: string;
  floorType: string;
  floorColor: string;
  wallColor: string;
  floorLevel?: number;
  bounds: SpatialBox;
  furniture: StagedFurniture[];
  lights?: Array<{ position: [number, number, number]; color: string; intensity: number; distance: number }>;
  defects?: InspectionDefectPin[];
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

export interface DigitalTwinBlueprint {
  propertyId: string;
  publicId?: string;
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
  flooring?: string;
  furnishing?: string;
  facing?: string;
  views?: string[];
  balconyCount?: number;
  bathroomsCount?: number;
  efficiency: number;
  orientation: string;
  archetype?: string;
  levelsCount?: number;
  aboutSummary?: string;
  environmentalTheme: string;
  sunlightDirection?: [number, number, number];
  sunlightColor?: string;
  defects?: InspectionDefectPin[];
  floors?: FloorLevelSpec[];
  rooms: DigitalTwinRoom[];
  structuralWalls: StructuralWall[];
  doors?: DoorSpecification[];
  windows?: WindowSpecification[];
  balconies?: BalconySpecification[];
  glassPanels: GlassPanel[];
  focalTargets: Record<string, CameraFocalTarget>;
  waypoints: TourWaypoint[];
  fixtures: Array<{ item: string; detail: string; included: boolean }>;
}

export interface DynamicThreeTwinViewerProps {
  blueprint?: DigitalTwinBlueprint;
  rooms?: SpatialRoom[];
  propertyTitle?: string;
  conditionScore?: number;
  carpetSqft?: number;
  builtUpSqft?: number;
  floorHeight?: string;
  efficiency?: number;
  orientation?: string;
}

type TwinMode = "orbit" | "walk" | "tour";

const DEFAULT_ROOMS: SpatialRoom[] = [
  {
    id: "living",
    name: "Living & Dining Hall",
    dimensions: "30' x 22'",
    carpetSqft: 660,
    highlight: "Botticino Italian marble, floor-to-ceiling glass sliders looking to horizon",
    wallColor: "#FAF8F5",
    floorType: "Italian Botticino Marble",
  },
  {
    id: "kitchen",
    name: "Siemens Culinary Studio",
    dimensions: "15' x 15'",
    carpetSqft: 220,
    highlight: "Quartz island counter, Blum soft-close fittings & integrated downdraft",
    wallColor: "#F8F8F8",
    floorType: "Honed Quartzite",
  },
  {
    id: "master",
    name: "Master Suite",
    dimensions: "19' x 18'",
    carpetSqft: 342,
    highlight: "Engineered German oak wood floor, walk-in dressing wardrobe and private balcony",
    wallColor: "#EAE7DF",
    floorType: "Engineered Oak Hardwood",
  },
  {
    id: "bedroom_2",
    name: "Guest Suite (Bedroom 2)",
    dimensions: "15' x 14'",
    carpetSqft: 210,
    highlight: "Matte vitrified tiles, acoustic double-glazed windows",
    wallColor: "#F1EEE7",
    floorType: "Vitrified Matte Tile",
  },
  {
    id: "balcony",
    name: "Covered Sky Deck",
    dimensions: "21' x 11'",
    carpetSqft: 231,
    highlight: "Teak composite deck, frameless glass balustrade",
    wallColor: "#ECE9E2",
    floorType: "Weatherproof Teak Composite Deck",
  },
];

const DEFAULT_FIXTURES = [
  { item: "Modular Kitchen with Quartz Island", detail: "German Blum hardware & soft-close cabinets", included: true },
  { item: "VRV Central Climate Control", detail: "Daikin multi-zone inverter cooling", included: true },
  { item: "Italian Botticino Marble", detail: "Single-lot mirror-polished slabs in living & dining", included: true },
  { item: "Smart Home Lighting Automation", detail: "Lutron scene dimming & app control", included: true },
  { item: "Designer Staged Loose Furniture", detail: "Available for turnkey buyout from interior partner", included: false },
];

const DEFAULT_FOCAL_TARGETS: Record<string, CameraFocalTarget> = {
  living: { target: [-0.8, 1.6, 0.8], theta: 0.45, phi: 1.05, radius: 14, walk: [-1.0, 1.65, 3.2] },
  kitchen: { target: [6.9, 1.5, -0.6], theta: 1.95, phi: 1.05, radius: 12.5, walk: [5.8, 1.65, 1.2] },
  master: { target: [-6.8, 1.5, 0.5], theta: 0.35, phi: 1.08, radius: 13, walk: [-5.4, 1.65, 2.2] },
  bedroom_2: { target: [6.9, 1.5, 4.6], theta: 1.85, phi: 1.08, radius: 12, walk: [5.5, 1.65, 3.6] },
  balcony: { target: [1.8, 1.2, 5.2], theta: 2.35, phi: 1.05, radius: 12, walk: [0.8, 1.65, 4.4] },
  all: { target: [0, 2.8, 0], theta: 0.72, phi: 1.05, radius: 34, walk: [0, 1.65, 12] },
};

const DEFAULT_WAYPOINTS: TourWaypoint[] = [
  { p: [4.0, 3.5, 18.0], l: [0, 2.5, 0], label: "Approach · Architectural Facade" },
  { p: [-1.0, 1.65, 3.2], l: [2.0, 1.2, 0.0], label: "Living & Dining Pavilion" },
  { p: [5.8, 1.65, 1.2], l: [7.8, 1.1, -1.0], label: "Culinary Kitchen Studio (3:1 Ratio)" },
  { p: [-5.4, 1.65, 2.2], l: [-7.8, 1.1, -0.6], label: "Presidential Master Suite" },
  { p: [0.8, 1.65, 4.4], l: [2.8, 1.4, 6.5], label: "Covered Sky Deck & Balcony" },
  { p: [18, 16, 18], l: [0, 3.0, 0], label: "Aerial · Full Spatial Digital Twin" },
];

export const DynamicThreeTwinViewer: React.FC<DynamicThreeTwinViewerProps> = ({
  blueprint,
  rooms: propRooms,
  propertyTitle: propTitle = "Sovereign Luxury Residence",
  conditionScore: propCondition = 9.6,
  carpetSqft: propCarpet = 2000,
  builtUpSqft: propBuiltUp = 2500,
  floorHeight: propFloorHeight = "10.5 ft",
  efficiency: propEfficiency = 84,
  orientation: propOrientation = "East-Facing",
}) => {
  const propertyTitle = blueprint?.propertyTitle || propTitle;
  const conditionScore = blueprint?.conditionScore ?? propCondition;
  const carpetSqft = blueprint?.carpetSqft ?? propCarpet;
  const floorHeight = blueprint?.floorHeight || propFloorHeight;
  const orientation = blueprint?.orientation || propOrientation;
  const fixtures = blueprint?.fixtures || DEFAULT_FIXTURES;
  const bhkCount = blueprint?.bhkCount || 3;
  const levelsCount = blueprint?.levelsCount || (blueprint?.floors ? blueprint.floors.length : 1);
  const propertyType = blueprint?.propertyType || "Apartment";
  const floorDesc = blueprint?.floor || "Typical Floor";
  const aboutSummary = blueprint?.aboutSummary || `Verified civil and spatial specification model for ${propertyTitle}.`;

  // Calculate Living Hall to Kitchen Ratio
  const livingRoom = blueprint?.rooms?.find((r) => r.name.toLowerCase().includes("living"));
  const kitchenRoom = blueprint?.rooms?.find((r) => r.name.toLowerCase().includes("kitchen"));
  const hallKitchenRatio =
    livingRoom && kitchenRoom && kitchenRoom.carpetSqft > 0
      ? (livingRoom.carpetSqft / kitchenRoom.carpetSqft).toFixed(2)
      : "3.00";

  const activeRooms: SpatialRoom[] = blueprint
    ? blueprint.rooms.map((r) => ({
        id: r.id,
        name: r.name,
        dimensions: r.dimensions,
        carpetSqft: r.carpetSqft,
        highlight: r.highlight,
        wallColor: r.wallColor,
        floorType: r.floorType,
      }))
    : propRooms || DEFAULT_ROOMS;

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

  const activeRoom =
    activeRoomIndex >= 0 && activeRooms[activeRoomIndex]
      ? activeRooms[activeRoomIndex]
      : activeRooms[0] || DEFAULT_ROOMS[0];

  const handleSelectRoom = (index: number) => {
    setActiveRoomIndex(index);
    const room = activeRooms[index];
    if (room && cameraControlRef.current) {
      cameraControlRef.current.focusRoom(room.id);
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

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let animId = 0;
    let renderer: THREE.WebGLRenderer | null = null;

    try {
      const width = container.clientWidth || 800;
      const height = container.clientHeight || 540;

      const scene = new THREE.Scene();
      const fogColor = 0xd5cfc4;
      scene.background = new THREE.Color(fogColor);
      scene.fog = new THREE.Fog(fogColor, 50, 140);

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

      // Lighting Rig with Schema Facing / Sunlight Alignment
      scene.add(new THREE.HemisphereLight(0xfff5e6, 0xa39b8d, 0.72));
      const sunCol = blueprint?.sunlightColor ? parseInt(blueprint.sunlightColor.replace("#", ""), 16) : 0xffeeD6;
      const sun = new THREE.DirectionalLight(sunCol, 0.98);
      if (blueprint?.sunlightDirection) {
        sun.position.set(blueprint.sunlightDirection[0], blueprint.sunlightDirection[1], blueprint.sunlightDirection[2]);
      } else {
        sun.position.set(30, 48, 22);
      }
      sun.castShadow = true;
      sun.shadow.mapSize.set(1024, 1024);
      Object.assign(sun.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, far: 140 });
      scene.add(sun);

      // Materials
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

      const roofGroup = new THREE.Group();
      scene.add(roofGroup);

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

      // Ground plane & Roads
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

      // Surrounding Context
      const nb = [
        { x: -36, z: -26, w: 12, d: 14, h: 10, mat: M.grey1 },
        { x: -38, z: 8, w: 10, d: 9, h: 8, mat: M.grey2 },
        { x: 34, z: -26, w: 14, d: 14, h: 11, mat: M.grey2 },
        { x: 42, z: 6, w: 11, d: 9, h: 14, mat: M.grey1 },
      ];
      nb.forEach((n) => box(n.w, n.h, n.d, n.mat, n.x, n.h / 2, n.z));

      // Trees
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
      // PROCEDURAL BLUEPRINT RENDERING PIPELINE
      // ========================================================
      if (blueprint && blueprint.rooms && blueprint.rooms.length > 0) {
        // 1. Foundation Podium Slab
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

        // 2. Render Rooms (Floors, Skirting Baseboards, Furniture, Lights)
        blueprint.rooms.forEach((r) => {
          const b = r.bounds;
          const hexCol = parseInt(r.floorColor.replace("#", ""), 16) || 0xf4f1ea;
          const roomFloorMat = new THREE.MeshLambertMaterial({ color: hexCol });

          // Room Floor Slab
          const floorMesh = box(b.w, 0.28, b.d, roomFloorMat, b.x, b.y + 0.14, b.z, 0, structuralGroup);
          floorMesh.userData = { floorLevel: r.floorLevel ?? 0, type: "floor" };

          // Skirting Baseboard Border
          const skirtH = 0.08, skirtT = 0.04;
          box(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z - b.d / 2 + skirtT / 2, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
          box(b.w, skirtH, skirtT, M.cream2, b.x, b.y + 0.28 + skirtH / 2, b.z + b.d / 2 - skirtT / 2, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
          box(skirtT, skirtH, b.d, M.cream2, b.x - b.w / 2 + skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };
          box(skirtT, skirtH, b.d, M.cream2, b.x + b.w / 2 - skirtT / 2, b.y + 0.28 + skirtH / 2, b.z, 0, structuralGroup).userData = { floorLevel: r.floorLevel ?? 0 };

          // Staged Furniture
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

        // 3. Structural Perimeter & Partition Walls
        blueprint.structuralWalls?.forEach((w) => {
          const [sx, sy, sz] = w.size;
          const [px, py, pz] = w.position;
          const mat = w.isExterior ? M.cream2 : (M[w.materialKey] || M.cream);
          const wallMesh = box(sx, sy, sz, mat, px, py, pz, 0, structuralGroup);
          wallMesh.userData = { floorLevel: w.floorLevel ?? 0, type: "wall", isExterior: w.isExterior };
        });

        // 4. Engineered Doors (Frames, Leaves ajar, Brass Handles, Sliders)
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
            box(0.04, 0.35, 0.04, M.accent, 0.08, 0, 0.04, 0, doorGroup);
          } else if (d.doorType === "portal") {
            const frameMat = M.wood2;
            box(0.12, dh, 0.20, frameMat, -dw / 2 + 0.06, 0, 0, 0, doorGroup);
            box(0.12, dh, 0.20, frameMat, dw / 2 - 0.06, 0, 0, 0, doorGroup);
            box(dw, 0.12, 0.20, frameMat, 0, dh / 2 - 0.06, 0, 0, doorGroup);
          } else {
            const frameMat = M.dark;
            box(0.08, dh, 0.16, frameMat, -dw / 2 + 0.04, 0, 0, 0, doorGroup);
            box(0.08, dh, 0.16, frameMat, dw / 2 - 0.04, 0, 0, 0, doorGroup);
            box(dw, 0.08, 0.16, frameMat, 0, dh / 2 - 0.04, 0, 0, doorGroup);

            const leafW = dw - 0.10;
            const leafH = dh - 0.08;
            const leafMesh = new THREE.Mesh(new THREE.BoxGeometry(leafW, leafH, 0.04), M.wood2);
            const hinge = new THREE.Group();
            hinge.position.set(-dw / 2 + 0.06, 0, 0);
            leafMesh.position.set(leafW / 2, 0, 0);
            hinge.add(leafMesh);
            hinge.rotation.y = d.openAngle || 0.55;

            const handleGroup = new THREE.Group();
            handleGroup.position.set(leafW - 0.08, 0, 0.035);
            box(0.04, 0.14, 0.03, M.accent, 0, 0, 0, 0, handleGroup);
            box(0.12, 0.03, 0.04, M.accent, -0.04, 0.03, 0.03, 0, handleGroup);
            hinge.add(handleGroup);

            doorGroup.add(hinge);
          }

          structuralGroup.add(doorGroup);
        });

        // 5. Exterior Windows (Bronze Frames, Glazing, Mullions, Ledge Sills)
        blueprint.windows?.forEach((win) => {
          const [wx, wy, wz] = win.position;
          const [ww, wh] = win.size;
          const rotY = win.rotationY || 0;
          const winGroup = new THREE.Group();
          winGroup.position.set(wx, wy, wz);
          winGroup.rotation.y = rotY;
          winGroup.userData = { floorLevel: win.floorLevel ?? 0, type: "window" };

          const frameMat = M.dark;
          const frameThick = 0.06;
          const frameDepth = 0.16;

          box(ww, frameThick, frameDepth, frameMat, 0, wh / 2 - frameThick / 2, 0, 0, winGroup);
          box(ww, frameThick, frameDepth, frameMat, 0, -wh / 2 + frameThick / 2, 0, 0, winGroup);
          box(frameThick, wh, frameDepth, frameMat, -ww / 2 + frameThick / 2, 0, 0, 0, winGroup);
          box(frameThick, wh, frameDepth, frameMat, ww / 2 - frameThick / 2, 0, 0, 0, winGroup);

          box(ww + 0.14, 0.06, frameDepth + 0.10, M.cream2, 0, -wh / 2 - 0.03, 0.04, 0, winGroup);

          if (win.hasMullions) {
            box(0.04, wh - frameThick * 2, frameDepth * 0.8, frameMat, 0, 0, 0, 0, winGroup);
            box(ww - frameThick * 2, 0.04, frameDepth * 0.8, frameMat, 0, 0.15, 0, 0, winGroup);
          }

          const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(ww - frameThick * 2, wh - frameThick * 2), M.glass);
          glassMesh.position.set(0, 0, 0);
          winGroup.add(glassMesh);

          structuralGroup.add(winGroup);
        });

        // 6. Bounded Balconies (Teak Decks, Glass Balustrades, Handrails)
        blueprint.balconies?.forEach((balc) => {
          const b = balc.bounds;
          const balcGroup = new THREE.Group();
          balcGroup.userData = { floorLevel: balc.floorLevel ?? 0, type: "balcony" };

          box(b.w, 0.18, b.d, M.wood2, b.x, b.y + 0.09, b.z, 0, balcGroup);
          box(b.w + 0.08, 0.08, b.d + 0.08, M.dark, b.x, b.y + 0.14, b.z, 0, balcGroup);

          balc.railings?.forEach((rail) => {
            const [rx, ry, rz] = rail.position;
            const [rw, rh] = rail.size;
            const rRot = rail.rotationY || 0;

            const railGroup = new THREE.Group();
            railGroup.position.set(rx, ry, rz);
            railGroup.rotation.y = rRot;

            const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(rw, rh - 0.08), M.rail);
            glassMesh.position.set(0, -0.04, 0);
            railGroup.add(glassMesh);

            box(rw, 0.06, 0.08, M.accent, 0, rh / 2 - 0.03, 0, 0, railGroup);
            box(rw, 0.06, 0.06, M.dark, 0, -rh / 2 + 0.03, 0, 0, railGroup);

            [-rw / 2 + 0.05, 0, rw / 2 - 0.05].forEach((px) => {
              box(0.05, rh, 0.05, M.dark, px, 0, 0, 0, railGroup);
            });

            balcGroup.add(railGroup);
          });

          structuralGroup.add(balcGroup);
        });

        // 7. Standalone Glass Panels (Double-height void & Mezzanine)
        blueprint.glassPanels?.forEach((gp) => {
          const [gw, gh] = gp.size;
          const [gx, gy, gz] = gp.position;
          const gf = new THREE.Mesh(new THREE.PlaneGeometry(gw, gh), M.glass);
          gf.position.set(gx, gy, gz);
          if (gp.rotationY) gf.rotation.y = gp.rotationY;
          gf.userData = { floorLevel: gp.floorLevel ?? 0, type: "glass" };
          structuralGroup.add(gf);

          if (gp.handrail) {
            const hr = box(gw, 0.06, 0.08, M.accent, gx, gy + gh / 2, gz, gp.rotationY || 0, structuralGroup);
            hr.userData = { floorLevel: gp.floorLevel ?? 0 };
          }
        });

        // 8. Roof Cutaway Slab
        const levels = blueprint.levelsCount || (blueprint.floors ? blueprint.floors.length : 1);
        const topElevation = levels === 3 ? 10.8 : levels === 2 ? 7.2 : 3.6;
        box(totalW - 2, 0.3, totalD - 2, M.slab, centerX, topElevation + 0.15, centerZ, 0, roofGroup);
        box(totalW - 2, 0.45, 0.2, M.cream, centerX, topElevation + 0.45, centerZ + (totalD - 2) / 2, 0, roofGroup);

        // 9. Inspection Defect Markers (Prisma InspectionPhoto / DefectSeverity)
        blueprint.defects?.forEach((def) => {
          const [dx, dy, dz] = def.position;
          const col = parseInt(def.color.replace("#", ""), 16) || 0xf59e0b;
          const pinMat = new THREE.MeshBasicMaterial({ color: col });
          const ringMat = new THREE.MeshBasicMaterial({ color: col, wireframe: true, transparent: true, opacity: 0.65 });

          const pinMesh = new THREE.Mesh(new THREE.SphereGeometry(0.14, 16, 16), pinMat);
          pinMesh.position.set(dx, dy, dz);

          const ringMesh = new THREE.Mesh(new THREE.RingGeometry(0.20, 0.32, 24), ringMat);
          ringMesh.position.set(dx, dy, dz);
          ringMesh.rotation.y = Math.PI / 2;

          const pGroup = new THREE.Group();
          pGroup.add(pinMesh);
          pGroup.add(ringMesh);
          pGroup.userData = { floorLevel: def.floorLevel ?? 0, type: "defect", defect: def };
          structuralGroup.add(pGroup);
        });
      }

      // Initial Camera State
      const defaultAll = focalTargets["all"] || DEFAULT_FOCAL_TARGETS.all;
      const cvState = {
        theta: defaultAll.theta,
        phi: defaultAll.phi,
        radius: defaultAll.radius,
        thetaT: defaultAll.theta,
        phiT: defaultAll.phi,
        radiusT: defaultAll.radius,
        target: new THREE.Vector3(...defaultAll.target),
        targetT: new THREE.Vector3(...defaultAll.target),
        lastInteraction: performance.now(),
        walk: { pos: new THREE.Vector3(...defaultAll.walk), yaw: 0, pitch: 0 },
        tour: { index: 0, time: 0 },
        keys: {} as Record<string, boolean>,
      };

      cameraControlRef.current = {
        focusRoom: (roomId: string) => {
          const focal = focalTargets[roomId] || focalTargets["all"] || DEFAULT_FOCAL_TARGETS.all;
          cvState.targetT.set(focal.target[0], focal.target[1], focal.target[2]);
          cvState.thetaT = focal.theta;
          cvState.phiT = focal.phi;
          cvState.radiusT = focal.radius;
          cvState.walk.pos.set(focal.walk[0], focal.walk[1], focal.walk[2]);
          cvState.lastInteraction = performance.now();
        },
        setTopDown: (topDown: boolean) => {
          if (topDown) {
            cvState.targetT.set(0, 2.5, 0);
            cvState.phiT = 0.08;
            cvState.radiusT = 44;
          } else {
            cvState.targetT.set(0, 3.2, 0);
            cvState.phiT = 1.05;
            cvState.radiusT = 36;
          }
          cvState.lastInteraction = performance.now();
        },
        applyFloorFilter: (floorIdx: number) => {
          if (floorIdx === -1) {
            structuralGroup.children.forEach((c) => {
              c.visible = true;
            });
            stagedGroup.children.forEach((c) => {
              c.visible = stagedRef.current;
            });
            roofGroup.visible = !topDownRef.current;
            cameraControlRef.current?.focusRoom("all");
          } else {
            structuralGroup.children.forEach((c) => {
              if (c.userData && c.userData.floorLevel !== undefined) {
                c.visible = c.userData.floorLevel === floorIdx;
              }
            });
            stagedGroup.children.forEach((c) => {
              if (c.userData && c.userData.floorLevel !== undefined) {
                c.visible = stagedRef.current && c.userData.floorLevel === floorIdx;
              }
            });
            roofGroup.visible = false;

            const fl = blueprint?.floors?.[floorIdx];
            if (fl) {
              cvState.targetT.set(0, fl.elevation + 2.0, 0);
              cvState.phiT = 0.65;
              cvState.radiusT = 28;
              cvState.lastInteraction = performance.now();
            }
          }
        },
      };

      const tmpA = new THREE.Vector3();
      const tmpB = new THREE.Vector3();
      const tmpL = new THREE.Vector3();
      const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

      let isDragging = false;
      let px = 0;
      let py = 0;
      const dom = renderer.domElement;

      const onPointerDown = (e: PointerEvent) => {
        isDragging = true;
        px = e.clientX;
        py = e.clientY;
        cvState.lastInteraction = performance.now();
        dom.setPointerCapture(e.pointerId);
      };

      const onPointerMove = (e: PointerEvent) => {
        if (!isDragging) return;
        const dx = e.clientX - px;
        const dy = e.clientY - py;
        px = e.clientX;
        py = e.clientY;
        cvState.lastInteraction = performance.now();

        if (modeRef.current === "walk") {
          cvState.walk.yaw -= dx * 0.0042;
          cvState.walk.pitch = Math.max(-0.7, Math.min(0.7, cvState.walk.pitch - dy * 0.003));
        } else {
          cvState.thetaT -= dx * 0.005;
          cvState.phiT = Math.max(0.12, Math.min(1.42, cvState.phiT - dy * 0.004));
        }
      };

      const onPointerUp = () => {
        isDragging = false;
      };

      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        cvState.radiusT = Math.min(75, Math.max(8, cvState.radiusT + e.deltaY * 0.02));
        cvState.lastInteraction = performance.now();
      };

      const onKeyDown = (e: KeyboardEvent) => {
        const target = e.target as HTMLElement | null;
        if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
          return;
        }
        if (modeRef.current === "walk") {
          const lower = e.key.toLowerCase();
          if (["arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d", " "].includes(lower)) {
            e.preventDefault();
          }
        }
        cvState.keys[e.key.toLowerCase()] = true;
      };

      const onKeyUp = (e: KeyboardEvent) => {
        cvState.keys[e.key.toLowerCase()] = false;
      };

      dom.addEventListener("pointerdown", onPointerDown);
      dom.addEventListener("pointermove", onPointerMove);
      dom.addEventListener("pointerup", onPointerUp);
      dom.addEventListener("wheel", onWheel, { passive: false });
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);

      let lastTime = performance.now();

      const animate = (now: number) => {
        animId = requestAnimationFrame(animate);

        const currentMode = modeRef.current;
        const dt = Math.min(0.05, (now - lastTime) / 1000);
        lastTime = now;

        stagedGroup.visible = stagedRef.current;
        roofGroup.visible = !topDownRef.current && floorFilterRef.current === -1;

        if (currentMode === "orbit") {
          if (now - cvState.lastInteraction > 4000 && !topDownRef.current) {
            cvState.thetaT += 0.0006;
          }
          cvState.target.lerp(cvState.targetT, 0.08);
          cvState.theta += (cvState.thetaT - cvState.theta) * 0.08;
          cvState.phi += (cvState.phiT - cvState.phi) * 0.08;
          cvState.radius += (cvState.radiusT - cvState.radius) * 0.08;

          camera.position.set(
            cvState.target.x + cvState.radius * Math.sin(cvState.phi) * Math.cos(cvState.theta),
            cvState.target.y + cvState.radius * Math.cos(cvState.phi),
            cvState.target.z + cvState.radius * Math.sin(cvState.phi) * Math.sin(cvState.theta)
          );
          camera.lookAt(cvState.target);
        } else if (currentMode === "walk") {
          const k = cvState.keys;
          const sp = 4.2 * dt;
          const fx = Math.sin(cvState.walk.yaw);
          const fz = Math.cos(cvState.walk.yaw);
          if (k["w"] || k["arrowup"]) {
            cvState.walk.pos.x -= fx * sp;
            cvState.walk.pos.z -= fz * sp;
          }
          if (k["s"] || k["arrowdown"]) {
            cvState.walk.pos.x += fx * sp;
            cvState.walk.pos.z -= fz * sp;
          }
          if (k["a"] || k["arrowleft"]) {
            cvState.walk.pos.x += fz * sp;
            cvState.walk.pos.z -= fx * sp;
          }
          if (k["d"] || k["arrowright"]) {
            cvState.walk.pos.x -= fz * sp;
            cvState.walk.pos.z += fx * sp;
          }
          cvState.walk.pos.x = Math.max(-16, Math.min(16, cvState.walk.pos.x));
          cvState.walk.pos.z = Math.max(-14, Math.min(16, cvState.walk.pos.z));
          camera.position.copy(cvState.walk.pos);
          camera.rotation.order = "YXZ";
          camera.rotation.y = cvState.walk.yaw;
          camera.rotation.x = cvState.walk.pitch;
          camera.rotation.z = 0;
        } else if (currentMode === "tour") {
          const legDuration = 4.5;
          cvState.tour.time += dt;
          if (cvState.tour.time >= legDuration) {
            cvState.tour.time = 0;
            cvState.tour.index = (cvState.tour.index + 1) % waypoints.length;
          }
          const currWp = waypoints[cvState.tour.index] || waypoints[0];
          const nextWp = waypoints[(cvState.tour.index + 1) % waypoints.length] || waypoints[0];
          const progress = ease(Math.min(1, cvState.tour.time / (legDuration * 0.65)));

          tmpA.fromArray(currWp.p);
          tmpB.fromArray(nextWp.p);
          camera.position.lerpVectors(tmpA, tmpB, progress);

          tmpA.fromArray(currWp.l);
          tmpB.fromArray(nextWp.l);
          tmpL.lerpVectors(tmpA, tmpB, progress);
          camera.lookAt(tmpL);

          const displayedLabel = (progress > 0.5 ? nextWp : currWp).label;
          setCurrentTourLabel(displayedLabel);
        }

        renderer?.render(scene, camera);
      };
      animate(performance.now());

      const resizeObserver = new ResizeObserver(() => {
        if (!container || !renderer) return;
        const w = container.clientWidth;
        const h = container.clientHeight;
        if (!w || !h) return;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      });
      resizeObserver.observe(container);

      requestAnimationFrame(() => setIsSceneReady(true));

      return () => {
        cancelAnimationFrame(animId);
        resizeObserver.disconnect();
        dom.removeEventListener("pointerdown", onPointerDown);
        dom.removeEventListener("pointermove", onPointerMove);
        dom.removeEventListener("pointerup", onPointerUp);
        dom.removeEventListener("wheel", onWheel);
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("keyup", onKeyUp);
        renderer?.dispose();
      };
    } catch (e) {
      console.error("DynamicThreeTwinViewer initialization error:", e);
      setSceneFailed(true);
    }
  }, [blueprint]);

  return (
    <div className="w-full flex flex-col gap-4">
      {/* Property Specifications & About Notes Card */}
      <div className="w-full bg-[#1A1B1F] border border-white/10 rounded-2xl p-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <span className="px-3 py-1 text-xs font-semibold rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30">
              {propertyType} · {bhkCount} BHK
            </span>
            <span className="text-xs text-white/60">Floor: {floorDesc}</span>
            <span className="text-xs text-white/40">•</span>
            <span className="text-xs text-emerald-400 font-medium">
              Hall:Kitchen Ratio: {hallKitchenRatio}:1
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs text-white/70">
            <span className="flex items-center gap-1.5">
              <Bed className="w-4 h-4 text-amber-400" />
              <strong>{bhkCount}</strong> Distinct Bedrooms
            </span>
            <span className="flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-blue-400" />
              <strong>{levelsCount}</strong> Physical Floor{levelsCount > 1 ? "s" : ""}
            </span>
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <ShieldCheck className="w-4 h-4" />
              BIM Geometry Enforced
            </span>
          </div>
        </div>

        {/* About Notes & Multi-Floor Filter Row */}
        <div className="pt-3 flex flex-col md:flex-row items-start justify-between gap-4">
          <div className="flex-1">
            <div className="text-[11px] font-semibold tracking-wider uppercase text-white/40 mb-1 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              <span>Verified Listing "About" Specifications</span>
            </div>
            <p className="text-xs text-white/80 leading-relaxed font-normal">{aboutSummary}</p>
          </div>

          {/* Floor Level Filter */}
          {blueprint?.floors && blueprint.floors.length > 1 && (
            <div className="flex items-center gap-1.5 p-1 bg-black/40 rounded-xl border border-white/10 shrink-0">
              <span className="text-[11px] text-white/40 px-2 font-medium">Floor:</span>
              <button
                onClick={() => handleSetFloorFilter(-1)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeFloorFilter === -1
                    ? "bg-white text-black font-semibold shadow-md"
                    : "text-white/60 hover:text-white"
                }`}
              >
                All Levels
              </button>
              {blueprint.floors.map((fl, idx) => (
                <button
                  key={fl.id}
                  onClick={() => handleSetFloorFilter(idx)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeFloorFilter === idx
                      ? "bg-white text-black font-semibold shadow-md"
                      : "text-white/60 hover:text-white"
                  }`}
                >
                  {fl.name.split(" ")[0]}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Primary 3D Viewer Container */}
      <section
        ref={sectionRef}
        className="relative w-full bg-[#18191C] text-white rounded-3xl overflow-hidden shadow-2xl border border-white/15"
      >
        {/* Viewer Top Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 bg-[#1F2024]/90 backdrop-blur-md border-b border-white/10 z-20">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
              <BoxIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-base text-white tracking-tight">{propertyTitle}</h3>
              <p className="text-xs text-white/50 flex items-center gap-2">
                <span>{carpetSqft.toLocaleString()} sq.ft carpet</span>
                <span>•</span>
                <span className="text-emerald-400 font-medium">Condition {conditionScore}/10</span>
                <span>•</span>
                <span>{orientation}</span>
              </p>
            </div>
          </div>

          {/* Mode Selector */}
          <div className="flex items-center gap-1.5 p-1 bg-black/40 rounded-2xl border border-white/5">
            {(["orbit", "walk", "tour"] as TwinMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setActiveMode(mode)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all ${
                  activeMode === mode
                    ? "bg-white text-black font-semibold shadow-lg shadow-white/10"
                    : "text-white/60 hover:text-white hover:bg-white/5"
                }`}
              >
                {mode === "orbit" && "3D Orbit"}
                {mode === "walk" && "Walkthrough"}
                {mode === "tour" && "Auto-Tour"}
              </button>
            ))}
          </div>

          {/* Toggles: Staged Furniture, Top-Down, Fullscreen */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsStaged(!isStaged)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 border transition-all ${
                isStaged
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                  : "bg-white/5 text-white/50 border-white/10 hover:text-white"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              {isStaged ? "Staged" : "Unstaged"}
            </button>

            <button
              onClick={toggleTopDownCutaway}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 border transition-all ${
                isTopDown
                  ? "bg-blue-500/20 text-blue-300 border-blue-500/30"
                  : "bg-white/5 text-white/50 border-white/10 hover:text-white"
              }`}
            >
              <Grid className="w-3.5 h-3.5" />
              Cutaway
            </button>

            <button
              onClick={toggleFullscreen}
              className="p-2 rounded-xl bg-white/5 text-white/70 hover:text-white border border-white/10 hover:bg-white/10 transition-all"
              title="Toggle Fullscreen"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Main 3D Canvas Viewport */}
        <div className="relative w-full h-[600px] bg-gradient-to-b from-[#1c1d22] to-[#121316]">
          {!isSceneReady && !sceneFailed && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#18191C] z-30">
              <div className="w-9 h-9 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-white/60 tracking-wider uppercase font-semibold">
                Compiling Multi-Level BIM Model...
              </p>
            </div>
          )}

          <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

          {/* Room Quick-Focus Dock */}
          <div className="absolute bottom-5 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-2 bg-black/70 backdrop-blur-lg rounded-2xl border border-white/15 z-20 shadow-2xl overflow-x-auto max-w-[94%]">
            <button
              onClick={handleSelectWholeProperty}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                activeRoomIndex === -1 ? "bg-white text-black shadow-md" : "text-white/70 hover:text-white hover:bg-white/10"
              }`}
            >
              Overview (All)
            </button>

            {activeRooms.map((room, idx) => (
              <button
                key={room.id || idx}
                onClick={() => handleSelectRoom(idx)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  activeRoomIndex === idx
                    ? "bg-amber-400 text-black font-semibold shadow-md"
                    : "text-white/70 hover:text-white hover:bg-white/10"
                }`}
              >
                <span>{room.name.split(" ")[0]}</span>
                <span className="text-[10px] opacity-70">({room.carpetSqft} sqft)</span>
              </button>
            ))}
          </div>

          {/* Mode Indicator Overlays */}
          {activeMode === "walk" && (
            <div className="absolute top-4 left-4 px-3.5 py-2 bg-black/80 backdrop-blur-md rounded-xl text-xs text-white/90 border border-white/10 flex items-center gap-2.5 z-20">
              <Footprints className="w-4 h-4 text-amber-400 animate-pulse" />
              <span>WASD or Arrows to walk inside · Drag mouse to look around</span>
            </div>
          )}

          {activeMode === "tour" && (
            <div className="absolute top-4 left-4 px-3.5 py-2 bg-black/80 backdrop-blur-md rounded-xl text-xs text-white/90 border border-white/10 flex items-center gap-2.5 z-20">
              <Navigation className="w-4 h-4 text-blue-400 animate-spin" />
              <span>Tour: {currentTourLabel}</span>
            </div>
          )}
        </div>

        {/* Fixture & Structural Spec Verification Drawer */}
        <div className="px-6 py-5 bg-[#17181C] border-t border-white/10 flex flex-col md:flex-row items-start justify-between gap-6">
          <div className="flex-1">
            <h4 className="text-xs uppercase tracking-widest text-white/40 font-semibold mb-1.5 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Active Room Architecture & Material Finish
            </h4>
            <p className="text-sm text-white/80 leading-relaxed font-normal">{activeRoom.highlight}</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {fixtures.slice(0, 4).map((f, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2 bg-white/5 rounded-xl border border-white/5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs text-white/70">{f.item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default DynamicThreeTwinViewer;
