# scripts/parse_resume.py
#!/usr/bin/env python3
"""
CLI script to parse LaTeX resume
Usage:
    python scripts/parse_resume.py --input resume.tex --output resume.json
    python scripts/parse_resume.py --input resume.tex --validate
    python scripts/parse_resume.py --input resume.tex --list-bullets
"""

import argparse
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume.latex_parser import LaTeXResumeParser
from resume.bullet_manager import BulletManager
from resume.validator import ResumeValidator


def main():
    parser = argparse.ArgumentParser(description='Parse LaTeX resume')
    parser.add_argument(
        '--input',
        required=True,
        help='Input .tex resume file'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file for parsed data'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate resume structure'
    )
    parser.add_argument(
        '--list-bullets',
        action='store_true',
        help='List all bullets'
    )
    parser.add_argument(
        '--export-bullets',
        help='Export bullets to JSON file'
    )
    
    args = parser.parse_args()
    
    # Parse resume
    print(f"Parsing resume: {args.input}")
    latex_parser = LaTeXResumeParser()
    
    try:
        resume = latex_parser.parse_file(args.input)
    except Exception as e:
        print(f"ERROR: Failed to parse resume: {e}")
        return 1
    
    print(f"✓ Parsed successfully")
    print(f"  Name: {resume.personal.name}")
    print(f"  Total bullets: {len(resume.all_bullets)}")
    print(f"  Experience entries: {len(resume.experience)}")
    print(f"  Education entries: {len(resume.education)}")
    print(f"  Custom commands: {len(resume.custom_commands)}")
    
    # Validate
    if args.validate:
        print("\n=== Validation ===")
        validator = ResumeValidator()
        report = validator.generate_report(resume)
        print(report)
    
    # List bullets
    if args.list_bullets:
        print("\n=== Bullets ===")
        for i, bullet in enumerate(resume.all_bullets, 1):
            modifiable = "✓" if bullet.is_modifiable else "✗"
            print(f"{i}. [{modifiable}] {bullet.section}/{bullet.subsection}: {bullet.text[:80]}...")
    
    # Export bullets
    if args.export_bullets:
        bullet_mgr = BulletManager()
        bullet_mgr.load_from_resume(resume)
        bullet_mgr.export_bullets(args.export_bullets)
        print(f"\n✓ Bullets exported to: {args.export_bullets}")
    
    # Save to JSON
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(resume.to_dict(), f, indent=2, default=str)
        print(f"\n✓ Resume data saved to: {args.output}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

