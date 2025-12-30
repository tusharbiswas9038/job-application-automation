# scripts/manage_variants.py
#!/usr/bin/env python3
"""
Manage resume variants

Usage:
    python scripts/manage_variants.py list
    python scripts/manage_variants.py compare variant1.json variant2.json
    python scripts/manage_variants.py stats
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))


def list_variants(variants_dir='data/resumes/variants'):
    """List all generated variants"""
    variants_path = Path(variants_dir)
    
    if not variants_path.exists():
        print("No variants directory found")
        return
    
    # Find all .tex files
    tex_files = list(variants_path.glob('*.tex'))
    
    if not tex_files:
        print("No variants found")
        return
    
    print("\n" + "=" * 80)
    print(f"{'RESUME VARIANTS':^80}")
    print("=" * 80)
    print()
    print(f"Found {len(tex_files)} variant(s)")
    print()
    
    for i, tex_file in enumerate(tex_files, 1):
        pdf_file = tex_file.with_suffix('.pdf')
        
        print(f"{i}. {tex_file.name}")
        print(f"   LaTeX: {tex_file}")
        if pdf_file.exists():
            print(f"   PDF: {pdf_file}")
        print(f"   Size: {tex_file.stat().st_size / 1024:.1f} KB")
        print(f"   Modified: {tex_file.stat().st_mtime}")
        print()


def compare_variants(metadata_files: List[str]):
    """Compare multiple variants"""
    variants = []
    
    for metadata_file in metadata_files:
        try:
            with open(metadata_file, 'r') as f:
                variants.append(json.load(f))
        except Exception as e:
            print(f"Error loading {metadata_file}: {e}")
    
    if len(variants) < 2:
        print("Need at least 2 variants to compare")
        return
    
    print("\n" + "=" * 100)
    print(f"{'VARIANT COMPARISON':^100}")
    print("=" * 100)
    print()
    
    # Header
    print(f"{'Metric':<30}", end='')
    for i, v in enumerate(variants, 1):
        print(f"{'Variant ' + str(i):>15}", end='')
    print()
    print("-" * 100)
    
    # Job details
    print(f"{'Job Title':<30}", end='')
    for v in variants:
        title = v['job_title'][:13]
        print(f"{title:>15}", end='')
    print()
    
    print(f"{'Company':<30}", end='')
    for v in variants:
        company = (v.get('company') or 'N/A')[:13]
        print(f"{company:>15}", end='')
    print()
    
    # Content stats
    print(f"{'Total Bullets':<30}", end='')
    for v in variants:
        bullets = v.get('content_stats', {}).get('total_bullets', 0)
        print(f"{bullets:>15}", end='')
    print()
    
    print(f"{'AI Enhanced':<30}", end='')
    for v in variants:
        enhanced = v.get('bullets_enhanced', 0)
        print(f"{enhanced:>15}", end='')
    print()
    
    # Scores
    if any('scores' in v for v in variants):
        print()
        print("Scores:")
        
        print(f"{'  ATS Overall':<30}", end='')
        for v in variants:
            score = v.get('scores', {}).get('ats', {}).get('overall', 0)
            print(f"{score:>14.1f}", end='')
        print()
        
        print(f"{'  Keyword Match':<30}", end='')
        for v in variants:
            score = v.get('scores', {}).get('ats', {}).get('keyword_match', 0)
            print(f"{score:>13.1f}%", end='')
        print()
        
        if any(v.get('scores', {}).get('fit') for v in variants):
            print(f"{'  Job Fit':<30}", end='')
            for v in variants:
                score = v.get('scores', {}).get('fit', {}).get('overall', 0)
                print(f"{score:>14.1f}", end='')
            print()
    
    print()
    print("=" * 100)


def show_stats(variants_dir='data/resumes/variants'):
    """Show statistics about all variants"""
    variants_path = Path(variants_dir)
    
    if not variants_path.exists():
        print("No variants directory found")
        return
    
    tex_files = list(variants_path.glob('*.tex'))
    
    print("\n" + "=" * 70)
    print(f"{'VARIANT STATISTICS':^70}")
    print("=" * 70)
    print()
    
    print(f"Total Variants: {len(tex_files)}")
    
    if tex_files:
        total_size = sum(f.stat().st_size for f in tex_files)
        print(f"Total Size: {total_size / 1024:.1f} KB")
        print(f"Average Size: {total_size / len(tex_files) / 1024:.1f} KB")
    
    # Count PDFs
    pdf_count = len(list(variants_path.glob('*.pdf')))
    print(f"PDFs Generated: {pdf_count}")
    
    print()


def main():
    parser = argparse.ArgumentParser(description='Manage resume variants')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all variants')
    list_parser.add_argument('--dir', default='data/resumes/variants')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare variants')
    compare_parser.add_argument('metadata_files', nargs='+', help='Variant metadata JSON files')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--dir', default='data/resumes/variants')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_variants(args.dir)
    elif args.command == 'compare':
        compare_variants(args.metadata_files)
    elif args.command == 'stats':
        show_stats(args.dir)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

