# Quick Start Guide

Get running with Orbital Jurist in 5 minutes!

## 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## 2. Configure API Key

```bash
# Copy environment template
cp .env.example .env

# Add your Groq API key
export GROQ_API_KEY="your-key-here"
# Or edit .env file directly
```

Get a free Groq API key: https://console.groq.com/

## 3. First Analysis

```bash
# See valid satellite IDs
python run_analysis.py --list-satellites

# Run your first analysis (ISS vs Starlink)
python run_analysis.py --obj1 25544 --obj2 43013
```

## Expected Output

```
================================================================================
ORBITAL JURIST - AUTONOMOUS SPACE DEBRIS LIABILITY ARBITER
================================================================================
Case: NORAD 25544 vs NORAD 43013
Conjunction Time: 2025-12-30T12:00:00Z
================================================================================

============================================================
[PhysicsForensic] Initiating Physics Forensic Analysis
============================================================
[PhysicsForensic] Object 1: ISS (ZARYA) (NORAD 25544)
[PhysicsForensic] Object 2: STARLINK-1007 (NORAD 43013)
[PhysicsForensic] Minimum Distance: 234.5 km
[PhysicsForensic] Collision: NO
...

================================================================================
FINAL JUDGMENT
================================================================================

📋 Case Summary:
   Both satellites maintained active control with no collision occurring
   at minimum distance of 234.5 km.

⚖️  Liability Assignment:
   ISS (ZARYA): 0% fault
   STARLINK-1007: 0% fault

📖 Legal Reasoning:
   No collision occurred. Both parties operated within safe margins.
...
```

## Common Issues

### ❌ "Failed to fetch TLE data"

**Problem**: You used a non-existent satellite ID (like 99999)

**Solution**:
```bash
# Use real satellite IDs
python run_analysis.py --list-satellites

# Try ISS + Hubble
python run_analysis.py --obj1 25544 --obj2 20580
```

### ❌ "GROQ_API_KEY not set"

**Problem**: Missing API key

**Solution**:
```bash
# Set in terminal
export GROQ_API_KEY="gsk_..."

# Or edit .env file
echo "GROQ_API_KEY=gsk_..." > .env
```

### ❌ "Import Error"

**Problem**: Dependencies not installed

**Solution**:
```bash
# Reinstall
pip install -r requirements.txt

# Check Python version (need 3.9+)
python --version
```

## Test Scenarios

### 🛰️ Active Satellite vs Debris
```bash
python run_analysis.py --obj1 25544 --obj2 37849
```
Tests "last clear chance" doctrine - active satellite has duty to avoid debris.

### 🛰️ Two Active Satellites
```bash
python run_analysis.py --obj1 25544 --obj2 43013
```
Tests shared responsibility when both can maneuver.

### 🛰️ Debris vs Debris
```bash
python run_analysis.py --obj1 28353 --obj2 27386
```
Tests liability when neither object can avoid collision.

## Next Steps

### Run Tests
```bash
python test_system.py
```

### Start API Server
```bash
python main.py
# Visit http://localhost:8000/docs
```

### Save Results
```bash
python run_analysis.py --obj1 25544 --obj2 43013 --output results/case1.json
```

### Docker Deployment
```bash
docker-compose up -d
```

## Understanding the Output

The system produces three-phase analysis:

1. **Physics Forensic** (PhysicsForensic Agent)
   - Fetches satellite orbital data (TLEs)
   - Propagates orbits to conjunction time
   - Calculates miss distance and collision probability
   - Determines if satellites maneuvered

2. **Legal Analysis** (MaritimeScholar Agent)
   - Searches relevant maritime law precedents
   - Retrieves applicable space treaty articles
   - Analyzes liability factors based on object status

3. **Final Judgment** (LiabilityJudge Agent)
   - Synthesizes physical and legal evidence
   - Assigns fault percentages
   - Provides reasoning and recommendations

## Valid Satellite IDs (Quick Reference)

| ID | Name | Type |
|----|------|------|
| 25544 | ISS | Active Station |
| 20580 | Hubble | Active Telescope |
| 43013 | Starlink-1007 | Active Sat |
| 37849 | Cosmos Debris | Debris |
| 28353 | Fengyun Debris | Debris |

See `SATELLITE_IDS.md` for complete list.

## Getting Help

- 📖 **Full docs**: See `README.md`
- 🛰️ **Satellite IDs**: See `SATELLITE_IDS.md`  
- 🧪 **Testing**: Run `python test_system.py`
- 🐛 **Issues**: Check error messages for guidance
- 💡 **Tips**: Use `--list-satellites` for valid IDs

## Tips

✅ **DO:**
- Use real NORAD IDs from CelesTrak
- Start with ISS (25544) for testing
- Check `--list-satellites` for valid IDs
- Save important analyses with `--output`

❌ **DON'T:**
- Use made-up satellite IDs (like 99999)
- Forget to set GROQ_API_KEY
- Run without internet (needs TLE data)

---

**Ready to arbitrate space collisions! 🚀⚖️**