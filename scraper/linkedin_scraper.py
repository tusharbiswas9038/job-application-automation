# scraper/linkedin_scraper.py
import logging
import re
import urllib.parse
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime

from scraper.base_scraper import BaseScraper
from scraper.models import RawJob, ScrapingResult
from scraper.config import ScraperConfig

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """
    LinkedIn Jobs scraper using guest API [web:23]
    No authentication required, respects rate limits
    """
    
    JOB_URL_PATTERN = re.compile(r"https?://(?:\w+\.)?linkedin\.com/jobs/view/[^/]+-(\d+)(?:\?|$)")
    
    def scrape(
        self,
        keywords: str,
        location: str = "United States",
        max_pages: Optional[int] = None
    ) -> ScrapingResult:
        """
        Scrape LinkedIn jobs using guest API
        
        Args:
            keywords: Search keywords (e.g., "Kafka Administrator")
            location: Location string (e.g., "United States", "Remote")
            max_pages: Max pages to scrape (25 jobs/page), defaults to config
        
        Returns:
            ScrapingResult with list of RawJob objects
        """
        started_at = datetime.utcnow()
        pages = max_pages or self.config.linkedin_pages
        all_jobs: List[RawJob] = []
        
        logger.info(f"Starting LinkedIn scrape: '{keywords}' in '{location}'")
        
        try:
            for page in range(pages):
                start = page * 25
                
                logger.info(f"Scraping page {page + 1}/{pages} (start={start})")
                
                # Fetch page
                url = self.config.linkedin_guest_url.format(
                    keywords=urllib.parse.quote_plus(keywords),
                    location=urllib.parse.quote_plus(location),
                    start=start
                )
                
                try:
                    response = self._fetch_page(url)
                    jobs = self._parse_job_cards(response.text)
                    
                    if not jobs:
                        logger.warning(f"No jobs found on page {page + 1}, stopping")
                        break
                    
                    # Fetch detailed descriptions
                    for job_data in jobs:
                        try:
                            raw_job = self._enrich_job(job_data, keywords, location)
                            all_jobs.append(raw_job)
                        except Exception as e:
                            logger.error(f"Failed to enrich job {job_data.get('link')}: {e}")
                            continue
                    
                    logger.info(f"Page {page + 1}: extracted {len(jobs)} jobs")
                    
                except Exception as e:
                    logger.error(f"Error scraping page {page + 1}: {e}")
                    # Continue to next page instead of failing completely
                    continue
            
            completed_at = datetime.utcnow()
            
            return ScrapingResult(
                source='linkedin',
                query=f"{keywords} | {location}",
                jobs_found=len(all_jobs),
                jobs=all_jobs,
                success=True,
                started_at=started_at,
                completed_at=completed_at
            )
            
        except Exception as e:
            logger.exception(f"LinkedIn scraping failed: {e}")
            return ScrapingResult(
                source='linkedin',
                query=f"{keywords} | {location}",
                jobs_found=len(all_jobs),
                jobs=all_jobs,
                success=False,
                error_message=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow()
            )
    
    def _parse_job_cards(self, html: str) -> List[Dict[str, str]]:
        """
        Parse job cards from LinkedIn search results HTML [web:23]
        
        Returns:
            List of dicts with basic job info
        """
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Primary selector for LinkedIn job cards
        for card in soup.select('div.base-card'):
            try:
                title_el = card.select_one('h3.base-search-card__title')
                company_el = card.select_one('h4.base-search-card__subtitle')
                location_el = card.select_one('span.job-search-card__location')
                link_el = card.select_one('a.base-card__full-link')
                date_el = card.select_one('time')
                
                if not (title_el and company_el and location_el and link_el):
                    continue
                
                # Extract job ID from URL
                job_url = link_el['href'].split('?')[0]
                job_id_match = self.JOB_URL_PATTERN.search(job_url)
                
                if not job_id_match:
                    logger.warning(f"Could not extract job ID from {job_url}")
                    continue
                
                job_id = job_id_match.group(1)
                
                jobs.append({
                    'job_id': job_id,
                    'title': title_el.get_text(strip=True),
                    'company': company_el.get_text(strip=True),
                    'location': location_el.get_text(strip=True),
                    'link': job_url,
                    'posted_date': date_el.get('datetime') if date_el else None
                })
                
            except Exception as e:
                logger.warning(f"Failed to parse job card: {e}")
                continue
        
        # Fallback: try alternate selectors if primary failed [web:23]
        if not jobs:
            logger.info("Primary selector failed, trying fallback")
            for link_el in soup.find_all('a', href=self.JOB_URL_PATTERN):
                try:
                    parent = link_el.find_parent(['div', 'li'])
                    if not parent:
                        continue
                    
                    job_url = link_el['href'].split('?')[0]
                    job_id = self.JOB_URL_PATTERN.search(job_url).group(1)
                    
                    title = link_el.get_text(strip=True)
                    company_el = parent.find(['h4', 'span'], class_=re.compile(r'(subtitle|company)', re.I))
                    location_el = parent.find('span', class_=re.compile(r'location', re.I))
                    
                    jobs.append({
                        'job_id': job_id,
                        'title': title,
                        'company': company_el.get_text(strip=True) if company_el else '',
                        'location': location_el.get_text(strip=True) if location_el else '',
                        'link': job_url,
                        'posted_date': None
                    })
                    
                except Exception as e:
                    continue
        
        return jobs
    
    def _enrich_job(self, job_data: Dict[str, str], keywords: str, location: str) -> RawJob:
        """
        Fetch full job description and create RawJob object
        
        Args:
            job_data: Basic job info from search results
            keywords: Original search keywords
            location: Original search location
        
        Returns:
            RawJob with full description
        """
        job_url = job_data['link']
        
        # Fetch full job page
        response = self._fetch_page(job_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract description
        desc_container = soup.select_one('div.show-more-less-html__markup')
        
        if desc_container:
            description_html = str(desc_container)
            description_text = desc_container.get_text(separator='\n', strip=True)
        else:
            # Fallback: try to find any large text block
            description_html = ""
            description_text = soup.get_text(separator='\n', strip=True)[:5000]
        
        # Extract apply button
        apply_button = soup.select_one('a.jobs-apply-button')
        apply_url = apply_button['href'] if apply_button else job_url
        
        # Detect remote type
        remote_type = self._detect_remote_type(description_text)
        
        return RawJob(
            external_id=job_data['job_id'],
            source='linkedin',
            title=job_data['title'],
            company=job_data['company'],
            location=job_data['location'],
            url=job_url,
            description=description_text,
            description_html=description_html,
            posted_date=job_data.get('posted_date'),
            apply_url=apply_url,
            remote_type=remote_type,
            metadata={
                'search_keywords': keywords,
                'search_location': location,
            }
        )
    
    def _detect_remote_type(self, text: str) -> Optional[str]:
        """Detect if job is remote/hybrid/onsite from description"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['fully remote', '100% remote', 'remote-first']):
            return 'remote'
        elif any(keyword in text_lower for keyword in ['hybrid', 'remote/onsite', 'flexible']):
            return 'hybrid'
        elif any(keyword in text_lower for keyword in ['on-site', 'onsite', 'in-office']):
            return 'onsite'
        
        return None

