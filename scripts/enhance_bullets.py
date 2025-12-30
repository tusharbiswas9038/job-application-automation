# scripts/enhance_bullets.py
#!/usr/bin/env python3
"""
Enhance resume bullets using AI

Usage:
    python scripts/enhance_bullets.py --resume data/resumes/my_resume.tex --jd data/job_descriptions/kafka_admin_uber.txt --job-title "Kafka Administrator"
    python scripts/enhance_bullets.py --resume data/resumes/my_resume.tex --jd data/job_descriptions/kafka_admin_uber.txt --job-title "Kafka Administrator" --top 10
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume.latex_parser import LaTeXResumeParser
from resume.ats.keyword_extractor import KeywordExtractor
from resume.ai.ollama_client import OllamaClient
from resume.ai.bullet_enhancer import BulletEnhancer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Enhance resume bullets using AI'
    )
    
    parser.add_argument('--resume', required=True, help='Path to resume (.tex)')
    parser.add_argument('--jd', required=True, help='Path to job description (.txt)')
    parser.add_argument('--job-title', required=True, help='Target job title')
    parser.add_argument('--top', type=int, default=5, help='Number of bullets to enhance')
    
    args = parser.parse_args()
    
    try:
        # Check Ollama
        ollama = OllamaClient()
        if not ollama.is_available():
            logger.error("Ollama is not available. Start it with: ollama serve")
            sys.exit(1)
        
        # Parse resume
        parser_obj = LaTeXResumeParser()
        resume = parser_obj.parse_file(args.resume)
        
        # Read JD
        with open(args.jd, 'r') as f:
            jd_text = f.read()
        
        # Extract keywords
        keyword_extractor = KeywordExtractor()
        jd_keywords = keyword_extractor.extract_keywords(jd_text)
        top_keywords = [kw.keyword for kw in jd_keywords[:20]]
        
        # Enhance bullets
        enhancer = BulletEnhancer(ollama)
        
        print("\n" + "=" * 80)
        print(f"{'BULLET ENHANCEMENT SUGGESTIONS':^80}")
        print("=" * 80)
        print()
        
        enhanced_count = 0
        
        for bullet in resume.all_bullets[:args.top * 2]:  # Try more
            enhancement = enhancer.enhance_bullet(
                bullet,
                args.job_title,
                top_keywords
            )
            
            if enhancement:
                enhanced_count += 1
                
                print(f"{enhanced_count}. Original:")
                print(f"   {bullet.text}")
                print()
                print(f"   Enhanced (Confidence: {enhancement.confidence:.0%}):")
                print(f"   {enhancement.enhanced_text}")
                
                if enhancement.keywords_added:
                    print(f"   Keywords Added: {', '.join(enhancement.keywords_added)}")
                
                print(f"   Improvement Score: {enhancement.improvement_score:.0%}")
                print()
                print("-" * 80)
                print()
                
                if enhanced_count >= args.top:
                    break
        
        print(f"\n✓ Enhanced {enhanced_count} bullets")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()

