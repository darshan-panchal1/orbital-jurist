"""
Main FastAPI Application for The Orbital Jurist
Provides REST API for autonomous space debris liability arbitration
"""
import asyncio
import sys
import logging
import uvicorn
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import settings
from workflow.graph import OrbitalJuristWorkflow

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OrbitalJuristAPI")

def load_mcp_tools():
    """
    Load MCP server tools as Python modules
    This simulates the MCP connection by importing the tools directly
    """
    logger.info("Loading MCP Tools...")
    
    try:
        # Load orbital server tools
        logger.debug("Loading module: orbital_server")
        orbital_path = Path(__file__).parent / "mcp_servers" / "orbital_server.py"
        orbital_spec = importlib.util.spec_from_file_location("orbital_server", orbital_path)
        orbital_module = importlib.util.module_from_spec(orbital_spec)
        orbital_spec.loader.exec_module(orbital_module)
        
        # Load legal server tools
        logger.debug("Loading module: legal_server")
        legal_path = Path(__file__).parent / "mcp_servers" / "legal_server.py"
        legal_spec = importlib.util.spec_from_file_location("legal_server", legal_path)
        legal_module = importlib.util.module_from_spec(legal_spec)
        legal_spec.loader.exec_module(legal_module)
        
        # Extract tool functions
        def extract_callable(tool):
            if hasattr(tool, 'fn'):
                return tool.fn
            elif callable(tool):
                return tool
            else:
                raise ValueError(f"Cannot extract callable from {tool}")
        
        orbital_tools = {
            "get_tle_data": extract_callable(orbital_module.get_tle_data),
            "propagate_orbit": extract_callable(orbital_module.propagate_orbit),
            "calculate_miss_distance": extract_callable(orbital_module.calculate_miss_distance),
            "detect_maneuver": extract_callable(orbital_module.detect_maneuver)
        }
        
        legal_tools = {
            "search_maritime_precedents": extract_callable(legal_module.search_maritime_precedents),
            "get_liability_convention_article": extract_callable(legal_module.get_liability_convention_article),
            "analyze_liability_factors": extract_callable(legal_module.analyze_liability_factors),
            "get_all_precedents": extract_callable(legal_module.get_all_precedents),
            "calculate_damages_estimate": extract_callable(legal_module.calculate_damages_estimate)
        }
        
        logger.info(f"MCP Tools Loaded Successfully. Orbital: {len(orbital_tools)}, Legal: {len(legal_tools)}")
        return orbital_tools, legal_tools
        
    except Exception as e:
        logger.critical(f"Failed to load MCP tools: {e}")
        raise e

# Initialize FastAPI app
logger.info("Initializing FastAPI Application...")
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Autonomous arbitration system for space debris liability using orbital mechanics and maritime law"
)

# Load MCP tools
orbital_tools, legal_tools = load_mcp_tools()

# Initialize workflow
logger.info("Initializing Workflow Graph...")
workflow = OrbitalJuristWorkflow(orbital_tools, legal_tools)

# Request/Response Models
class ConjunctionAnalysisRequest(BaseModel):
    """Request model for conjunction analysis"""
    object_1_id: int = Field(..., description="NORAD catalog ID of first object", example=25544)
    object_2_id: int = Field(..., description="NORAD catalog ID of second object", example=99999)
    conjunction_time: Optional[str] = Field(
        None,
        description="ISO format datetime of conjunction (defaults to now)",
        example="2025-01-15T12:00:00Z"
    )

class JudgmentResponse(BaseModel):
    """Response model for liability judgment"""
    success: bool
    case_id: str
    judgment: Optional[dict]
    error: Optional[str]

# In-memory storage for analysis results
analysis_results = {}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming requests"""
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response Status: {response.status_code}")
    return response

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Orbital Jurist",
        "version": settings.API_VERSION,
        "description": "Autonomous Space Debris Liability Arbiter",
        "endpoints": {
            "analyze": "/api/v1/analyze",
            "status": "/api/v1/status/{case_id}",
            "precedents": "/api/v1/precedents",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "groq_configured": bool(settings.GROQ_API_KEY),
        "mcp_tools_loaded": {
            "orbital": len(orbital_tools),
            "legal": len(legal_tools)
        }
    }

@app.post("/api/v1/analyze", response_model=JudgmentResponse)
async def analyze_conjunction(request: ConjunctionAnalysisRequest, background_tasks: BackgroundTasks):
    """
    Analyze a conjunction event and render liability judgment
    """
    # Default conjunction time to now if not provided
    conjunction_time = request.conjunction_time or datetime.now(timezone.utc).isoformat()
    
    # Generate case ID
    case_id = f"OJ-{request.object_1_id}-{request.object_2_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    logger.info(f"[API] Processing New Analysis Request. CaseID: {case_id}")
    logger.debug(f"[API] Request Details: Obj1={request.object_1_id}, Obj2={request.object_2_id}, Time={conjunction_time}")
    
    try:
        # Run the workflow
        logger.info(f"[API] executing workflow for {case_id}...")
        final_state = workflow.run_sync(
            object_1_id=request.object_1_id,
            object_2_id=request.object_2_id,
            conjunction_time=conjunction_time
        )
        
        if final_state.get("error_message"):
            logger.error(f"[API] Workflow failed for {case_id}: {final_state['error_message']}")
            raise HTTPException(status_code=500, detail=final_state["error_message"])
        
        # Store result
        analysis_results[case_id] = final_state
        logger.info(f"[API] Analysis Complete. Result Stored.")
        
        return JudgmentResponse(
            success=True,
            case_id=case_id,
            judgment=final_state.get("final_judgment"),
            error=None
        )
    
    except Exception as e:
        logger.exception(f"[API] Unexpected Error during analysis for {case_id}")
        return JudgmentResponse(
            success=False,
            case_id=case_id,
            judgment=None,
            error=str(e)
        )

@app.get("/api/v1/status/{case_id}")
async def get_case_status(case_id: str):
    """
    Get the status and results of a specific case
    """
    logger.debug(f"[API] Checking status for CaseID: {case_id}")
    
    if case_id not in analysis_results:
        logger.warning(f"[API] CaseID {case_id} not found")
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    result = analysis_results[case_id]
    
    return {
        "case_id": case_id,
        "status": "complete" if result.get("verdict_complete") else "in_progress",
        "current_step": result.get("current_step"),
        "physics_complete": result.get("physics_complete", False),
        "legal_complete": result.get("legal_complete", False),
        "verdict_complete": result.get("verdict_complete", False),
        "judgment": result.get("final_judgment"),
        "error": result.get("error_message")
    }

@app.get("/api/v1/precedents")
async def list_precedents():
    """
    List all available legal precedents in the database
    """
    logger.info("[API] Fetching full precedent list")
    result = legal_tools["get_all_precedents"]()
    return result

@app.post("/api/v1/tle/{norad_id}")
async def get_tle(norad_id: int):
    """
    Fetch TLE data for a specific satellite
    """
    logger.info(f"[API] Fetching TLE for {norad_id}")
    try:
        result = orbital_tools["get_tle_data"](norad_id=norad_id)
        if not result.get("success"):
            logger.warning(f"[API] TLE not found for {norad_id}")
            raise HTTPException(status_code=404, detail=result.get("error", "TLE not found"))
        return result
    except Exception as e:
        logger.error(f"[API] Error fetching TLE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/propagate")
async def propagate_satellite(norad_id: int, target_time: str):
    """
    Propagate a satellite's orbit to a specific time
    """
    logger.info(f"[API] Propagating orbit for {norad_id} to {target_time}")
    try:
        result = orbital_tools["propagate_orbit"](
            norad_id=norad_id,
            target_time=target_time
        )
        if not result.get("success"):
            logger.error(f"[API] Propagation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Propagation failed"))
        return result
    except Exception as e:
        logger.error(f"[API] Exception during propagation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.critical(f"Global Exception caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )

def main():
    """Main entry point"""
    logger.info("Starting Orbital Jurist Server...")
    print(f"""
{'='*80}
ORBITAL JURIST - AUTONOMOUS SPACE DEBRIS LIABILITY ARBITER
{'='*80}
Version: {settings.API_VERSION}
API Server: http://{settings.API_HOST}:{settings.API_PORT}
Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs
{'='*80}

MCP Tools Loaded:
  Orbital Mechanics: {len(orbital_tools)} tools
  Legal Database: {len(legal_tools)} tools

Groq API: {'✓ Configured' if settings.GROQ_API_KEY else '✗ NOT CONFIGURED'}
{'='*80}
""")
    
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="warning" # Suppress uvicorn's default logs in favor of ours, or set to 'info'
    )

if __name__ == "__main__":
    main()