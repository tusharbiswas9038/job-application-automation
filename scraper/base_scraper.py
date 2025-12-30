# scraper/base_scraper.py
import logging
import time
import random
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from scraper.config import ScraperConfig
from scraper.models import RawJob, ScrapingResult

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers with retry logic and rate limiting"""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session = self._create_session()
        self.user_agent_idx = 0
        
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy [web:25]
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """Rotate user agents to avoid detection [web:21][web:23]"""
        self.user_agent_idx = (self.user_agent_idx + 1) % len(self.config.user_agents)
        
        return {
            "User-Agent": self.config.user_agents[self.user_agent_idx],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _fetch_page(self, url: str, **kwargs) -> requests.Response:
        """Fetch page with exponential backoff retry [web:25][web:28]"""
        # Add jitter to avoid thundering herd [web:25]
        jitter = random.uniform(0, 0.5)
        time.sleep(self.config.request_delay + jitter)
        
        headers = kwargs.pop('headers', self._get_headers())
        timeout = kwargs.pop('timeout', self.config.timeout)
        
        logger.debug(f"Fetching: {url}")
        
        response = self.session.get(
            url,
            headers=headers,
            timeout=timeout,
            **kwargs
        )
        
        # Check for soft blocks [web:23]
        if response.status_code == 999:
            logger.warning(f"LinkedIn soft-block (999) detected for {url}")
            raise requests.RequestException("LinkedIn soft-block")
        
        if "LinkedIn: Log In" in response.text:
            logger.warning(f"Login wall detected for {url}")
            raise requests.RequestException("Login wall detected")
        
        response.raise_for_status()
        return response
    
    @abstractmethod
    def scrape(self, **kwargs) -> List[RawJob]:
        """Implement scraping logic in subclasses"""
        pass
    
    def close(self):
        """Cleanup resources"""
        self.session.close()

