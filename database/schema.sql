-- database/schema.sql
-- SQLite schema for resume tailoring system

-- Job postings
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_url TEXT,
    job_description TEXT NOT NULL,
    jd_file_path TEXT,  -- Path to original JD file
    requirements_yaml TEXT,  -- Path to requirements file
    posted_date DATE,
    deadline_date DATE,
    location TEXT,
    salary_range TEXT,
    employment_type TEXT,
    status TEXT DEFAULT 'active',
    source TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company, job_title, posted_date)
);

-- Resume variants
CREATE TABLE IF NOT EXISTS variants (
    variant_id TEXT PRIMARY KEY,
    job_id INTEGER NOT NULL,
    base_resume_path TEXT NOT NULL,
    variant_latex_path TEXT NOT NULL,
    variant_pdf_path TEXT NOT NULL,
    metadata_json_path TEXT,
    
    -- Generation settings
    target_bullets INTEGER DEFAULT 18,
    ai_enhancement_enabled BOOLEAN DEFAULT 1,
    bullets_enhanced INTEGER DEFAULT 0,
    
    -- Content stats
    total_bullets INTEGER,
    keywords_added TEXT,  -- JSON array
    
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

-- ATS scores
CREATE TABLE IF NOT EXISTS ats_scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id TEXT NOT NULL,
    
    overall_score REAL,
    keyword_score REAL,
    format_score REAL,
    experience_score REAL,
    
    required_keywords_found INTEGER,
    required_keywords_total INTEGER,
    optional_keywords_found INTEGER,
    
    missing_keywords TEXT,  -- JSON array
    recommendations TEXT,  -- JSON array
    
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id) ON DELETE CASCADE
);

-- Job fit scores
CREATE TABLE IF NOT EXISTS job_fit_scores (
    fit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id TEXT NOT NULL,
    
    overall_fit REAL,
    required_skills_match REAL,
    preferred_skills_match REAL,
    experience_match REAL,
    
    matched_skills TEXT,
    missing_skills TEXT,
    
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id) ON DELETE CASCADE
);

-- Bullet changes
CREATE TABLE IF NOT EXISTS bullet_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id TEXT NOT NULL,
    
    change_type TEXT NOT NULL,
    position_original INTEGER,
    position_new INTEGER,
    
    original_text TEXT,
    new_text TEXT,
    
    keywords_added TEXT,
    similarity_score REAL,
    
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id) ON DELETE CASCADE
);

-- Applications
CREATE TABLE IF NOT EXISTS applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    variant_id TEXT,
    
    applied_date DATE NOT NULL,
    application_method TEXT,
    application_url TEXT,
    cover_letter_path TEXT,
    
    status TEXT DEFAULT 'applied',
    status_updated_at TIMESTAMP,
    
    followed_up BOOLEAN DEFAULT 0,
    follow_up_date DATE,
    
    interview_scheduled BOOLEAN DEFAULT 0,
    interview_date DATE,
    interview_type TEXT,
    
    offer_received BOOLEAN DEFAULT 0,
    offer_amount REAL,
    offer_date DATE,
    
    rejected_date DATE,
    rejection_reason TEXT,
    
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id) ON DELETE SET NULL
);

-- Activity log
CREATE TABLE IF NOT EXISTS activity_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_variants_job ON variants(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_ats_scores_variant ON ats_scores(variant_id);

-- Views
CREATE VIEW IF NOT EXISTS active_applications AS
SELECT 
    a.application_id,
    a.applied_date,
    a.status,
    j.company,
    j.job_title,
    j.location,
    v.variant_id,
    s.overall_score as ats_score,
    a.interview_scheduled,
    a.interview_date
FROM applications a
JOIN jobs j ON a.job_id = j.job_id
LEFT JOIN variants v ON a.variant_id = v.variant_id
LEFT JOIN ats_scores s ON v.variant_id = s.variant_id
WHERE a.status NOT IN ('rejected', 'withdrawn')
ORDER BY a.applied_date DESC;

CREATE VIEW IF NOT EXISTS job_pipeline AS
SELECT 
    j.job_id,
    j.company,
    j.job_title,
    j.location,
    j.status as job_status,
    COUNT(DISTINCT v.variant_id) as variants_generated,
    COUNT(DISTINCT a.application_id) as applications_count,
    MAX(s.overall_score) as best_ats_score,
    MAX(a.applied_date) as last_applied_date
FROM jobs j
LEFT JOIN variants v ON j.job_id = v.job_id
LEFT JOIN applications a ON j.job_id = a.job_id
LEFT JOIN ats_scores s ON v.variant_id = s.variant_id
GROUP BY j.job_id
ORDER BY j.created_at DESC;
