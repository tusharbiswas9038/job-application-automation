# resume/job_fit/career_trajectory.py
import logging
from typing import List, Tuple, Optional
import re

from resume.models import ParsedResume, ExperienceEntry
from resume.job_fit.models import CareerTrajectory, ExperienceLevel

logger = logging.getLogger(__name__)


class CareerTrajectoryAnalyzer:
    """
    Analyze career progression and trajectory
    """
    
    # Title level indicators
    LEVEL_KEYWORDS = {
        'senior': ['senior', 'sr', 'lead', 'principal', 'staff'],
        'mid': ['engineer', 'developer', 'administrator', 'analyst'],
        'junior': ['junior', 'jr', 'associate'],
        'entry': ['intern', 'trainee', 'apprentice'],
    }
    
    def __init__(self):
        pass
    
    def analyze_trajectory(self, resume: ParsedResume) -> CareerTrajectory:
        """
        Analyze career progression
        
        Returns:
            CareerTrajectory object
        """
        logger.info("Analyzing career trajectory")
        
        if not resume.experience:
            return CareerTrajectory(
                current_level=ExperienceLevel.ENTRY,
                progression_trend="unknown",
                promotions_count=0,
                avg_tenure_months=0.0,
                specialization=[],
                growth_areas=[],
                ready_for_level=ExperienceLevel.ENTRY
            )
        
        # Determine current level
        current_level = self._determine_level(resume.experience[0])
        
        # Analyze progression
        progression_trend = self._analyze_progression(resume.experience)
        
        # Count promotions (title changes within same company)
        promotions = self._count_promotions(resume.experience)
        
        # Calculate average tenure
        avg_tenure = self._calculate_avg_tenure(resume.experience)
        
        # Identify specialization areas
        specialization = self._identify_specialization(resume)
        
        # Identify growth areas
        growth_areas = self._identify_growth_areas(resume)
        
        # Determine readiness for next level
        ready_for = self._determine_readiness(
            current_level,
            progression_trend,
            promotions,
            avg_tenure
        )
        
        return CareerTrajectory(
            current_level=current_level,
            progression_trend=progression_trend,
            promotions_count=promotions,
            avg_tenure_months=avg_tenure,
            specialization=specialization,
            growth_areas=growth_areas,
            ready_for_level=ready_for
        )
    
    def _determine_level(self, experience: ExperienceEntry) -> ExperienceLevel:
        """Determine experience level from job title"""
        title_lower = experience.title.lower()
        
        # Check for level indicators in title
        if any(kw in title_lower for kw in self.LEVEL_KEYWORDS['senior']):
            return ExperienceLevel.SENIOR
        elif any(kw in title_lower for kw in self.LEVEL_KEYWORDS['junior']):
            return ExperienceLevel.JUNIOR
        elif any(kw in title_lower for kw in self.LEVEL_KEYWORDS['entry']):
            return ExperienceLevel.ENTRY
        else:
            # Default to mid-level
            return ExperienceLevel.MID
    
    def _analyze_progression(self, experiences: List[ExperienceEntry]) -> str:
        """Analyze progression trend (upward, lateral, downward)"""
        if len(experiences) < 2:
            return "insufficient_data"
        
        levels = [self._determine_level(exp) for exp in experiences]
        level_scores = {
            ExperienceLevel.ENTRY: 1,
            ExperienceLevel.JUNIOR: 2,
            ExperienceLevel.MID: 3,
            ExperienceLevel.SENIOR: 4
        }
        
        scores = [level_scores[level] for level in levels]
        
        # Check if generally increasing (allowing for some fluctuation)
        upward_moves = sum(1 for i in range(len(scores)-1) if scores[i] > scores[i+1])
        downward_moves = sum(1 for i in range(len(scores)-1) if scores[i] < scores[i+1])
        
        if upward_moves > downward_moves:
            return "upward"
        elif downward_moves > upward_moves:
            return "downward"
        else:
            return "lateral"
    
    def _count_promotions(self, experiences: List[ExperienceEntry]) -> int:
        """Count internal promotions (title changes at same company)"""
        promotions = 0
        
        for i in range(len(experiences) - 1):
            current = experiences[i]
            next_exp = experiences[i + 1]
            
            # Same company but different (better) title
            if current.company == next_exp.company:
                current_level = self._determine_level(current)
                next_level = self._determine_level(next_exp)
                
                level_scores = {
                    ExperienceLevel.ENTRY: 1,
                    ExperienceLevel.JUNIOR: 2,
                    ExperienceLevel.MID: 3,
                    ExperienceLevel.SENIOR: 4
                }
                
                if level_scores[current_level] > level_scores[next_level]:
                    promotions += 1
        
        return promotions
    
    def _calculate_avg_tenure(self, experiences: List[ExperienceEntry]) -> float:
        """Calculate average tenure per role in months"""
        if not experiences:
            return 0.0
        
        total_months = 0
        
        for exp in experiences:
            # Simplified: extract years
            start_year = self._extract_year(exp.start_date)
            end_year = self._extract_year(exp.end_date) if exp.end_date else 2025
            
            if start_year and end_year:
                months = (end_year - start_year) * 12
                total_months += max(months, 1)  # At least 1 month
        
        return total_months / len(experiences)
    
    def _extract_year(self, date_str: str) -> int:
        """Extract year from date string"""
        if not date_str:
            return None
        
        match = re.search(r'20\d{2}|19\d{2}', date_str)
        if match:
            return int(match.group(0))
        
        return None
    
    def _identify_specialization(self, resume: ParsedResume) -> List[str]:
        """Identify areas of specialization"""
        specializations = []
        
        # Analyze all text
        all_text = " ".join([
            resume.summary or "",
            *[b.text for b in resume.all_bullets]
        ]).lower()
        
        # Check for specialization keywords
        spec_keywords = {
            'kafka_streaming': ['kafka', 'streaming', 'real-time', 'event-driven'],
            'devops': ['devops', 'ci/cd', 'automation', 'infrastructure'],
            'cloud_architecture': ['cloud', 'aws', 'azure', 'architecture'],
            'data_engineering': ['data pipeline', 'etl', 'data processing'],
            'sre': ['sre', 'reliability', 'monitoring', 'observability'],
        }
        
        for spec_name, keywords in spec_keywords.items():
            matches = sum(1 for kw in keywords if kw in all_text)
            if matches >= 2:  # At least 2 keywords
                specializations.append(spec_name.replace('_', ' ').title())
        
        return specializations
    
    def _identify_growth_areas(self, resume: ParsedResume) -> List[str]:
        """Identify areas where candidate is growing"""
        growth_areas = []
        
        # Look for recent additions (in most recent role)
        if not resume.experience:
            return growth_areas
        
        recent_exp = resume.experience[0]
        recent_text = " ".join([b.text for b in recent_exp.bullets]).lower()
        
        # Look for learning indicators
        learning_keywords = [
            'learned', 'developed expertise', 'expanded knowledge',
            'gained experience', 'training', 'certification'
        ]
        
        for keyword in learning_keywords:
            if keyword in recent_text:
                # Extract context
                sentences = recent_text.split('.')
                for sentence in sentences:
                    if keyword in sentence:
                        growth_areas.append(sentence.strip()[:100])
        
        return growth_areas[:3]  # Top 3
    
    def _determine_readiness(
        self,
        current_level: ExperienceLevel,
        trend: str,
        promotions: int,
        avg_tenure: float
    ) -> ExperienceLevel:
        """Determine readiness for next level"""
        level_progression = {
            ExperienceLevel.ENTRY: ExperienceLevel.JUNIOR,
            ExperienceLevel.JUNIOR: ExperienceLevel.MID,
            ExperienceLevel.MID: ExperienceLevel.SENIOR,
            ExperienceLevel.SENIOR: ExperienceLevel.SENIOR,
        }
        
        # If upward trajectory and reasonable tenure, ready for next level
        if trend == "upward" and avg_tenure >= 18:  # 1.5+ years avg
            return level_progression.get(current_level, current_level)
        
        # If promoted recently, ready for current level
        if promotions > 0:
            return current_level
        
        # Otherwise, might need more time
        return current_level
    
    def calculate_trajectory_fit_score(
        self,
        trajectory: CareerTrajectory,
        required_level: ExperienceLevel
    ) -> float:
        """
        Calculate trajectory fit score (0-100)
        """
        score = 0.0
        
        # 1. Level match (50%)
        level_scores = {
            ExperienceLevel.ENTRY: 1,
            ExperienceLevel.JUNIOR: 2,
            ExperienceLevel.MID: 3,
            ExperienceLevel.SENIOR: 4
        }
        
        current_score = level_scores[trajectory.current_level]
        required_score = level_scores[required_level]
        
        if current_score >= required_score:
            score += 50
        else:
            # Partial credit
            score += (current_score / required_score) * 50
        
        # 2. Progression (20%)
        if trajectory.is_progressing:
            score += 20
        elif trajectory.progression_trend == "lateral":
            score += 10
        
        # 3. Promotions (15%)
        if trajectory.promotions_count >= 2:
            score += 15
        elif trajectory.promotions_count == 1:
            score += 10
        
        # 4. Tenure stability (15%)
        if 18 <= trajectory.avg_tenure_months <= 48:  # 1.5-4 years
            score += 15
        elif 12 <= trajectory.avg_tenure_months < 18:
            score += 10
        
        return min(score, 100.0)

