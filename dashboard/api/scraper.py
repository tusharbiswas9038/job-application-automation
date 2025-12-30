# dashboard/api/scraper.py

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper.linkedin_scraper import LinkedInScraper
from scraper.config import ScraperConfig
from scraper.processor.normalizer import JobNormalizer
from database.db_manager import DatabaseManager
from dashboard.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory storage for scraping jobs
scraping_jobs = {}


class ScrapingRequest(BaseModel):
    keywords: str
    location: str = "United States"
    max_pages: int = 3
    source: str = "linkedin"


class ImportRequest(BaseModel):
    job_ids: Optional[List[str]] = None


@router.post("/start")
async def start_scraping(
    background_tasks: BackgroundTasks,
    request: ScrapingRequest,
    user: dict = Depends(get_current_user)
) -> Dict:
    """Start a scraping job"""

    job_id = f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Initialize job status
    scraping_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "total_jobs": 0,
        "new_jobs": 0,
        "duplicates": 0,
        "keywords": request.keywords,
        "location": request.location,
        "source": request.source,
        "started_at": datetime.now().isoformat(),
        "message": "Starting scraper..."
    }

    # Run scraping in background
    background_tasks.add_task(
        run_scraping_job,
        job_id=job_id,
        keywords=request.keywords,
        location=request.location,
        max_pages=request.max_pages,
        source=request.source
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": "Scraping started"
    }


@router.get("/status/{job_id}")
async def get_scraping_status(
    job_id: str,
    user: dict = Depends(get_current_user)
) -> Dict:
    """Get status of a scraping job"""

    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return scraping_jobs[job_id]


@router.get("/history")
async def get_scraping_history(
    limit: int = 10,
    user: dict = Depends(get_current_user)
) -> List[Dict]:
    """Get scraping history"""

    jobs = sorted(
        scraping_jobs.values(),
        key=lambda x: x['started_at'],
        reverse=True
    )

    return jobs[:limit]


@router.get("/preview/{job_id}")
async def preview_scraped_jobs(
    job_id: str,
    user: dict = Depends(get_current_user)
) -> List[Dict]:
    """Preview scraped jobs before adding to database"""

    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_data = scraping_jobs[job_id]

    if 'scraped_jobs' not in job_data:
        return []

    return job_data['scraped_jobs']


@router.post("/import/{job_id}")
async def import_scraped_jobs(
    job_id: str,
    import_request: ImportRequest = Body(default=ImportRequest()),
    user: dict = Depends(get_current_user)
) -> Dict:
    """Import scraped jobs to database"""

    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_data = scraping_jobs[job_id]
    scraped_jobs = job_data.get('scraped_jobs', [])

    if not scraped_jobs:
        raise HTTPException(status_code=400, detail="No jobs to import")

    # Filter if specific job IDs provided
    if import_request.job_ids:
        scraped_jobs = [j for j in scraped_jobs if j['temp_id'] in import_request.job_ids]

    db = DatabaseManager()
    imported = 0
    skipped = 0

    for job in scraped_jobs:
        try:
            # Check for duplicates
            existing = db.get_job_by_url(job['job_url'])
            if existing:
                skipped += 1
                continue

            # Add to database
            db.add_job(
                job_url=job['job_url'],
                job_title=job['job_title'],
                company=job['company'],
                location=job.get('location', 'Remote'),
                posted_date=job.get('posted_date'),
                job_description=job.get('description', ''),
                keywords=job.get('keywords', []),
                required_skills=job.get('skills', []),
                source=job.get('source', 'linkedin')
            )
            imported += 1

        except Exception as e:
            logger.error(f"Failed to import job: {e}")
            skipped += 1

    return {
        "success": True,
        "imported": imported,
        "skipped": skipped,
        "total": len(scraped_jobs)
    }


async def run_scraping_job(
    job_id: str,
    keywords: str,
    location: str,
    max_pages: int,
    source: str
):
    """Background task to run scraping"""

    try:
        # Update status
        scraping_jobs[job_id]['message'] = "Initializing scraper..."
        scraping_jobs[job_id]['progress'] = 10

        # Initialize scraper
        config = ScraperConfig()

        if source == "linkedin":
            scraper = LinkedInScraper(config)
        else:
            scraping_jobs[job_id]['status'] = "error"
            scraping_jobs[job_id]['message'] = f"Unsupported source: {source}"
            return

        # Run scraping
        scraping_jobs[job_id]['message'] = f"Scraping {source}..."
        scraping_jobs[job_id]['progress'] = 30

        result = scraper.scrape(
            keywords=keywords,
            location=location,
            max_pages=max_pages
        )

        scraping_jobs[job_id]['progress'] = 60
        scraping_jobs[job_id]['message'] = "Processing results..."

        # Normalize jobs
        normalizer = JobNormalizer()
        processed_jobs = []

        for raw_job in result.jobs:
            try:
                normalized = normalizer.normalize(raw_job)

                # Convert to dict for JSON serialization
                processed_jobs.append({
                    'temp_id': f"temp_{len(processed_jobs)}",
                    'job_title': normalized.title,
                    'company': normalized.company,
                    'location': normalized.location,
                    'job_url': normalized.url,
                    'posted_date': normalized.posted_date.isoformat() if normalized.posted_date else None,
                    'description': normalized.description_text,
                    'keywords': normalized.keywords_found[:10] if normalized.keywords_found else [],
                    'skills': [],
                    'source': source,
                    'salary': f'${normalized.salary_min}-${normalized.salary_max}' if normalized.salary_min else None
                })
            except Exception as e:
                logger.error(f"Failed to normalize job: {e}")
                continue

        scraping_jobs[job_id]['progress'] = 80
        scraping_jobs[job_id]['message'] = "Checking for duplicates..."

        # Check duplicates
        db = DatabaseManager()
        new_jobs = []
        duplicates = 0

        for job in processed_jobs:
            existing = db.get_job_by_url(job['job_url'])
            if existing:
                duplicates += 1
                job['is_duplicate'] = True
            else:
                job['is_duplicate'] = False
                new_jobs.append(job)

        # Update final status
        scraping_jobs[job_id].update({
            'status': 'completed',
            'progress': 100,
            'total_jobs': len(processed_jobs),
            'new_jobs': len(new_jobs),
            'duplicates': duplicates,
            'scraped_jobs': processed_jobs,
            'completed_at': datetime.now().isoformat(),
            'message': f"Found {len(new_jobs)} new jobs, {duplicates} duplicates"
        })

    except Exception as e:
        logger.error(f"Scraping job failed: {e}", exc_info=True)
        scraping_jobs[job_id].update({
            'status': 'error',
            'progress': 0,
            'message': f"Error: {str(e)}",
            'completed_at': datetime.now().isoformat()
        })
