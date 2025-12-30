# processor/location_normalizer.py
import re
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedLocation:
    """Parsed location components"""
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    remote_type: Optional[str] = None
    normalized: str = ""


class LocationNormalizer:
    """Normalize location strings to structured format"""
    
    # Remote indicators
    REMOTE_PATTERNS = {
        'remote': r'\b(?:remote|work from home|wfh|distributed|anywhere)\b',
        'hybrid': r'\b(?:hybrid|flexible|remote/onsite)\b',
        'onsite': r'\b(?:onsite|on-site|in-office|office-based)\b',
    }
    
    # Country patterns
    COUNTRY_PATTERNS = {
        'United States': r'\b(?:USA?|United States|U\.S\.A?\.?)\b',
        'Canada': r'\bCanada\b',
        'United Kingdom': r'\b(?:UK|United Kingdom|Britain)\b',
        'India': r'\bIndia\b',
        'Germany': r'\bGermany\b',
    }
    
    # US state abbreviation pattern
    US_STATE_ABBR_PATTERN = re.compile(r'\b([A-Z]{2})\b')
    
    # Common location formats
    LOCATION_FORMATS = [
        # City, State format
        r'^([A-Za-z\s]+),\s*([A-Z]{2})$',
        # City, State, Country
        r'^([A-Za-z\s]+),\s*([A-Z]{2}),\s*(USA?|United States)$',
        # City, Country
        r'^([A-Za-z\s]+),\s*([A-Za-z\s]+)$',
    ]
    
    def __init__(self, us_states: Dict[str, str], location_aliases: Dict[str, str]):
        """
        Args:
            us_states: Dict mapping state names to abbreviations
            location_aliases: Dict of common location aliases
        """
        self.us_states = us_states
        self.us_states_reverse = {v: k.title() for k, v in us_states.items()}
        self.location_aliases = {k.lower(): v for k, v in location_aliases.items()}
    
    def normalize_location(self, location: str) -> ParsedLocation:
        """
        Normalize location string to structured format
        
        Args:
            location: Raw location string
        
        Returns:
            ParsedLocation with parsed components
        """
        if not location:
            return ParsedLocation(normalized="Unknown")
        
        original = location
        location = location.strip()
        
        # Check for remote indicators first
        remote_type = self._detect_remote_type(location)
        
        # Clean common suffixes
        location = re.sub(r'\(.*?\)', '', location)  # Remove parentheses
        location = location.replace(' Metropolitan Area', '')
        location = location.replace(' Area', '')
        location = location.strip()
        
        # Check aliases
        location_lower = location.lower()
        if location_lower in self.location_aliases:
            location = self.location_aliases[location_lower]
        
        # Try to parse structured formats
        parsed = self._parse_structured_location(location)
        
        if parsed.city:
            parsed.remote_type = remote_type
            return parsed
        
        # Fallback: treat as city or general location
        country = self._detect_country(original)
        
        return ParsedLocation(
            city=location,
            country=country or "United States",
            remote_type=remote_type,
            normalized=location
        )
    
    def _parse_structured_location(self, location: str) -> ParsedLocation:
        """Parse location in structured format (City, State)"""
        
        # Try: City, State
        match = re.match(r'^([^,]+),\s*([A-Z]{2})$', location.strip())
        if match:
            city = match.group(1).strip()
            state_abbr = match.group(2)
            state_name = self.us_states_reverse.get(state_abbr, state_abbr)
            
            return ParsedLocation(
                city=city,
                state=state_abbr,
                country="United States",
                normalized=f"{city}, {state_abbr}"
            )
        
        # Try: City, State, Country
        match = re.match(r'^([^,]+),\s*([A-Z]{2}),\s*(.*?)$', location.strip())
        if match:
            city = match.group(1).strip()
            state_abbr = match.group(2)
            country = match.group(3).strip()
            
            return ParsedLocation(
                city=city,
                state=state_abbr,
                country=country,
                normalized=f"{city}, {state_abbr}"
            )
        
        # Try: City, Country
        match = re.match(r'^([^,]+),\s*([^,]+)$', location.strip())
        if match:
            city = match.group(1).strip()
            potential_country = match.group(2).strip()
            
            # Check if second part is a country
            if potential_country in self.COUNTRY_PATTERNS or len(potential_country) > 10:
                return ParsedLocation(
                    city=city,
                    country=potential_country,
                    normalized=f"{city}, {potential_country}"
                )
            # Might be State name spelled out
            elif potential_country.lower() in self.us_states:
                state_abbr = self.us_states[potential_country.lower()]
                return ParsedLocation(
                    city=city,
                    state=state_abbr,
                    country="United States",
                    normalized=f"{city}, {state_abbr}"
                )
        
        return ParsedLocation(normalized=location)
    
    def _detect_remote_type(self, text: str) -> Optional[str]:
        """Detect if job is remote/hybrid/onsite"""
        text_lower = text.lower()
        
        # Check in priority order (remote > hybrid > onsite)
        for remote_type, pattern in self.REMOTE_PATTERNS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return remote_type
        
        return None
    
    def _detect_country(self, text: str) -> Optional[str]:
        """Detect country from text"""
        for country, pattern in self.COUNTRY_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return country
        
        return None

