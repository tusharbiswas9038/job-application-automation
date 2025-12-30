# scripts/batch_fit_score.py
#!/usr/bin/env python3
"""
Batch score multiple candidates for same role

Usage:
    python scripts/batch_fit_score.py --resumes data/resumes/*.tex --requirements data/job_requirements/kafka_admin.yaml
    python scripts/batch_fit_score.py --resumes data/resumes/*.tex --requirements data/job_requirements/kafka_admin.yaml --output reports/batch_results.json
"""

import argparse
import json
import logging
import sys
import glob
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume.latex_parser import LaTeXResumeParser
from resume.job_fit.fit_scorer import JobFitScorer
from resume.job_fit.models import FitComparison
from scripts.evaluate_fit import load_job_requirements

logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger(__name__)


def score_candidates(resume_files, job_requirements):
    """Score all candidates"""
    parser = LaTeXResumeParser()
    scorer = JobFitScorer()
    
    scores = []
    
    for resume_file in resume_files:
        try:
            logger.info(f"Scoring: {resume_file}")
            resume = parser.parse_file(resume_file)
            score = scorer.score_fit(resume, job_requirements)
            scores.append((resume_file, score))
        except Exception as e:
            logger.error(f"Error scoring {resume_file}: {e}")
    
    return scores


def print_comparison(scores, job_title):
    """Print comparison table"""
    print("\n" + "=" * 90)
    print(f"{'CANDIDATE COMPARISON':^90}")
    print("=" * 90)
    print(f"Position: {job_title}")
    print()
    
    # Sort by overall fit
    sorted_scores = sorted(scores, key=lambda x: x[1].overall_fit, reverse=True)
    
    # Header
    print(f"{'Rank':<6} {'Candidate':<25} {'Overall':<10} {'Skills':<10} {'Exp':<10} {'Fit Level':<15}")
    print("-" * 90)
    
    # Rows
    for i, (resume_file, score) in enumerate(sorted_scores, 1):
        name = score.candidate_name or Path(resume_file).stem
        
        # Truncate name if too long
        if len(name) > 24:
            name = name[:21] + "..."
        
        # Color code overall fit
        fit_color = (
            '\033[92m' if score.overall_fit >= 80 else
            '\033[93m' if score.overall_fit >= 70 else
            '\033[91m'
        )
        reset_color = '\033[0m'
        
        print(
            f"{i:<6} "
            f"{name:<25} "
            f"{fit_color}{score.overall_fit:5.1f}/100{reset_color} "
            f"{score.skill_fit:5.1f}/100 "
            f"{score.experience_fit:5.1f}/100 "
            f"{score.fit_level.value:<15}"
        )
    
    print("=" * 90)
    print()
    
    # Best candidate
    if sorted_scores:
        best_file, best_score = sorted_scores[0]
        print(f"🏆 Best Candidate: {best_score.candidate_name}")
        print(f"   Overall Fit: {best_score.overall_fit:.1f}/100")
        print(f"   Recommendation: {best_score.hire_recommendation}")
        print()


def print_top_candidates(scores, top_n=3):
    """Print detailed info for top candidates"""
    sorted_scores = sorted(scores, key=lambda x: x[1].overall_fit, reverse=True)
    
    print("=" * 90)
    print(f"TOP {min(top_n, len(sorted_scores))} CANDIDATES - DETAILED VIEW")
    print("=" * 90)
    print()
    
    for i, (resume_file, score) in enumerate(sorted_scores[:top_n], 1):
        print(f"{i}. {score.candidate_name} ({score.overall_fit:.1f}/100)")
        print()
        
        # Strengths
        if score.strengths:
            print("   Strengths:")
            for strength in score.strengths[:3]:
                print(f"   • {strength}")
            print()
        
        # Gaps
        if score.critical_gaps:
            print("   Critical Gaps:")
            for gap in score.critical_gaps[:3]:
                print(f"   • {gap}")
            print()
        
        print("-" * 90)
        print()


def save_batch_report(scores, job_title, output_file):
    """Save batch comparison report"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    sorted_scores = sorted(scores, key=lambda x: x[1].overall_fit, reverse=True)
    
    report = {
        'evaluated_at': datetime.now().isoformat(),
        'job_title': job_title,
        'total_candidates': len(scores),
        'candidates': []
    }
    
    for rank, (resume_file, score) in enumerate(sorted_scores, 1):
        report['candidates'].append({
            'rank': rank,
            'name': score.candidate_name,
            'resume_file': str(resume_file),
            'overall_fit': score.overall_fit,
            'fit_level': score.fit_level.value,
            'component_scores': {
                'skill': score.skill_fit,
                'experience': score.experience_fit,
                'trajectory': score.trajectory_fit,
                'culture': score.culture_fit,
                'education': score.education_fit,
            },
            'strengths': score.strengths,
            'critical_gaps': score.critical_gaps,
            'hire_recommendation': score.hire_recommendation,
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Batch report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Batch score multiple candidates for same role'
    )
    
    parser.add_argument(
        '--resumes',
        nargs='+',
        required=True,
        help='Resume files to score (supports wildcards)'
    )
    
    parser.add_argument(
        '--requirements',
        required=True,
        help='Path to job requirements file (.yaml)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for batch report (JSON)'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=3,
        help='Number of top candidates to show details for'
    )
    
    args = parser.parse_args()
    
    try:
        # Expand wildcards
        resume_files = []
        for pattern in args.resumes:
            resume_files.extend(glob.glob(pattern))
        
        if not resume_files:
            print("ERROR: No resume files found")
            sys.exit(1)
        
        print(f"Found {len(resume_files)} resume(s) to evaluate")
        
        # Load job requirements
        job_requirements = load_job_requirements(args.requirements)
        
        # Score all candidates
        print(f"Evaluating candidates for: {job_requirements.job_title}")
        scores = score_candidates(resume_files, job_requirements)
        
        if not scores:
            print("ERROR: No candidates successfully scored")
            sys.exit(1)
        
        # Print comparison
        print_comparison(scores, job_requirements.job_title)
        
        # Print top candidates
        print_top_candidates(scores, args.top)
        
        # Save report
        if args.output:
            save_batch_report(scores, job_requirements.job_title, args.output)
        
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()

