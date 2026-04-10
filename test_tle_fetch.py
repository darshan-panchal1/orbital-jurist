"""
Quick test script to verify TLE fetching works
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from utils.data_loader import CelesTrakClient
from utils.logging_config import get_logger

logger = get_logger("test_tle_fetch")


def test_tle_fetch() -> None:
    """Test TLE fetching for known satellites"""
    test_satellites = [
        (25544, "ISS (ZARYA)"),
        (43013, "STARLINK-1007"),
        (20580, "HST"),
    ]

    print("Testing TLE Fetch from CelesTrak\n")
    print("=" * 70)

    for norad_id, expected_name in test_satellites:
        print(f"\nTesting NORAD {norad_id} ({expected_name})...")

        tle_data = CelesTrakClient.fetch_tle(norad_id)

        if tle_data is None:
            print(f"  ✗ FAILED - No TLE data returned")
            continue

        print(f"  ✓ Name: {tle_data['name']}")
        print(f"  ✓ Epoch: {tle_data['epoch']}")
        print(f"  ✓ Line 1 length: {len(tle_data['line1'])} chars")
        print(f"  ✓ Line 2 length: {len(tle_data['line2'])} chars")

        # Validate TLE format
        if len(tle_data["line1"]) == 69 and tle_data["line1"][0] == "1":
            print(f"  ✓ Line 1 format valid")
        else:
            print(f"  ✗ Line 1 format invalid")

        if len(tle_data["line2"]) == 69 and tle_data["line2"][0] == "2":
            print(f"  ✓ Line 2 format valid")
        else:
            print(f"  ✗ Line 2 format invalid")

        # Try to parse with SGP4
        try:
            from sgp4.api import Satrec
            sat = Satrec.twoline2rv(tle_data["line1"], tle_data["line2"])
            print(f"  ✓ SGP4 parsing successful")
        except Exception as e:
            print(f"  ✗ SGP4 parsing failed: {e}")

        # Test circuit breaker status
        try:
            from utils.resilience import all_circuit_breaker_statuses
            statuses = all_circuit_breaker_statuses()
            celestrak_status = next(
                (s for s in statuses if s["name"] == "celestrak"), None
            )
            if celestrak_status:
                print(f"  ✓ Circuit breaker: {celestrak_status['state']}")
        except Exception:
            pass

    print("\n" + "=" * 70)
    print("TLE fetch test complete!")


if __name__ == "__main__":
    test_tle_fetch()