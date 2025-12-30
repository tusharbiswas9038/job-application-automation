# scraper/models.py
from dataclasses import dataclass, field, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
import hashlib
import json

@dataclass
class RawJob:
    """Raw job data from scraper before normalization"""
    # Core fields
    external_id: str  # LinkedIn job ID or company job ID
    source: str  # 'linkedin', 'confluent', 'uber', etc.
    title: str
    company: str
    location: str
    url: str
    
    # Content
    description: str
    description_html: Optional[str] = None
    
    # Metadata
    posted_date: Optional[str] = None  # Raw string, normalize later
    apply_url: Optional[str] = None
    remote_type: Optional[str] = None  # 'remote', 'hybrid', 'onsite'
    salary_range: Optional[str] = None
    
    # Tracking
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    scraper_version: str = "1.0.0"
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion"""
        data = asdict(self)
        data['scraped_at'] = self.scraped_at.isoformat()
        data['metadata'] = json.dumps(self.metadata)
        return data
    
    def generate_hash(self) -> str:
        """Generate unique hash for deduplication"""
        # Normalize for consistent hashing
        normalized = f"{self.company.lower()}|{self.title.lower()}|{self.location.lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def __repr__(self):
        return f"<RawJob: {self.title} @ {self.company} [{self.source}]>"


@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    source: str
    query: str
    jobs_found: int
    jobs: List['RawJob'] = field(default_factory=list)
    jobs_new: int = 0
    jobs_duplicate: int = 0
    success: bool = True
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source': self.source,
            'query': self.query,
            'jobs_found': self.jobs_found,
            'jobs_new': self.jobs_new,
            'jobs_duplicates': self.jobs_duplicate,
            'status': 'success' if self.success else 'failed',
            'error_log': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

