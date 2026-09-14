"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Compass,
  Layers,
  Maximize2,
  Minimize2,
  Navigation,
  Play,
  RotateCw,
  Ruler,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Footprints,
  Eye,
  Grid,
  Smartphone,
} from "lucide-react";
import * as THREE from "three";
import { BrandLoader } from "@/components/ui/BrandLoader";
import { SpatialRoom } from "@/types/property";

interface ThreeTwinViewerProps {
  rooms?: SpatialRoom[];
  propertyTitle: string;
  conditionScore?: number;
  carpetSqft?: number;
  builtUpSqft?: number;
  floorHeight?: string;
  efficiency?: number;
  orientation?: string;
}

type TwinMode = "orbit" | "walk" | "tour" | "plan" | "pano";

const DEFAULT_ROOMS: SpatialRoom[] = [
  {
    id: "living",
    name: "Living & Dining",
    dimensions: "22' x 16'",
    carpetSqft: 285,
    highlight: "Italian Botticino marble, triple-glazed balcony sliders",
    wallColor: "#F4F1EA",
    floorType: "Italian Marble",
  },
  {
    id: "kitchen",
    name: "Modular Kitchen",
    dimensions: "14' x 11'",
    carpetSqft: 154,
    highlight: "Quartz island counter, Blum soft-close fittings",
    wallColor: "#F8F8F8",
    floorType: "Vitrified Tile",
  },
  {
    id: "master",
    name: "Master Suite",
    dimensions: "18' x 14'",
    carpetSqft: 252,
    highlight: "Engineered oak floor, private sunset balcony",
    wallColor: "#EAE7DF",
    floorType: "Engineered Oak",
  },
  {
    id: "bath",
    name: "En-suite Bath",
    dimensions: "10' x 8'",
    carpetSqft: 80,
    highlight: "Grohe thermostatic concealed fixtures, frameless glass",
    wallColor: "#F1EEE7",
    floorType: "Anti-skid Ceramic",
  },
  {
    id: "balcony",
    name: "Deck Balcony",
    dimensions: "16' x 7'",
    carpetSqft: 112,
    highlight: "Teak composite deck, frameless glass balustrade",
    wallColor: "#ECE9E2",
    floorType: "Teak Composite",
  },
];

const FIXTURES = [
  { item: "Modular Kitchen with Quartz Island", detail: "German Blum hardware & soft-close cabinets", included: true },
  { item: "VRV Central Climate Control", detail: "Daikin multi-zone inverter cooling", included: true },
  { item: "Italian Botticino Marble", detail: "Single-lot mirror-polished slabs in living & dining", included: true },
  { item: "Smart Home Lighting Automation", detail: "Lutron scene dimming & app control", included: true },
  { item: "Teak Wood Main & Internal Doors", detail: "8-foot height with magnetic Yale latches", included: true },
  { item: "Designer Staged Loose Furniture", detail: "Available for turnkey buyout from interior partner", included: false },
  { item: "Audio & Entertainment Electronics", detail: "Wall-mount brackets pre-wired; appliances not included", included: false },
];

const PANO_ROOMS = [
  { id: "living", name: "Living", image: "/panoramas/pano_1.jpg", thumb: "/rooms/room_1.jpg" },
  { id: "kitchen", name: "Kitchen", image: "/panoramas/pano_2.jpg", thumb: "/rooms/room_2.jpg" },
  { id: "master", name: "Master", image: "/panoramas/pano_3.jpg", thumb: "/rooms/room_3.jpg" },
  { id: "bath", name: "Bath", image: "/panoramas/pano_4.jpg", thumb: "/rooms/room_4.jpg" },
  { id: "balcony", name: "Balcony", image: "/panoramas/pano_5.jpg", thumb: "/rooms/room_5.jpg" },
];

// Room-specific camera focal targets in 3D orbit space
const ROOM_FOCAL_TARGETS: Record<string, { target: [number, number, number]; theta: number; phi: number; radius: number; walk: [number, number, number] }> = {
  living: { target: [-0.8, 1.8, 2.0], theta: 0.45, phi: 1.05, radius: 14, walk: [-1.2, 1.65, 3.4] },
  kitchen: { target: [3.6, 1.6, -1.2], theta: 1.95, phi: 1.05, radius: 13, walk: [3.8, 1.65, -0.4] },
  master: { target: [-2.8, 4.8, -1.6], theta: 0.35, phi: 1.08, radius: 13, walk: [-1.5, 4.95, 1.8] },
  bath: { target: [-5.2, 4.8, 1.2], theta: 0.85, phi: 1.10, radius: 10, walk: [-4.5, 4.95, 0.5] },
  balcony: { target: [5.5, 4.8, 1.6], theta: 2.35, phi: 1.05, radius: 12, walk: [4.8, 4.95, 0.2] },
  all: { target: [0, 3.2, 0], theta: 0.72, phi: 1.05, radius: 34, walk: [0, 1.65, 11] },
};

export const ThreeTwinViewer: React.FC<ThreeTwinViewerProps> = ({
  rooms = DEFAULT_ROOMS,
  propertyTitle,
  conditionScore = 9.4,
  carpetSqft = 1850,
  builtUpSqft = 2240,
  floorHeight = "10.5 ft",
  efficiency = 83,
  orientation = "North-East",
}) => {
  const [activeMode, setActiveMode] = useState<TwinMode>("orbit");
  const [activeRoomIndex, setActiveRoomIndex] = useState<number>(0);
  const [isStaged, setIsStaged] = useState<boolean>(true);
  const [isTopDown, setIsTopDown] = useState<boolean>(false);
  const [showMeasurements, setShowMeasurements] = useState<boolean>(true);
  const [isRotating, setIsRotating] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isSceneReady, setIsSceneReady] = useState<boolean>(false);
  const [sceneFailed, setSceneFailed] = useState<boolean>(false);
  const [isPanoLoading, setIsPanoLoading] = useState<boolean>(false);
  const [rotateDismissed, setRotateDismissed] = useState<boolean>(false);

  const sectionRef = useRef<HTMLElement>(null);
  const [currentTourLabel, setCurrentTourLabel] = useState<string>("Approach · Facade");
  const [activePanoIndex, setActivePanoIndex] = useState<number>(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const panoContainerRef = useRef<HTMLDivElement>(null);

  // Active state synchronization refs to avoid recreating the Three.js scene on state toggles
  const modeRef = useRef<TwinMode>(activeMode);
  modeRef.current = activeMode;

  const stagedRef = useRef<boolean>(isStaged);
  stagedRef.current = isStaged;

  const topDownRef = useRef<boolean>(isTopDown);
  topDownRef.current = isTopDown;

  const autoRotateRef = useRef<boolean>(isRotating);
  autoRotateRef.current = isRotating;

  // External controller ref for camera movement
  const cameraControlRef = useRef<{
    focusRoom: (roomId: string) => void;
    setTopDown: (topDown: boolean) => void;
  } | null>(null);

  const activeRoom = rooms[activeRoomIndex] || rooms[0] || DEFAULT_ROOMS[0];

  // Handle room button click
  const handleSelectRoom = (index: number) => {
    setActiveRoomIndex(index);
    setActivePanoIndex(index % PANO_ROOMS.length);
    const room = rooms[index] || DEFAULT_ROOMS[index];
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

  // Fullscreen shows only the twin viewport (toolbar + scene), never the spec
  // sheet underneath. Uses the native Fullscreen API when the browser allows
  // it (and then asks phones to lock landscape), with the fixed overlay as
  // the fallback.
  const toggleFullscreen = () => {
    if (!isFullscreen) {
      setRotateDismissed(false);
      sectionRef.current
        ?.requestFullscreen?.()
        .then(() => (screen.orientation as unknown as { lock?: (o: "landscape") => Promise<void> }).lock?.("landscape"))
        .catch(() => {});
    }
    setIsFullscreen((v) => !v);
  };

  useEffect(() => {
    if (!isFullscreen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    const onFullscreenChange = () => {
      if (!document.fullscreenElement) setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("fullscreenchange", onFullscreenChange);
      (screen.orientation as unknown as { unlock?: () => void } | undefined)?.unlock?.();
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    };
  }, [isFullscreen]);

  // Phones explore the twin in landscape fullscreen; inline controls are hidden there.
  const inlineTouchHidden = isFullscreen ? "" : "touch:hidden";

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

  // ==========================================
  // Primary Three.js 3D Architectural Scene
  // Initialized ONCE — seamless mode transitions
  // ==========================================
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let animId = 0;
    let renderer: THREE.WebGLRenderer | null = null;

    try {
      const width = container.clientWidth || 800;
      const height = container.clientHeight || 500;

      const scene = new THREE.Scene();
      const fogColor = 0xd8d3ca;
      scene.background = new THREE.Color(fogColor);
      scene.fog = new THREE.Fog(fogColor, 45, 125);

      const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 350);
      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 0.95;

      while (container.firstChild) container.removeChild(container.firstChild);
      container.appendChild(renderer.domElement);

      // Scene Lights
      scene.add(new THREE.HemisphereLight(0xfff3e0, 0xa9a294, 0.65));
      const sun = new THREE.DirectionalLight(0xffeeD6, 0.95);
      sun.position.set(28, 42, 18);
      sun.castShadow = true;
      sun.shadow.mapSize.set(1024, 1024);
      Object.assign(sun.shadow.camera, { left: -35, right: 35, top: 35, bottom: -35, far: 120 });
      scene.add(sun);

      // Architectural materials matching Namasthetu.html
      const M = {
        ground: new THREE.MeshLambertMaterial({ color: 0xc8c3b8 }),
        road: new THREE.MeshLambertMaterial({ color: 0xe0dcd4 }),
        cream: new THREE.MeshLambertMaterial({ color: 0xf1eee7 }),
        cream2: new THREE.MeshLambertMaterial({ color: 0xe7e3da }),
        slab: new THREE.MeshLambertMaterial({ color: 0xece9e2 }),
        wood: new THREE.MeshLambertMaterial({ color: 0xb9824e }),
        wood2: new THREE.MeshLambertMaterial({ color: 0xa87042 }),
        woodFloor: new THREE.MeshLambertMaterial({ color: 0xc9a275 }),
        glass: new THREE.MeshPhongMaterial({ color: 0x22262c, transparent: true, opacity: 0.45, shininess: 90 }),
        rail: new THREE.MeshPhongMaterial({ color: 0xdfe4e6, transparent: true, opacity: 0.3 }),
        dark: new THREE.MeshLambertMaterial({ color: 0x3a3a40 }),
        sofa: new THREE.MeshLambertMaterial({ color: 0xd9d1c0 }),
        bed: new THREE.MeshLambertMaterial({ color: 0xf4f1ea }),
        accent: new THREE.MeshLambertMaterial({ color: 0xc9a66b }),
        rug: new THREE.MeshLambertMaterial({ color: 0xcabfa8 }),
        counter: new THREE.MeshLambertMaterial({ color: 0x8d6f50 }),
        white: new THREE.MeshLambertMaterial({ color: 0xfafaf6 }),
        leaf: new THREE.MeshLambertMaterial({ color: 0x93a07a }),
        trunk: new THREE.MeshLambertMaterial({ color: 0x8a7a62 }),
        grey1: new THREE.MeshLambertMaterial({ color: 0xddd9d0 }),
        grey2: new THREE.MeshLambertMaterial({ color: 0xd0cbc1 }),
        grey3: new THREE.MeshLambertMaterial({ color: 0xc6c1b8 }),
        lit: new THREE.MeshBasicMaterial({ color: 0xffd9a0 }),
      };

      const stagedGroup = new THREE.Group();
      scene.add(stagedGroup);

      const roofGroup = new THREE.Group();
      scene.add(roofGroup);

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

      // Ground plane, roads & plazas
      const g = new THREE.Mesh(new THREE.PlaneGeometry(240, 240), M.ground);
      g.rotation.x = -Math.PI / 2;
      g.receiveShadow = true;
      scene.add(g);

      const r1 = new THREE.Mesh(new THREE.PlaneGeometry(16, 240), M.road);
      r1.rotation.x = -Math.PI / 2;
      r1.position.set(0, 0.02, 0);
      r1.rotation.z = Math.PI / 2;
      r1.receiveShadow = true;
      scene.add(r1);

      const r2 = new THREE.Mesh(new THREE.PlaneGeometry(12, 240), M.road);
      r2.rotation.x = -Math.PI / 2;
      r2.position.set(28, 0.03, 0);
      r2.receiveShadow = true;
      scene.add(r2);

      // Building podium & main structure
      box(24, 0.4, 20, M.slab, 0, 0.2, 0);
      const H1 = 3.4;
      const F2 = H1 + 0.3;
      const H2 = 3.2;

      // Ground floor slabs & walls
      box(15, 0.3, 11, M.slab, -0.5, 0.55, -0.5);
      box(0.28, H1, 11, M.cream, -8.0, 0.7 + H1 / 2, -0.5);
      box(15, H1, 0.28, M.cream, -0.5, 0.7 + H1 / 2, -6.0);
      box(0.28, H1, 7.5, M.cream2, 7.0, 0.7 + H1 / 2, -2.25);
      box(4.5, H1, 0.28, M.cream, -5.75, 0.7 + H1 / 2, 5.0);

      // Glass front living area
      const gf1 = new THREE.Mesh(new THREE.PlaneGeometry(10.5, H1 - 0.2), M.glass);
      gf1.position.set(1.75, 0.7 + (H1 - 0.2) / 2, 5.0);
      scene.add(gf1);

      // Staged Interior: Living & Dining
      box(4.2, 0.75, 1.8, M.sofa, -1.2, 0.7 + 0.38, 2.8, 0, stagedGroup);
      box(2.2, 0.45, 1.2, M.wood, -1.2, 0.7 + 0.22, 1.2, 0, stagedGroup);
      box(5.5, 0.02, 3.8, M.rug, -1.2, 0.72, 2.0, 0, stagedGroup);
      box(3.2, 0.5, 0.6, M.dark, -1.2, 0.7 + 0.25, -5.6, 0, stagedGroup);
      const pl1 = new THREE.PointLight(0xffd9a0, 0.9, 12);
      pl1.position.set(-1.2, 3.2, 1.8);
      scene.add(pl1);

      // Staged Interior: Modular Kitchen Island
      box(3.2, 0.95, 1.4, M.counter, 4.4, 0.7 + 0.48, -0.8, 0, stagedGroup);
      box(0.45, 0.75, 0.45, M.wood2, 4.4, 0.7 + 0.38, -2.0, 0, stagedGroup);
      box(0.45, 0.75, 0.45, M.wood2, 3.4, 0.7 + 0.38, -2.0, 0, stagedGroup);

      // Second floor slab & walls
      box(16, 0.3, 10, M.slab, 0, F2 + 0.15, -0.5);
      const wy2 = F2 + 0.3 + H2 / 2;
      box(0.28, H2, 10, M.cream, -8.0, wy2, -0.5);
      box(16, H2, 0.28, M.cream, 0, wy2, -5.5);
      box(0.28, H2, 8.5, M.cream2, 8.0, wy2, -1.25);
      box(5.5, H2, 0.28, M.cream, -5.25, wy2, 4.5);

      // Second floor glass
      const gf2 = new THREE.Mesh(new THREE.PlaneGeometry(10.5, H2 - 0.2), M.glass);
      gf2.position.set(2.75, wy2, 4.5);
      scene.add(gf2);

      // Wood slat accent wall
      for (let k = 0; k < 14; k++) {
        box(0.08, H2 - 0.1, 0.15, k % 2 ? M.wood2 : M.wood, -7.8, wy2, -4.5 + k * 0.65, 0);
      }

      // Staged Interior: Master Bedroom Suite
      box(2.2, 0.35, 2.0, M.white, -3.2, F2 + 0.48, -1.8, 0, stagedGroup);
      box(2.0, 0.24, 1.8, M.bed, -3.2, F2 + 0.72, -1.8, 0, stagedGroup);
      box(0.55, 0.15, 0.35, M.accent, -3.7, F2 + 0.88, -2.5, 0, stagedGroup);
      box(0.55, 0.15, 0.35, M.accent, -2.7, F2 + 0.88, -2.5, 0, stagedGroup);
      box(2.2, 0.95, 0.12, M.wood, -3.2, F2 + 0.95, -2.75, 0, stagedGroup);
      box(1.8, 2.0, 0.6, M.wood2, 2.2, F2 + 1.3, -4.2, 0, stagedGroup);
      const pl2 = new THREE.PointLight(0xffd9a0, 0.85, 11);
      pl2.position.set(-2, F2 + 2.5, -1);
      scene.add(pl2);

      // Balcony deck with glass railing
      box(5.6, 0.08, 4.2, M.woodFloor, 5.2, F2 + 0.34, 1.5);
      const railG = new THREE.Mesh(new THREE.PlaneGeometry(5.6, 0.9), M.rail);
      railG.position.set(5.2, F2 + 0.8, 3.6);
      scene.add(railG);
      const railR = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 0.9), M.rail);
      railR.rotation.y = -Math.PI / 2;
      railR.position.set(8.0, F2 + 0.8, 1.5);
      scene.add(railR);
      box(1.8, 0.35, 0.8, M.sofa, 5.2, F2 + 0.52, 1.0, 0, stagedGroup);

      // Roof slab & parapet (grouped for top-down floor plan cutaway)
      box(16.5, 0.28, 10.5, M.slab, 0, F2 + 0.3 + H2 + 0.14, -0.5, 0, roofGroup);
      box(16.5, 0.45, 0.2, M.cream, 0, F2 + 0.3 + H2 + 0.5, 4.75, 0, roofGroup);

      // Neighborhood context: Surrounding buildings
      const nb: Array<{ x: number; z: number; w: number; d: number; h: number; mat: THREE.Material }> = [
        { x: -32, z: -22, w: 11, d: 12, h: 9, mat: M.grey1 },
        { x: -36, z: 6, w: 9, d: 8, h: 7, mat: M.grey2 },
        { x: -29, z: 26, w: 12, d: 16, h: 11, mat: M.grey3 },
        { x: 30, z: -24, w: 12, d: 14, h: 10, mat: M.grey2 },
        { x: 38, z: 4, w: 10, d: 8, h: 12, mat: M.grey1 },
        { x: 32, z: 28, w: 14, d: 11, h: 8, mat: M.grey3 },
        { x: -4, z: -34, w: 16, d: 10, h: 9, mat: M.grey1 },
        { x: 6, z: 36, w: 14, d: 12, h: 10, mat: M.grey2 },
      ];
      nb.forEach((n) => {
        box(n.w, n.h, n.d, n.mat, n.x, n.h / 2, n.z);
        const w = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 1.4), Math.random() < 0.5 ? M.lit : M.dark);
        w.position.set(n.x, n.h * 0.55, n.z + n.d / 2 + 0.02);
        scene.add(w);
      });

      // Trees
      for (let t = 0; t < 18; t++) {
        const a = (t / 18) * Math.PI * 2 + 0.2;
        const r = 16 + (t % 5) * 6;
        const x = Math.cos(a) * r;
        const z = Math.sin(a) * r;
        if (Math.abs(x) < 12 && Math.abs(z) < 10) continue;
        const th = 1.0 + (t % 3) * 0.4;
        const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.14, th, 6), M.trunk);
        tr.position.set(x, th / 2, z);
        tr.castShadow = true;
        scene.add(tr);
        const cr = new THREE.Mesh(new THREE.SphereGeometry(0.8 + (t % 3) * 0.3, 10, 8), M.leaf);
        cr.position.set(x, th + 0.6, z);
        cr.castShadow = true;
        scene.add(cr);
      }

      // Camera State & Orbit Controls
      const cvState = {
        theta: 0.72,
        phi: 1.05,
        radius: 34,
        thetaT: 0.72,
        phiT: 1.05,
        radiusT: 34,
        target: new THREE.Vector3(0, 3.2, 0),
        targetT: new THREE.Vector3(0, 3.2, 0),
        lastInteraction: performance.now(),
        walk: { pos: new THREE.Vector3(0, 1.65, 11), yaw: 0, pitch: 0 },
        tour: { index: 0, time: 0 },
        keys: {} as Record<string, boolean>,
      };

      // Connect camera controller functions
      cameraControlRef.current = {
        focusRoom: (roomId: string) => {
          const focal = ROOM_FOCAL_TARGETS[roomId] || ROOM_FOCAL_TARGETS.all;
          cvState.targetT.set(focal.target[0], focal.target[1], focal.target[2]);
          cvState.thetaT = focal.theta;
          cvState.phiT = focal.phi;
          cvState.radiusT = focal.radius;
          cvState.walk.pos.set(focal.walk[0], focal.walk[1], focal.walk[2]);
          cvState.lastInteraction = performance.now();
        },
        setTopDown: (topDown: boolean) => {
          if (topDown) {
            cvState.targetT.set(0, 3.0, 0);
            cvState.phiT = 0.08;
            cvState.radiusT = 44;
          } else {
            cvState.targetT.set(0, 3.2, 0);
            cvState.phiT = 1.05;
            cvState.radiusT = 34;
          }
          cvState.lastInteraction = performance.now();
        },
      };

      const WAYPOINTS = [
        { p: [3.5, 2.2, 14.0], l: [0, 2.5, 0], label: "Approach · Facade" },
        { p: [-1.2, 1.65, 3.4], l: [3.0, 1.2, 1.5], label: "Living Room · 285 sqft" },
        { p: [3.8, 1.65, -0.4], l: [-2.0, 1.1, -1.5], label: "Kitchen · Modular Island" },
        { p: [-1.5, 4.95, 1.8], l: [-3.2, 4.3, -1.8], label: "Master Bedroom · En-suite" },
        { p: [4.8, 4.95, 0.2], l: [7.2, 4.6, 3.6], label: "Balcony · Sunset Deck" },
        { p: [18, 14, 18], l: [0, 3.0, 0], label: "Aerial · Full Digital Twin" },
      ];

      const tmpA = new THREE.Vector3();
      const tmpB = new THREE.Vector3();
      const tmpL = new THREE.Vector3();
      const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

      // Event listeners for Orbit & Walk
      let isDragging = false;
      let px = 0;
      let py = 0;
      let pinchDist = 0;
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
        cvState.radiusT = Math.min(65, Math.max(8, cvState.radiusT + e.deltaY * 0.02));
        cvState.lastInteraction = performance.now();
      };

      const onTouchStart = (e: TouchEvent) => {
        if (e.touches.length === 2) {
          pinchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        }
      };

      const onTouchMove = (e: TouchEvent) => {
        if (e.touches.length === 2 && pinchDist) {
          const d2 = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
          cvState.radiusT = Math.min(65, Math.max(8, cvState.radiusT - (d2 - pinchDist) * 0.05));
          pinchDist = d2;
        }
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
      dom.addEventListener("touchstart", onTouchStart, { passive: true });
      dom.addEventListener("touchmove", onTouchMove, { passive: true });
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);

      // Continuous Render Loop
      let lastTime = performance.now();

      const animate = (now: number) => {
        animId = requestAnimationFrame(animate);

        const currentMode = modeRef.current;
        // Skip rendering if switched to 2D floor plan or 360 panorama
        if (currentMode === "plan" || currentMode === "pano") return;

        const dt = Math.min(0.05, (now - lastTime) / 1000);
        lastTime = now;

        // Sync staging & topdown roof visibility
        stagedGroup.visible = stagedRef.current;
        roofGroup.visible = !topDownRef.current;

        if (currentMode === "orbit") {
          // Subtle idle rotation when untouched
          if (autoRotateRef.current || (now - cvState.lastInteraction > 3500 && !topDownRef.current)) {
            cvState.thetaT += 0.0008;
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
            cvState.walk.pos.z += fz * sp;
          }
          if (k["a"] || k["arrowleft"]) {
            cvState.walk.pos.x += fz * sp;
            cvState.walk.pos.z -= fx * sp;
          }
          if (k["d"] || k["arrowright"]) {
            cvState.walk.pos.x -= fz * sp;
            cvState.walk.pos.z += fx * sp;
          }
          cvState.walk.pos.x = Math.max(-14, Math.min(14, cvState.walk.pos.x));
          cvState.walk.pos.z = Math.max(-12, Math.min(14, cvState.walk.pos.z));
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
            cvState.tour.index = (cvState.tour.index + 1) % WAYPOINTS.length;
          }
          const currWp = WAYPOINTS[cvState.tour.index];
          const nextWp = WAYPOINTS[(cvState.tour.index + 1) % WAYPOINTS.length];
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

      // First frame is on screen — drop the loader.
      requestAnimationFrame(() => setIsSceneReady(true));

      return () => {
        cancelAnimationFrame(animId);
        resizeObserver.disconnect();
        dom.removeEventListener("pointerdown", onPointerDown);
        dom.removeEventListener("pointermove", onPointerMove);
        dom.removeEventListener("pointerup", onPointerUp);
        dom.removeEventListener("wheel", onWheel);
        dom.removeEventListener("touchstart", onTouchStart);
        dom.removeEventListener("touchmove", onTouchMove);
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("keyup", onKeyUp);
        renderer?.dispose();
      };
    } catch (e) {
      console.error("ThreeTwinViewer initialization error:", e);
      setSceneFailed(true);
    }
  }, []);

  // ==========================================
  // Three.js 360° Photosphere Panorama Scene
  // Loaded when activeMode === "pano"
  // ==========================================
  useEffect(() => {
    const container = panoContainerRef.current;
    if (!container || activeMode !== "pano") return;

    let animId = 0;
    let renderer: THREE.WebGLRenderer | null = null;

    try {
      const width = container.clientWidth || 800;
      const height = container.clientHeight || 500;

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(72, width / height, 0.1, 1000);
      camera.position.set(0, 0, 0.1);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

      while (container.firstChild) container.removeChild(container.firstChild);
      container.appendChild(renderer.domElement);

      const sphereGeo = new THREE.SphereGeometry(500, 60, 40);
      sphereGeo.scale(-1, 1, 1);

      setIsPanoLoading(true);
      const loader = new THREE.TextureLoader();
      const currentPano = PANO_ROOMS[activePanoIndex] || PANO_ROOMS[0];
      const texture = loader.load(
        currentPano.image,
        () => setIsPanoLoading(false),
        undefined,
        () => setIsPanoLoading(false),
      );
      const sphereMat = new THREE.MeshBasicMaterial({ map: texture });
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      scene.add(sphere);

      let lon = 0;
      let lat = 0;
      let isDraggingPano = false;
      let px = 0;
      let py = 0;

      const dom = renderer.domElement;
      dom.style.cursor = "grab";

      const onDown = (e: PointerEvent) => {
        isDraggingPano = true;
        px = e.clientX;
        py = e.clientY;
        dom.style.cursor = "grabbing";
        dom.setPointerCapture(e.pointerId);
      };

      const onMove = (e: PointerEvent) => {
        if (!isDraggingPano) return;
        lon -= (e.clientX - px) * 0.14;
        lat += (e.clientY - py) * 0.14;
        lat = Math.max(-85, Math.min(85, lat));
        px = e.clientX;
        py = e.clientY;
      };

      const onUp = () => {
        isDraggingPano = false;
        dom.style.cursor = "grab";
      };

      dom.addEventListener("pointerdown", onDown);
      dom.addEventListener("pointermove", onMove);
      dom.addEventListener("pointerup", onUp);

      const animatePano = () => {
        animId = requestAnimationFrame(animatePano);
        if (!isDraggingPano) lon += 0.04;
        const phi = THREE.MathUtils.degToRad(90 - lat);
        const theta = THREE.MathUtils.degToRad(lon);
        const target = new THREE.Vector3(
          500 * Math.sin(phi) * Math.cos(theta),
          500 * Math.cos(phi),
          500 * Math.sin(phi) * Math.sin(theta)
        );
        camera.lookAt(target);
        renderer?.render(scene, camera);
      };
      animatePano();

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

      return () => {
        cancelAnimationFrame(animId);
        resizeObserver.disconnect();
        dom.removeEventListener("pointerdown", onDown);
        dom.removeEventListener("pointermove", onMove);
        dom.removeEventListener("pointerup", onUp);
        sphereGeo.dispose();
        sphereMat.dispose();
        texture.dispose();
        renderer?.dispose();
      };
    } catch (e) {
      console.error("Panorama rendering error:", e);
    }
  }, [activeMode, activePanoIndex]);

  return (
    <section
      ref={sectionRef}
      aria-labelledby="tour-heading"
      className={`bg-cream overflow-hidden transition-all ${
        isFullscreen ? "fixed inset-0 z-[100] flex flex-col" : "relative rounded-3xl border border-hairline shadow-sm"
      }`}
    >
      {/* Topbar / Header with Amberstone PRO Badge */}
      <div className="flex flex-col gap-4 border-b border-bone px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-7 short:flex-row short:items-center short:gap-3 short:px-3 short:py-2">
        <div className="flex shrink-0 items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink text-white shadow-sm short:hidden">
            <Layers className="h-5 w-5 text-gold-light" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 id="tour-heading" className="text-xl font-bold tracking-tight text-ink font-serif short:text-base">
                3D Digital Twin
              </h2>
              <span className="rounded-full bg-gold px-2 py-0.5 text-[10px] font-bold tracking-wider text-white uppercase">
                PRO
              </span>
            </div>
            <p className="text-xs text-smoke mt-0.5 short:hidden">
              {propertyTitle} · Cadastral &amp; Spatial Twin
            </p>
          </div>
        </div>

        {/* Toolbar Controls */}
        <div
          className={`no-scrollbar flex flex-wrap items-center gap-1.5 sm:gap-2 short:min-w-0 short:flex-nowrap short:gap-1.5 short:overflow-x-auto ${inlineTouchHidden}`}
          role="toolbar"
          aria-label="3D Twin modes"
        >
          <ToolbarButton
            active={activeMode === "orbit"}
            onClick={() => setActiveMode("orbit")}
            icon={<Navigation className="h-4 w-4" />}
            label="Orbit View"
          />
          <ToolbarButton
            active={activeMode === "walk"}
            onClick={() => setActiveMode("walk")}
            icon={<Footprints className="h-4 w-4" />}
            label="WASD Walk"
          />
          <ToolbarButton
            active={activeMode === "tour"}
            onClick={() => setActiveMode("tour")}
            icon={<Play className="h-4 w-4" />}
            label="Automated Tour"
          />
          <ToolbarButton
            active={activeMode === "plan"}
            onClick={() => setActiveMode("plan")}
            icon={<Grid className="h-4 w-4" />}
            label="2D CAD Plan"
          />
          <ToolbarButton
            active={activeMode === "pano"}
            onClick={() => setActiveMode("pano")}
            icon={<Compass className="h-4 w-4" />}
            label="360° Panorama"
          />
          <div className="h-5 w-px bg-bone mx-1 hidden sm:block" />
          <ToolbarButton
            active={isTopDown}
            onClick={toggleTopDownCutaway}
            icon={<Layers className="h-4 w-4" />}
            label="Cutaway Plan"
          />
          <ToolbarButton
            active={showMeasurements}
            onClick={() => setShowMeasurements((v) => !v)}
            icon={<Ruler className="h-4 w-4" />}
            label="Measure"
          />
          <ToolbarButton
            active={isStaged}
            onClick={() => setIsStaged((v) => !v)}
            icon={<Sparkles className="h-4 w-4" />}
            label="Virtual Staging"
          />
          <ToolbarButton
            active={isRotating}
            onClick={() => setIsRotating((v) => !v)}
            icon={<RotateCw className="h-4 w-4" />}
            label="Auto-rotate"
          />
          <ToolbarButton
            active={isFullscreen}
            onClick={toggleFullscreen}
            icon={isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            label={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          />
        </div>
      </div>

      {/* Phones in portrait: ask for landscape (orientation lock isn't available everywhere, e.g. iOS). */}
      {isFullscreen && !rotateDismissed && (
        <div className="absolute inset-0 z-[60] hidden flex-col items-center justify-center gap-4 bg-charcoal/95 px-8 text-center text-white phone-portrait:flex">
          <Smartphone className="h-10 w-10 rotate-90 text-gold-light" aria-hidden="true" />
          <p className="font-serif text-xl font-bold">Rotate your phone</p>
          <p className="text-sm text-white/70">The 3D twin is best explored in landscape.</p>
          <button
            type="button"
            onClick={() => setRotateDismissed(true)}
            className="mt-2 rounded-full border border-white/25 px-4 py-2 text-xs font-semibold text-white/85 cursor-pointer"
          >
            Continue in portrait
          </button>
        </div>
      )}

      {/* Main Viewport Container */}
      <div
        className={`relative w-full overflow-hidden bg-[#d8d3ca] ${
          isFullscreen ? "min-h-0 flex-1" : "h-[440px] sm:h-[540px]"
        }`}
      >
        {/* 1. Three.js 3D Viewport (kept mounted to avoid context disposal thrashing) */}
        <div
          ref={containerRef}
          style={{ display: activeMode !== "plan" && activeMode !== "pano" ? "block" : "none" }}
          className="h-full w-full cursor-grab active:cursor-grabbing"
          aria-label={`3D model of ${propertyTitle}`}
          role="img"
        />

        {!isSceneReady && activeMode !== "plan" && activeMode !== "pano" && (
          sceneFailed ? (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-stone px-6 text-center text-sm text-smoke">
              The interactive 3D view isn&apos;t available on this device. Try the 2D CAD Plan or 360° Panorama.
            </div>
          ) : (
            <BrandLoader label="Preparing digital twin" />
          )
        )}

        {/* Phones: launch the twin in landscape fullscreen instead of fiddling inline. */}
        {!isFullscreen && (
          <div className="absolute inset-0 z-30 hidden flex-col items-center justify-center gap-2 bg-charcoal/35 touch:flex">
            <button
              type="button"
              onClick={toggleFullscreen}
              className="flex min-h-11 items-center gap-2 rounded-full bg-white px-5 text-sm font-semibold text-ink shadow-lg cursor-pointer"
            >
              <Maximize2 className="h-4 w-4 text-gold" />
              View in 3D
            </button>
            <p className="text-[11px] font-medium text-white/85">Opens full screen · best in landscape</p>
          </div>
        )}

        {/* 2. 2D Architectural CAD Floor Plan */}
        {activeMode === "plan" && (
          <div className="flex h-full w-full items-center justify-center p-6 bg-cream-2 select-none overflow-hidden animate-fade-in short:items-start short:overflow-y-auto short:p-3 short:pb-16">
            <div className="relative w-full max-w-2xl rounded-2xl border-2 border-dashed border-bone bg-cream p-6 shadow-inner short:max-w-sm short:p-3">
              <div className="flex items-center justify-between border-b border-bone pb-3 mb-4 short:hidden">
                <div>
                  <p className="text-xs uppercase tracking-widest text-mist font-semibold">Architectural CAD Blueprint</p>
                  <p className="text-lg font-bold text-ink font-serif">{propertyTitle}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="pill-verified">{carpetSqft} sq ft carpet</span>
                  <div className="h-7 w-7 rounded-full bg-ink text-white flex items-center justify-center text-xs font-bold">
                    N
                  </div>
                </div>
              </div>

              {/* Floor Plan Vector SVG */}
              <svg viewBox="0 0 400 230" className="w-full h-auto drop-shadow-sm">
                <rect x="20" y="20" width="360" height="190" fill="#FAF7F0" stroke="#1A1A1F" strokeWidth="2.5" />
                {/* Partition Walls */}
                <line x1="180" y1="20" x2="180" y2="125" stroke="#1A1A1F" strokeWidth="2" />
                <line x1="20" y1="125" x2="180" y2="125" stroke="#1A1A1F" strokeWidth="2" />
                <line x1="180" y1="85" x2="380" y2="85" stroke="#1A1A1F" strokeWidth="2" />
                <line x1="280" y1="85" x2="280" y2="210" stroke="#1A1A1F" strokeWidth="2" />

                {/* Living Area */}
                <rect
                  x="22"
                  y="22"
                  width="156"
                  height="101"
                  fill={activeRoomIndex === 0 ? "rgba(168, 135, 90, 0.22)" : "transparent"}
                  className="transition-colors cursor-pointer"
                  onClick={() => handleSelectRoom(0)}
                />
                <text x="100" y="68" fontSize="11" fontWeight="600" fill="#1A1A1F" textAnchor="middle">
                  Formal Living &amp; Dining
                </text>
                <text x="100" y="84" fontSize="9" fill="#78716C" textAnchor="middle">
                  285 sq ft · 22&apos; × 16&apos;
                </text>

                {/* Kitchen Area */}
                <rect
                  x="22"
                  y="127"
                  width="156"
                  height="81"
                  fill={activeRoomIndex === 1 ? "rgba(168, 135, 90, 0.22)" : "transparent"}
                  className="transition-colors cursor-pointer"
                  onClick={() => handleSelectRoom(1)}
                />
                <text x="100" y="165" fontSize="11" fontWeight="600" fill="#1A1A1F" textAnchor="middle">
                  Modular Kitchen
                </text>
                <text x="100" y="181" fontSize="9" fill="#78716C" textAnchor="middle">
                  154 sq ft · Quartz Island
                </text>

                {/* Master Bedroom */}
                <rect
                  x="182"
                  y="22"
                  width="196"
                  height="61"
                  fill={activeRoomIndex === 2 ? "rgba(168, 135, 90, 0.22)" : "transparent"}
                  className="transition-colors cursor-pointer"
                  onClick={() => handleSelectRoom(2)}
                />
                <text x="280" y="52" fontSize="11" fontWeight="600" fill="#1A1A1F" textAnchor="middle">
                  Master Bedroom Suite
                </text>
                <text x="280" y="68" fontSize="9" fill="#78716C" textAnchor="middle">
                  252 sq ft · En-suite
                </text>

                {/* Bathroom */}
                <rect
                  x="182"
                  y="87"
                  width="96"
                  height="121"
                  fill={activeRoomIndex === 3 ? "rgba(168, 135, 90, 0.22)" : "transparent"}
                  className="transition-colors cursor-pointer"
                  onClick={() => handleSelectRoom(3)}
                />
                <text x="230" y="150" fontSize="10" fontWeight="600" fill="#1A1A1F" textAnchor="middle">
                  Bath
                </text>
                <text x="230" y="164" fontSize="8" fill="#78716C" textAnchor="middle">
                  80 sq ft
                </text>

                {/* Balcony */}
                <rect
                  x="282"
                  y="87"
                  width="96"
                  height="121"
                  fill={activeRoomIndex === 4 ? "rgba(168, 135, 90, 0.22)" : "transparent"}
                  className="transition-colors cursor-pointer"
                  onClick={() => handleSelectRoom(4)}
                />
                <text x="330" y="150" fontSize="10" fontWeight="600" fill="#1A1A1F" textAnchor="middle">
                  Balcony Deck
                </text>
                <text x="330" y="164" fontSize="8" fill="#78716C" textAnchor="middle">
                  112 sq ft
                </text>

                {/* Door swings */}
                <path d="M 20 60 A 25 25 0 0 1 45 85" fill="none" stroke="#A8A29E" strokeWidth="1" strokeDasharray="2,2" />
                <path d="M 180 50 A 25 25 0 0 1 205 75" fill="none" stroke="#A8A29E" strokeWidth="1" strokeDasharray="2,2" />
              </svg>

              <div className="mt-4 flex items-center justify-between text-xs text-smoke pt-2 border-t border-bone short:hidden">
                <span>RERA Carpet Area: {carpetSqft} sqft (Efficiency: {efficiency}%)</span>
                <span>Floor Height: {floorHeight} · Orientation: {orientation}</span>
              </div>
            </div>
          </div>
        )}

        {/* 3. Three.js 360° Panorama Viewport */}
        {activeMode === "pano" && (
          <div className="relative h-full w-full animate-fade-in">
            <div ref={panoContainerRef} className="h-full w-full" />
            {isPanoLoading && <BrandLoader label="Loading 360° photosphere" />}
            <div className="absolute top-4 left-4 z-10 rounded-xl bg-ink/80 px-3.5 py-2 text-white backdrop-blur">
              <p className="text-[10px] uppercase tracking-wider text-gold-light font-semibold">
                360° Photosphere
              </p>
              <p className="text-sm font-medium">{PANO_ROOMS[activePanoIndex]?.name || "Room"} View</p>
            </div>
            {/* 360 Thumbnail Navigation Strip */}
            <div className="absolute bottom-4 inset-x-0 z-10 flex justify-center gap-2 px-4 overflow-x-auto">
              {PANO_ROOMS.map((p, idx) => (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => {
                    setActivePanoIndex(idx);
                    setActiveRoomIndex(idx);
                  }}
                  className={`flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold backdrop-blur transition-all cursor-pointer ${
                    idx === activePanoIndex
                      ? "bg-gold text-white shadow-lg scale-105"
                      : "bg-ink/75 text-white hover:bg-ink"
                  }`}
                >
                  <img src={p.thumb} alt={p.name} className="h-5 w-8 object-cover rounded" />
                  <span>{p.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* HUD: Active Room Details Callout */}
        {activeMode !== "plan" && activeRoomIndex >= 0 && (
          <div className="absolute left-4 top-4 z-10 max-w-[230px] sm:max-w-xs rounded-2xl bg-white/95 p-3.5 sm:p-4 backdrop-blur shadow-md border border-white/60 animate-fade-in short:left-3 short:top-3 short:max-w-[220px] short:p-2.5">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gold">
                {activeMode === "tour" ? "Tour Waypoint" : "Spatial Room"}
              </span>
              <span className="rounded-full bg-forest/10 px-2 py-0.5 text-[10px] font-bold text-forest">
                {activeRoom.carpetSqft} sq ft
              </span>
            </div>
            <p className="mt-1 text-base font-bold text-ink font-serif">
              {activeMode === "tour" ? currentTourLabel : activeRoom.name}
            </p>
            <p className="text-xs text-smoke mt-0.5 short:hidden">
              {activeRoom.dimensions} · {activeRoom.floorType}
            </p>
            <p className="mt-2 border-t border-bone pt-2 text-[11px] text-muted line-clamp-2 short:hidden">
              {activeRoom.highlight}
            </p>
          </div>
        )}

        {/* HUD: Condition Score Badge */}
        <div className="absolute right-4 top-4 z-10 flex items-center gap-3 rounded-2xl bg-ink/90 px-3 py-2.5 text-white backdrop-blur shadow-md sm:px-4 short:right-3 short:top-3 short:py-1.5">
          <div className="text-right">
            <span className="block font-serif text-2xl font-bold leading-none text-gold-light short:text-xl">
              {conditionScore}
            </span>
            <span className="text-[9px] uppercase tracking-wider text-mist">/ 10 Score</span>
          </div>
          {/* Narrow and short screens: number only, so the badge never covers the room card. */}
          <div className="hidden border-l border-white/20 pl-3 sm:block short:hidden">
            <div className="flex items-center gap-1 text-[11px] font-semibold text-white">
              <ShieldCheck className="h-3.5 w-3.5 text-gold-light" />
              Verified Condition
            </div>
            <span className="text-[10px] text-mist">Zero Dampness</span>
          </div>
        </div>

        {/* HUD: Interactive Measurement Callout */}
        {showMeasurements && activeMode !== "plan" && (
          <div className={`absolute left-4 bottom-20 z-10 flex items-center gap-2 rounded-xl ${inlineTouchHidden} bg-charcoal/85 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur shadow-md animate-fade-in`}>
            <Ruler className="h-3.5 w-3.5 text-gold-light" />
            <span>↔ 5.4m × ↕ 4.2m · 22.7 m² · Clear height {floorHeight}</span>
          </div>
        )}

        {/* HUD: Virtual Staging Status Badge */}
        {activeMode !== "plan" && (
          <div className={`absolute left-4 bottom-28 z-10 flex items-center gap-1.5 rounded-full bg-ink/80 px-3 py-1 text-[11px] font-medium text-white backdrop-blur shadow-sm ${inlineTouchHidden}`}>
            <Sparkles className={`h-3 w-3 ${isStaged ? "text-gold-light" : "text-mist"}`} />
            <span>{isStaged ? "Furnished Designer Staging" : "Raw Structural Shell"}</span>
          </div>
        )}

        {/* HUD: Walk Mode Keyboard Navigation Hint */}
        {activeMode === "walk" && (
          <div className="absolute right-4 bottom-20 z-10 rounded-xl bg-ink/85 px-3 py-1.5 text-xs font-mono text-white backdrop-blur border border-white/10">
            WASD / Arrows to Walk · Drag to Look
          </div>
        )}

        {/* HUD: Room Switcher Bottom Carousel */}
        {activeMode !== "pano" && (
          <div className={`no-scrollbar absolute bottom-3 inset-x-0 z-10 ${inlineTouchHidden} flex justify-center items-center gap-1.5 px-4 overflow-x-auto`}>
            <button
              type="button"
              onClick={handleSelectWholeProperty}
              className={`flex shrink-0 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium backdrop-blur transition-all cursor-pointer ${
                activeRoomIndex === -1
                  ? "bg-gold text-white shadow-md scale-105 font-bold"
                  : "bg-white/85 text-ink hover:bg-white"
              }`}
            >
              <span>Full Twin</span>
            </button>
            {rooms.map((room, idx) => (
              <button
                key={room.id}
                type="button"
                onClick={() => handleSelectRoom(idx)}
                className={`flex shrink-0 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium backdrop-blur transition-all cursor-pointer ${
                  idx === activeRoomIndex
                    ? "bg-ink text-white shadow-md scale-105 font-semibold"
                    : "bg-white/85 text-ink hover:bg-white"
                }`}
              >
                <span>{room.name}</span>
                <span className="opacity-60 text-[10px]">{room.carpetSqft} sqft</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Architectural Specifications & Fixtures Breakdown (hidden in fullscreen) */}
      {!isFullscreen && (
      <div className="grid grid-cols-1 divide-y divide-bone border-t border-bone bg-cream lg:grid-cols-2 lg:divide-x lg:divide-y-0">
        {/* Left: Fixtures & Inclusions Checklist */}
        <div className="p-5 sm:p-7">
          <p className="eyebrow">Assurance Audit</p>
          <h3 className="mt-1 text-base font-bold text-ink font-serif">
            Fixtures &amp; Handover Inclusions
          </h3>
          <p className="mt-0.5 text-xs text-smoke">
            Physically cataloged by on-site civil engineer during spatial audit.
          </p>

          <div className="mt-4 space-y-2.5">
            {FIXTURES.map((fix) => (
              <div
                key={fix.item}
                className="flex items-center justify-between rounded-xl border border-bone bg-white/70 px-3.5 py-2.5 text-xs"
              >
                <div className="pr-3">
                  <p className="font-semibold text-ink">{fix.item}</p>
                  <p className="text-[11px] text-smoke">{fix.detail}</p>
                </div>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold shrink-0 ${
                    fix.included
                      ? "bg-forest/10 text-forest"
                      : "bg-neutral-200 text-neutral-600"
                  }`}
                >
                  {fix.included ? (
                    <>
                      <CheckCircle2 className="h-3 w-3" /> Included
                    </>
                  ) : (
                    <>
                      <XCircle className="h-3 w-3" /> Excluded
                    </>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Technical Cadastral & Dimensional Grid */}
        <div className="p-5 sm:p-7 flex flex-col justify-between">
          <div>
            <p className="eyebrow">Spatial Specs</p>
            <h3 className="mt-1 text-base font-bold text-ink font-serif">
              Engineering Dimensions
            </h3>
            <p className="mt-0.5 text-xs text-smoke">
              Cross-checked against approved municipal sanction plan &amp; RERA.
            </p>

            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <SpecBox label="Carpet Area" value={`${carpetSqft} sqft`} sub="100% RERA compliant" />
              <SpecBox label="Super Built-up" value={`${builtUpSqft} sqft`} sub="Total slab footprint" />
              <SpecBox label="Efficiency" value={`${efficiency}%`} sub="Usable carpet ratio" />
              <SpecBox label="Clear Height" value={floorHeight} sub="Floor to finished ceiling" />
              <SpecBox label="Orientation" value={orientation} sub="Vastu / solar exposure" />
              <SpecBox label="Cadastral ID" value="Verified" sub="ULPIN land parcel linked" />
            </div>
          </div>

          <div className="mt-6 rounded-2xl bg-white/90 p-4 border border-bone">
            <div className="flex items-center gap-2 text-xs font-bold text-ink">
              <ShieldCheck className="h-4 w-4 text-forest" />
              Amberstone 3D Digital Twin Certification
            </div>
            <p className="mt-1 text-[11px] text-smoke leading-relaxed">
              Spatial scans and structural models are encrypted and immutable. All dimensions are guaranteed within a ±0.5% margin of physical laser telemetry.
            </p>
          </div>
        </div>
      </div>
      )}
    </section>
  );
};

const ToolbarButton: React.FC<{
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}> = ({ active, onClick, icon, label }) => (
  <button
    type="button"
    onClick={onClick}
    aria-pressed={active}
    title={label}
    className={`flex min-h-9 min-w-9 shrink-0 items-center justify-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs font-semibold transition-all cursor-pointer sm:min-h-0 sm:px-3 short:min-h-9 short:px-2.5 ${
      active
        ? "bg-ink text-white shadow-sm"
        : "bg-white/80 text-graphite border border-bone hover:bg-white hover:text-ink"
    }`}
  >
    {icon}
    <span className="hidden sm:inline short:hidden">{label}</span>
  </button>
);

const SpecBox: React.FC<{ label: string; value: string; sub: string }> = ({ label, value, sub }) => (
  <div className="rounded-xl border border-bone bg-white/70 p-3">
    <p className="text-[10px] uppercase tracking-wider text-mist font-semibold">{label}</p>
    <p className="mt-1 font-serif text-lg font-bold text-ink leading-none">{value}</p>
    <p className="mt-1 text-[10px] text-smoke truncate">{sub}</p>
  </div>
);
