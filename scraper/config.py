# scraper/config.py
import os
from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path
import yaml

@dataclass
class ScraperConfig:
    """Centralized scraper configuration"""
    # Rate limiting
    request_delay: float = 2.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    timeout: int = 30
    
    # LinkedIn specific
    linkedin_pages: int = 10  # 25 jobs per page = 250 jobs
    linkedin_guest_url: str = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        "?keywords={keywords}&location={location}&start={start}"
    )
    
    # User agent rotation
    user_agents: List[str] = None
    
    # Storage
    cache_dir: Path = Path("data/cache")
    log_dir: Path = Path("data/logs")
    
    # Kafka-specific search queries
    search_queries: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ]
        
        if self.search_queries is None:
            self.search_queries = [
                {"keywords": "Kafka Administrator", "location": "United States"},
                {"keywords": "Kafka Platform Engineer", "location": "United States"},
                {"keywords": "Kafka Infrastructure Engineer", "location": "Remote"},
                {"keywords": "Apache Kafka Admin", "location": "United States"},
            ]
        
        # Create directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_yaml(cls, path: str):
        """Load configuration from YAML file"""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data.get('scraper', {}))


def get_config() -> ScraperConfig:
    """Get scraper configuration from env or defaults"""
    config_path = os.getenv('SCRAPER_CONFIG', 'config/scraper.yaml')
    
    if os.path.exists(config_path):
        return ScraperConfig.from_yaml(config_path)
    return ScraperConfig()

