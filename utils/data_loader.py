"""
Data Loading Utilities for Orbital and Legal Data
"""
import json
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from config import settings

class CelesTrakClient:
    """Client for fetching TLE data from CelesTrak"""
    
    @staticmethod
    def _validate_tle_line(line: str, line_number: int) -> bool:
        """
        Validate TLE line format
        
        Args:
            line: TLE line to validate
            line_number: Expected line number (1 or 2)
        
        Returns:
            True if valid, False otherwise
        """
        if len(line) != 69:
            return False
        if line[0] != str(line_number):
            return False
        return True
    
    @staticmethod
    def fetch_tle(norad_id: int) -> Optional[Dict[str, str]]:
        """
        Fetch TLE for a specific NORAD catalog ID
        
        Args:
            norad_id: NORAD catalog number
        
        Returns:
            Dictionary with TLE lines or None if not found
        """
        try:
            # Use CelesTrak's TLE format endpoint (not JSON)
            # This returns traditional 3-line TLE format
            url = f"{settings.CELESTRAK_BASE_URL}?CATNR={norad_id}&FORMAT=TLE"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse TLE format (3 lines: name, line1, line2)
            lines = response.text.strip().split('\n')
            
            if len(lines) >= 3:
                name = lines[0].strip()
                line1 = lines[1].strip()
                line2 = lines[2].strip()
                
                # Validate TLE lines
                if not CelesTrakClient._validate_tle_line(line1, 1):
                    print(f"Warning: Invalid TLE line 1 format for {norad_id}")
                    return None
                
                if not CelesTrakClient._validate_tle_line(line2, 2):
                    print(f"Warning: Invalid TLE line 2 format for {norad_id}")
                    return None
                
                # Extract epoch from line1 for reference
                # TLE epoch format is in columns 19-32 of line 1
                epoch_str = line1[18:32].strip()
                
                return {
                    "name": name,
                    "line1": line1,
                    "line2": line2,
                    "epoch": epoch_str,
                    "norad_id": norad_id
                }
            elif len(lines) == 1 and ("No GP data found" in lines[0] or "No TLE data found" in lines[0]):
                return None
            else:
                print(f"Warning: Unexpected TLE response format for {norad_id}: {len(lines)} lines")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching TLE for {norad_id}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching TLE for {norad_id}: {e}")
            return None

class LegalDatabase:
    """Manager for legal precedents and maritime law database"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or settings.DATA_DIR / "legal_precedents.json"
        self.precedents = self._load_precedents()
    
    def _load_precedents(self) -> List[Dict]:
        """Load legal precedents from JSON file"""
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                return json.load(f)
        else:
            # Create default precedents
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
            
            # Create directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save default precedents
            with open(self.db_path, 'w') as f:
                json.dump(default_precedents, f, indent=2)
            
            return default_precedents
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search for relevant legal precedents
        
        Args:
            query: Search query string
            top_k: Number of top results to return
        
        Returns:
            List of matching precedents
        """
        query_lower = query.lower()
        results = []
        
        for precedent in self.precedents:
            score = 0
            
            # Check keywords
            for keyword in precedent.get("keywords", []):
                if keyword.lower() in query_lower:
                    score += 3
            
            # Check title and principle
            if any(word in precedent["title"].lower() for word in query_lower.split()):
                score += 2
            
            if any(word in precedent["principle"].lower() for word in query_lower.split()):
                score += 1
            
            if score > 0:
                results.append((score, precedent))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in results[:top_k]]
    
    def get_by_id(self, precedent_id: str) -> Optional[Dict]:
        """Get specific precedent by ID"""
        for precedent in self.precedents:
            if precedent["id"] == precedent_id:
                return precedent
        return None