# resume/bullet_manager.py
import logging
import hashlib
from typing import List, Dict, Optional
from dataclasses import asdict

from resume.models import BulletPoint, ParsedResume

logger = logging.getLogger(__name__)


class BulletManager:
    """Manage bullet points for resume variants"""
    
    def __init__(self):
        self.bullets_by_id: Dict[str, BulletPoint] = {}
        self.bullets_by_section: Dict[str, List[BulletPoint]] = {}
    
    def load_from_resume(self, resume: ParsedResume):
        """Load bullets from parsed resume"""
        self.bullets_by_id.clear()
        self.bullets_by_section.clear()
        
        for bullet in resume.all_bullets:
            self.bullets_by_id[bullet.id] = bullet
            
            if bullet.section not in self.bullets_by_section:
                self.bullets_by_section[bullet.section] = []
            self.bullets_by_section[bullet.section].append(bullet)
        
        logger.info(f"Loaded {len(self.bullets_by_id)} bullets")
    
    def get_bullet(self, bullet_id: str) -> Optional[BulletPoint]:
        """Get bullet by ID"""
        return self.bullets_by_id.get(bullet_id)
    
    def get_modifiable_bullets(self) -> List[BulletPoint]:
        """Get all modifiable bullets"""
        return [b for b in self.bullets_by_id.values() if b.is_modifiable]
    
    def get_bullets_by_section(self, section: str) -> List[BulletPoint]:
        """Get bullets from specific section"""
        return self.bullets_by_section.get(section, [])
    
    def get_bullets_by_company(self, company: str) -> List[BulletPoint]:
        """Get experience bullets for specific company"""
        return [
            b for b in self.bullets_by_id.values()
            if b.section == 'experience' and b.subsection == company
        ]
    
    def filter_by_keywords(self, keywords: List[str]) -> List[BulletPoint]:
        """Filter bullets containing specific keywords"""
        keywords_lower = [kw.lower() for kw in keywords]
        
        matching_bullets = []
        for bullet in self.bullets_by_id.values():
            text_lower = bullet.text.lower()
            if any(kw in text_lower for kw in keywords_lower):
                matching_bullets.append(bullet)
        
        return matching_bullets
    
    def rank_bullets_for_job(
        self,
        job_keywords: List[str],
        target_section: Optional[str] = None
    ) -> List[tuple[BulletPoint, float]]:
        """
        Rank bullets by relevance to job keywords
        
        Args:
            job_keywords: Keywords from job description
            target_section: Optional section filter
        
        Returns:
            List of (bullet, score) tuples sorted by score
        """
        keywords_lower = set(kw.lower() for kw in job_keywords)
        ranked = []
        
        bullets = (
            self.get_bullets_by_section(target_section) if target_section
            else list(self.bullets_by_id.values())
        )
        
        for bullet in bullets:
            if not bullet.is_modifiable:
                continue
            
            text_lower = bullet.text.lower()
            words = set(text_lower.split())
            
            # Calculate overlap score
            overlap = len(keywords_lower & words)
            score = overlap / len(keywords_lower) * 100 if keywords_lower else 0
            
            if score > 0:
                ranked.append((bullet, score))
        
        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked
    
    def generate_bullet_id(self, section: str, subsection: str, index: int) -> str:
        """Generate unique bullet ID"""
        base = f"{section}_{subsection}_{index}".replace(' ', '_')
        return base.lower()
    
    def validate_bullet(self, bullet: BulletPoint, min_length: int = 20, max_length: int = 200) -> tuple[bool, List[str]]:
        """
        Validate bullet point
        
        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        
        if not bullet.text:
            errors.append("empty_text")
        
        if len(bullet.text) < min_length:
            errors.append(f"too_short_{len(bullet.text)}_chars")
        
        if len(bullet.text) > max_length:
            errors.append(f"too_long_{len(bullet.text)}_chars")
        
        # Check for weak verbs
        weak_verbs = ['worked on', 'helped with', 'responsible for', 'involved in']
        text_lower = bullet.text.lower()
        if any(verb in text_lower for verb in weak_verbs):
            errors.append("weak_verb")
        
        # Check starts with verb
        first_word = bullet.text.split()[0].lower()
        if first_word in ['the', 'a', 'an']:
            errors.append("doesnt_start_with_verb")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def export_bullets(self, output_file: str):
        """Export bullets to JSON for analysis"""
        import json
        
        data = {
            'total_bullets': len(self.bullets_by_id),
            'modifiable_bullets': len(self.get_modifiable_bullets()),
            'sections': {
                section: len(bullets)
                for section, bullets in self.bullets_by_section.items()
            },
            'bullets': [asdict(b) for b in self.bullets_by_id.values()]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported bullets to {output_file}")

