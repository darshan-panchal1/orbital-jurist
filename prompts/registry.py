"""
Versioned, parameterized prompt templates.
Agents import get_prompt(name) — never hardcode strings in agent methods.
"""
from typing import Any, Dict

from config import settings

# Each key is "<version>/<prompt_name>".
# Add new versions without modifying agent code.
_REGISTRY: Dict[str, str] = {

    # ── PhysicsForensic ──────────────────────────────────────────────────────
    "v1/physics_system": (
        "You are an expert in orbital mechanics and space situational awareness. "
        "Provide factual, technical analysis. Be concise and precise. "
        "Never speculate beyond what the data supports."
    ),
    "v1/physics_summary": (
        "As a Physics Forensic Expert, synthesize the following orbital conjunction data.\n"
        "\n"
        "OBJECT 1: {obj1_name} (NORAD {obj1_id})\n"
        "  Status            : {obj1_status}\n"
        "  Classification    : {obj1_confidence} confidence ({obj1_method})\n"
        "  Position at TCA   : {obj1_position}\n"
        "  Velocity at TCA   : {obj1_velocity}\n"
        "\n"
        "OBJECT 2: {obj2_name} (NORAD {obj2_id})\n"
        "  Status            : {obj2_status}\n"
        "  Classification    : {obj2_confidence} confidence ({obj2_method})\n"
        "  Position at TCA   : {obj2_position}\n"
        "  Velocity at TCA   : {obj2_velocity}\n"
        "\n"
        "CONJUNCTION:\n"
        "  Time of Closest Approach : {tca_time}\n"
        "  Minimum Distance         : {min_distance_km:.3f} km  (threshold: {threshold_km} km)\n"
        "  Relative Speed           : {rel_speed_ms:.1f} m/s\n"
        "  Collision Type           : {collision_type}\n"
        "  Collision Occurred       : {collision_occurred}\n"
        "  Status Confidence Note   : {confidence_note}\n"
        "\n"
        "Write a concise technical summary (3-4 sentences) covering:\n"
        "1. Objective facts of the event\n"
        "2. Control capability of each object (noting any classification uncertainty)\n"
        "3. Whether the conjunction was avoidable by either party\n"
    ),

    # ── MaritimeScholar ──────────────────────────────────────────────────────
    "v1/scholar_system": (
        "You are an expert in maritime law and the 1972 Liability Convention for outer space. "
        "Apply legal reasoning analogically from maritime to orbital contexts. "
        "Be precise about which doctrine applies and why."
    ),
    "v1/scholar_opinion": (
        "As a Maritime Law Scholar specializing in space law, analyze this case:\n"
        "\n"
        "PHYSICAL FACTS:\n"
        "  Object 1 ({obj1_name}): {obj1_status}\n"
        "  Object 2 ({obj2_name}): {obj2_status}\n"
        "  Minimum Distance   : {min_distance_km:.3f} km\n"
        "  Collision Type     : {collision_type}\n"
        "\n"
        "APPLICABLE PRECEDENTS:\n"
        "{precedents_json}\n"
        "\n"
        "TREATY BASIS:\n"
        "{treaty_text}\n"
        "\n"
        "LIABILITY ANALYSIS:\n"
        "{liability_json}\n"
        "\n"
        "Provide a legal opinion (3-4 sentences) addressing:\n"
        "1. Which doctrines apply and why\n"
        "2. How maritime precedents inform this orbital case\n"
        "3. The legal basis for liability assignment\n"
    ),

    # ── LiabilityJudge ───────────────────────────────────────────────────────
    "v1/judge_system": (
        "You are a Judge specializing in space law and orbital liability. "
        "Render fair, evidence-based judgments. "
        "Output ONLY valid JSON — no preamble, no markdown fences."
    ),

    # ── NoRisk (deterministic — no LLM call) ─────────────────────────────────
    # Used as a human-readable case_summary when miss distance is above the
    # conjunction risk threshold.  Substituted directly into the state dict.
    "v1/no_risk_summary": (
        "No conjunction risk detected. {obj1_name} and {obj2_name} passed at a "
        "minimum distance of {min_distance_km:.1f} km — "
        "{times_threshold:.0f}x the {threshold_km} km operational conjunction "
        "warning threshold. No damage occurred and no liability exists under "
        "Article III of the 1972 Liability Convention, which requires proof of "
        "fault and actual damage. Case dismissed."
    ),
    "v1/judge_judgment": (
        "As the Liability Judge in this orbital arbitration, render a binding judgment.\n"
        "\n"
        "CASE: {obj1_name} (NORAD {obj1_id}) vs {obj2_name} (NORAD {obj2_id})\n"
        "\n"
        "PHYSICAL EVIDENCE:\n"
        "  Object 1 Status  : {obj1_status} (confidence: {obj1_confidence})\n"
        "  Object 2 Status  : {obj2_status} (confidence: {obj2_confidence})\n"
        "  Minimum Distance : {min_distance_km:.3f} km\n"
        "  Relative Speed   : {rel_speed_ms:.1f} m/s\n"
        "  Collision Type   : {collision_type}\n"
        "  Collision        : {collision_occurred}\n"
        "\n"
        "APPLICABLE LAW — USE ONLY THESE DOCTRINES, NO OTHERS:\n"
        "{doctrines_json}\n"
        "\n"
        "LIABILITY FACTORS:\n"
        "  Suggested Split : {suggested_split}\n"
        "  Reasoning       : {factor_reasoning}\n"
        "\n"
        "DAMAGE ASSESSMENT:\n"
        "{damage_json}\n"
        "\n"
        "MANDATORY RULES — violating any rule is a critical error:\n"
        "  RULE 1: treaty_basis MUST be exactly: \"{treaty_basis_value}\" — copy verbatim, no substitution.\n"
        "  RULE 2: applicable_doctrines MUST only contain items from the APPLICABLE LAW list above.\n"
        "          Do NOT add any doctrine not present in that list.\n"
        "  RULE 3: If collision is False, fault_percentage_object_1 = 0 and fault_percentage_object_2 = 0.\n"
        "          Do not assign fault when no damage occurred.\n"
        "  RULE 4: fault_percentage_object_1 + fault_percentage_object_2 MUST equal 100 when collision is True,\n"
        "          and both MUST equal 0 when collision is False.\n"
        "\n"
        "Respond ONLY with JSON matching this schema exactly:\n"
        "{{\n"
        '  "case_summary"              : "<2-3 sentence summary>",\n'
        '  "fault_percentage_object_1" : <number>,\n'
        '  "fault_percentage_object_2" : <number>,\n'
        '  "primary_reasoning"         : "<main legal reasoning>",\n'
        '  "applicable_doctrines"      : ["<only items from APPLICABLE LAW list>"],\n'
        '  "treaty_basis"              : "<copy RULE 1 value verbatim>",\n'
        '  "recommendations"           : ["<rec1>", ...]\n'
        "}}\n"
    ),
}


def get_prompt(name: str, version: str = None, **kwargs: Any) -> str:
    """
    Retrieve and render a prompt template.

    Parameters
    ----------
    name    : Prompt key without version prefix, e.g. "physics_summary"
    version : Override the global PROMPT_VERSION from config
    **kwargs: Template substitution variables
    """
    v   = version or settings.PROMPT_VERSION
    key = f"{v}/{name}"
    if key not in _REGISTRY:
        raise KeyError(
            f"Prompt '{key}' not found. "
            f"Available: {[k for k in _REGISTRY if k.startswith(v + '/')]}"
        )
    template = _REGISTRY[key]
    if kwargs:
        return template.format(**kwargs)
    return template