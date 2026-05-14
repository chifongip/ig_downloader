# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Instagram Downloader is a web application for fetching and downloading Instagram media (photos, videos, reels, stories, profiles) using the `instagrapi` library.

## Tech Stack

- **Backend**: Python (FastAPI)
- **Instagram API**: instagrapi — also vendored locally in `instagrapi/` directory
- **Frontend**: HTML/CSS/JavaScript (vanilla), themed as "PRISM"
- **Storage**: Local file system (`downloads/` directory)

## Common Commands

### Start the server
```bash
conda activate scraper
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access the application
- Web UI: http://localhost:8000
- API docs: http://localhost:8000/docs

## Authentication

Credential loading priority: request args > environment variables (`IG_USERNAME`/`IG_PASSWORD`) > `config.json` > saved `session.json`.

After first successful login, a `session.json` is saved automatically (with 0o600 permissions). `config.json` and `session.json` are both gitignored.

## Architecture Notes

- **Single global scraper**: `get_scraper()` in `scraper.py` returns a module-level singleton. It auto-logins on first call if credentials are available. Once created, the same instance is reused regardless of what credentials subsequent requests pass.
- **Shared constants**: `DOWNLOADS_DIR` in `scraper.py` is the canonical downloads path — `instagram.py` imports and uses it directly rather than computing its own.
- **Media types**: 1=Photo, 2=Video (including reels when `product_type == "clips"`), 8=Album (carousel).
- **Pydantic model fields**: `instagrapi` models use Pydantic — `hasattr()` always returns `True` even for `None` fields. Check truthiness instead: `media.user.username if media.user else None`.
- **Story handling**: Stories require extracting the story ID from URLs like `/stories/username/123456/`. Story download uses a direct HTTP fetch rather than instagrapi's built-in method.
- **Album handling**: `/api/download` only returns the first item of an album. The frontend renders all carousel items and lets users click through.
- **Static file serving**: FastAPI serves `public/` directly — `index.html` at `/index.html`, CSS at `/css/`, JS at `/js/`. Root `/` redirects to `/index.html`.
- **Frontend XSS**: All user/API-supplied text must be escaped through `escapeHtml()` before injecting into `innerHTML`. The function is defined in `main.js`.
- **File serving security**: `/api/download/{filename}` validates that the resolved path stays within `DOWNLOADS_DIR` to prevent path traversal.

## API Endpoints

- `POST /api/fetch` — Fetch metadata for a post/reel/story/profile URL
- `POST /api/download` — Download media to server, returns local file path
- `GET /api/download/{filename}` — Serve a previously downloaded file (path-traversal protected)
- `GET /api/status` — Health check
