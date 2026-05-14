"""
Instagrapi integration utilities for Instagram media fetching and downloading.
"""
import json
import os
import logging
import re
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from urllib.parse import urlparse

from instagrapi import Client
from instagrapi.types import Media

# Configure logging
logger = logging.getLogger(__name__)

# Session file path for persistent login
SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "session.json")
DOWNLOADS_DIR = Path(__file__).parent.parent.parent / "downloads"
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json"

# Credential loading order: request args > env vars > config file > None
ENV_USERNAME = os.environ.get("IG_USERNAME")
ENV_PASSWORD = os.environ.get("IG_PASSWORD")


def load_config() -> Dict[str, str]:
    """Load Instagram credentials from config.json file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return {
                    "username": config.get("instagram_username", ""),
                    "password": config.get("instagram_password", ""),
                }
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config.json: {e}")
    return {"username": "", "password": ""}


class InstagramScraper:
    """Wrapper around instagrapi Client for Instagram media operations."""

    def __init__(self, username: str = None, password: str = None):
        """Initialize the scraper with optional credentials.

        Credential priority: function args > environment variables > config file
        """
        self.client = Client()

        # Load config file credentials
        config = load_config()
        CONFIG_USERNAME = config["username"]
        CONFIG_PASSWORD = config["password"]

        # Use provided credentials, then env vars, then config file
        self.username = username or ENV_USERNAME or CONFIG_USERNAME
        self.password = password or ENV_PASSWORD or CONFIG_PASSWORD
        self._loaded_session = False

    def _ensure_downloads_dir(self) -> Path:
        """Ensure downloads directory exists."""
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        return DOWNLOADS_DIR

    def load_session(self) -> bool:
        """Load saved session if available."""
        if os.path.exists(SESSION_FILE):
            try:
                self.client.load_settings(SESSION_FILE)
                # Test if session is valid
                self.client.login_by_sessionid(self.client.sessionid)
                self._loaded_session = True
                logger.info("Session loaded successfully")
                return True
            except Exception as e:
                logger.warning(f"Failed to load session: {e}")
                self._loaded_session = False
        return False

    def login(self) -> bool:
        """Login to Instagram with credentials or saved session."""
        if self.load_session():
            return True

        if self.username and self.password:
            try:
                self.client.login(self.username, self.password)
                self.client.dump_settings(SESSION_FILE)
                os.chmod(SESSION_FILE, 0o600)
                self._loaded_session = True
                logger.info("Login successful, session saved")
                return True
            except Exception as e:
                logger.error(f"Login failed: {e}")
                return False
        return False

    def logout(self):
        """Logout and clear session."""
        self.client.logout()
        self._loaded_session = False
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)

    def fetch_media_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch media information from Instagram URL.

        Args:
            url: Instagram post URL (photo, video, reel, story, profile)

        Returns:
            Dict with media info or None if failed
        """
        try:
            # Extract media pk from URL
            media_pk = self.client.media_pk_from_url(url)
            media = self.client.media_info(media_pk)

            return self._serialize_media(media)
        except Exception as e:
            logger.error(f"Failed to fetch media info: {e}")
            return None

    def fetch_user_medias(self, username: str, amount: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch recent posts from a user profile.

        Args:
            username: Instagram username
            amount: Number of posts to fetch

        Returns:
            List of media dictionaries
        """
        try:
            user_id = self.client.user_id_from_username(username)
            medias = self.client.user_medias(user_id, amount)

            return [self._serialize_media(m) for m in medias]
        except Exception as e:
            logger.error(f"Failed to fetch user medias: {e}")
            return []

    def download_media(self, url: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Download media from Instagram URL.

        Args:
            url: Instagram post URL
            output_dir: Optional output directory

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            media_pk = self.client.media_pk_from_url(url)

            media = self.client.media_info(media_pk)
            media_type = media.media_type

            if media_type == 1:
                # Photo
                path = self.client.photo_download(media_pk, output_dir)
                return str(path)
            elif media_type == 2 and media.product_type == "clips":
                # Reel
                path = self.client.clip_download(media_pk, output_dir)
                return str(path)
            elif media_type == 2:
                # Video
                path = self.client.video_download(media_pk, output_dir)
                return str(path)
            elif media_type == 8:
                # Album - download all photos/videos
                paths = self.client.album_download(media_pk, output_dir)
                return str(paths[0]) if paths else None
            else:
                logger.warning(f"Unsupported media type: {media_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
            return None

    def fetch_post_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a post without downloading.

        Args:
            url: Instagram post URL

        Returns:
            Dict with post metadata
        """
        try:
            media_pk = self.client.media_pk_from_url(url)
            media = self.client.media_info(media_pk)

            result = {
                "media_id": media.id,
                "media_pk": media.pk,
                "code": media.code,
                "media_type": media.media_type,
                "media_type_name": self._get_media_type_name(media.media_type),
                "thumbnail_url": media.thumbnail_url,
                "url": f"https://www.instagram.com/p/{media.code}/",
                "caption": getattr(media, 'caption_text', None),
                "user": {
                    "username": media.user.username if media.user else None,
                    "full_name": media.user.full_name if media.user else None,
                    "profile_pic_url": media.user.profile_pic_url if media.user else None,
                },
                "view_count": getattr(media, 'view_count', None),
                "like_count": getattr(media, 'like_count', None),
                "comment_count": getattr(media, 'comment_count', None),
                "duration": getattr(media, 'duration', None),
                "video_url": getattr(media, 'video_url', None),
            }

            # Handle album media (type 8) - include all child items
            if media.media_type == 8 and media.resources:
                child_items = []
                for child in media.resources:
                    child_items.append({
                        "media_type": child.media_type,
                        "media_type_name": self._get_media_type_name(child.media_type),
                        "thumbnail_url": child.thumbnail_url,
                        "video_url": getattr(child, 'video_url', None),
                    })
                result["carousel_media"] = child_items

            return result
        except Exception as e:
            logger.error(f"Failed to fetch post metadata: {e}")
            return None

    def _serialize_media(self, media: Media) -> Dict[str, Any]:
        """Convert Media object to dictionary."""
        thumbnail_url = media.thumbnail_url
        # Albums may have null thumbnail — use first child's thumbnail as fallback
        if not thumbnail_url and media.media_type == 8 and media.resources:
            for child in media.resources:
                if child.thumbnail_url:
                    thumbnail_url = child.thumbnail_url
                    break

        return {
            "media_id": media.id,
            "media_pk": media.pk,
            "code": media.code,
            "media_type": media.media_type,
            "media_type_name": self._get_media_type_name(media.media_type),
            "thumbnail_url": thumbnail_url,
            "url": f"https://www.instagram.com/p/{media.code}/",
            "caption": getattr(media, 'caption_text', None),
            "view_count": getattr(media, 'view_count', None),
            "like_count": getattr(media, 'like_count', None),
            "comment_count": getattr(media, 'comment_count', None),
            "duration": getattr(media, 'duration', None),
            "video_url": getattr(media, 'video_url', None),
            "product_type": getattr(media, 'product_type', None),
            "user": {
                "username": media.user.username if media.user else None,
                "full_name": media.user.full_name if media.user else None,
                "profile_pic_url": media.user.profile_pic_url if media.user else None,
            },
        }

    def _get_media_type_name(self, media_type: int) -> str:
        """Convert media type number to name."""
        types = {
            1: "Photo",
            2: "Video",
            8: "Album",
        }
        return types.get(media_type, f"Unknown({media_type})")

    def fetch_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch story metadata by story ID.

        Args:
            story_id: The story ID (numeric)

        Returns:
            Dict with story metadata or None if failed
        """
        try:
            story = self.client.story_info(story_id)
            return {
                "story_id": story.pk,
                "media_pk": story.pk,
                "media_type": story.media_type,
                "media_type_name": self._get_media_type_name(story.media_type),
                "thumbnail_url": story.thumbnail_url,
                "caption": getattr(story, 'caption_text', None),
                "user": {
                    "username": story.user.username if story.user else None,
                    "full_name": story.user.full_name if story.user else None,
                    "profile_pic_url": story.user.profile_pic_url if story.user else None,
                },
                "view_count": getattr(story, 'view_count', None),
                "taken_at": getattr(story, 'taken_at', None),
            }
        except Exception as e:
            logger.error(f"Failed to fetch story: {e}")
            return None

    def download_story(self, story_id: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Download story by story ID.

        Args:
            story_id: The story ID (numeric)
            output_dir: Optional output directory

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Convert output_dir to Path if provided
            folder = Path(output_dir) if output_dir else Path("")
            url = ""

            # Try to get story info to extract username
            try:
                story = self.client.story_info(story_id)
                username = story.user.username if story.user else 'unknown'
                url = str(story.thumbnail_url if story.media_type == 1 else story.video_url)
            except Exception:
                # Fall back to direct public request for story info
                username = 'unknown'
                try:
                    data = self.client.public_graphql_request(
                        {"story_id": story_id},
                        query_hash="d3d74d74c6b97bf631b10a9a2b458c7a",
                    )
                    story_data = data.get("reel", {}).get("latest_reel_media", {})
                    if story_data:
                        media = story_data.get("items", [{}])[0]
                        url = media.get("thumbnail_url") or media.get("video_url", "")
                        username = 'story'
                except Exception:
                    url = ""

            if not url:
                logger.error("Could not determine story media URL")
                return None

            # Determine file extension from URL (handle query strings)
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            ext = path_parts[-1].split('.')[-1] if '.' in path_parts[-1] else ('jpg' if 'jpg' in url.lower() else 'mp4')

            # Use username_storyid.ext format for proper naming
            filename = f"{username}_{story_id}.{ext}"
            path = folder / filename

            # Download using direct request with proper filename
            response = self.client.public.get(url, stream=True)
            response.raise_for_status()

            with open(path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)

            return str(path.resolve())
        except Exception as e:
            logger.error(f"Failed to download story: {e}")
            return None


# Global scraper instance (will be initialized with credentials if provided)
scraper: Optional[InstagramScraper] = None


def get_scraper(username: str = None, password: str = None) -> InstagramScraper:
    """Get or create scraper instance.

    Credentials can be provided via:
    1. Function arguments (username, password)
    2. Environment variables (IG_USERNAME, IG_PASSWORD)
    3. A saved session file (session.json)
    """
    global scraper
    if scraper is None:
        scraper = InstagramScraper(username, password)
        # Always attempt login if we have credentials
        if scraper.username and scraper.password:
            scraper.login()
        elif os.path.exists(SESSION_FILE):
            # Try loading from saved session
            scraper.load_session()
    return scraper


def extract_story_id_from_url(url: str) -> Optional[str]:
    """Extract story ID from Instagram story URL.

    URL format: https://www.instagram.com/stories/username/123456789/
    """
    # Match story URL pattern
    match = re.search(r'/stories/[^/]+/(\d+)/?', url)
    if match:
        return match.group(1)
    return None
