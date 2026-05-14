"""
FastAPI application for Instagram Downloader.
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from app.routes import instagram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Instagram Downloader API",
    description="API for fetching and downloading Instagram media",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(instagram.router)


@app.get("/", response_class=RedirectResponse)
async def root():
    """Redirect to index page."""
    return "/index.html"


@app.get("/index.html")
async def index():
    """Serve the main index page."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "public", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"error": "Index page not found"}


# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "public")
app.mount("/css", StaticFiles(directory=os.path.join(static_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(static_dir, "js")), name="js")


