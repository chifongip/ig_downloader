# Instagram Downloader

A web application for fetching and downloading Instagram media — photos, videos, reels, stories, and profile pictures.

## Features

- Fetch metadata and download Instagram posts, reels, stories, and profiles
- Carousel/album browsing with inline navigation
- Clean "PRISM" themed UI
- REST API with auto-generated docs
- Session persistence — log in once, stay authenticated

## Tech Stack

- **Backend**: Python, FastAPI, uvicorn
- **Instagram API**: [instagrapi](https://github.com/subzeroid/instagrapi) (vendored locally)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Storage**: Local filesystem (`downloads/` directory)

## Getting Started

### Prerequisites

- Python 3.10+
- An Instagram account

### Installation

```bash
git clone <repo-url>
cd ig_downloader
conda create -n scraper python=3.10 -y
conda activate scraper
pip install -r requirements.txt
```

### Configuration

Set your Instagram credentials using any of these methods (highest priority first):

1. **Request parameters** — pass `username`/`password` with each API call
2. **Environment variables** — `export IG_USERNAME=... IG_PASSWORD=...`
3. **config.json** — create a `config.json` in the project root:
   ```json
   { "username": "your_username", "password": "your_password" }
   ```
4. **Session file** — after the first successful login, a `session.json` is saved automatically and reused for future logins

### Running

```bash
conda activate scraper  # or use your preferred env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

| URL | Description |
|---|---|
| http://localhost:8000 | Web UI |
| http://localhost:8000/docs | Swagger API docs |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/fetch` | Fetch metadata for a post/reel/story/profile URL |
| `POST` | `/api/download` | Download media to server, returns local file path |
| `GET` | `/api/download/{filename}` | Serve a previously downloaded file |
| `GET` | `/api/status` | Health check |

## Project Structure

```
ig_downloader/
├── app/
│   ├── main.py              # FastAPI app setup and static file serving
│   ├── routes/
│   │   └── instagram.py     # API route handlers
│   └── utils/
│       └── scraper.py       # instagrapi wrapper, auth, and download logic
├── public/
│   ├── index.html            # Frontend UI
│   ├── css/                  # Stylesheets
│   └── js/                   # Client-side JavaScript
├── instagrapi/               # Vendored instagrapi library
├── downloads/                # Downloaded media (gitignored)
├── config.json               # Credentials (gitignored)
├── session.json              # Auth session (gitignored)
└── requirements.txt
```

## Security Notes

- `config.json` and `session.json` are gitignored to prevent credential leaks
- `session.json` is created with `0o600` permissions (owner read/write only)
- The download endpoint validates paths to prevent directory traversal attacks
