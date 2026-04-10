"""
LangGraph Workflow for Orbital Jurist System
Orchestrates the multi-agent liability analysis pipeline — fully async via ainvoke.

Flow:
    physics_forensic
        │
        ├─ error        → END
        ├─ no_risk      → no_risk_verdict → END   (miss dist > CONJUNCTION_RISK_THRESHOLD_KM)
        └─ continue     → maritime_scholar
                              │
                              ├─ error    → END
                              └─ continue → liability_judge → END
"""
import uuid
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from agents.orbital_agents import (
    LiabilityJudgeAgent,
    MaritimeScholarAgent,
    NoRiskVerdictAgent,
    PhysicsForensicAgent,
)
from config import settings
from utils.logging_config import get_logger, set_context
from workflow.state import OrbitalJuristState

logger = get_logger("workflow")


class OrbitalJuristWorkflow:
    """
    Main workflow orchestrator for the Orbital Jurist system
    """

    def __init__(self, orbital_tools: Dict[str, Any], legal_tools: Dict[str, Any]):
        """
        Initialize workflow with MCP tools
        """
        logger.info("Initializing OrbitalJuristWorkflow...")
        self.orbital_tools   = orbital_tools
        self.legal_tools     = legal_tools

        # Initialize agents
        logger.debug("Initializing Agents...")
        self.physics_agent   = PhysicsForensicAgent()
        self.scholar_agent   = MaritimeScholarAgent()
        self.judge_agent     = LiabilityJudgeAgent()
        self.no_risk_agent   = NoRiskVerdictAgent()

        # Build the workflow graph
        logger.debug("Building StateGraph...")
        self.graph = self._build_graph()
        logger.info("Workflow Graph compiled successfully.")

    # ── Graph construction ───────────────────────────────────────────────────

    def _build_graph(self):
        """
        Build the LangGraph workflow
        """
        workflow = StateGraph(OrbitalJuristState)

        # Nodes
        workflow.add_node("physics_forensic", self._physics_node)
        workflow.add_node("no_risk_verdict",  self._no_risk_node)
        workflow.add_node("maritime_scholar",  self._legal_node)
        workflow.add_node("liability_judge",   self._judge_node)

        # Entry point
        workflow.set_entry_point("physics_forensic")

        # physics → {error, no_risk, continue}
        workflow.add_conditional_edges(
            "physics_forensic",
            self._route_after_physics,
            {
                "error":    END,
                "no_risk":  "no_risk_verdict",
                "continue": "maritime_scholar",
            },
        )

        # no_risk → END  (deterministic verdict, no further agents needed)
        workflow.add_edge("no_risk_verdict", END)

        # maritime_scholar → {error, continue}
        workflow.add_conditional_edges(
            "maritime_scholar",
            lambda s: (
                "continue"
                if s.get("legal_complete") and not s.get("error_message")
                else "error"
            ),
            {"continue": "liability_judge", "error": END},
        )

        # liability_judge → END
        workflow.add_edge("liability_judge", END)

        return workflow.compile()

    # ── Routing ──────────────────────────────────────────────────────────────

    def _route_after_physics(self, state: OrbitalJuristState) -> str:
        """
        Three-way routing after physics analysis:
          error    — physics failed (TLE fetch error, propagation error, etc.)
          no_risk  — miss distance is above CONJUNCTION_RISK_THRESHOLD_KM
                     → deterministic no-liability verdict, skip LLM legal agents
          continue — miss distance is within the threshold, proceed to legal analysis
        """
        if state.get("error_message") or not state.get("physics_complete"):
            logger.error("Routing → error (physics incomplete or errored)")
            return "error"

        miss_data = state.get("miss_distance_data") or {}
        min_dist  = miss_data.get("minimum_distance_km", float("inf"))

        if min_dist > settings.CONJUNCTION_RISK_THRESHOLD_KM:
            logger.info(
                "Routing → no_risk (miss distance exceeds operational threshold)",
                extra={
                    "min_dist_km":  round(min_dist, 1),
                    "threshold_km": settings.CONJUNCTION_RISK_THRESHOLD_KM,
                },
            )
            return "no_risk"

        logger.info(
            "Routing → continue (conjunction risk confirmed — proceeding to legal)",
            extra={"min_dist_km": round(min_dist, 3)},
        )
        return "continue"

    # ── Nodes ────────────────────────────────────────────────────────────────

    def _physics_node(self, state: OrbitalJuristState) -> OrbitalJuristState:
        """Execute physics forensic analysis"""
        set_context(
            case_id=state.get("case_id", "-"),
            trace_id=state.get("trace_id", "-"),
        )
        logger.info("NODE physics_forensic started")
        return self.physics_agent.analyze(state, self.orbital_tools)

    def _no_risk_node(self, state: OrbitalJuristState) -> OrbitalJuristState:
        """Render deterministic no-conjunction-risk verdict (no LLM calls)"""
        set_context(
            case_id=state.get("case_id", "-"),
            trace_id=state.get("trace_id", "-"),
        )
        logger.info("NODE no_risk_verdict started")
        return self.no_risk_agent.render(state)

    def _legal_node(self, state: OrbitalJuristState) -> OrbitalJuristState:
        """Execute legal analysis"""
        set_context(
            case_id=state.get("case_id", "-"),
            trace_id=state.get("trace_id", "-"),
        )
        logger.info("NODE maritime_scholar started")
        return self.scholar_agent.analyze(state, self.legal_tools)

    def _judge_node(self, state: OrbitalJuristState) -> OrbitalJuristState:
        """Execute final adjudication"""
        set_context(
            case_id=state.get("case_id", "-"),
            trace_id=state.get("trace_id", "-"),
        )
        logger.info("NODE liability_judge started")
        return self.judge_agent.adjudicate(state, self.legal_tools)

    # ── Public entry point ───────────────────────────────────────────────────

    async def run(
        self,
        object_1_id:      int,
        object_2_id:      int,
        conjunction_time: str,
        case_id:          str = None,
        trace_id:         str = None,
    ) -> Dict[str, Any]:
        """
        Run the complete orbital jurist workflow (async)
        """
        case_id  = case_id  or f"OJ-{object_1_id}-{object_2_id}-{uuid.uuid4().hex[:8]}"
        trace_id = trace_id or uuid.uuid4().hex

        set_context(case_id=case_id, trace_id=trace_id)
        logger.info(
            "Workflow started",
            extra={"case_id": case_id, "obj1": object_1_id, "obj2": object_2_id},
        )

        initial_state: OrbitalJuristState = {
            "case_id":               case_id,
            "trace_id":              trace_id,
            "object_1_id":           object_1_id,
            "object_2_id":           object_2_id,
            "conjunction_time":      conjunction_time,
            "physics_complete":      False,
            "object_1_data":         None,
            "object_2_data":         None,
            "miss_distance_data":    None,
            "maneuver_analysis":     None,
            "legal_complete":        False,
            "applicable_precedents": None,
            "treaty_articles":       None,
            "liability_factors":     None,
            "verdict_complete":      False,
            "final_judgment":        None,
            "current_step":          "initialization",
            "error_message":         None,
            "requires_revision":     False,
            "messages": [
                {
                    "role":    "system",
                    "content": (
                        f"Case {case_id}: analyzing conjunction between "
                        f"NORAD {object_1_id} and {object_2_id} at {conjunction_time}"
                    ),
                }
            ],
        }

        try:
            final_state = await self.graph.ainvoke(initial_state)
            logger.info(
                "Workflow complete",
                extra={
                    "case_id": case_id,
                    "verdict": final_state.get("verdict_complete"),
                    "path":    final_state.get("current_step"),
                },
            )
            return final_state
        except Exception as e:
            logger.critical("Workflow execution failed",
                            extra={"case_id": case_id, "error": str(e)})
            raise e

    def run_sync(
        self,
        object_1_id:      int,
        object_2_id:      int,
        conjunction_time: str,
        case_id:          str = None,
        trace_id:         str = None,
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper — use from CLI only.
        FastAPI must always use the async run() to avoid blocking the event loop.
        """
        import asyncio
        return asyncio.run(
            self.run(
                object_1_id=object_1_id,
                object_2_id=object_2_id,
                conjunction_time=conjunction_time,
                case_id=case_id,
                trace_id=trace_id,
            )
        )