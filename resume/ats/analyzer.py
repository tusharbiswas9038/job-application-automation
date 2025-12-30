# resume/ats/analyzer.py
import logging
from typing import List, Dict, Tuple
from collections import defaultdict

from resume.models import ParsedResume
from resume.ats.models import (
    ATSScore, KeywordMatch, OptimizationSuggestion,
    KeywordCategory, MatchType
)

logger = logging.getLogger(__name__)


class ATSAnalyzer:
    """
    Analyze ATS score and provide actionable optimization suggestions
    """
    
    def __init__(self):
        pass
    
    def analyze(self, score: ATSScore, resume: ParsedResume) -> List[OptimizationSuggestion]:
        """
        Analyze ATS score and generate prioritized suggestions
        
        Args:
            score: ATS score result
            resume: Parsed resume
        
        Returns:
            List of OptimizationSuggestion objects, sorted by priority
        """
        logger.info("Analyzing ATS score for optimization opportunities")
        
        suggestions = []
        
        # 1. Critical missing keywords
        suggestions.extend(self._analyze_missing_keywords(score))
        
        # 2. Weak keyword matches
        suggestions.extend(self._analyze_weak_matches(score))
        
        # 3. Section-specific improvements
        suggestions.extend(self._analyze_sections(score, resume))
        
        # 4. Format improvements
        suggestions.extend(self._analyze_format(score, resume))
        
        # 5. Experience improvements
        suggestions.extend(self._analyze_experience(score, resume))
        
        # Sort by priority and impact
        suggestions.sort(
            key=lambda s: (
                self._priority_rank(s.priority),
                -s.impact
            )
        )
        
        logger.info(f"Generated {len(suggestions)} optimization suggestions")
        return suggestions
    
    def _analyze_missing_keywords(self, score: ATSScore) -> List[OptimizationSuggestion]:
        """Analyze critical missing keywords"""
        suggestions = []
        
        # Group by category
        by_category = defaultdict(list)
        for kw in score.missing_keywords:
            if kw.importance >= 0.7:  # Only important keywords
                by_category[kw.category].append(kw)
        
        # Technical skills
        if by_category[KeywordCategory.TECHNICAL]:
            tech_keywords = [kw.text for kw in by_category[KeywordCategory.TECHNICAL][:3]]
            
            suggestions.append(OptimizationSuggestion(
                priority="critical",
                category="keyword",
                issue=f"Missing critical technical skills: {', '.join(tech_keywords)}",
                suggestion=(
                    f"Add these skills to your Technical Skills section. "
                    f"If you have experience with them, also mention in bullet points."
                ),
                impact=8.0,
                keywords_affected=tech_keywords
            ))
        
        # Domain keywords
        if by_category[KeywordCategory.DOMAIN]:
            domain_keywords = [kw.text for kw in by_category[KeywordCategory.DOMAIN][:3]]
            
            suggestions.append(OptimizationSuggestion(
                priority="high",
                category="keyword",
                issue=f"Missing domain expertise keywords: {', '.join(domain_keywords)}",
                suggestion=(
                    f"Incorporate these terms into your experience bullets where relevant. "
                    f"Use them naturally in context of your achievements."
                ),
                impact=6.0,
                keywords_affected=domain_keywords
            ))
        
        # Certifications
        if by_category[KeywordCategory.CERTIFICATION]:
            cert_keywords = [kw.text for kw in by_category[KeywordCategory.CERTIFICATION]]
            
            suggestions.append(OptimizationSuggestion(
                priority="medium",
                category="certification",
                issue=f"Missing certifications mentioned in JD: {', '.join(cert_keywords)}",
                suggestion=(
                    "Consider obtaining these certifications if you don't have them. "
                    "If you have equivalent experience, mention it explicitly."
                ),
                impact=5.0,
                keywords_affected=cert_keywords
            ))
        
        return suggestions
    
    def _analyze_weak_matches(self, score: ATSScore) -> List[OptimizationSuggestion]:
        """Analyze keywords that matched weakly"""
        suggestions = []
        
        weak_matches = [
            m for m in score.matched_keywords
            if m.match_type in [MatchType.PARTIAL, MatchType.STEMMED] and
            m.keyword.importance >= 0.6
        ]
        
        if weak_matches:
            examples = weak_matches[:3]
            
            details = []
            for match in examples:
                details.append(
                    f"'{match.keyword.text}' matched as '{match.matched_text}'"
                )
            
            suggestions.append(OptimizationSuggestion(
                priority="high",
                category="keyword",
                issue=f"Important keywords matched weakly: {'; '.join(details)}",
                suggestion=(
                    "Use exact keyword phrasing from job description. "
                    "Replace similar terms with exact matches to improve ATS parsing."
                ),
                impact=7.0,
                keywords_affected=[m.keyword.text for m in examples]
            ))
        
        return suggestions
    
    def _analyze_sections(
        self,
        score: ATSScore,
        resume: ParsedResume
    ) -> List[OptimizationSuggestion]:
        """Analyze section-specific issues"""
        suggestions = []
        
        for section_name, section_score in score.section_scores.items():
            # Low match rate
            if section_score.match_rate < 0.3:
                suggestions.append(OptimizationSuggestion(
                    priority="high",
                    category="content",
                    issue=f"{section_name.title()} section has low keyword coverage ({section_score.match_rate:.1%})",
                    suggestion=(
                        f"Add more relevant keywords to {section_name}. "
                        f"Currently only {section_score.keyword_matches}/{section_score.total_keywords} keywords matched."
                    ),
                    impact=6.0,
                    keywords_affected=[]
                ))
            
            # Low density (for experience/skills)
            if section_name in ['experience', 'skills'] and section_score.density < 2:
                suggestions.append(OptimizationSuggestion(
                    priority="medium",
                    category="content",
                    issue=f"{section_name.title()} has low keyword density ({section_score.density:.1f}%)",
                    suggestion=(
                        f"Increase keyword density in {section_name}. "
                        "Focus on technical terms and job-relevant phrases."
                    ),
                    impact=4.0,
                    keywords_affected=[]
                ))
        
        return suggestions
    
    def _analyze_format(
        self,
        score: ATSScore,
        resume: ParsedResume
    ) -> List[OptimizationSuggestion]:
        """Analyze format and structure issues"""
        suggestions = []
        
        # Missing sections
        if not resume.summary:
            suggestions.append(OptimizationSuggestion(
                priority="medium",
                category="format",
                issue="Missing professional summary",
                suggestion=(
                    "Add a 3-4 sentence summary at the top highlighting your key qualifications "
                    "and how they match the job requirements. Include 2-3 top keywords."
                ),
                impact=5.0,
                keywords_affected=[]
            ))
        
        # Too few bullets
        if len(resume.all_bullets) < 10:
            suggestions.append(OptimizationSuggestion(
                priority="high",
                category="content",
                issue=f"Only {len(resume.all_bullets)} bullet points (recommended: 15-20)",
                suggestion=(
                    "Add more achievement-focused bullet points. Each should:\n"
                    "- Start with an action verb\n"
                    "- Include quantifiable results\n"
                    "- Incorporate relevant keywords naturally"
                ),
                impact=6.0,
                keywords_affected=[]
            ))
        
        # Too many bullets
        elif len(resume.all_bullets) > 25:
            suggestions.append(OptimizationSuggestion(
                priority="low",
                category="content",
                issue=f"Too many bullet points ({len(resume.all_bullets)})",
                suggestion=(
                    "Consider consolidating or removing less impactful bullets. "
                    "Focus on most recent and relevant achievements."
                ),
                impact=2.0,
                keywords_affected=[]
            ))
        
        # Missing contact info
        if not resume.personal.phone:
            suggestions.append(OptimizationSuggestion(
                priority="medium",
                category="format",
                issue="Missing phone number",
                suggestion="Add phone number to contact information section",
                impact=3.0,
                keywords_affected=[]
            ))
        
        return suggestions
    
    def _analyze_experience(
        self,
        score: ATSScore,
        resume: ParsedResume
    ) -> List[OptimizationSuggestion]:
        """Analyze experience section issues"""
        suggestions = []
        
        if not resume.experience:
            suggestions.append(OptimizationSuggestion(
                priority="critical",
                category="experience",
                issue="No experience section found",
                suggestion="Add work experience with relevant roles and achievements",
                impact=10.0,
                keywords_affected=[]
            ))
            return suggestions
        
        # Check for quantification in bullets
        bullets_with_numbers = sum(
            1 for exp in resume.experience
            for bullet in exp.bullets
            if any(char.isdigit() for char in bullet.text)
        )
        
        total_bullets = len(resume.all_bullets)
        quantified_ratio = bullets_with_numbers / total_bullets if total_bullets > 0 else 0
        
        if quantified_ratio < 0.3:
            suggestions.append(OptimizationSuggestion(
                priority="high",
                category="content",
                issue=f"Only {quantified_ratio:.0%} of bullets include quantification",
                suggestion=(
                    "Add numbers, percentages, or metrics to your accomplishments:\n"
                    "- Cluster size, message throughput, uptime %\n"
                    "- Number of systems managed\n"
                    "- Performance improvements achieved\n"
                    "- Team size, projects delivered"
                ),
                impact=7.0,
                keywords_affected=[]
            ))
        
        # Check for action verbs
        strong_verbs = [
            'managed', 'implemented', 'developed', 'optimized', 'designed',
            'automated', 'configured', 'deployed', 'migrated', 'architected'
        ]
        
        bullets_with_verbs = sum(
            1 for exp in resume.experience
            for bullet in exp.bullets
            if any(verb in bullet.text.lower() for verb in strong_verbs)
        )
        
        verb_ratio = bullets_with_verbs / total_bullets if total_bullets > 0 else 0
        
        if verb_ratio < 0.5:
            suggestions.append(OptimizationSuggestion(
                priority="medium",
                category="content",
                issue="Many bullets lack strong action verbs",
                suggestion=(
                    "Start each bullet with a strong action verb:\n"
                    f"Recommended: {', '.join(strong_verbs[:5])}"
                ),
                impact=5.0,
                keywords_affected=[]
            ))
        
        return suggestions
    
    def _priority_rank(self, priority: str) -> int:
        """Convert priority to numeric rank for sorting"""
        ranks = {
            'critical': 0,
            'high': 1,
            'medium': 2,
            'low': 3
        }
        return ranks.get(priority, 4)
    
    def generate_report(
        self,
        score: ATSScore,
        suggestions: List[OptimizationSuggestion]
    ) -> str:
        """
        Generate human-readable optimization report
        
        Returns:
            Formatted report string
        """
        lines = []
        
        lines.append("=" * 70)
        lines.append("ATS OPTIMIZATION REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Overall score
        lines.append(f"Overall ATS Score: {score.overall_score:.1f}/100 ({score.grade})")
        lines.append(f"Pass Threshold: {'✓ PASS' if score.pass_threshold else '✗ NEEDS IMPROVEMENT'}")
        lines.append("")
        
        # Component scores
        lines.append("Component Scores:")
        lines.append(f"  Keywords:   {score.keyword_score:.1f}/100")
        lines.append(f"  Experience: {score.experience_score:.1f}/100")
        lines.append(f"  Skills:     {score.skills_score:.1f}/100")
        lines.append(f"  Education:  {score.education_score:.1f}/100")
        lines.append(f"  Format:     {score.format_score:.1f}/100")
        lines.append("")
        
        # Keyword match stats
        lines.append(f"Keyword Matching: {score.matched_count}/{score.total_keywords} ({score.match_rate:.1%})")
        lines.append("")
        
        # Suggestions by priority
        by_priority = defaultdict(list)
        for sugg in suggestions:
            by_priority[sugg.priority].append(sugg)
        
        for priority in ['critical', 'high', 'medium', 'low']:
            if priority in by_priority:
                lines.append(f"{priority.upper()} PRIORITY ({len(by_priority[priority])} items):")
                lines.append("-" * 70)
                
                for i, sugg in enumerate(by_priority[priority], 1):
                    lines.append(f"{i}. {sugg.issue}")
                    lines.append(f"   → {sugg.suggestion}")
                    lines.append(f"   Impact: +{sugg.impact:.1f} points")
                    lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)

