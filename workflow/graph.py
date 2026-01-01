"""
LangGraph Workflow for Orbital Jurist System
Orchestrates the multi-agent liability analysis pipeline
"""
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from workflow.state import OrbitalJuristState
from agents.orbital_agents import (
    PhysicsForensicAgent,
    MaritimeScholarAgent,
    LiabilityJudgeAgent
)

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Workflow")

class OrbitalJuristWorkflow:
    """
    Main workflow orchestrator for the Orbital Jurist system
    """
    
    def __init__(self, orbital_tools: Dict[str, Any], legal_tools: Dict[str, Any]):
        """
        Initialize workflow with MCP tools
        """
        logger.info("Initializing OrbitalJuristWorkflow...")
        self.orbital_tools = orbital_tools
        self.legal_tools = legal_tools
        
        # Initialize agents
        logger.debug("Initializing Agents...")
        self.physics_agent = PhysicsForensicAgent()
        self.scholar_agent = MaritimeScholarAgent()
        self.judge_agent = LiabilityJudgeAgent()
        
        # Build the workflow graph
        logger.debug("Building StateGraph...")
        self.graph = self._build_graph()
        logger.info("Workflow Graph compiled successfully.")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow
        """
        workflow = StateGraph(OrbitalJuristState)
        
        # Add nodes for each agent
        workflow.add_node("physics_forensic", self._physics_node)
        workflow.add_node("maritime_scholar", self._legal_node)
        workflow.add_node("liability_judge", self._judge_node)
        
        # Define the flow
        workflow.set_entry_point("physics_forensic")
        
        # Physics -> Legal (if physics successful)
        workflow.add_conditional_edges(
            "physics_forensic",
            self._check_physics_complete,
            {
                "continue": "maritime_scholar",
                "error": END
            }
        )
        
        # Legal -> Judge (if legal successful)
        workflow.add_conditional_edges(
            "maritime_scholar",
            self._check_legal_complete,
            {
                "continue": "liability_judge",
                "error": END
            }
        )
        
        # Judge -> End
        workflow.add_edge("liability_judge", END)
        
        return workflow.compile()
    
    def _physics_node(self, state: OrbitalJuristState) -> OrbitalJuristState:
        """Execute physics forensic analysis"""
        logger.info(">>> NODE: Physics Forensic Agent Started")
        return self.physics_agent.analyze(state, self.orbital_tools)
    
    def _legal_node(self, state: OrbitalJuristState) -> OrbitalJuristState:
        """Execute legal analysis"""
        logger.info(">>> NODE: Maritime Scholar Agent Started")
        return self.scholar_agent.analyze(state, self.legal_tools)
    
    def _judge_node(self, state: OrbitalJuristState) -> OrbitalJuristState:
        """Execute final adjudication"""
        logger.info(">>> NODE: Liability Judge Agent Started")
        return self.judge_agent.adjudicate(state, self.legal_tools)
    
    def _check_physics_complete(self, state: OrbitalJuristState) -> str:
        """Check if physics analysis completed successfully"""
        logger.debug("Checking Physics Completion Status...")
        if state.get("error_message"):
            logger.error(f"Physics Error Detected: {state.get('error_message')}")
            return "error"
        if state.get("physics_complete"):
            logger.info("Physics Analysis Complete -> Proceeding to Legal Analysis")
            return "continue"
        logger.warning("Physics Incomplete (Unknown State) -> Terminating")
        return "error"
    
    def _check_legal_complete(self, state: OrbitalJuristState) -> str:
        """Check if legal analysis completed successfully"""
        logger.debug("Checking Legal Completion Status...")
        if state.get("error_message"):
            logger.error(f"Legal Error Detected: {state.get('error_message')}")
            return "error"
        if state.get("legal_complete"):
            logger.info("Legal Analysis Complete -> Proceeding to Adjudication")
            return "continue"
        logger.warning("Legal Incomplete (Unknown State) -> Terminating")
        return "error"
    
    async def run(
        self,
        object_1_id: int,
        object_2_id: int,
        conjunction_time: str
    ) -> Dict[str, Any]:
        """
        Run the complete orbital jurist workflow
        """
        # Initialize state
        initial_state: OrbitalJuristState = {
            "object_1_id": object_1_id,
            "object_2_id": object_2_id,
            "conjunction_time": conjunction_time,
            "physics_complete": False,
            "object_1_data": None,
            "object_2_data": None,
            "miss_distance_data": None,
            "maneuver_analysis": None,
            "legal_complete": False,
            "applicable_precedents": None,
            "treaty_articles": None,
            "liability_factors": None,
            "verdict_complete": False,
            "final_judgment": None,
            "current_step": "initialization",
            "error_message": None,
            "requires_revision": False,
            "messages": [
                {
                    "role": "system",
                    "content": f"Analyzing conjunction between NORAD {object_1_id} and {object_2_id} at {conjunction_time}"
                }
            ]
        }
        
        logger.info("="*60)
        logger.info("ORBITAL JURIST - AUTONOMOUS SPACE DEBRIS LIABILITY ARBITER")
        logger.info("="*60)
        logger.info(f"STARTING WORKFLOW: NORAD {object_1_id} vs {object_2_id}")
        logger.info(f"Target Conjunction Time: {conjunction_time}")
        
        # Execute workflow
        try:
            final_state = await self.graph.ainvoke(initial_state)
            logger.info("Workflow Execution Finished Successfully.")
            return final_state
        except Exception as e:
            logger.critical(f"Workflow Execution Failed: {e}")
            raise e
    
    def run_sync(
        self,
        object_1_id: int,
        object_2_id: int,
        conjunction_time: str
    ) -> Dict[str, Any]:
        """
        Synchronous version of run()
        """
        # Initialize state
        initial_state: OrbitalJuristState = {
            "object_1_id": object_1_id,
            "object_2_id": object_2_id,
            "conjunction_time": conjunction_time,
            "physics_complete": False,
            "object_1_data": None,
            "object_2_data": None,
            "miss_distance_data": None,
            "maneuver_analysis": None,
            "legal_complete": False,
            "applicable_precedents": None,
            "treaty_articles": None,
            "liability_factors": None,
            "verdict_complete": False,
            "final_judgment": None,
            "current_step": "initialization",
            "error_message": None,
            "requires_revision": False,
            "messages": [
                {
                    "role": "system",
                    "content": f"Analyzing conjunction between NORAD {object_1_id} and {object_2_id} at {conjunction_time}"
                }
            ]
        }
        
        logger.info("="*60)
        logger.info("ORBITAL JURIST - AUTONOMOUS SPACE DEBRIS LIABILITY ARBITER (SYNC)")
        logger.info("="*60)
        logger.info(f"STARTING WORKFLOW: NORAD {object_1_id} vs {object_2_id}")
        
        # Execute workflow synchronously
        try:
            final_state = self.graph.invoke(initial_state)
            logger.info("Workflow Execution (Sync) Finished Successfully.")
            return final_state
        except Exception as e:
            logger.critical(f"Workflow Execution (Sync) Failed: {e}")
            raise e