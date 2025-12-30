# resume/tailoring/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime
from pathlib import Path

from resume.models import BulletPoint, ParsedResume, ExperienceEntry
from resume.ats.models import ATSScore
from resume.job_fit.models import JobFitScore
from resume.ai.models import BulletEnhancement


@dataclass
class SelectedBullet:
    """A bullet selected for inclusion in variant"""
    bullet: BulletPoint
    relevance_score: float         # 0-1
    selection_reason: str
    was_enhanced: bool = False
    enhanced_version: Optional[str] = None


@dataclass
class VariantContent:
    """Content selected for a resume variant"""
    summary: str
    experience_sections: List['ExperienceSection']
    skills: Dict[str, List[str]]
    total_bullets: int
    
    def get_all_bullets(self) -> List[BulletPoint]:
        """Get all selected bullets"""
        bullets = []
        for section in self.experience_sections:
            bullets.extend([sb.bullet for sb in section.selected_bullets])
        return bullets


@dataclass
class ExperienceSection:
    """Experience section with selected bullets"""
    experience: ExperienceEntry
    selected_bullets: List[SelectedBullet]
    total_available: int


@dataclass
class ResumeVariant:
    """A generated resume variant"""
    variant_id: str
    base_resume_path: str
    job_title: str
    company: Optional[str] = None
    
    # Content
    content: Optional[VariantContent] = None
    
    # Generated files
    latex_path: Optional[str] = None
    pdf_path: Optional[str] = None
    
    # Scores
    ats_score: Optional[ATSScore] = None
    fit_score: Optional[JobFitScore] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    strategy: str = "ai_enhanced"
    bullets_enhanced: int = 0
    keywords_added: List[str] = field(default_factory=list)
    
    @property
    def output_filename(self) -> str:
        """Generate output filename"""
        # Clean company name
        company_clean = self.company.replace(' ', '_') if self.company else "company"
        # Clean job title
        title_clean = self.job_title.replace(' ', '_').lower()
        
        return f"resume_{company_clean}_{title_clean}_{self.variant_id[:8]}.tex"


@dataclass
class VariantGenerationConfig:
    """Configuration for variant generation"""
    # Bullet selection
    target_bullets: int = 18
    min_bullets_per_job: int = 3
    max_bullets_per_job: int = 15
    
    # AI enhancement
    use_ai_enhancement: bool = True
    max_bullets_to_enhance: int = 5
    min_enhancement_confidence: float = 0.7
    
    # Keyword optimization
    target_keyword_density: float = 0.04  # 4%
    min_keyword_frequency: int = 2
    
    # Scoring
    auto_score_after_generation: bool = True
    min_acceptable_ats_score: float = 70.0

