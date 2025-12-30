# scripts/generate_variant.py
#!/usr/bin/env python3
"""
Generate tailored resume variant for a specific job

Usage:
    python scripts/generate_variant.py --resume data/resumes/my_resume.tex --jd data/job_descriptions/kafka_admin_uber.txt --job-title "Kafka Administrator" --company "Uber"
    python scripts/generate_variant.py --resume data/resumes/my_resume.tex --jd data/job_descriptions/kafka_admin_uber.txt --job-title "Kafka Administrator" --company "Uber" --requirements data/job_requirements/kafka_admin_uber.yaml
"""

import argparse
import logging
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume.ats.models import KeywordCategory
from resume.tailoring.variant_generator import VariantGenerator
from resume.tailoring.models import VariantGenerationConfig, ResumeVariant, ResumeVariant
from resume.ai.ollama_client import OllamaClient
from scripts.evaluate_fit import load_job_requirements
from datetime import datetime, date
from enum import Enum
from database.db_manager import DatabaseManager
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def print_variant_summary(variant):
    """Print formatted variant summary"""
    print("\n" + "=" * 70)
    print(f"{'RESUME VARIANT GENERATED':^70}")
    print("=" * 70)
    print()
    
    print(f"Job Title: {variant.job_title}")
    if variant.company:
        print(f"Company: {variant.company}")
    print(f"Variant ID: {variant.variant_id[:8]}")
    print()
    
    print("Files Generated:")
    print(f"  LaTeX: {variant.latex_path}")
    if variant.pdf_path:
        print(f"  PDF:   {variant.pdf_path}")
    print()
    
    # Content statistics
    if variant.content:
        print("Content Statistics:")
        print(f"  Total Bullets: {variant.content.total_bullets}")
        print(f"  Experience Sections: {len(variant.content.experience_sections)}")
        
        for i, section in enumerate(variant.content.experience_sections, 1):
            enhanced_count = sum(1 for sb in section.selected_bullets if sb.was_enhanced)
            print(f"    {i}. {section.experience.title}: {len(section.selected_bullets)} bullets")
            if enhanced_count > 0:
                print(f"       ({enhanced_count} AI-enhanced)")
        print()
    
    # AI enhancements
    if variant.bullets_enhanced > 0:
        print(f"AI Enhancements:")
        print(f"  Bullets Enhanced: {variant.bullets_enhanced}")
        if variant.keywords_added:
            print(f"  Keywords Added: {', '.join(variant.keywords_added[:5])}")
        print()
    
    # Scores
    if variant.ats_score:
        score_color = (
            '\033[92m' if variant.ats_score.overall_score >= 80 else
            '\033[93m' if variant.ats_score.overall_score >= 70 else
            '\033[91m'
        )
        reset_color = '\033[0m'
        
        print("Scores:")
        print(f"  ATS Score: {score_color}{variant.ats_score.overall_score:.1f}/100{reset_color}")
        print(f"  Keyword Score: {variant.ats_score.keyword_score:.1f}%")
        
        if variant.fit_score:
            fit_color = (
                '\033[92m' if variant.fit_score.overall_fit >= 70 else
                '\033[93m' if variant.fit_score.overall_fit >= 60 else
                '\033[91m'
            )
            print(f"  Job Fit Score: {fit_color}{variant.fit_score.overall_fit:.1f}/100{reset_color}")
        print()
    
    print("=" * 70)


def print_bullet_details(variant, show_all=False):
    """Print detailed bullet selection info"""
    if not variant.content:
        return
    
    print("\n" + "=" * 70)
    print("BULLET SELECTION DETAILS")
    print("=" * 70)
    print()
    
    for exp_section in variant.content.experience_sections:
        print(f"{exp_section.experience.title} @ {exp_section.experience.company}")
        print(f"  Selected: {len(exp_section.selected_bullets)} / {exp_section.total_available}")
        print()
        
        for i, sb in enumerate(exp_section.selected_bullets, 1):
            if sb.was_enhanced:
                print(f"  {i}. ⭐ [ENHANCED] (Score: {sb.relevance_score:.2f})")
                print(f"     Original: {sb.bullet.text[:80]}...")
                print(f"     Enhanced: {sb.enhanced_version[:80]}...")
            else:
                status = "✓" if sb.relevance_score >= 0.7 else "~"
                print(f"  {i}. {status} (Score: {sb.relevance_score:.2f})")
                print(f"     {sb.bullet.text[:100]}...")
            
            if show_all:
                print(f"     Reason: {sb.selection_reason}")
            print()
        
        print()


def save_variant_metadata(variant: ResumeVariant, output_path: str):
    """Save variant metadata to JSON with proper serialization"""
    from datetime import datetime, date
    from enum import Enum
    
    def serialize_obj(obj):
        """Convert dataclass objects to dictionaries"""
        # Handle None
        if obj is None:
            return None
        
        # Handle datetime objects - MUST be before other checks
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        
        # Handle enums - convert to string/value
        if isinstance(obj, Enum):
            return obj.value if hasattr(obj, 'value') else str(obj)
        
        # Handle dataclasses
        if hasattr(obj, '__dataclass_fields__'):
            return {
                field: serialize_obj(getattr(obj, field))
                for field in obj.__dataclass_fields__
            }
        
        # Handle lists
        elif isinstance(obj, list):
            return [serialize_obj(item) for item in obj]
        
        # Handle dicts
        elif isinstance(obj, dict):
            return {k: serialize_obj(v) for k, v in obj.items()}
        
        # Handle sets
        elif isinstance(obj, set):
            return list(obj)
        
        # Handle other non-serializable types
        elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool)):
            try:
                return {k: serialize_obj(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
            except:
                return str(obj)
        
        # Return as-is for primitives (str, int, float, bool)
        else:
            return obj
    
    # Create serializable metadata - only include attributes that exist
    metadata = {}
    
    # Always present attributes
    if hasattr(variant, 'variant_id'):
        metadata['variant_id'] = variant.variant_id
    if hasattr(variant, 'job_title'):
        metadata['job_title'] = variant.job_title
    if hasattr(variant, 'company'):
        metadata['company'] = variant.company
    if hasattr(variant, 'latex_path'):
        metadata['latex_path'] = variant.latex_path
    if hasattr(variant, 'pdf_path'):
        metadata['pdf_path'] = variant.pdf_path
    if hasattr(variant, 'bullets_enhanced'):
        metadata['bullets_enhanced'] = variant.bullets_enhanced
    if hasattr(variant, 'keywords_added'):
        metadata['keywords_added'] = variant.keywords_added
    
    # Add generated_at timestamp
    metadata['generated_at'] = datetime.now().isoformat()
    
    # Serialize complex objects if they exist
    if hasattr(variant, 'ats_score') and variant.ats_score:
        metadata['ats_score'] = serialize_obj(variant.ats_score)
    
    if hasattr(variant, 'content') and variant.content:
        metadata['content'] = serialize_obj(variant.content)
    
    # Save to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Metadata saved to: {output_path}")


def save_to_database(variant, jd_file_path: str, job_requirements_path: Optional[str] = None):
    """Save variant and scores to database"""
    import sqlite3

    try:
        # Use direct connection instead of DatabaseManager to avoid lock issues
        conn = sqlite3.connect('data/resume_tracker.db', timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Read JD text
        with open(jd_file_path, 'r') as f:
            jd_text = f.read()

        # Check if job exists
        cursor.execute("""
            SELECT job_id FROM jobs
            WHERE company = ? AND job_title = ?
            ORDER BY created_at DESC LIMIT 1
        """, (variant.company, variant.job_title))

        row = cursor.fetchone()
        if row:
            job_id = row[0]
        else:
            # Insert job
            cursor.execute("""
                INSERT INTO jobs (
                    company, job_title, job_description, jd_file_path, requirements_yaml
                ) VALUES (?, ?, ?, ?, ?)
            """, (variant.company, variant.job_title, jd_text, jd_file_path, job_requirements_path))
            job_id = cursor.lastrowid

        # Get metadata path
        latex_filename = Path(variant.latex_path).stem
        metadata_path = Path(variant.latex_path).parent / f"{latex_filename}_metadata.json"

        # Insert variant
        cursor.execute("""
            INSERT INTO variants (
                variant_id, job_id, base_resume_path,
                variant_latex_path, variant_pdf_path, metadata_json_path,
                target_bullets, ai_enhancement_enabled,
                bullets_enhanced, total_bullets, keywords_added
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            variant.variant_id, job_id,
            str(Path(jd_file_path).parent.parent / "resumes" / "my_resume.tex"),
            variant.latex_path,
            variant.pdf_path if variant.pdf_path else '',
            str(metadata_path),
            variant.content.total_bullets if variant.content else 0,
            True,
            variant.bullets_enhanced,
            variant.content.total_bullets if variant.content else 0,
            json.dumps(variant.keywords_added)
        ))

        # Insert ATS score
        # Insert ATS score
        if variant.ats_score:
            try:
                # Count keyword categories
                required_found = len([m for m in variant.ats_score.matched_keywords
                                     if m.keyword.category.value == 'required'])
                required_total = required_found + len([k for k in variant.ats_score.missing_keywords
                                                      if k.category.value == 'required'])
                optional_found = variant.ats_score.matched_count - required_found

                cursor.execute("""
                    INSERT INTO ats_scores (
                        variant_id, overall_score, keyword_score,
                        format_score, experience_score,
                        required_keywords_found, required_keywords_total,
                        optional_keywords_found, missing_keywords, recommendations
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    variant.variant_id,
                    variant.ats_score.overall_score,
                    variant.ats_score.keyword_score,
                    variant.ats_score.format_score,
                    variant.ats_score.experience_score,
                    required_found,
                    required_total if required_total > 0 else None,
                    optional_found,
                    json.dumps([k.text for k in variant.ats_score.missing_keywords][:10]),
                    json.dumps(variant.ats_score.critical_gaps[:5] + variant.ats_score.improvements[:5])
                ))
            except Exception as e:
                logger.warning(f"Error saving detailed ATS score: {e}")
                # Save basic scores only
                cursor.execute("""
                    INSERT INTO ats_scores (variant_id, overall_score, keyword_score)
                    VALUES (?, ?, ?)
                """, (variant.variant_id, variant.ats_score.overall_score, variant.ats_score.keyword_score))
        
        conn.commit()
        conn.close()
        
        print(f"\n✓ Saved to database (Job ID: {job_id}, Variant ID: {variant.variant_id[:8]})")
    except Exception as e:
        logger.warning(f"Could not save to database: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate tailored resume variant for specific job'
    )
    
    parser.add_argument(
        '--resume',
        required=True,
        help='Path to base resume (.tex)'
    )
    
    parser.add_argument(
        '--jd',
        required=True,
        help='Path to job description (.txt)'
    )
    
    parser.add_argument(
        '--job-title',
        required=True,
        help='Target job title'
    )
    
    parser.add_argument(
        '--company',
        help='Company name'
    )
    
    parser.add_argument(
        '--requirements',
        help='Path to job requirements YAML (for fit scoring)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='data/resumes/variants',
        help='Output directory for variant (default: data/resumes/variants)'
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI enhancements (faster)'
    )
    
    parser.add_argument(
        '--target-bullets',
        type=int,
        default=18,
        help='Target number of bullets (default: 18)'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed bullet selection info'
    )
    
    parser.add_argument(
        '--save-metadata',
        help='Save variant metadata to JSON file'
    )
    
    args = parser.parse_args()
    
    try:
        # Read job description
        with open(args.jd, 'r', encoding='utf-8') as f:
            jd_text = f.read()
        
        # Load job requirements if provided
        job_requirements = None
        if args.requirements:
            logger.info(f"Loading job requirements from {args.requirements}")
            job_requirements = load_job_requirements(args.requirements)
        
        # Configure generation
        config = VariantGenerationConfig(
            target_bullets=args.target_bullets,
            use_ai_enhancement=not args.no_ai
        )
        
        # Check Ollama availability
        if config.use_ai_enhancement:
            ollama = OllamaClient()
            if not ollama.is_available():
                logger.warning("Ollama not available - AI enhancements disabled")
                logger.warning("Start Ollama with: ollama serve")
                config.use_ai_enhancement = False
        
        # Generate variant
        logger.info("Generating resume variant...")
        generator = VariantGenerator(config=config)
        
        variant = generator.generate_variant(
            resume_path=args.resume,
            jd_text=jd_text,
            job_title=args.job_title,
            company=args.company,
            output_dir=args.output_dir,
            job_requirements=job_requirements
        )
        
        # Print summary
        print_variant_summary(variant)
        
        # Print detailed info if requested
        if args.detailed:
            print_bullet_details(variant, show_all=True)
        
        # Save metadata if requested
        if args.save_metadata:
            save_variant_metadata(variant, args.save_metadata)

        # ALSO save metadata automatically to variant directory
        auto_metadata_path = Path(args.output_dir) / f"{variant.variant_id}_metadata.json"
        save_variant_metadata(variant, str(auto_metadata_path))

        # Save to database
        try:
            save_to_database(variant, args.jd, args.requirements)
        except Exception as e:
            logger.warning(f"Database save failed: {e}")
            import traceback; traceback.print_exc()
        
        # Exit code based on ATS score
        if variant.ats_score:
            if variant.ats_score.overall_score >= 70:
                sys.exit(0)
            else:
                logger.warning(f"ATS score below 70: {variant.ats_score.overall_score:.1f}")
                sys.exit(1)
        
        sys.exit(0)
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()


