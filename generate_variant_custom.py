#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from resume.tailoring.variant_generator import VariantGenerator
from resume.tailoring.models import VariantGenerationConfig

# Custom config for single-job resume
config = VariantGenerationConfig(
    target_bullets=18,
    min_bullets_per_job=3,
    max_bullets_per_job=18,  # Allow all bullets from one job
    use_ai_enhancement=True,
    max_bullets_to_enhance=8
)

generator = VariantGenerator(config=config)

with open('data/job_descriptions/kafka_admin_uber.txt', 'r') as f:
    jd_text = f.read()

variant = generator.generate_variant(
    resume_path="data/resumes/my_resume.tex",
    jd_text=jd_text,
    job_title="Kafka Administrator",
    company="Uber",
    output_dir="data/resumes/variants"
)

print(f"\n{'='*70}")
print(f"{'VARIANT GENERATED':^70}")
print(f"{'='*70}\n")
print(f"Job: {variant.job_title} @ {variant.company}")
print(f"Bullets: {variant.content.total_bullets}/11 available")
print(f"AI Enhanced: {variant.bullets_enhanced}")
if variant.keywords_added:
    print(f"Keywords Added: {', '.join(variant.keywords_added)}")
print(f"\nATS Score: {variant.ats_score.overall_score:.1f}/100")
print(f"Keyword Score: {variant.ats_score.keyword_score:.1f}/100")
print(f"\n✓ LaTeX: {variant.latex_path}")
if variant.pdf_path:
    print(f"✓ PDF: {variant.pdf_path}")
print()
