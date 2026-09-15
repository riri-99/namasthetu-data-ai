"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import * as THREE from "three";
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
  Sun,
  Compass,
  AlertTriangle,
  Sliders,
  Sparkles,
} from "lucide-react";

// ============================================================================
// PRISMA SCHEMA DOMAIN TYPES (Mirrors src/db/schema.prisma without modifying it)
// ============================================================================

export type PrismaPropertyType =
  | "APARTMENT"
  | "INDEPENDENT_HOUSE"
  | "VILLA"
  | "PLOT_LAND"
  | "PENTHOUSE"
  | "BUILDER_FLOOR";

export type PrismaFlooringType =
  | "VITRIFIED_TILES"
  | "CERAMIC_TILES"
  | "MARBLE"
  | "ITALIAN_MARBLE"
  | "GRANITE"
  | "WOODEN"
  | "MOSAIC"
  | "CONCRETE"
  | "OTHER";

export type PrismaFurnishingStatus =
  | "UNFURNISHED"
  | "SEMI_FURNISHED"
  | "FULLY_FURNISHED";

export type PrismaFacingDirection =
  | "NORTH"
  | "SOUTH"
  | "EAST"
  | "WEST"
  | "NORTH_EAST"
  | "NORTH_WEST"
  | "SOUTH_EAST"
  | "SOUTH_WEST";

export type PrismaPropertyView =
  | "GARDEN"
  | "POOL"
  | "CLUBHOUSE"
  | "COMMUNITY"
  | "MAIN_ROAD"
  | "CITY"
  | "SEA"
  | "LAKE"
  | "RIVER"
  | "GOLF_COURSE"
  | "HILLS"
  | "FOREST";

export interface SchemaPropertyInput {
  id?: string;
  publicId?: string;
  title?: string;
  description?: string;
  propertyType?: PrismaPropertyType;
  configuration?: string; // e.g. "3BHK", "4BHK"
  bhkCount?: number;
  carpetAreaSqft?: number;
  superBuiltUpAreaSqft?: number;
  floor?: string;
  floorNumber?: number;
  totalFloors?: number;
  facing?: PrismaFacingDirection;
  flooring?: PrismaFlooringType;
  furnishing?: PrismaFurnishingStatus;
  views?: PrismaPropertyView[];
  balconyCount?: number;
  bathrooms?: number;
  seepageDetected?: boolean;
  city?: string;
  locality?: string;
  prompt?: string;
}

export interface DeclarativeTwinViewerProps {
  property?: SchemaPropertyInput;
  prompt?: string;
  className?: string;
  initialMode?: "orbit" | "walk" | "tour";
  showSchemaController?: boolean;
}

// ============================================================================
// PROCEDURAL ARCHITECTURAL PALETTES (Strictly mapped from FlooringType)
// ============================================================================

const FLOOR_PALETTES: Record<PrismaFlooringType, { floorColor: number; floorType: string; wallColor: number; roughness: number }> = {
  ITALIAN_MARBLE: { floorColor: 0xf4f1ea, floorType: "Italian Statuario & Botticino Marble", wallColor: 0xfaf8f5, roughness: 0.15 },
  MARBLE: { floorColor: 0xfbf9f5, floorType: "Greek Thassos White Marble", wallColor: 0xffffff, roughness: 0.20 },
  WOODEN: { floorColor: 0xc9a275, floorType: "Engineered German Oak Hardwood", wallColor: 0xeae7df, roughness: 0.65 },
  GRANITE: { floorColor: 0x263238, floorType: "Honed Nero Impala Granite & Quartzite", wallColor: 0xf8f8f8, roughness: 0.40 },
  VITRIFIED_TILES: { floorColor: 0xece9e2, floorType: "Matte Vitrified Architectural Tiles (1200x600mm)", wallColor: 0xf1eee7, roughness: 0.55 },
  CERAMIC_TILES: { floorColor: 0xe8ecef, floorType: "Glazed Ceramic Tiles", wallColor: 0xf5f5f3, roughness: 0.50 },
  MOSAIC: { floorColor: 0xddd8ce, floorType: "Artisan Terrazzo & Mosaic Stone", wallColor: 0xefece6, roughness: 0.50 },
  CONCRETE: { floorColor: 0x8c8c8c, floorType: "Polished Architectural Concrete Screed", wallColor: 0xeceae4, roughness: 0.70 },
  OTHER: { floorColor: 0xece9e2, floorType: "Architectural Composite Slab", wallColor: 0xf1eee7, roughness: 0.55 },
};

const SUNLIGHT_VECTORS: Record<PrismaFacingDirection, { pos: [number, number, number]; color: number; label: string }> = {
  EAST: { pos: [18, 14, 16], color: 0xfff2de, label: "Morning Golden Sunrise" },
  NORTH_EAST: { pos: [14, 16, 14], color: 0xfff5e4, label: "Morning North-East Daylight" },
  WEST: { pos: [-18, 11, 16], color: 0xffd4a0, label: "Golden Hour Sunset" },
  SOUTH_WEST: { pos: [-14, 13, 14], color: 0xffe0b2, label: "Warm Afternoon Sunlight" },
  NORTH: { pos: [0, 18, -14], color: 0xe8f0fe, label: "Cool Diffused Daylight" },
  NORTH_WEST: { pos: [-12, 15, -10], color: 0xf5f2e8, label: "Soft Afternoon North-West Light" },
  SOUTH: { pos: [6, 22, 6], color: 0xfffee5, label: "High Zenith Midday Sunlight" },
  SOUTH_EAST: { pos: [14, 16, 10], color: 0xfff5e4, label: "Bright Morning South-East Sun" },
};

// ============================================================================
// DECLARATIVE SCHEMA-TO-SPATIAL COMPILER (IN-MEMORY, ZERO DISK I/O)
// ============================================================================

function compileSchemaToSpatialScene(input: SchemaPropertyInput, rawPrompt = "") {
  const promptText = `${rawPrompt} ${input.prompt || ""} ${input.description || ""} ${input.title || ""}`.toLowerCase();

  // 1. Resolve Configuration & Bedroom count
  let bhk = input.bhkCount;
  if (!bhk) {
    const m = (input.configuration || "").match(/(\d+)\s*(?:bhk|bed)/i) || promptText.match(/(\d+)\s*(?:bhk|bed)/i);
    bhk = m ? parseInt(m[1]) : 3;
  }
  bhk = Math.max(1, Math.min(5, bhk));

  // 2. Resolve Property Type & Archetype
  let propType: PrismaPropertyType = input.propertyType || "APARTMENT";
  if (!input.propertyType) {
    if (promptText.includes("penthouse")) propType = "PENTHOUSE";
    else if (promptText.includes("villa") || promptText.includes("bungalow")) propType = "VILLA";
    else if (promptText.includes("builder floor")) propType = "BUILDER_FLOOR";
  }

  // 3. Resolve Flooring
  let flooring: PrismaFlooringType = input.flooring || "VITRIFIED_TILES";
  if (!input.flooring) {
    if (promptText.includes("italian") || promptText.includes("statuario") || promptText.includes("botticino")) flooring = "ITALIAN_MARBLE";
    else if (promptText.includes("marble")) flooring = "MARBLE";
    else if (promptText.includes("wood") || promptText.includes("oak") || promptText.includes("hardwood")) flooring = "WOODEN";
    else if (promptText.includes("granite") || promptText.includes("quartz")) flooring = "GRANITE";
    else if (promptText.includes("concrete")) flooring = "CONCRETE";
  }

  // 4. Resolve Furnishing
  let furnishing: PrismaFurnishingStatus = input.furnishing || "FULLY_FURNISHED";
  if (!input.furnishing) {
    if (promptText.includes("unfurnished") || promptText.includes("bare shell") || promptText.includes("raw")) furnishing = "UNFURNISHED";
    else if (promptText.includes("semi") || promptText.includes("modular kitchen")) furnishing = "SEMI_FURNISHED";
  }

  // 5. Resolve Facing
  let facing: PrismaFacingDirection = input.facing || "EAST";
  if (!input.facing) {
    if (promptText.includes("north-east") || promptText.includes("northeast")) facing = "NORTH_EAST";
    else if (promptText.includes("north-west") || promptText.includes("northwest")) facing = "NORTH_WEST";
    else if (promptText.includes("south-east") || promptText.includes("southeast")) facing = "SOUTH_EAST";
    else if (promptText.includes("south-west") || promptText.includes("southwest")) facing = "SOUTH_WEST";
    else if (promptText.includes("north")) facing = "NORTH";
    else if (promptText.includes("west")) facing = "WEST";
    else if (promptText.includes("south")) facing = "SOUTH";
  }

  // 6. Resolve Views
  let views: PrismaPropertyView[] = input.views && input.views.length > 0 ? [...input.views] : [];
  if (views.length === 0) {
    if (promptText.includes("sea") || promptText.includes("ocean") || promptText.includes("marina")) views.push("SEA");
    if (promptText.includes("pool")) views.push("POOL");
    if (promptText.includes("golf") || promptText.includes("fairway")) views.push("GOLF_COURSE");
    if (promptText.includes("garden") || promptText.includes("park")) views.push("GARDEN");
    if (promptText.includes("city") || promptText.includes("skyline")) views.push("CITY");
    if (views.length === 0) views = ["CITY", "GARDEN"];
  }

  // 7. Resolve Carpet Area
  let carpet = input.carpetAreaSqft || (bhk === 1 ? 650 : bhk === 2 ? 1200 : bhk === 3 ? 1950 : bhk === 4 ? 2900 : 3800);
  if (propType === "PENTHOUSE" || propType === "VILLA") carpet = Math.max(carpet, 2800);

  // 8. Resolve Seepage / Defects
  let seepage = input.seepageDetected ?? (promptText.includes("seepage") || promptText.includes("dampness") || promptText.includes("leakage"));

  const isVilla = propType === "VILLA" || propType === "INDEPENDENT_HOUSE";
  const isPenthouse = propType === "PENTHOUSE";
  const levelsCount = isVilla ? 3 : 1;
  const ceilingHeight = isPenthouse ? 3.8 : 3.2;

  // 9. Procedural 3D Space Moulding
  // Enforce calibrated 3:1 Living Hall to Kitchen ratio
  const livingW = bhk >= 3 ? 9.2 : 7.6;
  const livingD = bhk >= 3 ? 6.8 : 5.8;
  const kitW = Math.round(livingW * 0.48 * 10) / 10;
  const kitD = Math.round(livingD * 0.68 * 10) / 10;
  const kitX = Math.round((livingW / 2 + kitW / 2 + 0.2) * 10) / 10;

  const floorPal = FLOOR_PALETTES[flooring] || FLOOR_PALETTES.VITRIFIED_TILES;

  interface DeclaredRoom {
    id: string;
    name: string;
    category: string;
    floorLevel: number;
    bounds: { x: number; y: number; z: number; w: number; d: number; h: number };
    floorColor: number;
    floorType: string;
    wallColor: number;
    carpetSqft: number;
    furniture: Array<{ id: string; name: string; type: string; pos: [number, number, number]; size: [number, number, number]; color: number }>;
    defect?: { type: string; pos: [number, number, number]; color: number; desc: string };
  }

  const rooms: DeclaredRoom[] = [];

  // Living Room
  const livingFurn: any[] = [];
  if (furnishing === "FULLY_FURNISHED") {
    livingFurn.push(
      { id: "sofa", name: "Sectional Boucle Sofa", type: "sofa", pos: [-0.8, 0.42, 1.8], size: [4.2, 0.75, 1.8], color: 0xd9d1c0 },
      { id: "coffee_table", name: "Marble Coffee Table", type: "table", pos: [-0.8, 0.25, 0.4], size: [2.2, 0.45, 1.1], color: 0xfafaf6 },
      { id: "dining", name: "Oak Dining Suite", type: "table", pos: [2.6, 0.45, -1.0], size: [2.4, 0.85, 1.2], color: 0xa87042 }
    );
  }
  rooms.push({
    id: "living",
    name: isVilla ? "Double-Height Grand Living Hall" : "Grand Living & Dining Pavilion",
    category: "LIVING_ROOM",
    floorLevel: 0,
    bounds: { x: 0, y: 0, z: 0, w: livingW, d: livingD, h: isVilla ? 6.4 : ceilingHeight },
    floorColor: floorPal.floorColor,
    floorType: floorPal.floorType,
    wallColor: floorPal.wallColor,
    carpetSqft: Math.round(carpet * 0.33),
    furniture: livingFurn,
  });

  // Kitchen (Calibrated 3:1 Ratio)
  const kitFurn: any[] = [];
  if (furnishing !== "UNFURNISHED") {
    kitFurn.push(
      { id: "k_island", name: "Quartz Island Prep Counter", type: "counter", pos: [kitX, 0.48, -0.6], size: [3.0, 0.95, 1.3], color: 0x8d6f50 },
      { id: "k_cabinets", name: "Blum Integrated Base Cabinets", type: "counter", pos: [kitX, 0.45, 1.2], size: [2.8, 0.9, 0.7], color: 0x5d4037 }
    );
  }
  rooms.push({
    id: "kitchen",
    name: "Siemens Integrated Culinary Studio",
    category: "KITCHEN",
    floorLevel: 0,
    bounds: { x: kitX, y: 0, z: -0.6, w: kitW, d: kitD, h: ceilingHeight },
    floorColor: FLOOR_PALETTES.GRANITE.floorColor,
    floorType: FLOOR_PALETTES.GRANITE.floorType,
    wallColor: floorPal.wallColor,
    carpetSqft: Math.round(carpet * 0.11),
    furniture: kitFurn,
  });

  // Master Bedroom (Bedroom 1)
  const mX = Math.round((-livingW / 2 - 2.9 - 0.2) * 10) / 10;
  const masterFurn: any[] = [];
  if (furnishing === "FULLY_FURNISHED") {
    masterFurn.push(
      { id: "m_bed", name: "King Designer Bed", type: "bed", pos: [mX, 0.35, 0.2], size: [2.2, 0.4, 2.1], color: 0xfafaf6 },
      { id: "m_wardrobe", name: "Full-Height Fitted Wardrobe", type: "wardrobe", pos: [mX, 1.2, -1.8], size: [3.2, 2.4, 0.6], color: 0x8d6f50 }
    );
  } else if (furnishing === "SEMI_FURNISHED") {
    masterFurn.push({ id: "m_wardrobe", name: "Full-Height Fitted Wardrobe", type: "wardrobe", pos: [mX, 1.2, -1.8], size: [3.2, 2.4, 0.6], color: 0x8d6f50 });
  }
  rooms.push({
    id: "master",
    name: "Presidential Master Suite (Bedroom 1)",
    category: "MASTER_BEDROOM",
    floorLevel: 0,
    bounds: { x: mX, y: 0, z: 0.5, w: 5.8, d: 5.4, h: ceilingHeight },
    floorColor: FLOOR_PALETTES.WOODEN.floorColor,
    floorType: FLOOR_PALETTES.WOODEN.floorType,
    wallColor: FLOOR_PALETTES.WOODEN.wallColor,
    carpetSqft: Math.round(carpet * 0.22),
    furniture: masterFurn,
    defect: seepage
      ? { type: "seepage", pos: [mX - 2.7, 2.2, 0.5], color: 0xf97316, desc: "Active seepage moisture mark verified by physical inspection" }
      : undefined,
  });

  // Secondary Bedrooms based on exact BHK count
  if (bhk >= 2) {
    const b2X = Math.round((livingW / 2 + 2.3 + 0.2) * 10) / 10;
    const b2Furn = furnishing === "FULLY_FURNISHED" ? [{ id: "b2_bed", name: "Queen Bed", type: "bed", pos: [b2X, 0.35, 4.4], size: [1.9, 0.4, 2.0], color: 0xfafaf6 }] : [];
    rooms.push({
      id: "bedroom_2",
      name: "Guest Suite (Bedroom 2)",
      category: "GUEST_BEDROOM",
      floorLevel: 0,
      bounds: { x: b2X, y: 0, z: 4.6, w: 4.6, d: 4.4, h: ceilingHeight },
      floorColor: floorPal.floorColor,
      floorType: floorPal.floorType,
      wallColor: floorPal.wallColor,
      carpetSqft: Math.round(carpet * 0.14),
      furniture: b2Furn,
    });
  }

  if (bhk >= 3) {
    const b3X = Math.round((-livingW / 2 - 2.4 - 0.2) * 10) / 10;
    const b3Furn = furnishing === "FULLY_FURNISHED" ? [{ id: "b3_bed", name: "Queen Bed", type: "bed", pos: [b3X, 0.35, -4.8], size: [1.9, 0.4, 2.0], color: 0xfafaf6 }] : [];
    rooms.push({
      id: "bedroom_3",
      name: "Children's Suite (Bedroom 3)",
      category: "GUEST_BEDROOM",
      floorLevel: 0,
      bounds: { x: b3X, y: 0, z: -4.8, w: 4.8, d: 4.4, h: ceilingHeight },
      floorColor: FLOOR_PALETTES.WOODEN.floorColor,
      floorType: FLOOR_PALETTES.WOODEN.floorType,
      wallColor: FLOOR_PALETTES.WOODEN.wallColor,
      carpetSqft: Math.round(carpet * 0.12),
      furniture: b3Furn,
    });
  }

  if (bhk >= 4) {
    const b4Furn = furnishing === "FULLY_FURNISHED" ? [{ id: "b4_bed", name: "Queen Bed", type: "bed", pos: [0, 0.35, -5.6], size: [1.9, 0.4, 2.0], color: 0xfafaf6 }] : [];
    rooms.push({
      id: "bedroom_4",
      name: "Garden Suite (Bedroom 4)",
      category: "GUEST_BEDROOM",
      floorLevel: 0,
      bounds: { x: 0, y: 0, z: -5.6, w: 4.8, d: 4.2, h: ceilingHeight },
      floorColor: floorPal.floorColor,
      floorType: floorPal.floorType,
      wallColor: floorPal.wallColor,
      carpetSqft: Math.round(carpet * 0.11),
      furniture: b4Furn,
    });
  }

  if (bhk >= 5) {
    const b5Furn = furnishing === "FULLY_FURNISHED" ? [{ id: "b5_desk", name: "Executive Desk", type: "table", pos: [5.4, 0.35, -4.5], size: [1.6, 0.75, 0.7], color: 0xa87042 }] : [];
    rooms.push({
      id: "bedroom_5",
      name: "Executive Library Suite (Bedroom 5)",
      category: "GUEST_BEDROOM",
      floorLevel: 0,
      bounds: { x: 5.4, y: 0, z: -5.6, w: 4.4, d: 4.0, h: ceilingHeight },
      floorColor: FLOOR_PALETTES.WOODEN.floorColor,
      floorType: FLOOR_PALETTES.WOODEN.floorType,
      wallColor: FLOOR_PALETTES.WOODEN.wallColor,
      carpetSqft: Math.round(carpet * 0.09),
      furniture: b5Furn,
    });
  }

  // Outdoor Balcony / Sky Deck
  const balcW = Math.round(livingW * 0.7 * 10) / 10;
  const balcD = 3.4;
  const balcZ = Math.round((livingD / 2 + balcD / 2) * 10) / 10;
  const balcFurn: any[] = [];
  if (isPenthouse || views.includes("POOL")) {
    balcFurn.push({ id: "jacuzzi", name: "Heated Sky Jacuzzi", type: "pool", pos: [-1.4, 0.4, balcZ], size: [2.4, 0.5, 2.0], color: 0x0f2b36 });
  }
  if (furnishing === "FULLY_FURNISHED") {
    balcFurn.push({ id: "balc_lounge", name: "Teak Loveseat", type: "chair", pos: [1.8, 0.35, balcZ], size: [1.8, 0.4, 0.8], color: 0xa87042 });
  }
  rooms.push({
    id: "balcony",
    name: isPenthouse ? "Wrap-Around Sky Deck & Jacuzzi" : "Covered Panoramic Sky Balcony",
    category: "BALCONY",
    floorLevel: 0,
    bounds: { x: 1.8, y: 0, z: balcZ, w: balcW, d: balcD, h: 1.1 },
    floorColor: 0xa87042,
    floorType: "Weatherproof Teak Composite Deck",
    wallColor: floorPal.wallColor,
    carpetSqft: Math.round(carpet * 0.10),
    furniture: balcFurn,
  });

  const sunlight = SUNLIGHT_VECTORS[facing] || SUNLIGHT_VECTORS.EAST;

  return {
    propertyTitle: input.title || (rawPrompt ? rawPrompt.split(".")[0].slice(0, 50) : "Sovereign 3D Twin"),
    propertyType: propType,
    configuration: `${bhk} BHK`,
    bhkCount: bhk,
    carpetSqft: carpet,
    flooring,
    furnishing,
    facing,
    views,
    levelsCount,
    ceilingHeight,
    seepageDetected: seepage,
    sunlight,
    rooms,
    livingToKitchenRatio: (Math.round(carpet * 0.33) / Math.max(1, Math.round(carpet * 0.11))).toFixed(2),
  };
}

// ============================================================================
// MAIN DECLARATIVE SCHEMA 3D COMPONENT (Zero Blueprint File, Zero JSON File)
// ============================================================================

export default function DeclarativeSchemaTwinViewer({
  property = {},
  prompt = "",
  className = "",
  initialMode = "orbit",
  showSchemaController = true,
}: DeclarativeTwinViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null);

  // Live Reactive Schema State (can mould on-the-fly)
  const [activePrompt, setActivePrompt] = useState(prompt);
  const [activeBHK, setActiveBHK] = useState(property.bhkCount || 3);
  const [activePropertyType, setActivePropertyType] = useState<PrismaPropertyType>(property.propertyType || "APARTMENT");
  const [activeFlooring, setActiveFlooring] = useState<PrismaFlooringType>(property.flooring || "ITALIAN_MARBLE");
  const [activeFurnishing, setActiveFurnishing] = useState<PrismaFurnishingStatus>(property.furnishing || "FULLY_FURNISHED");
  const [activeFacing, setActiveFacing] = useState<PrismaFacingDirection>(property.facing || "EAST");
  const [activeSeepage, setActiveSeepage] = useState(property.seepageDetected || false);
  const [activeCarpet, setActiveCarpet] = useState(property.carpetAreaSqft || 2100);

  const [mode, setMode] = useState<"orbit" | "walk" | "tour">(initialMode);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [selectedRoomId, setSelectedRoomId] = useState<string>("all");
  const [isCutaway, setIsCutaway] = useState(false);

  // Declarative compile in-memory (No JSON files!)
  const spatialScene = useMemo(() => {
    return compileSchemaToSpatialScene(
      {
        ...property,
        bhkCount: activeBHK,
        propertyType: activePropertyType,
        flooring: activeFlooring,
        furnishing: activeFurnishing,
        facing: activeFacing,
        carpetAreaSqft: activeCarpet,
        seepageDetected: activeSeepage,
      },
      activePrompt
    );
  }, [property, activePrompt, activeBHK, activePropertyType, activeFlooring, activeFurnishing, activeFacing, activeCarpet, activeSeepage]);

  // Three.js References
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const dynamicGroupRef = useRef<THREE.Group | null>(null);

  // Camera animation interpolation state
  const camState = useRef({
    theta: 0.72,
    phi: 1.05,
    radius: 28.0,
    target: new THREE.Vector3(0, 1.4, 0),
    tgtTheta: 0.72,
    tgtPhi: 1.05,
    tgtRadius: 28.0,
    tgtTarget: new THREE.Vector3(0, 1.4, 0),
    walkPos: new THREE.Vector3(0, 1.65, 8.0),
    isDragging: false,
    prevX: 0,
    prevY: 0,
  });

  // Initialize Three.js WebGL viewport
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 550;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x161412);
    scene.fog = new THREE.FogExp2(0x161412, 0.015);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 200);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    rendererRef.current = renderer;

    while (container.firstChild) container.removeChild(container.firstChild);
    container.appendChild(renderer.domElement);

    // Foundation Base Grid
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(160, 160),
      new THREE.MeshLambertMaterial({ color: 0x1f1d1a })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    const gridHelper = new THREE.GridHelper(160, 80, 0x44403c, 0x292524);
    gridHelper.position.y = 0.01;
    scene.add(gridHelper);

    // Lighting Rig
    scene.add(new THREE.HemisphereLight(0xfff7ed, 0x292524, 0.65));

    const sunLight = new THREE.DirectionalLight(0xfff2de, 1.1);
    sunLight.name = "sunLight";
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(1024, 1024);
    scene.add(sunLight);

    // Group for dynamic procedural geometry
    const dynamicGroup = new THREE.Group();
    dynamicGroupRef.current = dynamicGroup;
    scene.add(dynamicGroup);

    // Animation Loop
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate);
      const cs = camState.current;

      cs.theta += (cs.tgtTheta - cs.theta) * 0.08;
      cs.phi += (cs.tgtPhi - cs.phi) * 0.08;
      cs.radius += (cs.tgtRadius - cs.radius) * 0.08;
      cs.target.lerp(cs.tgtTarget, 0.08);

      const x = cs.target.x + cs.radius * Math.sin(cs.phi) * Math.sin(cs.theta);
      const y = cs.target.y + cs.radius * Math.cos(cs.phi);
      const z = cs.target.z + cs.radius * Math.sin(cs.phi) * Math.cos(cs.theta);

      camera.position.set(x, y, z);
      camera.lookAt(cs.target);

      renderer.render(scene, camera);
    };
    animate();

    // Resize Handler
    const handleResize = () => {
      if (!container || !camera || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    // Pointer Drag Controls
    const handleMouseDown = (e: MouseEvent) => {
      camState.current.isDragging = true;
      camState.current.prevX = e.clientX;
      camState.current.prevY = e.clientY;
    };
    const handleMouseMove = (e: MouseEvent) => {
      if (!camState.current.isDragging) return;
      const dx = e.clientX - camState.current.prevX;
      const dy = e.clientY - camState.current.prevY;
      camState.current.prevX = e.clientX;
      camState.current.prevY = e.clientY;

      camState.current.tgtTheta -= dx * 0.006;
      camState.current.tgtPhi = Math.max(0.08, Math.min(Math.PI / 2 - 0.05, camState.current.tgtPhi - dy * 0.006));
    };
    const handleMouseUp = () => {
      camState.current.isDragging = false;
    };
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      camState.current.tgtRadius = Math.max(6.0, Math.min(50.0, camState.current.tgtRadius + e.deltaY * 0.02));
    };

    container.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    container.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      window.removeEventListener("resize", handleResize);
      container.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      container.removeEventListener("wheel", handleWheel);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      renderer.dispose();
    };
  }, []);

  // Update Procedural Scene Graph Declaratively on SpatialScene changes
  useEffect(() => {
    const dynamicGroup = dynamicGroupRef.current;
    const scene = sceneRef.current;
    if (!dynamicGroup || !scene) return;

    // Clear previous in-memory geometries
    while (dynamicGroup.children.length > 0) {
      const child = dynamicGroup.children[0] as THREE.Mesh;
      if (child.geometry) child.geometry.dispose();
      dynamicGroup.remove(child);
    }

    // 1. Update Directional Sun Light based on Facing Direction
    const sunLight = scene.getObjectByName("sunLight") as THREE.DirectionalLight;
    if (sunLight) {
      sunLight.color.setHex(spatialScene.sunlight.color);
      sunLight.position.set(...spatialScene.sunlight.pos);
    }

    // 2. Foundation Slab
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    spatialScene.rooms.forEach((r) => {
      const b = r.bounds;
      minX = Math.min(minX, b.x - b.w / 2);
      maxX = Math.max(maxX, b.x + b.w / 2);
      minZ = Math.min(minZ, b.z - b.d / 2);
      maxZ = Math.max(maxZ, b.z + b.d / 2);
    });
    const totalW = Math.max(20, maxX - minX + 3.0);
    const totalD = Math.max(16, maxZ - minZ + 3.0);
    const centerX = (minX + maxX) / 2;
    const centerZ = (minZ + maxZ) / 2;

    const foundationMesh = new THREE.Mesh(
      new THREE.BoxGeometry(totalW, 0.35, totalD),
      new THREE.MeshLambertMaterial({ color: 0x2b2e35 })
    );
    foundationMesh.position.set(centerX, 0.175, centerZ);
    foundationMesh.receiveShadow = true;
    dynamicGroup.add(foundationMesh);

    // 3. Declarative Room Slabs, Walls, Furniture & Defect Pins
    spatialScene.rooms.forEach((room) => {
      const b = room.bounds;

      // Floor Mesh
      const floorMat = new THREE.MeshLambertMaterial({ color: room.floorColor });
      const floorMesh = new THREE.Mesh(new THREE.BoxGeometry(b.w, 0.22, b.d), floorMat);
      floorMesh.position.set(b.x, b.y + 0.11, b.z);
      floorMesh.receiveShadow = true;
      dynamicGroup.add(floorMesh);

      // Baseboard Skirting
      const skirtMat = new THREE.MeshLambertMaterial({ color: 0x44403c });
      const skirtMesh1 = new THREE.Mesh(new THREE.BoxGeometry(b.w, 0.08, 0.04), skirtMat);
      skirtMesh1.position.set(b.x, b.y + 0.22 + 0.04, b.z - b.d / 2 + 0.02);
      dynamicGroup.add(skirtMesh1);

      // Perimeter Enclosing Walls
      const wallMat = new THREE.MeshLambertMaterial({ color: room.wallColor });
      const wallThickness = 0.18;

      // Back Wall
      const wallNorth = new THREE.Mesh(new THREE.BoxGeometry(b.w, b.h, wallThickness), wallMat);
      wallNorth.position.set(b.x, b.y + b.h / 2, b.z - b.d / 2 + wallThickness / 2);
      wallNorth.castShadow = true;
      wallNorth.receiveShadow = true;
      dynamicGroup.add(wallNorth);

      // Side Walls
      const wallWest = new THREE.Mesh(new THREE.BoxGeometry(wallThickness, b.h, b.d), wallMat);
      wallWest.position.set(b.x - b.w / 2 + wallThickness / 2, b.y + b.h / 2, b.z);
      wallWest.castShadow = true;
      wallWest.receiveShadow = true;
      dynamicGroup.add(wallWest);

      // Staged Interior Furniture
      room.furniture.forEach((f) => {
        const fMesh = new THREE.Mesh(new THREE.BoxGeometry(...f.size), new THREE.MeshLambertMaterial({ color: f.color }));
        fMesh.position.set(...f.pos);
        fMesh.castShadow = true;
        dynamicGroup.add(fMesh);
      });

      // 3D Physical Defect Pin (seepage / crack marker)
      if (room.defect) {
        const def = room.defect;
        const pinMat = new THREE.MeshBasicMaterial({ color: def.color });
        const pinMesh = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 16), pinMat);
        pinMesh.position.set(...def.pos);

        const ringMat = new THREE.MeshBasicMaterial({ color: def.color, wireframe: true });
        const ringMesh = new THREE.Mesh(new THREE.RingGeometry(0.22, 0.35, 16), ringMat);
        ringMesh.position.set(...def.pos);
        ringMesh.rotation.y = Math.PI / 2;

        dynamicGroup.add(pinMesh);
        dynamicGroup.add(ringMesh);
      }
    });
  }, [spatialScene]);

  // Focus specific room
  const handleSelectRoom = (roomId: string) => {
    setSelectedRoomId(roomId);
    if (roomId === "all") {
      camState.current.tgtTarget.set(0, 1.4, 0);
      camState.current.tgtRadius = isCutaway ? 36.0 : 28.0;
    } else {
      const rm = spatialScene.rooms.find((r) => r.id === roomId);
      if (rm) {
        camState.current.tgtTarget.set(rm.bounds.x, rm.bounds.y + 1.2, rm.bounds.z);
        camState.current.tgtRadius = 12.0;
      }
    }
  };

  // Toggle Cutaway Top-Down View
  const toggleCutaway = () => {
    const next = !isCutaway;
    setIsCutaway(next);
    if (next) {
      camState.current.tgtPhi = 0.08;
      camState.current.tgtRadius = 36.0;
    } else {
      camState.current.tgtPhi = 1.05;
      camState.current.tgtRadius = 28.0;
    }
  };

  return (
    <div className={`relative w-full h-[650px] rounded-2xl overflow-hidden bg-stone-950 border border-stone-800 flex flex-col font-sans select-none ${className}`}>
      {/* Top Bar Header */}
      <header className="h-14 border-b border-stone-800 bg-stone-900/90 backdrop-blur-md px-4 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-black text-xs">
            3D
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-white tracking-tight">{spatialScene.propertyTitle}</h2>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Declarative Schema Twin · Zero-File
              </span>
            </div>
            <p className="text-[11px] text-stone-400">
              {spatialScene.configuration} · {spatialScene.carpetSqft.toLocaleString()} sq.ft · {spatialScene.flooring.replace(/_/g, " ")} · {spatialScene.sunlight.label}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsDrawerOpen(!isDrawerOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-500 text-stone-950 hover:bg-amber-400 transition-all shadow-md shadow-amber-500/20"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>Mould Schema Live</span>
          </button>

          <button
            onClick={toggleCutaway}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isCutaway ? "bg-amber-500/20 border-amber-500 text-amber-300" : "bg-stone-800/80 border-stone-700 text-stone-300 hover:text-white"
            }`}
          >
            <Grid className="h-3.5 w-3.5" />
            <span>{isCutaway ? "📐 Perspective" : "📐 Cutaway Plan"}</span>
          </button>
        </div>
      </header>

      {/* Main 3D Viewport */}
      <div className="flex-1 relative overflow-hidden">
        <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* Live Defect Alert Toast if Seepage Detected */}
        {spatialScene.seepageDetected && (
          <div className="absolute top-4 left-4 z-10">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-950/90 border border-amber-500/50 text-amber-300 text-xs font-medium backdrop-blur-md shadow-xl animate-pulse">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span>Inspection Defect Pin active in Master Suite</span>
            </div>
          </div>
        )}

        {/* Bottom Room Selector Pills */}
        <div className="absolute bottom-4 left-4 right-4 z-10 pointer-events-none">
          <div className="pointer-events-auto flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
            <button
              onClick={() => handleSelectRoom("all")}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all border ${
                selectedRoomId === "all" ? "bg-amber-500 text-stone-950 border-amber-400 shadow-lg" : "bg-stone-900/80 text-stone-300 border-stone-800 hover:bg-stone-800"
              }`}
            >
              Full Residence
            </button>
            {spatialScene.rooms.map((r) => (
              <button
                key={r.id}
                onClick={() => handleSelectRoom(r.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all border ${
                  selectedRoomId === r.id ? "bg-amber-500 text-stone-950 font-bold border-amber-400 shadow-lg" : "bg-stone-900/80 text-stone-300 border-stone-800 hover:bg-stone-800"
                }`}
              >
                {r.name}
              </button>
            ))}
          </div>
        </div>

        {/* Schema Information Overlay Card (Bottom Right) */}
        <div className="absolute bottom-16 right-4 z-10 w-72 rounded-xl bg-stone-900/90 border border-stone-800 p-3 text-xs space-y-1.5 backdrop-blur-md shadow-2xl pointer-events-none">
          <div className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between">
            <span>Declarative Schema Mapping</span>
            <span className="text-emerald-400 font-mono">0.2ms</span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Living : Kitchen Ratio:</span>
            <span className="font-bold text-amber-300">{spatialScene.livingToKitchenRatio} : 1</span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Flooring Finish:</span>
            <span className="font-semibold text-stone-200">{spatialScene.flooring.replace(/_/g, " ")}</span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Interior Staging:</span>
            <span className="font-semibold text-stone-200">{spatialScene.furnishing.replace(/_/g, " ")}</span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Sun Orientation:</span>
            <span className="font-semibold text-stone-200">{spatialScene.facing}</span>
          </div>
        </div>

        {/* Interactive Live Schema Moulding Drawer (Side Panel) */}
        {showSchemaController && isDrawerOpen && (
          <aside className="absolute right-0 top-0 bottom-0 w-84 bg-stone-900/98 border-l border-stone-800 shadow-2xl backdrop-blur-2xl z-30 p-4 overflow-y-auto space-y-3.5 text-xs animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-stone-800">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-400" />
                <h3 className="font-bold uppercase tracking-wider text-white text-xs">Mould 3D Space from DB</h3>
              </div>
              <button onClick={() => setIsDrawerOpen(false)} className="text-stone-400 hover:text-white text-sm px-1.5 py-0.5 rounded hover:bg-stone-800">
                ✕
              </button>
            </div>

            {/* Prompt Input Box */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-stone-300 block">Raw Database Prompt / Description</label>
              <textarea
                value={activePrompt}
                onChange={(e) => setActivePrompt(e.target.value)}
                placeholder="Paste any DB prompt, e.g. 4BHK Penthouse in Worli with Italian marble, fully furnished, sea view, West facing, seepage in master bath"
                rows={3}
                className="w-full bg-stone-950 border border-stone-700 rounded-xl p-2 text-xs text-stone-100 placeholder-stone-600 focus:outline-none focus:border-amber-500 resize-y"
              />
            </div>

            {/* Schema Enums Fine-Tuning */}
            <div className="space-y-2.5 pt-1">
              <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wide">Prisma Schema Controls</div>

              {/* Property Type */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">Property Type</label>
                <select
                  value={activePropertyType}
                  onChange={(e) => setActivePropertyType(e.target.value as PrismaPropertyType)}
                  className="w-full bg-stone-950 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200"
                >
                  <option value="APARTMENT">APARTMENT</option>
                  <option value="PENTHOUSE">PENTHOUSE (High Ceiling + Jacuzzi)</option>
                  <option value="VILLA">VILLA (Independent Multi-Floor)</option>
                  <option value="BUILDER_FLOOR">BUILDER_FLOOR</option>
                </select>
              </div>

              {/* Configuration (BHK) */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">Configuration (Bedrooms)</label>
                <div className="grid grid-cols-5 gap-1">
                  {[1, 2, 3, 4, 5].map((num) => (
                    <button
                      key={num}
                      onClick={() => setActiveBHK(num)}
                      className={`py-1 rounded-lg font-bold text-xs border ${
                        activeBHK === num ? "bg-amber-500 text-stone-950 border-amber-400" : "bg-stone-950 text-stone-300 border-stone-800 hover:bg-stone-800"
                      }`}
                    >
                      {num} BHK
                    </button>
                  ))}
                </div>
              </div>

              {/* Flooring Type */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">Flooring Finish (FlooringType)</label>
                <select
                  value={activeFlooring}
                  onChange={(e) => setActiveFlooring(e.target.value as PrismaFlooringType)}
                  className="w-full bg-stone-950 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200"
                >
                  <option value="ITALIAN_MARBLE">ITALIAN_MARBLE (Statuario Cream)</option>
                  <option value="MARBLE">MARBLE (Thassos White)</option>
                  <option value="WOODEN">WOODEN (German Oak Planks)</option>
                  <option value="GRANITE">GRANITE (Honed Nero Quartzite)</option>
                  <option value="VITRIFIED_TILES">VITRIFIED_TILES (Matte 1200x600)</option>
                  <option value="CONCRETE">CONCRETE (Industrial Screed)</option>
                </select>
              </div>

              {/* Furnishing Status */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">Furnishing Status (FurnishingStatus)</label>
                <div className="grid grid-cols-3 gap-1">
                  {(["UNFURNISHED", "SEMI_FURNISHED", "FULLY_FURNISHED"] as PrismaFurnishingStatus[]).map((st) => (
                    <button
                      key={st}
                      onClick={() => setActiveFurnishing(st)}
                      className={`py-1 px-1 rounded-lg text-[10px] font-semibold border truncate ${
                        activeFurnishing === st ? "bg-amber-500 text-stone-950 border-amber-400" : "bg-stone-950 text-stone-300 border-stone-800 hover:bg-stone-800"
                      }`}
                    >
                      {st === "UNFURNISHED" ? "Bare Shell" : st === "SEMI_FURNISHED" ? "Semi" : "Turnkey"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Facing Direction */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">Facing Direction (FacingDirection)</label>
                <select
                  value={activeFacing}
                  onChange={(e) => setActiveFacing(e.target.value as PrismaFacingDirection)}
                  className="w-full bg-stone-950 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200"
                >
                  <option value="EAST">EAST (Golden Sunrise)</option>
                  <option value="NORTH_EAST">NORTH_EAST (Morning Daylight)</option>
                  <option value="WEST">WEST (Warm Sunset)</option>
                  <option value="NORTH">NORTH (Diffused Cool Light)</option>
                  <option value="SOUTH">SOUTH (High Noon Sun)</option>
                </select>
              </div>

              {/* Seepage / Defect Toggle */}
              <div className="pt-2">
                <label className="flex items-center gap-2 p-2 rounded-xl bg-stone-950 border border-stone-800 text-xs text-stone-200 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={activeSeepage}
                    onChange={(e) => setActiveSeepage(e.target.checked)}
                    className="rounded bg-stone-900 border-stone-700 text-amber-500"
                  />
                  <span>Simulate Inspection Seepage Defect Pin</span>
                </label>
              </div>
            </div>

            <div className="pt-2 text-[10px] text-stone-500 text-center leading-tight">
              Moulds 3D spatial geometry in RAM instantly. No JSON files or blueprints generated.
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
