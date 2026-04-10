"""
Data Loading Utilities for Orbital and Legal Data
"""
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

import requests
from cachetools import TTLCache

from config import settings
from utils.logging_config import get_logger
from utils.resilience import (
    CircuitBreakerOpenError,
    celestrak_retry,
    get_circuit_breaker,
)

logger = get_logger("data_loader")

# ── TLE TTL cache (thread-safe) ───────────────────────────────────────────────
_tle_cache: TTLCache = TTLCache(maxsize=512, ttl=settings.CELESTRAK_CACHE_TTL_S)
_tle_cache_lock = threading.Lock()

# ── Circuit breaker for CelesTrak ─────────────────────────────────────────────
_celestrak_cb = get_circuit_breaker(
    "celestrak",
    failure_threshold=settings.CB_CELESTRAK_FAILURE_THRESHOLD,
    recovery_timeout=settings.CB_CELESTRAK_RECOVERY_TIMEOUT_S,
    expected_exception=requests.exceptions.RequestException,
)


class CelesTrakClient:

    @staticmethod
    def _validate_tle_line(line: str, expected_num: int) -> bool:
        return len(line) == 69 and line[0] == str(expected_num)

    @staticmethod
    @celestrak_retry()
    def _fetch_raw(norad_id: int) -> Optional[str]:
        """Raw HTTP fetch with retry (called inside circuit breaker)."""
        url = f"{settings.CELESTRAK_BASE_URL}?CATNR={norad_id}&FORMAT=TLE"
        resp = requests.get(url, timeout=settings.CELESTRAK_TIMEOUT_S)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def fetch_tle(norad_id: int) -> Optional[Dict[str, str]]:
        """
        Fetch TLE with:
        - TTL cache (1 h by default)
        - Retry (3 attempts, exponential back-off)
        - Circuit breaker (opens after 5 consecutive failures)
        """
        # Cache look-up
        with _tle_cache_lock:
            cached = _tle_cache.get(norad_id)
        if cached:
            logger.debug("TLE cache hit", extra={"norad_id": norad_id})
            return cached

        # Fetch via circuit breaker
        try:
            raw = _celestrak_cb.call(CelesTrakClient._fetch_raw, norad_id)
        except CircuitBreakerOpenError as exc:
            logger.error(
                "CelesTrak circuit open — rejecting TLE fetch",
                extra={"norad_id": norad_id, "error": str(exc)},
            )
            return None
        except Exception as exc:
            logger.error(
                "CelesTrak fetch failed after retries",
                extra={"norad_id": norad_id, "error": str(exc)},
            )
            return None

        if raw is None:
            return None

        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            logger.warning(
                "Unexpected TLE response line count",
                extra={"norad_id": norad_id, "lines": len(lines)},
            )
            return None

        name, line1, line2 = lines[0], lines[1], lines[2]

        if not CelesTrakClient._validate_tle_line(line1, 1):
            logger.warning("Invalid TLE line 1", extra={"norad_id": norad_id})
            return None
        if not CelesTrakClient._validate_tle_line(line2, 2):
            logger.warning("Invalid TLE line 2", extra={"norad_id": norad_id})
            return None

        result: Dict[str, str] = {
            "name":     name,
            "line1":    line1,
            "line2":    line2,
            "epoch":    line1[18:32].strip(),
            "norad_id": norad_id,
        }

        with _tle_cache_lock:
            _tle_cache[norad_id] = result

        logger.info("TLE fetched and cached", extra={"norad_id": norad_id, "sat_name": name})
        return result


class LegalDatabase:
    """
    In-memory legal precedent store with keyword scoring.
    """

    def __init__(self, db_path: Path = None):
        self.db_path   = db_path or settings.LEGAL_DB_PATH
        self.precedents: List[Dict] = self._load_precedents()

    def _load_precedents(self) -> List[Dict]:
        if self.db_path.exists():
            with open(self.db_path) as f:
                data = json.load(f)
            logger.info("Legal DB loaded", extra={"count": len(data)})
            return data

        logger.warning("Legal DB not found — writing defaults",
                       extra={"path": str(self.db_path)})
        defaults = self._default_precedents()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(defaults, f, indent=2)
        return defaults

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Keyword-frequency scoring over title + principle + keywords + application.
        """
        q_tokens = set(query.lower().split())
        scored = []

        for p in self.precedents:
            score = 0.0
            for kw in p.get("keywords", []):
                kw_tokens = set(kw.lower().split())
                score += 3.0 * len(q_tokens & kw_tokens)
            score += 2.0 * len(q_tokens & set(p["title"].lower().split()))
            score += 1.5 * len(q_tokens & set(p["principle"].lower().split()))
            score += 1.0 * len(q_tokens & set(p.get("application", "").lower().split()))
            if score > 0:
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:top_k]]

    def get_by_id(self, pid: str) -> Optional[Dict]:
        return next((p for p in self.precedents if p["id"] == pid), None)

    @staticmethod
    def _default_precedents() -> List[Dict]:
        default_precedents = [
            {
                "id": "rhodian_jettison",
                "title": "The Rhodian Law on Jettison",
                "principle": "Losses incurred for the common good must be shared proportionally",
                "application": "When debris is intentionally released to save other satellites, liability is distributed",
                "keywords": ["jettison", "common good", "proportional liability"]
            },
            {
                "id": "derelict_vessel",
                "title": "Derelict Vessel Doctrine",
                "principle": "An abandoned vessel drifting without control bears reduced liability",
                "application": "Non-maneuvering debris has limited fault in collisions",
                "keywords": ["derelict", "abandoned", "drifting", "uncontrolled"]
            },
            {
                "id": "last_clear_chance",
                "title": "Last Clear Chance Doctrine",
                "principle": "The party with final opportunity to avoid collision bears greater responsibility",
                "application": "Active satellite with ability to maneuver has duty to avoid known debris",
                "keywords": ["last chance", "avoidance", "active control", "duty"]
            },
            {
                "id": "unlit_vessel",
                "title": "Unlit Vessel Liability",
                "principle": "Vessels without proper signals/lights share fault in collisions",
                "application": "Dead satellites without transponders bear partial fault",
                "keywords": ["unlit", "signals", "transponder", "identification"]
            },
            {
                "id": "negligent_navigation",
                "title": "Negligent Navigation",
                "principle": "Failure to follow standard navigation procedures constitutes negligence",
                "application": "Ignoring conjunction warnings or failing to maneuver when able",
                "keywords": ["negligence", "navigation", "warning", "duty of care"]
            },
            {
                "id": "absolute_liability_launch",
                "title": "1972 Liability Convention - Article II",
                "principle": "Launching state is absolutely liable for damage on Earth's surface or to aircraft",
                "application": "Direct liability for damage caused by space object to ground or air",
                "keywords": ["absolute liability", "launching state", "surface damage"]
            },
            {
                "id": "fault_liability_space",
                "title": "1972 Liability Convention - Article III",
                "principle": "Liability for damage in space requires proof of fault",
                "application": "In-orbit collisions require establishing negligence or fault",
                "keywords": ["fault", "in-orbit", "negligence", "space collision"]
            }
        ]
        return default_precedents