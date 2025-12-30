# dashboard/config.py

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Dashboard configuration"""
    
    # App settings
    app_name: str = "Resume Tailoring Dashboard"
    debug: bool = True
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-12345") #change this
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "admin123")  #change this
    session_expire_hours: int = 24
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Paths
    project_root: str = "/project_JobScraping" #Update as your setup
    database_path: str = "data/resume_tracker.db" 
    resumes_dir: str = "data/resumes" 
    variants_dir: str = "data/resumes/variants" 
    job_descriptions_dir: str = "data/job_descriptions" 
    job_requirements_dir: str = "data/job_requirements"
    
    # Ollama settings
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://homevm:11434") #Update as your setup
    ollama_model: str = os.getenv("OLLAMA_MODEL", "jarvis-mid") #Update as your setup
    
    # Generation defaults
    default_target_bullets: int = 18
    default_ai_enhancement: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
