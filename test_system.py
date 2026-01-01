"""
Comprehensive Test Suite for Orbital Jurist
Tests all components and integration
"""
import sys
import json
import logging
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("system_tests.log"),
        logging.StreamHandler(sys.stderr)
    ]
)
# Silence chatty libraries
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("SystemTest")

def extract_callable(tool):
    """Helper to extract callable from FastMCP FunctionTool"""
    if hasattr(tool, 'fn'):
        return tool.fn
    elif callable(tool):
        return tool
    else:
        raise ValueError(f"Cannot extract callable from {tool}")

def test_imports():
    """Test all module imports"""
    logger.info("TEST: Testing imports...")
    try:
        from config import settings
        logger.debug("Imported config.settings")
        from utils.groq_client import GroqClient
        logger.debug("Imported utils.groq_client")
        from utils.data_loader import CelesTrakClient, LegalDatabase
        logger.debug("Imported utils.data_loader")
        from agents.orbital_agents import PhysicsForensicAgent, MaritimeScholarAgent, LiabilityJudgeAgent
        logger.debug("Imported agents.orbital_agents")
        from workflow.state import OrbitalJuristState
        logger.debug("Imported workflow.state")
        from workflow.graph import OrbitalJuristWorkflow
        logger.debug("Imported workflow.graph")
        
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.critical(f"✗ Import failed: {e}")
        return False

def test_groq_client():
    """Test Groq client configuration"""
    logger.info("TEST: Testing Groq client...")
    try:
        from utils.groq_client import GroqClient
        from config import settings
        
        if not settings.GROQ_API_KEY:
            logger.error("✗ GROQ_API_KEY not configured in settings")
            print("✗ GROQ_API_KEY not configured")
            return False
        
        logger.debug("Initializing GroqClient...")
        client = GroqClient()
        messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Say 'test successful' and nothing else."}
        ]
        
        logger.debug("Sending test chat request...")
        response = client.chat(messages, max_tokens=50)
        
        if response.get("error"):
            logger.error(f"✗ Groq API error: {response['error']}")
            print(f"✗ Groq API error: {response['error']}")
            return False
        
        if response.get("content"):
            content = response['content']
            logger.info(f"✓ Groq client working. Response: {content}")
            print(f"✓ Groq client working (response: {content[:50]}...)")
            return True
        else:
            logger.warning("✗ Groq returned empty response")
            print("✗ Groq returned empty response")
            return False
            
    except Exception as e:
        logger.exception(f"✗ Groq test failed: {e}")
        print(f"✗ Groq test failed: {e}")
        return False

def test_celestrak_client():
    """Test CelesTrak data fetching"""
    logger.info("TEST: Testing CelesTrak client...")
    try:
        from utils.data_loader import CelesTrakClient
        
        # Test with ISS (NORAD 25544 - always available)
        logger.debug("Fetching TLE for ISS (25544)...")
        tle_data = CelesTrakClient.fetch_tle(25544)
        
        if tle_data and tle_data.get("name"):
            logger.info(f"✓ CelesTrak working. Fetched: {tle_data['name']}")
            print(f"✓ CelesTrak working (fetched: {tle_data['name']})")
            return True
        else:
            logger.error("✗ CelesTrak returned no data")
            print("✗ CelesTrak returned no data")
            return False
            
    except Exception as e:
        logger.exception(f"✗ CelesTrak test failed: {e}")
        print(f"✗ CelesTrak test failed: {e}")
        return False

def test_legal_database():
    """Test legal database initialization"""
    logger.info("TEST: Testing legal database...")
    try:
        from utils.data_loader import LegalDatabase
        
        logger.debug("Initializing LegalDatabase...")
        db = LegalDatabase()
        
        if len(db.precedents) == 0:
            logger.error("✗ Legal database empty")
            print("✗ Legal database empty")
            return False
        
        # Test search
        logger.debug("Performing test search for 'derelict vessel'...")
        results = db.search("derelict vessel", top_k=2)
        
        if len(results) > 0:
            logger.info(f"✓ Legal database working. {len(db.precedents)} precedents loaded.")
            print(f"✓ Legal database working ({len(db.precedents)} precedents, search functional)")
            return True
        else:
            logger.error("✗ Legal database search returned no results")
            print("✗ Legal database search failed")
            return False
            
    except Exception as e:
        logger.exception(f"✗ Legal database test failed: {e}")
        print(f"✗ Legal database test failed: {e}")
        return False

def test_mcp_orbital_tools():
    """Test orbital MCP tools"""
    logger.info("TEST: Testing orbital MCP tools...")
    try:
        # Load orbital server
        logger.debug("Loading orbital_server module...")
        spec = importlib.util.spec_from_file_location(
            "orbital_server",
            Path(__file__).parent / "mcp_servers" / "orbital_server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test get_tle_data
        logger.debug("Testing tool: get_tle_data")
        get_tle_data = extract_callable(module.get_tle_data)
        result = get_tle_data(25544)
        if not result.get("success"):
            logger.error("✗ get_tle_data tool failed")
            print("✗ get_tle_data failed")
            return False
        
        # Test propagate_orbit
        logger.debug("Testing tool: propagate_orbit")
        propagate_orbit = extract_callable(module.propagate_orbit)
        time_now = datetime.now(timezone.utc).isoformat()
        result = propagate_orbit(25544, time_now)
        if not result.get("success"):
            logger.error("✗ propagate_orbit tool failed")
            print("✗ propagate_orbit failed")
            return False
        
        logger.info("✓ Orbital MCP tools working")
        print("✓ Orbital MCP tools working")
        return True
        
    except Exception as e:
        logger.exception(f"✗ Orbital MCP test failed: {e}")
        print(f"✗ Orbital MCP test failed: {e}")
        return False

def test_mcp_legal_tools():
    """Test legal MCP tools"""
    logger.info("TEST: Testing legal MCP tools...")
    try:
        # Load legal server
        logger.debug("Loading legal_server module...")
        spec = importlib.util.spec_from_file_location(
            "legal_server",
            Path(__file__).parent / "mcp_servers" / "legal_server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test search
        logger.debug("Testing tool: search_maritime_precedents")
        search_precedents = extract_callable(module.search_maritime_precedents)
        result = search_precedents("derelict", top_k=2)
        if not result.get("success"):
            logger.error("✗ search_maritime_precedents tool failed")
            print("✗ search_maritime_precedents failed")
            return False
        
        # Test treaty article
        logger.debug("Testing tool: get_liability_convention_article")
        get_article = extract_callable(module.get_liability_convention_article)
        result = get_article("III")
        if not result.get("success"):
            logger.error("✗ get_liability_convention_article tool failed")
            print("✗ get_liability_convention_article failed")
            return False
        
        logger.info("✓ Legal MCP tools working")
        print("✓ Legal MCP tools working")
        return True
        
    except Exception as e:
        logger.exception(f"✗ Legal MCP test failed: {e}")
        print(f"✗ Legal MCP test failed: {e}")
        return False

def test_agents():
    """Test agent initialization"""
    logger.info("TEST: Testing agent initialization...")
    try:
        from agents.orbital_agents import PhysicsForensicAgent, MaritimeScholarAgent, LiabilityJudgeAgent
        
        logger.debug("Initializing PhysicsForensicAgent...")
        physics = PhysicsForensicAgent()
        logger.debug("Initializing MaritimeScholarAgent...")
        scholar = MaritimeScholarAgent()
        logger.debug("Initializing LiabilityJudgeAgent...")
        judge = LiabilityJudgeAgent()
        
        logger.info("✓ All agents initialized successfully")
        print("✓ All agents initialized successfully")
        return True
        
    except Exception as e:
        logger.exception(f"✗ Agent test failed: {e}")
        print(f"✗ Agent test failed: {e}")
        return False

def test_workflow():
    """Test workflow graph creation"""
    logger.info("TEST: Testing workflow graph assembly...")
    try:
        from workflow.graph import OrbitalJuristWorkflow
        
        # Load tools
        logger.debug("Mock loading tools for workflow...")
        orbital_spec = importlib.util.spec_from_file_location(
            "orbital_server",
            Path(__file__).parent / "mcp_servers" / "orbital_server.py"
        )
        orbital_module = importlib.util.module_from_spec(orbital_spec)
        orbital_spec.loader.exec_module(orbital_module)
        
        legal_spec = importlib.util.spec_from_file_location(
            "legal_server",
            Path(__file__).parent / "mcp_servers" / "legal_server.py"
        )
        legal_module = importlib.util.module_from_spec(legal_spec)
        legal_spec.loader.exec_module(legal_module)
        
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
        
        logger.debug("Instantiating OrbitalJuristWorkflow...")
        workflow = OrbitalJuristWorkflow(orbital_tools, legal_tools)
        
        logger.info("✓ Workflow graph created successfully")
        print("✓ Workflow graph created successfully")
        return True
        
    except Exception as e:
        logger.exception(f"✗ Workflow test failed: {e}")
        print(f"✗ Workflow test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    logger.info("STARTING ALL TESTS")
    print("\n" + "="*60)
    print("ORBITAL JURIST SYSTEM TESTS")
    print("="*60)
    
    tests = [
        ("Module Imports", test_imports),
        ("Groq Client", test_groq_client),
        ("CelesTrak Client", test_celestrak_client),
        ("Legal Database", test_legal_database),
        ("Orbital MCP Tools", test_mcp_orbital_tools),
        ("Legal MCP Tools", test_mcp_legal_tools),
        ("Agent Initialization", test_agents),
        ("Workflow Graph", test_workflow),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            logger.info(f"--- Running Test: {test_name} ---")
            success = test_func()
            results.append((test_name, success))
            status = "PASSED" if success else "FAILED"
            logger.info(f"--- Test {test_name}: {status} ---")
        except Exception as e:
            logger.critical(f"Test {test_name} CRASHED: {e}")
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed")
    logger.info(f"TEST RUN COMPLETE. Score: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review system_tests.log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())