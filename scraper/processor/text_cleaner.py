# processor/text_cleaner.py
import re
import logging
from typing import Optional
import ftfy
from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


class TextCleaner:
    """Clean and normalize text content [web:45][web:35]"""
    
    # Regex patterns for cleaning
    MULTIPLE_SPACES = re.compile(r'\s+')
    MULTIPLE_NEWLINES = re.compile(r'\n{3,}')
    HTML_ENTITIES = re.compile(r'&[a-zA-Z]+;')
    URL_PATTERN = re.compile(r'https?://\S+')
    
    def __init__(self, unicode_norm: str = "NFC"):
        """
        Args:
            unicode_norm: Unicode normalization form (NFC, NFKC, NFD, NFKD)
                         Default NFC to preserve information [web:45]
        """
        self.unicode_norm = unicode_norm
    
    def clean_text(self, text: str) -> str:
        """
        Clean text with Unicode normalization
        
        Args:
            text: Raw text to clean
        
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Fix Unicode issues [web:45]
        text = ftfy.fix_text(text, normalization=self.unicode_norm)
        
        # Remove zero-width characters
        text = text.replace('\u200b', '')  # Zero-width space
        text = text.replace('\ufeff', '')  # BOM
        
        # Normalize whitespace
        text = self.MULTIPLE_SPACES.sub(' ', text)
        text = self.MULTIPLE_NEWLINES.sub('\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def html_to_text(self, html: str, preserve_links: bool = False) -> str:
        """
        Convert HTML to clean text
        
        Args:
            html: HTML content
            preserve_links: Keep URLs in text
        
        Returns:
            Plain text
        """
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style', 'noscript']):
            script.decompose()
        
        # Remove tracking pixels and hidden elements
        for hidden in soup.find_all(style=re.compile(r'display:\s*none')):
            hidden.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Remove URLs if not preserving
        if not preserve_links:
            text = self.URL_PATTERN.sub('', text)
        
        return self.clean_text(text)
    
    def html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to Markdown [web:35][web:38]
        
        Args:
            html: HTML content
        
        Returns:
            Markdown text
        """
        if not html:
            return ""
        
        try:
            # Convert to Markdown with ATX headings [web:38]
            markdown = md(
                html,
                heading_style="ATX",
                bullets="-",
                strip=['script', 'style', 'noscript'],
                convert=['p', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                        'strong', 'em', 'code', 'pre', 'blockquote', 'a']
            )
            
            # Clean up excessive newlines
            markdown = self.MULTIPLE_NEWLINES.sub('\n\n', markdown)
            
            return self.clean_text(markdown)
        
        except Exception as e:
            logger.warning(f"Failed to convert HTML to Markdown: {e}")
            return self.html_to_text(html)
    
    def extract_section(self, text: str, section_name: str) -> Optional[str]:
        """
        Extract specific section from job description
        
        Args:
            text: Full job description
            section_name: Section to extract (e.g., 'requirements', 'qualifications')
        
        Returns:
            Section text or None
        """
        # Common section headers
        patterns = {
            'requirements': r'(?:Requirements?|Qualifications?|What [Ww]e\'re [Ll]ooking [Ff]or):?\s*\n(.*?)(?:\n\n[A-Z]|\Z)',
            'responsibilities': r'(?:Responsibilities?|What [Yy]ou\'ll [Dd]o|Your [Rr]ole):?\s*\n(.*?)(?:\n\n[A-Z]|\Z)',
            'benefits': r'(?:Benefits?|What [Ww]e [Oo]ffer|Perks):?\s*\n(.*?)(?:\n\n[A-Z]|\Z)',
        }
        
        pattern = patterns.get(section_name.lower())
        if not pattern:
            return None
        
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return self.clean_text(match.group(1))
        
        return None

