"""
Standalone CLI Runner for Orbital Jurist
Runs analysis directly without the API server
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
import importlib.util

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import settings
from workflow.graph import OrbitalJuristWorkflow

def load_mcp_tools():
    """Load MCP server tools as Python modules"""
    # Load orbital server tools
    orbital_spec = importlib.util.spec_from_file_location(
        "orbital_server",
        Path(__file__).parent / "mcp_servers" / "orbital_server.py"
    )
    orbital_module = importlib.util.module_from_spec(orbital_spec)
    orbital_spec.loader.exec_module(orbital_module)
    
    # Load legal server tools
    legal_spec = importlib.util.spec_from_file_location(
        "legal_server",
        Path(__file__).parent / "mcp_servers" / "legal_server.py"
    )
    legal_module = importlib.util.module_from_spec(legal_spec)
    legal_spec.loader.exec_module(legal_module)
    
    # Extract tool functions - get the actual callable, not the FunctionTool wrapper
    def extract_callable(tool):
        """Extract callable function from FastMCP FunctionTool"""
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
    
    return orbital_tools, legal_tools

def print_judgment(final_state: dict):
    """Pretty print the final judgment"""
    judgment = final_state.get("final_judgment")
    
    if not judgment:
        print("\n❌ No judgment rendered")
        if final_state.get("error_message"):
            print(f"Error: {final_state['error_message']}")
        return
    
    print("\n" + "="*80)
    print("FINAL JUDGMENT")
    print("="*80)
    
    print(f"\n📋 Case Summary:")
    print(f"   {judgment.get('case_summary', 'N/A')}")
    
    print(f"\n⚖️  Liability Assignment:")
    obj1 = final_state["object_1_data"]
    obj2 = final_state["object_2_data"]
    fault1 = judgment.get("fault_percentage_object_1", 0)
    fault2 = judgment.get("fault_percentage_object_2", 0)
    
    print(f"   {obj1['name']} (NORAD {obj1['norad_id']}): {fault1}% fault")
    print(f"   {obj2['name']} (NORAD {obj2['norad_id']}): {fault2}% fault")
    
    print(f"\n📖 Legal Reasoning:")
    print(f"   {judgment.get('primary_reasoning', 'N/A')}")
    
    print(f"\n📜 Applicable Doctrines:")
    for doctrine in judgment.get("applicable_doctrines", []):
        print(f"   • {doctrine}")
    
    print(f"\n🏛️  Treaty Basis:")
    print(f"   {judgment.get('treaty_basis', 'N/A')}")
    
    if judgment.get("damage_estimate"):
        damage = judgment["damage_estimate"]
        print(f"\n💥 Damage Assessment:")
        print(f"   Severity: {damage.get('severity', 'N/A')}")
        print(f"   Kinetic Energy: {damage.get('kinetic_energy_mj', 0)} MJ")
        if damage.get("estimated_loss_usd"):
            print(f"   Estimated Loss: ${damage['estimated_loss_usd']:,.2f}")
    
    print(f"\n💡 Recommendations:")
    for rec in judgment.get("recommendations", []):
        print(f"   • {rec}")
    
    print("\n" + "="*80)
    print(f"Judgment rendered by: {judgment.get('adjudicating_authority', 'Orbital Jurist')}")
    print(f"Date: {judgment.get('judgment_date', 'N/A')}")
    print("="*80 + "\n")

def save_judgment(final_state: dict, output_file: str):
    """Save judgment to JSON file"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(final_state, f, indent=2)
    
    print(f"✓ Judgment saved to: {output_path}")

# Valid test satellite IDs for demonstrations
VALID_TEST_SATELLITES = {
    25544: "ISS (ZARYA) - International Space Station",
    20580: "HST - Hubble Space Telescope",
    43013: "STARLINK-1007 - SpaceX Starlink",
    41765: "STARLINK-1341 - SpaceX Starlink", 
    37849: "COSMOS 2251 DEB - Russian debris",
    28353: "FENGYUN 1C DEB - Chinese debris",
    27386: "IRIDIUM 33 DEB - Iridium debris",
    40128: "CZ-4B R/B - Chinese rocket body",
    43947: "STARLINK-1600 - SpaceX Starlink",
    48274: "STARLINK-3042 - SpaceX Starlink"
}

def suggest_valid_satellites():
    """Print list of valid test satellites"""
    print("\n" + "="*70)
    print("VALID TEST SATELLITE IDs")
    print("="*70)
    print("\nHere are some real satellites you can use for testing:\n")
    for norad_id, name in VALID_TEST_SATELLITES.items():
        print(f"  {norad_id:6d} - {name}")
    print("\n" + "="*70)
    print("\nExample commands:")
    print("  # ISS vs Starlink")
    print("  python run_analysis.py --obj1 25544 --obj2 43013")
    print("\n  # ISS vs Hubble")
    print("  python run_analysis.py --obj1 25544 --obj2 20580")
    print("\n  # Starlink vs debris")
    print("  python run_analysis.py --obj1 43013 --obj2 37849")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Orbital Jurist - Autonomous Space Debris Liability Arbiter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze conjunction between ISS and Starlink
  python run_analysis.py --obj1 25544 --obj2 43013
  
  # Analyze ISS and Hubble Space Telescope
  python run_analysis.py --obj1 25544 --obj2 20580
  
  # Analyze with specific conjunction time
  python run_analysis.py --obj1 25544 --obj2 43013 --time "2025-01-15T12:00:00Z"
  
  # Save results to file
  python run_analysis.py --obj1 25544 --obj2 43013 --output results/case_001.json
  
  # List valid satellite IDs
  python run_analysis.py --list-satellites
        """
    )
    
    parser.add_argument(
        "--obj1",
        type=int,
        required=False,
        help="NORAD catalog ID of first object (e.g., 25544 for ISS)"
    )
    
    parser.add_argument(
        "--obj2",
        type=int,
        required=False,
        help="NORAD catalog ID of second object"
    )
    
    parser.add_argument(
        "--time",
        type=str,
        default=None,
        help="Conjunction time in ISO format (default: current time)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for judgment (JSON format)"
    )
    
    parser.add_argument(
        "--list-satellites",
        action="store_true",
        help="Show list of valid test satellite IDs"
    )
    
    args = parser.parse_args()
    
    # Handle --list-satellites
    if args.list_satellites:
        suggest_valid_satellites()
        sys.exit(0)
    
    # Validate required arguments if not listing
    if not args.obj1 or not args.obj2:
        parser.error("--obj1 and --obj2 are required (or use --list-satellites)")
    
    # Check if user provided non-existent IDs
    if args.obj1 > 90000 or args.obj2 > 90000:
        print("⚠️  Warning: You provided NORAD IDs over 90000.")
        print("   These may not exist in CelesTrak's database.\n")
        suggest_valid_satellites()
        
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    # Validate Groq API key
    if not settings.GROQ_API_KEY:
        print("❌ Error: GROQ_API_KEY not set in environment")
        print("Please set the GROQ_API_KEY environment variable:")
        print("  export GROQ_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Load tools
    print("Loading MCP tools...")
    orbital_tools, legal_tools = load_mcp_tools()
    print(f"✓ Loaded {len(orbital_tools)} orbital tools and {len(legal_tools)} legal tools")
    
    # Initialize workflow
    workflow = OrbitalJuristWorkflow(orbital_tools, legal_tools)
    
    # Default time to now if not provided
    conjunction_time = args.time or datetime.now(timezone.utc).isoformat()
    
    print(f"\n🚀 Starting analysis...")
    print(f"   Object 1: NORAD {args.obj1}")
    print(f"   Object 2: NORAD {args.obj2}")
    print(f"   Time: {conjunction_time}\n")
    
    try:
        # Run analysis
        final_state = workflow.run_sync(
            object_1_id=args.obj1,
            object_2_id=args.obj2,
            conjunction_time=conjunction_time
        )
        
        # Check for specific errors
        error_msg = final_state.get("error_message") or ""

        if "Failed to fetch TLE data" in error_msg:
            print_judgment(final_state)
            print("\n" + "="*70)
            print("❌ ERROR: Cannot fetch satellite data from CelesTrak")
            print("="*70)
            print(f"\nOne or both NORAD IDs do not exist:")
            print(f"  Object 1: NORAD {args.obj1}")
            print(f"  Object 2: NORAD {args.obj2}")
            print("\nPossible reasons:")
            print("  • The satellite ID doesn't exist in CelesTrak's database")
            print("  • The satellite has not been catalogued yet")
            print("  • The ID was mistyped")
            suggest_valid_satellites()
            sys.exit(1)
        
        # Display results
        print_judgment(final_state)
        
        # Save to file if requested
        if args.output:
            save_judgment(final_state, args.output)
        
        # Exit with success
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Provide helpful guidance on common errors
        if "TLE" in str(e) or "fetch" in str(e).lower():
            print("\n💡 Tip: Use --list-satellites to see valid test satellite IDs")
        
        sys.exit(1)

if __name__ == "__main__":
    main()