# database/db_manager.py

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage SQLite database for resume tailoring system"""
    
    def __init__(self, db_path: str = "data/resume_tracker.db"):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Read schema
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        # Execute schema
        with self.get_connection() as conn:
            conn.executescript(schema)
            
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
        
        logger.info(f"Database initialized: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    # ========== Jobs ==========
    
    def add_job(self, company: str, job_title: str, job_description: str, **kwargs) -> int:
        """Add a new job posting"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO jobs (
                    company, job_title, job_description, jd_file_path,
                    job_url, requirements_yaml, posted_date, deadline_date,
                    location, salary_range, employment_type, source, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company, job_title, job_description,
                kwargs.get('jd_file_path'),
                kwargs.get('job_url'),
                kwargs.get('requirements_yaml'),
                kwargs.get('posted_date'),
                kwargs.get('deadline_date'),
                kwargs.get('location'),
                kwargs.get('salary_range'),
                kwargs.get('employment_type'),
                kwargs.get('source'),
                kwargs.get('notes')
            ))
            
            job_id = cursor.lastrowid
            logger.info(f"Added job: {company} - {job_title} (ID: {job_id})")
            return job_id
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get job by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_job_by_details(self, company: str, job_title: str) -> Optional[Dict]:
        """Get job by company and title"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM jobs 
                WHERE company = ? AND job_title = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (company, job_title))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_jobs(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """List jobs with optional filtering"""
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== Variants ==========
    
    def add_variant(self, variant_id: str, job_id: int, base_resume_path: str, 
                    variant_latex_path: str, variant_pdf_path: str, **kwargs) -> str:
        """Add a resume variant"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO variants (
                    variant_id, job_id, base_resume_path,
                    variant_latex_path, variant_pdf_path, metadata_json_path,
                    target_bullets, ai_enhancement_enabled,
                    bullets_enhanced, total_bullets, keywords_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                variant_id, job_id, base_resume_path,
                variant_latex_path, variant_pdf_path,
                kwargs.get('metadata_json_path'),
                kwargs.get('target_bullets', 18),
                kwargs.get('ai_enhancement_enabled', True),
                kwargs.get('bullets_enhanced', 0),
                kwargs.get('total_bullets'),
                json.dumps(kwargs.get('keywords_added', []))
            ))
            
            logger.info(f"Added variant: {variant_id} for job {job_id}")
            return variant_id
    
    def get_variant(self, variant_id: str) -> Optional[Dict]:
        """Get variant by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM variants WHERE variant_id = ?", (variant_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['keywords_added'] = json.loads(result['keywords_added'])
                return result
            return None
    
    def list_variants(self, job_id: Optional[int] = None) -> List[Dict]:
        """List variants, optionally filtered by job"""
        with self.get_connection() as conn:
            if job_id:
                cursor = conn.execute("""
                    SELECT * FROM variants 
                    WHERE job_id = ?
                    ORDER BY generated_at DESC
                """, (job_id,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM variants 
                    ORDER BY generated_at DESC
                    LIMIT 50
                """)
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['keywords_added'] = json.loads(result['keywords_added'])
                results.append(result)
            return results
    
    # ========== ATS Scores ==========
    
    def add_ats_score(self, variant_id: str, overall_score: float, keyword_score: float, **kwargs):
        """Add ATS score for a variant"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO ats_scores (
                    variant_id, overall_score, keyword_score,
                    format_score, experience_score,
                    required_keywords_found, required_keywords_total,
                    optional_keywords_found, missing_keywords, recommendations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                variant_id, overall_score, keyword_score,
                kwargs.get('format_score'),
                kwargs.get('experience_score'),
                kwargs.get('required_keywords_found'),
                kwargs.get('required_keywords_total'),
                kwargs.get('optional_keywords_found'),
                json.dumps(kwargs.get('missing_keywords', [])),
                json.dumps(kwargs.get('recommendations', []))
            ))
            
            logger.info(f"Added ATS score for variant {variant_id}: {overall_score:.1f}")
    
    # ========== Applications ==========
    
    def add_application(self, job_id: int, applied_date: date, variant_id: Optional[str] = None, **kwargs) -> int:
        """Add a job application"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO applications (
                    job_id, variant_id, applied_date,
                    application_method, application_url,
                    cover_letter_path, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, variant_id, applied_date,
                kwargs.get('application_method'),
                kwargs.get('application_url'),
                kwargs.get('cover_letter_path'),
                kwargs.get('status', 'applied'),
                kwargs.get('notes')
            ))
            
            application_id = cursor.lastrowid
            logger.info(f"Added application {application_id} for job {job_id}")
            return application_id
    
    def update_application_status(self, application_id: int, status: str, notes: Optional[str] = None):
        """Update application status"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE applications 
                SET status = ?, status_updated_at = ?, notes = COALESCE(?, notes), updated_at = ?
                WHERE application_id = ?
            """, (status, datetime.now(), notes, datetime.now(), application_id))
            
            logger.info(f"Updated application {application_id} status to: {status}")
    
    # ========== Views/Reports ==========
    
    def get_active_applications(self) -> List[Dict]:
        """Get all active applications"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM active_applications")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_job_pipeline(self) -> List[Dict]:
        """Get job pipeline summary"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM job_pipeline")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        with self.get_connection() as conn:
            stats = {}
            
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
            stats['total_jobs'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM variants")
            stats['total_variants'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM applications")
            stats['total_applications'] = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM applications 
                GROUP BY status
            """)
            stats['applications_by_status'] = {
                row['status']: row['count'] 
                for row in cursor.fetchall()
            }
            
            cursor = conn.execute("SELECT AVG(overall_score) FROM ats_scores")
            avg = cursor.fetchone()[0]
            stats['avg_ats_score'] = round(avg, 2) if avg else 0
            
            return stats

    def get_job_by_url(self, job_url: str) -> Optional[Dict]:
        """Check if job exists by URL"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE job_url = ?",
                (job_url,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
