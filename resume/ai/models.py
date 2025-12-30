# resume/ai/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class BulletEnhancement:
    """AI-enhanced bullet point"""
    original_text: str
    enhanced_text: str
    keywords_added: List[str]
    improvement_score: float      # 0-1, how much better
    confidence: float              # 0-1, AI confidence
    reasoning: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SummaryGeneration:
    """AI-generated professional summary"""
    generated_text: str
    keywords_included: List[str]
    word_count: int
    confidence: float
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationSuggestion:
    """AI suggestion for improvement"""
    section: str                   # "experience", "skills", etc.
    current_text: str
    suggested_text: str
    rationale: str
    expected_improvement: float    # Expected score increase
    keywords_affected: List[str]

