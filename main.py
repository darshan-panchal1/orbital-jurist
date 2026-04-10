"""
Production FastAPI Application for The Orbital Jurist
Provides REST API for autonomous space debris liability arbitration
"""
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from mcp_servers.registry import load_tools
from utils.logging_config import get_logger, new_request_id, set_context
from utils.resilience import all_circuit_breaker_statuses
from workflow.graph import OrbitalJuristWorkflow

logger = get_logger("api")

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)

# ── Optional API key auth ─────────────────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: Optional[str] = Security(_api_key_header)) -> None:
    """No-op when INTERNAL_API_KEY is unset; enforces key when set."""
    if settings.INTERNAL_API_KEY and key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


# ── TTL-aware in-memory results store ─────────────────────────────────────────
class _ResultsStore:
    def __init__(self, ttl: int = settings.RESULTS_TTL_SECONDS):
        self._store: dict = {}
        self._ttl   = ttl

    def put(self, key: str, value: dict) -> None:
        self._store[key] = {"data": value, "ts": time.monotonic()}

    def get(self, key: str) -> Optional[dict]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry["ts"] > self._ttl:
            del self._store[key]
            return None
        return entry["data"]

    def evict_expired(self) -> int:
        cutoff  = time.monotonic() - self._ttl
        expired = [k for k, v in self._store.items() if v["ts"] < cutoff]
        for k in expired:
            del self._store[k]
        return len(expired)


_results = _ResultsStore()

# ── Application lifecycle ──────────────────────────────────────────────────────
_workflow: Optional[OrbitalJuristWorkflow] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _workflow
    logger.info("Startup — loading MCP tools")
    orbital_tools, legal_tools = load_tools()
    _workflow = OrbitalJuristWorkflow(orbital_tools, legal_tools)
    logger.info("Startup complete")
    yield
    logger.info("Shutdown")


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Autonomous arbitration system for space debris liability using orbital mechanics and maritime law",
    lifespan=lifespan,
)

# ── CORS Configuration ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Note: Change to your specific frontend domains in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Request context middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    rid = new_request_id()
    set_context(
        request_id=rid,
        trace_id=request.headers.get("X-Trace-Id", rid),
    )
    request.state.request_id = rid
    t0       = time.monotonic()
    response = await call_next(request)
    elapsed  = round((time.monotonic() - t0) * 1000, 1)
    response.headers["X-Request-Id"] = rid
    logger.info(
        "HTTP",
        extra={
            "method": request.method,
            "path":   request.url.path,
            "status": response.status_code,
            "ms":     elapsed,
        },
    )
    return response


# ── Request/Response Models ────────────────────────────────────────────────────
class ConjunctionAnalysisRequest(BaseModel):
    """Request model for conjunction analysis"""
    object_1_id: int = Field(
        ..., ge=1, le=90000,
        description="NORAD catalog ID of first object",
        json_schema_extra={"example": 25544},
    )
    object_2_id: int = Field(
        ..., ge=1, le=90000,
        description="NORAD catalog ID of second object",
        json_schema_extra={"example": 43013},
    )
    conjunction_time: Optional[str] = Field(
        None,
        description="ISO format datetime of conjunction (defaults to now)",
        json_schema_extra={"example": "2025-01-15T12:00:00Z"}
    )

    @field_validator("conjunction_time")
    @classmethod
    def validate_iso_time(cls, v):
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(
                "conjunction_time must be ISO-8601 (e.g. 2025-06-15T12:00:00Z)"
            )
        return v

    @field_validator("object_2_id")
    @classmethod
    def different_objects(cls, v, info):
        if info.data.get("object_1_id") == v:
            raise ValueError("object_1_id and object_2_id must differ")
        return v


class JudgmentResponse(BaseModel):
    """Response model for liability judgment"""
    success:  bool
    case_id:  str
    judgment: Optional[dict] = None
    error:    Optional[str]  = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service":  "Orbital Jurist",
        "version":  settings.API_VERSION,
        "description": "Autonomous Space Debris Liability Arbiter",
        "endpoints": {
            "analyze":    "POST /api/v1/analyze",
            "status":     "GET  /api/v1/status/{case_id}",
            "precedents": "GET  /api/v1/precedents",
            "health":     "GET  /health",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status":           "healthy",
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "groq_configured":  bool(settings.GROQ_API_KEY),
        "circuit_breakers": all_circuit_breaker_statuses(),
        "mcp_tools_loaded": _workflow is not None,
    }


@app.post(
    "/api/v1/analyze",
    response_model=JudgmentResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.RATE_LIMIT_ANALYZE)
async def analyze_conjunction(
    request: Request,
    body:    ConjunctionAnalysisRequest,
):
    """
    Analyze a conjunction event and render liability judgment
    """
    if _workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not initialised")

    conjunction_time = body.conjunction_time or datetime.now(timezone.utc).isoformat()
    case_id  = f"OJ-{body.object_1_id}-{body.object_2_id}-{uuid.uuid4().hex[:8]}"
    trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex)

    set_context(case_id=case_id, trace_id=trace_id)
    logger.info(
        "Analysis request received",
        extra={"obj1": body.object_1_id, "obj2": body.object_2_id, "case_id": case_id},
    )

    try:
        final = await _workflow.run(
            object_1_id=body.object_1_id,
            object_2_id=body.object_2_id,
            conjunction_time=conjunction_time,
            case_id=case_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.exception("Workflow error", extra={"error": str(exc)})
        return JudgmentResponse(success=False, case_id=case_id, error=str(exc))

    if final.get("error_message"):
        return JudgmentResponse(
            success=False,
            case_id=case_id,
            error=final["error_message"],
        )

    _results.put(case_id, final)
    logger.info("Analysis complete", extra={"case_id": case_id})

    return JudgmentResponse(
        success=True,
        case_id=case_id,
        judgment=final.get("final_judgment"),
    )


@app.get(
    "/api/v1/status/{case_id}",
    dependencies=[Depends(verify_api_key)],
)
async def get_case_status(case_id: str):
    """
    Get the status and results of a specific case
    """
    logger.debug("Status check", extra={"case_id": case_id})

    result = _results.get(case_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_id!r} not found or expired",
        )

    return {
        "case_id":          case_id,
        "status":           "complete" if result.get("verdict_complete") else "in_progress",
        "current_step":     result.get("current_step"),
        "physics_complete": result.get("physics_complete", False),
        "legal_complete":   result.get("legal_complete",   False),
        "verdict_complete": result.get("verdict_complete", False),
        "judgment":         result.get("final_judgment"),
        "error":            result.get("error_message"),
    }


@app.get(
    "/api/v1/precedents",
    dependencies=[Depends(verify_api_key)],
)
async def list_precedents():
    """
    List all available legal precedents in the database
    """
    logger.info("Fetching full precedent list")
    if _workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not initialised")
    return _workflow.legal_tools["get_all_precedents"]()


@app.post(
    "/api/v1/tle/{norad_id}",
    dependencies=[Depends(verify_api_key)],
)
async def get_tle(norad_id: int):
    """
    Fetch TLE data for a specific satellite
    """
    logger.info("TLE fetch requested", extra={"norad_id": norad_id})
    if _workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not initialised")
    try:
        result = _workflow.orbital_tools["get_tle_data"](norad_id=norad_id)
        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "TLE not found"),
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("TLE fetch error", extra={"norad_id": norad_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/propagate",
    dependencies=[Depends(verify_api_key)],
)
async def propagate_satellite(norad_id: int, target_time: str):
    """
    Propagate a satellite's orbit to a specific time
    """
    logger.info("Propagation requested",
                extra={"norad_id": norad_id, "target_time": target_time})
    if _workflow is None:
        raise HTTPException(status_code=503, detail="Workflow not initialised")
    try:
        result = _workflow.orbital_tools["propagate_orbit"](
            norad_id=norad_id,
            target_time=target_time,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Propagation failed"),
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Propagation error",
                     extra={"norad_id": norad_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/admin/evict",
    include_in_schema=False,
    dependencies=[Depends(verify_api_key)],
)
async def manual_evict():
    """Manually evict expired results from the in-memory store"""
    n = _results.evict_expired()
    return {"evicted": n}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error("Unhandled exception", extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
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
Groq API: {'Configured' if settings.GROQ_API_KEY else 'NOT CONFIGURED'}
Auth:     {'Enabled (X-API-Key)' if settings.INTERNAL_API_KEY else 'Disabled'}
{'='*80}
""")

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_config=None,   # suppress uvicorn's default logging — we own the root logger
        workers=1,         # LangGraph graph state is in-process; use 1 worker
    )


if __name__ == "__main__":
    main()