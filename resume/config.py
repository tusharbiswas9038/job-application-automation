# resume/config.py
import os
from dataclasses import dataclass, field
from typing import List, Set, Dict
from pathlib import Path
import yaml


@dataclass
class ResumeConfig:
    """Configuration for resume parsing and management"""
    
    # Resume structure
    supported_sections: List[str] = field(default_factory=lambda: [
        'summary', 'experience', 'education', 'skills', 
        'certifications', 'projects', 'awards'
    ])
    
    # Sections that can be modified by LLM
    modifiable_sections: Set[str] = field(default_factory=lambda: {
        'summary', 'experience', 'projects'
    })
    
    # Static sections (never modify)
    static_sections: Set[str] = field(default_factory=lambda: {
        'education', 'certifications', 'awards', 'personal'
    })
    
    # Bullet identification
    bullet_command_pattern: str = r'\\item\s+'
    custom_bullet_pattern: str = r'\\newcommand\{\\([a-zA-Z0-9_]+)\}\{(.+?)\}'
    
    # Validation
    min_bullet_length: int = 20
    max_bullet_length: int = 200
    min_bullets_per_role: int = 2
    max_bullets_per_role: int = 8
    
    # File paths
    master_resume_dir: Path = Path("data/resumes")
    variants_dir: Path = Path("data/resumes/variants")
    compiled_dir: Path = Path("data/resumes/compiled")
    
    # LaTeX compilation
    latex_compiler: str = "pdflatex"
    latex_options: List[str] = field(default_factory=lambda: [
        '-interaction=nonstopmode',
        '-halt-on-error',
        '-output-directory='
    ])
    
    # Metadata
    metadata_formats: List[str] = field(default_factory=lambda: ['yaml', 'json'])
    
    def __post_init__(self):
        """Create directories if they don't exist"""
        self.master_resume_dir.mkdir(parents=True, exist_ok=True)
        self.variants_dir.mkdir(parents=True, exist_ok=True)
        self.compiled_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_yaml(cls, path: str):
        """Load configuration from YAML file"""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data.get('resume', {}))


def get_config() -> ResumeConfig:
    """Get resume configuration"""
    config_path = os.getenv('RESUME_CONFIG', 'config/resume.yaml')
    
    if os.path.exists(config_path):
        return ResumeConfig.from_yaml(config_path)
    return ResumeConfig()

