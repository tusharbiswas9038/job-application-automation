# resume/ats/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
from datetime import datetime


class KeywordCategory(Enum):
    """Keyword importance categories"""
    REQUIRED = "required"           # Must-have keywords
    TECHNICAL = "technical"         # Technical skills
    SOFT_SKILL = "soft_skill"       # Soft skills
    TOOL = "tool"                   # Tools and platforms
    DOMAIN = "domain"               # Domain knowledge
    CERTIFICATION = "certification" # Certifications
    EXPERIENCE = "experience"       # Experience-related


class MatchType(Enum):
    """How keyword was matched"""
    EXACT = "exact"                 # Exact match
    SYNONYM = "synonym"             # Matched via synonym
    PARTIAL = "partial"             # Partial match
    STEMMED = "stemmed"             # Matched after stemming
    MISSING = "missing"             # Not found


@dataclass
class Keyword:
    """Represents a keyword from job description"""
    text: str
    category: KeywordCategory
    importance: float  # 0.0 to 1.0
    synonyms: List[str] = field(default_factory=list)
    context: Optional[str] = None  # Where it appeared in JD
    
    def __hash__(self):
        return hash(self.text.lower())
    
    def __eq__(self, other):
        if isinstance(other, Keyword):
            return self.text.lower() == other.text.lower()
        return False


@dataclass
class KeywordMatch:
    """Represents a matched keyword in resume"""
    keyword: Keyword
    match_type: MatchType
    matched_text: str              # Actual text found in resume
    locations: List[str]           # Sections where found
    frequency: int                 # How many times it appears
    context_score: float = 0.0     # How well it's used in context
    
    @property
    def score(self) -> float:
        """Calculate match score based on type and frequency"""
        base_scores = {
            MatchType.EXACT: 1.0,
            MatchType.SYNONYM: 0.9,
            MatchType.STEMMED: 0.8,
            MatchType.PARTIAL: 0.6,
            MatchType.MISSING: 0.0
        }
        
        base = base_scores[self.match_type]
        
        # Bonus for multiple appearances (diminishing returns)
        frequency_multiplier = min(1.0 + (self.frequency - 1) * 0.1, 1.3)
        
        # Context bonus
        context_bonus = self.context_score * 0.2
        
        return min(base * frequency_multiplier + context_bonus, 1.0)


@dataclass
class JobDescription:
    """Parsed job description"""
    raw_text: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    
    # Parsed sections
    responsibilities: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    nice_to_have: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    
    # Extracted data
    required_experience_years: Optional[int] = None
    required_skills: Set[str] = field(default_factory=set)
    preferred_skills: Set[str] = field(default_factory=set)
    required_education: Optional[str] = None
    
    # Metadata
    parsed_at: datetime = field(default_factory=datetime.now)
    source_url: Optional[str] = None


@dataclass
class SectionScore:
    """Score for a resume section"""
    section_name: str
    keyword_matches: int
    total_keywords: int
    match_rate: float              # 0.0 to 1.0
    density: float                 # Keywords per 100 words
    quality_score: float           # 0.0 to 1.0
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ATSScore:
    """Complete ATS scoring result"""
    overall_score: float           # 0-100
    
    # Component scores
    keyword_score: float           # 0-100
    experience_score: float        # 0-100
    education_score: float         # 0-100
    skills_score: float            # 0-100
    format_score: float            # 0-100
    
    # Detailed analysis
    matched_keywords: List[KeywordMatch]
    missing_keywords: List[Keyword]
    section_scores: Dict[str, SectionScore]
    
    # Statistics
    total_keywords: int
    matched_count: int
    match_rate: float
    
    # Recommendations
    critical_gaps: List[str]       # Must fix
    improvements: List[str]        # Should fix
    enhancements: List[str]        # Nice to have
    
    # Metadata
    job_title: str
    scored_at: datetime = field(default_factory=datetime.now)
    
    @property
    def grade(self) -> str:
        """Get letter grade"""
        if self.overall_score >= 90:
            return "A+"
        elif self.overall_score >= 85:
            return "A"
        elif self.overall_score >= 80:
            return "A-"
        elif self.overall_score >= 75:
            return "B+"
        elif self.overall_score >= 70:
            return "B"
        elif self.overall_score >= 65:
            return "B-"
        elif self.overall_score >= 60:
            return "C+"
        elif self.overall_score >= 55:
            return "C"
        else:
            return "F"
    
    @property
    def pass_threshold(self) -> bool:
        """Does resume likely pass ATS screening?"""
        return self.overall_score >= 65  # Common ATS threshold


@dataclass
class OptimizationSuggestion:
    """Suggestion for improving ATS score"""
    priority: str                  # "critical", "high", "medium", "low"
    category: str                  # "keyword", "format", "experience", etc.
    issue: str                     # What's wrong
    suggestion: str                # How to fix
    impact: float                  # Expected score improvement (0-10)
    keywords_affected: List[str] = field(default_factory=list)

