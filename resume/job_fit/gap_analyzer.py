# resume/job_fit/gap_analyzer.py
import logging
from typing import List, Dict, Tuple

from resume.job_fit.models import SkillGap, SkillLevel

logger = logging.getLogger(__name__)


class GapAnalyzer:
    """
    Analyze gaps and provide development recommendations
    """
    
    # Training time estimates
    TRAINING_ESTIMATES = {
        (SkillLevel.NONE, SkillLevel.BEGINNER): "1-3 months",
        (SkillLevel.NONE, SkillLevel.INTERMEDIATE): "3-6 months",
        (SkillLevel.NONE, SkillLevel.ADVANCED): "6-12 months",
        (SkillLevel.NONE, SkillLevel.EXPERT): "1-2 years",
        (SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE): "2-4 months",
        (SkillLevel.BEGINNER, SkillLevel.ADVANCED): "4-8 months",
        (SkillLevel.BEGINNER, SkillLevel.EXPERT): "8-18 months",
        (SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED): "3-6 months",
        (SkillLevel.INTERMEDIATE, SkillLevel.EXPERT): "6-12 months",
        (SkillLevel.ADVANCED, SkillLevel.EXPERT): "3-6 months",
    }
    
    def __init__(self):
        pass
    
    def analyze_gaps(
        self,
        skill_gaps: List[SkillGap]
    ) -> Tuple[List[SkillGap], List[str]]:
        """
        Analyze gaps and enrich with training estimates
        
        Returns:
            (enriched_gaps, development_recommendations)
        """
        logger.info(f"Analyzing {len(skill_gaps)} skill gaps")
        
        enriched_gaps = []
        recommendations = []
        
        # Enrich each gap
        for gap in skill_gaps:
            enriched_gap = self._enrich_gap(gap)
            enriched_gaps.append(enriched_gap)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(enriched_gaps)
        
        return enriched_gaps, recommendations
    
    def _enrich_gap(self, gap: SkillGap) -> SkillGap:
        """Add training time and learnability assessment"""
        # Estimate training time
        key = (gap.current_level, gap.required_level)
        training_time = self.TRAINING_ESTIMATES.get(key, "6-12 months")
        
        # Assess if can learn (some skills are hard to learn quickly)
        can_learn = self._can_learn_skill(gap.skill_name, gap.current_level)
        
        # Update gap severity based on importance and training time
        if gap.importance >= 0.9 and "year" in training_time:
            gap_severity = "critical"
        elif gap.importance >= 0.7:
            gap_severity = "moderate"
        else:
            gap_severity = "minor"
        
        return SkillGap(
            skill_name=gap.skill_name,
            required_level=gap.required_level,
            current_level=gap.current_level,
            importance=gap.importance,
            gap_severity=gap_severity,
            training_time=training_time,
            can_learn=can_learn
        )
    
    def _can_learn_skill(self, skill: str, current_level: SkillLevel) -> bool:
        """Assess if skill can be reasonably learned"""
        # Some skills are harder to learn than others
        hard_skills = ['architecture', 'system design', 'leadership']
        
        skill_lower = skill.lower()
        
        # If hard skill and no experience, may be difficult
        if any(hard in skill_lower for hard in hard_skills) and current_level == SkillLevel.NONE:
            return False
        
        # Most technical skills can be learned
        return True
    
    def _generate_recommendations(self, gaps: List[SkillGap]) -> List[str]:
        """Generate development recommendations"""
        recommendations = []
        
        # Group by severity
        critical = [g for g in gaps if g.gap_severity == "critical"]
        moderate = [g for g in gaps if g.gap_severity == "moderate"]
        
        # Critical gaps
        if critical:
            rec = "Critical Skills to Develop:\n"
            for gap in critical[:3]:
                rec += f"  • {gap.skill_name} (Est. time: {gap.training_time})\n"
            recommendations.append(rec)
        
        # Moderate gaps
        if moderate:
            rec = "Additional Skills to Consider:\n"
            for gap in moderate[:3]:
                rec += f"  • {gap.skill_name} (Est. time: {gap.training_time})\n"
            recommendations.append(rec)
        
        # Learning suggestions
        if critical:
            recommendations.append(
                "Suggested Learning Path:\n"
                "  1. Start with hands-on projects in critical skills\n"
                "  2. Consider online courses (Udemy, Coursera, Pluralsight)\n"
                "  3. Pursue relevant certifications\n"
                "  4. Contribute to open-source projects"
            )
        
        return recommendations

