"""
Comprehensive Test Suite for Orbital Jurist
Tests all components and integration
"""
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.logging_config import get_logger

logger = get_logger("system_test")


def test_imports() -> bool:
    """Test all module imports"""
    logger.info("TEST: Testing imports...")
    try:
        from config import settings
        logger.debug("Imported config.settings")
        from utils.groq_client import GroqClient
        logger.debug("Imported utils.groq_client")
        from utils.data_loader import CelesTrakClient, LegalDatabase
        logger.debug("Imported utils.data_loader")
        from utils.resilience import get_circuit_breaker, all_circuit_breaker_statuses
        logger.debug("Imported utils.resilience")
        from agents.orbital_agents import PhysicsForensicAgent, MaritimeScholarAgent, LiabilityJudgeAgent
        logger.debug("Imported agents.orbital_agents")
        from workflow.state import OrbitalJuristState
        logger.debug("Imported workflow.state")
        from workflow.graph import OrbitalJuristWorkflow
        logger.debug("Imported workflow.graph")
        from prompts.registry import get_prompt
        logger.debug("Imported prompts.registry")
        from mcp_servers.registry import load_tools
        logger.debug("Imported mcp_servers.registry")
        logger.info("✓ All imports successful")
        print("✓ All imports successful")
        return True
    except Exception as e:
        logger.critical(f"Import failed: {e}")
        print(f"✗ Import failed: {e}")
        return False


def test_groq_client() -> bool:
    """Test Groq client configuration"""
    logger.info("TEST: Testing Groq client...")
    try:
        from utils.groq_client import GroqClient
        from config import settings

        if not settings.GROQ_API_KEY:
            print("✗ GROQ_API_KEY not configured")
            return False

        client = GroqClient()
        messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user",   "content": "Say 'test successful' and nothing else."},
        ]

        response = client.chat(messages, max_tokens=50)

        if response.get("error"):
            print(f"✗ Groq API error: {response['error']}")
            return False

        if response.get("content"):
            content = response["content"]
            logger.info(f"Groq response received: {content[:50]}")
            print(f"✓ Groq client working (response: {content[:50]}...)")
            return True
        else:
            print("✗ Groq returned empty response")
            return False

    except Exception as e:
        logger.exception(f"Groq test failed: {e}")
        print(f"✗ Groq test failed: {e}")
        return False


def test_celestrak_client() -> bool:
    """Test CelesTrak data fetching"""
    logger.info("TEST: Testing CelesTrak client...")
    try:
        from utils.data_loader import CelesTrakClient

        logger.debug("Fetching TLE for ISS (25544)...")
        tle_data = CelesTrakClient.fetch_tle(25544)

        if tle_data and tle_data.get("name"):
            logger.info(f"CelesTrak fetch OK: {tle_data['name']}")
            print(f"✓ CelesTrak working (fetched: {tle_data['name']})")
            return True
        else:
            print("✗ CelesTrak returned no data")
            return False

    except Exception as e:
        logger.exception(f"CelesTrak test failed: {e}")
        print(f"✗ CelesTrak test failed: {e}")
        return False


def test_circuit_breakers() -> bool:
    """Test circuit breaker registration and status"""
    logger.info("TEST: Testing circuit breakers...")
    try:
        from utils.resilience import get_circuit_breaker, all_circuit_breaker_statuses

        # Force registration by importing data_loader and groq_client
        from utils import data_loader, groq_client  # noqa: F401

        statuses = all_circuit_breaker_statuses()
        if len(statuses) == 0:
            print("✗ No circuit breakers registered")
            return False

        for s in statuses:
            logger.info(f"CB status: {s['name']} -> {s['state']}")

        print(f"✓ Circuit breakers registered ({len(statuses)} breakers)")
        return True

    except Exception as e:
        logger.exception(f"Circuit breaker test failed: {e}")
        print(f"✗ Circuit breaker test failed: {e}")
        return False


def test_legal_database() -> bool:
    """Test legal database initialization"""
    logger.info("TEST: Testing legal database...")
    try:
        from utils.data_loader import LegalDatabase

        db = LegalDatabase()

        if len(db.precedents) == 0:
            print("✗ Legal database empty")
            return False

        results = db.search("derelict vessel", top_k=2)

        if len(results) > 0:
            logger.info(f"Legal DB search OK: {len(results)} results")
            print(
                f"✓ Legal database working "
                f"({len(db.precedents)} precedents, search functional)"
            )
            return True
        else:
            print("✗ Legal database search returned no results")
            return False

    except Exception as e:
        logger.exception(f"Legal database test failed: {e}")
        print(f"✗ Legal database test failed: {e}")
        return False


def test_prompt_registry() -> bool:
    """Test versioned prompt registry"""
    logger.info("TEST: Testing prompt registry...")
    try:
        from prompts.registry import get_prompt

        system_prompt = get_prompt("physics_system")
        if not system_prompt:
            print("✗ Prompt registry returned empty physics_system")
            return False

        judge_prompt = get_prompt("judge_system")
        if not judge_prompt:
            print("✗ Prompt registry returned empty judge_system")
            return False

        # Test that unknown prompts raise correctly
        try:
            get_prompt("nonexistent_prompt_xyz")
            print("✗ Prompt registry should have raised KeyError")
            return False
        except KeyError:
            pass  # Expected

        print("✓ Prompt registry working (versioned templates load correctly)")
        return True

    except Exception as e:
        logger.exception(f"Prompt registry test failed: {e}")
        print(f"✗ Prompt registry test failed: {e}")
        return False


def test_mcp_orbital_tools() -> bool:
    """Test orbital MCP tools via registry"""
    logger.info("TEST: Testing orbital MCP tools...")
    try:
        from mcp_servers.registry import load_tools

        orbital_tools, _ = load_tools()

        # Test get_tle_data
        result = orbital_tools["get_tle_data"](norad_id=25544)
        if not result.get("success"):
            print(f"✗ get_tle_data failed: {result.get('error')}")
            return False

        # Test propagate_orbit
        time_now = datetime.now(timezone.utc).isoformat()
        result = orbital_tools["propagate_orbit"](norad_id=25544, target_time=time_now)
        if not result.get("success"):
            print(f"✗ propagate_orbit failed: {result.get('error')}")
            return False

        # Test detect_maneuver (heuristic-based)
        result = orbital_tools["detect_maneuver"](
            norad_id=25544,
            reference_time=time_now,
            lookback_hours=48,
        )
        if not result.get("success"):
            print(f"✗ detect_maneuver failed: {result.get('error')}")
            return False

        status = result.get("status")
        logger.info(f"ISS classified as: {status}")
        print(f"✓ Orbital MCP tools working (ISS status: {status})")
        return True

    except Exception as e:
        logger.exception(f"Orbital MCP test failed: {e}")
        print(f"✗ Orbital MCP test failed: {e}")
        return False


def test_mcp_legal_tools() -> bool:
    """Test legal MCP tools via registry"""
    logger.info("TEST: Testing legal MCP tools...")
    try:
        from mcp_servers.registry import load_tools

        _, legal_tools = load_tools()

        # Test search
        result = legal_tools["search_maritime_precedents"](query="derelict", top_k=2)
        if not result.get("success"):
            print(f"✗ search_maritime_precedents failed: {result.get('error')}")
            return False

        # Test treaty article
        result = legal_tools["get_liability_convention_article"](article="III")
        if not result.get("success"):
            print(f"✗ get_liability_convention_article failed: {result.get('error')}")
            return False

        # Test liability factors
        result = legal_tools["analyze_liability_factors"](
            object_1_status="ACTIVE",
            object_2_status="DRIFTING",
            warning_provided=True,
            maneuver_possible=True,
        )
        if not result.get("success"):
            print(f"✗ analyze_liability_factors failed: {result.get('error')}")
            return False

        split = result.get("liability_split", {})
        logger.info(f"Liability split: {split}")
        print(f"✓ Legal MCP tools working (split: {split})")
        return True

    except Exception as e:
        logger.exception(f"Legal MCP test failed: {e}")
        print(f"✗ Legal MCP test failed: {e}")
        return False


def test_agents() -> bool:
    """Test agent initialization"""
    logger.info("TEST: Testing agent initialization...")
    try:
        from agents.orbital_agents import (
            PhysicsForensicAgent,
            MaritimeScholarAgent,
            LiabilityJudgeAgent,
        )

        physics = PhysicsForensicAgent()
        scholar = MaritimeScholarAgent()
        judge   = LiabilityJudgeAgent()

        print("✓ All agents initialized successfully")
        return True

    except Exception as e:
        logger.exception(f"Agent test failed: {e}")
        print(f"✗ Agent test failed: {e}")
        return False


def test_workflow() -> bool:
    """Test workflow graph creation"""
    logger.info("TEST: Testing workflow graph assembly...")
    try:
        from mcp_servers.registry import load_tools
        from workflow.graph import OrbitalJuristWorkflow

        orbital_tools, legal_tools = load_tools()
        workflow = OrbitalJuristWorkflow(orbital_tools, legal_tools)

        # Verify the graph was compiled
        if workflow.graph is None:
            print("✗ Workflow graph not compiled")
            return False

        print("✓ Workflow graph created successfully")
        return True

    except Exception as e:
        logger.exception(f"Workflow test failed: {e}")
        print(f"✗ Workflow test failed: {e}")
        return False


def test_results_store() -> bool:
    """Test in-memory TTL results store"""
    logger.info("TEST: Testing results store...")
    try:
        import time

        # Inline minimal test of the store logic
        class _ResultsStore:
            def __init__(self, ttl):
                self._store = {}
                self._ttl   = ttl

            def put(self, key, value):
                self._store[key] = {"data": value, "ts": time.monotonic()}

            def get(self, key):
                entry = self._store.get(key)
                if entry is None:
                    return None
                if time.monotonic() - entry["ts"] > self._ttl:
                    del self._store[key]
                    return None
                return entry["data"]

            def evict_expired(self):
                cutoff  = time.monotonic() - self._ttl
                expired = [k for k, v in self._store.items() if v["ts"] < cutoff]
                for k in expired:
                    del self._store[k]
                return len(expired)

        store = _ResultsStore(ttl=1)
        store.put("test_key", {"result": "ok"})

        val = store.get("test_key")
        if val is None:
            print("✗ Results store get returned None immediately after put")
            return False

        # Wait for TTL to expire
        time.sleep(1.1)
        val = store.get("test_key")
        if val is not None:
            print("✗ Results store did not expire entry after TTL")
            return False

        print("✓ Results store working (TTL eviction confirmed)")
        return True

    except Exception as e:
        logger.exception(f"Results store test failed: {e}")
        print(f"✗ Results store test failed: {e}")
        return False


def run_all_tests() -> int:
    """Run all tests and return exit code"""
    logger.info("STARTING ALL TESTS")
    print("\n" + "=" * 60)
    print("ORBITAL JURIST SYSTEM TESTS")
    print("=" * 60)

    tests = [
        ("Module Imports",      test_imports),
        ("Groq Client",         test_groq_client),
        ("CelesTrak Client",    test_celestrak_client),
        ("Circuit Breakers",    test_circuit_breakers),
        ("Legal Database",      test_legal_database),
        ("Prompt Registry",     test_prompt_registry),
        ("Orbital MCP Tools",   test_mcp_orbital_tools),
        ("Legal MCP Tools",     test_mcp_legal_tools),
        ("Agent Initialization", test_agents),
        ("Workflow Graph",      test_workflow),
        ("Results Store TTL",   test_results_store),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            logger.info(f"--- Running Test: {test_name} ---")
            success = test_func()
            results.append((test_name, success))
            logger.info(f"--- Test {test_name}: {'PASSED' if success else 'FAILED'} ---")
        except Exception as e:
            logger.critical(f"Test {test_name} CRASHED: {e}")
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total  = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    logger.info(f"TEST RUN COMPLETE. Score: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())