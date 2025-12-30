# processor/config.py
import os
from dataclasses import dataclass, field
from typing import Dict, List, Set
from pathlib import Path
import yaml


@dataclass
class ProcessorConfig:
    """Configuration for job normalization and deduplication"""
    
    # Deduplication settings [web:31][web:33]
    fuzzy_threshold: int = 90  # 90-95% for tight matching [web:33]
    use_fuzzy_matching: bool = True
    
    # Text normalization
    unicode_normalization: str = "NFC"  # Preserve information [web:45]
    remove_html: bool = True
    convert_to_markdown: bool = True
    max_description_length: int = 50000
    min_description_length: int = 100
    
    # Language detection
    detect_language: bool = True
    allowed_languages: List[str] = field(default_factory=lambda: ['en'])
    
    # Location normalization
    normalize_locations: bool = True
    use_geocoding: bool = False  # Set True if you want precise coords [web:34]
    geocoding_rate_limit: float = 1.0  # Seconds between requests
    
    # Kafka-specific keywords (for validation)
    required_keywords: Set[str] = field(default_factory=lambda: {
        'kafka', 'apache kafka', 'event streaming', 'message broker',
        'streaming platform', 'data pipeline'
    })
    
    bonus_keywords: Set[str] = field(default_factory=lambda: {
        'zookeeper', 'schema registry', 'kafka connect', 'ksql', 'ksqldb',
        'kafka streams', 'mirrormaker', 'confluent', 'broker', 'partition',
        'consumer group', 'producer', 'topic', 'replication'
    })
    
    # US state abbreviations for location normalization
    us_states: Dict[str, str] = field(default_factory=lambda: {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY'
    })
    
    # Common location aliases
    location_aliases: Dict[str, str] = field(default_factory=lambda: {
        'sf': 'San Francisco',
        'bay area': 'San Francisco Bay Area',
        'nyc': 'New York',
        'la': 'Los Angeles',
        'dc': 'Washington',
        'philly': 'Philadelphia',
        'chi': 'Chicago',
        'greater boston': 'Boston',
        'silicon valley': 'San Francisco Bay Area',
        'tristate': 'New York',
        'dmv': 'Washington DC',
    })
    
    @classmethod
    def from_yaml(cls, path: str):
        """Load configuration from YAML file"""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data.get('processor', {}))


def get_config() -> ProcessorConfig:
    """Get processor configuration"""
    config_path = os.getenv('PROCESSOR_CONFIG', 'config/processor.yaml')
    
    if os.path.exists(config_path):
        return ProcessorConfig.from_yaml(config_path)
    return ProcessorConfig()

