# scraper/__init__.py
import logging
from typing import List
from datetime import datetime

from scraper.config import get_config
from scraper.linkedin_scraper import LinkedInScraper
from scraper.scrapers.confluent import ConfluentScraper
from scraper.models import RawJob, ScrapingResult
from scraper.utils import setup_logging, validate_raw_job, deduplicate_jobs

logger = logging.getLogger(__name__)


class JobScraperOrchestrator:
    """Main orchestrator for all scrapers"""
    
    def __init__(self):
        self.config = get_config()
        setup_logging(self.config.log_dir)
        
        # Initialize scrapers
        self.linkedin = LinkedInScraper(self.config)
        self.company_scrapers = [
            ConfluentScraper(self.config),
            # Add more company scrapers here
        ]
    
    def run_linkedin_scrape(self) -> tuple[List[RawJob], List[ScrapingResult]]:
        """Run all LinkedIn search queries"""
        all_jobs = []
        results = []
        
        logger.info(f"Starting LinkedIn scrape with {len(self.config.search_queries)} queries")
        
        for query in self.config.search_queries:
            result = self.linkedin.scrape(**query)
            results.append(result)
            
            # Get jobs from result would need to be stored in result object
            # For now, assuming scrape returns jobs in result
            
        logger.info(f"LinkedIn scrape completed: {len(all_jobs)} total jobs")
        return all_jobs, results
    
    def run_company_scrapes(self) -> tuple[List[RawJob], List[ScrapingResult]]:
        """Run all company-specific scrapers"""
        all_jobs = []
        results = []
        
        for scraper in self.company_scrapers:
            result = scraper.scrape(filter_kafka=True)
            results.append(result)
            
        return all_jobs, results
    
    def run_all(self, validate: bool = True) -> dict:
        """
        Run all scrapers and return aggregated results
        
        Returns:
            Dict with jobs and metadata
        """
        start_time = datetime.utcnow()
        
        # Run LinkedIn
        linkedin_jobs, linkedin_results = self.run_linkedin_scrape()
        
        # Run company scrapers
        company_jobs, company_results = self.run_company_scrapes()
        
        # Combine all jobs
        all_jobs = linkedin_jobs + company_jobs
        
        # Validate
        if validate:
            all_jobs = [job for job in all_jobs if validate_raw_job(job)]
        
        # Deduplicate
        unique_jobs = deduplicate_jobs(all_jobs)
        
        # Calculate statistics
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'jobs': unique_jobs,
            'stats': {
                'total_found': len(all_jobs),
                'unique_jobs': len(unique_jobs),
                'duplicates': len(all_jobs) - len(unique_jobs),
                'linkedin_jobs': len(linkedin_jobs),
                'company_jobs': len(company_jobs),
                'duration_seconds': duration,
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat()
            },
            'results': linkedin_results + company_results
        }
    
    def cleanup(self):
        """Close all scraper sessions"""
        self.linkedin.close()
        for scraper in self.company_scrapers:
            scraper.close()

