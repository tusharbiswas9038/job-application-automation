# dashboard/app.py

from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import timedelta
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.config import settings
from dashboard.auth import authenticate_user, create_access_token, get_current_user, get_optional_user

# Import API routers (we'll create these next)
from dashboard.api import jobs, variants, generate, files, scraper, stats

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Mount static files
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

# Templates
templates = Jinja2Templates(directory="dashboard/templates")

# Include API routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(variants.router, prefix="/api/variants", tags=["variants"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

# ============= Auth Routes =============

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    # Check if already authenticated
    user = get_optional_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.app_name
    })

@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    """Handle login"""
    if not authenticate_user(password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.app_name,
            "error": "Invalid password"
        }, status_code=401)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": "user"},
        expires_delta=timedelta(hours=settings.session_expire_hours)
    )
    
    # Redirect to dashboard with cookie
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.session_expire_hours * 3600,
        samesite="lax"
    )
    
    return response

@app.get("/logout")
async def logout():
    """Logout user"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# ============= Main Dashboard Routes =============

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": settings.app_name,
        "page": "dashboard"
    })

@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request, user: dict = Depends(get_current_user)):
    """Jobs list page"""
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "app_name": settings.app_name,
        "page": "jobs"
    })

@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail_page(request: Request, job_id: int, user: dict = Depends(get_current_user)):
    """Job detail page"""
    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "app_name": settings.app_name,
        "page": "jobs",
        "job_id": job_id
    })

@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request, user: dict = Depends(get_current_user)):
    """Generate variant page"""
    return templates.TemplateResponse("generate.html", {
        "request": request,
        "app_name": settings.app_name,
        "page": "generate"
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: dict = Depends(get_current_user)):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "app_name": settings.app_name,
        "page": "settings",
        "settings": {
            "ollama_host": settings.ollama_host,
            "ollama_model": settings.ollama_model,
            "default_target_bullets": settings.default_target_bullets,
            "default_ai_enhancement": settings.default_ai_enhancement
        }
    })

# ============= Health Check =============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0"
    }

# ============= Error Handlers =============

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
    
    return templates.TemplateResponse("404.html", {
        "request": request,
        "app_name": settings.app_name
    }, status_code=404)

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """Handle 401 errors"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"}
        )
    
    return RedirectResponse(url="/login", status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

# Favicon route
from fastapi.responses import FileResponse as FaviconResponse

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    favicon_path = Path("dashboard/static/favicon.ico")
    if favicon_path.exists():
        return FaviconResponse(favicon_path)
    return JSONResponse({"detail": "Not found"}, status_code=404)

@app.get("/scraper", response_class=HTMLResponse)
async def scraper_page(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("scraper.html", {
        "request": request,
        "user": user,
        "app_name": settings.app_name
    })
