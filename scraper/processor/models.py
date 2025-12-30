# processor/models.py
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import json


@dataclass
class NormalizedJob:
    """Job after normalization and enrichment"""
    
    # Original fields (preserved)
    external_id: str
    source: str
    raw_title: str
    raw_company: str
    raw_location: str
    url: str
    
    # Normalized fields
    title: str
    company: str
    location: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    remote_type: Optional[str] = None  # 'remote', 'hybrid', 'onsite'
    
    # Content
    description_text: str = ""
    description_markdown: Optional[str] = None
    
    # Dates
    posted_date: Optional[date] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    
    # Extracted data
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None  # 'yearly', 'hourly'
    
    # URLs
    apply_url: Optional[str] = None
    
    # Enrichment
    kafka_relevance_score: float = 0.0  # 0-100
    detected_language: Optional[str] = None
    keywords_found: List[str] = field(default_factory=list)
    
    # Validation
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    # Metadata
    normalization_version: str = "1.0.0"
    normalized_at: datetime = field(default_factory=datetime.utcnow)
    
    # Hash for deduplication
    dedup_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion"""
        data = asdict(self)
        
        # Convert dates to ISO format
        if self.posted_date:
            data['posted_date'] = self.posted_date.isoformat()
        data['scraped_at'] = self.scraped_at.isoformat()
        data['normalized_at'] = self.normalized_at.isoformat()
        
        # Convert lists to JSON
        data['keywords_found'] = json.dumps(self.keywords_found)
        data['validation_errors'] = json.dumps(self.validation_errors)
        
        return data
    
    def __repr__(self):
        return f"<NormalizedJob: {self.title} @ {self.company} [{self.location}]>"

