# resume/tailoring/variant_generator.py
import logging
import uuid
from typing import Optional, List, Dict
from pathlib import Path

from resume.models import ParsedResume
from resume.latex_parser import LaTeXResumeParser
from resume.ats.keyword_extractor import KeywordExtractor
from resume.ats.scorer import ATSScorer
from resume.job_fit.fit_scorer import JobFitScorer
from resume.job_fit.models import JobRequirements
from resume.ai.ollama_client import OllamaClient
from resume.ai.bullet_enhancer import BulletEnhancer
from resume.tailoring.bullet_selector import BulletSelector
from resume.tailoring.template_engine import TemplateEngine
from resume.tailoring.models import (
    ResumeVariant, VariantContent, VariantGenerationConfig
)

logger = logging.getLogger(__name__)


class VariantGenerator:
    """
    Generate tailored resume variants for specific jobs
    """
    
    def __init__(
        self,
        config: Optional[VariantGenerationConfig] = None,
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize variant generator
        
        Args:
            config: Generation configuration
            ollama_client: Ollama client for AI features
        """
        self.config = config or VariantGenerationConfig()
        self.ollama = ollama_client or OllamaClient()
        
        # Components
        self.parser = LaTeXResumeParser()
        self.keyword_extractor = KeywordExtractor()
        self.bullet_selector = BulletSelector(self.config)
        self.bullet_enhancer = BulletEnhancer(self.ollama)
        self.template_engine = TemplateEngine()
        self.ats_scorer = ATSScorer()
        self.fit_scorer = JobFitScorer()
    
    def generate_variant(
        self,
        resume_path: str,
        jd_text: str,
        job_title: str,
        company: Optional[str] = None,
        output_dir: str = "data/resumes/variants",
        job_requirements: Optional[JobRequirements] = None
    ) -> ResumeVariant:
        """
        Generate a tailored resume variant
        
        Args:
            resume_path: Path to base resume (.tex)
            jd_text: Job description text
            job_title: Target job title
            company: Company name
            output_dir: Where to save variant
            job_requirements: Optional structured requirements for fit scoring
        
        Returns:
            ResumeVariant with paths and scores
        """
        logger.info(f"Generating variant for: {job_title} at {company}")
        
        # 1. Parse base resume
        logger.info("Parsing base resume...")
        resume = self.parser.parse_file(resume_path)
        
        # 2. Extract job keywords
        logger.info("Extracting job keywords...")
        jd_keywords = self.keyword_extractor.extract_keywords(jd_text)
        top_keywords = [kw.text for kw in jd_keywords[:30]]
        
        # 3. Select best bullets
        logger.info("Selecting relevant bullets...")
        experience_sections = self.bullet_selector.select_bullets(
            resume, jd_text, top_keywords
        )
        
        # 4. AI Enhancement (if enabled and available)
        bullets_enhanced = 0
        keywords_added = []
        
        if self.config.use_ai_enhancement and self.ollama.is_available():
            logger.info("Enhancing bullets with AI...")
            bullets_enhanced, keywords_added = self._enhance_selected_bullets(
                experience_sections,
                job_title,
                top_keywords
            )
        
        # 5. Generate/optimize summary
        logger.info("Generating summary...")
        summary = self._generate_summary(
            resume,
            experience_sections,
            job_title,
            top_keywords
        )
        
        # 6. Optimize skills section
        logger.info("Optimizing skills...")
        skills = self._optimize_skills(resume, top_keywords)
        
        # 7. Build variant content
        content = VariantContent(
            summary=summary,
            experience_sections=experience_sections,
            skills=skills,
            total_bullets=sum(len(sec.selected_bullets) for sec in experience_sections)
        )
        
        # 8. Generate LaTeX and compile PDF
        logger.info("Generating LaTeX...")
        variant_id = str(uuid.uuid4())
        
        variant = ResumeVariant(
            variant_id=variant_id,
            base_resume_path=resume_path,
            job_title=job_title,
            company=company,
            content=content,
            bullets_enhanced=bullets_enhanced,
            keywords_added=keywords_added
        )
        
        latex_path, pdf_path = self.template_engine.generate_files(
            resume=resume,
            variant=variant,
            output_dir=output_dir
        )
        
        variant.latex_path = latex_path
        variant.pdf_path = pdf_path
        
        # 9. Score the variant (if enabled)
        if self.config.auto_score_after_generation:
            logger.info("Scoring variant...")
            
            # ATS Score
            variant_resume = self.parser.parse_file(latex_path)
            variant.ats_score = self.ats_scorer.score_resume(
                variant_resume, jd_text
            )
            
            # Job Fit Score (if requirements provided)
            if job_requirements:
                variant.fit_score = self.fit_scorer.score_fit(
                    variant_resume, job_requirements
                )
        
        logger.info(f"✓ Variant generated: {variant.output_filename}")
        if variant.ats_score:
            logger.info(f"  ATS Score: {variant.ats_score.overall_score:.1f}/100")
        if variant.fit_score:
            logger.info(f"  Fit Score: {variant.fit_score.overall_fit:.1f}/100")
        
        return variant
    
    def _enhance_selected_bullets(
        self,
        sections: List,
        job_title: str,
        missing_keywords: List[str]
    ) -> tuple[int, List[str]]:
        """Enhance selected bullets with AI"""
        total_enhanced = 0
        all_keywords_added = []
        
        # Collect all bullets
        all_bullets = []
        for section in sections:
            all_bullets.extend(section.selected_bullets)
        
        # Sort by relevance, enhance top ones
        all_bullets.sort(key=lambda sb: sb.relevance_score, reverse=True)
        
        for selected_bullet in all_bullets[:self.config.max_bullets_to_enhance]:
            enhancement = self.bullet_enhancer.enhance_bullet(
                selected_bullet.bullet,
                job_title,
                missing_keywords
            )
            
            if enhancement and enhancement.confidence >= self.config.min_enhancement_confidence:
                # Update the selected bullet
                selected_bullet.was_enhanced = True
                selected_bullet.enhanced_version = enhancement.enhanced_text
                total_enhanced += 1
                all_keywords_added.extend(enhancement.keywords_added)
        
        return total_enhanced, list(set(all_keywords_added))
    
    def _generate_summary(
        self,
        resume: ParsedResume,
        sections: List,
        job_title: str,
        keywords: List[str]
    ) -> str:
        """Generate or enhance professional summary"""
        # Collect key experience bullets
        experience_bullets = []
        for section in sections:
            for sb in section.selected_bullets[:2]:  # Top 2 per job
                text = sb.enhanced_version if sb.was_enhanced else sb.bullet.text
                experience_bullets.append(text)
        
        # Try AI generation
        if self.ollama.is_available():
            ai_summary = self.ollama.generate_summary(
                experience_bullets=experience_bullets,
                skills=resume.skills.technical[:10],
                job_title=job_title,
                keywords=keywords[:5]
            )
            
            if ai_summary:
                return ai_summary
        
        # Fallback to original summary with keyword injection
        if resume.summary:
            return self._inject_keywords_in_summary(resume.summary, keywords[:3])
        
        # Last resort: generic summary
        return f"Experienced professional with expertise in {', '.join(keywords[:3])} seeking {job_title} role."
    
    def _inject_keywords_in_summary(self, summary: str, keywords: List[str]) -> str:
        """Inject missing keywords into summary"""
        summary_lower = summary.lower()
        missing = [kw for kw in keywords if kw.lower() not in summary_lower]
        
        if not missing:
            return summary
        
        # Simple injection at the end
        addition = f" Specialized in {', '.join(missing[:2])}."
        return summary + addition
    
    def _optimize_skills(
        self,
        resume: ParsedResume,
        jd_keywords: List[str]
    ) -> Dict[str, List[str]]:
        """Optimize skills section based on JD"""
        optimized = {
            'technical': [],
            'tools': [],
            'languages': []
        }
        
        # Prioritize skills that match JD keywords
        all_resume_skills = (
            resume.skills.technical +
            resume.skills.tools +
            resume.skills.languages
        )
        
        # Score each skill
        skill_scores = []
        for skill in all_resume_skills:
            score = 0
            skill_lower = skill.lower()
            
            # Exact match with JD keyword
            for keyword in jd_keywords:
                if keyword.lower() == skill_lower:
                    score += 10
                elif keyword.lower() in skill_lower or skill_lower in keyword.lower():
                    score += 5
            
            skill_scores.append((skill, score))
        
        # Sort by score
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Distribute to categories
        for skill, score in skill_scores:
            if skill in resume.skills.technical:
                optimized['technical'].append(skill)
            elif skill in resume.skills.tools:
                optimized['tools'].append(skill)
            elif skill in resume.skills.languages:
                optimized['languages'].append(skill)
        
        # Add important JD keywords that aren't in resume (cautiously)
        for keyword in jd_keywords[:10]:
            keyword_clean = keyword.title()
            if keyword_clean not in [s.lower() for s in all_resume_skills]:
                # Check if it's a real technology (basic validation)
                if self._is_valid_tech_skill(keyword):
                    optimized['technical'].append(keyword_clean)
        
        return optimized
    
    def _is_valid_tech_skill(self, keyword: str) -> bool:
        """Basic validation if keyword is a real tech skill"""
        # Common tech keywords
        tech_indicators = [
            'kafka', 'kubernetes', 'docker', 'python', 'aws',
            'terraform', 'jenkins', 'git', 'linux', 'monitoring'
        ]
        
        keyword_lower = keyword.lower()
        return any(tech in keyword_lower for tech in tech_indicators)

