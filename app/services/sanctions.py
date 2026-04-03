"""
Sanctions Screening Service.

Uses the OFAC SDN (Specially Designated Nationals) list for free sanctions screening.
https://www.treasury.gov/ofac/downloads/sdn.xml
"""

import hashlib
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import xml.etree.ElementTree as ET

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class SanctionsMatch:
    """A match result from sanctions screening."""
    
    def __init__(
        self,
        score: float,
        name: str,
        sdn_type: str,
        program: str,
        uid: str,
        remarks: Optional[str] = None,
    ):
        self.score = score  # 0.0 - 1.0
        self.name = name
        self.sdn_type = sdn_type  # Individual, Entity
        self.program = program
        self.uid = uid
        self.remarks = remarks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "name": self.name,
            "sdn_type": self.sdn_type,
            "program": self.program,
            "uid": self.uid,
            "remarks": self.remarks,
        }


class SanctionsService:
    """
    Sanctions screening using OFAC SDN list.
    
    The SDN list is downloaded and cached locally.
    Names are normalized and compared using fuzzy matching.
    """
    
    OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
    CACHE_DIR = Path("data/sanctions")
    SDN_FILE = CACHE_DIR / "sdn.xml"
    CACHE_DURATION = timedelta(days=1)  # Re-download daily
    
    def __init__(self):
        self.sdn_entries: List[Dict[str, Any]] = []
        self.last_updated: Optional[datetime] = None
        self.initialized = False
        
        # Create cache directory
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Convert to lowercase
        name = name.lower()
        # Remove special characters
        name = re.sub(r"[^\w\s]", "", name)
        # Normalize whitespace
        name = " ".join(name.split())
        return name
    
    def _compute_similarity(self, name1: str, name2: str) -> float:
        """
        Compute similarity between two names.
        
        Uses a simple token-based approach:
        - Normalize both names
        - Split into tokens
        - Calculate Jaccard similarity
        """
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)
        
        # Exact match
        if norm1 == norm2:
            return 1.0
        
        # Token-based similarity
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        jaccard = intersection / union if union > 0 else 0.0
        
        # Also check for substring match on individual tokens
        substring_matches = 0
        for t1 in tokens1:
            for t2 in tokens2:
                if len(t1) >= 3 and len(t2) >= 3:
                    if t1 in t2 or t2 in t1:
                        substring_matches += 1
        
        # Combine scores
        substring_score = min(substring_matches / max(len(tokens1), len(tokens2)), 0.5)
        
        return min(jaccard + substring_score, 1.0)
    
    async def _download_sdn_list(self) -> bool:
        """Download OFAC SDN list."""
        try:
            logger.info("Downloading OFAC SDN list...")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.OFAC_SDN_URL)
                response.raise_for_status()
            
            # Save to cache
            with open(self.SDN_FILE, "wb") as f:
                f.write(response.content)
            
            logger.info(f"SDN list downloaded: {len(response.content)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download SDN list: {e}")
            return False
    
    def _parse_sdn_xml(self) -> List[Dict[str, Any]]:
        """Parse the SDN XML file."""
        entries = []
        
        try:
            tree = ET.parse(self.SDN_FILE)
            root = tree.getroot()
            
            # Handle namespace
            ns = {"sdn": "http://tempuri.org/sdnList.xsd"}
            
            # Try with namespace first
            sdn_entries = root.findall(".//sdn:sdnEntry", ns)
            if not sdn_entries:
                # Try without namespace
                sdn_entries = root.findall(".//sdnEntry")
            
            for entry in sdn_entries:
                # Get UID
                uid_elem = entry.find("sdn:uid", ns) or entry.find("uid")
                uid = uid_elem.text if uid_elem is not None else ""
                
                # Get name parts
                first_name = ""
                last_name = ""
                
                first_elem = entry.find("sdn:firstName", ns) or entry.find("firstName")
                last_elem = entry.find("sdn:lastName", ns) or entry.find("lastName")
                
                if first_elem is not None and first_elem.text:
                    first_name = first_elem.text
                if last_elem is not None and last_elem.text:
                    last_name = last_elem.text
                
                full_name = f"{first_name} {last_name}".strip()
                if not full_name:
                    continue
                
                # Get type
                type_elem = entry.find("sdn:sdnType", ns) or entry.find("sdnType")
                sdn_type = type_elem.text if type_elem is not None else "Unknown"
                
                # Get program
                program_elem = entry.find("sdn:programList/sdn:program", ns) or entry.find("programList/program")
                program = program_elem.text if program_elem is not None else ""
                
                # Get remarks
                remarks_elem = entry.find("sdn:remarks", ns) or entry.find("remarks")
                remarks = remarks_elem.text if remarks_elem is not None else None
                
                # Get aliases
                aliases = []
                aka_list = entry.findall("sdn:akaList/sdn:aka", ns) or entry.findall("akaList/aka")
                for aka in aka_list:
                    aka_first = aka.find("sdn:firstName", ns) or aka.find("firstName")
                    aka_last = aka.find("sdn:lastName", ns) or aka.find("lastName")
                    
                    aka_name_parts = []
                    if aka_first is not None and aka_first.text:
                        aka_name_parts.append(aka_first.text)
                    if aka_last is not None and aka_last.text:
                        aka_name_parts.append(aka_last.text)
                    
                    if aka_name_parts:
                        aliases.append(" ".join(aka_name_parts))
                
                entries.append({
                    "uid": uid,
                    "name": full_name,
                    "aliases": aliases,
                    "type": sdn_type,
                    "program": program,
                    "remarks": remarks,
                })
            
            logger.info(f"Parsed {len(entries)} SDN entries")
            
        except Exception as e:
            logger.error(f"Failed to parse SDN XML: {e}")
        
        return entries
    
    async def initialize(self, force_download: bool = False) -> bool:
        """
        Initialize the sanctions service.
        
        Downloads the SDN list if needed and parses it.
        """
        try:
            # Check if we need to download
            should_download = force_download
            
            if not self.SDN_FILE.exists():
                should_download = True
            elif self.last_updated is None:
                # Check file modification time
                mtime = datetime.fromtimestamp(self.SDN_FILE.stat().st_mtime)
                if datetime.utcnow() - mtime > self.CACHE_DURATION:
                    should_download = True
            
            if should_download:
                success = await self._download_sdn_list()
                if not success and not self.SDN_FILE.exists():
                    logger.warning("SDN list unavailable, sanctions screening disabled")
                    return False
            
            # Parse the list
            self.sdn_entries = self._parse_sdn_xml()
            self.last_updated = datetime.utcnow()
            self.initialized = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sanctions service: {e}")
            return False
    
    async def screen_name(
        self,
        name: str,
        threshold: float = 0.8,
    ) -> List[SanctionsMatch]:
        """
        Screen a name against the OFAC SDN list.
        
        Args:
            name: The name to screen
            threshold: Minimum similarity score (0.0 - 1.0) for a match
            
        Returns:
            List of matches above the threshold, sorted by score descending
        """
        if not self.initialized:
            await self.initialize()
        
        if not self.sdn_entries:
            logger.warning("No SDN entries loaded, skipping screening")
            return []
        
        matches = []
        
        for entry in self.sdn_entries:
            # Check main name
            score = self._compute_similarity(name, entry["name"])
            
            if score >= threshold:
                matches.append(SanctionsMatch(
                    score=score,
                    name=entry["name"],
                    sdn_type=entry["type"],
                    program=entry["program"],
                    uid=entry["uid"],
                    remarks=entry["remarks"],
                ))
                continue
            
            # Check aliases
            for alias in entry.get("aliases", []):
                score = self._compute_similarity(name, alias)
                if score >= threshold:
                    matches.append(SanctionsMatch(
                        score=score,
                        name=f"{entry['name']} (alias: {alias})",
                        sdn_type=entry["type"],
                        program=entry["program"],
                        uid=entry["uid"],
                        remarks=entry["remarks"],
                    ))
                    break
        
        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        
        return matches
    
    async def screen_entity(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        full_name: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        country: Optional[str] = None,
        threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Screen an entity (person or organization) against sanctions lists.
        
        Args:
            first_name: First name
            last_name: Last name
            full_name: Full name (used if first/last not provided)
            date_of_birth: DOB for additional verification
            country: Country code for risk assessment
            threshold: Minimum similarity for a match
            
        Returns:
            {
                "clear": True/False,
                "matches": [...],
                "checked_at": "...",
                "risk_flags": [...]
            }
        """
        # Construct name to screen
        if full_name:
            name = full_name
        elif first_name and last_name:
            name = f"{first_name} {last_name}"
        elif last_name:
            name = last_name
        else:
            return {
                "clear": None,
                "error": "No name provided",
                "checked_at": datetime.utcnow().isoformat(),
            }
        
        matches = await self.screen_name(name, threshold)
        
        risk_flags = []
        
        # Check high-risk countries
        HIGH_RISK_COUNTRIES = {"KP", "IR", "SY", "CU", "RU", "BY", "VE"}
        if country and country.upper() in HIGH_RISK_COUNTRIES:
            risk_flags.append(f"High-risk country: {country}")
        
        return {
            "clear": len(matches) == 0,
            "matches": [m.to_dict() for m in matches],
            "checked_at": datetime.utcnow().isoformat(),
            "risk_flags": risk_flags,
            "name_screened": name,
        }


# Singleton instance
sanctions_service = SanctionsService()
