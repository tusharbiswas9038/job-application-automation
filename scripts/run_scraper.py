# scripts/run_scraper.py
#!/usr/bin/env python3
"""
CLI script to run job scraper
Usage:
    python scripts/run_scraper.py --source all
    python scripts/run_scraper.py --source linkedin
    python scripts/run_scraper.py --source confluent
"""

import argparse
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import JobScraperOrchestrator
from database.db import JobDatabase


def main():
    parser = argparse.ArgumentParser(description='Run job scraper')
    parser.add_argument(
        '--source',
        choices=['all', 'linkedin', 'company'],
        default='all',
        help='Which scrapers to run'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run scraper but don\'t save to database'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = JobScraperOrchestrator()
    
    try:
        # Run scrapers
        if args.source == 'all':
            result = orchestrator.run_all()
        elif args.source == 'linkedin':
            jobs, results = orchestrator.run_linkedin_scrape()
            result = {'jobs': jobs, 'results': results}
        else:  # company
            jobs, results = orchestrator.run_company_scrapes()
            result = {'jobs': jobs, 'results': results}
        
        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"{'='*60}")
        print(f"Total jobs found: {result['stats']['total_found']}")
        print(f"Unique jobs: {result['stats']['unique_jobs']}")
        print(f"Duplicates removed: {result['stats']['duplicates']}")
        print(f"Duration: {result['stats']['duration_seconds']:.2f}s")
        print(f"{'='*60}\n")
        
        # Save to database
        if not args.dry_run:
            db = JobDatabase()
            saved_count, duplicate_count = db.insert_jobs(result['jobs'])
            db.insert_scraping_results(result['results'])
            
            print(f"Saved to database: {saved_count} new, {duplicate_count} duplicates")
        
        # Save to JSON file
        if args.output:
            output_data = {
                'stats': result['stats'],
                'jobs': [job.to_dict() for job in result['jobs']]
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            
            print(f"Results saved to: {args.output}")
    
    finally:
        orchestrator.cleanup()


if __name__ == '__main__':
    main()

