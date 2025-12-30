# resume/ats/scorer.py
import logging
from typing import List, Dict, Tuple
from datetime import datetime

from resume.models import ParsedResume
from resume.ats.models import (
    ATSScore, SectionScore, KeywordMatch, Keyword,
    MatchType, KeywordCategory, OptimizationSuggestion
)
from resume.ats.keyword_extractor import KeywordExtractor
from resume.ats.matcher import KeywordMatcher
from resume.ats.job_description import JobDescriptionParser

logger = logging.getLogger(__name__)


class ATSScorer:
    """
    Calculate comprehensive ATS score for resume
    """
    
    # Weight distribution for overall score
    WEIGHTS = {
        'keyword': 0.40,      # 40% - Keywords are most important
        'experience': 0.20,   # 20% - Experience relevance
        'skills': 0.20,       # 20% - Skills match
        'education': 0.10,    # 10% - Education fit
        'format': 0.10,       # 10% - Format quality
    }
    
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.keyword_matcher = KeywordMatcher()
        self.jd_parser = JobDescriptionParser()
    
    def score_resume(
        self,
        resume: ParsedResume,
        job_description: str,
        **jd_metadata
    ) -> ATSScore:
        """
        Score resume against job description
        
        Args:
            resume: Parsed resume
            job_description: Job description text
            **jd_metadata: Additional JD metadata (title, company, etc.)
        
        Returns:
            ATSScore object with detailed scoring
        """
        logger.info("Calculating ATS score")
        
        # Parse job description
        jd = self.jd_parser.parse(job_description, **jd_metadata)
        
        # Extract keywords from JD
        keywords = self.keyword_extractor.extract_keywords(job_description)
        
        # Match keywords against resume
        matches = self.keyword_matcher.match_keywords(resume, keywords)
        
        # Calculate component scores
        keyword_score = self._calculate_keyword_score(matches, keywords)
        experience_score = self._calculate_experience_score(resume, jd)
        skills_score = self._calculate_skills_score(resume, matches)
        education_score = self._calculate_education_score(resume, jd)
        format_score = self._calculate_format_score(resume)
        
        # Calculate overall score
        overall = (
            keyword_score * self.WEIGHTS['keyword'] +
            experience_score * self.WEIGHTS['experience'] +
            skills_score * self.WEIGHTS['skills'] +
            education_score * self.WEIGHTS['education'] +
            format_score * self.WEIGHTS['format']
        )
        
        # Calculate section scores
        section_scores = self._calculate_section_scores(resume, matches)
        
        # Separate matched and missing keywords
        matched_keywords = [m for m in matches if m.match_type != MatchType.MISSING]
        missing_keywords = [m.keyword for m in matches if m.match_type == MatchType.MISSING]
        
        # Generate recommendations
        critical_gaps, improvements, enhancements = self._generate_recommendations(
            matches, resume, jd
        )
        
        # Build ATSScore object
        score = ATSScore(
            overall_score=overall,
            keyword_score=keyword_score,
            experience_score=experience_score,
            education_score=education_score,
            skills_score=skills_score,
            format_score=format_score,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            section_scores=section_scores,
            total_keywords=len(keywords),
            matched_count=len(matched_keywords),
            match_rate=len(matched_keywords) / len(keywords) if keywords else 0,
            critical_gaps=critical_gaps,
            improvements=improvements,
            enhancements=enhancements,
            job_title=jd.title
        )
        
        logger.info(f"ATS Score: {score.overall_score:.1f}/100 ({score.grade})")
        return score
    
    def _calculate_keyword_score(
        self,
        matches: List[KeywordMatch],
        keywords: List[Keyword]
    ) -> float:
        """
        Calculate keyword matching score (0-100)
        
        Scoring:
        - Weighted by keyword importance
        - Match type affects score (exact > synonym > stemmed > partial)
        - Frequency bonus
        - Context quality bonus
        """
        if not keywords:
            return 0.0
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for match in matches:
            keyword_weight = match.keyword.importance
            match_score = match.score  # 0-1 from KeywordMatch.score property
            
            total_weighted_score += match_score * keyword_weight
            total_weight += keyword_weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize to 0-100
        raw_score = (total_weighted_score / total_weight) * 100
        
        # Apply penalties
        missing_critical = [
            m for m in matches
            if m.match_type == MatchType.MISSING and m.keyword.importance >= 0.8
        ]
        
        penalty = len(missing_critical) * 5  # -5 points per critical missing keyword
        
        return max(0, min(100, raw_score - penalty))
    
    def _calculate_experience_score(
        self,
        resume: ParsedResume,
        jd
    ) -> float:
        """
        Calculate experience relevance score (0-100)
        
        Factors:
        - Years of experience match
        - Relevant job titles
        - Recent vs old experience
        - Number of relevant roles
        """
        score = 0.0
        
        # 1. Years of experience (40 points)
        if jd.required_experience_years:
            total_years = len(resume.experience)  # Simplified: 1 role ≈ years
            if total_years >= jd.required_experience_years:
                score += 40
            else:
                # Partial credit
                ratio = total_years / jd.required_experience_years
                score += 40 * ratio
        else:
            # No requirement specified, give credit for having experience
            if resume.experience:
                score += 30
        
        # 2. Relevant job titles (30 points)
        if resume.experience and jd.title:  # Added check for jd.title
            title_keywords = ['kafka', 'administrator', 'devops', 'platform', 'engineer', 'sre']
            jd_title_lower = jd.title.lower()
            
            for exp in resume.experience:
                exp_title_lower = exp.title.lower()
                
                # Check for keyword overlap
                overlap = sum(1 for kw in title_keywords if kw in exp_title_lower and kw in jd_title_lower)
                if overlap > 0:
                    score += min(30, overlap * 10)
                    break
        elif resume.experience:
            # If no JD title, give partial credit for having relevant experience
            score += 15
        
        # 3. Recency (15 points)
        if resume.experience:
            recent_exp = resume.experience[0]  # Assuming first is most recent
            if recent_exp.end_date and 'present' in recent_exp.end_date.lower():
                score += 15
            else:
                score += 10  # Some credit for recent experience
        
        # 4. Number of roles (15 points)
        if len(resume.experience) >= 2:
            score += 15
        elif len(resume.experience) == 1:
            score += 10
        
        return min(100, score)


    def _calculate_skills_score(
        self,
        resume: ParsedResume,
        matches: List[KeywordMatch]
    ) -> float:
        """
        Calculate skills section score (0-100)
        
        Factors:
        - Technical skills matched
        - Tools matched
        - Certifications matched
        - Skills density
        """
        score = 0.0
        
        # 1. Technical skills matched (50 points)
        tech_matches = [
            m for m in matches
            if m.match_type != MatchType.MISSING and
            m.keyword.category == KeywordCategory.TECHNICAL
        ]
        
        if tech_matches:
            # Calculate match rate for technical skills
            all_tech = [
                m for m in matches
                if m.keyword.category == KeywordCategory.TECHNICAL
            ]
            tech_rate = len(tech_matches) / len(all_tech) if all_tech else 0
            score += tech_rate * 50
        
        # 2. Tools matched (25 points)
        tool_matches = [
            m for m in matches
            if m.match_type != MatchType.MISSING and
            m.keyword.category == KeywordCategory.TOOL
        ]
        
        if tool_matches:
            all_tools = [
                m for m in matches
                if m.keyword.category == KeywordCategory.TOOL
            ]
            tool_rate = len(tool_matches) / len(all_tools) if all_tools else 0
            score += tool_rate * 25
        
        # 3. Certifications (15 points)
        cert_matches = [
            m for m in matches
            if m.match_type != MatchType.MISSING and
            m.keyword.category == KeywordCategory.CERTIFICATION
        ]
        
        if cert_matches:
            score += 15
        elif resume.certifications:
            score += 10  # Partial credit for having certifications
        
        # 4. Skills section completeness (10 points)
        total_skills = (
            len(resume.skills.technical) +
            len(resume.skills.tools) +
            len(resume.skills.languages)
        )
        
        if total_skills >= 15:
            score += 10
        elif total_skills >= 10:
            score += 7
        elif total_skills >= 5:
            score += 5
        
        return min(100, score)
    
    def _calculate_education_score(
        self,
        resume: ParsedResume,
        jd
    ) -> float:
        """
        Calculate education score (0-100)
        
        Factors:
        - Has relevant degree
        - Degree level (BS/MS/PhD)
        - Relevant field
        """
        score = 0.0
        
        if not resume.education:
            return 30  # Some ATS give partial credit
        
        # 1. Has degree (50 points)
        score += 50
        
        # 2. Degree level (30 points)
        for edu in resume.education:
            degree_lower = edu.degree.lower()
            
            if any(kw in degree_lower for kw in ['phd', 'doctorate', 'doctor']):
                score += 30
                break
            elif any(kw in degree_lower for kw in ['master', 'ms', 'msc', 'mba']):
                score += 25
                break
            elif any(kw in degree_lower for kw in ['bachelor', 'bs', 'ba', 'bsc']):
                score += 20
                break
            elif 'diploma' in degree_lower:
                score += 15
                break
        
        # 3. Relevant field (20 points)
        relevant_fields = [
            'computer', 'software', 'information', 'technology',
            'engineering', 'science'
        ]
        
        for edu in resume.education:
            degree_lower = edu.degree.lower()
            if any(field in degree_lower for field in relevant_fields):
                score += 20
                break
        
        return min(100, score)
    
    def _calculate_format_score(self, resume: ParsedResume) -> float:
        """
        Calculate format/structure score (0-100)
        
        Factors:
        - ATS-friendly format (LaTeX is good)
        - Has all sections
        - Reasonable length
        - Proper contact info
        """
        score = 0.0
        
        # 1. LaTeX format (20 points - already ATS-friendly)
        score += 20
        
        # 2. Has required sections (40 points)
        sections_present = 0
        if resume.personal.name:
            sections_present += 1
        if resume.personal.email:
            sections_present += 1
        if resume.experience:
            sections_present += 1
        if resume.education:
            sections_present += 1
        if resume.skills.technical or resume.skills.tools:
            sections_present += 1
        
        score += (sections_present / 5) * 40
        
        # 3. Reasonable length (20 points)
        total_bullets = len(resume.all_bullets)
        if 10 <= total_bullets <= 25:
            score += 20
        elif 5 <= total_bullets < 10 or 25 < total_bullets <= 30:
            score += 15
        else:
            score += 10
        
        # 4. Contact info completeness (20 points)
        contact_score = 0
        if resume.personal.email:
            contact_score += 5
        if resume.personal.phone:
            contact_score += 5
        if resume.personal.linkedin:
            contact_score += 5
        if resume.personal.github:
            contact_score += 5
        
        score += contact_score
        
        return min(100, score)
    
    def _calculate_section_scores(
        self,
        resume: ParsedResume,
        matches: List[KeywordMatch]
    ) -> Dict[str, SectionScore]:
        """Calculate detailed scores for each resume section"""
        section_scores = {}
        
        sections = {
            'summary': resume.summary or "",
            'experience': self._get_experience_text(resume),
            'skills': self._get_skills_text(resume),
            'education': self._get_education_text(resume),
        }
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            # Count keywords in this section
            section_matches = [
                m for m in matches
                if section_name in m.locations
            ]
            
            total_section_keywords = len([
                m for m in matches
                if m.keyword.category in [
                    KeywordCategory.TECHNICAL,
                    KeywordCategory.DOMAIN,
                    KeywordCategory.TOOL
                ]
            ])
            
            # Calculate metrics
            word_count = len(section_text.split())
            match_rate = len(section_matches) / total_section_keywords if total_section_keywords > 0 else 0
            density = (len(section_matches) / word_count * 100) if word_count > 0 else 0
            
            # Quality score based on match types
            quality = sum(m.score for m in section_matches) / len(section_matches) if section_matches else 0
            
            # Generate suggestions
            suggestions = []
            if match_rate < 0.3:
                suggestions.append(f"Add more relevant keywords to {section_name}")
            if density < 2 and section_name in ['experience', 'skills']:
                suggestions.append(f"Increase keyword density in {section_name}")
            
            section_scores[section_name] = SectionScore(
                section_name=section_name,
                keyword_matches=len(section_matches),
                total_keywords=total_section_keywords,
                match_rate=match_rate,
                density=density,
                quality_score=quality * 100,
                suggestions=suggestions
            )
        
        return section_scores
    
    def _get_experience_text(self, resume: ParsedResume) -> str:
        """Get all experience text"""
        parts = []
        for exp in resume.experience:
            parts.append(exp.title)
            parts.append(exp.company)
            for bullet in exp.bullets:
                parts.append(bullet.text)
        return ' '.join(filter(None, parts))
    
    def _get_skills_text(self, resume: ParsedResume) -> str:
        """Get all skills text"""
        parts = []
        parts.extend(resume.skills.technical)
        parts.extend(resume.skills.tools)
        parts.extend(resume.skills.languages)
        return ' '.join(filter(None, parts))
    
    def _get_education_text(self, resume: ParsedResume) -> str:
        """Get all education text"""
        parts = []
        for edu in resume.education:
            parts.append(edu.degree)
            parts.append(edu.institution)
        return ' '.join(filter(None, parts))
    
    def _generate_recommendations(
        self,
        matches: List[KeywordMatch],
        resume: ParsedResume,
        jd
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Generate categorized recommendations
        
        Returns:
            (critical_gaps, improvements, enhancements)
        """
        critical_gaps = []
        improvements = []
        enhancements = []
        
        # Critical: Missing required/high-importance keywords
        critical_missing = [
            m for m in matches
            if m.match_type == MatchType.MISSING and m.keyword.importance >= 0.8
        ]
        
        for match in critical_missing[:5]:  # Top 5
            critical_gaps.append(
                f"Add '{match.keyword.text}' - appears {int(match.keyword.importance * 10)} times in JD"
            )
        
        # Improvements: Keywords matched but weakly
        weak_matches = [
            m for m in matches
            if m.match_type in [MatchType.PARTIAL, MatchType.STEMMED] and
            m.keyword.importance >= 0.6
        ]
        
        for match in weak_matches[:5]:
            improvements.append(
                f"Strengthen '{match.keyword.text}' - currently matched as '{match.matched_text}'"
            )
        
        # Improvements: Low frequency for important keywords
        low_freq = [
            m for m in matches
            if m.match_type in [MatchType.EXACT, MatchType.SYNONYM] and
            m.frequency == 1 and
            m.keyword.importance >= 0.7
        ]
        
        for match in low_freq[:3]:
            improvements.append(
                f"Use '{match.keyword.text}' more frequently - currently only appears once"
            )
        
        # Enhancements: Nice-to-have keywords
        nice_to_have = [
            m for m in matches
            if m.match_type == MatchType.MISSING and
            0.4 <= m.keyword.importance < 0.6
        ]
        
        for match in nice_to_have[:5]:
            enhancements.append(
                f"Consider adding '{match.keyword.text}' to boost relevance"
            )
        
        # Structure suggestions
        if not resume.summary:
            improvements.append("Add a professional summary highlighting key qualifications")
        
        if len(resume.all_bullets) < 10:
            improvements.append("Add more bullet points with quantified achievements")
        
        if not resume.certifications:
            enhancements.append("Add relevant certifications if you have any")
        
        return critical_gaps, improvements, enhancements

