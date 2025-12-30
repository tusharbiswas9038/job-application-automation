# resume/tailoring/__init__.py
"""
Resume tailoring and variant generation
"""

from resume.tailoring.variant_generator import VariantGenerator
from resume.tailoring.bullet_selector import BulletSelector
from resume.tailoring.template_engine import TemplateEngine
from resume.tailoring.models import (
    ResumeVariant, VariantContent, VariantGenerationConfig
)

__all__ = [
    'VariantGenerator',
    'BulletSelector',
    'TemplateEngine',
    'ResumeVariant',
    'VariantContent',
    'VariantGenerationConfig',
]

