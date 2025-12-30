# scripts/run_processor.py
#!/usr/bin/env python3
"""
CLI script to run job processor
Usage:
    python scripts/run_processor.py --input jobs.json --output normalized.json
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from processor import JobProcessor
from scraper.models import RawJob
from database.db import JobDatabase


def load_raw_jobs(input_file: str) -> list:
    """Load raw jobs from JSON file"""
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'jobs' in data:
        data = data['jobs']
    
    # Convert dicts to RawJob objects
    raw_jobs = []
    for job_data in data:
        # Convert scraped_at string to datetime if needed
        if isinstance(job_data.get('scraped_at'), str):
            job_data['scraped_at'] = datetime.fromisoformat(job_data['scraped_at'])
        
        raw_jobs.append(RawJob(**job_data))
    
    return raw_jobs


def main():
    parser = argparse.ArgumentParser(description='Run job processor')
    parser.add_argument(
        '--input',
        type=str,
        help='Input JSON file with raw jobs (or load from database)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file for normalized jobs'
    )
    parser.add_argument(
        '--save-db',
        action='store_true',
        help='Save normalized jobs to database'
    )
    parser.add_argument(
        '--from-db',
        action='store_true',
        help='Load raw jobs from database (newly scraped)'
    )
    
    args = parser.parse_args()
    
    # Load raw jobs
    if args.from_db:
        db = JobDatabase()
        raw_jobs = db.get_unprocessed_jobs()
        print(f"Loaded {len(raw_jobs)} unprocessed jobs from database")
    elif args.input:
        raw_jobs = load_raw_jobs(args.input)
        print(f"Loaded {len(raw_jobs)} raw jobs from {args.input}")
    else:
        print("Error: Must specify --input or --from-db")
        return 1
    
    if not raw_jobs:
        print("No jobs to process")
        return 0
    
    # Process jobs
    processor = JobProcessor()
    unique_jobs, stats = processor.process(raw_jobs)
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"Processing completed!")
    print(f"{'='*60}")
    print(f"Input jobs: {stats['input_jobs']}")
    print(f"Valid after normalization: {stats['normalized_jobs']}")
    print(f"Unique jobs: {stats['unique_jobs']}")
    print(f"Duplicates removed: {stats['duplicates']}")
    print(f"Kafka-relevant (score >= 50): {stats['kafka_relevant_jobs']}")
    print(f"Remote jobs: {stats['remote_jobs']}")
    print(f"Average relevance score: {stats['avg_relevance_score']:.1f}")
    print(f"Processing time: {stats['processing_time_seconds']:.2f}s")
    print(f"{'='*60}\n")
    
    # Save to database
    if args.save_db:
        db = JobDatabase()
        saved_count = db.insert_normalized_jobs(unique_jobs)
        print(f"Saved {saved_count} jobs to database")
    
    # Save to JSON
    if args.output:
        output_data = {
            'stats': stats,
            'jobs': [job.to_dict() for job in unique_jobs]
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        print(f"Normalized jobs saved to: {args.output}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

