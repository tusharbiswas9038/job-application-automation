# resume/job_fit/fit_scorer.py
import logging
from typing import Tuple, List, Optional

from resume.models import ParsedResume
from resume.job_fit.models import (
    JobFitScore, JobRequirements, FitLevel, SkillLevel
)
from resume.job_fit.skill_matcher import SkillMatcher
from resume.job_fit.experience_evaluator import ExperienceEvaluator
from resume.job_fit.career_trajectory import CareerTrajectoryAnalyzer
from resume.job_fit.culture_analyzer import CultureFitAnalyzer
from resume.job_fit.gap_analyzer import GapAnalyzer

logger = logging.getLogger(__name__)


class JobFitScorer:
    """
    Calculate comprehensive job fit score
    """
    
    # Weight distribution
    WEIGHTS = {
        'skill': 0.35,           # 35% - Skills most important
        'experience': 0.30,      # 30% - Experience relevance
        'trajectory': 0.15,      # 15% - Career progression
        'culture': 0.10,         # 10% - Cultural fit
        'education': 0.10,       # 10% - Education fit
    }
    
    def __init__(self):
        self.skill_matcher = SkillMatcher()
        self.experience_evaluator = ExperienceEvaluator()
        self.trajectory_analyzer = CareerTrajectoryAnalyzer()
        self.culture_analyzer = CultureFitAnalyzer()
        self.gap_analyzer = GapAnalyzer()
    
    def score_fit(
        self,
        resume: ParsedResume,
        job_requirements: JobRequirements
    ) -> JobFitScore:
        """
        Calculate comprehensive job fit score
        
        Args:
            resume: Parsed resume
            job_requirements: Structured job requirements
        
        Returns:
            JobFitScore object with complete analysis
        """
        logger.info(f"Scoring fit for: {job_requirements.job_title}")
        
        # 1. Skill matching
        skill_matches, skill_gaps = self.skill_matcher.match_skills(
            resume, job_requirements
        )
        skill_fit = self.skill_matcher.calculate_skill_fit_score(
            skill_matches, skill_gaps
        )
        
        # 2. Experience evaluation
        experience_matches = self.experience_evaluator.evaluate_experience(
            resume, job_requirements
        )
        experience_fit = self.experience_evaluator.calculate_experience_fit_score(
            experience_matches, job_requirements.min_years_experience
        )
        
        # 3. Career trajectory
        trajectory = self.trajectory_analyzer.analyze_trajectory(resume)
        trajectory_fit = self.trajectory_analyzer.calculate_trajectory_fit_score(
            trajectory, job_requirements.experience_level
        )
        
        # 4. Culture fit
        culture_indicators = self.culture_analyzer.analyze_culture_fit(
            resume, job_requirements
        )
        culture_fit = culture_indicators.fit_score * 100
        
        # 5. Education fit
        education_fit = self._calculate_education_fit(resume, job_requirements)
        
        # Calculate overall fit
        overall_fit = (
            skill_fit * self.WEIGHTS['skill'] +
            experience_fit * self.WEIGHTS['experience'] +
            trajectory_fit * self.WEIGHTS['trajectory'] +
            culture_fit * self.WEIGHTS['culture'] +
            education_fit * self.WEIGHTS['education']
        )
        
        # Determine fit level
        fit_level = self._determine_fit_level(overall_fit)
        
        # Analyze gaps and get recommendations
        enriched_gaps, development_recs = self.gap_analyzer.analyze_gaps(skill_gaps)
        
        # Identify strengths
        strengths = self._identify_strengths(
            skill_matches, experience_matches, trajectory
        )
        
        # Identify critical gaps
        critical_gaps = [
            f"{gap.skill_name} ({gap.required_level.value})"
            for gap in enriched_gaps
            if gap.gap_severity == "critical"
        ]
        
        return JobFitScore(
            overall_fit=overall_fit,
            fit_level=fit_level,
            skill_fit=skill_fit,
            experience_fit=experience_fit,
            culture_fit=culture_fit,
            trajectory_fit=trajectory_fit,
            education_fit=education_fit,
            skill_matches=skill_matches,
            skill_gaps=enriched_gaps,
            experience_matches=experience_matches,
            culture_indicators=culture_indicators,
            career_trajectory=trajectory,
            critical_gaps=critical_gaps,
            development_areas=development_recs,
            strengths=strengths,
            job_title=job_requirements.job_title,
            candidate_name=resume.personal.name or "Unknown"
        )
    
    def _calculate_education_fit(
        self,
        resume: ParsedResume,
        job_requirements: JobRequirements
    ) -> float:
        """Calculate education fit score"""
        if not resume.education:
            return 50.0  # Partial credit for no education listed
        
        score = 50.0  # Base score for having education
        
        # Check degree requirement
        if job_requirements.education_required:
            required_lower = job_requirements.education_required.lower()
            
            for edu in resume.education:
                degree_lower = edu.degree.lower()
                
                # Check match
                if required_lower in degree_lower or degree_lower in required_lower:
                    score += 30.0
                    break
        else:
            score += 20.0  # No specific requirement
        
        # Check certifications
        cert_match = False
        for required_cert in job_requirements.certifications_required:
            for cert in resume.certifications:
                if required_cert.lower() in cert.lower():
                    cert_match = True
                    break
        
        if cert_match:
            score += 20.0
        elif resume.certifications:
            score += 10.0  # Partial credit
        
        return min(score, 100.0)
    
    def _determine_fit_level(self, score: float) -> FitLevel:
        """Determine fit level from score"""
        if score >= 90:
            return FitLevel.EXCELLENT
        elif score >= 80:
            return FitLevel.STRONG
        elif score >= 70:
            return FitLevel.GOOD
        elif score >= 60:
            return FitLevel.MODERATE
        elif score >= 50:
            return FitLevel.WEAK
        else:
            return FitLevel.POOR
    
    def _identify_strengths(
        self,
        skill_matches,
        experience_matches,
        trajectory
    ) -> List[str]:
        """Identify candidate's key strengths"""
        strengths = []
        
        # Strong skill matches
        strong_skills = [
            m.skill_name for m in skill_matches
            if m.match_strength >= 0.9 and m.candidate_level in [SkillLevel.ADVANCED, SkillLevel.EXPERT]
        ]
        
        if strong_skills:
            strengths.append(f"Expert skills: {', '.join(strong_skills[:3])}")
        
        # Highly relevant experience
        relevant_exp = [
            m for m in experience_matches
            if m.relevance_score >= 0.8
        ]
        
        if relevant_exp:
            strengths.append(f"Highly relevant experience in {len(relevant_exp)} roles")
        
        # Career progression
        if trajectory.is_progressing:
            strengths.append("Strong upward career trajectory")
        
        if trajectory.promotions_count > 0:
            strengths.append(f"{trajectory.promotions_count} internal promotion(s)")
        
        # Specialization
        if trajectory.specialization:
            strengths.append(f"Specialized in: {', '.join(trajectory.specialization[:2])}")
        
        return strengths

