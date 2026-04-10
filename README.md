# Orbital Jurist

**Autonomous Space Debris Liability Arbiter**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3A5E?logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/Groq-Llama--3.3--70B-F55036)](https://console.groq.com/)
[![RunPod Serverless](https://img.shields.io/badge/RunPod-Serverless-5C4EE5?logo=docker&logoColor=white)](https://runpod.io/)
[![Netlify](https://img.shields.io/badge/Netlify-Frontend-00C7B7?logo=netlify&logoColor=white)](https://netlify.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade, multi-agent AI system that autonomously adjudicates liability in satellite conjunction and collision events. It bridges **orbital mechanics** and **admiralty law** — fetching live TLE data from CelesTrak, propagating orbits with SGP4, searching maritime legal precedents, and rendering structured liability judgments, all in under 30 seconds.

---

## Table of Contents

- [Overview](#overview)
- [Live Demo](#live-demo)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
  - [Backend — RunPod Serverless](#backend--runpod-serverless)
  - [Frontend — Netlify](#frontend--netlify)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Testing](#testing)
- [Agent Specialisation](#agent-specialisation)
- [MCP Tool Servers](#mcp-tool-servers)
- [Legal Database](#legal-database)
- [Limitations](#limitations)
- [Acknowledgements](#acknowledgements)

---

## Overview

LEO is cluttered with **36,000+ tracked debris objects** and growing. When two objects collide or narrowly miss, determining legal liability under the 1972 Outer Space Liability Convention takes years and lacks any automation. Orbital Jurist solves this.

### What it does

1. Fetches real-time Two-Line Element (TLE) data from CelesTrak for any two NORAD-catalogued objects
2. Propagates both orbits to the conjunction epoch using SGP4 and computes the minimum miss distance
3. Classifies each object's operational status (ACTIVE / DRIFTING / UNCERTAIN) using epoch age, BSTAR drag, and name heuristics
4. Searches a curated maritime law precedent database for applicable doctrines (Derelict Vessel, Last Clear Chance, Negligent Navigation, etc.)
5. Retrieves the applicable article from the 1972 Liability Convention
6. Renders a structured, legally-grounded fault judgment with percentage liability split, damage estimate, and actionable recommendations

### Why it matters

| Problem | Solution |
|---|---|
| Liability determination takes years | Automated judgment in < 30 seconds |
| No standard framework for orbital collisions | Maritime law analogically applied via AI |
| Physics and law evaluated in silos | Multi-agent pipeline integrating both |
| Debris operators have no feedback loop | Quantified fault percentages and recommendations |

---

## Live Demo

> **Frontend:** [orbital-jurist.netlify.app](https://orbital-jurist.netlify.app) *(replace with your URL)*  
> **Backend:** RunPod Serverless endpoint *(see [Deployment](#deployment))*

**Quick test — ISS vs. Starlink Debris:**

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"object_1_id": 25544, "object_2_id": 37849}}'
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    React UI  (Netlify CDN)                       │
│          Vite · DM Sans · Orbitron · Share Tech Mono             │
└──────────────────────────┬───────────────────────────────────────┘
                           │  HTTPS  POST /runsync
                           │  Authorization: Bearer <RUNPOD_API_KEY>
┌──────────────────────────▼───────────────────────────────────────┐
│              RunPod Serverless  (rp_handler.py)                  │
│          Docker · python:3.11-slim · CPU worker                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│             LangGraph Workflow Orchestrator                     │
│                   (workflow/graph.py)                           │
│                                                                 │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────┐  │
│  │ PhysicsForensic │──▶│  MaritimeScholar │──▶│LiabilityJudge│  │
│  │     Agent       │   │      Agent       │   │    Agent     │  │
│  └────────┬────────┘   └────────┬─────────┘   └──────┬───────┘  │
│           │                     │                    │          │
│   ┌───────▼──────┐      ┌───────▼──────┐    ┌────────▼─────┐    │
│   │  Orbital MCP │      │   Legal MCP  │    │   Legal MCP  │    │
│   │    Server    │      │    Server    │    │    Server    │    │
│   └───────┬──────┘      └───────┬──────┘    └──────────────┘    │
└───────────┼─────────────────────┼───────────────────────────────┘
            │                     │
   ┌────────▼────────┐   ┌────────▼────────┐
   │   CelesTrak     │   │Legal Precedents │
   │  TLE Database   │   │  (JSON + SPARQL)│
   │  SGP4 Propagator│   │ 1972 Convention │
   └─────────────────┘   └─────────────────┘
                  ↕ (all LLM calls)
        ┌──────────────────────────┐
        │   Groq  —  Llama-3.3-70B │
        │   High-speed inference   │
        └──────────────────────────┘
```

### Request lifecycle

```
UI  ──POST /runsync──▶  RunPod Queue
                             │
                        Worker starts (cold start ~5s, warm ~0s)
                             │
                        rp_handler.py  ──▶  OrbitalJuristWorkflow.run()
                             │
                        physics_forensic  ──▶  TLE fetch + SGP4 + maneuver classify
                             │
                        ┌────▼────────────────────────────────────────┐
                        │ miss_dist > 10 km?  ──yes──▶ NoRiskVerdict  │
                        │              no                             │
                        └────▼────────────────────────────────────────┘
                             │
                        maritime_scholar  ──▶  precedent search + treaty lookup
                             │
                        liability_judge  ──▶  structured JSON judgment
                             │
                        RunPod  ──▶  { status: "COMPLETED", output: { judgment, metadata } }
                             │
                        UI renders result
```

---

## Project Structure

```
orbital_jurist/
│
├── rp_handler.py               # RunPod serverless entrypoint
├── Dockerfile                  # Container image (python:3.11-slim + runpod)
├── main.py                     # FastAPI server (local dev / alternative deploy)
├── config.py                   # Pydantic settings — all tuneable parameters
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── netlify.toml                # Netlify build config (base: ui, publish: dist)
│
├── agents/
│   ├── __init__.py
│   └── orbital_agents.py       # PhysicsForensic · MaritimeScholar · LiabilityJudge · NoRisk
│
├── mcp_servers/
│   ├── __init__.py
│   ├── registry.py             # Single source of truth — load_tools()
│   ├── orbital_server.py       # SGP4, TLE fetch, miss-distance, maneuver classify
│   └── legal_server.py         # Precedent search, treaty articles, liability factors, damages
│
├── workflow/
│   ├── __init__.py
│   ├── state.py                # OrbitalJuristState TypedDict
│   └── graph.py                # LangGraph StateGraph — 4-node DAG with short-circuit
│
├── prompts/
│   ├── __init__.py
│   └── registry.py             # Versioned prompt templates — get_prompt(name)
│
├── utils/
│   ├── __init__.py
│   ├── groq_client.py          # Groq wrapper — retry, circuit breaker, structured output
│   ├── data_loader.py          # CelesTrakClient (TTL cache + CB) · LegalDatabase
│   ├── resilience.py           # CircuitBreaker · celestrak_retry · groq_retry
│   └── logging_config.py       # Structured JSON logging with per-request context
│
├── data/
│   └── legal_precedents.json   # Maritime law precedent corpus
│
├── test/
│   ├── test_system.py          # Full integration test suite (11 tests)
│   └── test_tle_fetch.py       # CelesTrak connectivity smoke test
│
└── ui/                         # React frontend (Vite)
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── .env.example            # VITE_RUNPOD_ENDPOINT_ID · VITE_RUNPOD_API_KEY
    └── src/
        ├── main.jsx
        └── App.jsx             # Full SPA — form, pipeline visualiser, results renderer
```

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Backend |
| Docker | 24+ | Build + RunPod deploy |
| Node.js | 18+ | Frontend build |
| Groq API key | — | LLM inference ([get one](https://console.groq.com/)) |
| Docker Hub account | — | Container registry |
| RunPod account | — | Serverless backend ([sign up](https://runpod.io/)) |

### Local backend (without Docker)

```bash
git clone https://github.com/your-org/orbital-jurist.git
cd orbital-jurist

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set GROQ_API_KEY

# Run the FastAPI server
python main.py
# → http://localhost:8000/docs
```

### Local frontend

```bash
cd ui
cp .env.example .env
# Edit .env:
#   VITE_RUNPOD_ENDPOINT_ID=your_endpoint_id
#   VITE_RUNPOD_API_KEY=your_runpod_api_key

npm install
npm run dev
# → http://localhost:5173
```

---

## Deployment

### Backend — RunPod Serverless

The backend runs as a **CPU-only serverless worker** on RunPod. All LLM inference is handled by Groq's external API, so no GPU is required — this keeps costs near zero.

#### Step 1 — Build and push the Docker image

```bash
# Replace with your Docker Hub username
export DOCKER_USER=your_dockerhub_username

docker build \
  --platform linux/amd64 \
  --tag $DOCKER_USER/orbital-jurist:latest \
  .

docker push $DOCKER_USER/orbital-jurist:latest
```

> **Apple Silicon users:** The `--platform linux/amd64` flag is mandatory. RunPod workers run on x86_64.

#### Step 2 — Create the endpoint

1. Go to [console.runpod.io/serverless](https://console.runpod.io/serverless)
2. Click **New Endpoint** → **Import from Docker Registry**
3. Set **Container Image** to `docker.io/your_dockerhub_username/orbital-jurist:latest`
4. Configure:

| Setting | Value | Reason |
|---|---|---|
| GPU type | CPU only | Groq handles all inference |
| Min workers | `0` | Scale to zero — no idle cost |
| Max workers | `3` | Handles concurrent requests |
| Idle timeout | `30s` | Container kept warm after each job |
| Execution timeout | `120s` | Workflow takes 10–30s |
| Container disk | `5 GB` | Dependencies + Python packages |

5. Click **Create Endpoint** — note your **Endpoint ID**

#### Step 3 — Set environment variables

In the endpoint **Settings → Environment Variables**, add:

| Key | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_...` |
| `LOG_JSON` | `false` |
| `LOG_LEVEL` | `INFO` |

> **Security:** Never bake API keys into your Docker image. Always inject at runtime via RunPod environment variables.

#### Step 4 — Verify

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "object_1_id": 25544,
      "object_2_id": 43013
    }
  }'
```

Expected response shape:

```json
{
  "id": "job-abc123",
  "status": "COMPLETED",
  "output": {
    "judgment": {
      "case_summary": "...",
      "fault_percentage_object_1": 85.0,
      "fault_percentage_object_2": 15.0,
      "primary_reasoning": "...",
      "applicable_doctrines": ["Last Clear Chance Doctrine"],
      "treaty_basis": "1972 Liability Convention, Article III (Fault-Based Liability)",
      "recommendations": ["..."],
      "physical_findings": { ... },
      "damage_estimate": { "severity": "CATASTROPHIC", "kinetic_energy_mj": 308.13 }
    },
    "metadata": {
      "case_id": "OJ-25544-43013-abc12345",
      "object_1_name": "ISS (ZARYA)",
      "object_2_name": "STARLINK-1007",
      "miss_distance_km": 0.347,
      "collision_occurred": true,
      "verdict_complete": true
    }
  },
  "executionTime": 18432
}
```

#### Updating the deployment

```bash
# Rebuild and push a new image tag
docker build --platform linux/amd64 -t $DOCKER_USER/orbital-jurist:v1.1 .
docker push $DOCKER_USER/orbital-jurist:v1.1

# In RunPod console → endpoint Settings → update Container Image → Save
# Workers pull the new image on next cold start
```

---

### Frontend — Netlify

The React SPA is deployed to Netlify with automatic builds on `git push`.

#### Step 1 — Set environment variables in Netlify

Go to **Site Settings → Environment Variables** and add:

| Key | Value |
|---|---|
| `VITE_RUNPOD_ENDPOINT_ID` | Your RunPod endpoint ID |
| `VITE_RUNPOD_API_KEY` | Your RunPod API key |

> **Note:** Vite bakes `VITE_*` variables into the client bundle at build time. Do not store secrets here that must remain server-side only. The RunPod API key in the frontend authenticates requests to your specific endpoint — scope it appropriately.

#### Step 2 — Connect your repo

1. Push your repo to GitHub
2. In Netlify: **Add new site → Import an existing project**
3. Select your repo
4. Build settings are auto-detected from `netlify.toml`:

```toml
[build]
  base    = "ui"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "19"
```

5. Click **Deploy site**

#### Step 3 — Local build test

```bash
cd ui
npm run build
# Output in ui/dist/
```

---

## API Reference

### RunPod endpoint

| Operation | URL | Method |
|---|---|---|
| Synchronous (recommended) | `https://api.runpod.ai/v2/{endpoint_id}/runsync` | POST |
| Asynchronous submit | `https://api.runpod.ai/v2/{endpoint_id}/run` | POST |
| Poll async status | `https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}` | GET |
| Health check | `https://api.runpod.ai/v2/{endpoint_id}/health` | GET |

All requests require `Authorization: Bearer YOUR_RUNPOD_API_KEY`.

### Request body

```json
{
  "input": {
    "object_1_id": 25544,
    "object_2_id": 43013,
    "conjunction_time": "2025-06-15T12:00:00Z"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `object_1_id` | integer | ✅ | NORAD catalog ID of first object (1–90000) |
| `object_2_id` | integer | ✅ | NORAD catalog ID of second object (must differ from object_1_id) |
| `conjunction_time` | ISO-8601 string | ❌ | Defaults to current UTC time |

### FastAPI endpoints (local dev)

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | API info and version |
| `/health` | GET | Health + circuit breaker status |
| `/api/v1/analyze` | POST | Full conjunction analysis |
| `/api/v1/status/{case_id}` | GET | Retrieve cached result by case ID |
| `/api/v1/precedents` | GET | List all legal precedents |
| `/api/v1/tle/{norad_id}` | POST | Fetch TLE data for a satellite |
| `/api/v1/propagate` | POST | Propagate orbit to a target time |

---

## Configuration

All parameters are in `config.py` and can be overridden via environment variables.

```python
# LLM
PHYSICS_MODEL   = "llama-3.3-70b-versatile"
SCHOLAR_MODEL   = "llama-3.3-70b-versatile"
JUDGE_MODEL     = "llama-3.3-70b-versatile"
TEMPERATURE     = 0.1
MAX_TOKENS      = 4096

# Analysis thresholds
COLLISION_THRESHOLD_KM          = 1.0    # Below → collision event
CONJUNCTION_RISK_THRESHOLD_KM   = 10.0   # Above → NoRiskVerdict (no LLM calls)
MANEUVER_DETECTION_WINDOW_HOURS = 48
VELOCITY_CHANGE_THRESHOLD_MS    = 0.5

# CelesTrak
CELESTRAK_CACHE_TTL_S           = 3600   # 1 hour TLE cache
CELESTRAK_TIMEOUT_S             = 15.0

# Circuit breakers
CB_CELESTRAK_FAILURE_THRESHOLD  = 5
CB_CELESTRAK_RECOVERY_TIMEOUT_S = 120.0
CB_GROQ_FAILURE_THRESHOLD       = 3
CB_GROQ_RECOVERY_TIMEOUT_S      = 60.0

# Rate limiting (FastAPI only)
RATE_LIMIT_ANALYZE              = "10/minute"
RATE_LIMIT_DEFAULT              = "60/minute"

# Results TTL (FastAPI in-memory cache)
RESULTS_TTL_SECONDS             = 3600
```

---

## Testing

### Run the full test suite

```bash
# From project root with venv activated and GROQ_API_KEY set
python test/test_system.py
```

Runs 11 integration tests covering imports, Groq client, CelesTrak fetch, circuit breakers, legal DB, prompt registry, all MCP tools, agent initialisation, workflow graph compilation, and TTL results store.

### CelesTrak smoke test

```bash
python test/test_tle_fetch.py
# Tests ISS (25544), Starlink-1007 (43013), Hubble (20580)
```

### CLI analysis (no API server needed)

```bash
# List valid test satellite IDs
python run_analysis.py --list-satellites

# ISS vs Starlink (active vs active)
python run_analysis.py --obj1 25544 --obj2 43013

# ISS vs Russian debris (active vs drifting — tests Last Clear Chance Doctrine)
python run_analysis.py --obj1 25544 --obj2 37849

# Save judgment to file
python run_analysis.py --obj1 25544 --obj2 43013 --output results/case_001.json

# Custom conjunction time
python run_analysis.py --obj1 25544 --obj2 43013 --time "2025-06-15T12:00:00Z"
```

### Recommended test scenarios

| Scenario | obj1 | obj2 | Expected result |
|---|---|---|---|
| Active vs Active | 25544 (ISS) | 43013 (Starlink) | Shared liability ~50/50 |
| Active vs Debris | 25544 (ISS) | 37849 (Cosmos DEB) | ISS 80–90% fault (Last Clear Chance) |
| Debris vs Debris | 28353 (FY-1C DEB) | 27386 (Iridium DEB) | Split — neither could avoid |
| No conjunction risk | 25544 (ISS) | 20580 (Hubble) | NoRiskVerdict — large miss distance |

---

## Agent Specialisation

### PhysicsForensicAgent

- **Model:** Llama-3.3-70B @ temperature 0.1 (deterministic)
- **Tools:** `get_tle_data`, `propagate_orbit`, `calculate_miss_distance`, `detect_maneuver`
- **Output:** Miss distance, relative velocity, collision type, operational status of each object
- **Short-circuit:** If miss distance > `CONJUNCTION_RISK_THRESHOLD_KM` (10 km), routes to `NoRiskVerdictAgent` — no further LLM calls

### MaritimeScholarAgent

- **Model:** Llama-3.3-70B @ temperature 0.1
- **Tools:** `search_maritime_precedents`, `get_liability_convention_article`, `analyze_liability_factors`
- **Logic:** Status-aware precedent filtering — only doctrines factually applicable to the ACTIVE/DRIFTING/UNCERTAIN status pair are passed to the judge, preventing hallucinated citations

### LiabilityJudgeAgent

- **Model:** Llama-3.3-70B @ temperature 0.1 (structured JSON output)
- **Tools:** `calculate_damages_estimate`
- **Post-processing guardrails:**
  - Fault percentages forced to 0/0 when no collision occurred
  - Fault sum normalised to 100 when collision occurred
  - Treaty basis hard-overridden from retrieved article (prevents hallucination)
  - Hallucinated doctrines stripped against whitelist

### NoRiskVerdictAgent

- **Model:** None — fully deterministic, zero LLM calls
- **Trigger:** Miss distance > `CONJUNCTION_RISK_THRESHOLD_KM`
- **Output:** Immediate dismissal under Article III (no damage → no cause of action)

---

## MCP Tool Servers

### Orbital Mechanics Server (`orbital_server.py`)

| Tool | Description |
|---|---|
| `get_tle_data(norad_id)` | Fetch TLE from CelesTrak with TTL cache + circuit breaker |
| `propagate_orbit(norad_id, target_time)` | SGP4 orbit propagation to any epoch |
| `calculate_miss_distance(id_1, id_2, start_time, end_time)` | Brute-force TCA scan at 30s steps |
| `detect_maneuver(norad_id, reference_time, lookback_hours)` | Status classify via name heuristic + epoch age + BSTAR |

### Legal Database Server (`legal_server.py`)

| Tool | Description |
|---|---|
| `search_maritime_precedents(query, top_k)` | Keyword-frequency scoring across title, principle, keywords, application |
| `get_liability_convention_article(article)` | Retrieve Articles II, III, IV, V verbatim |
| `analyze_liability_factors(...)` | Rule-based liability split by status pair + warning + maneuver capability |
| `calculate_damages_estimate(...)` | Kinetic energy → severity → financial loss estimate |
| `get_all_precedents()` | Full precedent corpus |

---

## Legal Database

`data/legal_precedents.json` contains seven curated precedents:

| ID | Doctrine | When applied |
|---|---|---|
| `rhodian_jettison` | Rhodian Law on Jettison | Both objects DRIFTING — proportional shared loss |
| `derelict_vessel` | Derelict Vessel Doctrine | One object is uncontrolled / debris |
| `last_clear_chance` | Last Clear Chance Doctrine | Active object had capability + warning |
| `unlit_vessel` | Unlit Vessel Liability | Non-maneuvering object lacked transponder/signals |
| `negligent_navigation` | Negligent Navigation | Active object ignored conjunction warning |
| `absolute_liability_launch` | 1972 Convention Art. II | Surface damage — absolute liability |
| `fault_liability_space` | 1972 Convention Art. III | In-orbit collision — fault required |

To add custom precedents, append to `data/legal_precedents.json` with the same schema.

---

## Limitations

| Area | Current limitation | Known path forward |
|---|---|---|
| **TLE accuracy** | SGP4 has ~1 km positional uncertainty | Replace with SP (Special Perturbations) numerical integration |
| **Status classification** | Single-TLE heuristic — no multi-epoch velocity comparison | Historical TLE archive analysis |
| **Multi-party events** | Bilateral conjunctions only | Extend state schema and judgment schema |
| **Classified objects** | Public TLE data only — classified objects excluded | Space-Track.org authenticated access |
| **Jurisdiction** | Based on 1972 Convention only | Add national law overlays (US Commercial Space, EU, etc.) |
| **Real conjunction data** | Synthetic TCA from ±2h propagation window | Ingest CDMs from Space-Track.org directly |
| **Cold start latency** | RunPod worker cold start ~5–10s | Set `min_workers = 1` for production (adds idle cost) |

---

## Acknowledgements

- **[CelesTrak](https://celestrak.org)** — Dr. T.S. Kelso for free, real-time satellite tracking data
- **[SGP4](https://github.com/brandon-rhodes/python-sgp4)** — Brandon Rhodes for the Python SGP4 library
- **[Groq](https://groq.com)** — for ultra-low-latency Llama-3.3-70B inference
- **[LangGraph](https://github.com/langchain-ai/langgraph)** — for the multi-agent workflow orchestration framework
- **[RunPod](https://runpod.io)** — for the serverless GPU/CPU compute platform
- Space law scholars and the authors of the **1972 Outer Space Liability Convention**

---

## Contributing

Contributions are welcome. Before opening a PR:

1. Run `python test/test_system.py` — all 11 tests must pass
2. Follow existing code style — minimal diffs, preserve comments, no abbreviations in identifiers
3. For new legal precedents, include a source citation in the JSON
4. For new agent behaviours, add a corresponding test in `test_system.py`

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

> *"In orbit, every collision is preventable. The question is: who had the duty to prevent it?"*