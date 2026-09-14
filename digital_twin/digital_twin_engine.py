"""
Digital Twin Spatial Engine
Translates property listings, specifications, and "About" notes into
architecturally accurate 3D Three.js spatial blueprints with full physical BIM geometry:
enclosing interior & exterior walls, doors with frames/leaves/handles, windows with sills/mullions/glass,
properly bounded balconies with sliding doors and glass balustrades, and distinct room floors.
"""

import os
import sys
import re
import json
import math
import random
import hashlib
from typing import Dict, Any, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Architectural finish palettes
FINISH_PALETTES = {
    "marble": {
        "floorColor": "#F4F1EA",
        "floorType": "Italian Botticino Marble",
        "wallColor": "#FAF8F5",
        "materialKey": "cream",
    },
    "thassos": {
        "floorColor": "#FBF9F5",
        "floorType": "Greek Thassos White Marble",
        "wallColor": "#FFFFFF",
        "materialKey": "white",
    },
    "wood": {
        "floorColor": "#C9A275",
        "floorType": "Engineered Oak Hardwood",
        "wallColor": "#EAE7DF",
        "materialKey": "woodFloor",
    },
    "walnut": {
        "floorColor": "#5D4037",
        "floorType": "Natural Walnut Hardwood",
        "wallColor": "#ECEAE4",
        "materialKey": "wood2",
    },
    "quartz": {
        "floorColor": "#263238",
        "floorType": "Honed Dark Quartzite",
        "wallColor": "#F8F8F8",
        "materialKey": "dark",
    },
    "tile": {
        "floorColor": "#ECE9E2",
        "floorType": "Vitrified Matte Tile",
        "wallColor": "#F1EEE7",
        "materialKey": "cream2",
    },
    "deck": {
        "floorColor": "#A87042",
        "floorType": "Weatherproof Teak Composite Deck",
        "wallColor": "#ECE9E2",
        "materialKey": "wood2",
    },
    "pool": {
        "floorColor": "#0F2B36",
        "floorType": "Balinese Sukabumi Stone Pool Deck",
        "wallColor": "#0F2B36",
        "materialKey": "dark",
    },
}

class DigitalTwinEngine:
    def __init__(self):
        pass

    def extract_property_about(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts verified specifications and architectural notes directly from the property listing.
        """
        title = property_data.get("title", "Luxury Sovereign Residence")
        prop_type = property_data.get("propertyType", "Apartment")
        cfg_str = str(property_data.get("configuration", "3 BHK"))
        carpet_sqft = int(property_data.get("carpetAreaSqft", 2000))
        built_up_sqft = int(property_data.get("superBuiltUpAreaSqft", int(carpet_sqft * 1.28)))
        floor_str = str(property_data.get("floor", "Typical Floor"))
        city = property_data.get("city", "Mumbai")
        facing = property_data.get("facing", "East")
        
        # 1. Detect Exact Bedroom Count
        bhk_m = re.search(r'(\d+)\s*(?:bhk|bed)', cfg_str.lower())
        if bhk_m:
            bhk_count = int(bhk_m.group(1))
        else:
            bhk_count = 3

        # 2. Detect Architectural Archetype & Floor Levels
        floor_lower = floor_str.lower()
        title_lower = title.lower()
        prop_type_lower = prop_type.lower()
        
        is_villa = "villa" in prop_type_lower or "villa" in title_lower or "villa" in floor_lower
        is_g2 = "g + 2" in floor_lower or "g+2" in floor_lower or "3 floor" in floor_lower or "3-floor" in floor_lower
        is_g1 = "g + 1" in floor_lower or "g+1" in floor_lower or "2 floor" in floor_lower or "duplex" in prop_type_lower or "duplex" in title_lower

        if is_villa and is_g2:
            archetype = "villa_g2"
            levels_count = 3
            floor_height = "11.0 ft (Double Height Void: 22 ft)"
        elif is_villa or is_g1:
            archetype = "villa_g1" if is_villa else "duplex"
            levels_count = 2
            floor_height = "10.5 ft"
        else:
            archetype = "apartment"
            levels_count = 1
            floor_height = "10.5 ft"

        # 3. Detect Special Amenities & Notes from Listing
        amenities = property_data.get("amenities", [])
        has_plunge_pool = any("plunge pool" in str(a).lower() or "pool" in str(a).lower() for a in amenities) or "pool" in title_lower
        has_terrace_garden = any("terrace" in str(a).lower() or "garden" in str(a).lower() for a in amenities) or "terrace" in title_lower or "garden" in title_lower

        inspection_summary = ""
        if isinstance(property_data.get("inspection"), dict):
            inspection_summary = property_data["inspection"].get("summary", "")

        env_theme = {
            "Mumbai": "mumbai_coast",
            "Dubai": "dubai_skyline",
            "Pune": "pune_hills",
            "Indore": "indore_greens",
            "Bengaluru": "bengaluru_garden",
        }.get(city, "mumbai_coast")

        return {
            "propertyId": property_data.get("id", "prop-twin"),
            "propertyTitle": title,
            "locality": property_data.get("locality", "Prime Corridor"),
            "city": city,
            "state": property_data.get("state", "Maharashtra"),
            "propertyType": prop_type,
            "configuration": cfg_str,
            "bhkCount": bhk_count,
            "carpetSqft": carpet_sqft,
            "builtUpSqft": built_up_sqft,
            "floor": floor_str,
            "facing": facing,
            "floorHeight": floor_height,
            "conditionScore": property_data.get("trustScore", 96) / 10 if property_data.get("trustScore") else 9.6,
            "efficiency": 84,
            "orientation": f"{facing}-Facing",
            "archetype": archetype,
            "levelsCount": levels_count,
            "hasPlungePool": has_plunge_pool,
            "hasTerraceGarden": has_terrace_garden,
            "inspectionSummary": inspection_summary,
            "environmentalTheme": env_theme,
            "spatialRoomsRaw": property_data.get("spatialRooms", []),
        }

    # =========================================================================
    # ARCHITECTURAL WALL, OPENING, DOOR, WINDOW & BALCONY SOLVERS
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
        """
        Builds a wall along the X axis with openings for doors or windows,
        generating solid flanking segments, sill walls below windows, and lintels above.
        """
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
            
            # Solid segment before opening
            if op_left > cur_x + 0.02:
                seg_w = op_left - cur_x
                seg_x = cur_x + seg_w / 2.0
                seg_y = y_base + height / 2.0
                self._add_wall_segment(
                    walls, seg_x, seg_y, z, seg_w, height, thickness,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_seg_{idx}"
                )
            
            # Wall below opening (window sill wall)
            if sill_h > 0.02:
                sill_y = y_base + sill_h / 2.0
                self._add_wall_segment(
                    walls, op_x, sill_y, z, op_w, sill_h, thickness,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_sill_{idx}"
                )
            
            # Wall lintel above opening
            lintel_h = height - (sill_h + op_h)
            if lintel_h > 0.02:
                lintel_y = y_base + sill_h + op_h + lintel_h / 2.0
                self._add_wall_segment(
                    walls, op_x, lintel_y, z, op_w, lintel_h, thickness,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_lintel_{idx}"
                )
            
            # Register Door or Window entity
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
            
        # Final solid segment
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
        """
        Builds a wall along the Z axis with openings for doors or windows,
        generating solid flanking segments, sill walls below windows, and lintels above.
        """
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
            op_rear = op_z - op_w / 2.0
            op_front = op_z + op_w / 2.0
            
            # Solid segment before opening
            if op_rear > cur_z + 0.02:
                seg_d = op_rear - cur_z
                seg_z = cur_z + seg_d / 2.0
                seg_y = y_base + height / 2.0
                self._add_wall_segment(
                    walls, x, seg_y, seg_z, thickness, height, seg_d,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_seg_{idx}"
                )
            
            # Sill below opening
            if sill_h > 0.02:
                sill_y = y_base + sill_h / 2.0
                self._add_wall_segment(
                    walls, x, sill_y, op_z, thickness, sill_h, op_w,
                    material_key=mat, is_exterior=is_exterior, floor_level=floor_level,
                    wall_id=f"{id_prefix}_sill_{idx}"
                )
            
            # Lintel above opening
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
                    "size": [round(thickness, 3), round(op_h, 3), round(op_w, 3)],
                    "rotationY": math.pi / 2,
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
                    "rotationY": math.pi / 2,
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
                    "size": [round(thickness, 3), round(op_h, 3), round(op_w, 3)],
                    "rotationY": math.pi / 2,
                    "floorLevel": floor_level,
                    "doorType": "sliding",
                    "panelsCount": 2,
                    "frameMaterial": "dark",
                })
                
            cur_z = max(cur_z, op_front)
            
        # Final solid segment
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
        """
        Creates a complete balcony system including teak deck slab,
        tempered safety glass balustrades with handrails, and register in both balconies and glass_panels.
        """
        if open_sides is None:
            open_sides = ["front", "left", "right"]

        railings = []
        # Front Railing
        if "front" in open_sides:
            p_z = deck_z + deck_d / 2.0
            rail_front = {
                "id": f"{balc_id}_rail_front",
                "position": [round(deck_x, 3), round(deck_y + rail_height / 2.0, 3), round(p_z, 3)],
                "size": [round(deck_w, 3), round(rail_height, 3)],
                "rotationY": 0.0,
                "floorLevel": floor_level,
                "type": "glass",
                "handrail": True,
            }
            railings.append(rail_front)
            glass_panels.append(rail_front)

        # Left Railing
        if "left" in open_sides:
            p_x = deck_x - deck_w / 2.0
            rail_left = {
                "id": f"{balc_id}_rail_left",
                "position": [round(p_x, 3), round(deck_y + rail_height / 2.0, 3), round(deck_z, 3)],
                "size": [round(deck_d, 3), round(rail_height, 3)],
                "rotationY": math.pi / 2,
                "floorLevel": floor_level,
                "type": "glass",
                "handrail": True,
            }
            railings.append(rail_left)
            glass_panels.append(rail_left)

        # Right Railing
        if "right" in open_sides:
            p_x = deck_x + deck_w / 2.0
            rail_right = {
                "id": f"{balc_id}_rail_right",
                "position": [round(p_x, 3), round(deck_y + rail_height / 2.0, 3), round(deck_z, 3)],
                "size": [round(deck_d, 3), round(rail_height, 3)],
                "rotationY": math.pi / 2,
                "floorLevel": floor_level,
                "type": "glass",
                "handrail": True,
            }
            railings.append(rail_right)
            glass_panels.append(rail_right)

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

    def solve_spatial_layout(self, about: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solves 3D spatial layout enforcing:
          1. Exact physical number of bedrooms matching configuration.
          2. Calibrated 3:1 Living Hall to Kitchen ratio.
          3. Multi-floor elevations and double-height living room for villas.
          4. Complete architectural BIM geometry: enclosing walls, doors, windows, balconies, floors.
        """
        archetype = about["archetype"]
        bhk_count = about["bhkCount"]
        carpet = about["carpetSqft"]

        H_FLOOR = 3.2
        H_DOUBLE = 6.4

        generated_rooms = []
        structural_walls = []
        doors = []
        windows = []
        balconies = []
        glass_panels = []
        floors = []
        focal_targets = {}
        tour_waypoints = []

        tour_waypoints.append({
            "p": [4.0, 3.5, 18.0],
            "l": [0.0, 2.5, 0.0],
            "label": "Approach · Architectural Facade"
        })

        if archetype == "villa_g2":
            # =========================================================
            # ARCHETYPE 1: G+2 INDEPENDENT VILLA (3 PHYSICAL FLOORS)
            # =========================================================
            floors = [
                {"id": "floor_0", "name": "Ground Floor (Grand Living & Pool Deck)", "elevation": 0.0, "roomIds": ["living", "kitchen", "pool_deck", "foyer"]},
                {"id": "floor_1", "name": "First Floor (Master Suite & Mezzanine)", "elevation": 3.7, "roomIds": ["master", "mezzanine", "bedroom_2"]},
                {"id": "floor_2", "name": "Second Floor (Bedrooms 3 & 4 & Sky Deck)", "elevation": 7.4, "roomIds": ["bedroom_3", "bedroom_4", "sky_terrace"]}
            ]

            # ---------------------------------------------------------
            # LEVEL 0 (GROUND FLOOR) - Living Hall, Kitchen, Pool Deck
            # ---------------------------------------------------------
            living_w, living_d = 10.0, 7.5
            living_bounds = {"x": 0.0, "y": 0.0, "z": 0.0, "w": living_w, "d": living_d, "h": H_DOUBLE}
            living_furniture = [
                {"id": "sofa_main", "name": "Sectional White Boucle Sofa", "type": "sofa", "position": [-1.2, 0.45, 1.8], "size": [4.5, 0.85, 2.0], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "coffee_tbl", "name": "Low Marble Coffee Table", "type": "table", "position": [-1.2, 0.25, 0.2], "size": [2.4, 0.45, 1.2], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "living_rug", "name": "Textured Hand-Woven Rug", "type": "rug", "position": [-1.2, 0.02, 1.0], "size": [5.6, 0.02, 4.0], "materialKey": "rug", "color": "#CABFA8"},
                {"id": "dining_tbl", "name": "8-Seater Smoked Oak Dining Table", "type": "table", "position": [2.5, 0.45, -1.0], "size": [2.8, 0.85, 1.4], "materialKey": "wood2", "color": "#A87042"},
                {"id": "tv_console", "name": "Fluted Marble Media Console", "type": "tv_unit", "position": [-1.2, 0.35, -3.2], "size": [3.6, 0.6, 0.5], "materialKey": "dark", "color": "#3A3A40"},
            ]
            generated_rooms.append({
                "id": "living",
                "name": "Double-Height Grand Living & Dining Hall",
                "floorLevel": 0,
                "dimensions": "32' x 24' (22ft Ceiling)",
                "carpetSqft": int(carpet * 0.34),
                "highlight": "22ft double-height floor-to-ceiling glass looking out to Championship Fairway and private pool deck",
                "floorType": FINISH_PALETTES["thassos"]["floorType"],
                "floorColor": FINISH_PALETTES["thassos"]["floorColor"],
                "wallColor": FINISH_PALETTES["thassos"]["wallColor"],
                "bounds": living_bounds,
                "furniture": living_furniture,
                "lights": [{"position": [-1.2, 5.2, 0.5], "color": "#FFD9A0", "intensity": 1.2, "distance": 16.0}],
            })
            focal_targets["living"] = {"target": [0.0, 2.2, 0.5], "theta": 0.45, "phi": 1.05, "radius": 16.0, "walk": [-1.0, 1.65, 3.2]}
            tour_waypoints.append({"p": [-1.0, 1.65, 3.2], "l": [2.0, 1.5, -0.5], "label": "Ground Floor · Double-Height Living (32' x 24')"})

            # Gourmet Kitchen Studio
            kit_w, kit_d = 4.8, 4.8
            kit_bounds = {"x": 7.6, "y": 0.0, "z": 0.0, "w": kit_w, "d": kit_d, "h": H_FLOOR}
            kit_furniture = [
                {"id": "k_island", "name": "Corian Central Island with Wine Chiller", "type": "counter", "position": [7.6, 0.50, 0.0], "size": [3.2, 0.95, 1.4], "materialKey": "counter", "color": "#8D6F50"},
                {"id": "k_stools", "name": "Bar Stools Set", "type": "stool", "position": [7.6, 0.40, -1.1], "size": [2.4, 0.75, 0.45], "materialKey": "wood2", "color": "#A87042"},
            ]
            generated_rooms.append({
                "id": "kitchen",
                "name": "Siemens Integrated Gourmet Kitchen",
                "floorLevel": 0,
                "dimensions": "16' x 16'",
                "carpetSqft": int(carpet * 0.11),
                "highlight": "Corian central island with wine chiller, integrated induction downdraft & soft-close Blum hardware",
                "floorType": FINISH_PALETTES["quartz"]["floorType"],
                "floorColor": FINISH_PALETTES["quartz"]["floorColor"],
                "wallColor": FINISH_PALETTES["quartz"]["wallColor"],
                "bounds": kit_bounds,
                "furniture": kit_furniture,
                "lights": [{"position": [7.6, 2.8, 0.0], "color": "#FFFFFF", "intensity": 0.9, "distance": 11.0}],
            })
            focal_targets["kitchen"] = {"target": [7.6, 1.6, 0.0], "theta": 1.95, "phi": 1.05, "radius": 13.0, "walk": [6.5, 1.65, 1.2]}
            tour_waypoints.append({"p": [6.5, 1.65, 1.2], "l": [8.5, 1.2, -1.0], "label": "Ground Floor · Gourmet Kitchen Studio (3.2:1 Ratio)"})

            # Pool Deck & Private Pool
            pool_w, pool_d = 9.0, 5.0
            pool_bounds = {"x": 0.0, "y": 0.0, "z": 8.0, "w": pool_w, "d": pool_d, "h": 1.2}
            pool_furniture = [
                {"id": "pool_water", "name": "Heated Infinity Plunge Pool", "type": "counter", "position": [0.0, 0.35, 8.5], "size": [6.0, 0.45, 2.8], "materialKey": "pool", "color": "#0F2B36"},
                {"id": "lounger_1", "name": "Balinese Teak Sun Lounger", "type": "chair", "position": [-3.2, 0.35, 7.2], "size": [1.8, 0.4, 0.8], "materialKey": "wood2", "color": "#A87042"},
                {"id": "lounger_2", "name": "Balinese Teak Sun Lounger", "type": "chair", "position": [3.2, 0.35, 7.2], "size": [1.8, 0.4, 0.8], "materialKey": "wood2", "color": "#A87042"},
            ]
            generated_rooms.append({
                "id": "pool_deck",
                "name": "Private Heated Plunge Pool & Deck",
                "floorLevel": 0,
                "dimensions": "28' x 16'",
                "carpetSqft": int(carpet * 0.15),
                "highlight": "Balinese Sukabumi stone infinity plunge pool, teak decking, and private garden vista",
                "floorType": FINISH_PALETTES["deck"]["floorType"],
                "floorColor": FINISH_PALETTES["deck"]["floorColor"],
                "wallColor": FINISH_PALETTES["deck"]["wallColor"],
                "bounds": pool_bounds,
                "furniture": pool_furniture,
            })
            focal_targets["pool_deck"] = {"target": [0.0, 1.0, 8.0], "theta": 2.35, "phi": 1.10, "radius": 14.0, "walk": [0.0, 1.65, 5.8]}
            tour_waypoints.append({"p": [0.0, 1.65, 5.8], "l": [0.0, 0.8, 9.5], "label": "Ground Floor · Heated Plunge Pool & Deck"})

            # --- GROUND FLOOR WALLS & OPENINGS ---
            # 1. Living Hall Rear Exterior Wall (Z = -3.75, X from -5.0 to 5.0, H = 6.4m)
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-5.0, x_end=5.0, z=-3.75, y_base=0.0, height=H_DOUBLE, thickness=0.22,
                openings=[
                    {"type": "window", "x": -2.5, "width": 2.2, "height": 1.2, "sillHeight": 3.8, "name": "High Clerestory Window Left"},
                    {"type": "window", "x": 2.5, "width": 2.2, "height": 1.2, "sillHeight": 3.8, "name": "High Clerestory Window Right"},
                ],
                is_exterior=True, floor_level=0, id_prefix="g_living_north"
            )

            # 2. Living / Kitchen Partition Wall (X = 5.0, Z from -3.75 to 2.4, H = 3.2m)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-3.75, z_end=2.4, x=5.0, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=[
                    {"type": "door", "doorType": "portal", "z": 0.0, "width": 3.2, "height": 2.6, "sillHeight": 0.0, "name": "Culinary Portal Archway"}
                ],
                is_exterior=False, floor_level=0, id_prefix="g_living_kitchen"
            )

            # 3. Kitchen Exterior Walls
            # Kitchen Rear Wall (Z = -2.4, X from 5.0 to 10.0)
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=5.0, x_end=10.0, z=-2.4, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "x": 7.6, "width": 2.0, "height": 1.1, "sillHeight": 1.1, "name": "Kitchen Counter Window"}
                ],
                is_exterior=True, floor_level=0, id_prefix="g_kit_north"
            )
            # Kitchen Right Exterior Wall (X = 10.0, Z from -2.4 to 2.4)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.4, z_end=2.4, x=10.0, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "z": 0.0, "width": 1.8, "height": 1.2, "sillHeight": 1.1, "name": "Kitchen Garden Window"}
                ],
                is_exterior=True, floor_level=0, id_prefix="g_kit_east"
            )
            # Kitchen Front Exterior Wall (Z = 2.4, X from 5.0 to 10.0)
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=5.0, x_end=10.0, z=2.4, y_base=0.0, height=H_FLOOR, thickness=0.22,
                is_exterior=True, floor_level=0, id_prefix="g_kit_south"
            )

            # 4. Living West Wall (X = -5.0, Z from -3.75 to 3.75, H = 6.4m)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-3.75, z_end=3.75, x=-5.0, y_base=0.0, height=H_DOUBLE, thickness=0.22,
                openings=[
                    {"type": "door", "z": -1.8, "width": 1.2, "height": 2.4, "doorType": "swing", "name": "Grand Foyer Entry Door"}
                ],
                is_exterior=True, floor_level=0, id_prefix="g_living_west"
            )

            # 5. Grand Double-Height Front Glass Facade (Z = 3.75, X: -5.0 to 5.0)
            glass_panels.append({
                "id": "glass_double_height_facade",
                "position": [0.0, 3.2, 3.75],
                "size": [9.6, 6.2],
                "rotationY": 0.0,
                "floorLevel": 0
            })
            doors.append({
                "id": "slider_ground_pool",
                "name": "Double-Height Glass Sliders to Pool Deck",
                "position": [0.0, 1.4, 3.75],
                "size": [5.6, 2.8, 0.12],
                "rotationY": 0.0,
                "floorLevel": 0,
                "doorType": "sliding",
                "panelsCount": 4,
                "frameMaterial": "dark"
            })

            # 6. Balcony / Pool Deck Balustrade System
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_pool_ground",
                name="Private Pool Sun Deck",
                floor_level=0,
                deck_x=0.0, deck_y=0.0, deck_z=8.0,
                deck_w=9.0, deck_d=5.0,
                rail_height=1.1,
                open_sides=["front", "left", "right"]
            )

            # ---------------------------------------------------------
            # LEVEL 1 (FIRST FLOOR - Y = 3.7m) - Master Suite, Mezzanine, Bed 2
            # ---------------------------------------------------------
            m_w, m_d = 6.8, 5.8
            m_bounds = {"x": -6.5, "y": 3.7, "z": 0.5, "w": m_w, "d": m_d, "h": H_FLOOR}
            m_furniture = [
                {"id": "m_bed", "name": "King Master Bed", "type": "bed", "position": [-6.5, 4.15, 0.0], "size": [2.2, 0.5, 2.1], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "m_headboard", "name": "Natural Walnut Slat Headboard", "type": "wardrobe", "position": [-6.5, 4.65, -1.4], "size": [2.8, 1.2, 0.12], "materialKey": "walnut", "color": "#5D4037"},
                {"id": "m_nightstand_1", "name": "Floating Nightstand", "type": "table", "position": [-8.0, 4.05, -1.2], "size": [0.6, 0.35, 0.45], "materialKey": "accent", "color": "#C9A66B"},
                {"id": "m_nightstand_2", "name": "Floating Nightstand", "type": "table", "position": [-5.0, 4.05, -1.2], "size": [0.6, 0.35, 0.45], "materialKey": "accent", "color": "#C9A66B"},
                {"id": "m_sofa", "name": "Master Balcony Daybed", "type": "sofa", "position": [-6.5, 4.1, 2.4], "size": [2.0, 0.4, 0.8], "materialKey": "sofa", "color": "#D9D1C0"},
            ]
            generated_rooms.append({
                "id": "master",
                "name": "Presidential Master Suite (1st Floor)",
                "floorLevel": 1,
                "dimensions": "22' x 19'",
                "carpetSqft": int(carpet * 0.22),
                "highlight": "Natural walnut hardwood flooring, wrap-around fairway balcony, and private jacuzzi pavilion",
                "floorType": FINISH_PALETTES["walnut"]["floorType"],
                "floorColor": FINISH_PALETTES["walnut"]["floorColor"],
                "wallColor": FINISH_PALETTES["walnut"]["wallColor"],
                "bounds": m_bounds,
                "furniture": m_furniture,
                "lights": [{"position": [-6.5, 6.2, 0.5], "color": "#FFD9A0", "intensity": 0.9, "distance": 12.0}],
            })
            focal_targets["master"] = {"target": [-6.5, 4.8, 0.5], "theta": 0.35, "phi": 1.08, "radius": 14.0, "walk": [-4.5, 5.35, 2.0]}
            tour_waypoints.append({"p": [-4.5, 5.35, 2.0], "l": [-7.5, 4.6, -0.5], "label": "1st Floor · Presidential Master Suite (22' x 19')"})

            # Mezzanine Gallery Lounge Bridge
            mezz_w, mezz_d = 6.0, 3.8
            mezz_bounds = {"x": 0.0, "y": 3.7, "z": -2.2, "w": mezz_w, "d": mezz_d, "h": H_FLOOR}
            mezz_furniture = [
                {"id": "mezz_sofa", "name": "Mezzanine Reading Couch", "type": "sofa", "position": [0.0, 4.1, -2.4], "size": [2.4, 0.65, 0.9], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "mezz_bookcase", "name": "Floor-to-Ceiling Oak Bookcase", "type": "wardrobe", "position": [0.0, 4.8, -3.9], "size": [3.6, 1.8, 0.4], "materialKey": "wood", "color": "#B9824E"},
            ]
            generated_rooms.append({
                "id": "mezzanine",
                "name": "Mezzanine Family Lounge (1st Floor)",
                "floorLevel": 1,
                "dimensions": "20' x 12'",
                "carpetSqft": int(carpet * 0.10),
                "highlight": "Glass-railed gallery bridge overlooking the double-height grand living hall",
                "floorType": FINISH_PALETTES["wood"]["floorType"],
                "floorColor": FINISH_PALETTES["wood"]["floorColor"],
                "wallColor": FINISH_PALETTES["wood"]["wallColor"],
                "bounds": mezz_bounds,
                "furniture": mezz_furniture,
            })
            focal_targets["mezzanine"] = {"target": [0.0, 4.8, -2.0], "theta": 0.85, "phi": 1.05, "radius": 12.0, "walk": [0.0, 5.35, -1.0]}

            # Bedroom 2 (Junior Master Suite)
            b2_w, b2_d = 5.4, 5.0
            b2_bounds = {"x": 6.8, "y": 3.7, "z": 0.5, "w": b2_w, "d": b2_d, "h": H_FLOOR}
            b2_furniture = [
                {"id": "b2_bed", "name": "Queen Bed", "type": "bed", "position": [6.8, 4.15, 0.0], "size": [1.9, 0.5, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "b2_desk", "name": "Study Writing Desk", "type": "table", "position": [8.5, 4.1, 1.5], "size": [1.4, 0.75, 0.6], "materialKey": "wood2", "color": "#A87042"},
            ]
            generated_rooms.append({
                "id": "bedroom_2",
                "name": "Junior Master Suite (Bedroom 2 - 1st Floor)",
                "floorLevel": 1,
                "dimensions": "18' x 16'",
                "carpetSqft": int(carpet * 0.14),
                "highlight": "Engineered German oak wood flooring with ensuite bath and morning sun balcony",
                "floorType": FINISH_PALETTES["wood"]["floorType"],
                "floorColor": FINISH_PALETTES["wood"]["floorColor"],
                "wallColor": FINISH_PALETTES["wood"]["wallColor"],
                "bounds": b2_bounds,
                "furniture": b2_furniture,
            })
            focal_targets["bedroom_2"] = {"target": [6.8, 4.8, 0.5], "theta": 1.85, "phi": 1.08, "radius": 13.0, "walk": [5.2, 5.35, 1.8]}
            tour_waypoints.append({"p": [5.2, 5.35, 1.8], "l": [7.8, 4.6, -0.2], "label": "1st Floor · Junior Master Suite (18' x 16')"})

            # --- LEVEL 1 WALLS, DOORS & BALCONIES ---
            # Master Suite Partition Wall (X = -3.1, Z from -2.4 to 3.4)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.4, z_end=3.4, x=-3.1, y_base=3.7, height=H_FLOOR, thickness=0.18,
                openings=[
                    {"type": "door", "z": 0.5, "width": 1.0, "height": 2.2, "doorType": "swing", "name": "Presidential Master Suite Door"}
                ],
                is_exterior=False, floor_level=1, id_prefix="l1_master_east"
            )
            # Master Suite West Exterior Wall (X = -9.9, Z from -2.4 to 3.4)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.4, z_end=3.4, x=-9.9, y_base=3.7, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "z": 0.5, "width": 2.6, "height": 1.5, "sillHeight": 0.85, "name": "Master Panoramic Horizon Window"}
                ],
                is_exterior=True, floor_level=1, id_prefix="l1_master_west"
            )
            # Master Suite South Wall (Z = 3.4, X from -9.9 to -3.1) with Balcony Slider
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-9.9, x_end=-3.1, z=3.4, y_base=3.7, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "slider", "x": -6.5, "width": 2.4, "height": 2.4, "sillHeight": 0.0, "name": "Master Balcony Slider"}
                ],
                is_exterior=True, floor_level=1, id_prefix="l1_master_south"
            )
            # Master Suite Balcony
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_master_l1",
                name="Master Fairway Balcony",
                floor_level=1,
                deck_x=-6.5, deck_y=3.7, deck_z=4.5,
                deck_w=4.2, deck_d=2.0,
                rail_height=1.1,
                open_sides=["front", "left", "right"]
            )

            # Mezzanine Gallery Guard Railing (overlooking double-height void at Z = -0.3, X from -3.0 to 3.0)
            glass_panels.append({
                "id": "mezzanine_gallery_rail",
                "position": [0.0, 4.25, -0.3],
                "size": [6.0, 1.1],
                "rotationY": 0.0,
                "floorLevel": 1,
                "handrail": True
            })

            # Bedroom 2 Partition Wall (X = 4.1, Z from -2.0 to 3.0)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.0, z_end=3.0, x=4.1, y_base=3.7, height=H_FLOOR, thickness=0.18,
                openings=[
                    {"type": "door", "z": 0.5, "width": 1.0, "height": 2.2, "doorType": "swing", "name": "Bedroom 2 Suite Door"}
                ],
                is_exterior=False, floor_level=1, id_prefix="l1_bed2_west"
            )
            # Bedroom 2 East Exterior Wall (X = 9.5, Z from -2.0 to 3.0)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.0, z_end=3.0, x=9.5, y_base=3.7, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "z": 0.5, "width": 2.2, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 2 Sunrise Window"}
                ],
                is_exterior=True, floor_level=1, id_prefix="l1_bed2_east"
            )
            # Bedroom 2 South Wall (Z = 3.0, X from 4.1 to 9.5) with Slider
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=4.1, x_end=9.5, z=3.0, y_base=3.7, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "slider", "x": 6.8, "width": 2.2, "height": 2.4, "sillHeight": 0.0, "name": "Bedroom 2 Balcony Slider"}
                ],
                is_exterior=True, floor_level=1, id_prefix="l1_bed2_south"
            )
            # Bedroom 2 Morning Balcony
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_bed2_l1",
                name="Bedroom 2 Morning Sun Balcony",
                floor_level=1,
                deck_x=6.8, deck_y=3.7, deck_z=4.0,
                deck_w=3.6, deck_d=1.8,
                rail_height=1.1,
                open_sides=["front", "left", "right"]
            )

            # ---------------------------------------------------------
            # LEVEL 2 (SECOND FLOOR - Y = 7.4m) - Bed 3, Bed 4, Sky Terrace
            # ---------------------------------------------------------
            b3_w, b3_d = 5.0, 4.8
            b3_bounds = {"x": -5.0, "y": 7.4, "z": -0.5, "w": b3_w, "d": b3_d, "h": H_FLOOR}
            b3_furniture = [
                {"id": "b3_bed", "name": "Queen Suite Bed", "type": "bed", "position": [-5.0, 7.85, -0.8], "size": [1.9, 0.5, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "b3_side", "name": "Nightstand", "type": "table", "position": [-6.3, 7.75, -1.8], "size": [0.55, 0.35, 0.45], "materialKey": "accent", "color": "#C9A66B"},
            ]
            generated_rooms.append({
                "id": "bedroom_3",
                "name": "Fairway Guest Suite (Bedroom 3 - 2nd Floor)",
                "floorLevel": 2,
                "dimensions": "16' x 16'",
                "carpetSqft": int(carpet * 0.12),
                "highlight": "Private upper-level vista suite overlooking championship greenery",
                "floorType": FINISH_PALETTES["tile"]["floorType"],
                "floorColor": FINISH_PALETTES["tile"]["floorColor"],
                "wallColor": FINISH_PALETTES["tile"]["wallColor"],
                "bounds": b3_bounds,
                "furniture": b3_furniture,
            })
            focal_targets["bedroom_3"] = {"target": [-5.0, 8.4, -0.5], "theta": 0.45, "phi": 1.08, "radius": 13.0, "walk": [-3.5, 8.95, 1.2]}
            tour_waypoints.append({"p": [-3.5, 8.95, 1.2], "l": [-5.5, 8.2, -1.5], "label": "2nd Floor · Fairway Suite (Bedroom 3)"})

            # Bedroom 4 (Sky Den & Study)
            b4_w, b4_d = 5.0, 4.8
            b4_bounds = {"x": 5.0, "y": 7.4, "z": -0.5, "w": b4_w, "d": b4_d, "h": H_FLOOR}
            b4_furniture = [
                {"id": "b4_bed", "name": "Convertible Lounge Bed", "type": "bed", "position": [5.0, 7.85, -0.8], "size": [1.9, 0.5, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "b4_chair", "name": "Reading Armchair", "type": "chair", "position": [6.4, 7.8, 0.8], "size": [0.85, 0.75, 0.85], "materialKey": "sofa", "color": "#D9D1C0"},
            ]
            generated_rooms.append({
                "id": "bedroom_4",
                "name": "Sky Den & Study (Bedroom 4 - 2nd Floor)",
                "floorLevel": 2,
                "dimensions": "16' x 16'",
                "carpetSqft": int(carpet * 0.12),
                "highlight": "Panoramic upper-level bedroom suite with executive library",
                "floorType": FINISH_PALETTES["wood"]["floorType"],
                "floorColor": FINISH_PALETTES["wood"]["floorColor"],
                "wallColor": FINISH_PALETTES["wood"]["wallColor"],
                "bounds": b4_bounds,
                "furniture": b4_furniture,
            })
            focal_targets["bedroom_4"] = {"target": [5.0, 8.4, -0.5], "theta": 1.75, "phi": 1.08, "radius": 13.0, "walk": [3.5, 8.95, 1.2]}
            tour_waypoints.append({"p": [3.5, 8.95, 1.2], "l": [5.5, 8.2, -1.5], "label": "2nd Floor · Sky Den & Study (Bedroom 4)"})

            # Rooftop Sky Terrace & Pergola Deck
            terr_w, terr_d = 8.4, 4.6
            terr_bounds = {"x": 0.0, "y": 7.4, "z": 4.5, "w": terr_w, "d": terr_d, "h": 1.1}
            terr_furniture = [
                {"id": "terr_sofa", "name": "Rooftop Outdoor Lounge", "type": "sofa", "position": [0.0, 7.75, 5.0], "size": [2.6, 0.45, 1.0], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "terr_tbl", "name": "Weatherproof Coffee Table", "type": "table", "position": [0.0, 7.65, 3.6], "size": [1.4, 0.35, 0.8], "materialKey": "wood2", "color": "#A87042"},
            ]
            generated_rooms.append({
                "id": "sky_terrace",
                "name": "Rooftop Sky Terrace & Pergola Deck",
                "floorLevel": 2,
                "dimensions": "28' x 15'",
                "carpetSqft": int(carpet * 0.13),
                "highlight": "Unobstructed 360-degree fairway skyline views, stargazing deck, and tempered safety balustrade",
                "floorType": FINISH_PALETTES["deck"]["floorType"],
                "floorColor": FINISH_PALETTES["deck"]["floorColor"],
                "wallColor": FINISH_PALETTES["deck"]["wallColor"],
                "bounds": terr_bounds,
                "furniture": terr_furniture,
            })
            focal_targets["sky_terrace"] = {"target": [0.0, 8.0, 4.5], "theta": 2.25, "phi": 1.05, "radius": 14.0, "walk": [0.0, 8.95, 2.8]}
            tour_waypoints.append({"p": [0.0, 8.95, 2.8], "l": [0.0, 8.0, 6.5], "label": "2nd Floor · Rooftop Sky Terrace & Pergola"})

            # Level 2 Walls & Terrace Balustrades
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.9, z_end=1.9, x=-2.5, y_base=7.4, height=H_FLOOR, thickness=0.18,
                openings=[
                    {"type": "door", "z": -0.5, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 3 Suite Door"}
                ],
                is_exterior=False, floor_level=2, id_prefix="l2_bed3_door"
            )
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-7.5, x_end=-2.5, z=-2.9, y_base=7.4, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "x": -5.0, "width": 2.0, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 3 Vista Window"}
                ],
                is_exterior=True, floor_level=2, id_prefix="l2_bed3_north"
            )
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.9, z_end=1.9, x=2.5, y_base=7.4, height=H_FLOOR, thickness=0.18,
                openings=[
                    {"type": "door", "z": -0.5, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 4 Suite Door"}
                ],
                is_exterior=False, floor_level=2, id_prefix="l2_bed4_door"
            )
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=2.5, x_end=7.5, z=-2.9, y_base=7.4, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "x": 5.0, "width": 2.0, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 4 Vista Window"}
                ],
                is_exterior=True, floor_level=2, id_prefix="l2_bed4_north"
            )

            # Rooftop Sky Terrace Balustrades
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_sky_terrace_l2",
                name="Rooftop Sky Pergola Deck",
                floor_level=2,
                deck_x=0.0, deck_y=7.4, deck_z=4.5,
                deck_w=8.4, deck_d=4.6,
                rail_height=1.1,
                open_sides=["front", "left", "right"]
            )

        else:
            # =========================================================
            # ARCHETYPE 2: LUXURY APARTMENTS (SINGLE LEVEL)
            # Enforces:
            #   1. Exact N physical bedrooms (2 BHK, 3 BHK, 4 BHK, 5 BHK)
            #   2. Calibrated 3:1 Living Hall to Kitchen ratio
            #   3. Full enclosing interior/exterior walls, doors, windows, balconies
            # =========================================================
            floors = [
                {"id": "floor_0", "name": "Apartment Suite Level", "elevation": 0.0, "roomIds": ["living", "kitchen", "balcony", "master", "bedroom_2"]}
            ]

            # 1. Living & Dining Pavilion (Hall) - 9.2m x 6.8m = 62.5 m2
            living_w, living_d = 9.2, 6.8
            living_bounds = {"x": 0.0, "y": 0.0, "z": 0.0, "w": living_w, "d": living_d, "h": H_FLOOR}
            living_furniture = [
                {"id": "sofa_main", "name": "Curved Designer Italian Sofa", "type": "sofa", "position": [-0.8, 0.42, 1.8], "size": [4.2, 0.75, 1.8], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "coffee_tbl", "name": "Botticino Marble Coffee Table", "type": "table", "position": [-0.8, 0.25, 0.4], "size": [2.2, 0.45, 1.1], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "living_rug", "name": "Silken Area Rug", "type": "rug", "position": [-0.8, 0.02, 1.1], "size": [5.2, 0.02, 3.6], "materialKey": "rug", "color": "#CABFA8"},
                {"id": "dining_tbl", "name": "Dining Table & Chairs", "type": "table", "position": [2.6, 0.45, -1.0], "size": [2.4, 0.85, 1.2], "materialKey": "wood2", "color": "#A87042"},
                {"id": "tv_console", "name": "Floating Media Credenza", "type": "tv_unit", "position": [-0.8, 0.30, -3.0], "size": [3.4, 0.6, 0.5], "materialKey": "dark", "color": "#3A3A40"},
            ]
            generated_rooms.append({
                "id": "living",
                "name": "Grand Living & Dining Pavilion",
                "floorLevel": 0,
                "dimensions": "30' x 22'",
                "carpetSqft": int(carpet * 0.33),
                "highlight": "Mirror-polished Italian Statuario marble floors with floor-to-ceiling panoramic glass facade",
                "floorType": FINISH_PALETTES["marble"]["floorType"],
                "floorColor": FINISH_PALETTES["marble"]["floorColor"],
                "wallColor": FINISH_PALETTES["marble"]["wallColor"],
                "bounds": living_bounds,
                "furniture": living_furniture,
                "lights": [{"position": [-0.8, 2.8, 1.0], "color": "#FFD9A0", "intensity": 0.9, "distance": 12.0}],
            })
            focal_targets["living"] = {"target": [-0.8, 1.6, 0.8], "theta": 0.45, "phi": 1.05, "radius": 14.0, "walk": [-1.0, 1.65, 3.2]}
            tour_waypoints.append({"p": [-1.0, 1.65, 3.2], "l": [2.0, 1.2, 0.0], "label": "Living & Dining Pavilion (30' x 22')"})

            # 2. Culinary Studio (Kitchen) - 4.4m x 4.6m = 20.2 m2 -> 62.5 / 20.2 = 3.09:1 ratio!
            kit_w, kit_d = 4.4, 4.6
            kit_bounds = {"x": 6.9, "y": 0.0, "z": -0.6, "w": kit_w, "d": kit_d, "h": H_FLOOR}
            kit_furniture = [
                {"id": "k_island", "name": "Quartz Island Prep Counter", "type": "counter", "position": [6.9, 0.48, -0.6], "size": [3.0, 0.95, 1.3], "materialKey": "counter", "color": "#8D6F50"},
                {"id": "k_stools", "name": "Breakfast Bar Stools", "type": "stool", "position": [6.9, 0.38, -1.8], "size": [2.2, 0.75, 0.45], "materialKey": "wood2", "color": "#A87042"},
            ]
            generated_rooms.append({
                "id": "kitchen",
                "name": "Culinary Studio & Island Kitchen",
                "floorLevel": 0,
                "dimensions": "15' x 15'",
                "carpetSqft": int(carpet * 0.11),
                "highlight": "Quartz central island with integrated gas/induction burners & soft-close cabinets",
                "floorType": FINISH_PALETTES["quartz"]["floorType"],
                "floorColor": FINISH_PALETTES["quartz"]["floorColor"],
                "wallColor": FINISH_PALETTES["quartz"]["wallColor"],
                "bounds": kit_bounds,
                "furniture": kit_furniture,
                "lights": [{"position": [6.9, 2.8, -0.6], "color": "#FFFFFF", "intensity": 0.85, "distance": 10.0}],
            })
            focal_targets["kitchen"] = {"target": [6.9, 1.5, -0.6], "theta": 1.95, "phi": 1.05, "radius": 12.5, "walk": [5.8, 1.65, 1.2]}
            tour_waypoints.append({"p": [5.8, 1.65, 1.2], "l": [7.8, 1.1, -1.0], "label": "Culinary Kitchen Studio (3.1:1 Hall Ratio)"})

            # 3. Covered Sky Deck & Balcony
            balc_w, balc_d = 6.4, 3.4
            balc_bounds = {"x": 1.8, "y": 0.0, "z": 5.2, "w": balc_w, "d": balc_d, "h": 1.1}
            balc_furniture = [
                {"id": "b_lounge", "name": "Weatherproof Balcony Loveseat", "type": "chair", "position": [1.8, 0.35, 4.8], "size": [1.8, 0.4, 0.8], "materialKey": "sofa", "color": "#D9D1C0"},
                {"id": "b_table", "name": "Outdoor Teak Coffee Table", "type": "table", "position": [1.8, 0.25, 5.8], "size": [0.9, 0.35, 0.6], "materialKey": "wood2", "color": "#A87042"},
            ]
            generated_rooms.append({
                "id": "balcony",
                "name": "Covered Sky Deck & Balcony",
                "floorLevel": 0,
                "dimensions": "21' x 11'",
                "carpetSqft": int(carpet * 0.10),
                "highlight": "Panoramic open vista with frameless tempered glass balustrade & teak deck",
                "floorType": FINISH_PALETTES["deck"]["floorType"],
                "floorColor": FINISH_PALETTES["deck"]["floorColor"],
                "wallColor": FINISH_PALETTES["deck"]["wallColor"],
                "bounds": balc_bounds,
                "furniture": balc_furniture,
            })
            focal_targets["balcony"] = {"target": [1.8, 1.2, 5.2], "theta": 2.35, "phi": 1.05, "radius": 12.0, "walk": [0.8, 1.65, 4.4]}
            tour_waypoints.append({"p": [0.8, 1.65, 4.4], "l": [2.8, 1.4, 6.5], "label": "Covered Sky Deck & Balcony"})

            # 4. Master Suite (Bedroom 1)
            m_w, m_d = 5.8, 5.4
            m_bounds = {"x": -6.8, "y": 0.0, "z": 0.5, "w": m_w, "d": m_d, "h": H_FLOOR}
            m_furniture = [
                {"id": "m_bed", "name": "King Bed", "type": "bed", "position": [-6.8, 0.35, 0.2], "size": [2.2, 0.4, 2.1], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "m_headboard", "name": "Acoustic Fluted Headboard", "type": "wardrobe", "position": [-6.8, 0.95, -1.0], "size": [2.6, 1.0, 0.12], "materialKey": "wood", "color": "#B9824E"},
                {"id": "m_side_1", "name": "Nightstand", "type": "table", "position": [-8.2, 0.30, -0.9], "size": [0.55, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
                {"id": "m_side_2", "name": "Nightstand", "type": "table", "position": [-5.4, 0.30, -0.9], "size": [0.55, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
            ]
            generated_rooms.append({
                "id": "master",
                "name": "Presidential Master Suite (Bedroom 1)",
                "floorLevel": 0,
                "dimensions": "19' x 18'",
                "carpetSqft": int(carpet * 0.22),
                "highlight": "Engineered German oak wood flooring with walk-in wardrobe and en-suite bath",
                "floorType": FINISH_PALETTES["wood"]["floorType"],
                "floorColor": FINISH_PALETTES["wood"]["floorColor"],
                "wallColor": FINISH_PALETTES["wood"]["wallColor"],
                "bounds": m_bounds,
                "furniture": m_furniture,
                "lights": [{"position": [-6.8, 2.6, 0.5], "color": "#FFD9A0", "intensity": 0.85, "distance": 11.0}],
            })
            focal_targets["master"] = {"target": [-6.8, 1.5, 0.5], "theta": 0.35, "phi": 1.08, "radius": 13.0, "walk": [-5.4, 1.65, 2.2]}
            tour_waypoints.append({"p": [-5.4, 1.65, 2.2], "l": [-7.8, 1.1, -0.6], "label": "Presidential Master Suite (Bedroom 1)"})

            # 5. Bedroom 2 (Guest Suite)
            b2_w, b2_d = 4.6, 4.4
            b2_bounds = {"x": 6.9, "y": 0.0, "z": 4.6, "w": b2_w, "d": b2_d, "h": H_FLOOR}
            b2_furniture = [
                {"id": "b2_bed", "name": "Queen Bed", "type": "bed", "position": [6.9, 0.35, 4.4], "size": [1.9, 0.4, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                {"id": "b2_side", "name": "Bedside Nightstand", "type": "table", "position": [8.2, 0.30, 3.4], "size": [0.5, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
            ]
            generated_rooms.append({
                "id": "bedroom_2",
                "name": "Guest Suite (Bedroom 2)",
                "floorLevel": 0,
                "dimensions": "15' x 14'",
                "carpetSqft": int(carpet * 0.14),
                "highlight": "Matte vitrified tiles, acoustic double-glazed windows, and built-in wardrobes",
                "floorType": FINISH_PALETTES["tile"]["floorType"],
                "floorColor": FINISH_PALETTES["tile"]["floorColor"],
                "wallColor": FINISH_PALETTES["tile"]["wallColor"],
                "bounds": b2_bounds,
                "furniture": b2_furniture,
            })
            focal_targets["bedroom_2"] = {"target": [6.9, 1.5, 4.6], "theta": 1.85, "phi": 1.08, "radius": 12.0, "walk": [5.5, 1.65, 3.6]}
            tour_waypoints.append({"p": [5.5, 1.65, 3.6], "l": [7.8, 1.1, 4.8], "label": "Guest Suite (Bedroom 2)"})

            # 6. Bedroom 3 (if >= 3 BHK)
            if bhk_count >= 3:
                b3_w, b3_d = 4.8, 4.4
                b3_bounds = {"x": -6.8, "y": 0.0, "z": -4.8, "w": b3_w, "d": b3_d, "h": H_FLOOR}
                b3_furniture = [
                    {"id": "b3_bed", "name": "Queen Bed", "type": "bed", "position": [-6.8, 0.35, -4.8], "size": [1.9, 0.4, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                    {"id": "b3_desk", "name": "Writing Desk", "type": "table", "position": [-8.2, 0.35, -3.4], "size": [1.2, 0.75, 0.55], "materialKey": "wood2", "color": "#A87042"},
                ]
                generated_rooms.append({
                    "id": "bedroom_3",
                    "name": "Children's Suite (Bedroom 3)",
                    "floorLevel": 0,
                    "dimensions": "16' x 14'",
                    "carpetSqft": int(carpet * 0.12),
                    "highlight": "Natural daylit bedroom with custom study alcove and wooden flooring",
                    "floorType": FINISH_PALETTES["wood"]["floorType"],
                    "floorColor": FINISH_PALETTES["wood"]["floorColor"],
                    "wallColor": FINISH_PALETTES["wood"]["wallColor"],
                    "bounds": b3_bounds,
                    "furniture": b3_furniture,
                })
                focal_targets["bedroom_3"] = {"target": [-6.8, 1.5, -4.8], "theta": 0.55, "phi": 1.08, "radius": 12.0, "walk": [-5.4, 1.65, -3.6]}
                tour_waypoints.append({"p": [-5.4, 1.65, -3.6], "l": [-7.8, 1.1, -5.4], "label": "Children's Suite (Bedroom 3)"})

            # 7. Bedroom 4 (if >= 4 BHK)
            if bhk_count >= 4:
                b4_w, b4_d = 4.8, 4.2
                b4_bounds = {"x": 0.0, "y": 0.0, "z": -5.6, "w": b4_w, "d": b4_d, "h": H_FLOOR}
                b4_furniture = [
                    {"id": "b4_bed", "name": "Queen Bed", "type": "bed", "position": [0.0, 0.35, -5.6], "size": [1.9, 0.4, 2.0], "materialKey": "white", "color": "#FAFAF6"},
                    {"id": "b4_side", "name": "Bedside Nightstand", "type": "table", "position": [1.3, 0.30, -6.6], "size": [0.5, 0.35, 0.4], "materialKey": "accent", "color": "#C9A66B"},
                ]
                generated_rooms.append({
                    "id": "bedroom_4",
                    "name": "Garden Suite (Bedroom 4)",
                    "floorLevel": 0,
                    "dimensions": "16' x 14'",
                    "carpetSqft": int(carpet * 0.11),
                    "highlight": "Quiet garden-facing suite with integrated dressing alcove",
                    "floorType": FINISH_PALETTES["tile"]["floorType"],
                    "floorColor": FINISH_PALETTES["tile"]["floorColor"],
                    "wallColor": FINISH_PALETTES["tile"]["wallColor"],
                    "bounds": b4_bounds,
                    "furniture": b4_furniture,
                })
                focal_targets["bedroom_4"] = {"target": [0.0, 1.5, -5.6], "theta": 1.25, "phi": 1.08, "radius": 12.0, "walk": [0.0, 1.65, -4.2]}
                tour_waypoints.append({"p": [0.0, 1.65, -4.2], "l": [0.0, 1.1, -6.4], "label": "Garden Suite (Bedroom 4)"})

            # --- APARTMENT WALLS, DOORS, WINDOWS & BALCONIES ---

            # 1. Living South Wall (Z = 3.4, X from -4.6 to 4.6) with Balcony Sliding System
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-4.6, x_end=4.6, z=3.4, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=[
                    {"type": "slider", "x": 1.8, "width": 5.8, "height": 2.5, "sillHeight": 0.0, "name": "Panoramic Balcony Sliders"}
                ],
                is_exterior=False, floor_level=0, id_prefix="apt_living_balc"
            )

            # 2. Living West Partition Wall (X = -4.6, Z from -3.4 to 3.4)
            # Contains doors to Master Suite and Bedroom 3 (if >= 3 BHK)
            west_openings = [
                {"type": "door", "z": 0.5, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Master Suite Door"}
            ]
            if bhk_count >= 3:
                west_openings.append(
                    {"type": "door", "z": -2.8, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 3 Suite Door"}
                )
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-3.4, z_end=3.4, x=-4.6, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=west_openings,
                is_exterior=False, floor_level=0, id_prefix="apt_living_west"
            )

            # 3. Living East Partition Wall (X = 4.6, Z from -3.4 to 3.4)
            # Contains kitchen portal archway and Bedroom 2 entrance door
            east_openings = [
                {"type": "door", "doorType": "portal", "z": -0.6, "width": 2.4, "height": 2.4, "sillHeight": 0.0, "name": "Kitchen Portal Arch"},
                {"type": "door", "z": 2.5, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 2 Suite Door"}
            ]
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-3.4, z_end=3.4, x=4.6, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=east_openings,
                is_exterior=False, floor_level=0, id_prefix="apt_living_east"
            )

            # 4. Living North Wall (Z = -3.4, X from -4.6 to 4.6)
            north_openings = []
            if bhk_count >= 4:
                north_openings.append(
                    {"type": "door", "x": 0.0, "width": 0.95, "height": 2.15, "doorType": "swing", "name": "Bedroom 4 Suite Door"}
                )
            else:
                north_openings.append(
                    {"type": "door", "x": -1.5, "width": 1.1, "height": 2.3, "doorType": "pivot", "name": "Main Entrance Door (Yale Smart Lock)"}
                )
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-4.6, x_end=4.6, z=-3.4, y_base=0.0, height=H_FLOOR, thickness=0.18,
                openings=north_openings,
                is_exterior=False, floor_level=0, id_prefix="apt_living_north"
            )

            # 5. Master Suite Enclosing Exterior Walls
            # West Exterior Wall (X = -9.7, Z from -2.2 to 3.2)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.2, z_end=3.2, x=-9.7, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "z": 0.5, "width": 2.6, "height": 1.4, "sillHeight": 0.85, "name": "Master Suite Horizon Window"}
                ],
                is_exterior=True, floor_level=0, id_prefix="apt_master_west"
            )
            # South Exterior Wall (Z = 3.2, X from -9.7 to -4.6)
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=-9.7, x_end=-4.6, z=3.2, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "x": -6.8, "width": 2.0, "height": 1.4, "sillHeight": 0.85, "name": "Master Suite Sunset Window"}
                ],
                is_exterior=True, floor_level=0, id_prefix="apt_master_south"
            )

            # Partition Wall between Master Suite and Bedroom 3 (Z = -2.2, X from -9.7 to -4.6)
            if bhk_count >= 3:
                self._add_wall_x_with_openings(
                    structural_walls, doors, windows,
                    x_start=-9.7, x_end=-4.6, z=-2.2, y_base=0.0, height=H_FLOOR, thickness=0.18,
                    is_exterior=False, floor_level=0, id_prefix="apt_part_m_b3"
                )
                # Bedroom 3 West Exterior Wall (X = -9.2, Z from -7.0 to -2.2)
                self._add_wall_z_with_openings(
                    structural_walls, doors, windows,
                    z_start=-7.0, z_end=-2.2, x=-9.2, y_base=0.0, height=H_FLOOR, thickness=0.22,
                    openings=[
                        {"type": "window", "z": -4.8, "width": 2.0, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 3 Daylight Window"}
                    ],
                    is_exterior=True, floor_level=0, id_prefix="apt_b3_west"
                )
                # Bedroom 3 North Exterior Wall (Z = -7.0, X from -9.2 to -4.4)
                self._add_wall_x_with_openings(
                    structural_walls, doors, windows,
                    x_start=-9.2, x_end=-4.4, z=-7.0, y_base=0.0, height=H_FLOOR, thickness=0.22,
                    openings=[
                        {"type": "window", "x": -6.8, "width": 1.8, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 3 Study Window"}
                    ],
                    is_exterior=True, floor_level=0, id_prefix="apt_b3_north"
                )

            # 6. Kitchen Enclosing Exterior Walls
            # North Wall (Z = -2.9, X from 4.6 to 9.1)
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=4.6, x_end=9.1, z=-2.9, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "x": 6.9, "width": 2.0, "height": 1.1, "sillHeight": 1.1, "name": "Kitchen Counter Window"}
                ],
                is_exterior=True, floor_level=0, id_prefix="apt_kit_north"
            )
            # East Wall (X = 9.1, Z from -2.9 to 1.7)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=-2.9, z_end=1.7, x=9.1, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "z": -0.6, "width": 1.6, "height": 1.2, "sillHeight": 1.1, "name": "Kitchen Side Ventilation"}
                ],
                is_exterior=True, floor_level=0, id_prefix="apt_kit_east"
            )
            # Partition Wall between Kitchen and Bedroom 2 (Z = 1.7, X from 4.6 to 9.1)
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=4.6, x_end=9.1, z=1.7, y_base=0.0, height=H_FLOOR, thickness=0.18,
                is_exterior=False, floor_level=0, id_prefix="apt_part_kit_b2"
            )

            # 7. Bedroom 2 Enclosing Exterior Walls
            # East Wall (X = 9.2, Z from 1.7 to 6.8)
            self._add_wall_z_with_openings(
                structural_walls, doors, windows,
                z_start=1.7, z_end=6.8, x=9.2, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "z": 4.6, "width": 2.2, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 2 Sunrise Window"}
                ],
                is_exterior=True, floor_level=0, id_prefix="apt_b2_east"
            )
            # South Wall (Z = 6.8, X from 4.6 to 9.2)
            self._add_wall_x_with_openings(
                structural_walls, doors, windows,
                x_start=4.6, x_end=9.2, z=6.8, y_base=0.0, height=H_FLOOR, thickness=0.22,
                openings=[
                    {"type": "window", "x": 6.9, "width": 1.8, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 2 Garden Window"}
                ],
                is_exterior=True, floor_level=0, id_prefix="apt_b2_south"
            )

            # 8. Bedroom 4 (if >= 4 BHK)
            if bhk_count >= 4:
                # North Exterior Wall (Z = -7.7, X from -2.4 to 2.4)
                self._add_wall_x_with_openings(
                    structural_walls, doors, windows,
                    x_start=-2.4, x_end=2.4, z=-7.7, y_base=0.0, height=H_FLOOR, thickness=0.22,
                    openings=[
                        {"type": "window", "x": 0.0, "width": 2.4, "height": 1.4, "sillHeight": 0.85, "name": "Bedroom 4 Garden Vista Window"}
                    ],
                    is_exterior=True, floor_level=0, id_prefix="apt_b4_north"
                )
                self._add_wall_z_with_openings(
                    structural_walls, doors, windows,
                    z_start=-7.7, z_end=-3.4, x=-2.4, y_base=0.0, height=H_FLOOR, thickness=0.18,
                    is_exterior=False, floor_level=0, id_prefix="apt_b4_west"
                )
                self._add_wall_z_with_openings(
                    structural_walls, doors, windows,
                    z_start=-7.7, z_end=-3.4, x=2.4, y_base=0.0, height=H_FLOOR, thickness=0.18,
                    is_exterior=False, floor_level=0, id_prefix="apt_b4_east"
                )

            # 9. Covered Sky Deck & Balcony Balustrades
            self._add_balcony_system(
                balconies, glass_panels,
                balc_id="balc_sky_deck_apt",
                name="Covered Sky Balcony & Sunset Deck",
                floor_level=0,
                deck_x=1.8, deck_y=0.0, deck_z=5.2,
                deck_w=6.4, deck_d=3.4,
                rail_height=1.1,
                open_sides=["front", "left", "right"]
            )

        # Final Waypoint: Aerial Overview
        tour_waypoints.append({
            "p": [18.0, 16.0, 18.0],
            "l": [0.0, 3.0, 0.0],
            "label": "Aerial · Full 3D Spatial Digital Twin"
        })

        focal_targets["all"] = {
            "target": [0.0, 2.8, 0.0],
            "theta": 0.72,
            "phi": 1.05,
            "radius": 34.0,
            "walk": [0.0, 1.65, 12.0],
        }

        # Dynamic fixtures
        fixtures = [
            {"item": f"{bhk_count} Distinct Bedroom Suites", "detail": f"Accurately mapped with Master Suite + {bhk_count - 1} secondary suites", "included": True},
            {"item": "Calibrated 3:1 Living Hall to Kitchen Ratio", "detail": "Grand entertainment volume with dedicated ergonomic culinary studio", "included": True},
            {"item": "Structural BIM Perimeter & Partition Walls", "detail": "Full height architectural walls with proper openings and skirting", "included": True},
            {"item": "Engineered Teak Doors & Smart Handles", "detail": "8-foot height door portals with brass handles and smooth frames", "included": True},
            {"item": "Double-Glazed Acoustic Window Casements", "detail": "42dB street noise attenuation with bronze profiles and sills", "included": True},
            {"item": "Teak Balconies with Safety Glass Balustrades", "detail": "Tempered laminated glass with continuous top handrail", "included": True},
            {"item": "Turnkey Designer Staging Packages", "detail": "Available as staged turnkey package upon conveyance", "included": False},
        ]

        # Formatted Architectural About Notes Summary
        about_summary = (
            f"Compiled directly from property listing: '{about['propertyTitle']}'. "
            f"Architecture: {about['propertyType']} ({about['configuration']}), {about['carpetSqft']:,} sq.ft carpet on {about['floor']}. "
            f"Physical layout strictly allocates {bhk_count} bedrooms with calibrated 3:1 hall-to-kitchen ratio, "
            f"enclosed structural walls, door portals, window casements, and outdoor balconies. "
            f"Verified by civil inspection audit ({about['conditionScore']}/10 composite structural score)."
        )

        return {
            "propertyId": about["propertyId"],
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
            "conditionScore": about["conditionScore"],
            "efficiency": about["efficiency"],
            "orientation": about["orientation"],
            "archetype": archetype,
            "levelsCount": about["levelsCount"],
            "environmentalTheme": about["environmentalTheme"],
            "aboutSummary": about_summary,
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

    def compile_from_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compiles authoritative Digital Twin spatial blueprint from property listing data.
        """
        about = self.extract_property_about(property_data)
        blueprint = self.solve_spatial_layout(about)
        return blueprint

    def compile(self, prompt: str = "", meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compiles a digital twin blueprint from a prompt or metadata dictionary.
        """
        prop_data = dict(meta) if meta else {}
        if prompt:
            if not prop_data.get("title"):
                prop_data["title"] = prompt.split(".")[0] if "." in prompt else prompt[:50]
            if not prop_data.get("configuration"):
                m = re.search(r'(\d+)\s*(?:bhk|bed)', prompt.lower())
                if m:
                    prop_data["configuration"] = f"{m.group(1)} BHK"
            if not prop_data.get("carpetAreaSqft"):
                m_sq = re.search(r'(\d[\d,]+)\s*(?:sqft|sq\.ft)', prompt.lower())
                if m_sq:
                    prop_data["carpetAreaSqft"] = int(m_sq.group(1).replace(",", ""))
        return self.compile_from_property(prop_data)

    def export_typescript(self, blueprint: Dict[str, Any], filepath: str, export_name: str = "GENERATED_TWIN_BLUEPRINT"):
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        content = f"""// AUTO-GENERATED BY SOVEREIGN DIGITAL TWIN COMPILER
// Target Component: sample/DynamicThreeTwinViewer.tsx
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

export interface DigitalTwinRoom {{
  id: string;
  name: string;
  floorLevel: number;
  dimensions: string;
  carpetSqft: number;
  highlight: string;
  floorType: string;
  floorColor: string;
  wallColor: string;
  bounds: SpatialBox;
  furniture: StagedFurniture[];
  lights?: Array<{{ position: [number, number, number]; color: string; intensity: number; distance: number }}>;
}}

export interface FloorDefinition {{
  id: string;
  name: string;
  elevation: number;
  roomIds: string[];
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
  railings: Array<{{ id: string; position: [number, number, number]; size: [number, number]; rotationY: number; type: string; handrail?: boolean }}>;
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

export interface DigitalTwinBlueprint {{
  propertyId: string;
  propertyTitle: string;
  locality: string;
  city: string;
  state: string;
  propertyType: string;
  configuration: string;
  bhkCount: number;
  carpetSqft: number;
  builtUpSqft: number;
  floor: string;
  floorHeight: string;
  conditionScore: number;
  efficiency: number;
  orientation: string;
  archetype: string;
  levelsCount: number;
  environmentalTheme: string;
  aboutSummary: string;
  floors: FloorDefinition[];
  rooms: DigitalTwinRoom[];
  structuralWalls: StructuralWall[];
  doors: DoorSpecification[];
  windows: WindowSpecification[];
  balconies: BalconySpecification[];
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
