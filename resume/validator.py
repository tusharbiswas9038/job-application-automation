# resume/validator.py
import logging
import re
from typing import List, Tuple, Dict
from resume.models import ParsedResume, BulletPoint
from resume.config import get_config, ResumeConfig

logger = logging.getLogger(__name__)


class ResumeValidator:
    """Validate resume structure and content"""
    
    def __init__(self, config: ResumeConfig = None):
        self.config = config or get_config()
    
    def validate_resume(self, resume: ParsedResume) -> Tuple[bool, List[str]]:
        """
        Validate complete resume
        
        Returns:
            Tuple of (is_valid, list of errors/warnings)
        """
        issues = []
        
        # Check personal info
        if not resume.personal.name:
            issues.append("ERROR: Missing name")
        if not resume.personal.email:
            issues.append("WARNING: Missing email")
        if not resume.personal.phone:
            issues.append("WARNING: Missing phone")
        
        # Check required sections
        if not resume.experience:
            issues.append("ERROR: No experience section")
        if not resume.education:
            issues.append("WARNING: No education section")
        if not resume.summary:
            issues.append("WARNING: No summary/objective")
        
        # Validate experience entries
        for i, exp in enumerate(resume.experience):
            exp_issues = self._validate_experience(exp, i)
            issues.extend(exp_issues)
        
        # Validate bullets
        for bullet in resume.all_bullets:
            bullet_issues = self._validate_bullet(bullet)
            issues.extend(bullet_issues)
        
        # Check overall bullet count
        total_bullets = len(resume.all_bullets)
        if total_bullets < 10:
            issues.append(f"WARNING: Only {total_bullets} bullets (recommended: 15-25)")
        elif total_bullets > 40:
            issues.append(f"WARNING: {total_bullets} bullets (may be too verbose)")
        
        has_errors = any(issue.startswith("ERROR") for issue in issues)
        is_valid = not has_errors
        
        return is_valid, issues
    
    def _validate_experience(self, exp, index: int) -> List[str]:
        """Validate single experience entry"""
        issues = []
        prefix = f"Experience[{index}] ({exp.company})"
        
        if not exp.title:
            issues.append(f"ERROR: {prefix}: Missing title")
        if not exp.company:
            issues.append(f"ERROR: {prefix}: Missing company")
        
        # Check bullet count
        bullet_count = len(exp.bullets)
        if bullet_count < self.config.min_bullets_per_role:
            issues.append(
                f"WARNING: {prefix}: Only {bullet_count} bullets "
                f"(min: {self.config.min_bullets_per_role})"
            )
        elif bullet_count > self.config.max_bullets_per_role:
            issues.append(
                f"WARNING: {prefix}: {bullet_count} bullets "
                f"(max: {self.config.max_bullets_per_role})"
            )
        
        return issues
    
    def _validate_bullet(self, bullet: BulletPoint) -> List[str]:
        """Validate single bullet point"""
        issues = []
        prefix = f"Bullet[{bullet.id}]"
        
        # Check length
        length = len(bullet.text)
        if length < self.config.min_bullet_length:
            issues.append(
                f"WARNING: {prefix}: Too short ({length} chars, "
                f"min: {self.config.min_bullet_length})"
            )
        elif length > self.config.max_bullet_length:
            issues.append(
                f"WARNING: {prefix}: Too long ({length} chars, "
                f"max: {self.config.max_bullet_length})"
            )
        
        # Check for weak verbs
        weak_verbs = ['worked on', 'helped with', 'responsible for', 'involved in']
        text_lower = bullet.text.lower()
        for weak in weak_verbs:
            if weak in text_lower:
                issues.append(f"WARNING: {prefix}: Contains weak phrase '{weak}'")
        
        # Check starts with action verb
        first_word = bullet.text.split()[0] if bullet.text else ''
        if first_word.lower() in ['the', 'a', 'an', 'i', 'we']:
            issues.append(f"WARNING: {prefix}: Should start with action verb")
        
        # Check for numbers/quantification
        if not re.search(r'\d+', bullet.text):
            issues.append(f"INFO: {prefix}: Missing quantification")
        
        return issues
    
    def generate_report(self, resume: ParsedResume) -> str:
        """Generate validation report"""
        is_valid, issues = self.validate_resume(resume)
        
        report = f"""
=== Resume Validation Report ===
Resume: {resume.source_file}
Name: {resume.personal.name}
Total Bullets: {len(resume.all_bullets)}
Experience Entries: {len(resume.experience)}

Status: {'✓ VALID' if is_valid else '✗ INVALID'}

Issues Found: {len(issues)}
"""
        
        if issues:
            report += "\n".join(f"  - {issue}" for issue in issues)
        else:
            report += "\n  No issues found!"
        
        return report

