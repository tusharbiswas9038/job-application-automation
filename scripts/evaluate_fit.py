# scripts/evaluate_fit.py
#!/usr/bin/env python3
"""
Evaluate job fit for a candidate

Usage:
    python scripts/evaluate_fit.py --resume data/resumes/my_resume.tex --requirements data/job_requirements/kafka_admin.yaml
    python scripts/evaluate_fit.py --resume data/resumes/my_resume.tex --requirements data/job_requirements/kafka_admin.yaml --output reports/fit_report.json
"""

import argparse
import json
import logging
import sys
import yaml
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume.latex_parser import LaTeXResumeParser
from resume.job_fit.fit_scorer import JobFitScorer
from resume.job_fit.models import (
    JobRequirements, SkillLevel, ExperienceLevel
)

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def load_job_requirements(requirements_file: str) -> JobRequirements:
    """Load job requirements from YAML file"""
    path = Path(requirements_file)
    
    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_file}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Parse skill levels
    required_skills = {
        skill: SkillLevel[level.upper()]
        for skill, level in data.get('required_skills', {}).items()
    }
    
    preferred_skills = {
        skill: SkillLevel[level.upper()]
        for skill, level in data.get('preferred_skills', {}).items()
    }
    
    # Parse experience level
    exp_level = ExperienceLevel[data.get('experience_level', 'MID').upper()]
    
    return JobRequirements(
        job_title=data['job_title'],
        company=data.get('company', 'Unknown'),
        experience_level=exp_level,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        min_years_experience=data.get('min_years_experience', 3),
        domain_experience_required=data.get('domain_experience', []),
        company_size=data.get('company_size', 'enterprise'),
        work_environment=data.get('work_environment', 'hybrid'),
        team_structure=data.get('team_structure', 'collaborative'),
        education_required=data.get('education_required'),
        certifications_required=data.get('certifications_required', [])
    )


def print_fit_summary(score):
    """Print formatted fit summary"""
    print("\n" + "=" * 70)
    print(f"{'JOB FIT EVALUATION':^70}")
    print("=" * 70)
    print()
    
    # Overall fit with color
    fit_color = (
        '\033[92m' if score.overall_fit >= 80 else   # Green
        '\033[93m' if score.overall_fit >= 70 else   # Yellow
        '\033[91m'                                     # Red
    )
    reset_color = '\033[0m'
    
    print(f"Candidate: {score.candidate_name}")
    print(f"Position: {score.job_title}")
    print()
    print(f"Overall Fit: {fit_color}{score.overall_fit:.1f}/100{reset_color} ({score.fit_level.value.upper()})")
    print(f"Recommendation: {score.hire_recommendation}")
    print()
    
    # Component scores
    print("Component Breakdown:")
    print(f"  Skills:      {score.skill_fit:5.1f}/100  {'█' * int(score.skill_fit / 10)}")
    print(f"  Experience:  {score.experience_fit:5.1f}/100  {'█' * int(score.experience_fit / 10)}")
    print(f"  Trajectory:  {score.trajectory_fit:5.1f}/100  {'█' * int(score.trajectory_fit / 10)}")
    print(f"  Culture:     {score.culture_fit:5.1f}/100  {'█' * int(score.culture_fit / 10)}")
    print(f"  Education:   {score.education_fit:5.1f}/100  {'█' * int(score.education_fit / 10)}")
    print()


def print_strengths(score):
    """Print candidate strengths"""
    if not score.strengths:
        return
    
    print("=" * 70)
    print("KEY STRENGTHS")
    print("=" * 70)
    print()
    
    for i, strength in enumerate(score.strengths, 1):
        print(f"  {i}. {strength}")
    print()


def print_gaps(score):
    """Print skill gaps"""
    if not score.critical_gaps:
        return
    
    print("=" * 70)
    print("CRITICAL GAPS")
    print("=" * 70)
    print()
    
    for i, gap in enumerate(score.critical_gaps, 1):
        print(f"  {i}. {gap}")
    print()
    
    # Show development recommendations
    if score.development_areas:
        print("=" * 70)
        print("DEVELOPMENT RECOMMENDATIONS")
        print("=" * 70)
        print()
        
        for rec in score.development_areas:
            print(rec)
            print()


def print_skill_details(score, limit=10):
    """Print detailed skill analysis"""
    print("=" * 70)
    print("SKILL MATCH DETAILS")
    print("=" * 70)
    print()
    
    # Top skill matches
    if score.skill_matches:
        print("Matched Skills:")
        print()
        
        top_matches = sorted(
            score.skill_matches,
            key=lambda m: m.match_strength,
            reverse=True
        )[:limit]
        
        for i, match in enumerate(top_matches, 1):
            strength_icon = '✓✓' if match.match_strength >= 0.9 else '✓' if match.match_strength >= 0.7 else '~'
            
            print(f"{i:2}. {strength_icon} {match.skill_name}")
            print(f"    Required: {match.required_level.value.title()}")
            print(f"    Candidate: {match.candidate_level.value.title()}")
            print(f"    Match Strength: {match.match_strength:.0%}")
            if match.years_experience:
                print(f"    Experience: {match.years_experience} years")
            print()
    
    # Skill gaps
    if score.skill_gaps:
        critical_gaps = [g for g in score.skill_gaps if g.gap_severity == "critical"]
        
        if critical_gaps:
            print("Critical Skill Gaps:")
            print()
            
            for i, gap in enumerate(critical_gaps[:5], 1):
                print(f"{i}. {gap.skill_name}")
                print(f"   Required: {gap.required_level.value.title()}")
                print(f"   Current: {gap.current_level.value.title()}")
                print(f"   Training Time: {gap.training_time}")
                print()


def print_experience_details(score):
    """Print experience relevance details"""
    if not score.experience_matches:
        return
    
    print("=" * 70)
    print("EXPERIENCE RELEVANCE")
    print("=" * 70)
    print()
    
    for i, exp in enumerate(score.experience_matches[:3], 1):
        relevance_icon = '★★★' if exp.relevance_score >= 0.8 else '★★' if exp.relevance_score >= 0.6 else '★'
        
        print(f"{i}. {relevance_icon} {exp.job_title} @ {exp.company}")
        print(f"   Relevance: {exp.relevance_score:.0%}")
        print(f"   Duration: {exp.duration_months} months")
        print(f"   Recency: {exp.recency_score:.0%}")
        
        if exp.matching_aspects:
            print(f"   Matches: {', '.join(exp.matching_aspects)}")
        
        if exp.technology_overlap:
            print(f"   Tech Overlap: {', '.join(exp.technology_overlap[:5])}")
        print()


def print_career_trajectory(score):
    """Print career trajectory analysis"""
    trajectory = score.career_trajectory
    
    print("=" * 70)
    print("CAREER TRAJECTORY")
    print("=" * 70)
    print()
    
    print(f"Current Level: {trajectory.current_level.value.upper()}")
    print(f"Progression: {trajectory.progression_trend.upper()}")
    print(f"Promotions: {trajectory.promotions_count}")
    print(f"Avg Tenure: {trajectory.avg_tenure_months / 12:.1f} years per role")
    print(f"Ready For: {trajectory.ready_for_level.value.upper()}")
    print()
    
    if trajectory.specialization:
        print(f"Specialization: {', '.join(trajectory.specialization)}")
        print()


def save_detailed_report(score, output_file):
    """Save detailed JSON report"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    report = {
        'evaluated_at': score.evaluated_at.isoformat(),
        'candidate_name': score.candidate_name,
        'job_title': score.job_title,
        'overall_fit': score.overall_fit,
        'fit_level': score.fit_level.value,
        'hire_recommendation': score.hire_recommendation,
        'is_good_fit': score.is_good_fit,
        'component_scores': {
            'skill': score.skill_fit,
            'experience': score.experience_fit,
            'trajectory': score.trajectory_fit,
            'culture': score.culture_fit,
            'education': score.education_fit,
        },
        'strengths': score.strengths,
        'critical_gaps': score.critical_gaps,
        'development_areas': score.development_areas,
        'skill_matches': [
            {
                'skill_name': m.skill_name,
                'required_level': m.required_level.value,
                'candidate_level': m.candidate_level.value,
                'match_strength': m.match_strength,
                'years_experience': m.years_experience,
            }
            for m in score.skill_matches
        ],
        'skill_gaps': [
            {
                'skill_name': g.skill_name,
                'required_level': g.required_level.value,
                'current_level': g.current_level.value,
                'importance': g.importance,
                'gap_severity': g.gap_severity,
                'training_time': g.training_time,
                'can_learn': g.can_learn,
            }
            for g in score.skill_gaps
        ],
        'experience_matches': [
            {
                'job_title': e.job_title,
                'company': e.company,
                'relevance_score': e.relevance_score,
                'duration_months': e.duration_months,
                'recency_score': e.recency_score,
                'matching_aspects': e.matching_aspects,
                'technology_overlap': e.technology_overlap,
            }
            for e in score.experience_matches
        ],
        'career_trajectory': {
            'current_level': score.career_trajectory.current_level.value,
            'progression_trend': score.career_trajectory.progression_trend,
            'promotions_count': score.career_trajectory.promotions_count,
            'avg_tenure_months': score.career_trajectory.avg_tenure_months,
            'specialization': score.career_trajectory.specialization,
            'ready_for_level': score.career_trajectory.ready_for_level.value,
        },
        'culture_fit': {
            'company_size_match': score.culture_indicators.company_size_match,
            'industry_match': score.culture_indicators.industry_match,
            'work_style_indicators': score.culture_indicators.work_style_indicators,
            'values_alignment': score.culture_indicators.values_alignment,
            'leadership_style': score.culture_indicators.leadership_style,
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Detailed report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate candidate job fit against requirements'
    )
    
    parser.add_argument(
        '--resume',
        required=True,
        help='Path to resume file (.tex)'
    )
    
    parser.add_argument(
        '--requirements',
        required=True,
        help='Path to job requirements file (.yaml)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for detailed JSON report'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed skill and experience analysis'
    )
    
    args = parser.parse_args()
    
    try:
        # Parse resume
        logger.info(f"Parsing resume: {args.resume}")
        parser_obj = LaTeXResumeParser()
        resume = parser_obj.parse_file(args.resume)
        
        # Load job requirements
        logger.info(f"Loading requirements: {args.requirements}")
        job_requirements = load_job_requirements(args.requirements)
        
        # Score fit
        logger.info("Evaluating job fit...")
        scorer = JobFitScorer()
        score = scorer.score_fit(resume, job_requirements)
        
        # Print summary
        print_fit_summary(score)
        
        # Print strengths and gaps
        print_strengths(score)
        print_gaps(score)
        
        # Print detailed analysis if requested
        if args.detailed:
            print_skill_details(score)
            print_experience_details(score)
            print_career_trajectory(score)
        
        # Save detailed report if output specified
        if args.output:
            save_detailed_report(score, args.output)
        
        # Exit code based on fit
        sys.exit(0 if score.is_good_fit else 1)
    
    except Exception as e:
        logger.error(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()

