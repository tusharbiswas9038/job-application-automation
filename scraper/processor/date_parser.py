# processor/date_parser.py
import re
import logging
from datetime import datetime, date, timedelta
from typing import Optional
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)


class DateParser:
    """Parse dates from various formats [web:39][web:40]"""
    
    # Relative date patterns
    RELATIVE_PATTERNS = {
        r'(\d+)\s*(?:minute|min)s?\s*ago': lambda m: timedelta(minutes=int(m.group(1))),
        r'(\d+)\s*(?:hour|hr)s?\s*ago': lambda m: timedelta(hours=int(m.group(1))),
        r'(\d+)\s*days?\s*ago': lambda m: timedelta(days=int(m.group(1))),
        r'(\d+)\s*weeks?\s*ago': lambda m: timedelta(weeks=int(m.group(1))),
        r'(\d+)\s*months?\s*ago': lambda m: timedelta(days=int(m.group(1)) * 30),
        r'yesterday': lambda m: timedelta(days=1),
        r'today': lambda m: timedelta(days=0),
    }
    
    def parse_date(self, date_string: Optional[str]) -> Optional[date]:
        """
        Parse date from various formats [web:40][web:42]
        
        Supported formats:
        - ISO 8601: 2024-12-28
        - American: 12/28/2024
        - European: 28/12/2024
        - Natural: Dec 28, 2024
        - Relative: "2 days ago", "1 week ago"
        
        Args:
            date_string: Date string to parse
        
        Returns:
            date object or None if parsing fails
        """
        if not date_string:
            return None
        
        date_string = date_string.strip()
        
        # Try relative dates first
        for pattern, delta_func in self.RELATIVE_PATTERNS.items():
            match = re.search(pattern, date_string, re.IGNORECASE)
            if match:
                delta = delta_func(match)
                return (datetime.now() - delta).date()
        
        # Try dateutil parser (handles most formats) [web:40][web:46]
        try:
            parsed = dateutil_parser.parse(date_string, fuzzy=True)
            return parsed.date()
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse date '{date_string}': {e}")
            return None
    
    def normalize_date_range(self, start_str: Optional[str], end_str: Optional[str]) -> tuple[Optional[date], Optional[date]]:
        """
        Parse and normalize date range
        
        Args:
            start_str: Start date string
            end_str: End date string
        
        Returns:
            Tuple of (start_date, end_date)
        """
        start_date = self.parse_date(start_str)
        end_date = self.parse_date(end_str)
        
        # Validate range
        if start_date and end_date:
            if start_date > end_date:
                logger.warning(f"Invalid date range: {start_date} > {end_date}, swapping")
                start_date, end_date = end_date, start_date
        
        return start_date, end_date

