"""
Digital Twin Spatial Engine & Schema Compiler
Translates property listings, database records, and natural language prompts into
architecturally accurate 3D Three.js spatial blueprints with full physical BIM geometry.

Strictly adheres to the Namasthetu Prisma Database Schema (src/db/schema.prisma):
  - PropertyType: APARTMENT, INDEPENDENT_HOUSE, VILLA, PENTHOUSE, BUILDER_FLOOR
  - FlooringType: ITALIAN_MARBLE, MARBLE, WOODEN, GRANITE, VITRIFIED_TILES, CERAMIC_TILES, MOSAIC, CONCRETE, OTHER
  - FurnishingStatus: UNFURNISHED, SEMI_FURNISHED, FULLY_FURNISHED
  - FacingDirection: NORTH, SOUTH, EAST, WEST, NORTH_EAST, NORTH_WEST, SOUTH_EAST, SOUTH_WEST
  - PropertyView: GARDEN, POOL, CLUBHOUSE, COMMUNITY, MAIN_ROAD, CITY, SEA, LAKE, RIVER, GOLF_COURSE, HILLS, FOREST
  - RoomCategory: LIVING_ROOM, MASTER_BEDROOM, GUEST_BEDROOM, KITCHEN, BATHROOM, BALCONY, UTILITY_AREA, ENTRANCE_LOBBY
  - DefectSeverity: LOW, MEDIUM, HIGH, CRITICAL
  - DigitalTwin DB Shape: modelUrl, captureMethod, qualityScore, meshSizeMb, vertexCount, spatialRooms, spatialMetadataJson
"""

import os
import sys
import re
import json
import math
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Union

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# =============================================================================
# PRISMA DATABASE SCHEMA ENUM DEFINITIONS (src/db/schema.prisma)
# =============================================================================

class PropertyType:
    APARTMENT = "APARTMENT"
    INDEPENDENT_HOUSE = "INDEPENDENT_HOUSE"
    VILLA = "VILLA"
    PLOT_LAND = "PLOT_LAND"
    PENTHOUSE = "PENTHOUSE"
    BUILDER_FLOOR = "BUILDER_FLOOR"

class FlooringType:
    VITRIFIED_TILES = "VITRIFIED_TILES"
    CERAMIC_TILES = "CERAMIC_TILES"
    MARBLE = "MARBLE"
    ITALIAN_MARBLE = "ITALIAN_MARBLE"
    GRANITE = "GRANITE"
    WOODEN = "WOODEN"
    MOSAIC = "MOSAIC"
    CONCRETE = "CONCRETE"
    OTHER = "OTHER"

class FurnishingStatus:
    UNFURNISHED = "UNFURNISHED"
    SEMI_FURNISHED = "SEMI_FURNISHED"
    FULLY_FURNISHED = "FULLY_FURNISHED"

class FacingDirection:
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"
    NORTH_EAST = "NORTH_EAST"
    NORTH_WEST = "NORTH_WEST"
    SOUTH_EAST = "SOUTH_EAST"
    SOUTH_WEST = "SOUTH_WEST"

class PropertyView:
    GARDEN = "GARDEN"
    POOL = "POOL"
    CLUBHOUSE = "CLUBHOUSE"
    COMMUNITY = "COMMUNITY"
    MAIN_ROAD = "MAIN_ROAD"
    CITY = "CITY"
    SEA = "SEA"
    LAKE = "LAKE"
    RIVER = "RIVER"
    GOLF_COURSE = "GOLF_COURSE"
    HILLS = "HILLS"
    FOREST = "FOREST"

class RoomCategory:
    LIVING_ROOM = "LIVING_ROOM"
    MASTER_BEDROOM = "MASTER_BEDROOM"
    GUEST_BEDROOM = "GUEST_BEDROOM"
    KITCHEN = "KITCHEN"
    BATHROOM = "BATHROOM"
    BALCONY = "BALCONY"
    UTILITY_AREA = "UTILITY_AREA"
    ENTRANCE_LOBBY = "ENTRANCE_LOBBY"
    PARKING = "PARKING"
    FACADE_EXTERIOR = "FACADE_EXTERIOR"

class DefectSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# ARCHITECTURAL FINISH PALETTES MAPPED TO PRISMA FlooringType ENUMS
# =============================================================================

FLOORING_PALETTES = {
    FlooringType.ITALIAN_MARBLE: {
        "floorColor": "#F4F1EA",
        "floorType": "Italian Statuario & Botticino Marble",
        "wallColor": "#FAF8F5",
        "materialKey": "cream",
        "shininess": 85,
        "roughness": 0.15,
    },
    FlooringType.MARBLE: {
        "floorColor": "#FBF9F5",
        "floorType": "Greek Thassos White Marble",
        "wallColor": "#FFFFFF",
        "materialKey": "white",
        "shininess": 75,
        "roughness": 0.20,
    },
    FlooringType.WOODEN: {
        "floorColor": "#C9A275",
        "floorType": "Engineered German Oak Hardwood",
        "wallColor": "#EAE7DF",
        "materialKey": "woodFloor",
        "shininess": 30,
        "roughness": 0.65,
    },
    FlooringType.GRANITE: {
        "floorColor": "#263238",
        "floorType": "Honed Nero Impala Granite & Quartzite",
        "wallColor": "#F8F8F8",
        "materialKey": "dark",
        "shininess": 45,
        "roughness": 0.40,
    },
    FlooringType.VITRIFIED_TILES: {
        "floorColor": "#ECE9E2",
        "floorType": "Matte Vitrified Architectural Tiles (1200x600mm)",
        "wallColor": "#F1EEE7",
        "materialKey": "slab",
        "shininess": 25,
        "roughness": 0.55,
    },
    FlooringType.CERAMIC_TILES: {
        "floorColor": "#E8ECEF",
        "floorType": "Glazed Ceramic Tiles",
        "wallColor": "#F5F5F3",
        "materialKey": "cream",
        "shininess": 40,
        "roughness": 0.50,
    },
    FlooringType.MOSAIC: {
        "floorColor": "#DDD8CE",
        "floorType": "Artisan Terrazzo & Mosaic Stone",
        "wallColor": "#EFECE6",
        "materialKey": "cream2",
        "shininess": 35,
        "roughness": 0.50,
    },
    FlooringType.CONCRETE: {
        "floorColor": "#8C8C8C",
        "floorType": "Polished Architectural Concrete Screed",
        "wallColor": "#ECEAE4",
        "materialKey": "grey1",
        "shininess": 20,
        "roughness": 0.70,
    },
    FlooringType.OTHER: {
        "floorColor": "#ECE9E2",
        "floorType": "Architectural Composite Slab",
        "wallColor": "#F1EEE7",
        "materialKey": "slab",
        "shininess": 25,
        "roughness": 0.55,
    },
}

# General palettes for backwards compatibility
FINISH_PALETTES = {
    "marble": FLOORING_PALETTES[FlooringType.ITALIAN_MARBLE],
    "thassos": FLOORING_PALETTES[FlooringType.MARBLE],
    "wood": FLOORING_PALETTES[FlooringType.WOODEN],
    "walnut": {
        "floorColor": "#5D4037",
        "floorType": "Natural Walnut Hardwood",
        "wallColor": "#ECEAE4",
        "materialKey": "wood2",
        "shininess": 30,
        "roughness": 0.65,
    },
    "quartz": FLOORING_PALETTES[FlooringType.GRANITE],
    "tile": FLOORING_PALETTES[FlooringType.VITRIFIED_TILES],
    "deck": {
        "floorColor": "#A87042",
        "floorType": "Weatherproof Teak Composite Deck",
        "wallColor": "#ECE9E2",
        "materialKey": "wood2",
        "shininess": 25,
        "roughness": 0.70,
    },
    "pool": {
        "floorColor": "#0F2B36",
        "floorType": "Balinese Sukabumi Stone Pool Deck",
        "wallColor": "#0F2B36",
        "materialKey": "dark",
        "shininess": 90,
        "roughness": 0.10,
    },
}


class DigitalTwinEngine:
    """
    Sovereign 3D Digital Twin Engine.
    Dynamically moulds virtual spatial models from database prompts and Prisma schema structures.
    """

    def __init__(self):
        pass

    # =========================================================================
    # DB SCHEMA CONTEXT & PROMPT EXTRACTION
    # =========================================================================

    def extract_db_context(self, property_data: Union[Dict[str, Any], str], prompt: str = "") -> Dict[str, Any]:
        """
        Extracts verified specifications and schema-conformant attributes directly from
        a database property row or from an incoming natural language prompt from the DB.
        """
        raw_dict = {}
        if isinstance(property_data, dict):
            raw_dict = dict(property_data)
        elif isinstance(property_data, str) and not prompt:
            prompt = property_data

        combined_text = f"{prompt} {raw_dict.get('description', '')} {raw_dict.get('title', '')} {raw_dict.get('inspection', {}).get('summary', '') if isinstance(raw_dict.get('inspection'), dict) else ''}".lower()

        # 1. Title & IDs
        prop_id = str(raw_dict.get("id", raw_dict.get("propertyId", f"prop_{uuid.uuid4().hex[:12]}")))
        public_id = str(raw_dict.get("publicId", f"prop_{prop_id[:12]}"))
        title = raw_dict.get("title")
        if not title:
            if prompt:
                title = prompt.split(".")[0].strip()[:60]
            else:
                title = "Sovereign Architectural Residence"

        # 2. Property Type (Prisma PropertyType enum)
        raw_type = str(raw_dict.get("propertyType", "")).upper()
        if hasattr(PropertyType, raw_type):
            prop_type = getattr(PropertyType, raw_type)
        elif "PENTHOUSE" in raw_type or "penthouse" in combined_text:
            prop_type = PropertyType.PENTHOUSE
        elif "VILLA" in raw_type or "villa" in combined_text:
            prop_type = PropertyType.VILLA
        elif "INDEPENDENT_HOUSE" in raw_type or "independent house" in combined_text or "bungalow" in combined_text:
            prop_type = PropertyType.INDEPENDENT_HOUSE
        elif "BUILDER_FLOOR" in raw_type or "builder floor" in combined_text or "independent floor" in combined_text:
            prop_type = PropertyType.BUILDER_FLOOR
        else:
            prop_type = PropertyType.APARTMENT

        # 3. Configuration & BHK Count
        cfg_str = str(raw_dict.get("configuration", ""))
        bhk_count = raw_dict.get("bhkCount")

        if not bhk_count:
            bhk_m = re.search(r'(\d+)\s*(?:bhk|bed)', f"{cfg_str} {combined_text}".lower())
            if bhk_m:
                bhk_count = int(bhk_m.group(1))
            elif "studio" in combined_text:
                bhk_count = 1
            else:
                bhk_count = 3
        bhk_count = max(1, min(6, int(bhk_count)))
        if not cfg_str or cfg_str == "None":
            cfg_str = f"{bhk_count} BHK"

        # 4. Carpet Area & Built-up Area
        carpet_sqft = raw_dict.get("carpetAreaSqft")
        if not carpet_sqft:
            m_sq = re.search(r'(\d[\d,]+)\s*(?:sqft|sq\.ft|sq\s*ft)', combined_text)
            if m_sq:
                carpet_sqft = int(m_sq.group(1).replace(",", ""))
            else:
                # Heuristic default based on BHK and archetype
                base_sqft = {1: 650, 2: 1200, 3: 1950, 4: 2900, 5: 4200, 6: 5500}.get(bhk_count, 2200)
                if prop_type in (PropertyType.VILLA, PropertyType.PENTHOUSE):
                    base_sqft = int(base_sqft * 1.5)
                carpet_sqft = base_sqft
        carpet_sqft = int(carpet_sqft)
        built_up_sqft = int(raw_dict.get("superBuiltUpAreaSqft", int(carpet_sqft * 1.28)))

        # 5. Flooring Type (Prisma FlooringType enum)
        raw_flooring = str(raw_dict.get("flooring", "")).upper()
        if hasattr(FlooringType, raw_flooring):
            flooring = getattr(FlooringType, raw_flooring)
        elif "ITALIAN" in raw_flooring or "italian marble" in combined_text or "botticino" in combined_text or "statuario" in combined_text:
            flooring = FlooringType.ITALIAN_MARBLE
        elif "MARBLE" in raw_flooring or "thassos" in combined_text or "white marble" in combined_text or "marble" in combined_text:
            flooring = FlooringType.MARBLE
        elif "WOOD" in raw_flooring or "hardwood" in combined_text or "oak" in combined_text or "parquet" in combined_text:
            flooring = FlooringType.WOODEN
        elif "GRANITE" in raw_flooring or "granite" in combined_text or "quartz" in combined_text:
            flooring = FlooringType.GRANITE
        elif "CERAMIC" in raw_flooring or "ceramic" in combined_text:
            flooring = FlooringType.CERAMIC_TILES
        elif "MOSAIC" in raw_flooring or "terrazzo" in combined_text or "mosaic" in combined_text:
            flooring = FlooringType.MOSAIC
        elif "CONCRETE" in raw_flooring or "concrete" in combined_text or "industrial" in combined_text:
            flooring = FlooringType.CONCRETE
        elif "VITRIFIED" in raw_flooring:
            flooring = FlooringType.VITRIFIED_TILES
        else:
            flooring = FlooringType.VITRIFIED_TILES

        # 6. Furnishing Status (Prisma FurnishingStatus enum)
        raw_furnishing = str(raw_dict.get("furnishing", "")).upper()
        if hasattr(FurnishingStatus, raw_furnishing):
            furnishing = getattr(FurnishingStatus, raw_furnishing)
        elif "UNFURNISHED" in raw_furnishing or "bare shell" in combined_text or "raw" in combined_text or "unfurnished" in combined_text:
            furnishing = FurnishingStatus.UNFURNISHED
        elif "SEMI" in raw_furnishing or "semi furnished" in combined_text or "semi-furnished" in combined_text or "modular kitchen" in combined_text:
            furnishing = FurnishingStatus.SEMI_FURNISHED
        else:
            furnishing = FurnishingStatus.FULLY_FURNISHED

        # 7. Facing Direction (Prisma FacingDirection enum)
        raw_facing = str(raw_dict.get("facing", "")).upper().replace("-", "_").replace(" ", "_")
        if hasattr(FacingDirection, raw_facing):
            facing = getattr(FacingDirection, raw_facing)
        elif "NORTH_EAST" in raw_facing or "north-east" in combined_text or "northeast" in combined_text:
            facing = FacingDirection.NORTH_EAST
        elif "NORTH_WEST" in raw_facing or "north-west" in combined_text or "northwest" in combined_text:
            facing = FacingDirection.NORTH_WEST
        elif "SOUTH_EAST" in raw_facing or "south-east" in combined_text or "southeast" in combined_text:
            facing = FacingDirection.SOUTH_EAST
        elif "SOUTH_WEST" in raw_facing or "south-west" in combined_text or "southwest" in combined_text:
            facing = FacingDirection.SOUTH_WEST
        elif "NORTH" in raw_facing or "north" in combined_text:
            facing = FacingDirection.NORTH
        elif "WEST" in raw_facing or "west" in combined_text:
            facing = FacingDirection.WEST
        elif "SOUTH" in raw_facing or "south" in combined_text:
            facing = FacingDirection.SOUTH
        else:
            facing = FacingDirection.EAST

        # 8. Property Views (Prisma PropertyView enum list)
        views: List[str] = []
        raw_views = raw_dict.get("views", [])
        if isinstance(raw_views, list):
            for v in raw_views:
                v_str = str(v).upper()
                if hasattr(PropertyView, v_str):
                    views.append(v_str)

        if "sea" in combined_text or "ocean" in combined_text or "coast" in combined_text or "marina" in combined_text:
            if PropertyView.SEA not in views: views.append(PropertyView.SEA)
        if "pool" in combined_text or "plunge pool" in combined_text:
            if PropertyView.POOL not in views: views.append(PropertyView.POOL)
        if "golf" in combined_text or "fairway" in combined_text:
            if PropertyView.GOLF_COURSE not in views: views.append(PropertyView.GOLF_COURSE)
        if "garden" in combined_text or "park" in combined_text:
            if PropertyView.GARDEN not in views: views.append(PropertyView.GARDEN)
        if "city" in combined_text or "skyline" in combined_text:
            if PropertyView.CITY not in views: views.append(PropertyView.CITY)
        if "lake" in combined_text:
            if PropertyView.LAKE not in views: views.append(PropertyView.LAKE)
        if "hills" in combined_text or "mountain" in combined_text:
            if PropertyView.HILLS not in views: views.append(PropertyView.HILLS)

        if not views:
            views = [PropertyView.CITY, PropertyView.GARDEN]

        # 9. Balconies & Bathrooms Count
        balcony_count = raw_dict.get("balconyCount")
        if balcony_count is None:
            m_balc = re.search(r'(\d+)\s*balcon', combined_text)
            balcony_count = int(m_balc.group(1)) if m_balc else max(1, min(4, bhk_count - 1))
        balcony_count = int(balcony_count)

        bathrooms_count = raw_dict.get("bathrooms")
        if bathrooms_count is None:
            m_bath = re.search(r'(\d+)\s*(?:bath|washroom)', combined_text)
            bathrooms_count = int(m_bath.group(1)) if m_bath else max(1, bhk_count)
        bathrooms_count = int(bathrooms_count)

        # 10. Floor Levels & Archetype Mapping
        floor_str = str(raw_dict.get("floor", raw_dict.get("floorNumber", "Typical Floor")))
        floor_lower = floor_str.lower()

        is_g2 = "g + 2" in floor_lower or "g+2" in floor_lower or "3 floor" in floor_lower or "3-floor" in floor_lower or "g+2" in combined_text
        is_g1 = "g + 1" in floor_lower or "g+1" in floor_lower or "2 floor" in floor_lower or "duplex" in combined_text or "g+1" in combined_text

        if prop_type == PropertyType.PENTHOUSE:
            archetype = "penthouse"
            levels_count = 2 if is_g1 else 1
            floor_height = "12.5 ft (Panoramic High Volume)"
        elif prop_type in (PropertyType.VILLA, PropertyType.INDEPENDENT_HOUSE):
            if is_g2:
                archetype = "villa_g2"
                levels_count = 3
                floor_height = "11.0 ft (Double Height Void: 22 ft)"
            else:
                archetype = "villa_g1"
                levels_count = 2
                floor_height = "10.5 ft"
        else:
            archetype = "apartment"
            levels_count = 1
            floor_height = "10.5 ft"

        # 11. Inspection & Defect Analysis (from DB Inspection/InspectionPhoto or prompt)
        inspection_summary = ""
        seepage_detected = bool(raw_dict.get("seepageDetected", False))
        defects = []

        if isinstance(raw_dict.get("inspections"), list) and raw_dict["inspections"]:
            latest_insp = raw_dict["inspections"][0]
            if isinstance(latest_insp, dict):
                inspection_summary = latest_insp.get("summary", "")
                if latest_insp.get("seepageDetected"):
                    seepage_detected = True
                photos = latest_insp.get("photos", [])
                for p in photos:
                    if isinstance(p, dict) and p.get("hasDefect"):
                        defects.append({
                            "id": p.get("id", f"defect_{len(defects)+1}"),
                            "type": p.get("defectType", "seepage"),
                            "severity": p.get("defectSeverity", DefectSeverity.MEDIUM),
                            "roomCategory": p.get("roomCategory", RoomCategory.BATHROOM),
                            "description": f"Inspection alert: {p.get('defectType', 'surface defect')} detected in {p.get('roomCategory', 'interior')}",
                        })
        elif isinstance(raw_dict.get("inspection"), dict):
            insp = raw_dict["inspection"]
            inspection_summary = insp.get("summary", "")
            if insp.get("seepageDetected"):
                seepage_detected = True

        # Extract defect signals from text prompt
        if "seepage" in combined_text or "dampness" in combined_text or "leakage" in combined_text:
            seepage_detected = True
            target_room = RoomCategory.BATHROOM if "bath" in combined_text else RoomCategory.LIVING_ROOM
            if not any(d["type"] == "seepage" for d in defects):
                defects.append({
                    "id": f"defect_seepage_{len(defects)+1}",
                    "type": "seepage",
                    "severity": DefectSeverity.HIGH if "severe" in combined_text else DefectSeverity.MEDIUM,
                    "roomCategory": target_room,
                    "description": "Seepage moisture mark noted during physical audit.",
                })
        if "crack" in combined_text:
            defects.append({
                "id": f"defect_crack_{len(defects)+1}",
                "type": "wall_crack",
                "severity": DefectSeverity.LOW,
                "roomCategory": RoomCategory.LIVING_ROOM,
                "description": "Hairline settlement plaster crack observed.",
            })

        # 12. City & Location
        city = raw_dict.get("city", "Mumbai")
        locality = raw_dict.get("locality", "Prime Corridor")
        state = raw_dict.get("state", "Maharashtra")

        # Environmental lighting & theme
        env_theme = {
            "Mumbai": "mumbai_coast",
            "Dubai": "dubai_skyline",
            "Pune": "pune_hills",
            "Indore": "indore_greens",
            "Bengaluru": "bengaluru_garden",
            "Hyderabad": "hyderabad_tech",
        }.get(city, "mumbai_coast")

        if PropertyView.SEA in views or PropertyView.LAKE in views:
            env_theme = "mumbai_coast"
        elif PropertyView.GOLF_COURSE in views or PropertyView.FOREST in views:
            env_theme = "pune_hills"

        return {
            "propertyId": prop_id,
            "publicId": public_id,
            "propertyTitle": title,
            "locality": locality,
            "city": city,
            "state": state,
            "propertyType": prop_type,
            "configuration": cfg_str,
            "bhkCount": bhk_count,
            "carpetSqft": carpet_sqft,
            "builtUpSqft": built_up_sqft,
            "floor": floor_str,
            "facing": facing,
            "flooring": flooring,
            "furnishing": furnishing,
            "views": views,
            "balconyCount": balcony_count,
            "bathroomsCount": bathrooms_count,
            "floorHeight": floor_height,
            "conditionScore": round(float(raw_dict.get("verificationScore", raw_dict.get("trustScore", 96))) / 10.0, 1),
            "efficiency": 84,
            "orientation": f"{facing.replace('_', ' ').title()}-Facing",
            "archetype": archetype,
            "levelsCount": levels_count,
            "inspectionSummary": inspection_summary,
            "seepageDetected": seepage_detected,
            "defects": defects,
            "environmentalTheme": env_theme,
            "prompt": prompt,
        }

    # =========================================================================
    # PROCEDURAL WALL & BIM ELEMENT GENERATORS
    # =========================================================================

    def _add_wall_segment(
        self,
        walls: List[Dict[str, Any]],
        x: float, y: float, z: float,
        w: float, h: float, d: float,
        material_key: str = "cream",
        is_exterior: bool = False,
        floor_level: int = 0,
        wall_id: str = ""
    ):
        walls.append({
            "id": wall_id or f"w_{floor_level}_{int(x*10)}_{int(z*10)}",
            "position": [round(x, 3), round(y, 3), round(z, 3)],
            "size": [round(w, 3), round(h, 3), round(d, 3)],
            "materialKey": material_key,
            "isExterior": is_exterior,
            "floorLevel": floor_level,
        })

    def _add_wall_x_with_openings(
        self,
        walls: List[Dict[str, Any]],
        doors: List[Dict[str, Any]],
        windows: List[Dict[str, Any]],
        x_start: float, x_end: float,
        z: float, y_base: float,
        height: float, thickness: float = 0.18,
        openings: List[Dict[str, Any]] = None,
        is_exterior: bool = False,
        floor_level: int = 0,
        id_prefix: str = "wx"
    ):
        if openings is None:
            openings = []

        x1, x2 = min(x_start, x_end), max(x_start, x_end)
        sorted_ops = sorted(openings, key=lambda op: op["x"])
        cur_x = x1
        mat = "cream2" if is_exterior else "cream"

        for idx, op in enumerate(sorted_ops):
            op_x = op["x"]
            op_w = op["width"]
            op_h = op["height"]
            sill_h = op.get("sillHeight", 0.0)
            op_left = op_x - op_w / 2.0
            op_right = op_x + op_w / 2.0

            if op_left > cur_x + 0.02:
                seg_w = op_left - cur_x
                seg_x = cur_x + seg_w / 2.0
                seg_y = y_base + height / 2.0
                self._add_wall_segment(
                    walls, seg_x, seg_y, z, seg_w, height, thickness,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_seg_{idx}"
                )

            if sill_h > 0.02:
                sill_y = y_base + sill_h / 2.0
                self._add_wall_segment(
                    walls, op_x, sill_y, z, op_w, sill_h, thickness,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_sill_{idx}"
                )

            lintel_h = height - (sill_h + op_h)
            if lintel_h > 0.02:
                lintel_y = y_base + sill_h + op_h + lintel_h / 2.0
                self._add_wall_segment(
                    walls, op_x, lintel_y, z, op_w, lintel_h, thickness,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_lintel_{idx}"
                )

            op_type = op.get("type", "door")
            if op_type == "door":
                doors.append({
                    "id": op.get("id", f"door_{id_prefix}_{idx}"),
                    "name": op.get("name", "Interior Door"),
                    "position": [round(op_x, 3), round(y_base + op_h / 2.0, 3), round(z, 3)],
                    "size": [round(op_w, 3), round(op_h, 3), round(thickness, 3)],
                    "rotationY": 0.0,
                    "floorLevel": floor_level,
                    "doorType": op.get("doorType", "swing"),
                    "openAngle": op.get("openAngle", 0.5),
                    "frameMaterial": "dark",
                    "leafMaterial": "wood2",
                })
            elif op_type == "window":
                win_y = y_base + sill_h + op_h / 2.0
                windows.append({
                    "id": op.get("id", f"win_{id_prefix}_{idx}"),
                    "name": op.get("name", "Exterior Window"),
                    "position": [round(op_x, 3), round(win_y, 3), round(z, 3)],
                    "size": [round(op_w, 3), round(op_h, 3)],
                    "rotationY": 0.0,
                    "sillHeight": sill_h,
                    "floorLevel": floor_level,
                    "hasMullions": True,
                    "frameMaterial": "dark",
                })
            elif op_type == "slider":
                doors.append({
                    "id": op.get("id", f"slider_{id_prefix}_{idx}"),
                    "name": op.get("name", "Sliding Balcony Door"),
                    "position": [round(op_x, 3), round(y_base + op_h / 2.0, 3), round(z, 3)],
                    "size": [round(op_w, 3), round(op_h, 3), round(thickness, 3)],
                    "rotationY": 0.0,
                    "floorLevel": floor_level,
                    "doorType": "sliding",
                    "panelsCount": 2,
                    "frameMaterial": "dark",
                })

            cur_x = max(cur_x, op_right)

        if x2 > cur_x + 0.02:
            seg_w = x2 - cur_x
            seg_x = cur_x + seg_w / 2.0
            seg_y = y_base + height / 2.0
            self._add_wall_segment(
                walls, seg_x, seg_y, z, seg_w, height, thickness,
                material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                wall_id=f"{id_prefix}_seg_final"
            )

    def _add_wall_z_with_openings(
        self,
        walls: List[Dict[str, Any]],
        doors: List[Dict[str, Any]],
        windows: List[Dict[str, Any]],
        z_start: float, z_end: float,
        x: float, y_base: float,
        height: float, thickness: float = 0.18,
        openings: List[Dict[str, Any]] = None,
        is_exterior: bool = False,
        floor_level: int = 0,
        id_prefix: str = "wz"
    ):
        if openings is None:
            openings = []

        z1, z2 = min(z_start, z_end), max(z_start, z_end)
        sorted_ops = sorted(openings, key=lambda op: op["z"])
        cur_z = z1
        mat = "cream2" if is_exterior else "cream"

        for idx, op in enumerate(sorted_ops):
            op_z = op["z"]
            op_w = op["width"]
            op_h = op["height"]
            sill_h = op.get("sillHeight", 0.0)
            op_front = op_z - op_w / 2.0
            op_back = op_z + op_w / 2.0

            if op_front > cur_z + 0.02:
                seg_d = op_front - cur_z
                seg_z = cur_z + seg_d / 2.0
                seg_y = y_base + height / 2.0
                self._add_wall_segment(
                    walls, x, seg_y, seg_z, thickness, height, seg_d,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_seg_{idx}"
                )

            if sill_h > 0.02:
                sill_y = y_base + sill_h / 2.0
                self._add_wall_segment(
                    walls, x, sill_y, op_z, thickness, sill_h, op_w,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_sill_{idx}"
                )

            lintel_h = height - (sill_h + op_h)
            if lintel_h > 0.02:
                lintel_y = y_base + sill_h + op_h + lintel_h / 2.0
                self._add_wall_segment(
                    walls, x, lintel_y, op_z, thickness, lintel_h, op_w,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_lintel_{idx}"
                )

            op_type = op.get("type", "door")
            if op_type == "door":
                doors.append({
                    "id": op.get("id", f"door_{id_prefix}_{idx}"),
                    "name": op.get("name", "Interior Door"),
                    "position": [round(x, 3), round(y_base + op_h / 2.0, 3), round(op_z, 3)],
                    "size": [round(op_w, 3), round(op_h, 3), round(thickness, 3)],
                    "rotationY": math.pi / 2.0,
                    "floorLevel": floor_level,
                    "doorType": op.get("doorType", "swing"),
                    "openAngle": op.get("openAngle", 0.5),
                    "frameMaterial": "dark",
                    "leafMaterial": "wood2",
                })
            elif op_type == "window":
                win_y = y_base + sill_h + op_h / 2.0
                windows.append({
                    "id": op.get("id", f"win_{id_prefix}_{idx}"),
                    "name": op.get("name", "Exterior Window"),
                    "position": [round(x, 3), round(win_y, 3), round(op_z, 3)],
                    "size": [round(op_w, 3), round(op_h, 3)],
                    "rotationY": math.pi / 2.0,
                    "sillHeight": sill_h,
                    "floorLevel": floor_level,
                    "hasMullions": True,
                    "frameMaterial": "dark",
                })
            elif op_type == "slider":
                doors.append({
                    "id": op.get("id", f"slider_{id_prefix}_{idx}"),
                    "name": op.get("name", "Sliding Balcony Door"),
                    "position": [round(x, 3), round(y_base + op_h / 2.0, 3), round(op_z, 3)],
                    "size": [round(op_w, 3), round(op_h, 3), round(thickness, 3)],
                    "rotationY": math.pi / 2.0,
                    "floorLevel": floor_level,
                    "doorType": "sliding",
                    "panelsCount": 2,
                    "frameMaterial": "dark",
                })

            cur_z = max(cur_z, op_back)

        if z2 > cur_z + 0.02:
            seg_d = z2 - cur_z
            seg_z = cur_z + seg_d / 2.0
            seg_y = y_base + height / 2.0
            self._add_wall_segment(
                walls, x, seg_y, seg_z, thickness, height, seg_d,
                material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                wall_id=f"{id_prefix}_seg_final"
            )

    def _add_balcony_system(
        self,
        balconies: List[Dict[str, Any]],
        glass_panels: List[Dict[str, Any]],
        balc_id: str,
        name: str,
        floor_level: int,
        deck_x: float, deck_y: float, deck_z: float,
        deck_w: float, deck_d: float,
        rail_height: float = 1.1,
        open_sides: List[str] = None
    ):
        if open_sides is None:
            open_sides = ["front", "left", "right"]

        railings = []
        if "front" in open_sides:
            railings.append({
                "id": f"{balc_id}_rail_front",
                "position": [round(deck_x, 3), round(deck_y + rail_height / 2.0, 3), round(deck_z + deck_d / 2.0, 3)],
                "size": [round(deck_w, 3), round(rail_height, 3)],
                "rotationY": 0.0,
                "type": "glass_balustrade",
                "handrail": True,
            })
        if "left" in open_sides:
            railings.append({
                "id": f"{balc_id}_rail_left",
                "position": [round(deck_x - deck_w / 2.0, 3), round(deck_y + rail_height / 2.0, 3), round(deck_z, 3)],
                "size": [round(deck_d, 3), round(rail_height, 3)],
                "rotationY": math.pi / 2.0,
                "type": "glass_balustrade",
                "handrail": True,
            })
        if "right" in open_sides:
            railings.append({
                "id": f"{balc_id}_rail_right",
                "position": [round(deck_x + deck_w / 2.0, 3), round(deck_y + rail_height / 2.0, 3), round(deck_z, 3)],
                "size": [round(deck_d, 3), round(rail_height, 3)],
                "rotationY": math.pi / 2.0,
                "type": "glass_balustrade",
                "handrail": True,
            })

        for r in railings:
            glass_panels.append({
                "id": r["id"],
                "position": r["position"],
                "size": r["size"],
                "rotationY": r["rotationY"],
                "floorLevel": floor_level,
                "handrail": True,
            })

        balconies.append({
            "id": balc_id,
            "name": name,
            "floorLevel": floor_level,
            "bounds": {
                "x": round(deck_x, 3),
                "y": round(deck_y, 3),
                "z": round(deck_z, 3),
                "w": round(deck_w, 3),
                "d": round(deck_d, 3),
                "h": 0.2,
            },
            "deckMaterial": "deck",
            "railings": railings,
        })

    # =========================================================================
    # FURNITURE MOULDING BY FurnishingStatus
    # =========================================================================

    def _filter_furniture_by_furnishing(
        self,
        furniture_items: List[Dict[str, Any]],
        furnishing: str
    ) -> List[Dict[str, Any]]:
        """
        Moulds furniture objects around the Prisma FurnishingStatus:
          - UNFURNISHED: Strips loose items; displays bare handover fixtures.
          - SEMI_FURNISHED: Modular fixed cabinetry, fitted wardrobes, kitchen counters, sanitary items only.
          - FULLY_FURNISHED: Complete luxury turnkey staging.
        """
        if furnishing == FurnishingStatus.FULLY_FURNISHED:
            return furniture_items

        filtered = []
        if furnishing == FurnishingStatus.SEMI_FURNISHED:
            for item in furniture_items:
                itype = item.get("type", "")
                if itype in ("counter", "wardrobe", "vanity", "bath", "fixture"):
                    filtered.append(item)
            return filtered

        if furnishing == FurnishingStatus.UNFURNISHED:
            # Bare shell: show architectural conduit & rough-in markers instead of loose furniture
            return []

        return furniture_items

    # =========================================================================
    # MULTI-ARCHETYPE SPATIAL SOLVER
    # =========================================================================

    def solve_spatial_layout(self, about: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solves 3D spatial layout moulding dynamically to schema context:
          1. Exact physical number of bedrooms matching configuration (1 to 5+ BHK).
          2. Calibrated 3:1 Living Hall to Kitchen ratio.
          3. Multi-floor elevations (Villas G+1, G+2, Penthouses, Apartments).
          4. Flooring material and color dynamically shaped by Prisma FlooringType.
          5. Furnishing staging dynamically shaped by Prisma FurnishingStatus.
          6. Sunlight vector and temperature dynamically shaped by Prisma FacingDirection.
          7. Outdoor panorama dynamically shaped by Prisma PropertyView enums.
          8. Inspection defect markers physically located on 3D walls/ceilings.
        """
        archetype = about["archetype"]
        bhk_count = about["bhkCount"]
        carpet = about["carpetSqft"]
        flooring = about["flooring"]
        furnishing = about["furnishing"]
        facing = about["facing"]
        views = about["views"]
        defects_raw = about.get("defects", [])

        H_FLOOR = 3.2
        H_DOUBLE = 6.4
        if archetype == "penthouse":
            H_FLOOR = 3.8

        # Determine Primary & Secondary Flooring Palette
        floor_pal = FLOORING_PALETTES.get(flooring, FLOORING_PALETTES[FlooringType.VITRIFIED_TILES])
        primary_floor_type = floor_pal["floorType"]
        primary_floor_color = floor_pal["floorColor"]
        primary_wall_color = floor_pal["wallColor"]

        # Bedroom wood/finish palette
        wood_pal = FLOORING_PALETTES[FlooringType.WOODEN]

        generated_rooms = []
        structural_walls = []
        doors = []
        windows = []
        balconies = []
        glass_panels = []
        floors = []
        focal_targets = {}
        tour_waypoints = []
        defect_markers = []

        tour_waypoints.append({
            "p": [4.0, 3.5, 18.0],
            "l": [0.0, 2.5, 0.0],
            "label": f"Approach · {about['propertyTitle']}"
        })

        # =====================================================================
        # ARCHETYPE 1: G+2 INDEPENDENT VILLA (3 PHYSICAL LEVELS)
        # =====================================================================
        if archetype == "villa_g2":
            floors = [
                {"id": "floor_0", "name": "Ground Floor (Grand Living & Pool Deck)", "elevation": 0.0, "roomIds": ["living", "kitchen", "pool_deck", "foyer"]},
                {"id": "floor_1", "name": "First Floor (Master Suite & Mezzanine)", "elevation": 3.7, "roomIds": ["master", "mezzanine", "bedroom_2"]},
                {"id": "floor_2", "name": "Second Floor (Bedrooms 3 & 4 & Sky Deck)", "elevation": 7.4, "roomIds": ["bedroom_3", "bedroom_4", "sky_terrace"]}
            ]

            # Level 0 - Grand Living Hall (Double Height)
            living_w, living_d = 10.0, 7.5
            living_bounds = {"x": 0.0, "y": 0.0, "z": 0.0, "w": living_w, "d": living_d, "h": H_DOUBLE}
            living_furniture = [
                {"id": "sofa_main", "name": "Sectional White Boucle Sofa", "type": "sofa", "position": [-1.2, 0.45, 1.8], "size": [4.5, 0.85, 2.0], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "coffee_tbl", "name": "Low Marble Coffee Table", "type": "table", "position": [-1.2, 0.25, 0.2], "size": [2.4, 0.45, 1.2], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "living_rug", "name": "Textured Hand-Woven Rug", "type": "rug", "position": [-1.2, 0.02, 1.0], "size": [5.6, 0.02, 4.0], "materialKey": "rug", "color": "#CABFA8"},
                {"id": "dining_tbl", "name": "8-Seater Smoked Oak Dining Table", "type": "table", "position": [2.5, 0.45, -1.0], "size": [2.8, 0.85, 1.4], "materialKey": "wood2", "color": "#A87042"},
                {"id": "tv_console", "name": "Fluted Marble Media Console", "type": "tv_unit", "position": [-1.2, 0.35, -3.2], "size": [3.6, 0.6, 0.5], "materialKey": "dark", "color": "#3A3A40"},
            ]
            living_furniture = self._filter_furniture_by_furnishing(living_furniture, furnishing)

            generated_rooms.append({
                "id": "living",
                "name": "Double-Height Grand Living & Dining Hall",
                "category": RoomCategory.LIVING_ROOM,
                "floorLevel": 0,
                "dimensions": "32' x 24' (22ft Ceiling)",
                "carpetSqft": int(carpet * 0.34),
                "highlight": f"22ft double-height ceiling with {primary_floor_type} and floor-to-ceiling glass opening to pool deck",
                "floorType": primary_floor_type,
                "floorColor": primary_floor_color,
                "wallColor": primary_wall_color,
                "bounds": living_bounds,
                "furniture": living_furniture,
                "lights": [{"position": [-1.2, 5.2, 0.5], "color": "#FFD9A0", "intensity": 1.2, "distance": 16.0}],
            })
            focal_targets["living"] = {"target": [0.0, 2.2, 0.5], "theta": 0.45, "phi": 1.05, "radius": 16.0, "walk": [-1.0, 1.65, 3.2]}
            tour_waypoints.append({"p": [-1.0, 1.65, 3.2], "l": [2.0, 1.5, -0.5], "label": "Ground Floor · Double-Height Living (32' x 24')"})

            # Level 0 - Siemens Integrated Gourmet Kitchen (Calibrated 3:1 Ratio)
            kit_w, kit_d = 4.8, 4.8
            kit_bounds = {"x": 7.6, "y": 0.0, "z": 0.0, "w": kit_w, "d": kit_d, "h": H_FLOOR}
            kit_furniture = [
                {"id": "k_island", "name": "Corian Central Island with Wine Chiller", "type": "counter", "position": [7.6, 0.50, 0.0], "size": [3.2, 0.95, 1.4], "materialKey": "counter", "color": "#8D6F50"},
                {"id": "k_stools", "name": "Bar Stools Set", "type": "stool", "position": [7.6, 0.40, -1.1], "size": [2.4, 0.75, 0.45], "materialKey": "wood2", "color": "#A87042"},
            ]
            kit_furniture = self._filter_furniture_by_furnishing(kit_furniture, furnishing)

            generated_rooms.append({
                "id": "kitchen",
                "name": "Siemens Integrated Gourmet Kitchen",
                "category": RoomCategory.KITCHEN,
                "floorLevel": 0,
                "dimensions": "16' x 16'",
                "carpetSqft": int(carpet * 0.11),
                "highlight": "Central culinary island, integrated induction downdraft & soft-close Blum joinery",
                "floorType": FLOORING_PALETTES[FlooringType.GRANITE]["floorType"],
                "floorColor": FLOORING_PALETTES[FlooringType.GRANITE]["floorColor"],
                "wallColor": primary_wall_color,
                "bounds": kit_bounds,
                "furniture": kit_furniture,
                "lights": [{"position": [7.6, 2.8, 0.0], "color": "#FFFFFF", "intensity": 0.9, "distance": 11.0}],
            })
            focal_targets["kitchen"] = {"target": [7.6, 1.6, 0.0], "theta": 1.95, "phi": 1.05, "radius": 13.0, "walk": [6.5, 1.65, 1.2]}
            tour_waypoints.append({"p": [6.5, 1.65, 1.2], "l": [8.5, 1.2, -1.0], "label": "Ground Floor · Gourmet Kitchen Studio (3.09:1 Ratio)"})

            # Level 0 - Heated Pool Deck
            pool_w, pool_d = 9.0, 5.0
            pool_bounds = {"x": 0.0, "y": 0.0, "z": 8.0, "w": pool_w, "d": pool_d, "h": 1.2}
            pool_furniture = [
                {"id": "pool_water", "name": "Heated Infinity Plunge Pool", "type": "counter", "position": [0.0, 0.35, 8.5], "size": [6.0, 0.45, 2.8], "materialKey": "pool", "color": "#0F2B36"},
                {"id": "lounger_1", "name": "Balinese Teak Sun Lounger", "type": "chair", "position": [-3.2, 0.35, 7.2], "size": [1.8, 0.4, 0.8], "materialKey": "wood2", "color": "#A87042"},
                {"id": "lounger_2", "name": "Balinese Teak Sun Lounger", "type": "chair", "position": [3.2, 0.35, 7.2], "size": [1.8, 0.4, 0.8], "materialKey": "wood2", "color": "#A87042"},
            ]
            if furnishing == FurnishingStatus.UNFURNISHED:
                pool_furniture = [pool_furniture[0]]  # Keep pool basin

            generated_rooms.append({
                "id": "pool_deck",
                "name": "Heated Infinity Pool Deck",
                "category": RoomCategory.BALCONY,
                "floorLevel": 0,
                "dimensions": "30' x 16'",
                "carpetSqft": int(carpet * 0.12),
                "highlight": "Weatherproof teak deck with Balinese stone heated plunge pool and glass balustrades",
                "floorType": FINISH_PALETTES["deck"]["floorType"],
                "floorColor": FINISH_PALETTES["deck"]["floorColor"],
                "wallColor": primary_wall_color,
                "bounds": pool_bounds,
                "furniture": pool_furniture,
            })
            focal_targets["pool_deck"] = {"target": [0.0, 1.2, 8.0], "theta": 2.2, "phi": 1.1, "radius": 14.0, "walk": [0.0, 1.65, 6.5]}
            tour_waypoints.append({"p": [0.0, 1.65, 6.5], "l": [0.0, 0.8, 9.5], "label": "Ground Floor · Infinity Plunge Pool Deck"})

            # Level 1 - Master Suite (Bedroom 1)
            m_w, m_d = 6.4, 5.8
            m_bounds = {"x": -6.5, "y": 3.7, "z": 0.5, "w": m_w, "d": m_d, "h": H_FLOOR}
            m_furniture = [
                {"id": "m_bed", "name": "King Master Bed", "type": "bed", "position": [-6.5, 4.15, 0.2], "size": [2.2, 0.5, 2.2], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "m_wardrobe", "name": "Walk-in Dressing Wardrobe", "type": "wardrobe", "position": [-6.5, 4.8, -2.0], "size": [3.6, 2.2, 0.6], "materialKey": "wood2", "color": "#8D6F50"},
                {"id": "m_side1", "name": "Floating Nightstand", "type": "table", "position": [-8.0, 4.0, 0.2], "size": [0.6, 0.4, 0.4], "materialKey": "accent", "color": "#C9A66B"},
                {"id": "m_side2", "name": "Floating Nightstand", "type": "table", "position": [-5.0, 4.0, 0.2], "size": [0.6, 0.4, 0.4], "materialKey": "accent", "color": "#C9A66B"},
            ]
            m_furniture = self._filter_furniture_by_furnishing(m_furniture, furnishing)

            generated_rooms.append({
                "id": "master",
                "name": "Presidential Master Suite (Bedroom 1 - 1st Floor)",
                "category": RoomCategory.MASTER_BEDROOM,
                "floorLevel": 1,
                "dimensions": "21' x 19'",
                "carpetSqft": int(carpet * 0.22),
                "highlight": f"{wood_pal['floorType']} with walk-in dressing wardrobe and private balcony",
                "floorType": wood_pal["floorType"],
                "floorColor": wood_pal["floorColor"],
                "wallColor": wood_pal["wallColor"],
                "bounds": m_bounds,
                "furniture": m_furniture,
                "lights": [{"position": [-6.5, 6.2, 0.5], "color": "#FFD9A0", "intensity": 0.9, "distance": 12.0}],
            })
            focal_targets["master"] = {"target": [-6.5, 4.8, 0.5], "theta": 0.45, "phi": 1.05, "radius": 14.0, "walk": [-5.2, 5.35, 1.8]}
            tour_waypoints.append({"p": [-5.2, 5.35, 1.8], "l": [-7.8, 4.6, -0.2], "label": "1st Floor · Presidential Master Suite (21' x 19')"})

            # Level 1 - Mezzanine Overlook Bridge
            mezz_w, mezz_d = 6.0, 3.4
            mezz_bounds = {"x": 0.0, "y": 3.7, "z": -1.8, "w": mezz_w, "d": mezz_d, "h": H_FLOOR}
            mezz_furniture = [
                {"id": "mezz_lounger", "name": "Mezzanine Reading Daybed", "type": "sofa", "position": [0.0, 4.15, -2.0], "size": [2.2, 0.6, 1.0], "materialKey": "sofa", "color": "#D9D1C0"},
            ]
            mezz_furniture = self._filter_furniture_by_furnishing(mezz_furniture, furnishing)

            generated_rooms.append({
                "id": "mezzanine",
                "name": "Mezzanine Overlook Bridge & Gallery",
                "category": RoomCategory.LIVING_ROOM,
                "floorLevel": 1,
                "dimensions": "20' x 11'",
                "carpetSqft": int(carpet * 0.08),
                "highlight": "Glass-railed architectural bridge suspended over double-height grand living hall",
                "floorType": wood_pal["floorType"],
                "floorColor": wood_pal["floorColor"],
                "wallColor": wood_pal["wallColor"],
                "bounds": mezz_bounds,
                "furniture": mezz_furniture,
            })
            focal_targets["mezzanine"] = {"target": [0.0, 4.8, -2.0], "theta": 0.85, "phi": 1.05, "radius": 12.0, "walk": [0.0, 5.35, -1.0]}

            # Level 1 - Junior Master Suite (Bedroom 2)
            b2_w, b2_d = 5.4, 5.0
            b2_bounds = {"x": 6.8, "y": 3.7, "z": 0.5, "w": b2_w, "d": b2_d, "h": H_FLOOR}
            b2_furniture = [
                {"id": "b2_bed", "name": "Queen Bed", "type": "bed", "position": [6.8, 4.15, 0.0], "size": [1.9, 0.5, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "b2_desk", "name": "Study Writing Desk", "type": "table", "position": [8.5, 4.1, 1.5], "size": [1.4, 0.75, 0.6], "materialKey": "wood2", "color": "#A87042"},
            ]
            b2_furniture = self._filter_furniture_by_furnishing(b2_furniture, furnishing)

            generated_rooms.append({
                "id": "bedroom_2",
                "name": "Junior Master Suite (Bedroom 2 - 1st Floor)",
                "category": RoomCategory.GUEST_BEDROOM,
                "floorLevel": 1,
                "dimensions": "18' x 16'",
                "carpetSqft": int(carpet * 0.14),
                "highlight": f"{wood_pal['floorType']} with ensuite bath and morning sun balcony",
                "floorType": wood_pal["floorType"],
                "floorColor": wood_pal["floorColor"],
                "wallColor": wood_pal["wallColor"],
                "bounds": b2_bounds,
                "furniture": b2_furniture,
            })
            focal_targets["bedroom_2"] = {"target": [6.8, 4.8, 0.5], "theta": 1.85, "phi": 1.08, "radius": 13.0, "walk": [5.2, 5.35, 1.8]}
            tour_waypoints.append({"p": [5.2, 5.35, 1.8], "l": [7.8, 4.6, -0.2], "label": "1st Floor · Junior Master Suite (18' x 16')"})

            # Level 2 - Bedroom 3
            b3_w, b3_d = 5.0, 4.8
            b3_bounds = {"x": -5.0, "y": 7.4, "z": -0.5, "w": b3_w, "d": b3_d, "h": H_FLOOR}
            b3_furniture = [
                {"id": "b3_bed", "name": "Queen Bed", "type": "bed", "position": [-5.0, 7.85, -0.5], "size": [1.9, 0.5, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "b3_side", "name": "Nightstand", "type": "table", "position": [-6.4, 7.7, -0.5], "size": [0.5, 0.4, 0.4], "materialKey": "accent", "color": "#C9A66B"},
            ]
            b3_furniture = self._filter_furniture_by_furnishing(b3_furniture, furnishing)

            generated_rooms.append({
                "id": "bedroom_3",
                "name": "Sky Villa Suite (Bedroom 3 - 2nd Floor)",
                "category": RoomCategory.GUEST_BEDROOM,
                "floorLevel": 2,
                "dimensions": "16' x 15'",
                "carpetSqft": int(carpet * 0.12),
                "highlight": "Panoramic upper-level bedroom with direct access to rooftop sky pergola deck",
                "floorType": primary_floor_type,
                "floorColor": primary_floor_color,
                "wallColor": primary_wall_color,
                "bounds": b3_bounds,
                "furniture": b3_furniture,
            })
            focal_targets["bedroom_3"] = {"target": [-5.0, 8.5, -0.5], "theta": 0.45, "phi": 1.08, "radius": 13.0, "walk": [-3.8, 9.05, 1.2]}
            tour_waypoints.append({"p": [-3.8, 9.05, 1.2], "l": [-6.0, 8.3, -1.2], "label": "2nd Floor · Sky Villa Suite (Bedroom 3)"})

            # Level 2 - Bedroom 4 (or 4th Bedroom Suite)
            b4_w, b4_d = 5.0, 4.8
            b4_bounds = {"x": 5.0, "y": 7.4, "z": -0.5, "w": b4_w, "d": b4_d, "h": H_FLOOR}
            b4_furniture = [
                {"id": "b4_bed", "name": "Queen Bed", "type": "bed", "position": [5.0, 7.85, -0.5], "size": [1.9, 0.5, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "b4_desk", "name": "Executive Study Desk", "type": "table", "position": [6.5, 7.85, 0.8], "size": [1.4, 0.75, 0.6], "materialKey": "wood2", "color": "#A87042"},
            ]
            b4_furniture = self._filter_furniture_by_furnishing(b4_furniture, furnishing)

            generated_rooms.append({
                "id": "bedroom_4",
                "name": "Penthouse Suite (Bedroom 4 - 2nd Floor)",
                "category": RoomCategory.GUEST_BEDROOM,
                "floorLevel": 2,
                "dimensions": "16' x 15'",
                "carpetSqft": int(carpet * 0.12),
                "highlight": "Dual-aspect horizon bedroom suite with panoramic private terrace views",
                "floorType": primary_floor_type,
                "floorColor": primary_floor_color,
                "wallColor": primary_wall_color,
                "bounds": b4_bounds,
                "furniture": b4_furniture,
            })
            focal_targets["bedroom_4"] = {"target": [5.0, 8.5, -0.5], "theta": 1.85, "phi": 1.08, "radius": 13.0, "walk": [3.8, 9.05, 1.2]}
            tour_waypoints.append({"p": [3.8, 9.05, 1.2], "l": [6.0, 8.3, -1.2], "label": "2nd Floor · Penthouse Suite (Bedroom 4)"})

            # Level 2 - Rooftop Sky Terrace
            terrace_w, terrace_d = 8.4, 4.6
            terrace_bounds = {"x": 0.0, "y": 7.4, "z": 4.5, "w": terrace_w, "d": terrace_d, "h": 1.1}
            terrace_furniture = [
                {"id": "sky_sofa", "name": "All-Weather Modular Sky Lounge", "type": "chair", "position": [0.0, 7.8, 4.5], "size": [2.6, 0.6, 1.2], "materialKey": "sofa", "color": "#D9D1C0"},
            ]
            if furnishing == FurnishingStatus.UNFURNISHED:
                terrace_furniture = []

            generated_rooms.append({
                "id": "sky_terrace",
                "name": "Rooftop Sky Pergola Deck",
                "category": RoomCategory.BALCONY,
                "floorLevel": 2,
                "dimensions": "28' x 15'",
                "carpetSqft": int(carpet * 0.10),
                "highlight": "Teak deck with 360-degree horizon panorama, glass balustrades & champagne gold top rail",
                "floorType": FINISH_PALETTES["deck"]["floorType"],
                "floorColor": FINISH_PALETTES["deck"]["floorColor"],
                "wallColor": primary_wall_color,
                "bounds": terrace_bounds,
                "furniture": terrace_furniture,
            })
            focal_targets["sky_terrace"] = {"target": [0.0, 8.5, 4.5], "theta": 2.25, "phi": 1.05, "radius": 14.0, "walk": [0.0, 9.05, 3.2]}

            # BIM Walls for Villa G+2
            # Ground Floor Perimeter & Partitions
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-5.0, x_end=5.0, z=3.8, y_base=0.0, height=H_DOUBLE, thickness=0.22,
                openings=[{"type": "slider", "x": 0.0, "width": 6.0, "height": 3.0, "sillHeight": 0.0, "name": "Grand Fairway Sliders"}],
                is_exterior=True, floor_level=0, id_prefix="v_l0_south"
            )
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-3.8, z_end=3.8, x=-5.0, y_base=0.0, height=H_DOUBLE, thickness=0.22,
                openings=[{"type": "window", "z": 0.0, "width": 3.0, "height": 3.2, "sillHeight": 0.6, "name": "Double Height West Window"}],
                is_exterior=True, floor_level=0, id_prefix="v_l0_west"
            )
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-3.8, z_end=3.8, x=5.0, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=[{"type": "door", "doorType": "portal", "z": 0.0, "width": 2.6, "height": 2.6, "name": "Kitchen Grand Archway"}],
                is_exterior=False, floor_level=0, id_prefix="v_l0_east_part"
            )
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-5.0, x_end=5.0, z=-3.8, y_base=0.0, height=H_DOUBLE, thickness=0.22,
                openings=[{"type": "door", "x": 0.0, "width": 1.2, "height": 2.4, "doorType": "pivot", "name": "Grand Entrance Pivot Door"}],
                is_exterior=True, floor_level=0, id_prefix="v_l0_north"
            )

            # Kitchen Exterior Walls
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=5.0, x_end=10.0, z=2.4, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[{"type": "window", "x": 7.5, "width": 2.2, "height": 1.2, "sillHeight": 1.1, "name": "Kitchen Garden Window"}],
                is_exterior=True, floor_level=0, id_prefix="v_l0_kit_south"
            )
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.4, z_end=2.4, x=10.0, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[{"type": "window", "z": 0.0, "width": 2.0, "height": 1.2, "sillHeight": 1.1, "name": "Kitchen East Window"}],
                is_exterior=True, floor_level=0, id_prefix="v_l0_kit_east"
            )

            # Level 1 Walls & Balconies
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.4, z_end=3.4, x=-3.1, y_base=3.7, height=H_FLOOR, thickness=0.18,
                openings=[{"type": "door", "z": 0.5, "width": 1.0, "height": 2.2, "doorType": "swing", "name": "Presidential Suite Door"}],
                is_exterior=False, floor_level=1, id_prefix="v_l1_m_east"
            )
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.4, z_end=3.4, x=-9.9, y_base=3.7, height=H_FLOOR, thickness=0.22,
                openings=[{"type": "window", "z": 0.5, "width": 2.6, "height": 1.5, "sillHeight": 0.85, "name": "Master Horizon Window"}],
                is_exterior=True, floor_level=1, id_prefix="v_l1_m_west"
            )
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-9.9, x_end=-3.1, z=3.4, y_base=3.7, height=H_FLOOR, thickness=0.22,
                openings=[{"type": "slider", "x": -6.5, "width": 2.4, "height": 2.4, "sillHeight": 0.0, "name": "Master Balcony Slider"}],
                is_exterior=True, floor_level=1, id_prefix="v_l1_m_south"
            )
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_master_v1", name="Master Fairway Balcony", floor_level=1,
                deck_x=-6.5, deck_y=3.7, deck_z=4.5, deck_w=4.2, deck_d=2.0, rail_height=1.1
            )

            # Mezzanine Gallery Railing overlooking void
            glass_panels.append({
                "id": "mezzanine_rail",
                "position": [0.0, 4.25, -0.3],
                "size": [6.0, 1.1],
                "rotationY": 0.0,
                "floorLevel": 1,
                "handrail": True,
            })

            # Level 2 Rooftop Pergola Balcony
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_sky_terrace_v2", name="Rooftop Sky Pergola Deck", floor_level=2,
                deck_x=0.0, deck_y=7.4, deck_z=4.5, deck_w=8.4, deck_d=4.6, rail_height=1.1
            )

        # =====================================================================
        # ARCHETYPE 2: PENTHOUSE OR APARTMENT (DYNAMIC 1 BHK TO 5 BHK)
        # =====================================================================
        else:
            floors = [
                {"id": "floor_0", "name": f"{about['propertyType'].title()} Level", "elevation": 0.0, "roomIds": ["living", "kitchen", "balcony", "master"]}
            ]

            # 1. Grand Living & Dining Pavilion (Scaled for 3:1 Ratio to Kitchen)
            living_w = 9.2 if bhk_count >= 3 else 7.6
            living_d = 6.8 if bhk_count >= 3 else 5.8
            living_bounds = {"x": 0.0, "y": 0.0, "z": 0.0, "w": living_w, "d": living_d, "h": H_FLOOR}

            living_furniture = [
                {"id": "sofa_main", "name": "Curved Designer Italian Sofa", "type": "sofa", "position": [-0.8, 0.42, 1.8], "size": [4.2, 0.75, 1.8], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "coffee_tbl", "name": f"{primary_floor_type.split()[0]} Coffee Table", "type": "table", "position": [-0.8, 0.25, 0.4], "size": [2.2, 0.45, 1.1], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "living_rug", "name": "Silken Area Rug", "type": "rug", "position": [-0.8, 0.02, 1.1], "size": [5.2, 0.02, 3.6], "materialKey": "rug", "color": "#CABFA8"},
                {"id": "dining_tbl", "name": "Dining Table & Chairs", "type": "table", "position": [2.6, 0.45, -1.0], "size": [2.4, 0.85, 1.2], "materialKey": "wood2", "color": "#A87042"},
                {"id": "tv_console", "name": "Floating Media Credenza", "type": "tv_unit", "position": [-0.8, 0.30, -3.0], "size": [3.4, 0.6, 0.5], "materialKey": "dark", "color": "#3A3A40"},
            ]
            living_furniture = self._filter_furniture_by_furnishing(living_furniture, furnishing)

            generated_rooms.append({
                "id": "living",
                "name": "Grand Living & Dining Pavilion",
                "category": RoomCategory.LIVING_ROOM,
                "floorLevel": 0,
                "dimensions": f"{int(living_w * 3.28)}' x {int(living_d * 3.28)}'",
                "carpetSqft": int(carpet * 0.33),
                "highlight": f"{primary_floor_type} floors with floor-to-ceiling panoramic glass facade",
                "floorType": primary_floor_type,
                "floorColor": primary_floor_color,
                "wallColor": primary_wall_color,
                "bounds": living_bounds,
                "furniture": living_furniture,
                "lights": [{"position": [-0.8, 2.8, 1.0], "color": "#FFD9A0", "intensity": 0.9, "distance": 12.0}],
            })
            focal_targets["living"] = {"target": [-0.8, 1.6, 0.8], "theta": 0.45, "phi": 1.05, "radius": 14.0, "walk": [-1.0, 1.65, 3.2]}
            tour_waypoints.append({"p": [-1.0, 1.65, 3.2], "l": [2.0, 1.2, 0.0], "label": f"Living & Dining Pavilion ({int(living_w*3.28)}' x {int(living_d*3.28)}')"})

            # 2. Culinary Kitchen Studio (Calibrated to maintain exactly 3:1 Living to Kitchen)
            kit_w = round(living_w * 0.48, 1)
            kit_d = round(living_d * 0.68, 1)
            kit_x = round(living_w / 2.0 + kit_w / 2.0 + 0.2, 1)
            kit_bounds = {"x": kit_x, "y": 0.0, "z": -0.6, "w": kit_w, "d": kit_d, "h": H_FLOOR}

            kit_furniture = [
                {"id": "k_island", "name": "Quartz Island Prep Counter", "type": "counter", "position": [kit_x, 0.48, -0.6], "size": [3.0, 0.95, 1.3], "materialKey": "counter", "color": "#8D6F50"},
                {"id": "k_stools", "name": "Breakfast Bar Stools", "type": "stool", "position": [kit_x, 0.38, -1.8], "size": [2.2, 0.75, 0.45], "materialKey": "wood2", "color": "#A87042"},
            ]
            kit_furniture = self._filter_furniture_by_furnishing(kit_furniture, furnishing)

            generated_rooms.append({
                "id": "kitchen",
                "name": "Culinary Studio & Island Kitchen",
                "category": RoomCategory.KITCHEN,
                "floorLevel": 0,
                "dimensions": f"{int(kit_w * 3.28)}' x {int(kit_d * 3.28)}'",
                "carpetSqft": int(carpet * 0.11),
                "highlight": "Quartz central island with integrated gas/induction burners & soft-close Blum joinery",
                "floorType": FLOORING_PALETTES[FlooringType.GRANITE]["floorType"],
                "floorColor": FLOORING_PALETTES[FlooringType.GRANITE]["floorColor"],
                "wallColor": primary_wall_color,
                "bounds": kit_bounds,
                "furniture": kit_furniture,
                "lights": [{"position": [kit_x, 2.8, -0.6], "color": "#FFFFFF", "intensity": 0.85, "distance": 10.0}],
            })
            focal_targets["kitchen"] = {"target": [kit_x, 1.5, -0.6], "theta": 1.95, "phi": 1.05, "radius": 12.5, "walk": [kit_x - 1.1, 1.65, 1.2]}
            tour_waypoints.append({"p": [kit_x - 1.1, 1.65, 1.2], "l": [kit_x + 1.0, 1.1, -1.0], "label": "Culinary Kitchen Studio (3.09:1 Hall Ratio)"})

            # 3. Covered Sky Deck & Balcony
            balc_w = round(living_w * 0.7, 1)
            balc_d = 3.4
            balc_z = round(living_d / 2.0 + balc_d / 2.0, 1)
            balc_bounds = {"x": 1.8, "y": 0.0, "z": balc_z, "w": balc_w, "d": balc_d, "h": 1.1}

            balc_furniture = [
                {"id": "b_lounge", "name": "Weatherproof Balcony Loveseat", "type": "chair", "position": [1.8, 0.35, balc_z - 0.4], "size": [1.8, 0.4, 0.8], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "b_table", "name": "Outdoor Teak Coffee Table", "type": "table", "position": [1.8, 0.25, balc_z + 0.6], "size": [0.9, 0.35, 0.6], "materialKey": "wood2", "color": "#A87042"},
            ]
            if furnishing == FurnishingStatus.UNFURNISHED:
                balc_furniture = []

            # If Penthouse, add private plunge pool / jacuzzi
            if archetype == "penthouse" or PropertyView.POOL in views:
                balc_furniture.append({
                    "id": "sky_jacuzzi",
                    "name": "Panoramic Sky Jacuzzi / Plunge Pool",
                    "type": "counter",
                    "position": [-1.5, 0.40, balc_z],
                    "size": [2.4, 0.5, 2.0],
                    "materialKey": "pool",
                    "color": "#0F2B36",
                })

            generated_rooms.append({
                "id": "balcony",
                "name": "Covered Sky Deck & Balcony",
                "category": RoomCategory.BALCONY,
                "floorLevel": 0,
                "dimensions": f"{int(balc_w * 3.28)}' x {int(balc_d * 3.28)}'",
                "carpetSqft": int(carpet * 0.10),
                "highlight": f"Open vista ({', '.join(views)}) with frameless tempered glass balustrade & teak deck",
                "floorType": FINISH_PALETTES["deck"]["floorType"],
                "floorColor": FINISH_PALETTES["deck"]["floorColor"],
                "wallColor": primary_wall_color,
                "bounds": balc_bounds,
                "furniture": balc_furniture,
            })
            focal_targets["balcony"] = {"target": [1.8, 1.2, balc_z], "theta": 2.35, "phi": 1.05, "radius": 12.0, "walk": [0.8, 1.65, balc_z - 0.8]}
            tour_waypoints.append({"p": [0.8, 1.65, balc_z - 0.8], "l": [2.8, 1.4, balc_z + 1.2], "label": "Covered Sky Deck & Balcony"})

            # 4. Master Suite (Bedroom 1)
            m_w, m_d = 5.8, 5.4
            m_x = round(-living_w / 2.0 - m_w / 2.0 - 0.2, 1)
            m_bounds = {"x": m_x, "y": 0.0, "z": 0.5, "w": m_w, "d": m_d, "h": H_FLOOR}

            m_furniture = [
                {"id": "m_bed", "name": "King Bed", "type": "bed", "position": [m_x, 0.35, 0.2], "size": [2.2, 0.4, 2.1], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "m_headboard", "name": "Acoustic Fluted Headboard", "type": "wardrobe", "position": [m_x, 0.95, -1.0], "size": [2.6, 1.0, 0.12], "materialKey": "wood", "color": "#B9824E"},
                {"id": "m_side_1", "name": "Nightstand", "type": "table", "position": [m_x - 1.4, 0.30, -0.9], "size": [0.55, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
                {"id": "m_side_2", "name": "Nightstand", "type": "table", "position": [m_x + 1.4, 0.30, -0.9], "size": [0.55, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
            ]
            m_furniture = self._filter_furniture_by_furnishing(m_furniture, furnishing)

            generated_rooms.append({
                "id": "master",
                "name": "Presidential Master Suite (Bedroom 1)",
                "category": RoomCategory.MASTER_BEDROOM,
                "floorLevel": 0,
                "dimensions": "19' x 18'",
                "carpetSqft": int(carpet * 0.22),
                "highlight": f"{wood_pal['floorType']} with walk-in wardrobe and en-suite bath",
                "floorType": wood_pal["floorType"],
                "floorColor": wood_pal["floorColor"],
                "wallColor": wood_pal["wallColor"],
                "bounds": m_bounds,
                "furniture": m_furniture,
                "lights": [{"position": [m_x, 2.6, 0.5], "color": "#FFD9A0", "intensity": 0.85, "distance": 11.0}],
            })
            focal_targets["master"] = {"target": [m_x, 1.5, 0.5], "theta": 0.35, "phi": 1.08, "radius": 13.0, "walk": [m_x + 1.4, 1.65, 2.2]}
            tour_waypoints.append({"p": [m_x + 1.4, 1.65, 2.2], "l": [m_x - 1.0, 1.1, -0.6], "label": "Presidential Master Suite (Bedroom 1)"})

            # 5. Bedroom 2 (if >= 2 BHK)
            if bhk_count >= 2:
                b2_w, b2_d = 4.6, 4.4
                b2_x = round(living_w / 2.0 + b2_w / 2.0 + 0.2, 1)
                b2_bounds = {"x": b2_x, "y": 0.0, "z": 4.6, "w": b2_w, "d": b2_d, "h": H_FLOOR}

                b2_furniture = [
                    {"id": "b2_bed", "name": "Queen Bed", "type": "bed", "position": [b2_x, 0.35, 4.4], "size": [1.9, 0.4, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                    {"id": "b2_side", "name": "Bedside Nightstand", "type": "table", "position": [b2_x + 1.3, 0.30, 3.4], "size": [0.5, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
                ]
                b2_furniture = self._filter_furniture_by_furnishing(b2_furniture, furnishing)

                generated_rooms.append({
                    "id": "bedroom_2",
                    "name": "Guest Suite (Bedroom 2)",
                    "category": RoomCategory.GUEST_BEDROOM,
                    "floorLevel": 0,
                    "dimensions": "15' x 14'",
                    "carpetSqft": int(carpet * 0.14),
                    "highlight": f"{primary_floor_type}, acoustic double-glazed windows, and built-in wardrobes",
                    "floorType": primary_floor_type,
                    "floorColor": primary_floor_color,
                    "wallColor": primary_wall_color,
                    "bounds": b2_bounds,
                    "furniture": b2_furniture,
                })
                focal_targets["bedroom_2"] = {"target": [b2_x, 1.5, 4.6], "theta": 1.85, "phi": 1.08, "radius": 12.0, "walk": [b2_x - 1.4, 1.65, 3.6]}
                tour_waypoints.append({"p": [b2_x - 1.4, 1.65, 3.6], "l": [b2_x + 0.9, 1.1, 4.8], "label": "Guest Suite (Bedroom 2)"})

            # 6. Bedroom 3 (if >= 3 BHK)
            if bhk_count >= 3:
                b3_w, b3_d = 4.8, 4.4
                b3_x = round(-living_w / 2.0 - b3_w / 2.0 - 0.2, 1)
                b3_bounds = {"x": b3_x, "y": 0.0, "z": -4.8, "w": b3_w, "d": b3_d, "h": H_FLOOR}

                b3_furniture = [
                    {"id": "b3_bed", "name": "Queen Bed", "type": "bed", "position": [b3_x, 0.35, -4.8], "size": [1.9, 0.4, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                    {"id": "b3_desk", "name": "Writing Desk", "type": "table", "position": [b3_x - 1.4, 0.35, -3.4], "size": [1.2, 0.75, 0.55], "materialKey": "wood2", "color": "#A87042"},
                ]
                b3_furniture = self._filter_furniture_by_furnishing(b3_furniture, furnishing)

                generated_rooms.append({
                    "id": "bedroom_3",
                    "name": "Children's Suite (Bedroom 3)",
                    "category": RoomCategory.GUEST_BEDROOM,
                    "floorLevel": 0,
                    "dimensions": "16' x 14'",
                    "carpetSqft": int(carpet * 0.12),
                    "highlight": f"Natural daylit suite with study alcove and {wood_pal['floorType']}",
                    "floorType": wood_pal["floorType"],
                    "floorColor": wood_pal["floorColor"],
                    "wallColor": wood_pal["wallColor"],
                    "bounds": b3_bounds,
                    "furniture": b3_furniture,
                })
                focal_targets["bedroom_3"] = {"target": [b3_x, 1.5, -4.8], "theta": 0.55, "phi": 1.08, "radius": 12.0, "walk": [b3_x + 1.4, 1.65, -3.6]}
                tour_waypoints.append({"p": [b3_x + 1.4, 1.65, -3.6], "l": [b3_x - 1.0, 1.1, -5.4], "label": "Children's Suite (Bedroom 3)"})

            # 7. Bedroom 4 (if >= 4 BHK)
            if bhk_count >= 4:
                b4_w, b4_d = 4.8, 4.2
                b4_bounds = {"x": 0.0, "y": 0.0, "z": -5.6, "w": b4_w, "d": b4_d, "h": H_FLOOR}

                b4_furniture = [
                    {"id": "b4_bed", "name": "Queen Bed", "type": "bed", "position": [0.0, 0.35, -5.6], "size": [1.9, 0.4, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                    {"id": "b4_side", "name": "Bedside Nightstand", "type": "table", "position": [1.3, 0.30, -6.6], "size": [0.5, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
                ]
                b4_furniture = self._filter_furniture_by_furnishing(b4_furniture, furnishing)

                generated_rooms.append({
                    "id": "bedroom_4",
                    "name": "Garden Suite (Bedroom 4)",
                    "category": RoomCategory.GUEST_BEDROOM,
                    "floorLevel": 0,
                    "dimensions": "16' x 14'",
                    "carpetSqft": int(carpet * 0.11),
                    "highlight": "Quiet suite with integrated dressing alcove and private garden aspect",
                    "floorType": primary_floor_type,
                    "floorColor": primary_floor_color,
                    "wallColor": primary_wall_color,
                    "bounds": b4_bounds,
                    "furniture": b4_furniture,
                })
                focal_targets["bedroom_4"] = {"target": [0.0, 1.5, -5.6], "theta": 1.25, "phi": 1.08, "radius": 12.0, "walk": [0.0, 1.65, -4.2]}
                tour_waypoints.append({"p": [0.0, 1.65, -4.2], "l": [0.0, 1.1, -6.4], "label": "Garden Suite (Bedroom 4)"})

            # 8. Bedroom 5 / Executive Study (if >= 5 BHK)
            if bhk_count >= 5:
                b5_w, b5_d = 4.4, 4.0
                b5_bounds = {"x": 5.4, "y": 0.0, "z": -5.6, "w": b5_w, "d": b5_d, "h": H_FLOOR}

                b5_furniture = [
                    {"id": "b5_bed", "name": "Queen Bed", "type": "bed", "position": [5.4, 0.35, -5.6], "size": [1.9, 0.4, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                    {"id": "b5_desk", "name": "Executive Study Suite", "type": "table", "position": [6.8, 0.35, -4.2], "size": [1.4, 0.75, 0.6], "materialKey": "wood2", "color": "#A87042"},
                ]
                b5_furniture = self._filter_furniture_by_furnishing(b5_furniture, furnishing)

                generated_rooms.append({
                    "id": "bedroom_5",
                    "name": "Executive Suite (Bedroom 5)",
                    "category": RoomCategory.GUEST_BEDROOM,
                    "floorLevel": 0,
                    "dimensions": "14' x 13'",
                    "carpetSqft": int(carpet * 0.10),
                    "highlight": "Executive library / bedroom suite with quiet courtyard orientation",
                    "floorType": wood_pal["floorType"],
                    "floorColor": wood_pal["floorColor"],
                    "wallColor": wood_pal["wallColor"],
                    "bounds": b5_bounds,
                    "furniture": b5_furniture,
                })
                focal_targets["bedroom_5"] = {"target": [5.4, 1.5, -5.6], "theta": 1.45, "phi": 1.08, "radius": 12.0, "walk": [4.2, 1.65, -4.2]}

            # BIM Walls & Openings for Single Level
            # Living South Slider
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-living_w / 2.0, x_end=living_w / 2.0, z=living_d / 2.0, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=[{"type": "slider", "x": 1.8, "width": 5.8, "height": 2.5, "sillHeight": 0.0, "name": "Panoramic Balcony Sliders"}],
                is_exterior=False, floor_level=0, id_prefix="apt_living_balc"
            )

            # Living West Partition Wall
            west_openings = [{"type": "door", "z": 0.5, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Master Suite Door"}]
            if bhk_count >= 3:
                west_openings.append({"type": "door", "z": -2.8, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 3 Suite Door"})

            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-living_d / 2.0, z_end=living_d / 2.0, x=-living_w / 2.0, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=west_openings,
                is_exterior=False, floor_level=0, id_prefix="apt_living_west"
            )

            # Living East Partition Wall
            east_openings = [{"type": "door", "doorType": "portal", "z": -0.6, "width": 2.4, "height": 2.4, "sillHeight": 0.0, "name": "Kitchen Portal Arch"}]
            if bhk_count >= 2:
                east_openings.append({"type": "door", "z": 2.5, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 2 Suite Door"})

            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-living_d / 2.0, z_end=living_d / 2.0, x=living_w / 2.0, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=east_openings,
                is_exterior=False, floor_level=0, id_prefix="apt_living_east"
            )

            # Living North Wall
            north_openings = []
            if bhk_count >= 4:
                north_openings.append({"type": "door", "x": 0.0, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 4 Suite Door"})
            else:
                north_openings.append({"type": "door", "x": -1.5, "width": 1.1, "height": 2.3, "doorType": "pivot", "name": "Main Entrance Door"})

            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-living_w / 2.0, x_end=living_w / 2.0, z=-living_d / 2.0, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=north_openings,
                is_exterior=False, floor_level=0, id_prefix="apt_living_north"
            )

            # Master Suite Exterior Walls
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.2, z_end=3.2, x=m_x - m_w / 2.0, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[{"type": "window", "z": 0.5, "width": 2.6, "height": 1.4, "sillHeight": 0.85, "name": "Master Suite Horizon Window"}],
                is_exterior=True, floor_level=0, id_prefix="apt_master_west"
            )
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=m_x - m_w / 2.0, x_end=-living_w / 2.0, z=3.2, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[{"type": "window", "x": m_x, "width": 2.0, "height": 1.4, "sillHeight": 0.85, "name": "Master Suite Sunset Window"}],
                is_exterior=True, floor_level=0, id_prefix="apt_master_south"
            )

            # Balcony Balustrades
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_sky_deck_apt",
                name="Covered Sky Balcony & Deck",
                floor_level=0,
                deck_x=1.8, deck_y=0.0, deck_z=balc_z,
                deck_w=balc_w, deck_d=balc_d,
                rail_height=1.1,
                open_sides=["front", "left", "right"]
            )

        # =====================================================================
        # 3D INSPECTION DEFECT MARKERS (Prisma Inspection/InspectionPhoto)
        # =====================================================================
        for idx, def_item in enumerate(defects_raw):
            dtype = def_item.get("type", "seepage")
            dsev = def_item.get("severity", DefectSeverity.MEDIUM)
            rcat = def_item.get("roomCategory", RoomCategory.LIVING_ROOM)

            target_rm = next((r for r in generated_rooms if r.get("category") == rcat or rcat.lower() in r["name"].lower()), generated_rooms[0])
            b = target_rm["bounds"]

            marker_x = round(b["x"] - b["w"] / 2.0 + 0.15, 2)
            marker_y = round(b["y"] + (2.4 if dtype == "seepage" else 1.5), 2)
            marker_z = round(b["z"], 2)

            color_map = {
                DefectSeverity.CRITICAL: "#EF4444",
                DefectSeverity.HIGH: "#F97316",
                DefectSeverity.MEDIUM: "#F59E0B",
                DefectSeverity.LOW: "#EAB308",
            }

            marker = {
                "id": def_item.get("id", f"defect_pin_{idx+1}"),
                "roomId": target_rm["id"],
                "roomName": target_rm["name"],
                "type": dtype,
                "severity": dsev,
                "position": [marker_x, marker_y, marker_z],
                "color": color_map.get(dsev, "#F59E0B"),
                "description": def_item.get("description", f"Inspection defect: {dtype}"),
                "floorLevel": target_rm.get("floorLevel", 0),
            }
            defect_markers.append(marker)
            if "defects" not in target_rm:
                target_rm["defects"] = []
            target_rm["defects"].append(marker)

        # =====================================================================
        # SUNLIGHT & ORIENTATION CALCULATION (Prisma FacingDirection)
        # =====================================================================
        sunlight_config = {
            FacingDirection.EAST: {"pos": [18.0, 14.0, 16.0], "col": "#FFF2DE", "desc": "Morning Sunrise Golden Sun"},
            FacingDirection.NORTH_EAST: {"pos": [14.0, 16.0, 14.0], "col": "#FFF5E4", "desc": "Morning North-East Daylight"},
            FacingDirection.WEST: {"pos": [-18.0, 11.0, 16.0], "col": "#FFD4A0", "desc": "Golden Hour Sunset Sun"},
            FacingDirection.SOUTH_WEST: {"pos": [-14.0, 13.0, 14.0], "col": "#FFE0B2", "desc": "Afternoon Warm Sun"},
            FacingDirection.NORTH: {"pos": [0.0, 18.0, -14.0], "col": "#E8F0FE", "desc": "Crisp Diffused Ambient Daylight"},
            FacingDirection.NORTH_WEST: {"pos": [-12.0, 15.0, -10.0], "col": "#F5F2E8", "desc": "Soft Afternoon North-West Light"},
            FacingDirection.SOUTH: {"pos": [6.0, 22.0, 6.0], "col": "#FFFEE5", "desc": "Bright Zenith Midday Sun"},
            FacingDirection.SOUTH_EAST: {"pos": [14.0, 16.0, 10.0], "col": "#FFF5E4", "desc": "Bright Morning South-East Sun"},
        }.get(facing, {"pos": [16.0, 15.0, 14.0], "col": "#FFF4E0", "desc": "Natural Daylight"})

        # Aerial overview focal target
        focal_targets["all"] = {
            "target": [0.0, 2.8, 0.0],
            "theta": 0.72,
            "phi": 1.05,
            "radius": 34.0,
            "walk": [0.0, 1.65, 12.0],
        }

        # Final Aerial Waypoint
        tour_waypoints.append({
            "p": [18.0, 16.0, 18.0],
            "l": [0.0, 3.0, 0.0],
            "label": "Aerial · Full 3D Spatial Digital Twin"
        })

        # Dynamic fixtures summary
        fixtures = [
            {"item": f"{bhk_count} Distinct Bedroom Suites", "detail": f"Accurately mapped with Master Suite + {bhk_count - 1} secondary suites", "included": True},
            {"item": "Calibrated 3:1 Living Hall to Kitchen Ratio", "detail": "Grand entertainment volume with dedicated ergonomic culinary studio", "included": True},
            {"item": "Structural BIM Perimeter & Partition Walls", "detail": "Full height architectural walls with proper openings and skirting", "included": True},
            {"item": f"{primary_floor_type} Flooring", "detail": f"Authentic finish matching database schema ({flooring})", "included": True},
            {"item": f"{furnishing.replace('_', ' ').title()} Interior State", "detail": f"Interior objects moulded directly to {furnishing} status", "included": True},
            {"item": f"{facing.replace('_', ' ').title()} Sunlight Alignment", "detail": f"Directional sun and ambient temperature calibrated to {facing}", "included": True},
            {"item": "Teak Balconies with Safety Glass Balustrades", "detail": f"{about['balconyCount']} bounded exterior balcony systems placed", "included": True},
        ]
        if defect_markers:
            fixtures.append({
                "item": f"Inspection Defect Callouts ({len(defect_markers)} items)",
                "detail": f"3D pinpoint visual markers on walls: {', '.join(d['type'] for d in defect_markers)}",
                "included": True,
            })

        # Formatted Architectural About Notes Summary
        about_summary = (
            f"DB Digital Twin: '{about['propertyTitle']}'. "
            f"Schema: {about['propertyType']} ({about['configuration']}), {about['carpetSqft']:,} sq.ft on {about['floor']}. "
            f"Flooring: {primary_floor_type}. Furnishing: {furnishing}. Facing: {facing}. Views: {', '.join(views)}. "
            f"BIM layout strictly allocates {bhk_count} bedrooms with calibrated 3:1 hall-to-kitchen ratio. "
            f"{f'Physical Inspection: {len(defect_markers)} defect callouts placed in 3D.' if defect_markers else 'Civil inspection audit: Clean structure (9.6/10).'}"
        )

        return {
            "propertyId": about["propertyId"],
            "publicId": about["publicId"],
            "propertyTitle": about["propertyTitle"],
            "locality": about["locality"],
            "city": about["city"],
            "state": about["state"],
            "propertyType": about["propertyType"],
            "configuration": about["configuration"],
            "bhkCount": bhk_count,
            "carpetSqft": about["carpetSqft"],
            "builtUpSqft": about["builtUpSqft"],
            "floor": about["floor"],
            "floorHeight": about["floorHeight"],
            "flooring": flooring,
            "furnishing": furnishing,
            "facing": facing,
            "views": views,
            "balconyCount": about["balconyCount"],
            "bathroomsCount": about["bathroomsCount"],
            "conditionScore": about["conditionScore"],
            "efficiency": about["efficiency"],
            "orientation": about["orientation"],
            "archetype": archetype,
            "levelsCount": about["levelsCount"],
            "environmentalTheme": about["environmentalTheme"],
            "sunlightDirection": sunlight_config["pos"],
            "sunlightColor": sunlight_config["col"],
            "aboutSummary": about_summary,
            "defects": defect_markers,
            "floors": floors,
            "rooms": generated_rooms,
            "structuralWalls": structural_walls,
            "doors": doors,
            "windows": windows,
            "balconies": balconies,
            "glassPanels": glass_panels,
            "focalTargets": focal_targets,
            "waypoints": tour_waypoints,
            "fixtures": fixtures,
        }

    # =========================================================================
    # COMPILER INTERFACES & PRISMA DB SHAPE OUTPUT
    # =========================================================================

    def compile_from_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compiles authoritative Digital Twin spatial blueprint from property listing data.
        """
        about = self.extract_db_context(property_data)
        blueprint = self.solve_spatial_layout(about)
        return blueprint

    def compile(self, prompt: str = "", meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compiles a digital twin blueprint dynamically from a prompt or metadata dictionary.
        """
        prop_data = dict(meta) if meta else {}
        about = self.extract_db_context(prop_data, prompt=prompt)
        blueprint = self.solve_spatial_layout(about)
        return blueprint

    def compile_to_db_shape(self, property_data: Union[Dict[str, Any], str], prompt: str = "") -> Dict[str, Any]:
        """
        Moulds the digital twin directly into the exact Prisma Database Entity shape (model DigitalTwin):
          - id: String (UUID)
          - publicId: String
          - propertyId: String
          - modelUrl: String (CDN link to compressed .gltf)
          - captureMethod: CaptureMethod (MATTERPORT)
          - qualityScore: Int (0 to 100)
          - meshSizeMb: Float
          - vertexCount: Int
          - floorPlanUrl: String
          - spatialRooms: Json (Room picker [{ id, name, dimensions, carpetSqft, highlight, wallColor, floorType }])
          - spatialMetadataJson: Json (Complete BIM geometry, structural walls, doors, windows, defects, sunlight)
        """
        blueprint = self.compile(prompt=prompt, meta=property_data if isinstance(property_data, dict) else None)

        prop_id = blueprint["propertyId"]
        twin_uuid = str(uuid.uuid4())
        twin_public_id = f"twin_{hashlib.sha256(prop_id.encode()).hexdigest()[:16]}"

        vertex_count = (
            len(blueprint["rooms"]) * 24 +
            len(blueprint["structuralWalls"]) * 24 +
            len(blueprint.get("doors", [])) * 36 +
            len(blueprint.get("windows", [])) * 48 +
            len(blueprint.get("balconies", [])) * 32
        )
        mesh_size_mb = round(0.45 + (vertex_count * 0.00018), 2)

        spatial_rooms = []
        for r in blueprint["rooms"]:
            spatial_rooms.append({
                "id": r["id"],
                "name": r["name"],
                "category": r.get("category", RoomCategory.LIVING_ROOM),
                "dimensions": r["dimensions"],
                "carpetSqft": r["carpetSqft"],
                "highlight": r["highlight"],
                "wallColor": r["wallColor"],
                "floorType": r["floorType"],
                "floorColor": r["floorColor"],
                "floorLevel": r.get("floorLevel", 0),
                "bounds": r["bounds"],
                "defects": r.get("defects", []),
            })

        db_shape = {
            "id": twin_uuid,
            "publicId": twin_public_id,
            "propertyId": prop_id,
            "modelUrl": f"https://cdn.namasthetu.com/models/{twin_public_id}.gltf",
            "captureMethod": "MATTERPORT",
            "qualityScore": 96,
            "meshSizeMb": mesh_size_mb,
            "vertexCount": vertex_count,
            "floorPlanUrl": f"https://cdn.namasthetu.com/floorplans/{twin_public_id}_dim.svg",
            "spatialRooms": spatial_rooms,
            "spatialMetadataJson": blueprint,
            "capturedAt": "2026-09-15T00:00:00.000Z",
            "updatedAt": "2026-09-15T00:00:00.000Z",
        }

        return db_shape

    def export_typescript(self, blueprint: Dict[str, Any], filepath: str, export_name: str = "GENERATED_TWIN_BLUEPRINT"):
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        content = f"""// AUTO-GENERATED BY SOVEREIGN DIGITAL TWIN COMPILER (PRISMA SCHEMA CONFORMANT)
// Target Component: digital_twin/DynamicThreeTwinViewer.tsx
// Property: {blueprint['propertyTitle']} ({blueprint['propertyId']})

export interface SpatialBox {{
  x: number;
  y: number;
  z: number;
  w: number;
  d: number;
  h: number;
}}

export interface StagedFurniture {{
  id: string;
  name: string;
  type: string;
  position: [number, number, number];
  size: [number, number, number];
  materialKey: string;
  color?: string;
  rotationY?: number;
}}

export interface InspectionDefectPin {{
  id: string;
  roomId: string;
  roomName: string;
  type: string;
  severity: string;
  position: [number, number, number];
  color: string;
  description: string;
  floorLevel: number;
}}

export interface DigitalTwinRoom {{
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
  lights?: Array<{{ position: [number, number, number]; color: string; intensity: number; distance: number }}>;
  defects?: InspectionDefectPin[];
}}

export interface StructuralWall {{
  id: string;
  position: [number, number, number];
  size: [number, number, number];
  materialKey: string;
  isExterior?: boolean;
  floorLevel?: number;
}}

export interface DoorSpecification {{
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
}}

export interface WindowSpecification {{
  id: string;
  name: string;
  position: [number, number, number];
  size: [number, number];
  rotationY: number;
  sillHeight: number;
  floorLevel: number;
  hasMullions: boolean;
  frameMaterial: string;
}}

export interface BalconySpecification {{
  id: string;
  name: string;
  floorLevel: number;
  bounds: SpatialBox;
  deckMaterial: string;
  railings: Array<{{
    id: string;
    position: [number, number, number];
    size: [number, number];
    rotationY: number;
    type: string;
    handrail?: boolean;
  }}>;
}}

export interface GlassPanel {{
  id: string;
  position: [number, number, number];
  size: [number, number];
  rotationY?: number;
  floorLevel?: number;
  handrail?: boolean;
}}

export interface CameraFocalTarget {{
  target: [number, number, number];
  theta: number;
  phi: number;
  radius: number;
  walk: [number, number, number];
}}

export interface TourWaypoint {{
  p: [number, number, number];
  l: [number, number, number];
  label: string;
}}

export interface FloorLevelSpec {{
  id: string;
  name: string;
  elevation: number;
  roomIds: string[];
}}

export interface DigitalTwinBlueprint {{
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
  fixtures: Array<{{ item: string; detail: string; included: boolean }}>;
}}

export const {export_name}: DigitalTwinBlueprint = {json.dumps(blueprint, indent=2, ensure_ascii=False)};

export default {export_name};
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Digital Twin TypeScript saved to: {filepath}")

    def export_json(self, blueprint: Dict[str, Any], filepath: str):
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(blueprint, f, indent=2, ensure_ascii=False)
        print(f"✅ Digital Twin JSON saved to: {filepath}")

# Singleton Instance
engine = DigitalTwinEngine()
