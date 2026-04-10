"""
Single source of truth for MCP tool loading.
Both main.py (API) and run_analysis.py (CLI) import from here.
"""
import importlib.util
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from utils.logging_config import get_logger

logger = get_logger("tool_registry")

_ORBITAL_TOOL_NAMES = (
    "get_tle_data",
    "propagate_orbit",
    "calculate_miss_distance",
    "detect_maneuver",
)
_LEGAL_TOOL_NAMES = (
    "search_maritime_precedents",
    "get_liability_convention_article",
    "analyze_liability_factors",
    "get_all_precedents",
    "calculate_damages_estimate",
)

_MCP_DIR = Path(__file__).parent


def _load_module(name: str, path: Path):
    spec   = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_callable(obj: Any, name: str) -> Callable:
    """
    Extract the underlying callable from a FastMCP FunctionTool.
    FastMCP stores the original function in .fn. If the attribute is absent
    the object itself must be callable (plain function or partial).
    """
    fn = getattr(obj, "fn", None)
    if fn is not None and callable(fn):
        return fn
    if callable(obj):
        return obj
    raise TypeError(
        f"Cannot extract callable for tool '{name}' "
        f"(type: {type(obj).__name__}). "
        "Ensure FastMCP FunctionTool exposes a '.fn' attribute."
    )


def load_tools() -> Tuple[Dict[str, Callable], Dict[str, Callable]]:
    """
    Load and return (orbital_tools, legal_tools) as plain callable dicts.
    Raises on import error or missing tool name.
    """
    logger.info("Loading MCP tool modules...")

    orbital_mod = _load_module("orbital_server", _MCP_DIR / "orbital_server.py")
    legal_mod   = _load_module("legal_server",   _MCP_DIR / "legal_server.py")

    orbital_tools: Dict[str, Callable] = {}
    for name in _ORBITAL_TOOL_NAMES:
        obj = getattr(orbital_mod, name, None)
        if obj is None:
            raise AttributeError(f"orbital_server is missing tool '{name}'")
        orbital_tools[name] = _extract_callable(obj, name)

    legal_tools: Dict[str, Callable] = {}
    for name in _LEGAL_TOOL_NAMES:
        obj = getattr(legal_mod, name, None)
        if obj is None:
            raise AttributeError(f"legal_server is missing tool '{name}'")
        legal_tools[name] = _extract_callable(obj, name)

    logger.info(
        "MCP tools loaded",
        extra={"orbital": len(orbital_tools), "legal": len(legal_tools)},
    )
    return orbital_tools, legal_tools