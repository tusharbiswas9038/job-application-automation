import logging
import subprocess
import re
from pathlib import Path
from typing import Tuple, Optional

from resume.models import ParsedResume
from resume.tailoring.models import ResumeVariant

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Generate LaTeX files preserving original template structure
    """
    
    def __init__(self):
        pass
    
    def generate_files(
        self,
        resume: ParsedResume,
        variant: ResumeVariant,
        output_dir: str
    ) -> Tuple[str, Optional[str]]:
        """Generate LaTeX by modifying original template"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = variant.output_filename
        latex_path = output_path / filename
        
        # Read original LaTeX file
        base_path = Path(variant.base_resume_path)
        if not base_path.exists():
            raise FileNotFoundError(f"Base resume not found: {base_path}")
        
        with open(base_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Modify content while preserving structure
        modified_content = self._modify_template(
            original_content,
            resume,
            variant
        )
        
        # Write modified file
        with open(latex_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        logger.info(f"LaTeX written to: {latex_path}")
        
        # Compile to PDF
        pdf_path = self._compile_pdf(latex_path)
        
        return str(latex_path), pdf_path
    
    def _modify_template(
        self,
        original: str,
        resume: ParsedResume,
        variant: ResumeVariant
    ) -> str:
        """Modify original template with variant content"""
        content = original
        
        # 1. Replace summary
        content = self._replace_summary(content, variant.content.summary)
        
        # 2. Replace experience bullets
        content = self._replace_experience_bullets(content, variant)
        
        return content
    
    def _replace_summary(self, content: str, new_summary: str) -> str:
        """Replace summary section"""
        # Pattern: \section*{Summary}\n...content...\n\n%-----------
        pattern = (
            r'(\\section\*\{Summary\}\s*\n)'
            r'(.*?)'
            r'(\n\s*%-+[A-Z\s]+-+)'
        )
        
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(
                pattern,
                r'\1' + new_summary + '\n' + r'\3',
                content,
                flags=re.DOTALL,
                count=1
            )
            logger.info("✓ Replaced summary section")
        else:
            logger.warning("⚠ Summary section not found")
        
        return content
    
    def _replace_experience_bullets(self, content: str, variant) -> str:
        """Replace experience bullets preserving custom commands"""
        
        # Pattern to match the itemize block
        pattern = (
            r'(\\resumeItemListStart\s*\n)'
            r'((?:.*?\n)*?)'  # All lines between start and end
            r'(\s*\\resumeItemListEnd)'
        )
        
        # Build replacement bullets
        new_bullets = []
        for exp_section in variant.content.experience_sections:
            for selected_bullet in exp_section.selected_bullets:
                bullet_text = (
                    selected_bullet.enhanced_version
                    if selected_bullet.was_enhanced
                    else selected_bullet.bullet.text
                )
                
                # Clean up AI artifacts
                bullet_text = re.sub(r'\s*\[X\]\s*\.?', '', bullet_text)
                bullet_text = bullet_text.strip()
                
                # Proper indentation and escaping
                new_bullets.append(f'      \\resumeItem{{{bullet_text}}}')
        
        bullets_block = '\n'.join(new_bullets) + '\n'
        
        # Replace first occurrence (the experience section)
        match = re.search(pattern, content, re.DOTALL)
        if match:
            replacement = match.group(1) + bullets_block + match.group(3)
            content = content[:match.start()] + replacement + content[match.end():]
            logger.info(f"✓ Replaced experience bullets")
        else:
            logger.warning(f"⚠ Could not find experience bullets block")
        
        return content
    
    def _compile_pdf(self, latex_path: Path) -> Optional[str]:
        """Compile LaTeX to PDF"""
        try:
            import shutil
            
            if not shutil.which('pdflatex'):
                logger.warning("pdflatex not found, skipping PDF compilation")
                return None
            
            # Compile twice for references
            for run in [1, 2]:
                subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', 
                     '-output-directory', str(latex_path.parent), 
                     str(latex_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            pdf_path = latex_path.with_suffix('.pdf')
            if pdf_path.exists():
                logger.info(f"✓ PDF compiled successfully")
                
                # Cleanup
                for ext in ['.aux', '.log', '.out']:
                    aux_file = latex_path.with_suffix(ext)
                    if aux_file.exists():
                        aux_file.unlink()
                
                return str(pdf_path)
            
            return None
        
        except Exception as e:
            logger.error(f"PDF compilation error: {e}")
            return None
