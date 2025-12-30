***

## **2. QUICKSTART.md**

```bash
# 🚀 Quick Start Guide

Get up and running in 5 minutes!

---

## ⚡ Super Fast Setup

### Step 1: Start the System (30 seconds)

```bash
cd /project_JobScraping
./start.sh
```

If `start.sh` doesn't exist:

```bash
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 &
```


### Step 2: Access Dashboard (10 seconds)

Open browser:

```
http://YOUR_IP:8000
```

Login:

- Username: `admin`
- Password: `admin123`


### Step 3: Scrape Your First Job (2 minutes)

1. Click **"🔍 Scrape Jobs"** → **"Settings"**
2. Enter:
    - Keywords: `Kafka Admin`
    - Location: `India`
    - Pages: `1`
3. Click **"Start Scraping"**
4. Wait for results (30-60 seconds)
5. Click **"Import All New Jobs"**

✅ Jobs imported!

### Step 4: Generate Your First Resume (1 minute)

1. Click **"Jobs"**
2. Click on any job
3. Click **"Generate Variant"**
4. Click **"Generate"**
5. Wait 20-30 seconds
6. Click **"Download PDF"**

✅ Custom resume ready!

---

## 🎯 Common Tasks

### Daily Job Search

```bash
# Morning routine
1. Open dashboard
2. Scrape Jobs → Search for "Your Role"
3. Import new jobs
4. Generate variants for top 3
5. Download PDFs
6. Apply!
```


### Check Your Stats

```bash
Dashboard → See:
- Total jobs tracked
- Variants generated
- Average ATS score
- Recent activity
```


### Improve Low Scores

```bash
1. Jobs → Click job with low score
2. View "Recommendations"
3. Generate Variant → Add suggested keywords
4. Compare scores
```


---

## 🔧 Quick Commands

### Start/Stop

```bash
# Start
cd /project_JobScraping
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 &

# Stop
pkill -f "uvicorn dashboard.app:app"

# Restart
pkill -f "uvicorn dashboard.app:app" && sleep 2 && \
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 &
```


### Backup

```bash
cp data/resume_tracker.db backups/backup_$(date +%Y%m%d).db
```


### Check Status

```bash
# Is it running?
ps aux | grep uvicorn

# Check logs
tail -20 dashboard.log

# Database stats
sqlite3 data/resume_tracker.db "SELECT COUNT(*) FROM jobs;"
```


---

## 💡 Pro Tips

### Tip 1: Bulk Scraping

Set max_pages to 3-5 for comprehensive results

### Tip 2: AI Enhancement

Always enable AI for better bullet points

### Tip 3: Target Bullets

- Senior roles: 15-18 bullets
- Mid-level: 11-14 bullets
- Junior: 8-11 bullets


### Tip 4: Keyword Optimization

Check "missing_keywords" in ATS results and add them

### Tip 5: Daily Automation

Add cron job for automatic scraping:

```bash
0 9 * * * cd /project_JobScraping && curl -X POST http://localhost:8000/api/scraper/start -H "Content-Type: application/json" -d '{"keywords":"Your Role","location":"Your City","max_pages":2}'
```


---

## 🐛 Quick Fixes

### Dashboard won't open?

```bash
# Kill and restart
pkill -f uvicorn && sleep 2
cd /project_JobScraping
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 &
```


### Can't generate PDF?

```bash
# Install LaTeX
apt-get update && apt-get install -y texlive-full
```


### Ollama not working?

```bash
# Disable AI enhancement temporarily
# Generate → Uncheck "AI Enhancement"
```


---

## 📊 Understanding Your Scores

### ATS Score Ranges

- 🟢 **80-100**: Excellent - Apply immediately!
- 🟡 **70-79**: Good - Minor tweaks needed
- 🟠 **60-69**: Fair - Add keywords
- 🔴 **<60**: Needs work - Follow recommendations


### Score Components

- **Keyword Score**: How many JD keywords you have
- **Format Score**: Resume structure (usually 100%)
- **Experience Score**: Role alignment

---

## ✅ Success Checklist

After setup, you should be able to:

- [ ] Login to dashboard
- [ ] Scrape jobs from LinkedIn
- [ ] Import jobs to database
- [ ] Generate resume variant
- [ ] Download PDF
- [ ] View ATS score
- [ ] See recommendations

If all checked: **You're ready! 🎉**

---

## 🆘 Need Help?

1. Check logs: `tail -f dashboard.log`
2. Test database: `sqlite3 data/resume_tracker.db ".tables"`
3. Verify services: `systemctl status ollama`
4. Read full docs: `README.md`

---

**Happy Job Hunting! 🎯**

```

***