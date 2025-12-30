# resume/models.py
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class SectionType(Enum):
    """Section types in resume"""
    PERSONAL = "personal"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    CERTIFICATIONS = "certifications"
    PROJECTS = "projects"
    AWARDS = "awards"
    CUSTOM = "custom"


@dataclass
class BulletPoint:
    """Individual bullet point in resume"""
    id: str  # Unique identifier (e.g., 'kafkaBulletOne')
    text: str
    section: str
    subsection: Optional[str] = None  # e.g., company/role name
    is_modifiable: bool = True
    original_text: Optional[str] = None  # For tracking modifications
    command_name: Optional[str] = None  # LaTeX command name if defined
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperienceEntry:
    """Work experience entry"""
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: List[BulletPoint] = field(default_factory=list)
    is_current: bool = False
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['bullets'] = [b.to_dict() for b in self.bullets]
        return data


@dataclass
class EducationEntry:
    """Education entry"""
    degree: str
    institution: str
    location: Optional[str] = None
    graduation_date: Optional[str] = None
    gpa: Optional[str] = None
    honors: Optional[str] = None
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SkillsSection:
    """Skills section"""
    technical: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PersonalInfo:
    """Personal information"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ResumeMetadata:
    """Resume metadata (from YAML frontmatter)"""
    name: Optional[str] = None
    target_role: Optional[str] = None
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data


@dataclass
class ParsedResume:
    """Complete parsed resume structure"""
    # Metadata
    metadata: ResumeMetadata
    source_file: str
    
    # Sections
    personal: PersonalInfo
    summary: Optional[str] = None
    experience: List[ExperienceEntry] = field(default_factory=list)
    education: List[EducationEntry] = field(default_factory=list)
    skills: SkillsSection = field(default_factory=SkillsSection)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    awards: List[str] = field(default_factory=list)
    
    # All bullets for easy access
    all_bullets: List[BulletPoint] = field(default_factory=list)
    
    # Custom commands mapping
    custom_commands: Dict[str, str] = field(default_factory=dict)
    
    # Parsing metadata
    parsed_at: datetime = field(default_factory=datetime.utcnow)
    parser_version: str = "1.0.0"
    
    def get_modifiable_bullets(self) -> List[BulletPoint]:
        """Get all bullets that can be modified by LLM"""
        return [b for b in self.all_bullets if b.is_modifiable]
    
    def get_bullets_by_section(self, section: str) -> List[BulletPoint]:
        """Get bullets from specific section"""
        return [b for b in self.all_bullets if b.section == section]
    
    def get_experience_bullets(self, company: Optional[str] = None) -> List[BulletPoint]:
        """Get experience bullets, optionally filtered by company"""
        bullets = []
        for exp in self.experience:
            if company is None or exp.company == company:
                bullets.extend(exp.bullets)
        return bullets
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            'metadata': self.metadata.to_dict(),
            'source_file': self.source_file,
            'personal': self.personal.to_dict(),
            'summary': self.summary,
            'experience': [e.to_dict() for e in self.experience],
            'education': [e.to_dict() for e in self.education],
            'skills': self.skills.to_dict(),
            'projects': self.projects,
            'certifications': self.certifications,
            'awards': self.awards,
            'all_bullets': [b.to_dict() for b in self.all_bullets],
            'custom_commands': self.custom_commands,
            'parsed_at': self.parsed_at.isoformat(),
            'parser_version': self.parser_version
        }
    
    def __repr__(self):
        return f"<ParsedResume: {self.personal.name} | {len(self.all_bullets)} bullets>"

