# resume/ai/__init__.py
"""
AI-powered resume enhancement
"""

from resume.ai.ollama_client import OllamaClient
from resume.ai.bullet_enhancer import BulletEnhancer
from resume.ai.models import BulletEnhancement, SummaryGeneration

__all__ = [
    'OllamaClient',
    'BulletEnhancer',
    'BulletEnhancement',
    'SummaryGeneration',
]

