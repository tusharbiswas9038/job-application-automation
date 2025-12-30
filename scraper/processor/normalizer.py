# scraper/processor/normalizer.py
import logging
from typing import List, Optional
from langdetect import detect, LangDetectException
from datetime import datetime

from scraper.processor.config import get_config, ProcessorConfig
from scraper.processor.models import NormalizedJob
from scraper.processor.text_cleaner import TextCleaner
from scraper.processor.date_parser import DateParser
from scraper.processor.salary_extractor import SalaryExtractor
from scraper.processor.location_normalizer import LocationNormalizer
from scraper.processor.keyword_extractor import KeywordExtractor
from scraper.models import RawJob

logger = logging.getLogger(__name__)


class JobNormalizer:
    """Main normalizer orchestrating all normalization steps"""

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or get_config()
        self.text_cleaner = TextCleaner()
        self.date_parser = DateParser()
        self.salary_extractor = SalaryExtractor()
        
        self.location_normalizer = LocationNormalizer(
            us_states=self.config.us_states,
            location_aliases=self.config.location_aliases
        )
        
        self.keyword_extractor = KeywordExtractor(
            required_keywords=self.config.required_keywords,
            bonus_keywords=self.config.bonus_keywords
        )

    def normalize(self, raw_job: RawJob) -> NormalizedJob:
        """Normalize a raw job posting"""
        
        logger.debug(f"Normalizing job: {raw_job.title} at {raw_job.company}")

        # Clean text fields
        title = self.text_cleaner.clean_text(raw_job.title) if raw_job.title else ''
        company = self.text_cleaner.clean_text(raw_job.company) if raw_job.company else ''
        description_text = self.text_cleaner.clean_text(raw_job.description or '')

        # Parse location
        location_parsed = self.location_normalizer.normalize_location(raw_job.location or "")
        location = location_parsed.normalized or raw_job.location or "Remote"

        # Parse posted date
        posted_date = None
        if raw_job.posted_date:
            posted_date = self.date_parser.parse_date(raw_job.posted_date)

        # Extract salary
        salary_min = None
        salary_max = None
        salary_currency = None
        if hasattr(raw_job, 'salary') and raw_job.salary:
            salary_info = self.salary_extractor.extract(raw_job.salary)
            if salary_info:
                salary_min = salary_info.get('min')
                salary_max = salary_info.get('max')
                salary_currency = salary_info.get('currency')

        # Extract keywords
        keywords_found = self.keyword_extractor.extract_keywords(description_text)[:20]

        # Detect language
        detected_language = self._detect_language(description_text)

        # Build normalized job with correct field names
        normalized = NormalizedJob(
            external_id=getattr(raw_job, 'job_id', raw_job.url.split('/')[-1]),
            source=raw_job.source,
            raw_title=raw_job.title,
            raw_company=raw_job.company,
            raw_location=raw_job.location or '',
            url=raw_job.url,
            title=title,
            company=company,
            location=location,
            city=location_parsed.city,
            state=location_parsed.state,
            country=location_parsed.country,
            remote_type=location_parsed.remote_type,
            description_text=description_text,
            posted_date=posted_date,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            detected_language=detected_language,
            keywords_found=keywords_found,
            scraped_at=datetime.utcnow(),
            normalized_at=datetime.utcnow()
        )

        logger.debug(f"Normalized job: {normalized.title} | Location: {normalized.location}")
        return normalized

    def _detect_language(self, text: str) -> str:
        """Detect language of job description"""
        if not text or len(text.strip()) < 50:
            return "en"

        try:
            lang = detect(text)
            return lang if lang in ["en", "es", "fr", "de"] else "en"
        except LangDetectException:
            return "en"

    def normalize_batch(self, raw_jobs: List[RawJob]) -> List[NormalizedJob]:
        """Normalize multiple jobs"""
        normalized_jobs = []

        for raw_job in raw_jobs:
            try:
                normalized = self.normalize(raw_job)
                normalized_jobs.append(normalized)
            except Exception as e:
                logger.error(f"Failed to normalize job {raw_job.url}: {e}")
                continue

        logger.info(f"Normalized {len(normalized_jobs)}/{len(raw_jobs)} jobs")
        return normalized_jobs
