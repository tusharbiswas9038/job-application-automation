# dashboard/api/variants.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import DatabaseManager
from dashboard.auth import get_current_user

router = APIRouter()

@router.get("/")
async def list_variants(
    job_id: Optional[int] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
) -> List[Dict]:
    """List variants"""
    db = DatabaseManager()
    
    try:
        variants = db.list_variants(job_id=job_id)[:limit]
        
        # Enrich with scores and job info
        enriched = []
        for variant in variants:
            job = db.get_job(variant['job_id'])
            
            # Get ATS score
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT overall_score, keyword_score, format_score, experience_score
                    FROM ats_scores 
                    WHERE variant_id = ?
                    ORDER BY scored_at DESC LIMIT 1
                """, (variant['variant_id'],))
                
                score_row = cursor.fetchone()
            
            variant_data = dict(variant)
            variant_data['job'] = dict(job) if job else None
            
            if score_row:
                variant_data['scores'] = dict(score_row)
            else:
                variant_data['scores'] = None
            
            enriched.append(variant_data)
        
        return enriched
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{variant_id}")
async def get_variant(variant_id: str, user: dict = Depends(get_current_user)) -> Dict:
    """Get variant details"""
    db = DatabaseManager()
    
    variant = db.get_variant(variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    # Get job
    job = db.get_job(variant['job_id'])
    
    # Get ATS score
    with db.get_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM ats_scores 
            WHERE variant_id = ?
            ORDER BY scored_at DESC LIMIT 1
        """, (variant_id,))
        
        score_row = cursor.fetchone()
    
    variant_data = dict(variant)
    variant_data['job'] = dict(job) if job else None
    variant_data['scores'] = dict(score_row) if score_row else None
    
    # Load metadata if exists
    import json
    metadata_path = Path(variant.get('metadata_json_path', ''))
    if metadata_path.exists():
        with open(metadata_path) as f:
            variant_data['metadata'] = json.load(f)
    
    return variant_data

@router.delete("/{variant_id}")
async def delete_variant(variant_id: str, user: dict = Depends(get_current_user)) -> Dict:
    """Delete variant and associated files"""
    db = DatabaseManager()
    
    variant = db.get_variant(variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    try:
        # Delete files
        import os
        files_to_delete = [
            variant.get('variant_latex_path'),
            variant.get('variant_pdf_path'),
            variant.get('metadata_json_path')
        ]
        
        for file_path in files_to_delete:
            if file_path and Path(file_path).exists():
                os.remove(file_path)
        
        # Delete from database
        with db.get_connection() as conn:
            conn.execute("DELETE FROM variants WHERE variant_id = ?", (variant_id,))
        
        return {
            "success": True,
            "message": "Variant deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{variant_id}/download")
async def download_pdf(
    variant_id: str,
    user: dict = Depends(get_current_user)
):
    """Download PDF variant"""
    from fastapi.responses import FileResponse
    import os

    db = DatabaseManager()
    variant = db.get_variant(variant_id)

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    pdf_path = variant.get('variant_pdf_path')

    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=pdf_path,
        filename=f"resume_{variant_id[:8]}.pdf",
        media_type="application/pdf"
    )

@router.get("/{variant_id}/download-tex")
async def download_tex(
    variant_id: str,
    user: dict = Depends(get_current_user)
):
    """Download LaTeX source"""
    from fastapi.responses import FileResponse
    import os

    db = DatabaseManager()
    variant = db.get_variant(variant_id)

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    tex_path = variant.get('variant_latex_path')

    if not tex_path or not os.path.exists(tex_path):
        raise HTTPException(status_code=404, detail="LaTeX file not found")

    return FileResponse(
        path=tex_path,
        filename=f"resume_{variant_id[:8]}.tex",
        media_type="application/x-tex"
    )

