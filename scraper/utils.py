# scraper/utils.py
import logging
import hashlib
from pathlib import Path
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


def setup_logging(log_dir: Path, log_level: str = "INFO"):
    """Configure logging for scraper"""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log filename with timestamp
    log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def validate_raw_job(job) -> bool:
    """Validate RawJob has required fields"""
    required = ['external_id', 'title', 'company', 'description', 'url']
    
    for field in required:
        if not getattr(job, field, None):
            logger.warning(f"Job missing required field: {field}")
            return False
    
    # Validate URL format
    if not job.url.startswith('http'):
        logger.warning(f"Invalid URL: {job.url}")
        return False
    
    # Validate description length
    if len(job.description) < 100:
        logger.warning(f"Description too short: {len(job.description)} chars")
        return False
    
    return True


def deduplicate_jobs(jobs: List) -> List:
    """
    Deduplicate jobs based on hash
    Keeps first occurrence
    """
    seen_hashes = set()
    unique_jobs = []
    
    for job in jobs:
        job_hash = job.generate_hash()
        
        if job_hash not in seen_hashes:
            seen_hashes.add(job_hash)
            unique_jobs.append(job)
        else:
            logger.debug(f"Duplicate found: {job.title} @ {job.company}")
    
    logger.info(f"Deduplication: {len(jobs)} → {len(unique_jobs)} jobs")
    return unique_jobs

