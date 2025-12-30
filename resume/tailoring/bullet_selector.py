# resume/tailoring/bullet_selector.py
import logging
from typing import List, Dict, Tuple
import re

from resume.models import ParsedResume, BulletPoint, ExperienceEntry
from resume.ats.keyword_extractor import KeywordExtractor
from resume.ats.matcher import KeywordMatcher
from resume.tailoring.models import (
    SelectedBullet, ExperienceSection, VariantGenerationConfig
)

logger = logging.getLogger(__name__)


class BulletSelector:
    """
    Intelligently select best bullets for a job
    """
    
    def __init__(self, config: VariantGenerationConfig):
        self.config = config
        self.keyword_extractor = KeywordExtractor()
        self.matcher = KeywordMatcher()
    
    def select_bullets(
        self,
        resume: ParsedResume,
        jd_text: str,
        jd_keywords: List[str]
    ) -> List[ExperienceSection]:
        """
        Select best bullets for the job
        
        Args:
            resume: Parsed resume
            jd_text: Job description text
            jd_keywords: Important keywords from JD
        
        Returns:
            List of ExperienceSection with selected bullets
        """
        logger.info(f"Selecting bullets for resume with {len(resume.experience)} experience entries")
        
        sections = []
        total_bullets_selected = 0
        target = self.config.target_bullets
        
        # Score all bullets across all experiences
        all_scored_bullets = []
        
        for exp in resume.experience:
            for bullet in exp.bullets:
                score = self._score_bullet(bullet, jd_keywords, jd_text)
                all_scored_bullets.append((exp, bullet, score))
        
        # Sort by score
        all_scored_bullets.sort(key=lambda x: x[2], reverse=True)
        
        # Select bullets per experience
        bullets_per_exp = {}
        
        for exp, bullet, score in all_scored_bullets:
            exp_id = id(exp)
            
            if exp_id not in bullets_per_exp:
                bullets_per_exp[exp_id] = {
                    'experience': exp,
                    'bullets': []
                }
            
            current_count = len(bullets_per_exp[exp_id]['bullets'])
            
            # Check constraints
            if current_count >= self.config.max_bullets_per_job:
                continue
            
            if total_bullets_selected >= target:
                break
            
            bullets_per_exp[exp_id]['bullets'].append((bullet, score))
            total_bullets_selected += 1
        
        # Ensure minimum bullets per experience
        for exp_id, data in bullets_per_exp.items():
            if len(data['bullets']) < self.config.min_bullets_per_job:
                exp = data['experience']
                # Add more bullets from this experience
                remaining = [b for b in exp.bullets if b not in [x[0] for x in data['bullets']]]
                need = self.config.min_bullets_per_job - len(data['bullets'])
                
                for bullet in remaining[:need]:
                    score = self._score_bullet(bullet, jd_keywords, jd_text)
                    data['bullets'].append((bullet, score))
        
        # Build ExperienceSection objects
        for exp_id, data in bullets_per_exp.items():
            exp = data['experience']
            selected_bullets = []
            
            for bullet, score in data['bullets']:
                reason = self._get_selection_reason(bullet, score, jd_keywords)
                selected_bullets.append(SelectedBullet(
                    bullet=bullet,
                    relevance_score=score,
                    selection_reason=reason
                ))
            
            sections.append(ExperienceSection(
                experience=exp,
                selected_bullets=selected_bullets,
                total_available=len(exp.bullets)
            ))
        
        logger.info(f"Selected {total_bullets_selected} bullets across {len(sections)} experiences")
        return sections
    
    def _score_bullet(
        self,
        bullet: BulletPoint,
        jd_keywords: List[str],
        jd_text: str
    ) -> float:
        """
        Score a bullet's relevance (0-1)
        
        Scoring factors:
        - Keyword matches (40%)
        - Has metrics/numbers (20%)
        - Action verb strength (15%)
        - Length appropriateness (10%)
        - Recency (15%)
        """
        score = 0.0
        text_lower = bullet.text.lower()
        
        # 1. Keyword matching (40%)
        matched_keywords = 0
        for keyword in jd_keywords[:20]:  # Top 20 keywords
            if keyword.lower() in text_lower:
                matched_keywords += 1
        
        keyword_score = min(matched_keywords / 5.0, 1.0) * 0.4
        score += keyword_score
        
        # 2. Has quantification (20%)
        if re.search(r'\d+[\%\+]?', bullet.text):
            score += 0.2
        
        # 3. Strong action verb (15%)
        strong_verbs = [
            'architected', 'designed', 'implemented', 'optimized',
            'automated', 'led', 'managed', 'developed', 'deployed',
            'reduced', 'increased', 'improved', 'scaled'
        ]
        
        first_word = bullet.text.split()[0].lower() if bullet.text else ""
        if first_word in strong_verbs:
            score += 0.15
        elif any(verb in text_lower for verb in strong_verbs):
            score += 0.10
        
        # 4. Length appropriateness (10%)
        word_count = len(bullet.text.split())
        if 10 <= word_count <= 25:
            score += 0.10
        elif 8 <= word_count <= 30:
            score += 0.05
        
        # 5. Recency (15%) - from subsection if available
        # Most recent job gets full points
        if bullet.subsection and "present" in bullet.subsection.lower():
            score += 0.15
        elif bullet.subsection and any(year in bullet.subsection for year in ['2024', '2023', '2022']):
            score += 0.10
        else:
            score += 0.05
        
        return min(score, 1.0)
    
    def _get_selection_reason(
        self,
        bullet: BulletPoint,
        score: float,
        jd_keywords: List[str]
    ) -> str:
        """Generate human-readable selection reason"""
        reasons = []
        
        # Check why it scored high
        text_lower = bullet.text.lower()
        
        # Keyword matches
        matched = [kw for kw in jd_keywords[:10] if kw.lower() in text_lower]
        if matched:
            reasons.append(f"Matches keywords: {', '.join(matched[:3])}")
        
        # Has metrics
        if re.search(r'\d+[\%\+]?', bullet.text):
            reasons.append("Contains quantifiable results")
        
        # Strong action
        strong_verbs = ['architected', 'designed', 'implemented', 'optimized', 'automated', 'led']
        if any(verb in text_lower for verb in strong_verbs):
            reasons.append("Strong action verb")
        
        # High relevance
        if score >= 0.8:
            reasons.append("High relevance score")
        
        return "; ".join(reasons) if reasons else "Relevant to role"
    
    def reorder_bullets_by_relevance(
        self,
        sections: List[ExperienceSection]
    ) -> List[ExperienceSection]:
        """Reorder bullets within each section by relevance"""
        for section in sections:
            section.selected_bullets.sort(
                key=lambda sb: sb.relevance_score,
                reverse=True
            )
        
        return sections

