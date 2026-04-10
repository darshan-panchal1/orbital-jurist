"""
Specialized Agents for Orbital Liability Analysis
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict

from config import settings
from prompts.registry import get_prompt
from utils.groq_client import GroqClient
from utils.logging_config import get_logger
from workflow.state import OrbitalJuristState

logger = get_logger("agents")


# ── Doctrine whitelist per status combination ─────────────────────────────────
# Ensures the Judge can only cite doctrines that are factually applicable.
# Keys are (obj1_status, obj2_status); values are allowable doctrine titles.
_APPLICABLE_DOCTRINES: Dict[tuple, list] = {
    ("ACTIVE",    "ACTIVE"):    ["Last Clear Chance Doctrine", "Negligent Navigation"],
    ("ACTIVE",    "DRIFTING"):  ["Last Clear Chance Doctrine", "Negligent Navigation",
                                 "Derelict Vessel Doctrine", "Unlit Vessel Liability"],
    ("DRIFTING",  "ACTIVE"):    ["Last Clear Chance Doctrine", "Negligent Navigation",
                                 "Derelict Vessel Doctrine", "Unlit Vessel Liability"],
    ("DRIFTING",  "DRIFTING"):  ["Derelict Vessel Doctrine", "Unlit Vessel Liability",
                                 "The Rhodian Law on Jettison"],
    ("ACTIVE",    "UNCERTAIN"): ["Last Clear Chance Doctrine", "Negligent Navigation"],
    ("UNCERTAIN", "ACTIVE"):    ["Last Clear Chance Doctrine", "Negligent Navigation"],
    ("UNCERTAIN", "DRIFTING"):  ["Derelict Vessel Doctrine", "Unlit Vessel Liability"],
    ("DRIFTING",  "UNCERTAIN"): ["Derelict Vessel Doctrine", "Unlit Vessel Liability"],
    ("UNCERTAIN", "UNCERTAIN"): ["The Rhodian Law on Jettison"],
}


def _get_allowed_doctrines(status1: str, status2: str) -> list:
    """Return the doctrine whitelist for this status pair, falling back to empty."""
    key = (status1.upper(), status2.upper())
    return _APPLICABLE_DOCTRINES.get(key, [])


def _filter_precedents_by_status(precedents: list, status1: str, status2: str) -> list:
    """
    Remove precedents whose titles are not in the allowed whitelist for the
    given status combination.  Prevents the Judge from citing inapplicable law.
    """
    allowed = set(_get_allowed_doctrines(status1, status2))
    return [p for p in precedents if p.get("title") in allowed]


# ─────────────────────────────────────────────────────────────────────────────
# NoRiskVerdictAgent  (deterministic — zero LLM calls)
# ─────────────────────────────────────────────────────────────────────────────

class NoRiskVerdictAgent:
    """
    Renders a deterministic "no conjunction risk" judgment when miss distance
    exceeds CONJUNCTION_RISK_THRESHOLD_KM.

    No LLM call is made.  The verdict is constructed purely from physics data
    and the hardcoded legal rule: Article III requires actual damage — without
    damage there is no cause of action.
    """

    def render(self, state: OrbitalJuristState) -> OrbitalJuristState:
        obj1      = state["object_1_data"]
        obj2      = state["object_2_data"]
        miss_data = state["miss_distance_data"]
        min_dist  = miss_data["minimum_distance_km"]
        threshold = settings.CONJUNCTION_RISK_THRESHOLD_KM

        logger.info(
            "NoRiskVerdict: miss distance exceeds conjunction threshold — dismissing",
            extra={
                "min_dist_km":  round(min_dist, 1),
                "threshold_km": threshold,
            },
        )

        case_summary = get_prompt(
            "no_risk_summary",
            obj1_name=obj1["sat_name"],
            obj2_name=obj2["sat_name"],
            min_distance_km=min_dist,
            times_threshold=min_dist / threshold,
            threshold_km=threshold,
        )

        final_judgment = {
            "case_summary":              case_summary,
            "fault_percentage_object_1": 0.0,
            "fault_percentage_object_2": 0.0,
            "primary_reasoning": (
                "No damage occurred. Article III of the 1972 Liability Convention "
                "requires proof of both fault and actual damage. With a miss distance "
                f"of {min_dist:.1f} km — {min_dist / threshold:.0f}x the "
                f"{threshold} km operational conjunction warning threshold — "
                "there is no damage and therefore no cause of action."
            ),
            "applicable_doctrines": [],
            "treaty_basis": "1972 Liability Convention, Article III (no damage — case dismissed)",
            "recommendations": [
                "No immediate action required — objects are operating safely.",
                "Continue standard Space Situational Awareness monitoring.",
                "Revisit if future TLE updates indicate an approaching conjunction.",
            ],
            "physical_findings": {
                "object_1":           obj1,
                "object_2":           obj2,
                "miss_distance_km":   min_dist,
                "collision_occurred": False,
                "conjunction_risk":   False,
            },
            "legal_findings": {
                "precedents":        [],
                "liability_factors": {},
            },
            "damage_estimate":        None,
            "judgment_date":          datetime.utcnow().isoformat() + "Z",
            "adjudicating_authority": "Orbital Jurist Autonomous System v1.0",
            "prompt_version":         settings.PROMPT_VERSION,
        }

        return {
            **state,
            "verdict_complete":      True,
            "final_judgment":        final_judgment,
            "applicable_precedents": [],
            "treaty_articles":       [],
            "liability_factors":     {},
            "legal_complete":        True,
            "current_step":          "complete",
            "messages": state["messages"] + [
                {
                    "role":    "assistant",
                    "content": f"[NoRiskVerdict] {case_summary}",
                }
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# PhysicsForensicAgent
# ─────────────────────────────────────────────────────────────────────────────

class PhysicsForensicAgent:
    """
    Agent responsible for establishing physical truth of orbital events.
    Uses orbital mechanics tools to determine what actually happened.
    """

    def __init__(self):
        self.client = GroqClient(model=settings.PHYSICS_MODEL, temperature=0.1)
        self.name   = "PhysicsForensic"
        logger.info(f"Initialized {self.name} Agent",
                    extra={"model": settings.PHYSICS_MODEL})

    def analyze(
        self, state: OrbitalJuristState, tools: Dict[str, Any]
    ) -> OrbitalJuristState:
        """
        Perform physics forensic analysis
        """
        logger.info(f"[{self.name}] Initiating Physics Forensic Analysis")

        obj1_id          = state["object_1_id"]
        obj2_id          = state["object_2_id"]
        conjunction_time = state["conjunction_time"]

        logger.debug(
            f"[{self.name}] Conjunction parameters",
            extra={"obj1": obj1_id, "obj2": obj2_id, "time": conjunction_time},
        )

        # Step 1: Get TLE data for both objects
        logger.info(f"[{self.name}] Fetching TLE data...")
        
        # FIX: Capture the raw responses from the MCP tool
        res1 = tools["get_tle_data"](norad_id=obj1_id)
        res2 = tools["get_tle_data"](norad_id=obj2_id)

        # FIX: Unpack 'data' if the tool wraps the result, otherwise use the response itself
        obj1_tle = res1.get("data", res1) if res1.get("success") else res1
        obj2_tle = res2.get("data", res2) if res2.get("success") else res2

        if not res1.get("success") or not res2.get("success"):
            logger.error(
                f"[{self.name}] Failed to fetch TLE data",
                extra={
                    "obj1_ok": res1.get("success"),
                    "obj2_ok": res2.get("success"),
                },
            )
            return {
                **state,
                "error_message":   "Failed to fetch TLE data",
                "physics_complete": False,
            }

        # FIX: Use .get() to avoid KeyError if sat_name is missing or renamed
        logger.info(
            f"[{self.name}] TLE data ready",
            extra={
                "obj1": obj1_tle.get("sat_name", "UNKNOWN"), 
                "obj2": obj2_tle.get("sat_name", "UNKNOWN")
            },
        )

        # Step 2: Propagate orbits to conjunction time
        logger.info(f"[{self.name}] Propagating orbits to {conjunction_time}...")
        obj1_state = tools["propagate_orbit"](
            norad_id=obj1_id, target_time=conjunction_time
        )
        obj2_state = tools["propagate_orbit"](
            norad_id=obj2_id, target_time=conjunction_time
        )

        # Step 3: Calculate miss distance
        logger.info(f"[{self.name}] Calculating miss distance...")
        ref = datetime.fromisoformat(conjunction_time.replace("Z", "+00:00"))
        miss_data = tools["calculate_miss_distance"](
            id_1=obj1_id,
            id_2=obj2_id,
            start_time=(ref - timedelta(hours=2)).isoformat(),
            end_time=(ref + timedelta(hours=2)).isoformat(),
            time_step_seconds=30,
        )

        if not miss_data.get("success"):
            logger.error(
                f"[{self.name}] Failed to calculate miss distance",
                extra={"error": miss_data.get("error")},
            )
            return {
                **state,
                "error_message":   "Failed to calculate miss distance",
                "physics_complete": False,
            }

        min_dist  = miss_data["minimum_distance_km"]
        collision = min_dist < settings.COLLISION_THRESHOLD_KM

        logger.info(
            f"[{self.name}] Closest approach computed",
            extra={
                "min_dist_km":    round(min_dist, 3),
                "collision":      collision,
                "conjunction":    min_dist <= settings.CONJUNCTION_RISK_THRESHOLD_KM,
            },
        )

        # Step 4: Classify object status
        logger.info(f"[{self.name}] Classifying object status...")
        obj1_maneuver = tools["detect_maneuver"](
            norad_id=obj1_id,
            reference_time=conjunction_time,
            lookback_hours=settings.MANEUVER_DETECTION_WINDOW_HOURS,
        )
        obj2_maneuver = tools["detect_maneuver"](
            norad_id=obj2_id,
            reference_time=conjunction_time,
            lookback_hours=settings.MANEUVER_DETECTION_WINDOW_HOURS,
        )

        logger.info(
            f"[{self.name}] Status classification complete",
            extra={
                "obj1_status": obj1_maneuver.get("status"),
                "obj2_status": obj2_maneuver.get("status"),
            },
        )

        # Step 5: Use LLM to synthesize findings
        prompt = get_prompt(
            "physics_summary",
            obj1_name=obj1_tle.get("sat_name", f"NORAD {obj1_id}"),
            obj1_id=obj1_id,
            obj1_status=obj1_maneuver.get("status", "UNKNOWN"),
            obj1_confidence=obj1_maneuver.get("classification_confidence", "?"),
            obj1_method=obj1_maneuver.get("method", "?"),
            obj1_position=obj1_state.get("position_km"),
            obj1_velocity=obj1_state.get("velocity_km_s"),
            obj2_name=obj2_tle.get("sat_name", f"NORAD {obj2_id}"),
            obj2_id=obj2_id,
            obj2_status=obj2_maneuver.get("status", "UNKNOWN"),
            obj2_confidence=obj2_maneuver.get("classification_confidence", "?"),
            obj2_method=obj2_maneuver.get("method", "?"),
            obj2_position=obj2_state.get("position_km"),
            obj2_velocity=obj2_state.get("velocity_km_s"),
            tca_time=miss_data["time_of_closest_approach"],
            min_distance_km=min_dist,
            threshold_km=settings.COLLISION_THRESHOLD_KM,
            rel_speed_ms=miss_data["relative_speed_m_s"],
            collision_type=miss_data["collision_type"],
            collision_occurred=collision,
            confidence_note=(
                "Status inferred from object name, epoch age, and BSTAR. "
                "Multi-TLE historical analysis not performed."
            ),
        )

        logger.debug(f"[{self.name}] Sending prompt to LLM")

        response = self.client.chat(
            messages=[
                {"role": "system", "content": get_prompt("physics_system")},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=512,
        )

        if response.get("error"):
            logger.error(f"[{self.name}] LLM synthesis failed",
                         extra={"error": response["error"]})
            return {
                **state,
                "error_message":   f"LLM error: {response['error']}",
                "physics_complete": False,
            }

        summary = response["content"]
        logger.info(f"[{self.name}] Physics summary generated")

        # FIX: Populate state with safe .get() values
        return {
            **state,
            "physics_complete": True,
            "object_1_data": {
                "norad_id":          obj1_id,
                "sat_name":          obj1_tle.get("sat_name", f"NORAD {obj1_id}"),
                "status":            obj1_maneuver.get("status", "UNKNOWN"),
                "confidence":        obj1_maneuver.get("classification_confidence", "?"),
                "maneuver_detected": obj1_maneuver.get("maneuver_detected", False),
                "state_vector":      obj1_state,
            },
            "object_2_data": {
                "norad_id":          obj2_id,
                "sat_name":          obj2_tle.get("sat_name", f"NORAD {obj2_id}"),
                "status":            obj2_maneuver.get("status", "UNKNOWN"),
                "confidence":        obj2_maneuver.get("classification_confidence", "?"),
                "maneuver_detected": obj2_maneuver.get("maneuver_detected", False),
                "state_vector":      obj2_state,
            },
            "miss_distance_data": miss_data,
            "maneuver_analysis": {
                "object_1": obj1_maneuver,
                "object_2": obj2_maneuver,
            },
            "current_step": "legal_analysis",
            "messages": state["messages"] + [
                {"role": "assistant", "content": f"[PhysicsForensic] {summary}"}
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# MaritimeScholarAgent
# ─────────────────────────────────────────────────────────────────────────────

class MaritimeScholarAgent:
    """
    Agent responsible for finding applicable legal precedents.
    Uses maritime law and space treaties to establish legal framework.
    """

    def __init__(self):
        self.client = GroqClient(model=settings.SCHOLAR_MODEL, temperature=0.1)
        self.name   = "MaritimeScholar"
        logger.info(f"Initialized {self.name} Agent",
                    extra={"model": settings.SCHOLAR_MODEL})

    def analyze(
        self, state: OrbitalJuristState, tools: Dict[str, Any]
    ) -> OrbitalJuristState:
        """
        Perform legal analysis based on physics findings
        """
        logger.info(f"[{self.name}] Initiating Legal Analysis")

        obj1      = state["object_1_data"]
        obj2      = state["object_2_data"]
        miss_data = state["miss_distance_data"]
        collision = miss_data["minimum_distance_km"] < settings.COLLISION_THRESHOLD_KM

        logger.info(
            f"[{self.name}] Object statuses",
            extra={"obj1_status": obj1["status"], "obj2_status": obj2["status"]},
        )

        # Step 1: Build status-aware search queries
        queries = []
        if obj1["status"] == "DRIFTING" or obj2["status"] == "DRIFTING":
            queries.append("derelict vessel drifting uncontrolled")
        if obj1["status"] == "ACTIVE" or obj2["status"] == "ACTIVE":
            queries.append("last clear chance active control avoidance")
        if collision:
            queries.append("collision liability fault negligence")
        if not queries:
            queries.append("orbital collision liability space")

        logger.debug(f"[{self.name}] Search queries generated",
                     extra={"queries": queries})

        # Step 2: Search precedents, then filter to only factually applicable ones
        seen_ids:       set  = set()
        raw_precedents: list = []
        for q in queries:
            res = tools["search_maritime_precedents"](query=q, top_k=3)
            if res.get("success"):
                for p in res["precedents"]:
                    if p["id"] not in seen_ids:
                        raw_precedents.append(p)
                        seen_ids.add(p["id"])
            else:
                logger.warning(f"[{self.name}] Precedent search failed",
                               extra={"query": q, "error": res.get("error")})

        # Filter to only doctrines appropriate for this status combination
        precedents = _filter_precedents_by_status(
            raw_precedents, obj1["status"], obj2["status"]
        )

        discarded = len(raw_precedents) - len(precedents)
        if discarded > 0:
            logger.info(
                f"[{self.name}] Precedent filtering removed inapplicable doctrines",
                extra={
                    "raw":       len(raw_precedents),
                    "filtered":  len(precedents),
                    "discarded": discarded,
                    "statuses":  f"{obj1['status']} vs {obj2['status']}",
                },
            )

        logger.info(f"[{self.name}] Applicable precedents after filtering",
                    extra={"count": len(precedents)})

        # Step 3: Get applicable treaty article
        logger.info(f"[{self.name}] Retrieving treaty provisions...")
        treaty_article = tools["get_liability_convention_article"](article="III")

        # Step 4: Analyze liability factors — pass collision_occurred
        logger.info(f"[{self.name}] Analyzing liability factors...")
        liability_analysis = tools["analyze_liability_factors"](
            object_1_status=obj1["status"],
            object_2_status=obj2["status"],
            warning_provided=True,
            maneuver_possible=(
                obj1["status"] == "ACTIVE" or obj2["status"] == "ACTIVE"
            ),
            collision_occurred=collision,
        )

        # Step 5: LLM synthesis
        prompt = get_prompt(
            "scholar_opinion",
            obj1_name=obj1["sat_name"],
            obj1_status=obj1["status"],
            obj2_name=obj2["sat_name"],
            obj2_status=obj2["status"],
            min_distance_km=miss_data["minimum_distance_km"],
            collision_type=miss_data["collision_type"],
            precedents_json=json.dumps(precedents, indent=2),
            treaty_text=treaty_article.get("text", ""),
            liability_json=json.dumps(liability_analysis, indent=2),
        )

        logger.debug(f"[{self.name}] Sending prompt to LLM")

        response = self.client.chat(
            messages=[
                {"role": "system", "content": get_prompt("scholar_system")},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=600,
        )

        if response.get("error"):
            logger.error(f"[{self.name}] Scholar LLM failed",
                         extra={"error": response["error"]})
            return {
                **state,
                "error_message": f"LLM error: {response['error']}",
                "legal_complete": False,
            }

        opinion = response["content"]
        logger.info(f"[{self.name}] Legal opinion generated")

        return {
            **state,
            "legal_complete":        True,
            "applicable_precedents": precedents,
            "treaty_articles":       [treaty_article],
            "liability_factors":     liability_analysis,
            "current_step":          "adjudication",
            "messages": state["messages"] + [
                {"role": "assistant", "content": f"[MaritimeScholar] {opinion}"}
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# LiabilityJudgeAgent
# ─────────────────────────────────────────────────────────────────────────────

class LiabilityJudgeAgent:
    """
    Agent responsible for final adjudication.
    Synthesizes physics and legal analysis into binding judgment.
    """

    def __init__(self):
        self.client = GroqClient(model=settings.JUDGE_MODEL, temperature=0.1)
        self.name   = "LiabilityJudge"
        logger.info(f"Initialized {self.name} Agent",
                    extra={"model": settings.JUDGE_MODEL})

    def adjudicate(
        self, state: OrbitalJuristState, tools: Dict[str, Any]
    ) -> OrbitalJuristState:
        """
        Render final judgment on liability
        """
        logger.info(f"[{self.name}] Rendering Final Judgment")

        obj1       = state["object_1_data"]
        obj2       = state["object_2_data"]
        miss_data  = state["miss_distance_data"]
        precedents = state["applicable_precedents"] or []
        liability  = state["liability_factors"]      or {}
        collision  = miss_data["minimum_distance_km"] < settings.COLLISION_THRESHOLD_KM

        # ── Hard treaty basis anchor ─────────────────────────────────────────
        # Pull the exact title from the retrieved article rather than letting
        # the LLM choose.  This prevents hallucinated treaty references.
        treaty_articles = state.get("treaty_articles") or []
        if treaty_articles and treaty_articles[0].get("title"):
            treaty_basis_value = treaty_articles[0]["title"]
        else:
            treaty_basis_value = "1972 Liability Convention, Article III (Fault-Based Liability)"

        logger.info(
            f"[{self.name}] Adjudication parameters",
            extra={
                "collision":    collision,
                "obj1":         obj1["sat_name"],
                "obj2":         obj2["sat_name"],
                "treaty_basis": treaty_basis_value,
            },
        )

        # ── Damage estimate (only if collision) ───────────────────────────────
        damage = None
        if collision:
            logger.info(f"[{self.name}] Calculating damage estimate...")
            damage = tools["calculate_damages_estimate"](
                collision_speed_m_s=miss_data["relative_speed_m_s"],
                object_mass_kg=10.0,
                mission_value_usd=1_000_000.0,
            )
            logger.info(f"[{self.name}] Damage severity: {damage.get('severity')}")
        else:
            logger.info(f"[{self.name}] No collision — skipping damage estimate.")

        # ── Build the allowed doctrine list from filtered precedents ──────────
        allowed_doctrine_titles = [p["title"] for p in precedents]

        prompt = get_prompt(
            "judge_judgment",
            obj1_name=obj1["sat_name"],
            obj1_id=obj1["norad_id"],
            obj1_status=obj1["status"],
            obj1_confidence=obj1.get("confidence", "?"),
            obj2_name=obj2["sat_name"],
            obj2_id=obj2["norad_id"],
            obj2_status=obj2["status"],
            obj2_confidence=obj2.get("confidence", "?"),
            min_distance_km=miss_data["minimum_distance_km"],
            rel_speed_ms=miss_data["relative_speed_m_s"],
            collision_type=miss_data["collision_type"],
            collision_occurred=collision,
            doctrines_json=json.dumps(allowed_doctrine_titles, indent=2),
            suggested_split=liability.get("liability_split", {}),
            factor_reasoning="; ".join(liability.get("reasoning", [])),
            damage_json=(
                json.dumps(damage, indent=2) if damage else "No collision — no damages"
            ),
            treaty_basis_value=treaty_basis_value,
        )

        schema = {
            "type": "object",
            "properties": {
                "case_summary":              {"type": "string"},
                "fault_percentage_object_1": {"type": "number"},
                "fault_percentage_object_2": {"type": "number"},
                "primary_reasoning":         {"type": "string"},
                "applicable_doctrines":      {
                    "type":  "array",
                    "items": {"type": "string"},
                },
                "treaty_basis":    {"type": "string"},
                "recommendations": {
                    "type":  "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "case_summary",
                "fault_percentage_object_1",
                "fault_percentage_object_2",
                "primary_reasoning",
                "applicable_doctrines",
                "treaty_basis",
                "recommendations",
            ],
        }

        logger.info(f"[{self.name}] Awaiting structured output from model...")
        judgment = self.client.structured_output(
            messages=[
                {"role": "system", "content": get_prompt("judge_system")},
                {"role": "user",   "content": prompt},
            ],
            schema=schema,
        )

        if judgment.get("error"):
            logger.error(f"[{self.name}] Structured output failed",
                         extra={"error": judgment["error"]})
            return {
                **state,
                "error_message":   judgment["error"],
                "verdict_complete": False,
            }

        # ── Post-processing guardrails ────────────────────────────────────────

        # 1. Enforce zero fault when no collision occurred
        if not collision:
            if judgment.get("fault_percentage_object_1", 0) != 0 \
               or judgment.get("fault_percentage_object_2", 0) != 0:
                logger.warning(
                    f"[{self.name}] Model assigned non-zero fault despite no collision"
                    " — correcting to 0/0",
                    extra={
                        "f1": judgment.get("fault_percentage_object_1"),
                        "f2": judgment.get("fault_percentage_object_2"),
                    },
                )
            judgment["fault_percentage_object_1"] = 0.0
            judgment["fault_percentage_object_2"] = 0.0

        # 2. Normalise fault sum to 100 when collision did occur
        elif collision:
            f1 = judgment.get("fault_percentage_object_1", 0)
            f2 = judgment.get("fault_percentage_object_2", 0)
            if abs(f1 + f2 - 100) > 0.5:
                logger.warning(
                    f"[{self.name}] Fault percentages don't sum to 100 — normalising",
                    extra={"f1": f1, "f2": f2},
                )
                total = f1 + f2 or 100
                judgment["fault_percentage_object_1"] = round(f1 / total * 100, 1)
                judgment["fault_percentage_object_2"] = round(f2 / total * 100, 1)

        # 3. Hard-override treaty basis with the retrieved value
        if judgment.get("treaty_basis") != treaty_basis_value:
            logger.warning(
                f"[{self.name}] Model substituted a different treaty basis — overriding",
                extra={
                    "model_value":   judgment.get("treaty_basis"),
                    "correct_value": treaty_basis_value,
                },
            )
            judgment["treaty_basis"] = treaty_basis_value

        # 4. Strip any hallucinated doctrines not in the allowed list
        allowed_set        = set(allowed_doctrine_titles)
        original_doctrines = judgment.get("applicable_doctrines", [])
        cleaned_doctrines  = [d for d in original_doctrines if d in allowed_set]
        if len(cleaned_doctrines) != len(original_doctrines):
            hallucinated = set(original_doctrines) - allowed_set
            logger.warning(
                f"[{self.name}] Removed hallucinated doctrines from judgment",
                extra={"removed": list(hallucinated)},
            )
        judgment["applicable_doctrines"] = cleaned_doctrines

        # ── Assemble final judgment ───────────────────────────────────────────
        final_judgment = {
            **judgment,
            "physical_findings": {
                "object_1":           obj1,
                "object_2":           obj2,
                "miss_distance_km":   miss_data["minimum_distance_km"],
                "collision_occurred": collision,
            },
            "legal_findings": {
                "precedents":        precedents,
                "liability_factors": liability,
            },
            "damage_estimate":        damage,
            "judgment_date":          datetime.utcnow().isoformat() + "Z",
            "adjudicating_authority": "Orbital Jurist Autonomous System v1.0",
            "prompt_version":         settings.PROMPT_VERSION,
        }

        logger.info(
            f"[{self.name}] FINAL JUDGMENT RENDERED",
            extra={
                "fault_obj1": judgment["fault_percentage_object_1"],
                "fault_obj2": judgment["fault_percentage_object_2"],
                "treaty":     judgment.get("treaty_basis"),
                "doctrines":  judgment.get("applicable_doctrines"),
            },
        )

        return {
            **state,
            "verdict_complete": True,
            "final_judgment":   final_judgment,
            "current_step":     "complete",
            "messages": state["messages"] + [
                {
                    "role":    "assistant",
                    "content": (
                        f"[LiabilityJudge] "
                        f"{judgment.get('case_summary', 'Judgment rendered')}"
                    ),
                }
            ],
        }