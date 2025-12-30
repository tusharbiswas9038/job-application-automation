# resume/variant_manager.py
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from resume.config import get_config, ResumeConfig
from resume.models import ParsedResume, BulletPoint

logger = logging.getLogger(__name__)


class VariantManager:
    """Manage resume variants for different job applications"""
    
    def __init__(self, config: Optional[ResumeConfig] = None):
        self.config = config or get_config()
    
    def create_variant(
        self,
        master_resume: ParsedResume,
        variant_name: str,
        bullet_modifications: Dict[str, str],
        summary_override: Optional[str] = None
    ) -> Path:
        """
        Create resume variant with modified bullets
        
        Args:
            master_resume: Original parsed resume
            variant_name: Name for this variant (e.g., 'uber_kafka_admin')
            bullet_modifications: Dict mapping bullet_id -> modified_text
            summary_override: Optional modified summary
        
        Returns:
            Path to generated variant .tex file
        """
        # Read master resume file
        with open(master_resume.source_file, 'r') as f:
            latex_content = f.read()
        
        # Apply modifications
        modified_content = latex_content
        
        # Modify custom commands
        for bullet_id, new_text in bullet_modifications.items():
            # Find original bullet
            original_bullet = next(
                (b for b in master_resume.all_bullets if b.id == bullet_id),
                None
            )
            
            if not original_bullet:
                logger.warning(f"Bullet {bullet_id} not found, skipping")
                continue
            
            if original_bullet.command_name:
                # Replace custom command definition
                old_cmd = f"\\newcommand{{\\{original_bullet.command_name}}}{{{original_bullet.text}}}"
                new_cmd = f"\\newcommand{{\\{original_bullet.command_name}}}{{{new_text}}}"
                
                modified_content = modified_content.replace(old_cmd, new_cmd)
                logger.debug(f"Modified command: {original_bullet.command_name}")
            else:
                # Replace inline bullet
                # This is more complex - need to be careful
                modified_content = modified_content.replace(
                    f"\\item {original_bullet.text}",
                    f"\\item {new_text}"
                )
        
        # Modify summary if provided
        if summary_override and master_resume.summary:
            modified_content = modified_content.replace(
                master_resume.summary,
                summary_override
            )
        
        # Add variant metadata as comment
        metadata_comment = f"""
% Variant: {variant_name}
% Generated: {datetime.now().isoformat()}
% Modified bullets: {len(bullet_modifications)}
"""
        
        # Insert after documentclass
        modified_content = modified_content.replace(
            '\\documentclass',
            metadata_comment + '\\documentclass',
            1
        )
        
        # Save variant
        variant_path = self.config.variants_dir / f"{variant_name}.tex"
        with open(variant_path, 'w') as f:
            f.write(modified_content)
        
        logger.info(f"Created variant: {variant_path}")
        return variant_path
    
    def list_variants(self) -> List[Dict[str, str]]:
        """List all resume variants"""
        variants = []
        
        for tex_file in self.config.variants_dir.glob('*.tex'):
            # Extract metadata from comments
            with open(tex_file, 'r') as f:
                content = f.read()
            
            variant_info = {
                'name': tex_file.stem,
                'path': str(tex_file),
                'modified': datetime.fromtimestamp(tex_file.stat().st_mtime).isoformat()
            }
            
            # Try to extract metadata from comments
            if '% Variant:' in content:
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('% Variant:'):
                        variant_info['variant_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('% Generated:'):
                        variant_info['generated'] = line.split(':', 1)[1].strip()
            
            variants.append(variant_info)
        
        return variants
    
    def delete_variant(self, variant_name: str) -> bool:
        """Delete a resume variant"""
        variant_path = self.config.variants_dir / f"{variant_name}.tex"
        
        if variant_path.exists():
            variant_path.unlink()
            logger.info(f"Deleted variant: {variant_name}")
            return True
        
        return False
    
    def copy_master_to_variant(self, master_path: str, variant_name: str) -> Path:
        """Create a copy of master resume as starting point for variant"""
        master_path = Path(master_path)
        variant_path = self.config.variants_dir / f"{variant_name}.tex"
        
        shutil.copy2(master_path, variant_path)
        logger.info(f"Copied master to variant: {variant_path}")
        
        return variant_path

