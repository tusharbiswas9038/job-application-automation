# processor/keyword_extractor.py
import re
import logging
from typing import Set, List, Dict
from collections import Counter

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extract Kafka-related keywords and calculate relevance"""
    
    def __init__(self, required_keywords: Set[str], bonus_keywords: Set[str]):
        """
        Args:
            required_keywords: Core Kafka keywords
            bonus_keywords: Additional relevant keywords
        """
        self.required_keywords = {kw.lower() for kw in required_keywords}
        self.bonus_keywords = {kw.lower() for kw in bonus_keywords}
        self.all_keywords = self.required_keywords | self.bonus_keywords
        
        # Compile patterns for efficient matching
        self.keyword_patterns = {
            kw: re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in self.all_keywords
        }
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract Kafka-related keywords from text
        
        Args:
            text: Job description text
        
        Returns:
            List of found keywords
        """
        if not text:
            return []
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword, pattern in self.keyword_patterns.items():
            if pattern.search(text):
                found_keywords.append(keyword)
        
        return found_keywords
    
    def calculate_relevance_score(self, text: str, title: str) -> float:
        """
        Calculate Kafka relevance score (0-100)
        
        Scoring:
        - Required keyword in title: +30 points
        - Required keywords in description: +10 each (max 40)
        - Bonus keywords: +2 each (max 30)
        
        Args:
            text: Job description
            title: Job title
        
        Returns:
            Score from 0-100
        """
        score = 0.0
        
        text_lower = text.lower()
        title_lower = title.lower()
        
        # Check title for required keywords
        title_has_kafka = any(kw in title_lower for kw in self.required_keywords)
        if title_has_kafka:
            score += 30
        
        # Count required keywords in description
        required_count = sum(
            1 for kw in self.required_keywords
            if self.keyword_patterns[kw].search(text)
        )
        score += min(required_count * 10, 40)
        
        # Count bonus keywords
        bonus_count = sum(
            1 for kw in self.bonus_keywords
            if self.keyword_patterns[kw].search(text)
        )
        score += min(bonus_count * 2, 30)
        
        return min(score, 100.0)
    
    def get_keyword_density(self, text: str) -> Dict[str, int]:
        """
        Get keyword frequency counts
        
        Args:
            text: Job description
        
        Returns:
            Dict mapping keywords to counts
        """
        text_lower = text.lower()
        density = {}
        
        for keyword, pattern in self.keyword_patterns.items():
            matches = pattern.findall(text)
            if matches:
                density[keyword] = len(matches)
        
        return density

