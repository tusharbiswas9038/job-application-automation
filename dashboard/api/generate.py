# dashboard/api/generate.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.auth import get_current_user
from dashboard.config import settings
from database.db_manager import DatabaseManager

router = APIRouter()

# Store generation progress
generation_status = {}

async def generate_variant_task(
    task_id: str,
    resume_path: str,
    jd_text: str,
    jd_file_path: str,
    job_title: str,
    company: str,
    target_bullets: int,
    use_ai: bool
):
    """Background task to generate variant"""
    try:
        generation_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "Starting generation...",
            "started_at": datetime.now().isoformat()
        }
        
        # Import here to avoid circular dependencies
        from resume.tailoring.variant_generator import VariantGenerator
        from resume.tailoring.models import VariantGenerationConfig
        
        # Update progress
        generation_status[task_id].update({
            "progress": 10,
            "message": "Parsing resume..."
        })
        
        # Configure generation
        config = VariantGenerationConfig(
            target_bullets=target_bullets,
            use_ai_enhancement=use_ai
        )
        
        generation_status[task_id].update({
            "progress": 20,
            "message": "Extracting keywords..."
        })
        
        # Generate variant
        generator = VariantGenerator(config=config)
        
        generation_status[task_id].update({
            "progress": 40,
            "message": "Selecting bullets..."
        })
        
        variant = generator.generate_variant(
            resume_path=resume_path,
            jd_text=jd_text,
            job_title=job_title,
            company=company,
            output_dir=settings.variants_dir
        )
        
        generation_status[task_id].update({
            "progress": 80,
            "message": "Saving to database..."
        })
        
        # Save to database with proper jd_file_path
        import sqlite3
        conn = sqlite3.connect('data/resume_tracker.db', timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if job exists
        cursor.execute("""
            SELECT job_id FROM jobs 
            WHERE company = ? AND job_title = ?
            ORDER BY created_at DESC LIMIT 1
        """, (company, job_title))
        
        row = cursor.fetchone()
        if row:
            job_id = row[0]
        else:
            # Insert job with proper jd_file_path
            cursor.execute("""
                INSERT INTO jobs (
                    company, job_title, job_description, jd_file_path
                ) VALUES (?, ?, ?, ?)
            """, (company, job_title, jd_text, jd_file_path))
            job_id = cursor.lastrowid
        
        # Get metadata path
        latex_filename = Path(variant.latex_path).stem
        metadata_path = Path(variant.latex_path).parent / f"{latex_filename}_metadata.json"
        
        # Insert variant
        cursor.execute("""
            INSERT INTO variants (
                variant_id, job_id, base_resume_path,
                variant_latex_path, variant_pdf_path, metadata_json_path,
                target_bullets, ai_enhancement_enabled,
                bullets_enhanced, total_bullets, keywords_added
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            variant.variant_id, job_id,
            resume_path,
            variant.latex_path,
            variant.pdf_path if variant.pdf_path else '',
            str(metadata_path),
            variant.content.total_bullets if variant.content else 0,
            True,
            variant.bullets_enhanced,
            variant.content.total_bullets if variant.content else 0,
            json.dumps(variant.keywords_added)
        ))
        
        # Insert ATS score
        if variant.ats_score:
            from resume.ats.models import KeywordCategory
            
            try:
                required_found = len([m for m in variant.ats_score.matched_keywords
                                     if m.keyword.category.value == 'required'])
                required_total = required_found + len([k for k in variant.ats_score.missing_keywords
                                                      if k.category.value == 'required'])
                optional_found = variant.ats_score.matched_count - required_found
                
                cursor.execute("""
                    INSERT INTO ats_scores (
                        variant_id, overall_score, keyword_score,
                        format_score, experience_score,
                        required_keywords_found, required_keywords_total,
                        optional_keywords_found, missing_keywords, recommendations
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    variant.variant_id,
                    variant.ats_score.overall_score,
                    variant.ats_score.keyword_score,
                    variant.ats_score.format_score,
                    variant.ats_score.experience_score,
                    required_found,
                    required_total if required_total > 0 else None,
                    optional_found,
                    json.dumps([k.text for k in variant.ats_score.missing_keywords][:10]),
                    json.dumps(variant.ats_score.critical_gaps[:5] + variant.ats_score.improvements[:5])
                ))
            except Exception as e:
                # Save basic scores only
                cursor.execute("""
                    INSERT INTO ats_scores (variant_id, overall_score, keyword_score)
                    VALUES (?, ?, ?)
                """, (variant.variant_id, variant.ats_score.overall_score, variant.ats_score.keyword_score))
        
        conn.commit()
        conn.close()
        
        # Complete
        generation_status[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Generation completed successfully!",
            "variant_id": variant.variant_id,
            "ats_score": variant.ats_score.overall_score if variant.ats_score else 0,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        generation_status[task_id].update({
            "status": "failed",
            "progress": 0,
            "message": f"Error: {str(e)}",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "failed_at": datetime.now().isoformat()
        })

@router.post("/start")
async def start_generation(
    background_tasks: BackgroundTasks,
    job_title: str = Form(...),
    company: str = Form(...),
    job_description: str = Form(...),
    target_bullets: int = Form(18),
    use_ai: bool = Form(True),
    resume_file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user)
) -> dict:
    """Start variant generation"""
    
    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())[:8]
    
    # Determine resume path
    if resume_file:
        # Save uploaded resume
        resume_path = Path(settings.resumes_dir) / resume_file.filename
        with open(resume_path, 'wb') as f:
            content = await resume_file.read()
            f.write(content)
    else:
        # Use default resume
        resume_path = Path(settings.resumes_dir) / "my_resume.tex"
        if not resume_path.exists():
            raise HTTPException(status_code=400, detail="No resume found. Please upload one.")
    
    # Save job description to file
    jd_filename = f"{company.lower().replace(' ', '_')}_{job_title.lower().replace(' ', '_')}_{task_id}.txt"
    jd_path = Path(settings.job_descriptions_dir) / jd_filename
    jd_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jd_path, 'w') as f:
        f.write(job_description)
    
    # Start background task
    background_tasks.add_task(
        generate_variant_task,
        task_id=task_id,
        resume_path=str(resume_path),
        jd_text=job_description,
        jd_file_path=str(jd_path),
        job_title=job_title,
        company=company,
        target_bullets=target_bullets,
        use_ai=use_ai
    )
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "Generation started"
    }

@router.get("/status/{task_id}")
async def get_generation_status(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Get generation status"""
    if task_id not in generation_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return generation_status[task_id]

@router.get("/stream/{task_id}")
async def stream_generation_progress(task_id: str, user: dict = Depends(get_current_user)):
    """Stream generation progress (SSE)"""
    
    async def event_generator():
        while True:
            if task_id in generation_status:
                status = generation_status[task_id]
                yield f"data: {json.dumps(status)}\n\n"
                
                if status['status'] in ['completed', 'failed']:
                    break
            
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
