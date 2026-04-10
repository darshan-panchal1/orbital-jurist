"""
State definitions for the Orbital Jurist workflow
"""
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import add_messages


class OrbitalJuristState(TypedDict):
    """State for the multi-agent orbital liability workflow"""

    # ── Tracing ──────────────────────────────────────────────────────────────
    case_id:  str
    trace_id: str

    # ── Input parameters ─────────────────────────────────────────────────────
    object_1_id:      int
    object_2_id:      int
    conjunction_time: str

    # ── Physics analysis results ─────────────────────────────────────────────
    physics_complete:  bool
    object_1_data:     Optional[Dict[str, Any]]
    object_2_data:     Optional[Dict[str, Any]]
    miss_distance_data: Optional[Dict[str, Any]]
    maneuver_analysis: Optional[Dict[str, Any]]

    # ── Legal analysis results ────────────────────────────────────────────────
    legal_complete:        bool
    applicable_precedents: Optional[List[Dict[str, Any]]]
    treaty_articles:       Optional[List[Dict[str, Any]]]
    liability_factors:     Optional[Dict[str, Any]]

    # ── Final verdict ─────────────────────────────────────────────────────────
    verdict_complete: bool
    final_judgment:   Optional[Dict[str, Any]]

    # ── Workflow control ──────────────────────────────────────────────────────
    current_step:     str
    error_message:    Optional[str]
    requires_revision: bool

    # ── Message history for agents ────────────────────────────────────────────
    messages: Annotated[List[Dict[str, str]], add_messages]


class PhysicsAnalysisOutput(TypedDict):
    """Structured output from physics forensic analysis"""
    object_1_status:     str   # ACTIVE, DRIFTING, UNCERTAIN
    object_2_status:     str
    minimum_distance_km: float
    relative_speed_m_s:  float
    collision_occurred:  bool
    collision_type:      str   # head-on, chasing, crossing
    object_1_maneuvered: bool
    object_2_maneuvered: bool
    warning_possible:    bool  # Was conjunction predictable?


class LegalAnalysisOutput(TypedDict):
    """Structured output from maritime scholar analysis"""
    primary_doctrine:      str
    supporting_precedents: List[str]
    treaty_article:        str
    liability_theory:      str
    mitigating_factors:    List[str]
    aggravating_factors:   List[str]


class LiabilityJudgment(TypedDict):
    """Final judgment structure"""
    case_summary:              str
    physical_findings:         Dict[str, Any]
    legal_findings:            Dict[str, Any]
    fault_percentage_object_1: float
    fault_percentage_object_2: float
    primary_reasoning:         str
    applicable_doctrines:      List[str]
    treaty_basis:              str
    damage_estimate:           Optional[Dict[str, Any]]
    recommendations:           List[str]
    dissenting_opinion:        Optional[str]