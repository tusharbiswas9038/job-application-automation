# resume/ats/job_description.py
import re
import logging
from typing import List, Optional, Tuple
from resume.ats.models import JobDescription

logger = logging.getLogger(__name__)


class JobDescriptionParser:
    """
    Parse job description into structured format
    """
    
    # Section headers to look for
    SECTION_HEADERS = {
        'responsibilities': [
            r'responsibilities',
            r'what you.ll do',  # Fixed: removed problematic escaping
            r'what youll do',
            r'job description',
            r'duties',
            r'role',
            r'day to day',
        ],
        'requirements': [
            r'requirements',
            r'qualifications',
            r'what we.re looking for',  # Fixed
            r'what were looking for',
            r'you have',
            r'must have',
            r'required',
            r'skills',
        ],
        'nice_to_have': [
            r'nice to have',
            r'preferred',
            r'bonus',
            r'plus',
            r'ideal candidate',
            r'desirable',
        ],
        'benefits': [
            r'benefits',
            r'what we offer',
            r'perks',
            r'compensation',
            r'we offer',
        ],
    }
    
    # Experience patterns
    EXPERIENCE_PATTERNS = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience',
        r'experience\s+of\s+(\d+)\+?\s*(?:years?|yrs?)',
        r'minimum\s+(\d+)\s+(?:years?|yrs?)',
        r'at least\s+(\d+)\s+(?:years?|yrs?)',
    ]
    
    def __init__(self):
        pass
    
    def parse(self, jd_text: str, **metadata) -> JobDescription:
        """
        Parse job description text
        
        Args:
            jd_text: Full job description text
            **metadata: Additional metadata (title, company, url, etc.)
        
        Returns:
            JobDescription object
        """
        logger.info("Parsing job description")
        
        # Extract title (often in first line or capitalized)
        title = self._extract_title(jd_text)
        
        # Split into sections
        sections = self._split_sections(jd_text)
        
        # Extract structured data
        responsibilities = sections.get('responsibilities', [])
        requirements = sections.get('requirements', [])
        nice_to_have = sections.get('nice_to_have', [])
        benefits = sections.get('benefits', [])
        
        # Extract experience requirement
        exp_years = self._extract_experience_years(jd_text)
        
        # Create JobDescription object
        jd = JobDescription(
            raw_text=jd_text,
            title=metadata.get('title', title),
            company=metadata.get('company'),
            location=metadata.get('location'),
            responsibilities=responsibilities,
            requirements=requirements,
            nice_to_have=nice_to_have,
            benefits=benefits,
            required_experience_years=exp_years,
            source_url=metadata.get('url')
        )
        
        logger.info(f"Parsed JD: {jd.title} - {len(requirements)} requirements")
        return jd
    
    def _extract_title(self, text: str) -> str:
        """Extract job title from text"""
        lines = text.strip().split('\n')
        
        # Try to find title in first 10 lines
        for line in lines[:10]:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip lines that look like section headers
            if any(header in line.lower() for header in ['about', 'we are', 'location:', 'responsibilities', 'requirements']):
                continue
            
            # Title should be reasonable length
            if 10 < len(line) < 100:
                # Clean up
                title = re.sub(r'^#+\s*', '', line)      # Remove markdown headers
                title = re.sub(r'\*+', '', title)        # Remove emphasis
                title = re.sub(r'^[-•]\s*', '', title)   # Remove bullets
                title = title.strip()
                
                # Check if it looks like a job title (has keywords)
                title_lower = title.lower()
                job_keywords = [
                    'engineer', 'administrator', 'developer', 'manager', 'lead',
                    'architect', 'analyst', 'specialist', 'coordinator', 'consultant',
                    'director', 'senior', 'junior', 'principal', 'staff'
                ]
                
                if any(keyword in title_lower for keyword in job_keywords):
                    return title
                
                # First decent line might be title
                if not title.endswith(':') and len(title.split()) <= 8:
                    return title
        
        return "Unknown Position"


    def _split_sections(self, text: str) -> dict:
        """
        Split job description into sections
        
        Returns:
            Dict mapping section name to list of bullet points
        """
        sections = {
            'responsibilities': [],
            'requirements': [],
            'nice_to_have': [],
            'benefits': [],
        }
        
        # Normalize text
        text = text.replace('\r\n', '\n')
        lines = text.split('\n')
        
        current_section = None
        current_bullets = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is a section header
            section_name = self._identify_section(line)
            
            if section_name:
                # Save previous section
                if current_section and current_bullets:
                    sections[current_section].extend(current_bullets)
                
                # Start new section
                current_section = section_name
                current_bullets = []
            
            elif current_section:
                # Extract bullet point
                bullet = self._extract_bullet(line)
                if bullet:
                    current_bullets.append(bullet)
        
        # Save last section
        if current_section and current_bullets:
            sections[current_section].extend(current_bullets)
        
        return sections
    
    def _identify_section(self, line: str) -> Optional[str]:
        """Identify if line is a section header"""
        line_lower = line.lower()
        
        for section, patterns in self.SECTION_HEADERS.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    return section
        
        return None
    
    def _extract_bullet(self, line: str) -> Optional[str]:
        """Extract clean bullet point from line"""
        # Remove bullet markers
        line = re.sub(r'^[\*\-\•\◦\▪\→]+\s*', '', line)
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        
        # Must have minimum length
        if len(line) < 10:
            return None
        
        return line.strip()
    
    def _extract_experience_years(self, text: str) -> Optional[int]:
        """Extract required years of experience"""
        for pattern in self.EXPERIENCE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    years = int(match.group(1))
                    return years
                except (ValueError, IndexError):
                    continue
        
        return None

