"""
MCP Server for Orbital Mechanics Tools
Provides satellite propagation and collision analysis capabilities
"""
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from cachetools import TTLCache
from fastmcp import FastMCP
from sgp4.api import Satrec, jday

sys.path.append(str(Path(__file__).parent.parent))

from config import settings
from utils.data_loader import CelesTrakClient
from utils.logging_config import get_logger

logger = get_logger("orbital_mcp_server")

# Initialize FastMCP server
logger.info("Initializing FastMCP server 'orbital_mechanics_server'...")
mcp = FastMCP("orbital_mechanics_server")

# ── TLE cache (thread-safe, TTL-backed) ──────────────────────────────────────
_tle_cache: TTLCache = TTLCache(maxsize=512, ttl=settings.CELESTRAK_CACHE_TTL_S)
_tle_cache_lock = threading.Lock()


def parse_tle(line1: str, line2: str) -> Satrec:
    """Parse TLE and return satellite object"""
    return Satrec.twoline2rv(line1, line2)


def datetime_to_jd(dt: datetime) -> Tuple[float, float]:
    """Convert datetime to Julian date"""
    return jday(
        dt.year, dt.month, dt.day,
        dt.hour, dt.minute,
        dt.second + dt.microsecond / 1e6,
    )


# ── Internal TLE fetch — delegates to shared CelesTrakClient ─────────────────

def _get_tle_data_internal(norad_id: int) -> Dict:
    """
    Delegates to CelesTrakClient which owns the TTL cache, retry, and
    circuit-breaker logic. Wraps result in the legacy dict shape so all
    callers remain unchanged.
    """
    tle = CelesTrakClient.fetch_tle(norad_id)
    if tle is None:
        return {
            "success":  False,
            "error":    f"Could not fetch TLE for NORAD ID {norad_id}",
            "norad_id": norad_id,
        }
    
    # FIX: Ensure both 'name' and 'sat_name' exist in the returned dictionary
    # to prevent KeyErrors across all tools regardless of what the client returns.
    raw_name = tle.get("sat_name") or tle.get("name") or f"NORAD {norad_id}"
    tle["name"] = raw_name
    tle["sat_name"] = raw_name

    return {"success": True, **tle}


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_tle_data(norad_id: int) -> Dict:
    """
    Fetch TLE data for a satellite from CelesTrak

    Args:
        norad_id: NORAD catalog number

    Returns:
        Dictionary containing TLE data and metadata
    """
    logger.info("Tool 'get_tle_data' invoked", extra={"norad_id": norad_id})
    result = _get_tle_data_internal(norad_id)
    logger.info("Tool 'get_tle_data' completed",
                extra={"norad_id": norad_id, "success": result.get("success")})
    return result


@mcp.tool()
def propagate_orbit(norad_id: int, target_time: str) -> Dict:
    """
    Propagate satellite orbit to a specific time

    Args:
        norad_id: NORAD catalog number
        target_time: ISO format datetime string (e.g., '2024-01-15T12:00:00Z')

    Returns:
        Dictionary with position (km) and velocity (km/s) vectors in TEME frame
    """
    logger.info("Tool 'propagate_orbit' invoked",
                extra={"norad_id": norad_id, "target_time": target_time})

    tle_data = _get_tle_data_internal(norad_id)
    if not tle_data.get("success"):
        logger.error("Propagation aborted: TLE fetch failed",
                     extra={"norad_id": norad_id})
        return tle_data

    # Parse TLE
    try:
        sat = parse_tle(tle_data["line1"], tle_data["line2"])
    except Exception as e:
        logger.error("Failed to parse TLE",
                     extra={"norad_id": norad_id, "error": str(e)})
        return {
            "success":  False,
            "error":    f"Failed to parse TLE: {str(e)}",
            "norad_id": norad_id,
        }

    # Parse target time
    try:
        dt = datetime.fromisoformat(target_time.replace("Z", "+00:00"))
        jd, fr = datetime_to_jd(dt)
    except Exception as e:
        logger.error("Invalid datetime format",
                     extra={"target_time": target_time, "error": str(e)})
        return {
            "success":  False,
            "error":    f"Invalid datetime format: {str(e)}",
            "norad_id": norad_id,
        }

    # Propagate
    try:
        error_code, position, velocity = sat.sgp4(jd, fr)

        if error_code != 0:
            logger.warning("SGP4 propagation error",
                           extra={"norad_id": norad_id, "error_code": error_code})
            return {
                "success":  False,
                "error":    f"SGP4 error code: {error_code}",
                "norad_id": norad_id,
            }

        speed = float(np.linalg.norm(velocity))
        logger.info("Propagation successful",
                    extra={"norad_id": norad_id, "speed_km_s": round(speed, 3)})

        # FIX: Safe naming
        return {
            "success":      True,
            "norad_id":     norad_id,
            "name":         tle_data.get("name", f"NORAD {norad_id}"),
            "epoch":        target_time,
            "position_km":  list(position),
            "velocity_km_s": list(velocity),
            "magnitude_km": float(np.linalg.norm(position)),
            "speed_km_s":   speed,
        }

    except Exception as e:
        logger.error("Propagation algorithm failed",
                     extra={"norad_id": norad_id, "error": str(e)})
        return {
            "success":  False,
            "error":    f"Propagation failed: {str(e)}",
            "norad_id": norad_id,
        }


@mcp.tool()
def calculate_miss_distance(
    id_1: int,
    id_2: int,
    start_time: str,
    end_time: str,
    time_step_seconds: int = 60,
) -> Dict:
    """
    Calculate minimum miss distance between two objects over a time window
    """
    logger.info(
        "Tool 'calculate_miss_distance' invoked",
        extra={"id1": id_1, "id2": id_2, "step_s": time_step_seconds},
    )

    tle1 = _get_tle_data_internal(id_1)
    tle2 = _get_tle_data_internal(id_2)

    if not tle1.get("success") or not tle2.get("success"):
        logger.error("Aborting miss distance calc: TLE fetch failed")
        return {
            "success": False,
            "error":   "Failed to fetch TLE data for one or both objects",
        }

    # Parse TLEs
    try:
        sat1 = parse_tle(tle1["line1"], tle1["line2"])
        sat2 = parse_tle(tle2["line1"], tle2["line2"])
    except Exception as e:
        logger.error("TLE parsing error", extra={"error": str(e)})
        return {"success": False, "error": f"Failed to parse TLEs: {str(e)}"}

    # Parse times
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt   = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except Exception as e:
        logger.error("Date parsing error", extra={"error": str(e)})
        return {"success": False, "error": f"Invalid datetime format: {str(e)}"}

    logger.info("Starting propagation loop for close approach analysis...")

    min_distance = float("inf")
    tca_time = tca_pos1 = tca_pos2 = tca_vel1 = tca_vel2 = None
    steps_calculated = 0
    current_dt = start_dt

    while current_dt <= end_dt:
        jd, fr = datetime_to_jd(current_dt)

        error1, pos1, vel1 = sat1.sgp4(jd, fr)
        error2, pos2, vel2 = sat2.sgp4(jd, fr)

        if error1 == 0 and error2 == 0:
            distance = float(np.linalg.norm(np.array(pos1) - np.array(pos2)))
            if distance < min_distance:
                min_distance = distance
                tca_time     = current_dt
                tca_pos1     = pos1
                tca_pos2     = pos2
                tca_vel1     = vel1
                tca_vel2     = vel2

        current_dt += timedelta(seconds=time_step_seconds)
        steps_calculated += 1

    logger.info("Propagation loop completed",
                extra={"steps": steps_calculated})

    if tca_time is None:
        logger.warning("No valid propagation data found in time window")
        return {
            "success": False,
            "error":   "No valid propagation data found in time window",
        }

    # Calculate relative velocity
    rel_velocity     = np.array(tca_vel1) - np.array(tca_vel2)
    rel_speed_km_s   = float(np.linalg.norm(rel_velocity))

    # Determine collision geometry
    pos_diff      = np.array(tca_pos1) - np.array(tca_pos2)
    pos_diff_unit = pos_diff / np.linalg.norm(pos_diff)
    rel_vel_unit  = rel_velocity / (np.linalg.norm(rel_velocity) + 1e-10)

    collision_angle_cos = float(np.dot(pos_diff_unit, rel_vel_unit))
    if collision_angle_cos < -0.5:
        collision_type = "head-on"
    elif collision_angle_cos > 0.5:
        collision_type = "chasing"
    else:
        collision_type = "crossing"

    logger.info(
        "TCA found",
        extra={
            "tca":        tca_time.isoformat(),
            "min_dist_km": round(min_distance, 2),
            "type":        collision_type,
        },
    )

    # FIX: Safe naming
    return {
        "success":                True,
        "object_1":               {"norad_id": id_1, "name": tle1.get("name", f"NORAD {id_1}")},
        "object_2":               {"norad_id": id_2, "name": tle2.get("name", f"NORAD {id_2}")},
        "minimum_distance_km":    float(min_distance),
        "time_of_closest_approach": tca_time.isoformat(),
        "relative_speed_km_s":    rel_speed_km_s,
        "relative_speed_m_s":     rel_speed_km_s * 1000,
        "collision_angle_cosine": collision_angle_cos,
        "collision_type":         collision_type,
        "object_1_position_km":   list(tca_pos1),
        "object_2_position_km":   list(tca_pos2),
        "object_1_velocity_km_s": list(tca_vel1),
        "object_2_velocity_km_s": list(tca_vel2),
    }


@mcp.tool()
def detect_maneuver(
    norad_id: int,
    reference_time: str,
    lookback_hours: int = 48,
) -> Dict:
    """
    Classify satellite operational status.
    """
    logger.info("Tool 'detect_maneuver' invoked",
                extra={"norad_id": norad_id, "lookback_h": lookback_hours})

    tle_data = _get_tle_data_internal(norad_id)
    if not tle_data.get("success"):
        logger.error("Maneuver detection aborted: TLE fetch failed",
                     extra={"norad_id": norad_id})
        return tle_data

    line1 = tle_data["line1"]
    line2 = tle_data["line2"]
    
    # FIX: Safe extraction of the name
    raw_name = tle_data.get("sat_name") or tle_data.get("name") or f"NORAD {norad_id}"
    name  = raw_name.upper()

    # ── Epoch staleness ───────────────────────────────────────────────────
    try:
        sat         = Satrec.twoline2rv(line1, line2)
        epoch_jd    = sat.jdsatepoch + sat.jdsatepochF
        now_dt      = datetime.now(timezone.utc)
        now_jd      = 2440587.5 + now_dt.timestamp() / 86400.0
        epoch_age_d = now_jd - epoch_jd
        bstar       = sat.bstar
    except Exception as exc:
        logger.warning("SGP4 epoch parse error",
                       extra={"norad_id": norad_id, "error": str(exc)})
        epoch_age_d = 0.0
        bstar       = 0.0

    # ── Classification rules (ordered by confidence) ──────────────────────
    DEBRIS_TOKENS = {"DEB", "R/B", "ROCKET", "STAGE", "FRAG", "ARIANE", "CZ-"}
    is_debris_name = any(tok in name for tok in DEBRIS_TOKENS)
    is_stale       = epoch_age_d > 30
    is_high_drag   = abs(bstar) > 0.01

    if is_debris_name or is_high_drag:
        status            = "DRIFTING"
        maneuver_detected = False
        confidence        = "HIGH" if is_debris_name else "MEDIUM"
    elif is_stale:
        status            = "UNCERTAIN"
        maneuver_detected = False
        confidence        = "LOW"
    else:
        status            = "ACTIVE"
        maneuver_detected = True
        confidence        = "MEDIUM"

    logger.info(
        "Maneuver classification complete",
        extra={
            "norad_id":        norad_id,
            "status":          status,
            "confidence":      confidence,
            "epoch_age_days":  round(epoch_age_d, 1),
            "bstar":           bstar,
        },
    )

    # FIX: Ensure sat_name is always passed safely
    return {
        "success":                   True,
        "norad_id":                  norad_id,
        "sat_name":                  raw_name,
        "maneuver_detected":         maneuver_detected,
        "status":                    status,
        "classification_confidence": confidence,
        "epoch_age_days":            round(epoch_age_d, 1),
        "bstar":                     bstar,
        "method":                    "name_heuristic+epoch_age+bstar",
        "limitation": (
            "Single-TLE velocity comparison is not a valid maneuver detector. "
            "Status inferred from object name, epoch age, and BSTAR coefficient."
        ),
        "lookback_hours": lookback_hours,
    }


if __name__ == "__main__":
    logger.info("Starting Orbital Mechanics MCP Server loop...")
    try:
        mcp.run()
    except Exception as e:
        logger.critical("MCP Server crashed", extra={"error": str(e)})