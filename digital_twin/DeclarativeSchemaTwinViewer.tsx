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
  Eye,
  EyeOff,
  Video,
  Play,
  RotateCw,
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

const FLOOR_PALETTES: Record<
  PrismaFlooringType,
  { floorColor: number; floorType: string; wallColor: number; roughness: number }
> = {
  ITALIAN_MARBLE: {
    floorColor: 0xf4f1ea,
    floorType: "Italian Statuario & Botticino Marble",
    wallColor: 0xfaf8f5,
    roughness: 0.15,
  },
  MARBLE: {
    floorColor: 0xfbf9f5,
    floorType: "Greek Thassos White Marble",
    wallColor: 0xffffff,
    roughness: 0.2,
  },
  WOODEN: {
    floorColor: 0xc9a275,
    floorType: "Engineered German Oak Hardwood",
    wallColor: 0xeae7df,
    roughness: 0.65,
  },
  GRANITE: {
    floorColor: 0x263238,
    floorType: "Honed Nero Impala Granite & Quartzite",
    wallColor: 0xf8f8f8,
    roughness: 0.4,
  },
  VITRIFIED_TILES: {
    floorColor: 0xece9e2,
    floorType: "Matte Vitrified Architectural Tiles (1200x600mm)",
    wallColor: 0xf1eee7,
    roughness: 0.55,
  },
  CERAMIC_TILES: {
    floorColor: 0xe8ecef,
    floorType: "Glazed Ceramic Tiles",
    wallColor: 0xf5f5f3,
    roughness: 0.5,
  },
  MOSAIC: {
    floorColor: 0xddd8ce,
    floorType: "Artisan Terrazzo & Mosaic Stone",
    wallColor: 0xefece6,
    roughness: 0.5,
  },
  CONCRETE: {
    floorColor: 0x8c8c8c,
    floorType: "Polished Architectural Concrete Screed",
    wallColor: 0xeceae4,
    roughness: 0.7,
  },
  OTHER: {
    floorColor: 0xece9e2,
    floorType: "Architectural Composite Slab",
    wallColor: 0xf1eee7,
    roughness: 0.55,
  },
};

const SUNLIGHT_VECTORS: Record<
  PrismaFacingDirection,
  { pos: [number, number, number]; color: number; label: string }
> = {
  EAST: { pos: [22, 18, 18], color: 0xfff2de, label: "East · 5000K (Morning Sunrise)" },
  NORTH_EAST: { pos: [16, 18, 16], color: 0xfff5e4, label: "North-East · 5500K (Soft Daylight)" },
  WEST: { pos: [-22, 14, 18], color: 0xffd4a0, label: "West · 3200K (Golden Sunset)" },
  SOUTH_WEST: { pos: [-16, 16, 16], color: 0xffe0b2, label: "South-West · 3800K (Warm Afternoon)" },
  NORTH: { pos: [0, 22, -18], color: 0xe8f0fe, label: "North · 6500K (Cool Diffuse Daylight)" },
  NORTH_WEST: { pos: [-14, 18, -12], color: 0xf5f2e8, label: "North-West · 5800K (Afternoon Light)" },
  SOUTH: { pos: [8, 26, 8], color: 0xfffee5, label: "South · 5800K (High Zenith Midday)" },
  SOUTH_EAST: { pos: [16, 18, 12], color: 0xfff5e4, label: "South-East · 5200K (Bright Morning)" },
};

// ============================================================================
// BIM DATA INTERFACES FOR DECLARATIVE SYNTHESIS
// ============================================================================

export interface DeclaredRoom {
  id: string;
  name: string;
  category: string;
  floorLevel: number;
  bounds: { x: number; y: number; z: number; w: number; d: number; h: number };
  floorColor: number;
  floorType: string;
  wallColor: number;
  carpetSqft: number;
  furniture: Array<{
    id: string;
    name: string;
    type: string;
    pos: [number, number, number];
    size: [number, number, number];
    color: number;
    rotationY?: number;
  }>;
  defect?: { type: string; pos: [number, number, number]; color: number; desc: string };
  focalTarget: { pos: [number, number, number]; radius: number; theta: number; phi: number };
}

export interface DeclaredWall {
  id: string;
  pos: [number, number, number];
  size: [number, number, number];
  color: number;
  floorLevel: number;
  isExterior?: boolean;
}

export interface DeclaredDoor {
  id: string;
  pos: [number, number, number];
  size: [number, number, number];
  rotationY: number;
  doorType: "hinged" | "sliding" | "pocket";
  openAngle: number;
  floorLevel: number;
}

export interface DeclaredWindow {
  id: string;
  pos: [number, number, number];
  size: [number, number, number];
  rotationY: number;
  floorLevel: number;
}

export interface DeclaredBalcony {
  id: string;
  pos: [number, number, number];
  size: [number, number, number];
  floorLevel: number;
  railings: Array<{ pos: [number, number, number]; size: [number, number]; rotationY: number }>;
}

export interface DeclaredWater {
  id: string;
  name: string;
  pos: [number, number, number];
  size: [number, number, number];
  floorLevel: number;
  type: "jacuzzi" | "pool";
}

export interface DeclaredWaypoint {
  pos: [number, number, number];
  look: [number, number, number];
  label: string;
}

export interface DeclaredSpatialScene {
  propertyTitle: string;
  propertyType: PrismaPropertyType;
  configuration: string;
  bhkCount: number;
  carpetSqft: number;
  flooring: PrismaFlooringType;
  furnishing: PrismaFurnishingStatus;
  facing: PrismaFacingDirection;
  views: PrismaPropertyView[];
  levelsCount: number;
  ceilingHeight: number;
  seepageDetected: boolean;
  sunlight: { pos: [number, number, number]; color: number; label: string };
  livingToKitchenRatio: string;
  rooms: DeclaredRoom[];
  walls: DeclaredWall[];
  doors: DeclaredDoor[];
  windows: DeclaredWindow[];
  balconies: DeclaredBalcony[];
  waters: DeclaredWater[];
  waypoints: DeclaredWaypoint[];
}

// ============================================================================
// DECLARATIVE SCHEMA-TO-SPATIAL COMPILER (IN-MEMORY, ZERO DISK I/O)
// ============================================================================

function compileSchemaToSpatialScene(
  input: SchemaPropertyInput,
  rawPrompt = ""
): DeclaredSpatialScene {
  const promptText = `${rawPrompt} ${input.prompt || ""} ${input.description || ""} ${
    input.title || ""
  }`.toLowerCase();

  // 1. Resolve Configuration & Bedroom count
  let bhk = input.bhkCount;
  if (!bhk) {
    const m =
      (input.configuration || "").match(/(\d+)\s*(?:bhk|bed)/i) ||
      promptText.match(/(\d+)\s*(?:bhk|bed)/i);
    bhk = m ? parseInt(m[1]) : 3;
  }
  bhk = Math.max(1, Math.min(5, bhk));

  // 2. Resolve Property Type & Archetype
  let propType: PrismaPropertyType = input.propertyType || "APARTMENT";
  if (!input.propertyType) {
    if (promptText.includes("penthouse")) propType = "PENTHOUSE";
    else if (promptText.includes("villa") || promptText.includes("bungalow"))
      propType = "VILLA";
    else if (promptText.includes("builder floor")) propType = "BUILDER_FLOOR";
  }

  // 3. Resolve Flooring
  let flooring: PrismaFlooringType = input.flooring || "ITALIAN_MARBLE";
  if (!input.flooring) {
    if (
      promptText.includes("italian") ||
      promptText.includes("statuario") ||
      promptText.includes("botticino")
    )
      flooring = "ITALIAN_MARBLE";
    else if (promptText.includes("marble")) flooring = "MARBLE";
    else if (
      promptText.includes("wood") ||
      promptText.includes("oak") ||
      promptText.includes("hardwood")
    )
      flooring = "WOODEN";
    else if (promptText.includes("granite") || promptText.includes("quartz"))
      flooring = "GRANITE";
    else if (promptText.includes("concrete")) flooring = "CONCRETE";
  }

  // 4. Resolve Furnishing
  let furnishing: PrismaFurnishingStatus = input.furnishing || "FULLY_FURNISHED";
  if (!input.furnishing) {
    if (
      promptText.includes("unfurnished") ||
      promptText.includes("bare shell") ||
      promptText.includes("raw")
    )
      furnishing = "UNFURNISHED";
    else if (promptText.includes("semi") || promptText.includes("modular kitchen"))
      furnishing = "SEMI_FURNISHED";
  }

  // 5. Resolve Facing
  let facing: PrismaFacingDirection = input.facing || "EAST";
  if (!input.facing) {
    if (promptText.includes("north-east") || promptText.includes("northeast"))
      facing = "NORTH_EAST";
    else if (promptText.includes("north-west") || promptText.includes("northwest"))
      facing = "NORTH_WEST";
    else if (promptText.includes("south-east") || promptText.includes("southeast"))
      facing = "SOUTH_EAST";
    else if (promptText.includes("south-west") || promptText.includes("southwest"))
      facing = "SOUTH_WEST";
    else if (promptText.includes("north")) facing = "NORTH";
    else if (promptText.includes("west")) facing = "WEST";
    else if (promptText.includes("south")) facing = "SOUTH";
  }

  // 6. Resolve Views
  let views: PrismaPropertyView[] =
    input.views && input.views.length > 0 ? [...input.views] : [];
  if (views.length === 0) {
    if (
      promptText.includes("sea") ||
      promptText.includes("ocean") ||
      promptText.includes("marina")
    )
      views.push("SEA");
    if (promptText.includes("pool")) views.push("POOL");
    if (promptText.includes("golf") || promptText.includes("fairway"))
      views.push("GOLF_COURSE");
    if (promptText.includes("garden") || promptText.includes("park"))
      views.push("GARDEN");
    if (promptText.includes("city") || promptText.includes("skyline"))
      views.push("CITY");
    if (views.length === 0) views = ["CITY", "GARDEN"];
  }

  // 7. Resolve Carpet Area
  let carpet =
    input.carpetAreaSqft ||
    (bhk === 1 ? 650 : bhk === 2 ? 1200 : bhk === 3 ? 1950 : bhk === 4 ? 2900 : 3800);
  if (propType === "PENTHOUSE" || propType === "VILLA") carpet = Math.max(carpet, 2800);

  // 8. Resolve Seepage / Defects
  const seepage =
    input.seepageDetected ??
    (promptText.includes("seepage") ||
      promptText.includes("dampness") ||
      promptText.includes("leakage"));

  const isVilla = propType === "VILLA" || propType === "INDEPENDENT_HOUSE";
  const isPenthouse = propType === "PENTHOUSE";
  const levelsCount = isVilla ? 3 : 1;
  const ceilingHeight = isPenthouse ? 3.8 : 3.2;

  // 9. Procedural 3D Space Layout
  // Calibrated 3:1 Living Hall to Kitchen area ratio
  const livingW = bhk >= 3 ? 9.2 : 7.8;
  const livingD = bhk >= 3 ? 6.8 : 5.8;
  const kitW = Math.round(livingW * 0.48 * 10) / 10;
  const kitD = Math.round(livingD * 0.68 * 10) / 10;
  const kitX = Math.round((livingW / 2 + kitW / 2 + 0.2) * 10) / 10;

  const floorPal = FLOOR_PALETTES[flooring] || FLOOR_PALETTES.ITALIAN_MARBLE;
  const wallMatColor = floorPal.wallColor;

  const rooms: DeclaredRoom[] = [];
  const walls: DeclaredWall[] = [];
  const doors: DeclaredDoor[] = [];
  const windows: DeclaredWindow[] = [];
  const balconies: DeclaredBalcony[] = [];
  const waters: DeclaredWater[] = [];
  const waypoints: DeclaredWaypoint[] = [];

  // ==========================================
  // ROOM 1: Grand Living & Dining Pavilion
  // ==========================================
  const livingFurn: any[] = [];
  if (furnishing === "FULLY_FURNISHED") {
    livingFurn.push(
      {
        id: "sofa",
        name: "Sectional Boucle Sofa",
        type: "sofa",
        pos: [-1.2, 0.45, 1.4],
        size: [3.8, 0.78, 1.4],
        color: 0xd9d1c0,
      },
      {
        id: "chaise",
        name: "Chaise Lounge Extension",
        type: "sofa",
        pos: [1.2, 0.45, 1.8],
        size: [1.2, 0.65, 1.8],
        color: 0xd9d1c0,
      },
      {
        id: "coffee_table",
        name: "Marble Coffee Table",
        type: "table",
        pos: [-0.6, 0.26, 0.4],
        size: [2.0, 0.42, 0.9],
        color: 0xfbf9f5,
      },
      {
        id: "tv_credenza",
        name: "Low-Profile Oak Media Console",
        type: "table",
        pos: [-0.8, 0.35, -livingD / 2 + 0.4],
        size: [3.2, 0.5, 0.45],
        color: 0x5d4037,
      },
      {
        id: "dining_suite",
        name: "German Oak Dining Suite (8-Seater)",
        type: "table",
        pos: [2.4, 0.46, -1.0],
        size: [2.4, 0.85, 1.2],
        color: 0xa87042,
      }
    );
  } else if (furnishing === "SEMI_FURNISHED") {
    livingFurn.push({
      id: "tv_wall_joinery",
      name: "Architectural Fluted TV Joinery Panel",
      type: "wardrobe",
      pos: [-0.8, 1.4, -livingD / 2 + 0.15],
      size: [3.4, 2.6, 0.15],
      color: 0x8d6f50,
    });
  }

  rooms.push({
    id: "living",
    name: isVilla ? "Double-Height Grand Living Hall" : "Grand Living & Dining Pavilion",
    category: "LIVING_ROOM",
    floorLevel: 0,
    bounds: {
      x: 0,
      y: 0,
      z: 0,
      w: livingW,
      d: livingD,
      h: isVilla ? 6.4 : ceilingHeight,
    },
    floorColor: floorPal.floorColor,
    floorType: floorPal.floorType,
    wallColor: wallMatColor,
    carpetSqft: Math.round(carpet * 0.33),
    furniture: livingFurn,
    focalTarget: { pos: [0, 1.2, 0], radius: 18, theta: 0.72, phi: 1.05 },
  });

  // Perimeter walls for Living Room
  // North Wall (Back)
  walls.push({
    id: "wall_liv_north",
    pos: [0, ceilingHeight / 2, -livingD / 2],
    size: [livingW, ceilingHeight, 0.2],
    color: wallMatColor,
    floorLevel: 0,
    isExterior: true,
  });
  // West partition
  walls.push({
    id: "wall_liv_west",
    pos: [-livingW / 2, ceilingHeight / 2, -0.6],
    size: [0.2, ceilingHeight, livingD - 1.8],
    color: wallMatColor,
    floorLevel: 0,
  });
  // East partition
  walls.push({
    id: "wall_liv_east",
    pos: [livingW / 2, ceilingHeight / 2, 1.2],
    size: [0.2, ceilingHeight, livingD - 2.6],
    color: wallMatColor,
    floorLevel: 0,
  });

  // Windows in Living Room (North view)
  windows.push({
    id: "win_liv_panoramic",
    pos: [0, 1.5, -livingD / 2],
    size: [4.4, 2.2, 0.16],
    rotationY: 0,
    floorLevel: 0,
  });

  // ==========================================
  // ROOM 2: Siemens Culinary Studio (Kitchen)
  // ==========================================
  const kitFurn: any[] = [];
  if (furnishing !== "UNFURNISHED") {
    kitFurn.push(
      {
        id: "k_island",
        name: "Quartz Island Prep Counter",
        type: "counter",
        pos: [kitX, 0.5, -0.6],
        size: [kitW - 0.4, 0.95, 1.3],
        color: 0x8d6f50,
      },
      {
        id: "k_cabinets",
        name: "Blum Base Culinary Cabinets",
        type: "counter",
        pos: [kitX, 0.46, -1.8],
        size: [kitW - 0.2, 0.9, 0.7],
        color: 0x5d4037,
      }
    );
  }

  rooms.push({
    id: "kitchen",
    name: "Siemens Integrated Culinary Studio",
    category: "KITCHEN",
    floorLevel: 0,
    bounds: { x: kitX, y: 0, z: -0.8, w: kitW, d: kitD, h: ceilingHeight },
    floorColor: FLOOR_PALETTES.GRANITE.floorColor,
    floorType: FLOOR_PALETTES.GRANITE.floorType,
    wallColor: wallMatColor,
    carpetSqft: Math.round(carpet * 0.11),
    furniture: kitFurn,
    focalTarget: { pos: [kitX, 1.1, -0.8], radius: 10, theta: 0.92, phi: 0.98 },
  });

  // Kitchen exterior walls
  walls.push({
    id: "wall_kit_north",
    pos: [kitX, ceilingHeight / 2, -0.8 - kitD / 2],
    size: [kitW, ceilingHeight, 0.2],
    color: wallMatColor,
    floorLevel: 0,
    isExterior: true,
  });
  walls.push({
    id: "wall_kit_east",
    pos: [kitX + kitW / 2, ceilingHeight / 2, -0.8],
    size: [0.2, ceilingHeight, kitD],
    color: wallMatColor,
    floorLevel: 0,
    isExterior: true,
  });

  // ==========================================
  // ROOM 3: Presidential Master Suite
  // ==========================================
  const mX = Math.round((-livingW / 2 - 3.1) * 10) / 10;
  const masterLevel = isVilla ? 1 : 0;
  const masterY = masterLevel * 3.4;
  const masterFurn: any[] = [];

  if (furnishing === "FULLY_FURNISHED") {
    masterFurn.push(
      {
        id: "m_bed",
        name: "King Platform Bed & Nightstands",
        type: "bed",
        pos: [mX, masterY + 0.38, 0.4],
        size: [2.3, 0.45, 2.2],
        color: 0xfafaf6,
      },
      {
        id: "m_wardrobe",
        name: "Full-Height Fitted Wardrobe",
        type: "wardrobe",
        pos: [mX, masterY + 1.3, -1.8],
        size: [3.4, 2.5, 0.65],
        color: 0x8d6f50,
      }
    );
  } else if (furnishing === "SEMI_FURNISHED") {
    masterFurn.push({
      id: "m_wardrobe",
      name: "Full-Height Fitted Wardrobe",
      type: "wardrobe",
      pos: [mX, masterY + 1.3, -1.8],
      size: [3.4, 2.5, 0.65],
      color: 0x8d6f50,
    });
  }

  rooms.push({
    id: "master",
    name: "Presidential Master Suite (Bedroom 1)",
    category: "MASTER_BEDROOM",
    floorLevel: masterLevel,
    bounds: { x: mX, y: masterY, z: 0.5, w: 5.8, d: 5.4, h: ceilingHeight },
    floorColor: FLOOR_PALETTES.WOODEN.floorColor,
    floorType: FLOOR_PALETTES.WOODEN.floorType,
    wallColor: FLOOR_PALETTES.WOODEN.wallColor,
    carpetSqft: Math.round(carpet * 0.22),
    furniture: masterFurn,
    defect: seepage
      ? {
          type: "seepage",
          pos: [mX - 2.6, masterY + 1.8, 0.5],
          color: 0xf97316,
          desc: "Capillary moisture ingress verified along north-west party wall",
        }
      : undefined,
    focalTarget: { pos: [mX, masterY + 1.2, 0.5], radius: 11, theta: 0.58, phi: 1.02 },
  });

  // Master Bedroom Walls
  walls.push(
    {
      id: "wall_m_west",
      pos: [mX - 2.9, masterY + ceilingHeight / 2, 0.5],
      size: [0.2, ceilingHeight, 5.4],
      color: wallMatColor,
      floorLevel: masterLevel,
      isExterior: true,
    },
    {
      id: "wall_m_north",
      pos: [mX, masterY + ceilingHeight / 2, -2.2],
      size: [5.8, ceilingHeight, 0.2],
      color: wallMatColor,
      floorLevel: masterLevel,
      isExterior: true,
    },
    {
      id: "wall_m_south",
      pos: [mX, masterY + ceilingHeight / 2, 3.2],
      size: [5.8, ceilingHeight, 0.2],
      color: wallMatColor,
      floorLevel: masterLevel,
      isExterior: true,
    }
  );

  // Master Bedroom Door
  doors.push({
    id: "door_master",
    pos: [-livingW / 2, masterY + 1.1, 0.8],
    size: [0.95, 2.2, 0.12],
    rotationY: Math.PI / 2,
    doorType: "hinged",
    openAngle: 0.45,
    floorLevel: masterLevel,
  });

  // Master Window
  windows.push({
    id: "win_master",
    pos: [mX - 2.9, masterY + 1.5, 0.5],
    size: [3.2, 2.0, 0.16],
    rotationY: Math.PI / 2,
    floorLevel: masterLevel,
  });

  // ==========================================
  // ROOMS 4+: Secondary Bedrooms
  // ==========================================
  if (bhk >= 2) {
    const b2X = Math.round((livingW / 2 + 2.5) * 10) / 10;
    const b2Level = 0;
    const b2Y = 0;
    const b2Furn =
      furnishing === "FULLY_FURNISHED"
        ? [
            {
              id: "b2_bed",
              name: "Queen Designer Bed",
              type: "bed",
              pos: [b2X, b2Y + 0.38, 4.2],
              size: [1.9, 0.42, 2.1],
              color: 0xfafaf6,
            },
          ]
        : [];

    rooms.push({
      id: "bedroom_2",
      name: "Guest Suite (Bedroom 2)",
      category: "GUEST_BEDROOM",
      floorLevel: b2Level,
      bounds: { x: b2X, y: b2Y, z: 4.4, w: 4.8, d: 4.4, h: ceilingHeight },
      floorColor: floorPal.floorColor,
      floorType: floorPal.floorType,
      wallColor: wallMatColor,
      carpetSqft: Math.round(carpet * 0.14),
      furniture: b2Furn,
      focalTarget: { pos: [b2X, b2Y + 1.1, 4.4], radius: 10, theta: 1.1, phi: 0.95 },
    });

    walls.push(
      {
        id: "wall_b2_east",
        pos: [b2X + 2.4, ceilingHeight / 2, 4.4],
        size: [0.2, ceilingHeight, 4.4],
        color: wallMatColor,
        floorLevel: b2Level,
        isExterior: true,
      },
      {
        id: "wall_b2_south",
        pos: [b2X, ceilingHeight / 2, 6.6],
        size: [4.8, ceilingHeight, 0.2],
        color: wallMatColor,
        floorLevel: b2Level,
        isExterior: true,
      }
    );

    doors.push({
      id: "door_b2",
      pos: [livingW / 2, 1.1, 3.4],
      size: [0.95, 2.2, 0.12],
      rotationY: Math.PI / 2,
      doorType: "hinged",
      openAngle: 0.45,
      floorLevel: b2Level,
    });
  }

  if (bhk >= 3) {
    const b3X = Math.round((-livingW / 2 - 2.5) * 10) / 10;
    const b3Level = isVilla ? 1 : 0;
    const b3Y = b3Level * 3.4;
    const b3Furn =
      furnishing === "FULLY_FURNISHED"
        ? [
            {
              id: "b3_bed",
              name: "Queen Bed",
              type: "bed",
              pos: [b3X, b3Y + 0.38, -4.8],
              size: [1.9, 0.42, 2.0],
              color: 0xfafaf6,
            },
          ]
        : [];

    rooms.push({
      id: "bedroom_3",
      name: "Children's Suite (Bedroom 3)",
      category: "GUEST_BEDROOM",
      floorLevel: b3Level,
      bounds: { x: b3X, y: b3Y, z: -4.8, w: 4.8, d: 4.4, h: ceilingHeight },
      floorColor: FLOOR_PALETTES.WOODEN.floorColor,
      floorType: FLOOR_PALETTES.WOODEN.floorType,
      wallColor: FLOOR_PALETTES.WOODEN.wallColor,
      carpetSqft: Math.round(carpet * 0.12),
      furniture: b3Furn,
      focalTarget: { pos: [b3X, b3Y + 1.1, -4.8], radius: 10, theta: 0.45, phi: 0.95 },
    });

    walls.push(
      {
        id: "wall_b3_west",
        pos: [b3X - 2.4, b3Y + ceilingHeight / 2, -4.8],
        size: [0.2, ceilingHeight, 4.4],
        color: wallMatColor,
        floorLevel: b3Level,
        isExterior: true,
      },
      {
        id: "wall_b3_north",
        pos: [b3X, b3Y + ceilingHeight / 2, -7.0],
        size: [4.8, ceilingHeight, 0.2],
        color: wallMatColor,
        floorLevel: b3Level,
        isExterior: true,
      }
    );
  }

  if (bhk >= 4) {
    const b4Level = isVilla ? 2 : 0;
    const b4Y = b4Level * 3.4;
    const b4Furn =
      furnishing === "FULLY_FURNISHED"
        ? [
            {
              id: "b4_bed",
              name: "Queen Garden Bed",
              type: "bed",
              pos: [0, b4Y + 0.38, -5.6],
              size: [1.9, 0.42, 2.0],
              color: 0xfafaf6,
            },
          ]
        : [];

    rooms.push({
      id: "bedroom_4",
      name: "Sky Garden Suite (Bedroom 4)",
      category: "GUEST_BEDROOM",
      floorLevel: b4Level,
      bounds: { x: 0, y: b4Y, z: -5.6, w: 4.8, d: 4.2, h: ceilingHeight },
      floorColor: floorPal.floorColor,
      floorType: floorPal.floorType,
      wallColor: wallMatColor,
      carpetSqft: Math.round(carpet * 0.11),
      furniture: b4Furn,
      focalTarget: { pos: [0, b4Y + 1.1, -5.6], radius: 10, theta: 0.68, phi: 1.0 },
    });
  }

  if (bhk >= 5) {
    const b5Level = isVilla ? 2 : 0;
    const b5Y = b5Level * 3.4;
    const b5Furn =
      furnishing === "FULLY_FURNISHED"
        ? [
            {
              id: "b5_desk",
              name: "Executive Teak Library Suite",
              type: "table",
              pos: [5.2, b5Y + 0.45, -5.0],
              size: [1.8, 0.78, 0.9],
              color: 0xa87042,
            },
          ]
        : [];

    rooms.push({
      id: "bedroom_5",
      name: "Executive Library Suite (Bedroom 5)",
      category: "GUEST_BEDROOM",
      floorLevel: b5Level,
      bounds: { x: 5.2, y: b5Y, z: -5.6, w: 4.6, d: 4.0, h: ceilingHeight },
      floorColor: FLOOR_PALETTES.WOODEN.floorColor,
      floorType: FLOOR_PALETTES.WOODEN.floorType,
      wallColor: FLOOR_PALETTES.WOODEN.wallColor,
      carpetSqft: Math.round(carpet * 0.09),
      furniture: b5Furn,
      focalTarget: { pos: [5.2, b5Y + 1.1, -5.6], radius: 10, theta: 0.85, phi: 1.0 },
    });
  }

  // ==========================================
  // BALCONY / SKY DECK / JACUZZI / LAP POOL
  // ==========================================
  const balcW = Math.round(livingW * 0.72 * 10) / 10;
  const balcD = 3.6;
  const balcZ = Math.round((livingD / 2 + balcD / 2) * 10) / 10;
  const balcLevel = 0;
  const balcFurn: any[] = [];

  if (furnishing === "FULLY_FURNISHED") {
    balcFurn.push({
      id: "balc_lounge",
      name: "Weatherproof Teak Loveseat",
      type: "chair",
      pos: [1.6, 0.38, balcZ],
      size: [1.8, 0.42, 0.85],
      color: 0xa87042,
    });
  }

  rooms.push({
    id: "balcony",
    name: isPenthouse
      ? "Wrap-Around Sky Deck & Jacuzzi"
      : "Covered Panoramic Sky Balcony",
    category: "BALCONY",
    floorLevel: balcLevel,
    bounds: { x: 1.2, y: 0, z: balcZ, w: balcW, d: balcD, h: 0.25 },
    floorColor: 0xa87042,
    floorType: "Weatherproof Teak Composite Deck",
    wallColor: wallMatColor,
    carpetSqft: Math.round(carpet * 0.1),
    furniture: balcFurn,
    focalTarget: { pos: [1.2, 0.8, balcZ], radius: 9, theta: 0.82, phi: 0.95 },
  });

  // Balcony Safety Glass Balustrades with Handrails
  balconies.push({
    id: "balcony_railing",
    pos: [1.2, 0, balcZ],
    size: [balcW, 1.1, balcD],
    floorLevel: balcLevel,
    railings: [
      { pos: [1.2, 0.55, balcZ + balcD / 2], size: [balcW, 1.1], rotationY: 0 },
      {
        pos: [1.2 + balcW / 2, 0.55, balcZ],
        size: [balcD, 1.1],
        rotationY: Math.PI / 2,
      },
      {
        pos: [1.2 - balcW / 2, 0.55, balcZ],
        size: [balcD, 1.1],
        rotationY: Math.PI / 2,
      },
    ],
  });

  // Sliding Glass Doors connecting Living to Balcony
  doors.push({
    id: "door_balcony_slider",
    pos: [1.2, 1.2, livingD / 2],
    size: [3.2, 2.4, 0.12],
    rotationY: 0,
    doorType: "sliding",
    openAngle: 0.8,
    floorLevel: 0,
  });

  // Heated Sky Jacuzzi (Penthouse / Sea view)
  if (isPenthouse || views.includes("SEA") || views.includes("POOL")) {
    waters.push({
      id: "sky_jacuzzi",
      name: isVilla ? "Sunken Azure Lap Pool" : "Heated Infinity Sky Jacuzzi",
      pos: [-1.4, 0.35, balcZ],
      size: [2.4, 0.5, 2.0],
      floorLevel: 0,
      type: isVilla ? "pool" : "jacuzzi",
    });
  }

  // ==========================================
  // WAYPOINTS FOR CINEMATIC AUTO-TOUR
  // ==========================================
  waypoints.push(
    { pos: [0, 1.65, 3.6], look: [0, 1.2, 0], label: "Grand Living & Dining Pavilion" },
    {
      pos: [kitX - 1.0, 1.65, -0.4],
      look: [kitX, 1.1, -0.8],
      label: "Siemens Integrated Culinary Studio",
    },
    {
      pos: [mX + 1.2, masterY + 1.65, 0.5],
      look: [mX, masterY + 1.1, 0.5],
      label: "Presidential Master Suite (Bedroom 1)",
    }
  );

  if (seepage) {
    waypoints.push({
      pos: [mX - 1.4, masterY + 1.8, 0.5],
      look: [mX - 2.6, masterY + 1.8, 0.5],
      label: "⚠️ Inspection Defect Pin: Capillary Seepage Moisture",
    });
  }

  waypoints.push({
    pos: [1.2, 1.65, balcZ - 1.2],
    look: [1.2, 0.8, balcZ + 1.2],
    label: isPenthouse ? "Wrap-Around Sky Deck & Jacuzzi" : "Covered Panoramic Sky Balcony",
  });

  const sunlight = SUNLIGHT_VECTORS[facing] || SUNLIGHT_VECTORS.EAST;

  return {
    propertyTitle:
      input.title ||
      (rawPrompt ? rawPrompt.split(".")[0].slice(0, 50) : "Sovereign 3D Twin"),
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
    livingToKitchenRatio: (
      Math.round(carpet * 0.33) / Math.max(1, Math.round(carpet * 0.11))
    ).toFixed(2),
    rooms,
    walls,
    doors,
    windows,
    balconies,
    waters,
    waypoints,
  };
}

// ============================================================================
// CLEAN RECURSIVE DISPOSAL HELPER (ZERO GPU LEAKS)
// ============================================================================

function disposeObject3D(obj: THREE.Object3D) {
  obj.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (mesh.isMesh) {
      if (mesh.geometry) mesh.geometry.dispose();
      if (mesh.material) {
        if (Array.isArray(mesh.material)) {
          mesh.material.forEach((m) => m.dispose());
        } else {
          mesh.material.dispose();
        }
      }
    }
  });
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

  // Live Reactive Schema State
  const [activePrompt, setActivePrompt] = useState(prompt);
  const [debouncedPrompt, setDebouncedPrompt] = useState(prompt);
  const [activeBHK, setActiveBHK] = useState(property.bhkCount || 3);
  const [activePropertyType, setActivePropertyType] = useState<PrismaPropertyType>(
    property.propertyType || "APARTMENT"
  );
  const [activeFlooring, setActiveFlooring] = useState<PrismaFlooringType>(
    property.flooring || "ITALIAN_MARBLE"
  );
  const [activeFurnishing, setActiveFurnishing] = useState<PrismaFurnishingStatus>(
    property.furnishing || "FULLY_FURNISHED"
  );
  const [activeFacing, setActiveFacing] = useState<PrismaFacingDirection>(
    property.facing || "EAST"
  );
  const [activeSeepage, setActiveSeepage] = useState(property.seepageDetected || false);
  const [activeCarpet, setActiveCarpet] = useState(property.carpetAreaSqft || 2100);

  // UI Modes & Toggles
  const [mode, setMode] = useState<"orbit" | "walk" | "tour">(initialMode);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [selectedRoomId, setSelectedRoomId] = useState<string>("all");
  const [isCutaway, setIsCutaway] = useState(false);
  const [isStaged, setIsStaged] = useState(true);
  const [activeFloorFilter, setActiveFloorFilter] = useState<number>(-1); // -1 = All Levels
  const [tourBannerText, setTourBannerText] = useState<string>("");

  // Debounce Prompt input to prevent rebuilding Three.js meshes on every keystroke
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedPrompt(activePrompt);
    }, 200);
    return () => clearTimeout(t);
  }, [activePrompt]);

  // Declarative In-Memory Spatial Scene Compiler
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
      debouncedPrompt
    );
  }, [
    property,
    debouncedPrompt,
    activeBHK,
    activePropertyType,
    activeFlooring,
    activeFurnishing,
    activeFacing,
    activeCarpet,
    activeSeepage,
  ]);

  // Three.js References
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const dynamicGroupRef = useRef<THREE.Group | null>(null);
  const stagedGroupRef = useRef<THREE.Group | null>(null);
  const defectGroupRef = useRef<THREE.Group | null>(null);

  // Camera Animation and Navigation State
  const camState = useRef({
    theta: 0.72,
    phi: 1.05,
    radius: 28.0,
    target: new THREE.Vector3(0, 1.4, 0),
    tgtTheta: 0.72,
    tgtPhi: 1.05,
    tgtRadius: 28.0,
    tgtTarget: new THREE.Vector3(0, 1.4, 0),
    walkPos: new THREE.Vector3(0, 1.65, 4.5),
    isDragging: false,
    prevX: 0,
    prevY: 0,
    keys: {} as Record<string, boolean>,
    tourIdx: 0,
    tourT: 0,
  });

  // Sync mode state ref for event handlers
  const modeRef = useRef(mode);
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  const isCutawayRef = useRef(isCutaway);
  useEffect(() => {
    isCutawayRef.current = isCutaway;
  }, [isCutaway]);

  // Initialize Three.js WebGL Viewport
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 550;

    const scene = new THREE.Scene();
    const fogColor = 0xd5cfc4;
    scene.background = new THREE.Color(fogColor);
    scene.fog = new THREE.Fog(fogColor, 45, 140);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 300);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    rendererRef.current = renderer;

    while (container.firstChild) container.removeChild(container.firstChild);
    container.appendChild(renderer.domElement);

    // Architectural Ground Plane & Paved Access Road
    const groundGeo = new THREE.PlaneGeometry(240, 240);
    const groundMat = new THREE.MeshLambertMaterial({ color: 0xc4beaf });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    const roadGeo = new THREE.PlaneGeometry(16, 240);
    const roadMat = new THREE.MeshLambertMaterial({ color: 0xded9cf });
    const road = new THREE.Mesh(roadGeo, roadMat);
    road.rotation.x = -Math.PI / 2;
    road.position.set(0, 0.015, 0);
    road.rotation.z = Math.PI / 2;
    road.receiveShadow = true;
    scene.add(road);

    // Soft Surrounding Landscaping Trees
    const trunkMat = new THREE.MeshLambertMaterial({ color: 0x84745c });
    const leafMat = new THREE.MeshLambertMaterial({ color: 0x8e9c74 });
    for (let t = 0; t < 16; t++) {
      const a = (t / 16) * Math.PI * 2 + 0.1;
      const rad = 24 + (t % 4) * 5;
      const x = Math.cos(a) * rad;
      const z = Math.sin(a) * rad;
      const th = 1.0 + (t % 3) * 0.4;
      const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, th, 6), trunkMat);
      tr.position.set(x, th / 2, z);
      scene.add(tr);
      const cr = new THREE.Mesh(
        new THREE.SphereGeometry(0.85 + (t % 3) * 0.35, 10, 8),
        leafMat
      );
      cr.position.set(x, th + 0.65, z);
      scene.add(cr);
    }

    // Daylight Lighting Rig with Configured Shadow Camera Frustum
    const hemiLight = new THREE.HemisphereLight(0xfff5e6, 0xa39b8d, 0.75);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xffeed6, 1.1);
    sunLight.name = "sunLight";
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(1024, 1024);
    sunLight.shadow.camera.left = -40;
    sunLight.shadow.camera.right = 40;
    sunLight.shadow.camera.top = 40;
    sunLight.shadow.camera.bottom = -40;
    sunLight.shadow.camera.near = 1;
    sunLight.shadow.camera.far = 140;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    // Groups for dynamic geometry, staged furniture, and defects
    const dynamicGroup = new THREE.Group();
    dynamicGroupRef.current = dynamicGroup;
    scene.add(dynamicGroup);

    const stagedGroup = new THREE.Group();
    stagedGroupRef.current = stagedGroup;
    scene.add(stagedGroup);

    const defectGroup = new THREE.Group();
    defectGroupRef.current = defectGroup;
    scene.add(defectGroup);

    // Main 60FPS Animation Loop
    let pulseCounter = 0;
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate);
      const cs = camState.current;
      const curMode = modeRef.current;

      // Defect Pulse Animation
      pulseCounter += 0.05;
      if (defectGroup.children.length > 0) {
        const s = 1.0 + Math.sin(pulseCounter * 2.5) * 0.22;
        defectGroup.children.forEach((c) => {
          if (c.name === "defectRing") {
            c.scale.set(s, s, s);
          }
        });
      }

      // First-Person Walk Mode
      if (curMode === "walk") {
        const walkSpeed = 0.14;
        const forward = new THREE.Vector3();
        camera.getWorldDirection(forward);
        forward.y = 0;
        forward.normalize();

        const right = new THREE.Vector3();
        right.crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

        if (cs.keys["w"] || cs.keys["arrowup"]) {
          cs.tgtTarget.addScaledVector(forward, walkSpeed);
        }
        if (cs.keys["s"] || cs.keys["arrowdown"]) {
          cs.tgtTarget.addScaledVector(forward, -walkSpeed);
        }
        if (cs.keys["a"] || cs.keys["arrowleft"]) {
          cs.tgtTarget.addScaledVector(right, -walkSpeed);
        }
        if (cs.keys["d"] || cs.keys["arrowright"]) {
          cs.tgtTarget.addScaledVector(right, walkSpeed);
        }
      }

      // Cinematic Auto-Tour Mode
      if (curMode === "tour" && spatialScene.waypoints.length > 0) {
        const wps = spatialScene.waypoints;
        cs.tourT += 0.0035;
        if (cs.tourT >= 1.0) {
          cs.tourT = 0;
          cs.tourIdx = (cs.tourIdx + 1) % wps.length;
          setTourBannerText(wps[cs.tourIdx].label || "Cinematic Fly-through");
        }

        const currWp = wps[cs.tourIdx] || wps[0];
        const nextWp = wps[(cs.tourIdx + 1) % wps.length] || wps[0];

        const factor = (1 - Math.cos(cs.tourT * Math.PI)) / 2;
        const px = currWp.pos[0] + (nextWp.pos[0] - currWp.pos[0]) * factor;
        const py = currWp.pos[1] + (nextWp.pos[1] - currWp.pos[1]) * factor;
        const pz = currWp.pos[2] + (nextWp.pos[2] - currWp.pos[2]) * factor;

        const lx = currWp.look[0] + (nextWp.look[0] - currWp.look[0]) * factor;
        const ly = currWp.look[1] + (nextWp.look[1] - currWp.look[1]) * factor;
        const lz = currWp.look[2] + (nextWp.look[2] - currWp.look[2]) * factor;

        camera.position.set(px, py, pz);
        camera.lookAt(lx, ly, lz);
      } else {
        // Smooth Spherical Damping for Orbit / Walk
        cs.theta += (cs.tgtTheta - cs.theta) * 0.08;
        cs.phi += (cs.tgtPhi - cs.phi) * 0.08;
        cs.radius += (cs.tgtRadius - cs.radius) * 0.08;
        cs.target.lerp(cs.tgtTarget, 0.08);

        const x = cs.target.x + cs.radius * Math.sin(cs.phi) * Math.sin(cs.theta);
        const y = cs.target.y + cs.radius * Math.cos(cs.phi);
        const z = cs.target.z + cs.radius * Math.sin(cs.phi) * Math.cos(cs.theta);

        camera.position.set(x, y, z);
        camera.lookAt(cs.target);
      }

      renderer.render(scene, camera);
    };
    animate();

    // Window Resize Handler
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
      if (modeRef.current === "tour") return;
      camState.current.isDragging = true;
      camState.current.prevX = e.clientX;
      camState.current.prevY = e.clientY;
    };
    const handleMouseMove = (e: MouseEvent) => {
      if (!camState.current.isDragging || modeRef.current === "tour") return;
      const dx = e.clientX - camState.current.prevX;
      const dy = e.clientY - camState.current.prevY;
      camState.current.prevX = e.clientX;
      camState.current.prevY = e.clientY;

      if (isCutawayRef.current) {
        camState.current.tgtTarget.x -= dx * 0.04;
        camState.current.tgtTarget.z -= dy * 0.04;
      } else {
        camState.current.tgtTheta -= dx * 0.007;
        camState.current.tgtPhi = Math.max(
          0.12,
          Math.min(Math.PI / 2 - 0.05, camState.current.tgtPhi - dy * 0.006)
        );
      }
    };
    const handleMouseUp = () => {
      camState.current.isDragging = false;
    };
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (modeRef.current === "tour") return;
      camState.current.tgtRadius = Math.max(
        6.0,
        Math.min(55.0, camState.current.tgtRadius + e.deltaY * 0.03)
      );
    };

    // Keyboard controls for Walk Mode
    const handleKeyDown = (e: KeyboardEvent) => {
      camState.current.keys[e.key.toLowerCase()] = true;
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      camState.current.keys[e.key.toLowerCase()] = false;
    };

    // Touch Controls for Mobile/Tablet
    let touchStartDist = 0;
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        camState.current.isDragging = true;
        camState.current.prevX = e.touches[0].clientX;
        camState.current.prevY = e.touches[0].clientY;
      } else if (e.touches.length === 2) {
        touchStartDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    };
    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 1 && camState.current.isDragging) {
        const dx = e.touches[0].clientX - camState.current.prevX;
        const dy = e.touches[0].clientY - camState.current.prevY;
        camState.current.prevX = e.touches[0].clientX;
        camState.current.prevY = e.touches[0].clientY;
        camState.current.tgtTheta -= dx * 0.008;
        camState.current.tgtPhi = Math.max(
          0.12,
          Math.min(Math.PI / 2 - 0.05, camState.current.tgtPhi - dy * 0.008)
        );
      } else if (e.touches.length === 2) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const factor = (touchStartDist - dist) * 0.05;
        camState.current.tgtRadius = Math.max(
          6.0,
          Math.min(55.0, camState.current.tgtRadius + factor)
        );
        touchStartDist = dist;
      }
    };
    const handleTouchEnd = () => {
      camState.current.isDragging = false;
    };

    container.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    container.addEventListener("wheel", handleWheel, { passive: false });
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    container.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchmove", handleTouchMove, { passive: true });
    window.addEventListener("touchend", handleTouchEnd);

    // Complete Unmount Cleanup
    return () => {
      window.removeEventListener("resize", handleResize);
      container.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      container.removeEventListener("wheel", handleWheel);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      container.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);

      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      disposeObject3D(scene);
      renderer.dispose();
    };
  }, []);

  // Update Three.js Procedural Meshes Declaratively (Zero-Disk I/O)
  useEffect(() => {
    const dynamicGroup = dynamicGroupRef.current;
    const stagedGroup = stagedGroupRef.current;
    const defectGroup = defectGroupRef.current;
    const scene = sceneRef.current;
    if (!dynamicGroup || !stagedGroup || !defectGroup || !scene) return;

    // Clean previous geometries and materials with recursive disposal
    disposeObject3D(dynamicGroup);
    while (dynamicGroup.children.length > 0) dynamicGroup.remove(dynamicGroup.children[0]);

    disposeObject3D(stagedGroup);
    while (stagedGroup.children.length > 0) stagedGroup.remove(stagedGroup.children[0]);

    disposeObject3D(defectGroup);
    while (defectGroup.children.length > 0) defectGroup.remove(defectGroup.children[0]);

    // 1. Update Directional Sun Light based on Facing Direction
    const sunLight = scene.getObjectByName("sunLight") as THREE.DirectionalLight;
    if (sunLight) {
      sunLight.color.setHex(spatialScene.sunlight.color);
      sunLight.position.set(...spatialScene.sunlight.pos);
    }

    // Material Library
    const M = {
      slab: new THREE.MeshLambertMaterial({ color: 0x2b2e35 }),
      wallMat: new THREE.MeshLambertMaterial({ color: 0xfaf8f5 }),
      wallExterior: new THREE.MeshLambertMaterial({ color: 0xe7e3da }),
      skirtMat: new THREE.MeshLambertMaterial({ color: 0x44403c }),
      frameMat: new THREE.MeshLambertMaterial({ color: 0x1f1d1a }),
      doorLeaf: new THREE.MeshLambertMaterial({ color: 0xa87042 }),
      brassHandle: new THREE.MeshLambertMaterial({ color: 0xd4af37 }),
      glass: new THREE.MeshPhongMaterial({
        color: 0x1e242b,
        transparent: true,
        opacity: 0.38,
        shininess: 95,
      }),
      balustradeRail: new THREE.MeshLambertMaterial({ color: 0x64748b }),
      water: new THREE.MeshPhongMaterial({
        color: 0x0f2b36,
        transparent: true,
        opacity: 0.85,
        shininess: 120,
      }),
    };

    // 2. Foundation Slab
    let minX = Infinity,
      maxX = -Infinity,
      minZ = Infinity,
      maxZ = -Infinity;
    spatialScene.rooms.forEach((r) => {
      const b = r.bounds;
      minX = Math.min(minX, b.x - b.w / 2);
      maxX = Math.max(maxX, b.x + b.w / 2);
      minZ = Math.min(minZ, b.z - b.d / 2);
      maxZ = Math.max(maxZ, b.z + b.d / 2);
    });
    const totalW = Math.max(22, maxX - minX + 3.5);
    const totalD = Math.max(16, maxZ - minZ + 3.5);
    const centerX = (minX + maxX) / 2;
    const centerZ = (minZ + maxZ) / 2;

    const foundationMesh = new THREE.Mesh(
      new THREE.BoxGeometry(totalW, 0.35, totalD),
      M.slab
    );
    foundationMesh.position.set(centerX, 0.175, centerZ);
    foundationMesh.receiveShadow = true;
    dynamicGroup.add(foundationMesh);

    // 3. Room Floors, Baseboards, Furniture & Lights
    spatialScene.rooms.forEach((room) => {
      if (activeFloorFilter !== -1 && room.floorLevel !== activeFloorFilter) return;
      const b = room.bounds;

      // Floor Slab
      const floorMat = new THREE.MeshLambertMaterial({ color: room.floorColor });
      const floorMesh = new THREE.Mesh(new THREE.BoxGeometry(b.w, 0.22, b.d), floorMat);
      floorMesh.position.set(b.x, b.y + 0.11, b.z);
      floorMesh.receiveShadow = true;
      dynamicGroup.add(floorMesh);

      // Baseboard Skirting
      const skirtH = 0.08,
        skirtT = 0.04;
      const sk1 = new THREE.Mesh(new THREE.BoxGeometry(b.w, skirtH, skirtT), M.skirtMat);
      sk1.position.set(b.x, b.y + 0.22 + skirtH / 2, b.z - b.d / 2 + skirtT / 2);
      dynamicGroup.add(sk1);

      // Furniture (Added to stagedGroup so it can be toggled on/off)
      room.furniture.forEach((f) => {
        const fMat = new THREE.MeshLambertMaterial({ color: f.color });
        const fMesh = new THREE.Mesh(new THREE.BoxGeometry(...f.size), fMat);
        fMesh.position.set(...f.pos);
        if (f.rotationY) fMesh.rotation.y = f.rotationY;
        fMesh.castShadow = true;
        fMesh.receiveShadow = true;
        stagedGroup.add(fMesh);
      });

      // Warm Interior Ambient Light
      const pLight = new THREE.PointLight(0xfff2de, 0.65, 12);
      pLight.position.set(b.x, b.y + b.h - 0.4, b.z);
      dynamicGroup.add(pLight);

      // Inspection Defect Pin
      if (room.defect) {
        const def = room.defect;
        const pinMesh = new THREE.Mesh(
          new THREE.SphereGeometry(0.18, 16, 16),
          new THREE.MeshBasicMaterial({ color: def.color })
        );
        pinMesh.position.set(...def.pos);
        defectGroup.add(pinMesh);

        const ringMesh = new THREE.Mesh(
          new THREE.RingGeometry(0.24, 0.38, 24),
          new THREE.MeshBasicMaterial({
            color: def.color,
            wireframe: true,
            side: THREE.DoubleSide,
          })
        );
        ringMesh.name = "defectRing";
        ringMesh.position.set(...def.pos);
        ringMesh.rotation.y = Math.PI / 2;
        defectGroup.add(ringMesh);
      }
    });

    // 4. Structural BIM Walls (Adjust height in Cutaway Mode)
    const wallH = isCutaway ? 0.85 : spatialScene.ceilingHeight;
    spatialScene.walls.forEach((w) => {
      if (activeFloorFilter !== -1 && w.floorLevel !== activeFloorFilter) return;
      const [sx, , sz] = w.size;
      const [px, , pz] = w.pos;
      const mat = w.isExterior ? M.wallExterior : M.wallMat;
      const wallMesh = new THREE.Mesh(new THREE.BoxGeometry(sx, wallH, sz), mat);
      wallMesh.position.set(px, w.floorLevel * 3.4 + wallH / 2, pz);
      wallMesh.castShadow = true;
      wallMesh.receiveShadow = true;
      dynamicGroup.add(wallMesh);
    });

    // 5. Engineered Doors (Hinged & Sliding Glass)
    spatialScene.doors.forEach((d) => {
      if (activeFloorFilter !== -1 && d.floorLevel !== activeFloorFilter) return;
      if (isCutaway) return; // Hide tall door frames in cutaway top-down view
      const [dw, dh, dd] = d.size;
      const [dx, dy, dz] = d.pos;

      const doorGrp = new THREE.Group();
      doorGrp.position.set(dx, dy, dz);
      doorGrp.rotation.y = d.rotationY;

      // Frame
      const f1 = new THREE.Mesh(new THREE.BoxGeometry(dw, 0.08, dd), M.frameMat);
      f1.position.set(0, dh / 2 - 0.04, 0);
      doorGrp.add(f1);

      if (d.doorType === "sliding") {
        const pw = dw / 2 - 0.04;
        const g1 = new THREE.Mesh(new THREE.PlaneGeometry(pw, dh - 0.16), M.glass);
        g1.position.set(-dw / 4, 0, -0.02);
        doorGrp.add(g1);
        const g2 = new THREE.Mesh(new THREE.PlaneGeometry(pw, dh - 0.16), M.glass);
        g2.position.set(dw / 4, 0, 0.02);
        doorGrp.add(g2);
      } else {
        const leafW = dw - 0.12;
        const leafGrp = new THREE.Group();
        leafGrp.position.set(-dw / 2 + 0.06, 0, 0);
        leafGrp.rotation.y = d.openAngle || 0.45;

        const leafMesh = new THREE.Mesh(
          new THREE.BoxGeometry(leafW, dh - 0.08, 0.04),
          M.doorLeaf
        );
        leafMesh.position.set(leafW / 2, 0, 0);
        leafGrp.add(leafMesh);

        const handle = new THREE.Mesh(
          new THREE.CylinderGeometry(0.015, 0.015, 0.12, 8),
          M.brassHandle
        );
        handle.rotation.z = Math.PI / 2;
        handle.position.set(leafW - 0.1, 0, 0.04);
        leafGrp.add(handle);

        doorGrp.add(leafGrp);
      }
      dynamicGroup.add(doorGrp);
    });

    // 6. Double-Glazed Acoustic Windows
    spatialScene.windows.forEach((win) => {
      if (activeFloorFilter !== -1 && win.floorLevel !== activeFloorFilter) return;
      if (isCutaway) return;
      const [ww, wh, wd] = win.size;
      const [wx, wy, wz] = win.pos;

      const winGrp = new THREE.Group();
      winGrp.position.set(wx, wy, wz);
      winGrp.rotation.y = win.rotationY;

      const fTop = new THREE.Mesh(new THREE.BoxGeometry(ww, 0.08, wd), M.frameMat);
      fTop.position.set(0, wh / 2 - 0.04, 0);
      winGrp.add(fTop);
      const fBot = new THREE.Mesh(new THREE.BoxGeometry(ww, 0.08, wd), M.frameMat);
      fBot.position.set(0, -wh / 2 + 0.04, 0);
      winGrp.add(fBot);

      const glassPane = new THREE.Mesh(new THREE.PlaneGeometry(ww - 0.1, wh - 0.16), M.glass);
      winGrp.add(glassPane);

      dynamicGroup.add(winGrp);
    });

    // 7. Balconies with Safety Glass Balustrades & Metallic Handrails
    spatialScene.balconies.forEach((balc) => {
      if (activeFloorFilter !== -1 && balc.floorLevel !== activeFloorFilter) return;
      balc.railings.forEach((r) => {
        const [rw, rh] = r.size;
        const [rx, ry, rz] = r.pos;

        const railGrp = new THREE.Group();
        railGrp.position.set(rx, ry, rz);
        railGrp.rotation.y = r.rotationY;

        // Frameless Glass Balustrade
        const glassMesh = new THREE.Mesh(new THREE.PlaneGeometry(rw, rh), M.glass);
        railGrp.add(glassMesh);

        // Metallic Top Handrail
        const handrail = new THREE.Mesh(
          new THREE.BoxGeometry(rw, 0.06, 0.08),
          M.balustradeRail
        );
        handrail.position.set(0, rh / 2 - 0.03, 0);
        railGrp.add(handrail);

        dynamicGroup.add(railGrp);
      });
    });

    // 8. Water Features (Sky Jacuzzi / Sunken Lap Pool)
    spatialScene.waters.forEach((wat) => {
      if (activeFloorFilter !== -1 && wat.floorLevel !== activeFloorFilter) return;
      const [ww, wh, wd] = wat.size;
      const [wx, wy, wz] = wat.pos;

      const waterMesh = new THREE.Mesh(new THREE.BoxGeometry(ww, wh, wd), M.water);
      waterMesh.position.set(wx, wy, wz);
      dynamicGroup.add(waterMesh);
    });
  }, [spatialScene, isCutaway, activeFloorFilter]);

  // Sync Staged Furniture Visibility
  useEffect(() => {
    if (stagedGroupRef.current) {
      stagedGroupRef.current.visible = isStaged;
    }
  }, [isStaged]);

  // Handle Room Selection Focus
  const handleSelectRoom = (roomId: string) => {
    setSelectedRoomId(roomId);
    if (roomId === "all") {
      camState.current.tgtTarget.set(0, 1.4, 0);
      camState.current.tgtRadius = isCutaway ? 36.0 : 28.0;
    } else {
      const rm = spatialScene.rooms.find((r) => r.id === roomId);
      if (rm) {
        camState.current.tgtTarget.set(
          rm.focalTarget.pos[0],
          rm.focalTarget.pos[1],
          rm.focalTarget.pos[2]
        );
        camState.current.tgtRadius = rm.focalTarget.radius;
        camState.current.tgtTheta = rm.focalTarget.theta;
        camState.current.tgtPhi = rm.focalTarget.phi;
      }
    }
  };

  // Toggle Cutaway Top-Down View
  const toggleCutaway = () => {
    const next = !isCutaway;
    setIsCutaway(next);
    if (next) {
      camState.current.tgtPhi = 0.15;
      camState.current.tgtRadius = 38.0;
    } else {
      camState.current.tgtPhi = 1.05;
      camState.current.tgtRadius = 28.0;
    }
  };

  return (
    <div
      className={`relative w-full h-[650px] rounded-2xl overflow-hidden bg-stone-950 border border-stone-800 flex flex-col font-sans select-none ${className}`}
    >
      {/* Top Bar Header */}
      <header className="h-14 border-b border-stone-800 bg-stone-900/90 backdrop-blur-md px-4 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-black text-xs shadow-inner">
            3D
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-white tracking-tight">
                {spatialScene.propertyTitle}
              </h2>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Zero-File RAM Twin
              </span>
            </div>
            <p className="text-[11px] text-stone-400">
              {spatialScene.configuration} · {spatialScene.carpetSqft.toLocaleString()} sq.ft ·{" "}
              {spatialScene.flooring.replace(/_/g, " ")} · {spatialScene.sunlight.label}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Mode Switcher: Orbit / Walk / Tour */}
          <div className="flex items-center bg-stone-950/80 border border-stone-700/80 rounded-xl p-0.5 text-xs">
            <button
              onClick={() => setMode("orbit")}
              className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                mode === "orbit"
                  ? "bg-amber-500 text-stone-950 font-bold"
                  : "text-stone-300 hover:text-white"
              }`}
            >
              🌐 Orbit
            </button>
            <button
              onClick={() => setMode("walk")}
              className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                mode === "walk"
                  ? "bg-amber-500 text-stone-950 font-bold"
                  : "text-stone-300 hover:text-white"
              }`}
            >
              🚶 Walk
            </button>
            <button
              onClick={() => {
                setMode("tour");
                camState.current.tourIdx = 0;
                camState.current.tourT = 0;
              }}
              className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                mode === "tour"
                  ? "bg-amber-500 text-stone-950 font-bold"
                  : "text-stone-300 hover:text-white"
              }`}
            >
              🎬 Auto-Tour
            </button>
          </div>

          {/* Staging Toggle */}
          <button
            onClick={() => setIsStaged(!isStaged)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isStaged
                ? "bg-stone-800/80 border-stone-700 text-amber-300"
                : "bg-stone-950 border-stone-800 text-stone-400"
            }`}
          >
            {isStaged ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
            <span>{isStaged ? "Furnished" : "Bare Shell"}</span>
          </button>

          {/* Cutaway Plan Toggle */}
          <button
            onClick={toggleCutaway}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isCutaway
                ? "bg-amber-500/20 border-amber-500 text-amber-300"
                : "bg-stone-800/80 border-stone-700 text-stone-300 hover:text-white"
            }`}
          >
            <Grid className="h-3.5 w-3.5" />
            <span>{isCutaway ? "📐 Perspective" : "📐 Cutaway Plan"}</span>
          </button>

          {/* Mould Schema Drawer Trigger */}
          <button
            onClick={() => setIsDrawerOpen(!isDrawerOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-500 text-stone-950 hover:bg-amber-400 transition-all shadow-md shadow-amber-500/20"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>Mould Schema Live</span>
          </button>
        </div>
      </header>

      {/* Main 3D Viewport */}
      <div className="flex-1 relative overflow-hidden">
        <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* Multi-Floor Level Filter (For Multi-Level Villas) */}
        {spatialScene.levelsCount > 1 && (
          <div className="absolute top-4 left-4 z-10">
            <div className="flex items-center rounded-xl bg-stone-900/90 p-1 border border-stone-700/80 backdrop-blur-md shadow-xl text-xs gap-1">
              <span className="text-[10px] uppercase font-semibold text-stone-400 px-2">
                Floor:
              </span>
              <button
                onClick={() => setActiveFloorFilter(-1)}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all ${
                  activeFloorFilter === -1
                    ? "bg-amber-500 text-stone-950"
                    : "text-stone-300 hover:text-white"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setActiveFloorFilter(0)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                  activeFloorFilter === 0
                    ? "bg-amber-500 text-stone-950 font-bold"
                    : "text-stone-300 hover:text-white"
                }`}
              >
                Ground
              </button>
              <button
                onClick={() => setActiveFloorFilter(1)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                  activeFloorFilter === 1
                    ? "bg-amber-500 text-stone-950 font-bold"
                    : "text-stone-300 hover:text-white"
                }`}
              >
                1st Floor
              </button>
              {spatialScene.levelsCount >= 3 && (
                <button
                  onClick={() => setActiveFloorFilter(2)}
                  className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                    activeFloorFilter === 2
                      ? "bg-amber-500 text-stone-950 font-bold"
                      : "text-stone-300 hover:text-white"
                  }`}
                >
                  2nd Floor
                </button>
              )}
            </div>
          </div>
        )}

        {/* Live Defect Alert Toast if Seepage Detected */}
        {spatialScene.seepageDetected && (
          <div
            className={`absolute ${
              spatialScene.levelsCount > 1 ? "top-16" : "top-4"
            } left-4 z-10`}
          >
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-950/90 border border-amber-500/50 text-amber-300 text-xs font-medium backdrop-blur-md shadow-xl animate-pulse">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span>Inspection Defect Pin active in Master Suite</span>
            </div>
          </div>
        )}

        {/* Walk Mode Instructions Badge */}
        {mode === "walk" && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
            <div className="px-4 py-2 rounded-xl bg-black/85 border border-stone-700 text-stone-200 text-xs shadow-xl backdrop-blur-md flex items-center gap-2.5">
              <span>
                🎮 <strong>W / A / S / D</strong> or <strong>Arrow Keys</strong> to walk
              </span>
              <span>·</span>
              <span>
                <strong>Click + Drag</strong> to look around
              </span>
            </div>
          </div>
        )}

        {/* Tour Banner Overlay */}
        {mode === "tour" && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-black/85 border border-amber-500/40 text-amber-300 font-semibold text-xs shadow-2xl backdrop-blur-md">
              <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping" />
              <span>
                {tourBannerText || spatialScene.waypoints[0]?.label || "Touring residence..."}
              </span>
            </div>
          </div>
        )}

        {/* Bottom Room Selector Pills */}
        <div className="absolute bottom-4 left-4 right-4 z-10 pointer-events-none">
          <div className="pointer-events-auto flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
            <button
              onClick={() => handleSelectRoom("all")}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all border ${
                selectedRoomId === "all"
                  ? "bg-amber-500 text-stone-950 border-amber-400 shadow-lg"
                  : "bg-stone-900/80 text-stone-300 border-stone-800 hover:bg-stone-800"
              }`}
            >
              Full Residence
            </button>
            {spatialScene.rooms.map((r) => (
              <button
                key={r.id}
                onClick={() => handleSelectRoom(r.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all border ${
                  selectedRoomId === r.id
                    ? "bg-amber-500 text-stone-950 font-bold border-amber-400 shadow-lg"
                    : "bg-stone-900/80 text-stone-300 border-stone-800 hover:bg-stone-800"
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
            <span>Declarative Schema BIM</span>
            <span className="text-emerald-400 font-mono">0.2ms · RAM</span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Living : Kitchen Ratio:</span>
            <span className="font-bold text-amber-300">
              {spatialScene.livingToKitchenRatio} : 1
            </span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Flooring Finish:</span>
            <span className="font-semibold text-stone-200">
              {spatialScene.flooring.replace(/_/g, " ")}
            </span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Interior Staging:</span>
            <span className="font-semibold text-stone-200">
              {spatialScene.furnishing.replace(/_/g, " ")}
            </span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Sun Orientation:</span>
            <span className="font-semibold text-stone-200">{spatialScene.facing}</span>
          </div>
          <div className="flex justify-between text-stone-300">
            <span className="text-stone-400">Architecture Level:</span>
            <span className="font-semibold text-stone-200">
              {spatialScene.levelsCount} Level{spatialScene.levelsCount > 1 ? "s" : ""}
            </span>
          </div>
        </div>

        {/* Interactive Live Schema Moulding Drawer (Side Panel) */}
        {showSchemaController && isDrawerOpen && (
          <aside className="absolute right-0 top-0 bottom-0 w-84 bg-stone-900/98 border-l border-stone-800 shadow-2xl backdrop-blur-2xl z-30 p-4 overflow-y-auto space-y-3.5 text-xs animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-stone-800">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-400" />
                <h3 className="font-bold uppercase tracking-wider text-white text-xs">
                  Mould 3D Space from DB
                </h3>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="text-stone-400 hover:text-white text-sm px-1.5 py-0.5 rounded hover:bg-stone-800"
              >
                ✕
              </button>
            </div>

            {/* Prompt Input Box */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-stone-300 block">
                Raw Database Prompt / Description
              </label>
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
              <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wide">
                Prisma Schema Controls
              </div>

              {/* Property Type */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">
                  Property Type
                </label>
                <select
                  value={activePropertyType}
                  onChange={(e) =>
                    setActivePropertyType(e.target.value as PrismaPropertyType)
                  }
                  className="w-full bg-stone-950 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200"
                >
                  <option value="APARTMENT">APARTMENT</option>
                  <option value="PENTHOUSE">
                    PENTHOUSE (High Ceiling + Sky Jacuzzi)
                  </option>
                  <option value="VILLA">VILLA (Independent Multi-Floor G+2)</option>
                  <option value="BUILDER_FLOOR">BUILDER_FLOOR</option>
                </select>
              </div>

              {/* Configuration (BHK) */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">
                  Configuration (Bedrooms)
                </label>
                <div className="grid grid-cols-5 gap-1">
                  {[1, 2, 3, 4, 5].map((num) => (
                    <button
                      key={num}
                      onClick={() => setActiveBHK(num)}
                      className={`py-1 rounded-lg font-bold text-xs border ${
                        activeBHK === num
                          ? "bg-amber-500 text-stone-950 border-amber-400"
                          : "bg-stone-950 text-stone-300 border-stone-800 hover:bg-stone-800"
                      }`}
                    >
                      {num} BHK
                    </button>
                  ))}
                </div>
              </div>

              {/* Flooring Type */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">
                  Flooring Finish (FlooringType)
                </label>
                <select
                  value={activeFlooring}
                  onChange={(e) =>
                    setActiveFlooring(e.target.value as PrismaFlooringType)
                  }
                  className="w-full bg-stone-950 border border-stone-800 rounded-lg p-1.5 text-xs text-stone-200"
                >
                  <option value="ITALIAN_MARBLE">
                    ITALIAN_MARBLE (Statuario Cream)
                  </option>
                  <option value="MARBLE">MARBLE (Thassos White)</option>
                  <option value="WOODEN">WOODEN (German Oak Planks)</option>
                  <option value="GRANITE">GRANITE (Honed Nero Quartzite)</option>
                  <option value="VITRIFIED_TILES">
                    VITRIFIED_TILES (Matte 1200x600)
                  </option>
                  <option value="CONCRETE">CONCRETE (Industrial Screed)</option>
                </select>
              </div>

              {/* Furnishing Status */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">
                  Furnishing Status (FurnishingStatus)
                </label>
                <div className="grid grid-cols-3 gap-1">
                  {(
                    ["UNFURNISHED", "SEMI_FURNISHED", "FULLY_FURNISHED"] as PrismaFurnishingStatus[]
                  ).map((st) => (
                    <button
                      key={st}
                      onClick={() => setActiveFurnishing(st)}
                      className={`py-1 px-1 rounded-lg text-[10px] font-semibold border truncate ${
                        activeFurnishing === st
                          ? "bg-amber-500 text-stone-950 border-amber-400"
                          : "bg-stone-950 text-stone-300 border-stone-800 hover:bg-stone-800"
                      }`}
                    >
                      {st === "UNFURNISHED"
                        ? "Bare Shell"
                        : st === "SEMI_FURNISHED"
                        ? "Semi"
                        : "Turnkey"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Facing Direction */}
              <div>
                <label className="text-[10px] text-stone-400 block mb-1">
                  Facing Direction (FacingDirection)
                </label>
                <select
                  value={activeFacing}
                  onChange={(e) =>
                    setActiveFacing(e.target.value as PrismaFacingDirection)
                  }
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
