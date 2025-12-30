#!/bin/bash
BACKUP_DIR="/project_JobScraping/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/system_backup_$DATE.tar.gz \
    data/resume_tracker.db \
    data/resumes/ \
    dashboard/config.py
echo "✅ Backup created: $BACKUP_DIR/system_backup_$DATE.tar.gz"
