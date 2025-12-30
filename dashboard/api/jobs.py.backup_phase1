# dashboard/api/jobs.py

from fastapi import APIRouter, Depends, HTTPException, Form
from typing import List, Dict, Optional
from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import DatabaseManager
from dashboard.auth import get_current_user

router = APIRouter()

@router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
) -> List[Dict]:
    """List all jobs"""
    db = DatabaseManager()
    
    try:
        jobs = db.list_jobs(status=status, limit=limit)
        
        # Enrich with pipeline data
        pipeline = db.get_job_pipeline()
        pipeline_map = {p['job_id']: p for p in pipeline}
        
        enriched_jobs = []
        for job in jobs:
            job_data = dict(job)
            pipeline_data = pipeline_map.get(job['job_id'], {})
            
            job_data.update({
                "variants_count": pipeline_data.get('variants_generated', 0),
                "applications_count": pipeline_data.get('applications_count', 0),
                "best_ats_score": pipeline_data.get('best_ats_score', 0),
                "last_applied_date": pipeline_data.get('last_applied_date')
            })
            
            enriched_jobs.append(job_data)
        
        return enriched_jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}")
async def get_job(job_id: int, user: dict = Depends(get_current_user)) -> Dict:
    """Get job by ID"""
    db = DatabaseManager()
    
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get variants for this job
    variants = db.list_variants(job_id=job_id)
    
    # Get pipeline data
    pipeline = db.get_job_pipeline()
    pipeline_data = next((p for p in pipeline if p['job_id'] == job_id), {})
    
    job_data = dict(job)
    job_data.update({
        "variants": variants,
        "variants_count": len(variants),
        "best_ats_score": pipeline_data.get('best_ats_score', 0),
        "applications_count": pipeline_data.get('applications_count', 0)
    })
    
    return job_data

@router.post("/")
async def create_job(
    company: str = Form(...),
    job_title: str = Form(...),
    job_description: str = Form(...),
    job_url: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    salary_range: Optional[str] = Form(None),
    employment_type: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
) -> Dict:
    """Create new job"""
    db = DatabaseManager()
    
    try:
        job_id = db.add_job(
            company=company,
            job_title=job_title,
            job_description=job_description,
            job_url=job_url,
            location=location,
            salary_range=salary_range,
            employment_type=employment_type,
            notes=notes
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Job created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{job_id}")
async def update_job(
    job_id: int,
    notes: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    deadline_date: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
) -> Dict:
    """Update job details"""
    db = DatabaseManager()
    
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        with db.get_connection() as conn:
            updates = []
            params = []
            
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)
            
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            
            if deadline_date:
                updates.append("deadline_date = ?")
                params.append(deadline_date)
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(job_id)
                
                query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
                conn.execute(query, params)
        
        return {
            "success": True,
            "message": "Job updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{job_id}")
async def delete_job(job_id: int, user: dict = Depends(get_current_user)) -> Dict:
    """Delete job (cascades to variants)"""
    db = DatabaseManager()
    
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        with db.get_connection() as conn:
            conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        
        return {
            "success": True,
            "message": "Job deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}/variants")
async def get_job_variants(job_id: int, user: dict = Depends(get_current_user)) -> List[Dict]:
    """Get all variants for a job"""
    db = DatabaseManager()
    
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    variants = db.list_variants(job_id=job_id)
    
    # Enrich with ATS scores
    enriched = []
    with db.get_connection() as conn:
        for variant in variants:
            cursor = conn.execute("""
                SELECT overall_score, keyword_score 
                FROM ats_scores 
                WHERE variant_id = ?
                ORDER BY scored_at DESC LIMIT 1
            """, (variant['variant_id'],))
            
            score_row = cursor.fetchone()
            
            variant_data = dict(variant)
            if score_row:
                variant_data['ats_score'] = dict(score_row)['overall_score']
                variant_data['keyword_score'] = dict(score_row)['keyword_score']
            else:
                variant_data['ats_score'] = 0
                variant_data['keyword_score'] = 0
            
            enriched.append(variant_data)
    
    return enriched
