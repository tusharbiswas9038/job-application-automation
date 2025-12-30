# scripts/compare_resumes.py
#!/usr/bin/env python3
"""
Compare two resume versions to see what changed

Usage:
    python scripts/compare_resumes.py --original data/resumes/my_resume.tex --variant data/resumes/variants/resume_Uber_*.tex
    python scripts/compare_resumes.py --original data/resumes/my_resume.tex --variant data/resumes/variants/resume_Uber_*.tex --output reports/comparison.json
    python scripts/compare_resumes.py --original data/resumes/my_resume.tex --variant data/resumes/variants/resume_Uber_*.tex --html reports/comparison.html
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume.tailoring.comparator import ResumeComparator, ResumeComparison

def load_variant_metadata(variant_path: str) -> Optional[dict]:
    """Try to load variant metadata if it exists"""
    from pathlib import Path
    import json
    
    variant_file = Path(variant_path)
    variant_stem = variant_file.stem  # e.g., "resume_Uber_kafka_administrator_4fd346a4"
    
    # Extract short ID from filename (last part)
    parts = variant_stem.split('_')
    short_id = parts[-1] if parts else ""  # e.g., "4fd346a4"
    
    print(f"Looking for metadata with ID: {short_id}")
    
    # Try multiple patterns
    search_patterns = [
        # Exact match
        variant_file.parent / f"{variant_stem}_metadata.json",
        # Short ID with full UUID
        variant_file.parent / f"{short_id}-*_metadata.json",
        # Any file starting with short ID
        variant_file.parent / f"{short_id}*_metadata.json",
        # In reports directory
        Path("reports/variants") / f"*{short_id}*.json",
    ]
    
    # Search using glob patterns
    for pattern in search_patterns:
        if '*' in str(pattern):
            # Use glob for patterns with wildcards
            matches = list(pattern.parent.glob(pattern.name))
            if matches:
                metadata_path = matches[0]  # Take first match
                try:
                    print(f"✓ Loaded metadata: {metadata_path.name}")
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"⚠ Error loading {metadata_path}: {e}")
                    continue
        else:
            # Direct file check
            if pattern.exists():
                try:
                    print(f"✓ Loaded metadata: {pattern.name}")
                    with open(pattern, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"⚠ Error loading {pattern}: {e}")
                    continue
    
    print(f"⚠ No metadata found for variant: {variant_stem}")
    return None


def print_comparison_summary(comparison: ResumeComparison):
    """Print formatted comparison summary"""
    print("\n" + "=" * 80)
    print(f"{'RESUME COMPARISON':^80}")
    print("=" * 80)
    print()
    
    print(f"Original: {Path(comparison.original_path).name}")
    print(f"Variant:  {Path(comparison.variant_path).name}")
    print()
    
    # Overall metrics
    print("Overall Changes:")
    print(f"  Similarity: {comparison.similarity_score:.1%}")
    print(f"  Change Score: {comparison.change_score:.1f}/100")
    print(f"  Summary: {comparison.change_summary}")
    print()
    
    # Summary changes
    if comparison.summary_change:
        sc = comparison.summary_change
        if sc.change_type != "unchanged":
            print("Summary Section:")
            print(f"  Status: {sc.change_summary}")
            if sc.keywords_added:
                print(f"  Keywords Added: {', '.join(sc.keywords_added[:10])}")
            print()
    
    # Bullet statistics
    print("Experience Bullets:")
    print(f"  Original: {comparison.total_bullets_original}")
    print(f"  New: {comparison.total_bullets_new}")
    print(f"  AI Enhanced: {comparison.bullets_ai_enhanced}")
    print(f"  Modified: {comparison.bullets_modified}")
    print(f"  Added: {comparison.bullets_added}")
    print(f"  Removed: {comparison.bullets_removed}")
    print()
    
    # Keywords
    if comparison.keywords_added:
        print("Keywords Added to Resume:")
        print(f"  {', '.join(comparison.keywords_added[:15])}")
        print()


def print_detailed_changes(comparison: ResumeComparison, max_changes: int = 10):
    """Print detailed bullet-by-bullet changes"""
    print("=" * 80)
    print("DETAILED BULLET CHANGES")
    print("=" * 80)
    print()
    
    # Filter for significant changes
    significant = [
        bc for bc in comparison.bullet_changes
        if bc.is_significant
    ]
    
    if not significant:
        print("No significant changes found")
        return
    
    for i, change in enumerate(significant[:max_changes], 1):
        print(f"{i}. [{change.change_type.upper()}]")
        
        if change.change_type in ["modified", "ai_enhanced"]:
            print(f"\n   ORIGINAL ({change.position_original}):")
            print(f"   {change.original_text[:150]}...")
            print(f"\n   NEW ({change.position_new}):")
            print(f"   {change.new_text[:150]}...")
            
            if change.keywords_added:
                print(f"\n   ✓ Keywords Added: {', '.join(change.keywords_added)}")
            print(f"   Similarity: {change.similarity_score:.0%}")
        
        elif change.change_type == "added":
            print(f"\n   NEW ({change.position_new}):")
            print(f"   {change.new_text[:150]}...")
        
        elif change.change_type == "removed":
            print(f"\n   REMOVED ({change.position_original}):")
            print(f"   {change.original_text[:150]}...")
        
        print()
        print("-" * 80)
        print()


def save_comparison_json(comparison: ResumeComparison, output_file: str):
    """Save comparison to JSON"""
    data = {
        'original_file': comparison.original_path,
        'variant_file': comparison.variant_path,
        'compared_at': comparison.compared_at.isoformat(),
        'metrics': {
            'similarity_score': comparison.similarity_score,
            'change_score': comparison.change_score,
            'has_significant_changes': comparison.has_significant_changes,
        },
        'summary': {
            'total_bullets_original': comparison.total_bullets_original,
            'total_bullets_new': comparison.total_bullets_new,
            'bullets_ai_enhanced': comparison.bullets_ai_enhanced,
            'bullets_modified': comparison.bullets_modified,
            'bullets_added': comparison.bullets_added,
            'bullets_removed': comparison.bullets_removed,
            'keywords_added': comparison.keywords_added,
            'change_summary': comparison.change_summary,
        },
        'section_changes': {},
        'bullet_changes': []
    }
    
    # Summary changes
    if comparison.summary_change:
        data['section_changes']['summary'] = {
            'change_type': comparison.summary_change.change_type,
            'word_count_delta': comparison.summary_change.word_count_delta,
            'keywords_added': comparison.summary_change.keywords_added,
            'summary': comparison.summary_change.change_summary,
        }
    
    # Bullet changes
    for bc in comparison.bullet_changes:
        if bc.is_significant:
            data['bullet_changes'].append({
                'change_type': bc.change_type,
                'original_text': bc.original_text,
                'new_text': bc.new_text,
                'position_original': bc.position_original,
                'position_new': bc.position_new,
                'keywords_added': bc.keywords_added,
                'similarity_score': bc.similarity_score,
            })
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Comparison saved to: {output_file}")


def generate_html_report(comparison: ResumeComparison, output_file: str):
    """Generate HTML comparison report"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Resume Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
        .metric-label {{ color: #666; margin-top: 10px; }}
        .change {{ margin: 20px 0; padding: 15px; border-radius: 5px; border-left: 4px solid #ccc; }}
        .change-ai-enhanced {{ border-left-color: #4CAF50; background: #f0f8f0; }}
        .change-modified {{ border-left-color: #2196F3; background: #e3f2fd; }}
        .change-added {{ border-left-color: #FF9800; background: #fff3e0; }}
        .change-removed {{ border-left-color: #f44336; background: #ffebee; }}
        .change-type {{ font-weight: bold; color: #333; margin-bottom: 10px; }}
        .text-block {{ margin: 10px 0; padding: 10px; background: white; border-radius: 3px; }}
        .keywords {{ margin-top: 10px; }}
        .keyword-badge {{ display: inline-block; background: #4CAF50; color: white; padding: 3px 8px; border-radius: 3px; margin: 2px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Resume Comparison Report</h1>
        
        <p><strong>Original:</strong> {Path(comparison.original_path).name}</p>
        <p><strong>Variant:</strong> {Path(comparison.variant_path).name}</p>
        <p><strong>Generated:</strong> {comparison.compared_at.strftime('%Y-%m-%d %H:%M')}</p>
        
        <h2>Overall Metrics</h2>
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{comparison.similarity_score:.0%}</div>
                <div class="metric-label">Similarity</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{comparison.bullets_ai_enhanced}</div>
                <div class="metric-label">AI Enhanced</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{len(comparison.keywords_added)}</div>
                <div class="metric-label">Keywords Added</div>
            </div>
        </div>
        
        <h2>Summary</h2>
        <p>{comparison.change_summary}</p>
"""
    
    # Bullet changes
    if comparison.bullet_changes:
        html += "<h2>Significant Changes</h2>"
        
        significant = [bc for bc in comparison.bullet_changes if bc.is_significant]
        
        for bc in significant[:15]:
            change_class = f"change-{bc.change_type}"
            html += f'<div class="change {change_class}">'
            html += f'<div class="change-type">[{bc.change_type.upper()}]</div>'
            
            if bc.change_type in ["modified", "ai_enhanced"]:
                html += f'<div class="text-block"><strong>Original:</strong><br>{bc.original_text}</div>'
                html += f'<div class="text-block"><strong>New:</strong><br>{bc.new_text}</div>'
                
                if bc.keywords_added:
                    html += '<div class="keywords"><strong>Keywords Added:</strong> '
                    for kw in bc.keywords_added:
                        html += f'<span class="keyword-badge">{kw}</span>'
                    html += '</div>'
            
            html += '</div>'
    
    # Keywords summary
    if comparison.keywords_added:
        html += "<h2>All Keywords Added</h2>"
        html += '<div class="keywords">'
        for kw in comparison.keywords_added[:30]:
            html += f'<span class="keyword-badge">{kw}</span>'
        html += '</div>'
    
    html += """
    </div>
</body>
</html>
"""
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✓ HTML report saved to: {output_file}")


def main():

    parser = argparse.ArgumentParser(
        description="Compare two resume versions"
    )
    parser.add_argument(
        '--original',
        required=True,
        help='Path to original resume (LaTeX)'
    )
    parser.add_argument(
        '--variant',
        required=True,
        help='Path to variant resume (LaTeX)'
    )
    parser.add_argument(
        '--output',
        help='Save comparison to JSON file'
    )
    parser.add_argument(
        '--html',
        help='Generate HTML report'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed bullet-by-bullet changes'
    )

    args = parser.parse_args()

    # Load variant metadata if available
    variant_metadata = load_variant_metadata(args.variant)

    if variant_metadata:
        print(f"✓ Loaded variant metadata: {variant_metadata['variant_id']}\n")

    # Compare resumes
    comparator = ResumeComparator()
    comparison = comparator.compare(
        args.original,
        args.variant,
        variant=variant_metadata  # Pass metadata here
    )
    
    
    try:
        comparator = ResumeComparator()
        comparison = comparator.compare(args.original, args.variant)
        
        # Print summary
        print_comparison_summary(comparison)
        
        # Print detailed changes if requested
        if args.detailed:
            print_detailed_changes(comparison)
        
        # Save JSON if requested
        if args.output:
            save_comparison_json(comparison, args.output)
        
        # Generate HTML if requested
        if args.html:
            generate_html_report(comparison, args.html)
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

