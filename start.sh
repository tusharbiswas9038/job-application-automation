#!/bin/bash
cd /project_JobScraping
echo "🚀 Starting Job Application Automation System..."
nohup uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 > dashboard.log 2>&1 &
echo "✅ Dashboard running at http://$(hostname -I | awk '{print $1}'):8000"
echo "👤 Username: admin | Password: admin123"
