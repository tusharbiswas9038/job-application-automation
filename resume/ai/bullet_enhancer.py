# resume/ai/bullet_enhancer.py
import logging
from typing import List, Optional, Tuple
import re

from resume.models import BulletPoint
from resume.ai.ollama_client import OllamaClient
from resume.ai.models import BulletEnhancement

logger = logging.getLogger(__name__)


class BulletEnhancer:
    """
    Enhance resume bullets using AI
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        min_confidence: float = 0.7
    ):
        """
        Initialize bullet enhancer
        
        Args:
            ollama_client: Ollama client (creates default if None)
            min_confidence: Minimum confidence to accept enhancement
        """
        self.ollama = ollama_client or OllamaClient()
        self.min_confidence = min_confidence
    
    def enhance_bullet(
        self,
        bullet: BulletPoint,
        job_title: str,
        missing_keywords: List[str]
    ) -> Optional[BulletEnhancement]:
        """
        Enhance a single bullet point
        
        Args:
            bullet: Original bullet
            job_title: Target job title
            missing_keywords: Keywords to add
        
        Returns:
            BulletEnhancement or None if failed/low confidence
        """
        if not self.ollama.is_available():
            logger.warning("Ollama not available, skipping enhancement")
            return None
        
        # Generate enhanced version
        enhanced_text = self.ollama.enhance_bullet(
            bullet_text=bullet.text,
            job_title=job_title,
            keywords=missing_keywords,
            temperature=0.3
        )
        
        if not enhanced_text:
            return None
        
        # Clean up enhanced text
        enhanced_text = self._clean_bullet(enhanced_text)
        
        # Calculate improvement metrics
        keywords_added = self._find_added_keywords(
            bullet.text,
            enhanced_text,
            missing_keywords
        )
        
        improvement_score = self._calculate_improvement(
            bullet.text,
            enhanced_text,
            keywords_added
        )
        
        # Estimate confidence
        confidence = self._estimate_confidence(
            bullet.text,
            enhanced_text
        )
        
        # Only return if meets confidence threshold
        if confidence < self.min_confidence:
            logger.info(f"Enhancement confidence too low: {confidence:.2f}")
            return None
        
        return BulletEnhancement(
            original_text=bullet.text,
            enhanced_text=enhanced_text,
            keywords_added=keywords_added,
            improvement_score=improvement_score,
            confidence=confidence
        )
    
    def enhance_bullets_batch(
        self,
        bullets: List[BulletPoint],
        job_title: str,
        missing_keywords: List[str],
        max_enhancements: int = 5
    ) -> List[BulletEnhancement]:
        """
        Enhance multiple bullets
        
        Args:
            bullets: Bullets to enhance
            job_title: Target job
            missing_keywords: Keywords to incorporate
            max_enhancements: Max bullets to enhance
        
        Returns:
            List of successful enhancements
        """
        logger.info(f"Enhancing up to {max_enhancements} bullets")
        
        enhancements = []
        
        # Prioritize bullets with:
        # 1. Low keyword coverage
        # 2. High quality (action verb, metrics)
        # 3. Relevant to job
        
        for bullet in bullets[:max_enhancements * 2]:  # Try more than max
            enhancement = self.enhance_bullet(
                bullet,
                job_title,
                missing_keywords[:3]  # Focus on top keywords
            )
            
            if enhancement:
                enhancements.append(enhancement)
            
            if len(enhancements) >= max_enhancements:
                break
        
        logger.info(f"Enhanced {len(enhancements)} bullets")
        return enhancements
    
    def _clean_bullet(self, text: str) -> str:
        """Clean up AI-generated bullet"""
        # Remove quotes
        text = text.strip('"\'')
        
        # Remove bullet markers if AI added them
        text = re.sub(r'^[\-\*•]\s*', '', text)
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Ensure starts with capital
        if text:
            text = text[0].upper() + text[1:]
        
        return text.strip()
    
    def _find_added_keywords(
        self,
        original: str,
        enhanced: str,
        target_keywords: List[str]
    ) -> List[str]:
        """Find which keywords were successfully added"""
        original_lower = original.lower()
        enhanced_lower = enhanced.lower()
        
        added = []
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower not in original_lower and keyword_lower in enhanced_lower:
                added.append(keyword)
        
        return added
    
    def _calculate_improvement(
        self,
        original: str,
        enhanced: str,
        keywords_added: List[str]
    ) -> float:
        """Calculate improvement score (0-1)"""
        score = 0.0
        
        # Keywords added (0.5 points)
        if keywords_added:
            score += min(len(keywords_added) * 0.15, 0.5)
        
        # Has quantification (0.3 points)
        if re.search(r'\d+[\%\+]?', enhanced):
            score += 0.3
        
        # Action verb (0.2 points)
        action_verbs = [
            'managed', 'developed', 'implemented', 'optimized',
            'designed', 'automated', 'configured', 'deployed'
        ]
        if any(verb in enhanced.lower() for verb in action_verbs):
            score += 0.2
        
        return min(score, 1.0)
    
    def _estimate_confidence(
        self,
        original: str,
        enhanced: str
    ) -> float:
        """Estimate confidence in enhancement"""
        # Simple heuristics
        
        # Length reasonable (not too different)
        orig_len = len(original.split())
        enh_len = len(enhanced.split())
        
        if enh_len > orig_len * 2 or enh_len < orig_len * 0.5:
            return 0.5  # Length changed drastically
        
        # Contains key original terms
        orig_words = set(original.lower().split())
        enh_words = set(enhanced.lower().split())
        overlap = len(orig_words & enh_words) / len(orig_words) if orig_words else 0
        
        if overlap < 0.3:
            return 0.6  # Too different
        
        # Looks professional (no weird chars, proper capitalization)
        if not enhanced[0].isupper():
            return 0.7
        
        return 0.9  # High confidence

