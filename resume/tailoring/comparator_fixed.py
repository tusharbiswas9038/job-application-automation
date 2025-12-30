# resume/tailoring/comparator.py

import logging
import difflib
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import re

from resume.models import ParsedResume, BulletPoint
from resume.parser.latex_parser import LaTeXResumeParser
from resume.tailoring.models import ResumeVariant

logger = logging.getLogger(__name__)

@dataclass
class BulletChange:
    """A change to a bullet point"""
    change_type: str  # "added", "removed", "modified", "reordered", "ai_enhanced"
    original_text: Optional[str]
    new_text: Optional[str]
    position_original: Optional[int]
    position_new: Optional[int]
    keywords_added: List[str] = field(default_factory=list)
    similarity_score: float = 0.0  # 0-1, how similar
    
    @property
    def is_significant(self) -> bool:
        """Is this a significant change?"""
        if self.change_type in ["added", "removed"]:
            return True
        if self.change_type == "ai_enhanced":
            return len(self.keywords_added) > 0
        if self.change_type == "modified":
            return self.similarity_score < 0.7
        return False


@dataclass
class SectionChange:
    """Changes to a section"""
    section_name: str
    original_content: str
    new_content: str
    change_type: str  # "modified", "unchanged", "added", "removed"
    word_count_delta: int
    keywords_added: List[str] = field(default_factory=list)
    
    @property
    def change_summary(self) -> str:
        """Human-readable summary"""
        if self.change_type == "unchanged":
            return "No changes"
        elif self.change_type == "modified":
            summary = f"Modified ({abs(self.word_count_delta)} words "
            summary += "added)" if self.word_count_delta > 0 else "removed)"
            if self.keywords_added:
                summary += f", +{len(self.keywords_added)} keywords"
            return summary
        return self.change_type.title()


@dataclass
class ResumeComparison:
    """Complete comparison between two resume versions"""
    original_path: str
    variant_path: str
    compared_at: datetime = field(default_factory=datetime.now)
    
    # Section-level changes
    summary_change: Optional[SectionChange] = None
    skills_change: Optional[SectionChange] = None
    
    # Bullet-level changes
    bullet_changes: List[BulletChange] = field(default_factory=list)
    
    # Statistics
    total_bullets_original: int = 0
    total_bullets_new: int = 0
    bullets_added: int = 0
    bullets_removed: int = 0
    bullets_modified: int = 0
    bullets_ai_enhanced: int = 0
    
    # Keywords
    keywords_added: List[str] = field(default_factory=list)
    keyword_density_original: float = 0.0
    keyword_density_new: float = 0.0
    
    # Overall metrics
    similarity_score: float = 0.0  # 0-1
    change_score: float = 0.0  # 0-100, how much changed
    
    @property
    def has_significant_changes(self) -> bool:
        """Are there significant changes?"""
        return self.change_score > 10.0
    
    @property
    def change_summary(self) -> str:
        """One-line summary"""
        parts = []
        if self.bullets_ai_enhanced:
            parts.append(f"{self.bullets_ai_enhanced} bullets enhanced")
        if self.keywords_added:
            parts.append(f"{len(self.keywords_added)} keywords added")
        if self.summary_change and self.summary_change.change_type != "unchanged":
            parts.append("summary updated")
        return ", ".join(parts) if parts else "no significant changes"


class ResumeComparator:
    """
    Compare two resume versions and generate detailed diff
    """
    
    def __init__(self):
        self.parser = LaTeXResumeParser()
    
    def compare(
        self,
        original_path: str,
        variant_path: str,
        variant: Optional[ResumeVariant] = None
    ) -> ResumeComparison:
        """
        Compare original and variant resumes
        
        Args:
            original_path: Path to original resume
            variant_path: Path to generated variant
            variant: Optional ResumeVariant object with metadata
            
        Returns:
            ResumeComparison object
        """
        logger.info(f"Comparing: {original_path} vs {variant_path}")
        
        # Parse both resumes
        original = self.parser.parse_file(original_path)
        new = self.parser.parse_file(variant_path)
        
        comparison = ResumeComparison(
            original_path=original_path,
            variant_path=variant_path
        )
        
        # Compare summary
        comparison.summary_change = self._compare_section(
            "Summary",
            original.summary or "",
            new.summary or ""
        )
        
        # Compare bullets
        comparison.bullet_changes = self._compare_bullets(
            original.all_bullets,
            new.all_bullets,
            variant
        )
        
        # Calculate statistics
        comparison.total_bullets_original = len(original.all_bullets)
        comparison.total_bullets_new = len(new.all_bullets)
        comparison.bullets_added = sum(
            1 for bc in comparison.bullet_changes if bc.change_type == "added"
        )
        comparison.bullets_removed = sum(
            1 for bc in comparison.bullet_changes if bc.change_type == "removed"
        )
        comparison.bullets_modified = sum(
            1 for bc in comparison.bullet_changes if bc.change_type == "modified"
        )
        comparison.bullets_ai_enhanced = sum(
            1 for bc in comparison.bullet_changes if bc.change_type == "ai_enhanced"
        )
        
        # Extract keywords added
        if variant:
            comparison.keywords_added = variant.keywords_added if hasattr(variant, 'keywords_added') else []
        else:
            comparison.keywords_added = self._extract_added_keywords(original, new)
        
        # Calculate similarity
        comparison.similarity_score = self._calculate_similarity(original, new)
        comparison.change_score = (1 - comparison.similarity_score) * 100
        
        return comparison
    
    def _compare_section(
        self,
        section_name: str,
        original: str,
        new: str
    ) -> SectionChange:
        """Compare a single section"""
        if original == new:
            change_type = "unchanged"
        elif not original:
            change_type = "added"
        elif not new:
            change_type = "removed"
        else:
            change_type = "modified"
        
        word_count_delta = len(new.split()) - len(original.split())
        
        # Find new keywords
        keywords_added = self._find_new_keywords(original, new)
        
        return SectionChange(
            section_name=section_name,
            original_content=original,
            new_content=new,
            change_type=change_type,
            word_count_delta=word_count_delta,
            keywords_added=keywords_added
        )
    
    def _compare_bullets(
        self,
        original_bullets: List[BulletPoint],
        new_bullets: List[BulletPoint],
        variant: Optional[ResumeVariant]
    ) -> List[BulletChange]:
        """Compare bullet points with better matching"""
        changes = []
        
        # Get AI-enhanced info if available
        ai_enhanced_map = {}
        if variant:
            # If variant is dict (from JSON), extract info
            if isinstance(variant, dict):
                variant_content = variant.get('content', {})
                for exp_section in variant_content.get('experience_sections', []):
                    for sb in exp_section.get('selected_bullets', []):
                        if sb.get('was_enhanced'):
                            ai_enhanced_map[sb['bullet']['text']] = sb['enhanced_version']
            # If variant is ResumeVariant object
            elif hasattr(variant, 'content') and variant.content:
                for exp_section in variant.content.experience_sections:
                    for sb in exp_section.selected_bullets:
                        if sb.was_enhanced:
                            ai_enhanced_map[sb.bullet.text] = sb.enhanced_version
        
        # Create text mapping
        orig_texts = [b.text for b in original_bullets]
        new_texts = [b.text for b in new_bullets]
        
        # Use fuzzy matching for better detection
        used_new = set()
        used_orig = set()
        
        # First pass: Find AI-enhanced bullets
        for i, orig_text in enumerate(orig_texts):
            if orig_text in ai_enhanced_map:
                enhanced_text = ai_enhanced_map[orig_text]
                
                # Find the enhanced version in new_texts
                for j, new_text in enumerate(new_texts):
                    if j in used_new:
                        continue
                    
                    # Check if this is the enhanced version
                    if new_text == enhanced_text or self._text_similarity(enhanced_text, new_text) > 0.8:
                        keywords_added = self._find_new_keywords(orig_text, new_text)
                        
                        changes.append(BulletChange(
                            change_type="ai_enhanced",
                            original_text=orig_text,
                            new_text=new_text,
                            position_original=i,
                            position_new=j,
                            keywords_added=keywords_added,
                            similarity_score=self._text_similarity(orig_text, new_text)
                        ))
                        
                        used_new.add(j)
                        used_orig.add(i)
                        break
        
        # Second pass: Match remaining bullets by similarity
        for i, orig_text in enumerate(orig_texts):
            if i in used_orig:
                continue
            
            best_match = None
            best_similarity = 0.0
            
            for j, new_text in enumerate(new_texts):
                if j in used_new:
                    continue
                
                similarity = self._text_similarity(orig_text, new_text)
                
                if similarity > best_similarity and similarity > 0.5:  # Threshold
                    best_similarity = similarity
                    best_match = j
            
            if best_match is not None:
                new_text = new_texts[best_match]
                keywords_added = self._find_new_keywords(orig_text, new_text)
                
                change_type = "modified" if best_similarity < 0.9 else "unchanged"
                
                changes.append(BulletChange(
                    change_type=change_type,
                    original_text=orig_text,
                    new_text=new_text,
                    position_original=i,
                    position_new=best_match,
                    keywords_added=keywords_added,
                    similarity_score=best_similarity
                ))
                
                used_new.add(best_match)
                used_orig.add(i)
        
        # Third pass: Identify truly removed/added
        for i, orig_text in enumerate(orig_texts):
            if i not in used_orig:
                changes.append(BulletChange(
                    change_type="removed",
                    original_text=orig_text,
                    new_text=None,
                    position_original=i,
                    position_new=None
                ))
        
        for j, new_text in enumerate(new_texts):
            if j not in used_new:
                changes.append(BulletChange(
                    change_type="added",
                    original_text=None,
                    new_text=new_text,
                    position_original=None,
                    position_new=j
                ))
        
        return changes
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (0-1)"""
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def _find_new_keywords(self, original: str, new: str) -> List[str]:
        """Find keywords that appear in new but not original"""
        # Extract words
        orig_words = set(re.findall(r'\b\w+\b', original.lower()))
        new_words = set(re.findall(r'\b\w+\b', new.lower()))
        
        # Find significant new words (not common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        new_keywords = new_words - orig_words - common_words
        
        # Filter for technical/meaningful keywords
        meaningful = [
            w for w in new_keywords
            if len(w) > 3 and w not in common_words
        ]
        
        return sorted(meaningful)[:10]  # Top 10
    
    def _extract_added_keywords(
        self,
        original: ParsedResume,
        new: ParsedResume
    ) -> List[str]:
        """Extract all new keywords across resume"""
        orig_text = " ".join([
            original.summary or "",
            *[b.text for b in original.all_bullets]
        ])
        
        new_text = " ".join([
            new.summary or "",
            *[b.text for b in new.all_bullets]
        ])
        
        return self._find_new_keywords(orig_text, new_text)
    
    def _calculate_similarity(
        self,
        original: ParsedResume,
        new: ParsedResume
    ) -> float:
        """Calculate overall similarity (0-1)"""
        orig_text = " ".join([b.text for b in original.all_bullets])
        new_text = " ".join([b.text for b in new.all_bullets])
        
        return self._text_similarity(orig_text, new_text)
