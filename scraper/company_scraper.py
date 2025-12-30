# scraper/company_scraper.py
import logging
from typing import List, Optional, Dict
from abc import abstractmethod
from bs4 import BeautifulSoup
import json

from scraper.base_scraper import BaseScraper
from scraper.models import RawJob, ScrapingResult
from scraper.config import ScraperConfig

logger = logging.getLogger(__name__)


class CompanyScraper(BaseScraper):
    """Base class for company-specific scrapers"""
    
    COMPANY_NAME: str = "Unknown"
    CAREERS_URL: str = ""
    
    @abstractmethod
    def _parse_job_listings(self, html: str) -> List[Dict]:
        """Parse job listings from company careers page"""
        pass
    
    @abstractmethod
    def _parse_job_detail(self, html: str, job_url: str) -> RawJob:
        """Parse individual job detail page"""
        pass
    
    def scrape(self, filter_kafka: bool = True) -> ScrapingResult:
        """
        Scrape company careers page
        
        Args:
            filter_kafka: Only return Kafka-related jobs
        """
        logger.info(f"Scraping {self.COMPANY_NAME} careers page")
        
        try:
            # Fetch listings page
            response = self._fetch_page(self.CAREERS_URL)
            job_listings = self._parse_job_listings(response.text)
            
            # Filter Kafka jobs
            if filter_kafka:
                job_listings = [
                    job for job in job_listings
                    if self._is_kafka_related(job['title'])
                ]
            
            logger.info(f"Found {len(job_listings)} relevant jobs at {self.COMPANY_NAME}")
            
            # Fetch details for each job
            all_jobs = []
            for job_data in job_listings:
                try:
                    response = self._fetch_page(job_data['url'])
                    raw_job = self._parse_job_detail(response.text, job_data['url'])
                    all_jobs.append(raw_job)
                except Exception as e:
                    logger.error(f"Failed to fetch {job_data['url']}: {e}")
                    continue
            
            return ScrapingResult(
                source=self.COMPANY_NAME.lower(),
                query='kafka jobs',
                jobs_found=len(all_jobs),
                success=True
            )
            
        except Exception as e:
            logger.exception(f"Failed to scrape {self.COMPANY_NAME}: {e}")
            return ScrapingResult(
                source=self.COMPANY_NAME.lower(),
                query='kafka jobs',
                jobs_found=0,
                success=False,
                error_message=str(e)
            )
    
    def _is_kafka_related(self, title: str) -> bool:
        """Check if job title is Kafka-related"""
        kafka_keywords = [
            'kafka', 'streaming', 'platform engineer', 'data infrastructure',
            'event streaming', 'message broker', 'real-time data'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in kafka_keywords)

