# dashboard/api/files.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from typing import List
import sys
from pathlib import Path
import json
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.auth import get_current_user
from dashboard.config import settings

router = APIRouter()

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@router.get("/resumes")
async def list_resumes(user: dict = Depends(get_current_user)) -> List[dict]:
    """List all resume files"""
    resumes_dir = Path(settings.resumes_dir)
    
    files = []
    for file_path in resumes_dir.glob("*.tex"):
        stat = file_path.stat()
        files.append({
            "name": file_path.name,
            "path": str(file_path),
            "size": stat.st_size,
            "modified": stat.st_mtime
        })
    
    return files

@router.get("/variants")
async def list_variant_files(user: dict = Depends(get_current_user)) -> List[dict]:
    """List all variant files"""
    variants_dir = Path(settings.variants_dir)
    
    files = []
    for file_path in variants_dir.glob("*.pdf"):
        stat = file_path.stat()
        
        # Get corresponding metadata
        metadata_path = file_path.with_name(f"{file_path.stem}_metadata.json")
        metadata = None
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
        
        files.append({
            "name": file_path.name,
            "path": str(file_path),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "has_metadata": metadata_path.exists(),
            "metadata": metadata
        })
    
    return sorted(files, key=lambda x: x['modified'], reverse=True)

@router.get("/download/{file_type}/{filename}")
async def download_file(
    file_type: str,
    filename: str,
    user: dict = Depends(get_current_user)
):
    """Download a file"""
    
    if file_type == "resume":
        file_path = Path(settings.resumes_dir) / filename
    elif file_type == "variant":
        file_path = Path(settings.variants_dir) / filename
    elif file_type == "jd":
        file_path = Path(settings.job_descriptions_dir) / filename
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

@router.post("/upload/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
) -> dict:
    """Upload a resume file"""
    
    if not file.filename.endswith('.tex'):
        raise HTTPException(status_code=400, detail="Only .tex files allowed")
    
    file_path = Path(settings.resumes_dir) / file.filename
    
    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)
    
    return {
        "success": True,
        "filename": file.filename,
        "path": str(file_path),
        "message": "Resume uploaded successfully"
    }

@router.delete("/variants/{filename}")
async def delete_variant_file(
    filename: str,
    user: dict = Depends(get_current_user)
) -> dict:
    """Delete a variant file"""
    
    variants_dir = Path(settings.variants_dir)
    
    # Delete PDF
    pdf_path = variants_dir / filename
    if pdf_path.exists():
        pdf_path.unlink()
    
    # Delete TEX
    tex_path = pdf_path.with_suffix('.tex')
    if tex_path.exists():
        tex_path.unlink()
    
    # Delete metadata
    metadata_path = variants_dir / f"{pdf_path.stem}_metadata.json"
    if metadata_path.exists():
        metadata_path.unlink()
    
    return {
        "success": True,
        "message": "Files deleted successfully"
    }

@router.get("/export/database")
async def export_database(user: dict = Depends(get_current_user)):
    """Export database as JSON"""
    from database.db_manager import DatabaseManager
    
    db = DatabaseManager()
    
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "statistics": db.get_statistics(),
        "jobs": [dict(job) for job in db.list_jobs(limit=1000)],
        "variants": db.list_variants(),
        "pipeline": [dict(p) for p in db.get_job_pipeline()],
        "active_applications": [dict(a) for a in db.get_active_applications()]
    }
    
    # Save to file
    export_filename = f"resume_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    export_path = Path("data") / export_filename
    
    with open(export_path, 'w') as f:
        json.dump(export_data, f, indent=2, default=json_serial)
    
    return FileResponse(
        path=export_path,
        filename=export_filename,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={export_filename}"
        }
    )
