# scraper/processor/__init__.py

from scraper.processor.normalizer import JobNormalizer
from scraper.processor.deduplicator import JobDeduplicator
from scraper.processor.keyword_extractor import KeywordExtractor

__all__ = [
    'JobNormalizer',
    'JobDeduplicator', 
    'KeywordExtractor'
]
