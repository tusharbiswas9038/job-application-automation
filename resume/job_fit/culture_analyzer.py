# resume/job_fit/culture_analyzer.py
import logging
from typing import List

from resume.models import ParsedResume
from resume.job_fit.models import CultureFitIndicators, JobRequirements

logger = logging.getLogger(__name__)


class CultureFitAnalyzer:
    """
    Analyze cultural fit indicators from resume
    """
    
    # Company size indicators
    COMPANY_SIZE_INDICATORS = {
        'startup': ['startup', 'founding team', 'early stage', 'seed', 'series a'],
        'scaleup': ['growth stage', 'scaling', 'series b', 'series c', 'expanding'],
        'enterprise': ['enterprise', 'fortune', 'global', 'multinational', 'large scale'],
    }
    
    # Work style indicators
    WORK_STYLE_KEYWORDS = {
        'collaborative': ['collaborated', 'cross-functional', 'team', 'partnered', 'coordinated'],
        'autonomous': ['independently', 'self-directed', 'initiative', 'owned', 'drove'],
        'leadership': ['led', 'mentored', 'managed', 'guided', 'coached'],
        'innovative': ['innovative', 'created', 'designed', 'pioneered', 'launched'],
    }
    
    def __init__(self):
        pass
    
    def analyze_culture_fit(
        self,
        resume: ParsedResume,
        job_requirements: JobRequirements
    ) -> CultureFitIndicators:
        """
        Analyze cultural fit indicators
        
        Returns:
            CultureFitIndicators object
        """
        logger.info("Analyzing cultural fit")
        
        # Company size match
        company_size_match = self._check_company_size_match(
            resume,
            job_requirements.company_size
        )
        
        # Industry match
        industry_match = self._check_industry_match(resume, job_requirements)
        
        # Work style indicators
        work_style = self._extract_work_style(resume)
        
        # Values alignment
        values = self._extract_values(resume)
        
        # Leadership style
        leadership = self._determine_leadership_style(resume)
        
        return CultureFitIndicators(
            company_size_match=company_size_match,
            industry_match=industry_match,
            work_style_indicators=work_style,
            values_alignment=values,
            leadership_style=leadership
        )
    
    def _check_company_size_match(
        self,
        resume: ParsedResume,
        required_size: str
    ) -> bool:
        """Check if candidate has experience with similar company sizes"""
        if not resume.experience:
            return False
        
        # Check each company in experience
        for exp in resume.experience:
            company_text = f"{exp.company} {exp.title} {' '.join(b.text for b in exp.bullets)}".lower()
            
            # Check for size indicators
            if required_size in self.COMPANY_SIZE_INDICATORS:
                indicators = self.COMPANY_SIZE_INDICATORS[required_size]
                if any(ind in company_text for ind in indicators):
                    return True
        
        return False
    
    def _check_industry_match(
        self,
        resume: ParsedResume,
        job_requirements: JobRequirements
    ) -> bool:
        """Check industry/domain alignment"""
        # Check if candidate has domain experience
        for domain in job_requirements.domain_experience_required:
            domain_lower = domain.lower()
            
            # Check in experience
            for exp in resume.experience:
                exp_text = f"{exp.title} {' '.join(b.text for b in exp.bullets)}".lower()
                if domain_lower in exp_text:
                    return True
        
        return False
    
    def _extract_work_style(self, resume: ParsedResume) -> List[str]:
        """Extract work style indicators"""
        work_styles = []
        
        all_text = " ".join([
            resume.summary or "",
            *[b.text for b in resume.all_bullets]
        ]).lower()
        
        for style, keywords in self.WORK_STYLE_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in all_text)
            if matches >= 2:  # At least 2 keywords
                work_styles.append(style.title())
        
        return work_styles
    
    def _extract_values(self, resume: ParsedResume) -> List[str]:
        """Extract values alignment indicators"""
        values = []
        
        all_text = " ".join([
            resume.summary or "",
            *[b.text for b in resume.all_bullets]
        ]).lower()
        
        # Values keywords
        values_keywords = {
            'quality': ['quality', 'excellence', 'best practices', 'standards'],
            'innovation': ['innovation', 'cutting-edge', 'modern', 'new technology'],
            'efficiency': ['efficiency', 'optimization', 'performance', 'streamlined'],
            'collaboration': ['collaboration', 'teamwork', 'partnership', 'cross-functional'],
            'customer_focus': ['customer', 'user', 'client', 'stakeholder'],
        }
        
        for value, keywords in values_keywords.items():
            matches = sum(1 for kw in keywords if kw in all_text)
            if matches >= 2:
                values.append(value.replace('_', ' ').title())
        
        return values
    
    def _determine_leadership_style(self, resume: ParsedResume) -> str:
        """Determine leadership style from resume"""
        all_text = " ".join([b.text for b in resume.all_bullets]).lower()
        
        # Leadership indicators
        servant_leadership = ['mentored', 'coached', 'supported', 'enabled', 'empowered']
        directive_leadership = ['directed', 'managed', 'oversaw', 'supervised', 'controlled']
        collaborative_leadership = ['collaborated', 'facilitated', 'coordinated', 'partnered']
        
        scores = {
            'servant': sum(1 for kw in servant_leadership if kw in all_text),
            'directive': sum(1 for kw in directive_leadership if kw in all_text),
            'collaborative': sum(1 for kw in collaborative_leadership if kw in all_text),
        }
        
        if max(scores.values()) == 0:
            return "unknown"
        
        return max(scores.items(), key=lambda x: x[1])[0]

