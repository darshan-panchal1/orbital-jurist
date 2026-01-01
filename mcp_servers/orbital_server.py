"""
MCP Server for Orbital Mechanics Tools
Provides satellite propagation and collision analysis capabilities
"""
import sys
import logging
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import numpy as np
from sgp4.api import Satrec, jday
from sgp4 import exporter
from fastmcp import FastMCP
from utils.data_loader import CelesTrakClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("orbital_mcp_server")

# Initialize FastMCP server
logger.info("Initializing FastMCP server 'orbital_mechanics_server'...")
mcp = FastMCP("orbital_mechanics_server")

# Cache for TLE data
tle_cache = {}

def parse_tle(line1: str, line2: str) -> Satrec:
    """Parse TLE and return satellite object"""
    return Satrec.twoline2rv(line1, line2)

def datetime_to_jd(dt: datetime) -> Tuple[float, float]:
    """Convert datetime to Julian date"""
    return jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond/1e6)

# Define internal functions first (not decorated)
def _get_tle_data_internal(norad_id: int) -> Dict:
    """Internal function for fetching TLE data (not decorated)"""
    logger.debug(f"Internal TLE fetch requested for NORAD ID: {norad_id}")
    
    # Check cache first
    if norad_id in tle_cache:
        logger.debug(f"TLE cache hit for NORAD ID: {norad_id}")
        return tle_cache[norad_id]
    
    # Fetch from CelesTrak
    logger.info(f"Fetching TLE for NORAD ID {norad_id} from CelesTrak...")
    try:
        tle_data = CelesTrakClient.fetch_tle(norad_id)
    except Exception as e:
        logger.error(f"Error calling CelesTrakClient: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Exception during TLE fetch: {str(e)}",
            "norad_id": norad_id
        }
    
    if tle_data is None:
        logger.warning(f"Could not fetch TLE for NORAD ID {norad_id} (Data is None)")
        return {
            "success": False,
            "error": f"Could not fetch TLE for NORAD ID {norad_id}",
            "norad_id": norad_id
        }
    
    # Cache the result
    tle_cache[norad_id] = {
        "success": True,
        "norad_id": norad_id,
        "name": tle_data["name"],
        "line1": tle_data["line1"],
        "line2": tle_data["line2"],
        "epoch": tle_data["epoch"]
    }
    logger.info(f"TLE cached successfully for '{tle_data['name']}' (ID: {norad_id})")
    
    return tle_cache[norad_id]

# Now create the decorated version
@mcp.tool()
def get_tle_data(norad_id: int) -> Dict:
    """
    Fetch TLE data for a satellite from CelesTrak
    
    Args:
        norad_id: NORAD catalog number
    
    Returns:
        Dictionary containing TLE data and metadata
    """
    logger.info(f"Tool 'get_tle_data' invoked. NORAD ID: {norad_id}")
    result = _get_tle_data_internal(norad_id)
    logger.info(f"Tool 'get_tle_data' completed. Success: {result.get('success')}")
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
    logger.info(f"Tool 'propagate_orbit' invoked. ID: {norad_id}, Target Time: {target_time}")

    # Get TLE data using internal function
    tle_data = _get_tle_data_internal(norad_id)
    if not tle_data.get("success"):
        logger.error(f"Propagation aborted: TLE fetch failed for ID {norad_id}")
        return tle_data
    
    # Parse TLE
    try:
        sat = parse_tle(tle_data["line1"], tle_data["line2"])
    except Exception as e:
        logger.error(f"Failed to parse TLE for ID {norad_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to parse TLE: {str(e)}",
            "norad_id": norad_id
        }
    
    # Parse target time
    try:
        dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
        jd, fr = datetime_to_jd(dt)
    except Exception as e:
        logger.error(f"Invalid datetime format '{target_time}': {e}")
        return {
            "success": False,
            "error": f"Invalid datetime format: {str(e)}",
            "norad_id": norad_id
        }
    
    # Propagate
    try:
        error_code, position, velocity = sat.sgp4(jd, fr)
        
        if error_code != 0:
            logger.warning(f"SGP4 propagation error code {error_code} for ID {norad_id}")
            return {
                "success": False,
                "error": f"SGP4 error code: {error_code}",
                "norad_id": norad_id
            }
        
        speed = float(np.linalg.norm(velocity))
        logger.info(f"Propagation successful for ID {norad_id}. Speed: {speed:.3f} km/s")

        return {
            "success": True,
            "norad_id": norad_id,
            "name": tle_data["name"],
            "epoch": target_time,
            "position_km": list(position),
            "velocity_km_s": list(velocity),
            "magnitude_km": float(np.linalg.norm(position)),
            "speed_km_s": speed
        }
    
    except Exception as e:
        logger.error(f"Propagation algorithm failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Propagation failed: {str(e)}",
            "norad_id": norad_id
        }

@mcp.tool()
def calculate_miss_distance(
    id_1: int,
    id_2: int,
    start_time: str,
    end_time: str,
    time_step_seconds: int = 60
) -> Dict:
    """
    Calculate minimum miss distance between two objects over a time window
    
    Args:
        id_1: NORAD ID of first object
        id_2: NORAD ID of second object
        start_time: Start of analysis window (ISO format)
        end_time: End of analysis window (ISO format)
        time_step_seconds: Time step for propagation (default 60s)
    
    Returns:
        Dictionary with minimum distance, time of closest approach, and relative velocity
    """
    logger.info(f"Tool 'calculate_miss_distance' invoked. ID1: {id_1}, ID2: {id_2}, Window: {start_time} to {end_time}, Step: {time_step_seconds}s")
    
    # Get TLE data for both objects using internal function
    tle1 = _get_tle_data_internal(id_1)
    tle2 = _get_tle_data_internal(id_2)
    
    if not tle1.get("success") or not tle2.get("success"):
        logger.error("Aborting miss distance calc: TLE fetch failed.")
        return {
            "success": False,
            "error": "Failed to fetch TLE data for one or both objects"
        }
    
    # Parse TLEs
    try:
        sat1 = parse_tle(tle1["line1"], tle1["line2"])
        sat2 = parse_tle(tle2["line1"], tle2["line2"])
    except Exception as e:
        logger.error(f"TLE parsing error: {e}")
        return {
            "success": False,
            "error": f"Failed to parse TLEs: {str(e)}"
        }
    
    # Parse times
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Date parsing error: {e}")
        return {
            "success": False,
            "error": f"Invalid datetime format: {str(e)}"
        }
    
    logger.info("Starting propagation loop for close approach analysis...")
    
    # Propagate and find minimum distance
    min_distance = float('inf')
    tca_time = None
    tca_pos1 = None
    tca_pos2 = None
    tca_vel1 = None
    tca_vel2 = None
    
    current_dt = start_dt
    steps_calculated = 0
    
    while current_dt <= end_dt:
        jd, fr = datetime_to_jd(current_dt)
        
        error1, pos1, vel1 = sat1.sgp4(jd, fr)
        error2, pos2, vel2 = sat2.sgp4(jd, fr)
        
        if error1 == 0 and error2 == 0:
            distance = np.linalg.norm(np.array(pos1) - np.array(pos2))
            
            if distance < min_distance:
                min_distance = distance
                tca_time = current_dt
                tca_pos1 = pos1
                tca_pos2 = pos2
                tca_vel1 = vel1
                tca_vel2 = vel2
        
        current_dt += timedelta(seconds=time_step_seconds)
        steps_calculated += 1
    
    logger.info(f"Propagation loop completed. {steps_calculated} steps analyzed.")
    
    if tca_time is None:
        logger.warning("No valid propagation data found in time window.")
        return {
            "success": False,
            "error": "No valid propagation data found in time window"
        }
    
    # Calculate relative velocity
    rel_velocity = np.array(tca_vel1) - np.array(tca_vel2)
    rel_speed_km_s = float(np.linalg.norm(rel_velocity))
    
    # Determine collision geometry
    pos_diff = np.array(tca_pos1) - np.array(tca_pos2)
    pos_diff_unit = pos_diff / np.linalg.norm(pos_diff)
    rel_vel_unit = rel_velocity / (np.linalg.norm(rel_velocity) + 1e-10)
    
    # Dot product gives collision angle (-1 = head-on, +1 = chasing)
    collision_angle_cos = float(np.dot(pos_diff_unit, rel_vel_unit))
    collision_type = "head-on" if collision_angle_cos < -0.5 else "chasing" if collision_angle_cos > 0.5 else "crossing"
    
    logger.info(f"TCA Found: {tca_time.isoformat()} | Min Dist: {min_distance:.2f} km | Type: {collision_type}")
    
    return {
        "success": True,
        "object_1": {"norad_id": id_1, "name": tle1["name"]},
        "object_2": {"norad_id": id_2, "name": tle2["name"]},
        "minimum_distance_km": float(min_distance),
        "time_of_closest_approach": tca_time.isoformat(),
        "relative_speed_km_s": rel_speed_km_s,
        "relative_speed_m_s": rel_speed_km_s * 1000,
        "collision_angle_cosine": collision_angle_cos,
        "collision_type": collision_type,
        "object_1_position_km": list(tca_pos1),
        "object_2_position_km": list(tca_pos2),
        "object_1_velocity_km_s": list(tca_vel1),
        "object_2_velocity_km_s": list(tca_vel2)
    }

@mcp.tool()
def detect_maneuver(
    norad_id: int,
    reference_time: str,
    lookback_hours: int = 48
) -> Dict:
    """
    Detect if a satellite performed a maneuver in the lookback period
    
    Args:
        norad_id: NORAD catalog number
        reference_time: Reference time (ISO format)
        lookback_hours: Hours to look back (default 48)
    
    Returns:
        Dictionary indicating if maneuver detected and velocity statistics
    """
    logger.info(f"Tool 'detect_maneuver' invoked. ID: {norad_id}, Ref Time: {reference_time}, Lookback: {lookback_hours}h")

    # Use internal function
    tle_data = _get_tle_data_internal(norad_id)
    if not tle_data.get("success"):
        logger.error(f"Maneuver detection aborted: TLE fetch failed for ID {norad_id}")
        return tle_data
    
    try:
        sat = parse_tle(tle_data["line1"], tle_data["line2"])
        ref_dt = datetime.fromisoformat(reference_time.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Setup failed for maneuver detection: {e}")
        return {
            "success": False,
            "error": f"Setup failed: {str(e)}"
        }
    
    # Sample velocity at multiple points
    velocities = []
    times = []
    
    logger.debug("Sampling historical velocities...")
    for hours_back in range(0, lookback_hours + 1, 6):  # Sample every 6 hours
        sample_dt = ref_dt - timedelta(hours=hours_back)
        jd, fr = datetime_to_jd(sample_dt)
        
        error, pos, vel = sat.sgp4(jd, fr)
        if error == 0:
            velocities.append(np.linalg.norm(vel))
            times.append(hours_back)
    
    if len(velocities) < 2:
        logger.warning(f"Insufficient data points ({len(velocities)}) for maneuver detection.")
        return {
            "success": False,
            "error": "Insufficient data points for maneuver detection"
        }
    
    # Calculate statistics
    vel_array = np.array(velocities)
    vel_mean = float(np.mean(vel_array))
    vel_std = float(np.std(vel_array))
    vel_max_change = float(np.max(np.abs(np.diff(vel_array))))
    
    # Maneuver detected if velocity change exceeds threshold (0.0005 km/s = 0.5 m/s)
    maneuver_detected = vel_max_change > 0.0005 or vel_std > 0.0003
    
    # Classify object status
    if maneuver_detected:
        status = "ACTIVE"
    elif vel_std < 0.0001:
        status = "DRIFTING"
    else:
        status = "UNCERTAIN"
    
    logger.info(f"Maneuver Analysis Complete. Status: {status} | Max Change: {vel_max_change:.6f} km/s | Detected: {maneuver_detected}")

    return {
        "success": True,
        "norad_id": norad_id,
        "name": tle_data["name"],
        "maneuver_detected": maneuver_detected,
        "status": status,
        "velocity_mean_km_s": vel_mean,
        "velocity_std_km_s": vel_std,
        "max_velocity_change_km_s": vel_max_change,
        "max_velocity_change_m_s": vel_max_change * 1000,
        "lookback_hours": lookback_hours,
        "samples_analyzed": len(velocities)
    }

if __name__ == "__main__":
    # Run the MCP server
    logger.info("Starting Orbital Mechanics MCP Server loop...")
    try:
        mcp.run()
    except Exception as e:
        logger.critical(f"MCP Server crashed: {e}", exc_info=True)