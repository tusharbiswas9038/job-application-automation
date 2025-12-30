***

## **4. DEPLOYMENT.md**

```bash
# 🚀 Deployment Guide

Production deployment guide for the Job Application Automation System.

---

## 📋 Pre-Deployment Checklist

### System Requirements
- [ ] Ubuntu 20.04+ or Debian 11+
- [ ] Python 3.8+
- [ ] 2GB RAM minimum (4GB recommended)
- [ ] 10GB disk space
- [ ] Root or sudo access

### Software Dependencies
- [ ] Python pip
- [ ] LaTeX (texlive-full)
- [ ] Ollama (optional, for AI features)
- [ ] Git
- [ ] Nginx (for reverse proxy)
- [ ] Systemd (for service management)

---

## 🔧 Production Setup

### Step 1: System Preparation

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install dependencies
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    texlive-full \
    nginx \
    git \
    sqlite3 \
    curl \
    supervisor

# Install Ollama (optional)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```


### Step 2: Application Setup

```bash
# Clone/copy project
cd /opt
cp -r /project_JobScraping /opt/JobScraping
cd /opt/JobScraping

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    jinja2 \
    pydantic \
    requests \
    beautifulsoup4 \
    httpx \
    python-jose[cryptography] \
    passlib[bcrypt]

# Set permissions
chown -R www-data:www-data /opt/JobScraping
chmod +x /opt/JobScraping/start.sh
```


### Step 3: Create System Service

```bash
cat > /etc/systemd/system/job-scraper.service << 'EOSERVICE'
[Unit]
Description=Job Application Automation System
After=network.target ollama.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/JobScraping
Environment="PATH=/opt/JobScraping/venv/bin"
ExecStart=/opt/JobScraping/venv/bin/uvicorn dashboard.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/job-scraper/access.log
StandardError=append:/var/log/job-scraper/error.log

[Install]
WantedBy=multi-user.target
EOSERVICE

# Create log directory
mkdir -p /var/log/job-scraper
chown www-data:www-data /var/log/job-scraper

# Enable and start service
systemctl daemon-reload
systemctl enable job-scraper
systemctl start job-scraper
systemctl status job-scraper
```


### Step 4: Configure Nginx Reverse Proxy

```bash
cat > /etc/nginx/sites-available/job-scraper << 'EONGINX'
server {
    listen 80;
    server_name your-domain.com;  # Change this

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # Change this

    # SSL Configuration (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/job-scraper-access.log;
    error_log /var/log/nginx/job-scraper-error.log;

    # Max upload size
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files
    location /static/ {
        alias /opt/JobScraping/dashboard/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # PDF downloads
    location /downloads/ {
        alias /opt/JobScraping/data/resumes/variants/;
        add_header Content-Disposition "attachment";
    }
}
EONGINX

# Enable site
ln -s /etc/nginx/sites-available/job-scraper /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```


### Step 5: Setup SSL with Let's Encrypt

```bash
# Install certbot
apt-get install -y certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d your-domain.com

# Auto-renewal (already configured by certbot)
systemctl status certbot.timer
```


### Step 6: Configure Firewall

```bash
# UFW firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
ufw status
```


---

## 🔐 Security Hardening

### Change Default Credentials

```bash
# Edit dashboard/config.py
nano /opt/JobScraping/dashboard/config.py

# Change:
ADMIN_USERNAME = "admin"          # Change this
ADMIN_PASSWORD = "admin123"       # Change this
SECRET_KEY = "your-secret-key"    # Generate new key

# Generate secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```


### Restrict Database Access

```bash
chmod 600 /opt/JobScraping/data/resume_tracker.db
chown www-data:www-data /opt/JobScraping/data/resume_tracker.db
```


### Enable Fail2Ban (SSH Protection)

```bash
apt-get install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban
```


---

## 📊 Monitoring

### Setup Log Rotation

```bash
cat > /etc/logrotate.d/job-scraper << 'EOLOGROTATE'
/var/log/job-scraper/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload job-scraper
    endscript
}
EOLOGROTATE
```


### System Monitoring

```bash
# Check service status
systemctl status job-scraper

# View logs
journalctl -u job-scraper -f

# Check Nginx logs
tail -f /var/log/nginx/job-scraper-access.log
tail -f /var/log/nginx/job-scraper-error.log

# Monitor resources
htop
df -h
```


### Application Monitoring

```bash
# Check database size
du -h /opt/JobScraping/data/resume_tracker.db

# Check variants count
sqlite3 /opt/JobScraping/data/resume_tracker.db "SELECT COUNT(*) FROM variants;"

# Check disk usage
df -h /opt/JobScraping
```


---

## 🔄 Backup Strategy

### Automated Backup Script

```bash
cat > /opt/JobScraping/backup.sh << 'EOBACKUP'
#!/bin/bash

BACKUP_DIR="/opt/backups/job-scraper"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp /opt/JobScraping/data/resume_tracker.db \
   $BACKUP_DIR/resume_tracker_$DATE.db

# Backup resumes
tar -czf $BACKUP_DIR/resumes_$DATE.tar.gz \
   -C /opt/JobScraping/data resumes/

# Backup config
cp /opt/JobScraping/dashboard/config.py \
   $BACKUP_DIR/config_$DATE.py

# Delete old backups
find $BACKUP_DIR -name "*.db" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR"
EOBACKUP

chmod +x /opt/JobScraping/backup.sh
```


### Schedule Backups

```bash
# Add to crontab
crontab -e

# Add this line (daily backup at 2 AM)
0 2 * * * /opt/JobScraping/backup.sh >> /var/log/job-scraper/backup.log 2>&1
```


### Offsite Backup (Optional)

```bash
# Using rsync to remote server
rsync -avz --delete \
  /opt/backups/job-scraper/ \
  user@backup-server:/backups/job-scraper/
```


---

## 🔧 Maintenance

### Update Application

```bash
# Stop service
systemctl stop job-scraper

# Backup current version
cp -r /opt/JobScraping /opt/JobScraping.backup

# Pull updates (or copy new files)
cd /opt/JobScraping
# Apply updates here

# Restart service
systemctl start job-scraper
systemctl status job-scraper
```


### Database Maintenance

```bash
# Vacuum database (optimize)
sqlite3 /opt/JobScraping/data/resume_tracker.db "VACUUM;"

# Check integrity
sqlite3 /opt/JobScraping/data/resume_tracker.db "PRAGMA integrity_check;"

# Analyze query performance
sqlite3 /opt/JobScraping/data/resume_tracker.db "PRAGMA optimize;"
```


### Clear Old Data

```bash
# Delete old variants (older than 90 days)
sqlite3 /opt/JobScraping/data/resume_tracker.db << 'EOSQL'
DELETE FROM variants 
WHERE generated_at < date('now', '-90 days');
EOSQL

# Clean up orphaned PDFs
find /opt/JobScraping/data/resumes/variants/ -name "*.pdf" -mtime +90 -delete
```


---

## 📈 Scaling

### Horizontal Scaling (Multiple Instances)

```bash
# Use Nginx load balancing
upstream job_scraper {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    location / {
        proxy_pass http://job_scraper;
    }
}
```


### Database Optimization

```bash
# Create indexes for common queries
sqlite3 /opt/JobScraping/data/resume_tracker.db << 'EOSQL'
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_variants_generated ON variants(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ats_overall ON ats_scores(overall_score DESC);
EOSQL
```


---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u job-scraper -n 50

# Check port
lsof -i :8000

# Test manually
cd /opt/JobScraping
source venv/bin/activate
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000
```


### High CPU Usage

```bash
# Check processes
top -u www-data

# Restart service
systemctl restart job-scraper

# Check Ollama
systemctl status ollama
```


### Database Locked

```bash
# Kill any hanging processes
pkill -f "job-scraper"

# Check for .db-shm and .db-wal files
ls -la /opt/JobScraping/data/

# Restart
systemctl start job-scraper
```


---

## 🔄 Disaster Recovery

### Full System Restore

```bash
# Stop service
systemctl stop job-scraper

# Restore database
cp /opt/backups/job-scraper/resume_tracker_LATEST.db \
   /opt/JobScraping/data/resume_tracker.db

# Restore resumes
tar -xzf /opt/backups/job-scraper/resumes_LATEST.tar.gz \
   -C /opt/JobScraping/data/

# Fix permissions
chown -R www-data:www-data /opt/JobScraping/data

# Start service
systemctl start job-scraper
```


---

## 📞 Support \& Monitoring

### Health Check Endpoint

```bash
# Add to cron for monitoring
*/5 * * * * curl -f http://localhost:8000/ || systemctl restart job-scraper
```


### Email Alerts

```bash
# Install mailutils
apt-get install -y mailutils

# Add to backup script
if [ $? -eq 0 ]; then
    echo "Backup successful" | mail -s "Job Scraper Backup OK" admin@example.com
else
    echo "Backup failed" | mail -s "Job Scraper Backup FAILED" admin@example.com
fi
```


---

## ✅ Post-Deployment Checklist

- [ ] Service running (`systemctl status job-scraper`)
- [ ] Nginx configured and running
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Default password changed
- [ ] Backups configured and tested
- [ ] Log rotation setup
- [ ] Monitoring in place
- [ ] Tested from external network
- [ ] Documentation updated

---

**Deployment Date**: _____________________
**Deployed By**: _____________________
**Version**: 1.0.0
**Status**: ✅ Production Ready

```

***