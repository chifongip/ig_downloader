"""
Instagram API routes for FastAPI.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os

from app.utils.scraper import get_scraper, extract_story_id_from_url, DOWNLOADS_DIR

logger = logging.getLogger(__name__)
router = APIRouter()

# CORS configuration for the main app, not the router
# router.add_middleware is not supported - use app.add_middleware instead


class FetchRequest(BaseModel):
    url: str
    username: Optional[str] = None
    password: Optional[str] = None


class FetchResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    medias: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class DownloadRequest(BaseModel):
    url: str
    username: Optional[str] = None
    password: Optional[str] = None


class DownloadResponse(BaseModel):
    success: bool
    path: Optional[str] = None
    message: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    version: str = "1.0.0"



@router.get("/api/status", response_model=StatusResponse)
async def status():
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/api/fetch", response_model=FetchResponse)
async def fetch(request: FetchRequest):
    """
    Fetch metadata from an Instagram URL.
    Supports: posts, reels, stories, profiles.

    Requires Instagram credentials (via IG_USERNAME/IG_PASSWORD env vars or in request).
    """
    try:
        scraper = get_scraper(request.username, request.password)

        # Check if we have valid credentials
        if not scraper.username:
            return FetchResponse(
                success=False,
                message="Instagram credentials required. Set IG_USERNAME and IG_PASSWORD environment variables or provide username/password in request."
            )

        # Check if URL is a story URL
        if "/stories/" in request.url:
            story_id = extract_story_id_from_url(request.url)
            if story_id:
                data = scraper.fetch_story(story_id)
                if data:
                    return FetchResponse(success=True, data=data)
                return FetchResponse(success=False, message="Failed to fetch story. Check if story is public and credentials are correct.")
            return FetchResponse(success=False, message="Invalid story URL format")

        # Check if URL is a profile URL (reel or post)
        if "/reel/" in request.url or "/p/" in request.url:
            data = scraper.fetch_post_metadata(request.url)
            if data:
                return FetchResponse(success=True, data=data)
            return FetchResponse(success=False, message="Failed to fetch post metadata. Check if URL is valid and credentials are correct.")

        # Handle username/profile URLs
        if request.url.startswith("https://www.instagram.com/"):
            username = request.url.rstrip("/").split("/")[-1].split("?")[0]
            if not username:
                return FetchResponse(success=False, message="Invalid Instagram URL")
            medias = scraper.fetch_user_medias(username, amount=5)
            return FetchResponse(success=True, medias=medias)

        return FetchResponse(success=False, message="Unsupported URL format")

    except Exception as e:
        logger.error(f"Fetch error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.post("/api/download", response_model=DownloadResponse)
async def download(request: DownloadRequest):
    """
    Download media from an Instagram URL.
    Supports: posts, reels, stories.
    """
    try:
        scraper = get_scraper(request.username, request.password)
        downloads_dir = str(DOWNLOADS_DIR)
        os.makedirs(downloads_dir, exist_ok=True)

        # Check if URL is a story URL
        if "/stories/" in request.url:
            story_id = extract_story_id_from_url(request.url)
            if story_id:
                path = scraper.download_story(story_id, downloads_dir)
                if path:
                    return DownloadResponse(success=True, path=path)
                return DownloadResponse(success=False, message="Failed to download story")
            return DownloadResponse(success=False, message="Invalid story URL format")

        # Download post/reel
        path = scraper.download_media(request.url, downloads_dir)

        if path:
            return DownloadResponse(success=True, path=path)
        return DownloadResponse(success=False, message="Failed to download media")

    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/api/download/{filename}")
async def serve_download(filename: str):
    """Serve a downloaded file for streaming."""
    downloads_dir = str(DOWNLOADS_DIR)
    file_path = os.path.join(downloads_dir, filename)

    # Path traversal protection
    real_path = os.path.realpath(file_path)
    real_downloads = os.path.realpath(downloads_dir)
    if not real_path.startswith(real_downloads + os.sep) and real_path != real_downloads:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
