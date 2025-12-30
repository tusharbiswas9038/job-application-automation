# dashboard/api/stats.py

from fastapi import APIRouter, Depends
from typing import Dict, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import DatabaseManager
from dashboard.auth import get_current_user

router = APIRouter()

@router.get("/overview")
async def get_overview_stats(user: dict = Depends(get_current_user)) -> Dict:
    """Get overview statistics"""
    db = DatabaseManager()

    try:
        stats = db.get_statistics()
        pipeline = db.get_job_pipeline()

        # Calculate additional metrics
        jobs_with_variants = sum(1 for job in pipeline if job.get('variants_generated', 0) > 0)
        jobs_applied = sum(1 for job in pipeline if job.get('applications_count', 0) > 0)

        # ATS score distribution
        ats_distribution = {
            "excellent": 0,  # 80+
            "good": 0,       # 70-79
            "fair": 0,       # 60-69
            "poor": 0        # <60
        }

        for job in pipeline:
            score = job.get('best_ats_score')
            # Safely handle None values
            if score is not None:
                score = float(score)
                if score >= 80:
                    ats_distribution["excellent"] += 1
                elif score >= 70:
                    ats_distribution["good"] += 1
                elif score >= 60:
                    ats_distribution["fair"] += 1
                elif score > 0:
                    ats_distribution["poor"] += 1

        return {
            "total_jobs": stats.get('total_jobs', 0),
            "total_variants": stats.get('total_variants', 0),
            "total_applications": stats.get('total_applications', 0),
            "avg_ats_score": stats.get('avg_ats_score', 0.0),
            "jobs_with_variants": jobs_with_variants,
            "jobs_applied": jobs_applied,
            "applications_by_status": stats.get('applications_by_status', {}),
            "ats_distribution": ats_distribution,
            "recent_activity_count": min(stats.get('total_variants', 0), 10)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "total_jobs": 0,
            "total_variants": 0,
            "total_applications": 0,
            "avg_ats_score": 0.0
        }

@router.get("/recent-activity")
async def get_recent_activity(limit: int = 10, user: dict = Depends(get_current_user)) -> List[Dict]:
    """Get recent activity"""
    db = DatabaseManager()

    try:
        variants = db.list_variants()[:limit]

        activity = []
        for variant in variants:
            # Get job details
            job = db.get_job(variant['job_id'])

            activity.append({
                "type": "variant_generated",
                "variant_id": variant['variant_id'],
                "job_title": job['job_title'] if job else "Unknown",
                "company": job['company'] if job else "Unknown",
                "timestamp": variant['generated_at'],
                "bullets_enhanced": variant.get('bullets_enhanced', 0),
                "ai_enabled": variant.get('ai_enhancement_enabled', False)
            })

        return activity
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []

@router.get("/ats-trends")
async def get_ats_trends(user: dict = Depends(get_current_user)) -> Dict:
    """Get ATS score trends"""
    db = DatabaseManager()

    try:
        pipeline = db.get_job_pipeline()

        trends = {
            "labels": [],
            "scores": []
        }

        for job in pipeline[:10]:  # Last 10 jobs
            score = job.get('best_ats_score')
            if score is not None and float(score) > 0:
                trends["labels"].append(f"{job['company'][:15]}...")
                trends["scores"].append(round(float(score), 1))

        return trends
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"labels": [], "scores": []}

@router.get("/test-ollama")
async def test_ollama(user: dict = Depends(get_current_user)) -> Dict:
    """Test Ollama connection from server side"""
    import httpx
    from dashboard.config import settings

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_host}/api/tags")

            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])

                # Check if our model exists
                model_names = [m['name'] for m in models]
                has_our_model = any(settings.ollama_model in name for name in model_names)

                return {
                    "connected": True,
                    "models": model_names,
                    "model_count": len(models),
                    "has_configured_model": has_our_model,
                    "configured_model": settings.ollama_model,
                    "message": f"✓ Connected! Found {len(models)} model(s)"
                }
            else:
                return {
                    "connected": False,
                    "message": f"✗ HTTP {response.status_code}",
                    "error": response.text
                }
    except Exception as e:
        return {
            "connected": False,
            "message": f"✗ Connection failed",
            "error": str(e)
        }
