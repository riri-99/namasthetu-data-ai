"""
PAM (Photo Analysis Module) — EXIF & Anti-Spoofing Geotag Verification Substrate.

Implements:
- EXIF extraction from image files/bytes (GPS coordinates, capture timestamps)
- Decimal degree conversion from EXIF rational tuples (Degrees/Minutes/Seconds)
- Great-circle Haversine distance computation
- 25-meter Cadastral boundary anti-spoofing gate (HYC-SCO-2026-3841 Doc 05 §8)
"""

from __future__ import annotations

import io
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union
from PIL import Image, ExifTags
from pydantic import BaseModel, Field


class ExifMetadata(BaseModel):
    """Extracted and validated EXIF telemetry."""
    latitude: float = Field(..., description="Decimal latitude")
    longitude: float = Field(..., description="Decimal longitude")
    timestamp: datetime = Field(..., description="Capture timestamp (UTC)")
    is_geotag_valid: bool = Field(default=False, description="Valid within 25m boundary gate")
    distance_meters: Optional[float] = Field(default=None, description="Distance from property anchor")
    camera_make: Optional[str] = Field(default=None)
    camera_model: Optional[str] = Field(default=None)


def _convert_to_degrees(value: Any) -> Optional[float]:
    """Convert EXIF GPS coordinate (deg, min, sec) into decimal degrees."""
    if not value:
        return None
    try:
        # Handles tuples/lists of IFDRational or float/int
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, IndexError, ZeroDivisionError, ValueError):
        return None


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in meters between two points
    on the Earth using the Haversine formula.
    """
    r_earth_meters = 6371000.0  # Mean radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r_earth_meters * c, 2)


class ExifProcessor:
    """Extracts, parses, and validates EXIF GPS and timestamp metadata."""

    # Standard Cadastral anti-spoof threshold from Scope Doc 05
    GEOFENCE_RADIUS_METERS = 25.0

    @classmethod
    def parse_exif(
        cls,
        image_input: Union[str, bytes, Image.Image],
        target_coords: Optional[Tuple[float, float]] = None,
        fallback_coords: Optional[Tuple[float, float]] = None,
    ) -> ExifMetadata:
        """
        Extract EXIF telemetry and validate against target property coordinates.
        
        Args:
            image_input: Path to image, raw image bytes, or PIL Image object.
            target_coords: Optional (latitude, longitude) of property cadastral anchor.
            fallback_coords: Optional fallback (lat, lon) when EXIF is stripped by client.
        """
        img: Optional[Image.Image] = None
        should_close = False

        if isinstance(image_input, Image.Image):
            img = image_input
        elif isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input))
            should_close = True
        elif isinstance(image_input, str):
            img = Image.open(image_input)
            should_close = True
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        raw_exif: Dict[str, Any] = {}
        try:
            exif_data = img._getexif()
            if exif_data:
                for tag_id, val in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    raw_exif[tag_name] = val
        except Exception:
            raw_exif = {}
        finally:
            if should_close and img:
                img.close()

        # Parse GPS
        gps_info = raw_exif.get("GPSInfo", {})
        gps_dict: Dict[str, Any] = {}
        if isinstance(gps_info, dict):
            for k, v in gps_info.items():
                name = ExifTags.GPSTAGS.get(k, k)
                gps_dict[name] = v

        lat: Optional[float] = None
        lon: Optional[float] = None

        if "GPSLatitude" in gps_dict and "GPSLongitude" in gps_dict:
            raw_lat = _convert_to_degrees(gps_dict["GPSLatitude"])
            raw_lon = _convert_to_degrees(gps_dict["GPSLongitude"])

            if raw_lat is not None and raw_lon is not None:
                lat_ref = gps_dict.get("GPSLatitudeRef", "N")
                lon_ref = gps_dict.get("GPSLongitudeRef", "E")

                lat = -raw_lat if lat_ref in ("S", "s") else raw_lat
                lon = -raw_lon if lon_ref in ("W", "w") else raw_lon

        # Fallback to provided coords if EXIF lacks GPS
        if (lat is None or lon is None) and fallback_coords:
            lat, lon = fallback_coords
        
        # Default to 0.0, 0.0 if not resolvable
        lat = round(lat if lat is not None else 0.0, 6)
        lon = round(lon if lon is not None else 0.0, 6)

        # Parse Timestamp
        ts_str = (
            raw_exif.get("DateTimeOriginal")
            or raw_exif.get("DateTimeDigitized")
            or raw_exif.get("DateTime")
        )
        parsed_ts: datetime
        if ts_str:
            try:
                # Common EXIF date format: "YYYY:MM:DD HH:MM:SS"
                parsed_ts = datetime.strptime(str(ts_str).strip(), "%Y:%m:%d %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            except Exception:
                parsed_ts = datetime.now(timezone.utc)
        else:
            parsed_ts = datetime.now(timezone.utc)

        # Geotag Validation against 25m cadastral boundary
        is_valid = False
        distance: Optional[float] = None

        if target_coords and (lat != 0.0 or lon != 0.0):
            target_lat, target_lon = target_coords
            distance = haversine_distance_meters(lat, lon, target_lat, target_lon)
            is_valid = distance <= cls.GEOFENCE_RADIUS_METERS
        elif target_coords is None and (lat != 0.0 or lon != 0.0):
            # If no target coordinates specified to check against, valid if valid lat/lon present
            is_valid = (-90.0 <= lat <= 90.0) and (-180.0 <= lon <= 180.0)

        return ExifMetadata(
            latitude=lat,
            longitude=lon,
            timestamp=parsed_ts,
            is_geotag_valid=is_valid,
            distance_meters=distance,
            camera_make=str(raw_exif.get("Make")) if raw_exif.get("Make") else None,
            camera_model=str(raw_exif.get("Model")) if raw_exif.get("Model") else None,
        )
