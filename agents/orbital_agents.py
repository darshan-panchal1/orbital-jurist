"""
Specialized Agents for Orbital Liability Analysis
"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from config import settings
from utils.groq_client import GroqClient
from workflow.state import (
    OrbitalJuristState,
    PhysicsAnalysisOutput,
    LegalAnalysisOutput,
    LiabilityJudgment
)

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OrbitalAgents")

class PhysicsForensicAgent:
    """
    Agent responsible for establishing physical truth of orbital events
    Uses orbital mechanics tools to determine what actually happened
    """
    
    def __init__(self):
        self.client = GroqClient(model=settings.PHYSICS_MODEL, temperature=0.1)
        self.name = "PhysicsForensic"
        logger.info(f"Initialized {self.name} Agent")
    
    def analyze(self, state: OrbitalJuristState, tools: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform physics forensic analysis
        """
        logger.info(f"[{self.name}] Initiating Physics Forensic Analysis")
        
        obj1_id = state["object_1_id"]
        obj2_id = state["object_2_id"]
        conjunction_time = state["conjunction_time"]
        
        logger.debug(f"[{self.name}] Analyzing Conjunction: Obj1={obj1_id}, Obj2={obj2_id}, Time={conjunction_time}")
        
        # Step 1: Get TLE data for both objects
        logger.info(f"[{self.name}] Fetching TLE data...")
        obj1_tle = tools["get_tle_data"](norad_id=obj1_id)
        obj2_tle = tools["get_tle_data"](norad_id=obj2_id)
        
        if not obj1_tle.get("success") or not obj2_tle.get("success"):
            logger.error(f"[{self.name}] Failed to fetch TLE data. Obj1 Success: {obj1_tle.get('success')}, Obj2 Success: {obj2_tle.get('success')}")
            return {
                **state,
                "error_message": "Failed to fetch TLE data",
                "physics_complete": False
            }
        
        logger.info(f"[{self.name}] Object 1: {obj1_tle['name']} (NORAD {obj1_id})")
        logger.info(f"[{self.name}] Object 2: {obj2_tle['name']} (NORAD {obj2_id})")
        logger.debug(f"[{self.name}] Raw TLE 1: {obj1_tle}")
        logger.debug(f"[{self.name}] Raw TLE 2: {obj2_tle}")
        
        # Step 2: Propagate orbits to conjunction time
        logger.info(f"[{self.name}] Propagating orbits to {conjunction_time}...")
        obj1_state = tools["propagate_orbit"](
            norad_id=obj1_id,
            target_time=conjunction_time
        )
        obj2_state = tools["propagate_orbit"](
            norad_id=obj2_id,
            target_time=conjunction_time
        )
        
        # Step 3: Calculate miss distance
        logger.info(f"[{self.name}] Calculating miss distance...")
        start_time = (datetime.fromisoformat(conjunction_time.replace('Z', '+00:00')) - 
                      timedelta(hours=2)).isoformat()
        end_time = (datetime.fromisoformat(conjunction_time.replace('Z', '+00:00')) + 
                    timedelta(hours=2)).isoformat()
        
        miss_data = tools["calculate_miss_distance"](
            id_1=obj1_id,
            id_2=obj2_id,
            start_time=start_time,
            end_time=end_time,
            time_step_seconds=30
        )
        
        if not miss_data.get("success"):
            logger.error(f"[{self.name}] Failed to calculate miss distance: {miss_data.get('error', 'Unknown error')}")
            return {
                **state,
                "error_message": "Failed to calculate miss distance",
                "physics_complete": False
            }
        
        min_dist = miss_data["minimum_distance_km"]
        collision_occurred = min_dist < settings.COLLISION_THRESHOLD_KM
        
        logger.info(f"[{self.name}] Minimum Distance: {min_dist:.3f} km")
        logger.info(f"[{self.name}] Collision Threshold: {settings.COLLISION_THRESHOLD_KM} km")
        logger.warning(f"[{self.name}] Collision Detected: {'YES' if collision_occurred else 'NO'}")
        
        # Step 4: Detect maneuvers
        logger.info(f"[{self.name}] Analyzing maneuver history...")
        obj1_maneuver = tools["detect_maneuver"](
            norad_id=obj1_id,
            reference_time=conjunction_time,
            lookback_hours=settings.MANEUVER_DETECTION_WINDOW_HOURS
        )
        obj2_maneuver = tools["detect_maneuver"](
            norad_id=obj2_id,
            reference_time=conjunction_time,
            lookback_hours=settings.MANEUVER_DETECTION_WINDOW_HOURS
        )
        
        logger.info(f"[{self.name}] Object 1 Status: {obj1_maneuver.get('status', 'UNKNOWN')}")
        logger.info(f"[{self.name}] Object 2 Status: {obj2_maneuver.get('status', 'UNKNOWN')}")
        logger.debug(f"[{self.name}] Obj1 Maneuver Details: {obj1_maneuver}")
        logger.debug(f"[{self.name}] Obj2 Maneuver Details: {obj2_maneuver}")
        
        # Step 5: Use LLM to synthesize findings
        physics_prompt = f"""As a Physics Forensic Expert analyzing an orbital conjunction event, synthesize the following data:

OBJECT 1: {obj1_tle['name']} (NORAD {obj1_id})
- Status: {obj1_maneuver.get('status', 'UNKNOWN')}
- Maneuver Detected: {obj1_maneuver.get('maneuver_detected', False)}
- Position at TCA: {obj1_state['position_km']}
- Velocity at TCA: {obj1_state['velocity_km_s']}

OBJECT 2: {obj2_tle['name']} (NORAD {obj2_id})
- Status: {obj2_maneuver.get('status', 'UNKNOWN')}
- Maneuver Detected: {obj2_maneuver.get('maneuver_detected', False)}
- Position at TCA: {obj2_state['position_km']}
- Velocity at TCA: {obj2_state['velocity_km_s']}

CONJUNCTION DATA:
- Time of Closest Approach: {miss_data['time_of_closest_approach']}
- Minimum Distance: {min_dist:.3f} km
- Relative Speed: {miss_data['relative_speed_m_s']:.1f} m/s
- Collision Type: {miss_data['collision_type']}
- Collision Occurred: {collision_occurred}

Provide a concise technical summary (3-4 sentences) focusing on:
1. The objective facts of what happened
2. The status and control capability of each object
3. Whether the conjunction was avoidable by either party
"""
        logger.debug(f"[{self.name}] Sending prompt to LLM: {physics_prompt[:200]}...") # Log start of prompt
        
        messages = [
            {"role": "system", "content": "You are an expert in orbital mechanics and space situational awareness. Provide factual, technical analysis."},
            {"role": "user", "content": physics_prompt}
        ]
        
        response = self.client.chat(messages, max_tokens=500)
        physics_summary = response.get("content", "Analysis failed")
        
        logger.info(f"[{self.name}] PHYSICS SUMMARY Generated")
        logger.debug(f"[{self.name}] Full Summary: {physics_summary}")
        
        # Update state
        return {
            **state,
            "physics_complete": True,
            "object_1_data": {
                "norad_id": obj1_id,
                "name": obj1_tle["name"],
                "status": obj1_maneuver.get("status", "UNKNOWN"),
                "maneuver_detected": obj1_maneuver.get("maneuver_detected", False),
                "state_vector": obj1_state
            },
            "object_2_data": {
                "norad_id": obj2_id,
                "name": obj2_tle["name"],
                "status": obj2_maneuver.get("status", "UNKNOWN"),
                "maneuver_detected": obj2_maneuver.get("maneuver_detected", False),
                "state_vector": obj2_state
            },
            "miss_distance_data": miss_data,
            "maneuver_analysis": {
                "object_1": obj1_maneuver,
                "object_2": obj2_maneuver
            },
            "current_step": "legal_analysis",
            "messages": state["messages"] + [
                {"role": "assistant", "content": f"[PhysicsForensic] {physics_summary}"}
            ]
        }


class MaritimeScholarAgent:
    """
    Agent responsible for finding applicable legal precedents
    Uses maritime law and space treaties to establish legal framework
    """
    
    def __init__(self):
        self.client = GroqClient(model=settings.SCHOLAR_MODEL, temperature=0.1)
        self.name = "MaritimeScholar"
        logger.info(f"Initialized {self.name} Agent")
    
    def analyze(self, state: OrbitalJuristState, tools: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform legal analysis based on physics findings
        """
        logger.info(f"[{self.name}] Initiating Legal Analysis")
        
        obj1 = state["object_1_data"]
        obj2 = state["object_2_data"]
        miss_data = state["miss_distance_data"]
        
        # Step 1: Search for relevant precedents based on object status
        logger.info(f"[{self.name}] Searching legal precedents based on status: Obj1={obj1['status']}, Obj2={obj2['status']}")
        
        search_queries = []
        if obj1["status"] == "DRIFTING" or obj2["status"] == "DRIFTING":
            search_queries.append("derelict vessel drifting")
        if obj1["status"] == "ACTIVE" and obj2["status"] == "ACTIVE":
            search_queries.append("negligent navigation duty to avoid")
        if miss_data["minimum_distance_km"] < settings.COLLISION_THRESHOLD_KM:
            search_queries.append("collision liability fault")
            
        logger.debug(f"[{self.name}] Generated search queries: {search_queries}")
        
        all_precedents = []
        for query in search_queries:
            logger.debug(f"[{self.name}] Executing search: '{query}'")
            result = tools["search_maritime_precedents"](query=query, top_k=2)
            if result.get("success"):
                all_precedents.extend(result["precedents"])
            else:
                logger.warning(f"[{self.name}] Search failed for query '{query}': {result.get('error')}")
        
        # Remove duplicates
        seen_ids = set()
        unique_precedents = []
        for p in all_precedents:
            if p["id"] not in seen_ids:
                unique_precedents.append(p)
                seen_ids.add(p["id"])
        
        logger.info(f"[{self.name}] Found {len(unique_precedents)} unique relevant precedents")
        for p in unique_precedents:
            logger.info(f"  - Found Precedent: {p['title']}")
        
        # Step 2: Get applicable treaty article
        logger.info(f"[{self.name}] Retrieving treaty provisions...")
        treaty_article = tools["get_liability_convention_article"](article="III")
        logger.debug(f"[{self.name}] Treaty Article retrieved: {treaty_article.get('text', '')[:100]}...")
        
        # Step 3: Analyze liability factors
        logger.info(f"[{self.name}] Analyzing liability factors...")
        liability_analysis = tools["analyze_liability_factors"](
            object_1_status=obj1["status"],
            object_2_status=obj2["status"],
            warning_provided=True,  # Assume conjunction warnings available
            maneuver_possible=obj1["status"] == "ACTIVE" or obj2["status"] == "ACTIVE"
        )
        
        logger.info(f"[{self.name}] Applicable Doctrines Analysis Complete")
        for doctrine in liability_analysis.get("applicable_doctrines", []):
            logger.debug(f"  - Doctrine: {doctrine['name']} (Impact: {doctrine['impact']})")
        
        # Step 4: Use LLM to synthesize legal position
        legal_prompt = f"""As a Maritime Law Scholar specializing in space law, analyze this case:

PHYSICAL FACTS:
- Object 1 ({obj1['name']}): {obj1['status']}
- Object 2 ({obj2['name']}): {obj2['status']}
- Minimum Distance: {miss_data['minimum_distance_km']:.3f} km
- Collision Type: {miss_data['collision_type']}

APPLICABLE PRECEDENTS:
{json.dumps(unique_precedents, indent=2)}

TREATY BASIS:
{treaty_article['text']}

LIABILITY ANALYSIS:
{json.dumps(liability_analysis, indent=2)}

Provide a legal opinion (3-4 sentences) addressing:
1. Which legal doctrines apply and why
2. How maritime precedents inform this orbital case
3. The legal basis for liability assignment
"""
        logger.debug(f"[{self.name}] Sending prompt to LLM...")
        
        messages = [
            {"role": "system", "content": "You are an expert in maritime law and space law, particularly liability conventions. Provide clear legal reasoning."},
            {"role": "user", "content": legal_prompt}
        ]
        
        response = self.client.chat(messages, max_tokens=600)
        legal_summary = response.get("content", "Analysis failed")
        
        logger.info(f"[{self.name}] LEGAL OPINION Generated")
        logger.debug(f"[{self.name}] Full Opinion: {legal_summary}")
        
        # Update state
        return {
            **state,
            "legal_complete": True,
            "applicable_precedents": unique_precedents,
            "treaty_articles": [treaty_article],
            "liability_factors": liability_analysis,
            "current_step": "adjudication",
            "messages": state["messages"] + [
                {"role": "assistant", "content": f"[MaritimeScholar] {legal_summary}"}
            ]
        }


class LiabilityJudgeAgent:
    """
    Agent responsible for final adjudication
    Synthesizes physics and legal analysis into binding judgment
    """
    
    def __init__(self):
        self.client = GroqClient(model=settings.JUDGE_MODEL, temperature=0.1)
        self.name = "LiabilityJudge"
        logger.info(f"Initialized {self.name} Agent")
    
    def adjudicate(self, state: OrbitalJuristState, tools: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render final judgment on liability
        """
        logger.info(f"[{self.name}] Rendering Final Judgment")
        
        obj1 = state["object_1_data"]
        obj2 = state["object_2_data"]
        miss_data = state["miss_distance_data"]
        precedents = state["applicable_precedents"]
        liability_factors = state["liability_factors"]
        
        # Calculate damage estimate if collision occurred
        damage_estimate = None
        if miss_data["minimum_distance_km"] < settings.COLLISION_THRESHOLD_KM:
            logger.info(f"[{self.name}] Calculating damage estimate (Collision Detected)...")
            # Assume typical CubeSat mass if not known
            damage_estimate = tools["calculate_damages_estimate"](
                collision_speed_m_s=miss_data["relative_speed_m_s"],
                object_mass_kg=10.0,  # Default estimate
                mission_value_usd=1000000.0  # Default estimate
            )
            logger.info(f"[{self.name}] Damage Severity Calculated: {damage_estimate['severity']}")
            logger.debug(f"[{self.name}] Full Damage Estimate: {damage_estimate}")
        else:
            logger.info(f"[{self.name}] No collision detected, skipping damage estimate.")
        
        # Construct comprehensive judgment prompt
        judgment_prompt = f"""As the Liability Judge in this orbital arbitration, render a final, binding judgment.

CASE: {obj1['name']} vs {obj2['name']}

PHYSICAL EVIDENCE:
- Object 1 Status: {obj1['status']} (Maneuver: {obj1['maneuver_detected']})
- Object 2 Status: {obj2['status']} (Maneuver: {obj2['maneuver_detected']})
- Minimum Distance: {miss_data['minimum_distance_km']:.3f} km
- Relative Speed: {miss_data['relative_speed_m_s']:.1f} m/s
- Collision Type: {miss_data['collision_type']}
- Collision Occurred: {miss_data['minimum_distance_km'] < settings.COLLISION_THRESHOLD_KM}

APPLICABLE LAW:
{json.dumps([p['title'] for p in precedents], indent=2)}

LIABILITY FACTORS:
Suggested Split: {liability_factors['liability_split']}
Reasoning: {liability_factors['reasoning']}

DAMAGE ASSESSMENT:
{json.dumps(damage_estimate, indent=2) if damage_estimate else "No collision - no damages"}

Provide a complete judgment in JSON format with these exact fields:
{{
  "case_summary": "2-3 sentence summary",
  "fault_percentage_object_1": <number 0-100>,
  "fault_percentage_object_2": <number 0-100>,
  "primary_reasoning": "Main legal reasoning for this split",
  "applicable_doctrines": ["doctrine1", "doctrine2"],
  "treaty_basis": "1972 Liability Convention Article III",
  "recommendations": ["recommendation1", "recommendation2"]
}}

The fault percentages MUST sum to 100. Base your decision on both physical facts and legal principles.
"""
        logger.debug(f"[{self.name}] Constructing Judgment Prompt...")
        
        messages = [
            {"role": "system", "content": "You are a Judge specialized in space law and orbital liability. Render fair, reasoned judgments based on evidence and law. Output ONLY valid JSON."},
            {"role": "user", "content": judgment_prompt}
        ]
        
        # Get structured judgment
        schema = {
            "type": "object",
            "properties": {
                "case_summary": {"type": "string"},
                "fault_percentage_object_1": {"type": "number"},
                "fault_percentage_object_2": {"type": "number"},
                "primary_reasoning": {"type": "string"},
                "applicable_doctrines": {"type": "array", "items": {"type": "string"}},
                "treaty_basis": {"type": "string"},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
        
        logger.info(f"[{self.name}] Awaiting Structured Output from Model...")
        judgment = self.client.structured_output(messages, schema)
        
        if judgment.get("error"):
            logger.error(f"[{self.name}] Structured Output ERROR: {judgment['error']}")
            return {
                **state,
                "error_message": judgment["error"],
                "verdict_complete": False
            }
        
        # Enhance judgment with full context
        final_judgment = {
            **judgment,
            "physical_findings": {
                "object_1": obj1,
                "object_2": obj2,
                "miss_distance_km": miss_data["minimum_distance_km"],
                "collision_occurred": miss_data["minimum_distance_km"] < settings.COLLISION_THRESHOLD_KM
            },
            "legal_findings": {
                "precedents": precedents,
                "liability_factors": liability_factors
            },
            "damage_estimate": damage_estimate,
            "judgment_date": datetime.now().isoformat(),
            "adjudicating_authority": "Orbital Jurist Autonomous System v1.0"
        }
        
        logger.info(f"[{self.name}] FINAL JUDGMENT RENDERED")
        logger.info(f"Case: {judgment.get('case_summary', 'N/A')}")
        logger.info(f"Fault Split: Object 1: {judgment.get('fault_percentage_object_1', 0)}% | Object 2: {judgment.get('fault_percentage_object_2', 0)}%")
        logger.info(f"Reasoning: {judgment.get('primary_reasoning', 'N/A')}")
        logger.info(f"Treaty Basis: {judgment.get('treaty_basis', 'N/A')}")
        logger.debug(f"[{self.name}] Full JSON Judgment: {json.dumps(final_judgment, indent=2)}")
        
        return {
            **state,
            "verdict_complete": True,
            "final_judgment": final_judgment,
            "current_step": "complete",
            "messages": state["messages"] + [
                {"role": "assistant", "content": f"[LiabilityJudge] {judgment.get('case_summary', 'Judgment rendered')}"}
            ]
        }