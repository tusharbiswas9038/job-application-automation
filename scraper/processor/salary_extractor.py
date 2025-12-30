# processor/salary_extractor.py
import re
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class SalaryExtractor:
    """Extract salary information from job descriptions [web:44][web:47]"""
    
    # Salary patterns [web:44]
    SALARY_PATTERNS = [
        # Range with $ and "to"/"and"
        r'\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)\s*(?:to|-|and)\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)',
        
        # Single salary with modifiers
        r'\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)\s*(?:per|/)\s*(year|hour|month)',
        
        # K format (e.g., $100K - $150K)
        r'\$\s*([0-9]+)K?\s*(?:to|-|and)\s*\$?\s*([0-9]+)K',
        
        # Without $
        r'(?:salary|compensation|pay).*?([0-9]{1,3}(?:,[0-9]{3})+)\s*(?:to|-)\s*([0-9]{1,3}(?:,[0-9]{3})+)',
    ]
    
    # Period indicators
    PERIOD_PATTERNS = {
        'yearly': r'(?:per year|annually|annual|/year|/yr|p\.?a\.?)',
        'hourly': r'(?:per hour|hourly|/hour|/hr)',
        'monthly': r'(?:per month|monthly|/month|/mo)',
    }
    
    def extract_salary(self, text: str) -> Dict[str, Optional[float]]:
        """
        Extract salary information from text [web:44]
        
        Args:
            text: Job description text
        
        Returns:
            Dict with keys: min, max, currency, period
        """
        if not text:
            return self._empty_salary()
        
        text_lower = text.lower()
        
        # Try each pattern
        for pattern in self.SALARY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Extract numbers
                    if len(match.groups()) >= 2:
                        min_val = self._parse_salary_number(match.group(1))
                        max_val = self._parse_salary_number(match.group(2))
                    else:
                        min_val = self._parse_salary_number(match.group(1))
                        max_val = None
                    
                    # Detect period
                    period = self._detect_period(text_lower, match.start(), match.end())
                    
                    # Validate and normalize
                    if min_val and max_val:
                        # Ensure min < max
                        if min_val > max_val:
                            min_val, max_val = max_val, min_val
                        
                        # If values look like K format without K indicator
                        if min_val < 1000 and max_val < 1000:
                            min_val *= 1000
                            max_val *= 1000
                    
                    return {
                        'min': min_val,
                        'max': max_val,
                        'currency': 'USD',  # Default to USD, can be enhanced
                        'period': period
                    }
                
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse salary from match: {e}")
                    continue
        
        return self._empty_salary()
    
    def _parse_salary_number(self, salary_str: str) -> Optional[float]:
        """Parse salary number from string"""
        if not salary_str:
            return None
        
        # Remove commas and whitespace
        salary_str = salary_str.replace(',', '').replace(' ', '')
        
        # Check for K suffix
        if salary_str.upper().endswith('K'):
            salary_str = salary_str[:-1]
            multiplier = 1000
        else:
            multiplier = 1
        
        try:
            return float(salary_str) * multiplier
        except ValueError:
            return None
    
    def _detect_period(self, text: str, start: int, end: int) -> str:
        """Detect salary period from context around match"""
        # Look in window around the match
        window_size = 50
        context = text[max(0, start - window_size):min(len(text), end + window_size)]
        
        for period, pattern in self.PERIOD_PATTERNS.items():
            if re.search(pattern, context, re.IGNORECASE):
                return period
        
        # Default to yearly for high values
        return 'yearly'
    
    def _empty_salary(self) -> Dict[str, Optional[float]]:
        """Return empty salary dict"""
        return {
            'min': None,
            'max': None,
            'currency': None,
            'period': None
        }
    
    def validate_salary(self, salary: Dict) -> bool:
        """
        Validate salary makes sense for Kafka Admin role
        
        Typical Kafka Admin salaries: $80K - $200K/year [web:11]
        """
        if not salary['min']:
            return True  # No salary is valid
        
        min_val = salary['min']
        period = salary['period']
        
        # Convert to yearly for validation
        if period == 'hourly':
            min_val *= 2080  # 40 hours * 52 weeks
        elif period == 'monthly':
            min_val *= 12
        
        # Sanity checks
        if min_val < 30000 or min_val > 500000:
            logger.warning(f"Suspicious salary value: ${min_val}")
            return False
        
        return True

