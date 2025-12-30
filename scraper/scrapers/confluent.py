# scraper/scrapers/confluent.py
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
import json

from scraper.company_scraper import CompanyScraper
from scraper.models import RawJob

logger = logging.getLogger(__name__)


class ConfluentScraper(CompanyScraper):
    """
    Confluent careers page scraper
    Confluent uses Greenhouse ATS (common pattern)
    """
    
    COMPANY_NAME = "Confluent"
    CAREERS_URL = "https://careers.confluent.io/jobs"
    
    def _parse_job_listings(self, html: str) -> List[Dict]:
        """Parse Greenhouse job board"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Greenhouse uses structured JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'JobPosting':
                    jobs.append({
                        'title': data.get('title'),
                        'url': data.get('url'),
                        'location': data.get('jobLocation', {}).get('address', {}).get('addressLocality'),
                        'date_posted': data.get('datePosted')
                    })
            except:
                continue
        
        # Fallback: parse HTML if JSON-LD not available
        if not jobs:
            for job_card in soup.select('div.job-post'):
                title_el = job_card.select_one('a.job-title')
                location_el = job_card.select_one('span.location')
                
                if title_el:
                    jobs.append({
                        'title': title_el.get_text(strip=True),
                        'url': title_el['href'] if title_el.get('href', '').startswith('http') 
                               else f"https://careers.confluent.io{title_el['href']}",
                        'location': location_el.get_text(strip=True) if location_el else '',
                        'date_posted': None
                    })
        
        return jobs
    
    def _parse_job_detail(self, html: str, job_url: str) -> RawJob:
        """Parse Greenhouse job detail page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract structured data
        title = soup.select_one('h1.job-title')
        location = soup.select_one('div.location')
        description_div = soup.select_one('div#content')
        
        # Extract job ID from URL
        job_id = job_url.split('/')[-1].split('?')[0]
        
        return RawJob(
            external_id=f"confluent_{job_id}",
            source='confluent',
            title=title.get_text(strip=True) if title else '',
            company='Confluent',
            location=location.get_text(strip=True) if location else '',
            url=job_url,
            description=description_div.get_text(separator='\n', strip=True) if description_div else '',
            description_html=str(description_div) if description_div else '',
            apply_url=job_url,
            metadata={'scraper': 'greenhouse'}
        )

