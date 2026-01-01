# The Orbital Jurist 

**Autonomous Space Debris Liability Arbiter**

An advanced AI system that combines orbital mechanics, maritime law, and multi-agent reasoning to autonomously adjudicate liability in satellite collision and near-miss events. Built with LangGraph, Groq, and FastMCP.

##  Overview

The Orbital Jurist operates at the intersection of **Astrodynamics** and **Admiralty Law**, using three specialized AI agents to analyze orbital conjunctions and render legally-grounded liability judgments:

1. **PhysicsForensic Agent** - Establishes physical truth using orbital mechanics (SGP4 propagation)
2. **MaritimeScholar Agent** - Applies maritime law precedents and space treaties
3. **LiabilityJudge Agent** - Synthesizes evidence into binding judgments

### Why This Matters

- **Growing Problem**: LEO is cluttered with 36,000+ tracked debris objects
- **Legal Vacuum**: Current liability processes take years and lack automation
- **Innovation**: First system to algorithmically bridge orbital physics and legal reasoning

##  Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI REST API                      │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────┐
│              LangGraph Workflow Orchestrator       │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │
│  │  Physics   │→ │  Maritime  │→ │  Liability  │   │
│  │  Forensic  │  │  Scholar   │  │   Judge     │   │
│  └─────┬──────┘  └─────┬──────┘  └──────┬──────┘   │
└────────┼───────────────┼────────────────┼──────────┘
         │               │                │
    ┌────▼────┐     ┌────▼────┐     ┌─────▼───┐
    │ Orbital │     │  Legal  │     │  Legal  │
    │   MCP   │     │   MCP   │     │   MCP   │
    │ Server  │     │ Server  │     │ Server  │
    └────┬────┘     └────┬────┘     └────┬────┘
         │               │               │
    ┌────▼────┐     ┌────▼────┐          │
    │CelesTrak│     │ Maritime│          │
    │   TLEs  │     │   Law   │          │
    │  SGP4   │     │   DB    │          │
    └─────────┘     └─────────┘          │
                                         │
                    ┌────────────────────▼─────┐
                    │    Groq LLM (Llama 3)    │
                    │  High-Speed Reasoning    │
                    └──────────────────────────┘
```

##  Project Structure

```
orbital_jurist/
├── main.py                      # FastAPI server & endpoints
├── run_analysis.py              # CLI runner for standalone use
├── config.py                    # Configuration management
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
│
├── agents/                      # Multi-agent implementations
│   ├── __init__.py
│   └── orbital_agents.py        # PhysicsForensic, MaritimeScholar, LiabilityJudge
│
├── mcp_servers/                 # FastMCP tool servers
│   ├── __init__.py
│   ├── orbital_server.py        # SGP4, TLE fetching, collision detection
│   └── legal_server.py          # Legal precedents, treaty database
│
├── workflow/                    # LangGraph orchestration
│   ├── __init__.py
│   ├── state.py                 # State definitions
│   └── graph.py                 # Workflow graph
│
├── utils/                       # Utilities
│   ├── __init__.py
│   ├── groq_client.py           # Groq API wrapper
│   └── data_loader.py           # CelesTrak & legal DB loaders
│
└── data/                        # Data storage
    ├── legal_precedents.json    # Maritime law database
    └── README.md
```

##  Quick Start

### Prerequisites

- Python 3.9+
- Groq API key ([Get one here](https://console.groq.com/))

### Installation

```bash
# Clone repository
git clone <repository-url>
cd orbital_jurist

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Usage

#### Option 1: CLI (Recommended for testing)

```bash
# List valid satellite IDs for testing
python run_analysis.py --list-satellites

# Analyze conjunction between ISS and Starlink
python run_analysis.py --obj1 25544 --obj2 43013

# Analyze ISS and Hubble Space Telescope
python run_analysis.py --obj1 25544 --obj2 20580

# Specify conjunction time
python run_analysis.py --obj1 25544 --obj2 43013 --time "2025-01-15T12:00:00Z"

# Save results to file
python run_analysis.py --obj1 25544 --obj2 43013 --output results/case_001.json
```

**Valid Test Satellite IDs:**
- `25544` - ISS (ZARYA) - International Space Station
- `20580` - HST - Hubble Space Telescope
- `43013` - STARLINK-1007 - SpaceX Starlink
- `37849` - COSMOS 2251 DEB - Russian debris
- `28353` - FENGYUN 1C DEB - Chinese debris
- `27386` - IRIDIUM 33 DEB - Iridium debris

*Note: Use real NORAD catalog IDs from [CelesTrak](https://celestrak.org/satcat/search.php) for actual analysis.*

#### Option 2: FastAPI Server

```bash
# Start the API server
python main.py

# Server runs at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

**API Example:**

```bash
# Analyze conjunction via REST API
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "object_1_id": 25544,
    "object_2_id": 43013,
    "conjunction_time": "2025-01-15T12:00:00Z"
  }'
```

##  Example Output

```
================================================================================
ORBITAL JURIST - AUTONOMOUS SPACE DEBRIS LIABILITY ARBITER
================================================================================
Case: NORAD 25544 vs NORAD 99999
Conjunction Time: 2025-01-15T12:00:00Z
================================================================================

============================================================
[PhysicsForensic] Initiating Physics Forensic Analysis
============================================================
[PhysicsForensic] Fetching TLE data...
[PhysicsForensic] Object 1: ISS (ZARYA) (NORAD 25544)
[PhysicsForensic] Object 2: UNKNOWN (NORAD 99999)
[PhysicsForensic] Minimum Distance: 0.347 km
[PhysicsForensic] Collision: YES
[PhysicsForensic] Object 1 Status: ACTIVE
[PhysicsForensic] Object 2 Status: DRIFTING

[PhysicsForensic] PHYSICS SUMMARY:
The ISS demonstrated active control with recent maneuvers detected, while 
Object 99999 exhibited ballistic drift with no velocity changes. The 0.347 km 
miss distance constitutes a collision under the 1.0 km threshold. This was 
a chasing collision at 7,850 m/s relative velocity, indicating the ISS had 
the last clear opportunity to avoid the drifting debris.

============================================================
[MaritimeScholar] Initiating Legal Analysis
============================================================
[MaritimeScholar] Found 3 relevant precedents
  - Derelict Vessel Doctrine
  - Last Clear Chance Doctrine
  - 1972 Liability Convention - Article III

[MaritimeScholar] LEGAL OPINION:
The Derelict Vessel Doctrine applies as Object 99999 is an uncontrolled drifter.
However, the Last Clear Chance Doctrine shifts primary liability to the ISS, 
which maintained active control and had access to conjunction warnings. Under 
Article III of the 1972 Liability Convention, fault must be established for 
in-orbit collisions. The ISS's failure to maneuver despite capability and 
warning constitutes negligent navigation.

============================================================
[LiabilityJudge] Rendering Final Judgment
============================================================

================================================================================
FINAL JUDGMENT
================================================================================

📋 Case Summary:
   Active satellite ISS failed to maneuver to avoid drifting debris despite 
   capability and warning, resulting in collision at 0.347 km distance.

⚖️  Liability Assignment:
   ISS (ZARYA) (NORAD 25544): 85% fault
   UNKNOWN (NORAD 99999): 15% fault

📖 Legal Reasoning:
   The active satellite with maneuvering capability bore primary duty to avoid
   collision with known debris. Failure to execute avoidance maneuver despite
   conjunction warning constitutes negligent navigation.

📜 Applicable Doctrines:
   • Last Clear Chance Doctrine
   • Derelict Vessel Doctrine
   • Negligent Navigation

🏛️  Treaty Basis:
   1972 Liability Convention, Article III (Fault-Based Liability)

💥 Damage Assessment:
   Severity: CATASTROPHIC
   Kinetic Energy: 308.13 MJ
   Estimated Loss: $1,000,000.00

💡 Recommendations:
   • Implement automated collision avoidance for active satellites
   • Establish mandatory conjunction response protocols
   • Enhance debris tracking for improved warning lead times

================================================================================
Judgment rendered by: Orbital Jurist Autonomous System v1.0
Date: 2025-12-30T15:23:45.123456
================================================================================
```

## 🔧 Configuration

Edit `config.py` or set environment variables:

```python
# Analysis Parameters
COLLISION_THRESHOLD_KM = 1.0           # Collision distance threshold
MANEUVER_DETECTION_WINDOW_HOURS = 48   # Lookback for maneuver detection
VELOCITY_CHANGE_THRESHOLD_MS = 0.5     # Maneuver sensitivity (m/s)
```

##  MCP Tools

### Orbital Mechanics Server (`orbital_server.py`)

- `get_tle_data(norad_id)` - Fetch Two-Line Elements from CelesTrak
- `propagate_orbit(norad_id, target_time)` - SGP4 orbit propagation
- `calculate_miss_distance(id_1, id_2, start_time, end_time)` - Collision analysis
- `detect_maneuver(norad_id, reference_time, lookback_hours)` - Maneuver detection

### Legal Database Server (`legal_server.py`)

- `search_maritime_precedents(query, top_k)` - Search legal precedents
- `get_liability_convention_article(article)` - Retrieve treaty articles
- `analyze_liability_factors(...)` - Calculate liability split
- `calculate_damages_estimate(...)` - Estimate collision damages

##  Testing

```bash
# Run full test suite
python test_system.py

# List available test satellites
python run_analysis.py --list-satellites

# Test with ISS and Starlink (real satellites)
python run_analysis.py --obj1 25544 --obj2 43013

# Test orbital mechanics tools directly
python -c "from mcp_servers.orbital_server import get_tle_data; \
           from run_analysis import extract_callable; \
           tool = extract_callable(get_tle_data); \
           print(tool(25544))"

# Test legal database
python -c "from mcp_servers.legal_server import search_maritime_precedents; \
           from run_analysis import extract_callable; \
           tool = extract_callable(search_maritime_precedents); \
           print(tool('derelict vessel'))"
```

##  Legal Database

The system includes precedents from:

- **Rhodian Law on Jettison** - Proportional liability for common good
- **Derelict Vessel Doctrine** - Reduced liability for abandoned objects
- **Last Clear Chance Doctrine** - Duty of capable party to avoid collision
- **1972 Liability Convention** - International space law treaty

Add custom precedents by editing `data/legal_precedents.json`.

##  API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/api/v1/analyze` | POST | Analyze conjunction and render judgment |
| `/api/v1/status/{case_id}` | GET | Get case status and results |
| `/api/v1/precedents` | GET | List all legal precedents |
| `/api/v1/tle/{norad_id}` | POST | Fetch TLE data |
| `/api/v1/propagate` | POST | Propagate satellite orbit |

##  Technical Details

### Agent Specialization

**PhysicsForensic Agent**
- Model: Llama 3 70B (low temperature for deterministic physics)
- Tasks: TLE fetching, orbit propagation, maneuver detection
- Output: Objective physical truth (positions, velocities, status)

**MaritimeScholar Agent**
- Model: Mixtral 8x7B (broad knowledge for legal reasoning)
- Tasks: Precedent search, treaty interpretation, liability analysis
- Output: Legal framework and applicable doctrines

**LiabilityJudge Agent**
- Model: Llama 3 70B (structured reasoning)
- Tasks: Evidence synthesis, fault assignment, judgment rendering
- Output: Binding verdict with percentage liability split

### Data Sources

- **CelesTrak** - Free, real-time satellite TLE data
- **SGP4 Library** - Industry-standard orbit propagation
- **Maritime Law Corpus** - Historical precedents adapted for space

## ⚠️ Limitations

- **TLE Accuracy**: SGP4 has ~1km accuracy; high-precision cases may need numerical integration
- **Legal Scope**: Focuses on bilateral conjunctions; multi-party collisions require extension
- **Data Availability**: Relies on public TLE data; classified objects not included
- **Jurisdictional**: Based on 1972 Convention; national laws may vary

##  Acknowledgments

- **CelesTrak** for free satellite tracking data
- **SGP4 Library** maintainers
- Space law scholars and the 1972 Liability Convention authors

---

**Built with ❤️ for safer space operations**

*"In orbit, every collision is preventable. The question is: who had the duty to prevent it?"*