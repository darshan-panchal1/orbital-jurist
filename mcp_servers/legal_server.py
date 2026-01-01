"""
MCP Server for Legal Database and Maritime Law
Provides access to legal precedents and liability frameworks
"""
import sys
import logging
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import List, Dict, Optional
from fastmcp import FastMCP
from utils.data_loader import LegalDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("legal_mcp_server")

# Initialize FastMCP server
logger.info("Initializing FastMCP server 'legal_database_server'...")
mcp = FastMCP("legal_database_server")

# Initialize legal database
try:
    logger.info("Loading LegalDatabase...")
    legal_db = LegalDatabase()
    logger.info("LegalDatabase loaded successfully.")
except Exception as e:
    logger.critical(f"Failed to load LegalDatabase: {e}")
    raise e

# Internal functions (not decorated) for inter-function calls
def _search_maritime_precedents_internal(query: str, top_k: int = 3) -> Dict:
    """Internal function for searching precedents"""
    logger.debug(f"Internal search called with query='{query}', top_k={top_k}")
    try:
        results = legal_db.search(query, top_k=top_k)
        logger.info(f"Internal search found {len(results)} results for query: '{query}'")
        
        return {
            "success": True,
            "query": query,
            "num_results": len(results),
            "precedents": results
        }
    except Exception as e:
        logger.error(f"Internal search failed for query '{query}': {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "query": query
        }

@mcp.tool()
def search_maritime_precedents(query: str, top_k: int = 3) -> Dict:
    """
    Search for relevant maritime law precedents
    
    Args:
        query: Search query describing the situation
        top_k: Number of top results to return (default 3)
    
    Returns:
        Dictionary containing matching precedents
    """
    logger.info(f"Tool 'search_maritime_precedents' invoked. Query: '{query}', Top_k: {top_k}")
    result = _search_maritime_precedents_internal(query, top_k)
    logger.info(f"Tool 'search_maritime_precedents' completed. Success: {result.get('success')}")
    return result

@mcp.tool()
def get_liability_convention_article(article: str) -> Dict:
    """
    Retrieve specific article from the 1972 Liability Convention
    
    Args:
        article: Article identifier (e.g., 'II', 'III', 'IV')
    
    Returns:
        Dictionary containing article text and interpretation
    """
    logger.info(f"Tool 'get_liability_convention_article' invoked. Article: '{article}'")
    
    convention_articles = {
        "II": {
            "title": "Article II - Absolute Liability",
            "text": "A launching State shall be absolutely liable to pay compensation for damage caused by its space object on the surface of the earth or to aircraft flight.",
            "interpretation": "Strict liability for surface damage - no fault requirement",
            "application": "Applies to: Launch failures, re-entry incidents, surface impacts",
            "keywords": ["absolute liability", "surface damage", "launching state"]
        },
        "III": {
            "title": "Article III - Fault-Based Liability",
            "text": "In the event of damage being caused elsewhere than on the surface of the earth to a space object of one launching State or to persons or property on board such a space object by a space object of another launching State, the latter shall be liable only if the damage is due to its fault or the fault of persons for whom it is responsible.",
            "interpretation": "Requires proof of fault/negligence for in-orbit collisions",
            "application": "Applies to: Satellite collisions, orbital debris damage",
            "keywords": ["fault", "negligence", "in-orbit", "space collision"]
        },
        "IV": {
            "title": "Article IV - Joint Launch Liability",
            "text": "In the event of damage being caused to a space object of one launching State or to persons or property on board such a space object by a space object of States which have jointly launched a space object, they shall be jointly and severally liable for any damage caused.",
            "interpretation": "Joint launching states share collective liability",
            "application": "Applies to: Multi-nation launch programs",
            "keywords": ["joint launch", "collective liability", "multiple states"]
        },
        "V": {
            "title": "Article V - Exoneration",
            "text": "Whenever a launching State is exonerated wholly or partially from absolute liability, a launching State may also be exonerated wholly or partially from fault-based liability if it establishes that the damage resulted from gross negligence or from an act or omission done with intent to cause damage on the part of a claimant State.",
            "interpretation": "Defense against liability claims based on claimant's negligence",
            "application": "Applies to: Contributory negligence defenses",
            "keywords": ["exoneration", "gross negligence", "contributory fault"]
        }
    }
    
    article_upper = article.upper()
    
    if article_upper in convention_articles:
        logger.info(f"Article '{article_upper}' found.")
        return {
            "success": True,
            "article": article_upper,
            **convention_articles[article_upper]
        }
    else:
        logger.warning(f"Article '{article}' not found. Available: {list(convention_articles.keys())}")
        return {
            "success": False,
            "error": f"Article {article} not found",
            "available_articles": list(convention_articles.keys())
        }

@mcp.tool()
def analyze_liability_factors(
    object_1_status: str,
    object_2_status: str,
    warning_provided: bool,
    maneuver_possible: bool
) -> Dict:
    """
    Analyze liability factors based on object status and circumstances
    
    Args:
        object_1_status: Status of first object ('ACTIVE', 'DRIFTING', 'UNCERTAIN')
        object_2_status: Status of second object
        warning_provided: Whether conjunction warning was issued
        maneuver_possible: Whether maneuver was technically possible
    
    Returns:
        Dictionary with liability analysis and applicable doctrines
    """
    logger.info(f"Tool 'analyze_liability_factors' invoked. Obj1: {object_1_status}, Obj2: {object_2_status}, Warning: {warning_provided}, Maneuver: {maneuver_possible}")
    
    factors = {
        "applicable_doctrines": [],
        "liability_split": {},
        "reasoning": []
    }
    
    # Determine applicable doctrines
    if object_1_status == "DRIFTING" or object_2_status == "DRIFTING":
        logger.debug("Applying Derelict Vessel Doctrine")
        factors["applicable_doctrines"].append({
            "name": "Derelict Vessel Doctrine",
            "impact": "Drifting object has reduced liability"
        })
    
    if object_1_status == "ACTIVE" and object_2_status == "ACTIVE":
        if warning_provided and maneuver_possible:
            logger.debug("Applying Last Clear Chance & Negligent Navigation Doctrines")
            factors["applicable_doctrines"].append({
                "name": "Last Clear Chance Doctrine",
                "impact": "Both parties had duty to avoid collision"
            })
            factors["applicable_doctrines"].append({
                "name": "Negligent Navigation",
                "impact": "Failure to respond to warning constitutes negligence"
            })
    
    if object_1_status == "DRIFTING" or object_2_status == "DRIFTING":
        logger.debug("Applying Unlit Vessel Liability")
        factors["applicable_doctrines"].append({
            "name": "Unlit Vessel Liability",
            "impact": "Non-maneuvering object bears partial fault for lack of active control"
        })
    
    # Calculate liability split
    if object_1_status == "DRIFTING" and object_2_status == "ACTIVE":
        if warning_provided and maneuver_possible:
            factors["liability_split"] = {
                "object_1": "10-20%",
                "object_2": "80-90%"
            }
            factors["reasoning"].append(
                "Active object had last clear chance to avoid drifting debris"
            )
        else:
            factors["liability_split"] = {
                "object_1": "30-40%",
                "object_2": "60-70%"
            }
            factors["reasoning"].append(
                "Active object bears majority fault, but drifting object shares responsibility"
            )
    
    elif object_1_status == "ACTIVE" and object_2_status == "DRIFTING":
        if warning_provided and maneuver_possible:
            factors["liability_split"] = {
                "object_1": "80-90%",
                "object_2": "10-20%"
            }
            factors["reasoning"].append(
                "Object 1 had capability and warning but failed to maneuver"
            )
        else:
            factors["liability_split"] = {
                "object_1": "60-70%",
                "object_2": "30-40%"
            }
    
    elif object_1_status == "ACTIVE" and object_2_status == "ACTIVE":
        factors["liability_split"] = {
            "object_1": "50%",
            "object_2": "50%"
        }
        factors["reasoning"].append(
            "Both objects were active and capable of avoidance"
        )
    
    else:  # Both drifting or uncertain
        factors["liability_split"] = {
            "object_1": "50%",
            "object_2": "50%"
        }
        factors["reasoning"].append(
            "Neither object had capability to avoid collision"
        )
    
    # Add treaty reference
    factors["treaty_basis"] = "1972 Liability Convention, Article III (Fault-Based Liability)"
    
    logger.info("Liability analysis completed successfully.")
    return {
        "success": True,
        **factors
    }

@mcp.tool()
def get_all_precedents() -> Dict:
    """
    Retrieve all legal precedents in the database
    
    Returns:
        Dictionary containing all precedents
    """
    logger.info("Tool 'get_all_precedents' invoked.")
    try:
        count = len(legal_db.precedents)
        logger.info(f"Retrieved {count} precedents.")
        return {
            "success": True,
            "total_precedents": count,
            "precedents": legal_db.precedents
        }
    except Exception as e:
        logger.error(f"Error retrieving precedents: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def calculate_damages_estimate(
    collision_speed_m_s: float,
    object_mass_kg: float,
    mission_value_usd: Optional[float] = None
) -> Dict:
    """
    Estimate potential damages from collision
    
    Args:
        collision_speed_m_s: Relative collision speed in m/s
        object_mass_kg: Mass of impacted object in kg
        mission_value_usd: Mission value in USD (optional)
    
    Returns:
        Dictionary with damage estimates
    """
    logger.info(f"Tool 'calculate_damages_estimate' invoked. Speed: {collision_speed_m_s} m/s, Mass: {object_mass_kg} kg, Value: {mission_value_usd}")
    
    # Calculate kinetic energy (KE = 0.5 * m * v^2)
    kinetic_energy_j = 0.5 * object_mass_kg * (collision_speed_m_s ** 2)
    kinetic_energy_mj = kinetic_energy_j / 1e6
    
    logger.debug(f"Calculated Kinetic Energy: {kinetic_energy_mj} MJ")
    
    # Estimate damage severity
    if kinetic_energy_mj < 0.1:
        severity = "MINOR"
        damage_probability = "Low - possible surface damage"
    elif kinetic_energy_mj < 10:
        severity = "MODERATE"
        damage_probability = "Medium - likely component damage"
    elif kinetic_energy_mj < 100:
        severity = "SEVERE"
        damage_probability = "High - probable mission loss"
    else:
        severity = "CATASTROPHIC"
        damage_probability = "Very High - catastrophic fragmentation"
    
    logger.info(f"Damage Assessment: {severity}")

    result = {
        "success": True,
        "kinetic_energy_mj": round(kinetic_energy_mj, 2),
        "severity": severity,
        "damage_probability": damage_probability,
        "collision_speed_m_s": collision_speed_m_s,
        "object_mass_kg": object_mass_kg
    }
    
    if mission_value_usd:
        # Estimate financial impact based on severity
        severity_multipliers = {
            "MINOR": 0.05,
            "MODERATE": 0.3,
            "SEVERE": 0.7,
            "CATASTROPHIC": 1.0
        }
        
        estimated_loss = mission_value_usd * severity_multipliers[severity]
        result["mission_value_usd"] = mission_value_usd
        result["estimated_loss_usd"] = round(estimated_loss, 2)
        logger.info(f"Estimated financial loss: ${estimated_loss:,.2f}")
    
    return result

if __name__ == "__main__":
    # Run the MCP server
    logger.info("Starting MCP Server loop...")
    try:
        mcp.run()
    except Exception as e:
        logger.critical(f"MCP Server crashed: {e}", exc_info=True)