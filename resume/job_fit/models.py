# resume/job_fit/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime
from enum import Enum


class FitLevel(Enum):
    """Overall fit level"""
    EXCELLENT = "excellent"      # 90-100%
    STRONG = "strong"            # 80-89%
    GOOD = "good"                # 70-79%
    MODERATE = "moderate"        # 60-69%
    WEAK = "weak"                # 50-59%
    POOR = "poor"                # <50%


class SkillLevel(Enum):
    """Skill proficiency levels"""
    EXPERT = "expert"            # 5+ years or mastery
    ADVANCED = "advanced"        # 3-5 years
    INTERMEDIATE = "intermediate" # 1-3 years
    BEGINNER = "beginner"        # <1 year
    NONE = "none"                # No experience


class ExperienceLevel(Enum):
    """Experience level categories"""
    SENIOR = "senior"            # 7+ years
    MID = "mid"                  # 3-7 years
    JUNIOR = "junior"            # 1-3 years
    ENTRY = "entry"              # <1 year


@dataclass
class SkillGap:
    """A skill gap between candidate and job requirement"""
    skill_name: str
    required_level: SkillLevel
    current_level: SkillLevel
    importance: float            # 0-1
    gap_severity: str            # "critical", "moderate", "minor"
    training_time: Optional[str] = None  # e.g., "3-6 months"
    can_learn: bool = True


@dataclass
class SkillMatch:
    """A matched skill between candidate and job"""
    skill_name: str
    required_level: SkillLevel
    candidate_level: SkillLevel
    match_strength: float        # 0-1
    evidence: List[str]          # Where skill was demonstrated
    years_experience: Optional[int] = None


@dataclass
class ExperienceMatch:
    """Experience relevance to job requirements"""
    job_title: str
    company: str
    relevance_score: float       # 0-1
    matching_aspects: List[str]  # What aspects match
    duration_months: int
    recency_score: float         # 0-1, higher if more recent
    domain_match: bool
    technology_overlap: List[str]


@dataclass
class CultureFitIndicators:
    """Indicators of cultural fit"""
    company_size_match: bool     # Startup vs Enterprise experience
    industry_match: bool
    work_style_indicators: List[str]  # e.g., "collaborative", "autonomous"
    values_alignment: List[str]
    leadership_style: Optional[str] = None
    
    @property
    def fit_score(self) -> float:
        """Calculate culture fit score"""
        score = 0.0
        if self.company_size_match:
            score += 0.3
        if self.industry_match:
            score += 0.3
        if self.work_style_indicators:
            score += 0.2
        if self.values_alignment:
            score += 0.2
        return score


@dataclass
class CareerTrajectory:
    """Career progression analysis"""
    current_level: ExperienceLevel
    progression_trend: str       # "upward", "lateral", "downward"
    promotions_count: int
    avg_tenure_months: float
    specialization: List[str]    # Areas of focus
    growth_areas: List[str]      # Skills being developed
    ready_for_level: ExperienceLevel
    
    @property
    def is_progressing(self) -> bool:
        return self.progression_trend == "upward"


@dataclass
class JobFitScore:
    """Complete job fit assessment"""
    overall_fit: float           # 0-100
    fit_level: FitLevel
    
    # Component scores
    skill_fit: float             # 0-100
    experience_fit: float        # 0-100
    culture_fit: float           # 0-100
    trajectory_fit: float        # 0-100
    education_fit: float         # 0-100
    
    # Detailed analysis
    skill_matches: List[SkillMatch]
    skill_gaps: List[SkillGap]
    experience_matches: List[ExperienceMatch]
    culture_indicators: CultureFitIndicators
    career_trajectory: CareerTrajectory
    
    # Gaps and recommendations
    critical_gaps: List[str]
    development_areas: List[str]
    strengths: List[str]
    
    # Metadata
    job_title: str
    candidate_name: str
    evaluated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_good_fit(self) -> bool:
        """Is candidate a good fit?"""
        return self.overall_fit >= 70.0
    
    @property
    def hire_recommendation(self) -> str:
        """Hiring recommendation"""
        if self.overall_fit >= 85:
            return "Strong Hire - Excellent fit across all dimensions"
        elif self.overall_fit >= 75:
            return "Hire - Good fit with minor gaps"
        elif self.overall_fit >= 65:
            return "Consider - Moderate fit, assess cultural factors"
        elif self.overall_fit >= 55:
            return "Weak - Significant skill gaps"
        else:
            return "No Hire - Poor fit for role"


@dataclass
class JobRequirements:
    """Structured job requirements"""
    job_title: str
    company: str
    experience_level: ExperienceLevel
    
    # Required skills with levels
    required_skills: Dict[str, SkillLevel]
    preferred_skills: Dict[str, SkillLevel]
    
    # Experience requirements
    min_years_experience: int
    domain_experience_required: List[str]
    
    # Culture/Values
    company_size: str            # "startup", "scaleup", "enterprise"
    work_environment: str        # "remote", "hybrid", "office"
    team_structure: str          # "autonomous", "collaborative"
    
    # Education
    education_required: Optional[str] = None
    certifications_required: List[str] = field(default_factory=list)


@dataclass
class FitComparison:
    """Compare multiple candidates for same role"""
    job_title: str
    candidates: List[JobFitScore]
    
    @property
    def best_candidate(self) -> Optional[JobFitScore]:
        """Get best fit candidate"""
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.overall_fit)
    
    @property
    def ranked_candidates(self) -> List[JobFitScore]:
        """Get candidates ranked by fit"""
        return sorted(self.candidates, key=lambda c: c.overall_fit, reverse=True)

