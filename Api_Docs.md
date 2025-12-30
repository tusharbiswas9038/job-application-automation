***

## **3. API_DOCS.md**

```bash
# 🔌 API Documentation

Complete REST API reference for the Job Application Automation System.

---

## 🔐 Authentication

All endpoints require authentication via session cookie.

### Login

**Endpoint:** `POST /login`

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Login successful"
}
```

**Cookie:** `session_token` (automatically set)

### Logout

**Endpoint:** `POST /logout`

**Response:**

```json
{
  "success": true
}
```


---

## 📋 Jobs API

### List All Jobs

**Endpoint:** `GET /api/jobs/`

**Query Parameters:**

- `status` (optional): Filter by status (active, applied, rejected)
- `limit` (optional): Number of results (default: 50)

**Response:**

```json
[
  {
    "job_id": 1,
    "company": "ALIQAN Technologies",
    "job_title": "Kafka Admin",
    "location": "Pune, Maharashtra, India",
    "posted_date": "2025-12-30",
    "status": "active",
    "source": "linkedin",
    "best_ats_score": 75.4,
    "variants_generated": 1,
    "created_at": "2025-12-30T19:20:37"
  }
]
```


### Get Job Details

**Endpoint:** `GET /api/jobs/{job_id}`

**Response:**

```json
{
  "job_id": 1,
  "company": "ALIQAN Technologies",
  "job_title": "Kafka Admin",
  "job_url": "https://linkedin.com/jobs/...",
  "job_description": "Full job description...",
  "location": "Pune, India",
  "salary_range": "₹15-20 LPA",
  "posted_date": "2025-12-30",
  "status": "active",
  "source": "linkedin",
  "best_ats_score": 75.4,
  "variants": [
    {
      "variant_id": "4e8cf285-...",
      "ats_score": 75.4,
      "generated_at": "2025-12-30T19:20:37",
      "pdf_path": "data/resumes/variants/..."
    }
  ]
}
```


### Add Job

**Endpoint:** `POST /api/jobs/`

**Request:**

```json
{
  "company": "Company Name",
  "job_title": "Job Title",
  "job_url": "https://...",
  "job_description": "Full JD text",
  "location": "City, Country",
  "posted_date": "2025-12-30",
  "source": "linkedin"
}
```

**Response:**

```json
{
  "success": true,
  "job_id": 18,
  "message": "Job added successfully"
}
```


### Update Job

**Endpoint:** `PUT /api/jobs/{job_id}`

**Request:**

```json
{
  "status": "applied",
  "notes": "Applied on 2025-12-31"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Job updated"
}
```


### Delete Job

**Endpoint:** `DELETE /api/jobs/{job_id}`

**Response:**

```json
{
  "success": true,
  "message": "Job deleted"
}
```


---

## 🔍 Scraper API

### Start Scraping

**Endpoint:** `POST /api/scraper/start`

**Request:**

```json
{
  "keywords": "Kafka Admin",
  "location": "India",
  "max_pages": 3,
  "source": "linkedin"
}
```

**Response:**

```json
{
  "success": true,
  "job_id": "scrape_20251231_010627",
  "message": "Scraping started"
}
```


### Get Scraping Status

**Endpoint:** `GET /api/scraper/status/{job_id}`

**Response:**

```json
{
  "job_id": "scrape_20251231_010627",
  "status": "running",
  "progress": 45,
  "total_jobs": 0,
  "new_jobs": 0,
  "duplicates": 0,
  "message": "Scraping page 2..."
}
```

**Status Values:**

- `running`: Currently scraping
- `completed`: Finished successfully
- `error`: Failed


### Preview Scraped Jobs

**Endpoint:** `GET /api/scraper/preview/{job_id}`

**Response:**

```json
[
  {
    "temp_id": "temp_0",
    "job_title": "Kafka Administrator",
    "company": "Tech Company",
    "location": "Bangalore, India",
    "job_url": "https://...",
    "posted_date": "2025-12-30",
    "description": "Job description...",
    "keywords": ["kafka", "python", "docker"],
    "is_duplicate": false
  }
]
```


### Import Scraped Jobs

**Endpoint:** `POST /api/scraper/import/{job_id}`

**Request (Import All):**

```json
{}
```

**Request (Import Specific):**

```json
{
  "job_ids": ["temp_0", "temp_2", "temp_5"]
}
```

**Response:**

```json
{
  "success": true,
  "imported": 8,
  "skipped": 2,
  "total": 10
}
```


### Get Scraping History

**Endpoint:** `GET /api/scraper/history`

**Query Parameters:**

- `limit` (optional): Number of results (default: 10)

**Response:**

```json
[
  {
    "job_id": "scrape_20251231_010627",
    "status": "completed",
    "keywords": "Kafka Admin",
    "location": "India",
    "total_jobs": 10,
    "new_jobs": 8,
    "duplicates": 2,
    "started_at": "2025-12-31T01:06:27",
    "completed_at": "2025-12-31T01:07:15"
  }
]
```


---

## 📝 Generation API

### Generate Resume Variant

**Endpoint:** `POST /api/generate/variant`

**Request:**

```json
{
  "job_id": 1,
  "target_bullets": 11,
  "ai_enhancement_enabled": true
}
```

**Response:**

```json
{
  "success": true,
  "variant_id": "4e8cf285-6062-4e35-92c1-dab747ec05d0",
  "pdf_path": "data/resumes/variants/resume_...",
  "ats_score": 75.4,
  "bullets_enhanced": 5,
  "message": "Variant generated successfully"
}
```


### Get Variant Details

**Endpoint:** `GET /api/variants/{variant_id}`

**Response:**

```json
{
  "variant_id": "4e8cf285-...",
  "job_id": 1,
  "job_title": "Kafka Admin",
  "company": "ALIQAN Technologies",
  "target_bullets": 11,
  "total_bullets": 11,
  "bullets_enhanced": 5,
  "ai_enhancement_enabled": true,
  "keywords_added": ["kafka", "docker", "kubernetes"],
  "pdf_path": "data/resumes/variants/...",
  "generated_at": "2025-12-30T19:20:37",
  "ats_score": {
    "overall_score": 75.4,
    "keyword_score": 79.7,
    "format_score": 100.0,
    "experience_score": 55.0,
    "missing_keywords": ["terraform", "ansible"],
    "recommendations": [
      "Add 'terraform' - appears 10 times in JD"
    ]
  }
}
```


### Download Variant PDF

**Endpoint:** `GET /api/variants/{variant_id}/download`

**Response:** PDF file download

### Delete Variant

**Endpoint:** `DELETE /api/variants/{variant_id}`

**Response:**

```json
{
  "success": true,
  "message": "Variant deleted"
}
```


### List Variants

**Endpoint:** `GET /api/variants/`

**Query Parameters:**

- `job_id` (optional): Filter by job
- `limit` (optional): Number of results

**Response:**

```json
[
  {
    "variant_id": "4e8cf285-...",
    "job_id": 1,
    "company": "ALIQAN Technologies",
    "job_title": "Kafka Admin",
    "ats_score": 75.4,
    "bullets_enhanced": 5,
    "generated_at": "2025-12-30T19:20:37"
  }
]
```


---

## 📊 Statistics API

### Get Overview Statistics

**Endpoint:** `GET /api/stats/overview`

**Response:**

```json
{
  "total_jobs": 17,
  "total_variants": 3,
  "total_applications": 0,
  "avg_ats_score": 62.7,
  "jobs_with_variants": 3,
  "jobs_applied": 0,
  "applications_by_status": {
    "applied": 0,
    "interview": 0,
    "offer": 0,
    "rejected": 0
  },
  "ats_distribution": {
    "excellent": 0,
    "good": 1,
    "fair": 0,
    "poor": 2
  },
  "recent_activity_count": 3
}
```


### Get Recent Activity

**Endpoint:** `GET /api/stats/recent-activity`

**Query Parameters:**

- `limit` (optional): Number of items (default: 10)

**Response:**

```json
[
  {
    "type": "variant_generated",
    "variant_id": "4e8cf285-...",
    "job_title": "Kafka Admin",
    "company": "ALIQAN Technologies",
    "timestamp": "2025-12-30T19:20:37",
    "bullets_enhanced": 5,
    "ai_enabled": true
  }
]
```


### Get ATS Trends

**Endpoint:** `GET /api/stats/ats-trends`

**Response:**

```json
{
  "labels": [
    "ALIQAN Technologies",
    "Uber",
    "Infosys"
  ],
  "scores": [75.4, 54.7, 0]
}
```


### Test Ollama Connection

**Endpoint:** `GET /api/stats/test-ollama`

**Response (Success):**

```json
{
  "connected": true,
  "models": ["llama3.2:latest", "codellama:latest"],
  "model_count": 2,
  "has_configured_model": true,
  "configured_model": "llama3.2",
  "message": "✓ Connected! Found 2 model(s)"
}
```

**Response (Error):**

```json
{
  "connected": false,
  "message": "✗ Connection failed",
  "error": "Connection refused"
}
```


---

## 🔧 Configuration API

### Get Settings

**Endpoint:** `GET /api/settings`

**Response:**

```json
{
  "ollama_host": "http://localhost:11434",
  "ollama_model": "llama3.2",
  "database_path": "data/resume_tracker.db",
  "base_resume_path": "data/resumes/my_resume.tex"
}
```


### Export Database

**Endpoint:** `GET /api/settings/export-db`

**Response:** SQLite database file download

---

## 🚨 Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid input data"
}
```


### 401 Unauthorized

```json
{
  "detail": "Unauthorized"
}
```


### 404 Not Found

```json
{
  "detail": "Job not found"
}
```


### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "job_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```


### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "error": "Detailed error message"
}
```


---

## 📡 WebSocket Endpoints

### Real-time Scraping Updates

**Endpoint:** `ws://localhost:8000/ws/scraper/{job_id}`

**Messages:**

```json
{
  "event": "progress",
  "data": {
    "progress": 45,
    "message": "Scraping page 2..."
  }
}
```


---

## 🧪 Testing

### cURL Examples

**Login:**

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  -c cookies.txt
```

**List Jobs:**

```bash
curl http://localhost:8000/api/jobs/ \
  -b cookies.txt
```

**Start Scraping:**

```bash
curl -X POST http://localhost:8000/api/scraper/start \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"keywords":"Python Developer","location":"Bangalore","max_pages":2}'
```

**Generate Variant:**

```bash
curl -X POST http://localhost:8000/api/generate/variant \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"job_id":1,"target_bullets":11,"ai_enhancement_enabled":true}'
```


### Python Examples

```python
import requests

# Login
session = requests.Session()
session.post('http://localhost:8000/login', json={
    'username': 'admin',
    'password': 'admin123'
})

# Get jobs
jobs = session.get('http://localhost:8000/api/jobs/').json()

# Start scraping
response = session.post('http://localhost:8000/api/scraper/start', json={
    'keywords': 'Kafka Admin',
    'location': 'India',
    'max_pages': 3
})
job_id = response.json()['job_id']

# Generate variant
variant = session.post('http://localhost:8000/api/generate/variant', json={
    'job_id': 1,
    'target_bullets': 11,
    'ai_enhancement_enabled': True
}).json()
```


---

## 📝 Rate Limits

No rate limits currently enforced. Use responsibly.

---

## 🔄 API Versioning

Current version: **v1**

Future versions will be accessible via: `/api/v2/...`

---

**Last Updated**: December 31, 2025

```

***