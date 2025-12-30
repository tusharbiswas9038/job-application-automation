# resume/job_fit/experience_evaluator.py
import logging
from typing import List, Tuple, Optional
from datetime import datetime
import re

from resume.models import ParsedResume, ExperienceEntry
from resume.job_fit.models import (
    ExperienceMatch, ExperienceLevel, JobRequirements
)

logger = logging.getLogger(__name__)


class ExperienceEvaluator:
    """
    Evaluate experience relevance to job requirements
    """
    
    # Domain keywords
    DOMAIN_KEYWORDS = {
        'data_streaming': ['kafka', 'kinesis', 'pubsub', 'streaming', 'real-time'],
        'devops': ['devops', 'sre', 'infrastructure', 'ci/cd', 'automation'],
        'cloud': ['aws', 'azure', 'gcp', 'cloud'],
        'distributed_systems': ['distributed', 'microservices', 'cluster', 'replication'],
    }
    
    def __init__(self):
        pass
    
    def evaluate_experience(
        self,
        resume: ParsedResume,
        job_requirements: JobRequirements
    ) -> List[ExperienceMatch]:
        """
        Evaluate how well candidate's experience matches job requirements
        
        Returns:
            List of ExperienceMatch objects
        """
        logger.info("Evaluating experience relevance")
        
        matches = []
        
        for exp in resume.experience:
            match = self._evaluate_single_experience(exp, job_requirements)
            if match:
                matches.append(match)
        
        # Sort by relevance
        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        
        logger.info(f"Found {len(matches)} relevant experience entries")
        return matches
    
    def _evaluate_single_experience(
        self,
        experience: ExperienceEntry,
        job_requirements: JobRequirements
    ) -> Optional[ExperienceMatch]:
        """Evaluate a single experience entry"""
        relevance_score = 0.0
        matching_aspects = []
        technology_overlap = []
        
        exp_text = (
            f"{experience.title} {experience.company} " +
            " ".join(b.text for b in experience.bullets)
        ).lower()
        
        # 1. Job title similarity (30%)
        title_score = self._compare_job_titles(
            experience.title,
            job_requirements.job_title
        )
        relevance_score += title_score * 0.3
        
        if title_score > 0.5:
            matching_aspects.append(f"Similar role: {experience.title}")
        
        # 2. Domain match (30%)
        domain_score = 0.0
        for domain in job_requirements.domain_experience_required:
            if self._has_domain_experience(exp_text, domain):
                domain_score += 1.0
                matching_aspects.append(f"Domain: {domain}")
        
        if job_requirements.domain_experience_required:
            domain_score /= len(job_requirements.domain_experience_required)
        
        relevance_score += domain_score * 0.3
        
        # 3. Technology overlap (40%)
        required_techs = list(job_requirements.required_skills.keys())
        for tech in required_techs:
            if tech.lower() in exp_text:
                technology_overlap.append(tech)
        
        tech_score = len(technology_overlap) / len(required_techs) if required_techs else 0
        relevance_score += tech_score * 0.4
        
        if technology_overlap:
            matching_aspects.append(f"Technologies: {', '.join(technology_overlap[:3])}")
        
        # Calculate duration
        duration_months = self._calculate_duration(
            experience.start_date,
            experience.end_date
        )
        
        # Calculate recency (more recent = higher score)
        recency_score = self._calculate_recency(experience.end_date)
        
        # Domain match boolean
        domain_match = domain_score > 0.5
        
        return ExperienceMatch(
            job_title=experience.title,
            company=experience.company,
            relevance_score=relevance_score,
            matching_aspects=matching_aspects,
            duration_months=duration_months,
            recency_score=recency_score,
            domain_match=domain_match,
            technology_overlap=technology_overlap
        )
    
    def _compare_job_titles(self, candidate_title: str, required_title: str) -> float:
        """Compare job title similarity"""
        candidate_lower = candidate_title.lower()
        required_lower = required_title.lower()
        
        # Exact match
        if candidate_lower == required_lower:
            return 1.0
        
        # Extract key words
        candidate_words = set(re.findall(r'\w+', candidate_lower))
        required_words = set(re.findall(r'\w+', required_lower))
        
        # Remove common words
        stopwords = {'senior', 'junior', 'lead', 'staff', 'principal', 'engineer', 'developer'}
        candidate_words -= stopwords
        required_words -= stopwords
        
        # Jaccard similarity
        if not candidate_words and not required_words:
            return 0.5
        
        intersection = candidate_words & required_words
        union = candidate_words | required_words
        
        return len(intersection) / len(union) if union else 0.0
    
    def _has_domain_experience(self, text: str, domain: str) -> bool:
        """Check if experience text shows domain expertise"""
        domain_lower = domain.lower()
        
        # Direct mention
        if domain_lower in text:
            return True
        
        # Check domain keywords
        if domain_lower in self.DOMAIN_KEYWORDS:
            keywords = self.DOMAIN_KEYWORDS[domain_lower]
            return any(kw in text for kw in keywords)
        
        return False
    
    def _calculate_duration(self, start_date: str, end_date: str) -> int:
        """Calculate duration in months"""
        # Simple heuristic: extract years
        # In production, use proper date parsing
        
        if not start_date:
            return 12  # Default 1 year
        
        # Extract years
        start_year = self._extract_year(start_date)
        end_year = self._extract_year(end_date) if end_date and 'present' not in end_date.lower() else datetime.now().year
        
        if start_year and end_year:
            return (end_year - start_year) * 12
        
        return 12
    
    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from date string"""
        if not date_str:
            return None
        
        match = re.search(r'20\d{2}|19\d{2}', date_str)
        if match:
            return int(match.group(0))
        
        return None
    
    def _calculate_recency(self, end_date: str) -> float:
        """Calculate recency score (0-1, higher = more recent)"""
        if not end_date:
            return 0.5
        
        if 'present' in end_date.lower():
            return 1.0
        
        end_year = self._extract_year(end_date)
        if not end_year:
            return 0.5
        
        current_year = datetime.now().year
        years_ago = current_year - end_year
        
        # Exponential decay
        if years_ago == 0:
            return 1.0
        elif years_ago == 1:
            return 0.9
        elif years_ago == 2:
            return 0.7
        elif years_ago <= 5:
            return 0.5
        else:
            return 0.3
    
    def calculate_experience_fit_score(
        self,
        matches: List[ExperienceMatch],
        min_years_required: int
    ) -> float:
        """
        Calculate overall experience fit score (0-100)
        """
        if not matches:
            return 0.0
        
        # 1. Total years of relevant experience (40%)
        total_months = sum(m.duration_months for m in matches if m.relevance_score > 0.5)
        total_years = total_months / 12
        
        years_score = min(total_years / min_years_required, 1.0) if min_years_required > 0 else 1.0
        
        # 2. Relevance of experience (40%)
        avg_relevance = sum(m.relevance_score for m in matches) / len(matches)
        
        # 3. Recency (20%)
        avg_recency = sum(m.recency_score for m in matches) / len(matches)
        
        total_score = (
            years_score * 0.4 +
            avg_relevance * 0.4 +
            avg_recency * 0.2
        ) * 100
        
        return min(total_score, 100.0)
    
    def determine_experience_level(
        self,
        resume: ParsedResume
    ) -> ExperienceLevel:
        """Determine candidate's experience level"""
        # Count total years (approximate)
        total_months = 0
        
        for exp in resume.experience:
            duration = self._calculate_duration(exp.start_date, exp.end_date)
            total_months += duration
        
        total_years = total_months / 12
        
        if total_years >= 7:
            return ExperienceLevel.SENIOR
        elif total_years >= 3:
            return ExperienceLevel.MID
        elif total_years >= 1:
            return ExperienceLevel.JUNIOR
        else:
            return ExperienceLevel.ENTRY

