# resume/job_fit/skill_matcher.py
import logging
from typing import List, Dict, Tuple, Set, Optional
import re

from resume.models import ParsedResume
from resume.job_fit.models import (
    SkillMatch, SkillGap, SkillLevel, JobRequirements
)

logger = logging.getLogger(__name__)


class SkillMatcher:
    """
    Match candidate skills against job requirements
    """
    
    # Skill synonyms for matching
    SKILL_SYNONYMS = {
        'kafka': ['apache kafka', 'confluent', 'kafka streams'],
        'kubernetes': ['k8s', 'container orchestration'],
        'aws': ['amazon web services', 'ec2', 's3'],
        'python': ['python3', 'python scripting'],
        'ci/cd': ['continuous integration', 'continuous deployment', 'jenkins', 'gitlab ci'],
        'monitoring': ['observability', 'prometheus', 'grafana', 'datadog'],
        'iac': ['infrastructure as code', 'terraform', 'cloudformation'],
    }
    
    # Keywords indicating skill level
    LEVEL_INDICATORS = {
        SkillLevel.EXPERT: [
            'expert', 'mastery', 'deep expertise', 'architect',
            'led team', 'mentored', 'designed from scratch'
        ],
        SkillLevel.ADVANCED: [
            'advanced', 'proficient', 'extensive experience',
            'production', 'at scale', 'optimized', 'implemented'
        ],
        SkillLevel.INTERMEDIATE: [
            'experience with', 'worked with', 'familiar',
            'configured', 'deployed', 'maintained'
        ],
        SkillLevel.BEGINNER: [
            'basic', 'learning', 'exposure to', 'assisted with'
        ]
    }
    
    def __init__(self):
        pass
    
    def match_skills(
        self,
        resume: ParsedResume,
        job_requirements: JobRequirements
    ) -> Tuple[List[SkillMatch], List[SkillGap]]:
        """
        Match candidate skills against job requirements
        
        Returns:
            (skill_matches, skill_gaps)
        """
        logger.info("Matching skills against job requirements")
        
        # Extract candidate skills and levels
        candidate_skills = self._extract_candidate_skills(resume)
        
        # Match required skills
        matches = []
        gaps = []
        
        for skill_name, required_level in job_requirements.required_skills.items():
            match = self._match_single_skill(
                skill_name,
                required_level,
                candidate_skills,
                resume,
                importance=1.0
            )
            
            if match:
                matches.append(match)
            else:
                gap = SkillGap(
                    skill_name=skill_name,
                    required_level=required_level,
                    current_level=SkillLevel.NONE,
                    importance=1.0,
                    gap_severity="critical"
                )
                gaps.append(gap)
        
        # Match preferred skills
        for skill_name, required_level in job_requirements.preferred_skills.items():
            match = self._match_single_skill(
                skill_name,
                required_level,
                candidate_skills,
                resume,
                importance=0.5
            )
            
            if match:
                matches.append(match)
            else:
                gap = SkillGap(
                    skill_name=skill_name,
                    required_level=required_level,
                    current_level=SkillLevel.NONE,
                    importance=0.5,
                    gap_severity="moderate"
                )
                gaps.append(gap)
        
        logger.info(f"Found {len(matches)} skill matches and {len(gaps)} gaps")
        return matches, gaps
    
    def _extract_candidate_skills(
        self,
        resume: ParsedResume
    ) -> Dict[str, Tuple[SkillLevel, List[str]]]:
        """
        Extract skills from resume with inferred levels
        
        Returns:
            Dict mapping skill_name -> (level, evidence_list)
        """
        skills_dict = {}
        
        # Extract from technical skills section
        all_skills = (
            resume.skills.technical +
            resume.skills.tools +
            resume.skills.languages
        )
        
        for skill in all_skills:
            skill_lower = skill.lower()
            
            # Find evidence in experience bullets
            evidence = self._find_skill_evidence(skill, resume)
            
            # Infer level from evidence
            level = self._infer_skill_level(skill, evidence, resume)
            
            skills_dict[skill_lower] = (level, evidence)
        
        return skills_dict
    
    def _match_single_skill(
        self,
        skill_name: str,
        required_level: SkillLevel,
        candidate_skills: Dict[str, Tuple[SkillLevel, List[str]]],
        resume: ParsedResume,
        importance: float
    ) -> Optional[SkillMatch]:
        """Match a single skill"""
        skill_lower = skill_name.lower()
        
        # Direct match
        if skill_lower in candidate_skills:
            level, evidence = candidate_skills[skill_lower]
            return self._create_skill_match(
                skill_name, required_level, level, evidence, importance
            )
        
        # Check synonyms
        for candidate_skill, (level, evidence) in candidate_skills.items():
            if self._are_synonyms(skill_lower, candidate_skill):
                return self._create_skill_match(
                    skill_name, required_level, level, evidence, importance
                )
        
        # Fuzzy match
        for candidate_skill, (level, evidence) in candidate_skills.items():
            if self._fuzzy_match(skill_lower, candidate_skill):
                return self._create_skill_match(
                    skill_name, required_level, level, evidence, importance
                )
        
        return None
    
    def _create_skill_match(
        self,
        skill_name: str,
        required_level: SkillLevel,
        candidate_level: SkillLevel,
        evidence: List[str],
        importance: float
    ) -> SkillMatch:
        """Create a SkillMatch object"""
        # Calculate match strength
        level_scores = {
            SkillLevel.EXPERT: 5,
            SkillLevel.ADVANCED: 4,
            SkillLevel.INTERMEDIATE: 3,
            SkillLevel.BEGINNER: 2,
            SkillLevel.NONE: 0
        }
        
        required_score = level_scores[required_level]
        candidate_score = level_scores[candidate_level]
        
        # Match strength: 1.0 if meets or exceeds, proportional if below
        if candidate_score >= required_score:
            match_strength = 1.0
        else:
            match_strength = candidate_score / required_score if required_score > 0 else 0.0
        
        # Apply importance weight
        match_strength *= importance
        
        return SkillMatch(
            skill_name=skill_name,
            required_level=required_level,
            candidate_level=candidate_level,
            match_strength=match_strength,
            evidence=evidence,
            years_experience=self._estimate_years(evidence)
        )
    
    def _find_skill_evidence(
        self,
        skill: str,
        resume: ParsedResume
    ) -> List[str]:
        """Find evidence of skill usage in resume"""
        evidence = []
        skill_lower = skill.lower()
        
        # Check summary
        if resume.summary and skill_lower in resume.summary.lower():
            evidence.append(f"Summary: {resume.summary[:100]}")
        
        # Check experience bullets
        for bullet in resume.all_bullets:
            if skill_lower in bullet.text.lower():
                evidence.append(f"{bullet.subsection}: {bullet.text}")
        
        return evidence
    
    def _infer_skill_level(
        self,
        skill: str,
        evidence: List[str],
        resume: ParsedResume
    ) -> SkillLevel:
        """Infer skill level from evidence"""
        if not evidence:
            return SkillLevel.BEGINNER
        
        evidence_text = " ".join(evidence).lower()
        
        # Check for level indicators
        for level, indicators in self.LEVEL_INDICATORS.items():
            if any(indicator in evidence_text for indicator in indicators):
                return level
        
        # Default based on evidence count
        if len(evidence) >= 5:
            return SkillLevel.ADVANCED
        elif len(evidence) >= 3:
            return SkillLevel.INTERMEDIATE
        else:
            return SkillLevel.BEGINNER
    
    def _estimate_years(self, evidence: List[str]) -> Optional[int]:
        """Estimate years of experience from evidence"""
        # Look for year mentions in evidence
        for ev in evidence:
            match = re.search(r'(\d+)\+?\s*years?', ev.lower())
            if match:
                return int(match.group(1))
        
        # Estimate based on evidence count (rough heuristic)
        if len(evidence) >= 5:
            return 5
        elif len(evidence) >= 3:
            return 3
        elif len(evidence) >= 1:
            return 1
        
        return None
    
    def _are_synonyms(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are synonyms"""
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            skills_set = {canonical} | set(synonyms)
            if skill1 in skills_set and skill2 in skills_set:
                return True
        return False
    
    def _fuzzy_match(self, skill1: str, skill2: str, threshold: float = 0.85) -> bool:
        """Fuzzy string matching for skills"""
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, skill1, skill2).ratio()
        return ratio >= threshold
    
    def calculate_skill_fit_score(
        self,
        matches: List[SkillMatch],
        gaps: List[SkillGap]
    ) -> float:
        """
        Calculate overall skill fit score (0-100)
        """
        if not matches and not gaps:
            return 0.0
        
        total_skills = len(matches) + len(gaps)
        
        # Weighted score based on match strength
        match_score = sum(m.match_strength for m in matches)
        max_possible = total_skills
        
        # Penalize critical gaps heavily
        critical_gaps = [g for g in gaps if g.gap_severity == "critical"]
        penalty = len(critical_gaps) * 0.2
        
        score = (match_score / max_possible) * 100 if max_possible > 0 else 0
        score = max(0, score - (penalty * 10))
        
        return min(score, 100.0)

