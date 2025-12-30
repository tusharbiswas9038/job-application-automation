# resume/ats/matcher.py
import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from difflib import SequenceMatcher
import nltk
from nltk.stem import PorterStemmer

from resume.models import ParsedResume, BulletPoint
from resume.ats.models import Keyword, KeywordMatch, MatchType

logger = logging.getLogger(__name__)


class KeywordMatcher:
    """
    Match keywords from JD against resume content
    """
    
    def __init__(self, fuzzy_threshold: float = 0.85):
        """
        Args:
            fuzzy_threshold: Minimum similarity for fuzzy matching (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.stemmer = PorterStemmer()
    
    def match_keywords(
        self,
        resume: ParsedResume,
        keywords: List[Keyword]
    ) -> List[KeywordMatch]:
        """
        Match keywords against resume
        
        Args:
            resume: Parsed resume object
            keywords: List of keywords to match
        
        Returns:
            List of KeywordMatch objects
        """
        logger.info(f"Matching {len(keywords)} keywords against resume")
        
        # Build searchable text from resume
        resume_text = self._build_resume_text(resume)
        section_texts = self._build_section_texts(resume)
        
        matches = []
        
        for keyword in keywords:
            match = self._match_single_keyword(
                keyword,
                resume_text,
                section_texts
            )
            matches.append(match)
        
        logger.info(f"Found {len([m for m in matches if m.match_type != MatchType.MISSING])} matches")
        return matches
    
    def _build_resume_text(self, resume: ParsedResume) -> str:
        """Build full searchable text from resume"""
        parts = []
        
        # Personal info
        if resume.personal.name:
            parts.append(resume.personal.name)
        
        # Summary
        if resume.summary:
            parts.append(resume.summary)
        
        # Experience
        for exp in resume.experience:
            parts.append(exp.title)
            parts.append(exp.company)
            for bullet in exp.bullets:
                parts.append(bullet.text)
        
        # Education
        for edu in resume.education:
            parts.append(edu.degree)
            parts.append(edu.institution)
        
        # Skills
        parts.extend(resume.skills.technical)
        parts.extend(resume.skills.tools)
        parts.extend(resume.skills.languages)
        
        # Certifications
        parts.extend(resume.certifications)
        
        return ' '.join(filter(None, parts)).lower()
    
    def _build_section_texts(self, resume: ParsedResume) -> Dict[str, str]:
        """Build text for each resume section"""
        sections = {}
        
        # Summary
        if resume.summary:
            sections['summary'] = resume.summary.lower()
        
        # Experience
        exp_parts = []
        for exp in resume.experience:
            exp_parts.append(exp.title)
            exp_parts.append(exp.company)
            for bullet in exp.bullets:
                exp_parts.append(bullet.text)
        sections['experience'] = ' '.join(filter(None, exp_parts)).lower()
        
        # Skills
        skill_parts = []
        skill_parts.extend(resume.skills.technical)
        skill_parts.extend(resume.skills.tools)
        sections['skills'] = ' '.join(filter(None, skill_parts)).lower()
        
        # Education
        edu_parts = []
        for edu in resume.education:
            edu_parts.append(edu.degree)
            edu_parts.append(edu.institution)
        sections['education'] = ' '.join(filter(None, edu_parts)).lower()
        
        return sections
    
    def _match_single_keyword(
        self,
        keyword: Keyword,
        full_text: str,
        section_texts: Dict[str, str]
    ) -> KeywordMatch:
        """Match a single keyword against resume"""
        
        # Try exact match first
        match = self._exact_match(keyword, full_text, section_texts)
        if match:
            return match
        
        # Try synonym match
        match = self._synonym_match(keyword, full_text, section_texts)
        if match:
            return match
        
        # Try stemmed match
        match = self._stemmed_match(keyword, full_text, section_texts)
        if match:
            return match
        
        # Try fuzzy match
        match = self._fuzzy_match(keyword, full_text, section_texts)
        if match:
            return match
        
        # Not found
        return KeywordMatch(
            keyword=keyword,
            match_type=MatchType.MISSING,
            matched_text="",
            locations=[],
            frequency=0
        )
    
    def _exact_match(
        self,
        keyword: Keyword,
        full_text: str,
        section_texts: Dict[str, str]
    ) -> Optional[KeywordMatch]:
        """Try exact keyword match"""
        keyword_lower = keyword.text.lower()
        pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        
        if re.search(pattern, full_text):
            # Count frequency
            frequency = len(re.findall(pattern, full_text))
            
            # Find sections where it appears
            locations = []
            for section, text in section_texts.items():
                if re.search(pattern, text):
                    locations.append(section)
            
            # Calculate context score
            context_score = self._calculate_context_score(keyword, full_text)
            
            return KeywordMatch(
                keyword=keyword,
                match_type=MatchType.EXACT,
                matched_text=keyword.text,
                locations=locations,
                frequency=frequency,
                context_score=context_score
            )
        
        return None
    
    def _synonym_match(
        self,
        keyword: Keyword,
        full_text: str,
        section_texts: Dict[str, str]
    ) -> Optional[KeywordMatch]:
        """Try matching synonyms"""
        for synonym in keyword.synonyms:
            synonym_lower = synonym.lower()
            pattern = r'\b' + re.escape(synonym_lower) + r'\b'
            
            if re.search(pattern, full_text):
                frequency = len(re.findall(pattern, full_text))
                
                locations = []
                for section, text in section_texts.items():
                    if re.search(pattern, text):
                        locations.append(section)
                
                context_score = self._calculate_context_score(keyword, full_text)
                
                return KeywordMatch(
                    keyword=keyword,
                    match_type=MatchType.SYNONYM,
                    matched_text=synonym,
                    locations=locations,
                    frequency=frequency,
                    context_score=context_score
                )
        
        return None
    
    def _stemmed_match(
        self,
        keyword: Keyword,
        full_text: str,
        section_texts: Dict[str, str]
    ) -> Optional[KeywordMatch]:
        """Try matching after stemming"""
        keyword_stem = self.stemmer.stem(keyword.text.lower())
        
        # Extract words from full text
        words = re.findall(r'\b\w+\b', full_text)
        
        matches = []
        for word in words:
            if self.stemmer.stem(word.lower()) == keyword_stem:
                matches.append(word)
        
        if matches:
            # Use most common matched form
            from collections import Counter
            matched_text = Counter(matches).most_common(1)[0][0]
            
            frequency = len(matches)
            
            # Find sections
            locations = []
            for section, text in section_texts.items():
                if matched_text.lower() in text:
                    locations.append(section)
            
            return KeywordMatch(
                keyword=keyword,
                match_type=MatchType.STEMMED,
                matched_text=matched_text,
                locations=locations,
                frequency=frequency
            )
        
        return None
    
    def _fuzzy_match(
        self,
        keyword: Keyword,
        full_text: str,
        section_texts: Dict[str, str]
    ) -> Optional[KeywordMatch]:
        """Try fuzzy string matching"""
        keyword_lower = keyword.text.lower()
        words = re.findall(r'\b\w+\b', full_text)
        
        best_match = None
        best_ratio = 0.0
        
        for word in words:
            ratio = SequenceMatcher(None, keyword_lower, word.lower()).ratio()
            if ratio > best_ratio and ratio >= self.fuzzy_threshold:
                best_ratio = ratio
                best_match = word
        
        if best_match:
            frequency = full_text.lower().count(best_match.lower())
            
            locations = []
            for section, text in section_texts.items():
                if best_match.lower() in text:
                    locations.append(section)
            
            return KeywordMatch(
                keyword=keyword,
                match_type=MatchType.PARTIAL,
                matched_text=best_match,
                locations=locations,
                frequency=frequency
            )
        
        return None
    
    def _calculate_context_score(self, keyword: Keyword, text: str) -> float:
        """
        Calculate how well keyword is used in context
        
        Checks for:
        - Action verbs nearby (managed, implemented, optimized)
        - Quantification (numbers, percentages)
        - Impact words (improved, increased, reduced)
        """
        score = 0.0
        keyword_lower = keyword.text.lower()
        
        # Find all occurrences
        pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Get context window (50 chars before and after)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].lower()
            
            # Check for action verbs
            action_verbs = [
                'managed', 'implemented', 'developed', 'created', 'designed',
                'optimized', 'improved', 'configured', 'automated', 'deployed'
            ]
            if any(verb in context for verb in action_verbs):
                score += 0.3
            
            # Check for quantification
            if re.search(r'\d+[\%\+]?', context):
                score += 0.3
            
            # Check for impact words
            impact_words = ['increased', 'reduced', 'improved', 'achieved', 'delivered']
            if any(word in context for word in impact_words):
                score += 0.2
            
            # Max score per occurrence is 0.8
            score = min(score, 0.8)
        
        return min(score, 1.0)

