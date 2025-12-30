***

## **1. README.md - Main Project Documentation**

```bash
# 🎯 Job Application Automation System

A complete end-to-end platform for automating job search, resume customization, and application tracking with AI-powered optimization.

## 🌟 Features

### Core Capabilities
- **🔍 Automated Job Scraping**: LinkedIn job scraper with duplicate detection
- **📝 Smart Resume Tailoring**: Generate customized resume variants for each job
- **🤖 AI Enhancement**: Ollama-powered bullet point optimization
- **📊 ATS Scoring**: Automatic ATS compatibility scoring (0-100)
- **🎯 Keyword Matching**: Intelligent keyword extraction and matching
- **📈 Analytics Dashboard**: Track applications, scores, and success metrics
- **💼 Application Management**: Full pipeline tracking from discovery to offer

### Technical Features
- Full-stack web dashboard with authentication
- RESTful API for programmatic access
- SQLite database with relational schema
- LaTeX-based PDF generation
- Real-time scraping progress tracking
- Comprehensive recommendation engine

---

## 📦 Project Structure

```

/project_JobScraping/
├── dashboard/              \# Web UI and API
│   ├── api/               \# FastAPI endpoints
│   │   ├── jobs.py        \# Job management
│   │   ├── scraper.py     \# Scraping endpoints
│   │   ├── generate.py    \# Resume generation
│   │   ├── stats.py       \# Statistics \& analytics
│   │   └── variants.py    \# Variant management
│   ├── templates/         \# HTML templates
│   ├── static/            \# CSS/JS assets
│   ├── app.py             \# Main FastAPI app
│   ├── auth.py            \# Authentication
│   └── config.py          \# Configuration
│
├── scraper/               \# Job scraping module
│   ├── linkedin_scraper.py
│   ├── processor/
│   │   └── normalizer.py  \# Data normalization
│   └── config.py
│
├── resume/                \# Resume generation
│   ├── modules/
│   │   ├── latex_parser.py      \# LaTeX parsing
│   │   ├── scorer.py            \# ATS scoring
│   │   ├── variant_generator.py \# Resume tailoring
│   │   └── bullet_enhancer.py   \# AI enhancement
│   └── templates/
│
├── database/              \# Database management
│   ├── db_manager.py      \# Database operations
│   └── schema.sql         \# Database schema
│
├── data/                  \# Data storage
│   ├── resume_tracker.db  \# SQLite database
│   ├── resumes/           \# Generated PDFs
│   ├── job_descriptions/  \# Saved JDs
│   └── logs/              \# System logs
│
└── config/                \# Configuration files

```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- LaTeX distribution (texlive-full)
- Ollama (for AI features)
- Git

### Installation

1. **Clone or access the project**
```bash
cd /project_JobScraping
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install LaTeX**
```bash
apt-get update
apt-get install -y texlive-full
```

4. **Setup Ollama (optional for AI)**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

5. **Initialize database**
```bash
python -c "from database.db_manager import DatabaseManager; DatabaseManager()"
```


### Running the System

**Start the dashboard:**

```bash
cd /project_JobScraping
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000
```

**Or use the startup script:**

```bash
./start.sh
```

**Access the dashboard:**

```
URL: http://your-ip:8000
Username: admin
Password: admin123
```


---

## 📖 Usage Guide

### 1. Scraping Jobs

**Via Web Dashboard:**

1. Go to "🔍 Scrape Jobs" → "Settings"
2. Enter keywords (e.g., "Kafka Admin")
3. Set location (e.g., "India")
4. Choose number of pages (1-5)
5. Click "Start Scraping"
6. Preview results
7. Import all or select specific jobs

**Via API:**

```bash
curl -X POST http://localhost:8000/api/scraper/start \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "Kafka Admin",
    "location": "India",
    "max_pages": 3,
    "source": "linkedin"
  }'
```


### 2. Generating Resume Variants

**Via Web Dashboard:**

1. Go to "Jobs" page
2. Click on a job
3. Click "Generate Variant"
4. Customize settings:
    - Target bullets: 11-18
    - AI enhancement: ON/OFF
5. Click "Generate"
6. Download PDF

**Via API:**

```bash
curl -X POST http://localhost:8000/api/generate/variant \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "target_bullets": 11,
    "ai_enhancement_enabled": true
  }'
```


### 3. Viewing Statistics

**Dashboard Metrics:**

- Total jobs tracked
- Resume variants generated
- Average ATS score
- Applications submitted
- Recent activity feed

**ATS Score Breakdown:**

- Overall score (0-100)
- Keyword match score
- Format compatibility
- Experience match
- Recommendations


### 4. Managing Jobs

**Edit Job:**

- Update job details
- Modify requirements
- Add notes
- Change status

**Delete Job:**

- Remove from tracking
- Cascade deletes variants

**Track Applications:**

- Update application status
- Add interview notes
- Track offers

---

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# Dashboard
DASHBOARD_SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Database
DATABASE_PATH=data/resume_tracker.db

# Resume
BASE_RESUME_PATH=data/resumes/my_resume.tex
```


### Ollama Configuration

```bash
# Start Ollama service
systemctl start ollama

# Pull models
ollama pull llama3.2

# Test connection
curl http://localhost:11434/api/tags
```


### Database Configuration

```python
# In dashboard/config.py
class Settings:
    database_url: str = "sqlite:///data/resume_tracker.db"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
```


---

## 📊 Database Schema

### Core Tables

**jobs**: Job postings

- job_id, company, job_title, job_url
- job_description, location, posted_date
- status, source, best_ats_score

**variants**: Resume variants

- variant_id, job_id, pdf_path
- target_bullets, ai_enhancement_enabled
- bullets_enhanced, keywords_added

**ats_scores**: ATS scoring results

- score_id, variant_id
- overall_score, keyword_score, format_score
- missing_keywords, recommendations

**applications**: Application tracking

- application_id, job_id, variant_id
- status, applied_date, interview_date

---

## 🔌 API Reference

### Authentication

All API endpoints require authentication cookie.

**Login:**

```bash
POST /login
Body: {"username": "admin", "password": "admin123"}
```


### Job Endpoints

**List Jobs:**

```bash
GET /api/jobs/
```

**Get Job Details:**

```bash
GET /api/jobs/{job_id}
```

**Add Job:**

```bash
POST /api/jobs/
Body: {job data}
```

**Update Job:**

```bash
PUT /api/jobs/{job_id}
Body: {updated data}
```

**Delete Job:**

```bash
DELETE /api/jobs/{job_id}
```


### Scraper Endpoints

**Start Scraping:**

```bash
POST /api/scraper/start
Body: {"keywords": "...", "location": "...", "max_pages": 3}
```

**Get Status:**

```bash
GET /api/scraper/status/{job_id}
```

**Preview Results:**

```bash
GET /api/scraper/preview/{job_id}
```

**Import Jobs:**

```bash
POST /api/scraper/import/{job_id}
Body: {"job_ids": ["temp_0", "temp_1"]} # optional
```


### Generation Endpoints

**Generate Variant:**

```bash
POST /api/generate/variant
Body: {
  "job_id": 1,
  "target_bullets": 11,
  "ai_enhancement_enabled": true
}
```

**Get Variant:**

```bash
GET /api/variants/{variant_id}
```

**Download PDF:**

```bash
GET /api/variants/{variant_id}/download
```


### Statistics Endpoints

**Overview Stats:**

```bash
GET /api/stats/overview
```

**Recent Activity:**

```bash
GET /api/stats/recent-activity?limit=10
```

**ATS Trends:**

```bash
GET /api/stats/ats-trends
```


---

## 🛠️ Maintenance

### Backup Database

```bash
./backup.sh
```

Or manually:

```bash
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
cp data/resume_tracker.db backups/resume_tracker_$DATE.db
```


### View Logs

```bash
tail -f dashboard.log
tail -f data/logs/scraper.log
```


### Clear Cache

```bash
rm -rf data/cache/*
```


### Reset Database

```bash
rm data/resume_tracker.db
python -c "from database.db_manager import DatabaseManager; DatabaseManager()"
```


---

## 🐛 Troubleshooting

### Dashboard Won't Start

```bash
# Check port availability
lsof -i :8000

# Kill existing process
pkill -f "uvicorn dashboard.app:app"

# Restart
./start.sh
```


### Ollama Not Connecting

```bash
# Check Ollama status
systemctl status ollama

# Restart Ollama
systemctl restart ollama

# Test connection
curl http://localhost:11434/api/tags
```


### PDF Generation Fails

```bash
# Install LaTeX
apt-get install -y texlive-full

# Check pdflatex
which pdflatex

# Test compilation
cd data/resumes/variants
pdflatex resume_test.tex
```


### Scraper Not Working

```bash
# Check network
ping linkedin.com

# Update scraper config
nano scraper/config.py

# Check logs
tail -f data/logs/scraper.log
```


---

## 📈 Current Statistics

- **Total Jobs Tracked**: 17
- **Resume Variants**: 3
- **Average ATS Score**: 62.7
- **Best Score**: 75.4 (ALIQAN Technologies)
- **AI-Enhanced Bullets**: 15

---

## 🤝 Contributing

This is a personal project. For improvements:

1. Test thoroughly
2. Document changes
3. Update this README

---

## 📝 License

Personal use project. All rights reserved.

---

## 🙏 Acknowledgments

- **FastAPI**: Web framework
- **Ollama**: AI model serving
- **LaTeX**: PDF generation
- **SQLite**: Database

---

## 📞 Support

For issues or questions:

- Check logs: `dashboard.log`
- Review configuration: `dashboard/config.py`
- Test individual modules in `tests/`

---

**Last Updated**: December 31, 2025
**Version**: 1.0.0
**Status**: ✅ Production Ready

```

***