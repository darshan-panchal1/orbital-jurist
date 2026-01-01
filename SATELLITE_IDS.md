# Valid Satellite IDs for Testing

This document lists real, trackable satellites you can use to test the Orbital Jurist system.

## Quick Command

```bash
# Show this list from CLI
python run_analysis.py --list-satellites
```

## Common Test Satellites

### Active Satellites

| NORAD ID | Name | Type | Description |
|----------|------|------|-------------|
| 25544 | ISS (ZARYA) | Space Station | International Space Station |
| 20580 | HST | Space Telescope | Hubble Space Telescope |
| 43013 | STARLINK-1007 | LEO Constellation | SpaceX Starlink satellite |
| 41765 | STARLINK-1341 | LEO Constellation | SpaceX Starlink satellite |
| 43947 | STARLINK-1600 | LEO Constellation | SpaceX Starlink satellite |
| 48274 | STARLINK-3042 | LEO Constellation | SpaceX Starlink satellite |
| 27424 | ENVISAT | Earth Observation | European Space Agency satellite |
| 43175 | BREEZE-M R/B | Rocket Body | Russian upper stage |

### Debris Objects

| NORAD ID | Name | Type | Description |
|----------|------|------|-------------|
| 37849 | COSMOS 2251 DEB | Debris | Russian satellite debris |
| 28353 | FENGYUN 1C DEB | Debris | Chinese ASAT test debris |
| 27386 | IRIDIUM 33 DEB | Debris | Iridium collision debris |
| 40128 | CZ-4B R/B | Rocket Body | Chinese rocket body |
| 33278 | IRIDIUM 33 DEB | Debris | Collision debris fragment |

## Example Test Scenarios

### Scenario 1: Active vs Active
Test two maneuverable satellites that can both avoid collisions.

```bash
# ISS vs Starlink
python run_analysis.py --obj1 25544 --obj2 43013

# Expected: Both satellites active, shared liability
```

### Scenario 2: Active vs Debris
Test an active satellite encountering uncontrolled debris.

```bash
# ISS vs Russian debris
python run_analysis.py --obj1 25544 --obj2 37849

# Expected: Active satellite has "last clear chance" duty
```

### Scenario 3: Debris vs Debris
Test two uncontrolled objects colliding.

```bash
# Fengyun debris vs Iridium debris
python run_analysis.py --obj1 28353 --obj2 27386

# Expected: Neither had capability to avoid, shared liability
```

### Scenario 4: Similar Orbits (Close Approach)
Test satellites in similar orbits that might have close approaches.

```bash
# Two Starlink satellites in same shell
python run_analysis.py --obj1 43013 --obj2 41765

# Expected: Minimal miss distance, collision analysis
```

### Scenario 5: Different Orbital Regimes
Test satellites in different orbits (low chance of conjunction).

```bash
# LEO (ISS) vs essentially LEO but different altitude
python run_analysis.py --obj1 25544 --obj2 20580

# Expected: Large miss distance, no collision risk
```

## Finding More Satellites

### Option 1: CelesTrak Search
Visit [CelesTrak SATCAT Search](https://celestrak.org/satcat/search.php) to find NORAD IDs by:
- Satellite name
- Launch date
- Country
- Orbital parameters

### Option 2: Space-Track.org
For authenticated access to the full catalog:
1. Register at [Space-Track.org](https://www.space-track.org)
2. Search by name, NORAD ID, or other criteria
3. Download TLE data for analysis

### Option 3: N2YO.com
Live tracking and historical data:
- [N2YO ISS Tracking](https://www.n2yo.com/satellite/?s=25544)
- Search by name or NORAD ID
- See real-time position and orbit

## Validation Rules

The system validates satellite IDs:
- **Warning at ID > 90000**: May not exist in database
- **Error on TLE fetch failure**: Invalid or non-existent ID
- **Suggestion prompt**: Shows valid test IDs

## Common Errors

### Error: "Failed to fetch TLE data"
**Cause**: Satellite ID doesn't exist in CelesTrak database

**Solution**: 
```bash
# Check valid IDs
python run_analysis.py --list-satellites

# Use a known valid ID
python run_analysis.py --obj1 25544 --obj2 43013
```

### Error: "Could not fetch TLE for NORAD ID XXXXX"
**Cause**: Network issue or satellite recently deorbited

**Solution**:
- Check internet connection
- Try a different satellite ID
- Verify ID exists on CelesTrak website

## Testing Tips

1. **Start with ISS (25544)**: Always trackable, always available
2. **Use debris objects for "drifting" status**: They won't maneuver
3. **Use Starlink for "active" status**: They actively maintain orbits
4. **Mix active + debris**: Tests the "last clear chance" doctrine
5. **Same orbital shell**: Higher chance of close approaches

## Notes

- TLE data is updated regularly on CelesTrak (typically daily)
- Satellite IDs are assigned sequentially by NORAD/Space Force
- Deorbited satellites may eventually be removed from the catalog
- Some classified satellites have IDs but no public TLE data
- The system caches TLE data during execution to reduce API calls

## Updates

This list was current as of December 2025. For the most up-to-date information:
- Run `python run_analysis.py --list-satellites`
- Visit [CelesTrak](https://celestrak.org)
- Check [Space-Track.org](https://www.space-track.org)

---

**Need more satellites?** The system works with any valid NORAD catalog ID from CelesTrak!