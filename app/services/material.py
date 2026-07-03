"""
Stock footage download service.
"""

import os
import re
from pathlib import Path
from typing import List, Optional

from loguru import logger

from app.config import config
from app.models.schema import MaterialInfo
from app.utils import utils


def download_videos(
    task_id: str,
    search_terms: List[str],
    source: str = "pexels",
    video_aspect: str = "16:9",
    audio_duration: float = 60,
    max_clip_duration: Optional[int] = None,
    match_script_order: bool = False,
) -> Optional[List[str]]:
    """
    Download stock footage based on search terms.
    
    Args:
        task_id: Task ID for organizing downloads
        search_terms: List of search terms
        source: Stock source ("pexels", "pixabay", "coverr")
        video_aspect: Aspect ratio (e.g., "16:9", "9:16")
        audio_duration: Total duration needed in seconds
        max_clip_duration: Max duration per clip
        match_script_order: Match materials to script order
        
    Returns:
        List of downloaded video file paths, or None on failure
    """
    if not search_terms:
        logger.error("No search terms provided")
        return None
    
    task_dir = utils.task_dir(task_id)
    videos_dir = task_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse aspect ratio
    width, height = _parse_aspect(video_aspect)
    
    downloaded = []
    clips_needed = max(1, int(audio_duration / (max_clip_duration or 5)))
    
    # Determine search strategy
    if match_script_order:
        # Use terms in order
        terms_to_search = search_terms[:clips_needed]
    else:
        # Use all terms, pick best matches
        terms_to_search = search_terms * (clips_needed // len(search_terms) + 1)
        terms_to_search = terms_to_search[:clips_needed]
    
    for i, term in enumerate(terms_to_search):
        if len(downloaded) >= clips_needed:
            break
        
        # Generate filename
        clip_name = f"clip_{i+1:03d}.mp4"
        clip_path = videos_dir / clip_name
        
        logger.info(f"Downloading video for term '{term}': {clip_name}")
        
        # Download based on source
        if source == "pexels":
            success = _download_from_pexels(term, clip_path, width, height)
        elif source == "pixabay":
            success = _download_from_pixabay(term, clip_path, width, height)
        elif source == "coverr":
            success = _download_from_coverr(term, clip_path, width, height)
        else:
            logger.error(f"Unknown source: {source}")
            continue
        
        if success:
            downloaded.append(str(clip_path))
    
    if not downloaded:
        logger.error("No videos downloaded successfully")
        return None
    
    logger.info(f"Downloaded {len(downloaded)} videos")
    return downloaded


def _download_from_pexels(
    term: str,
    output_path: Path,
    width: int,
    height: int,
) -> bool:
    """Download from Pexels API."""
    api_key = config.stock.pexels_api_key
    
    if not api_key:
        logger.warning("Pexels API key not configured")
        return False
    
    try:
        import requests
        
        # Search endpoint
        url = "https://api.pexels.com/videos/search"
        params = {
            "query": term,
            "per_page": 1,
            "size": "medium",
            "orientation": "landscape" if width > height else "portrait",
        }
        
        headers = {"Authorization": api_key}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Pexels search failed: {response.text}")
            return False
        
        data = response.json()
        if not data.get("videos"):
            logger.warning(f"No videos found for '{term}'")
            return False
        
        # Get video URL (largest available)
        video = data["videos"][0]
        video_file = video.get("video_files", [])
        
        # Filter by resolution
        best_url = None
        for vf in video_file:
            if vf["width"] == width and vf["height"] == height:
                best_url = vf["link"]
                break
        
        if not best_url:
            # Fallback to largest available
            video_file.sort(key=lambda x: x["width"] * x["height"], reverse=True)
            if video_file:
                best_url = video_file[0]["link"]
        
        if not best_url:
            return False
        
        # Download video
        resp = requests.get(best_url, timeout=60)
        if resp.status_code != 200:
            return False
        
        with open(output_path, "wb") as f:
            f.write(resp.content)
        
        logger.info(f"Downloaded from Pexels: {output_path}")
        return True
        
    except ImportError:
        logger.error("requests library not installed")
        return False
    except Exception as e:
        logger.error(f"Pexels download failed: {e}")
        return False


def _download_from_pixabay(
    term: str,
    output_path: Path,
    width: int,
    height: int,
) -> bool:
    """Download from Pixabay API."""
    api_key = config.stock.pixabay_api_key or "1234567890abcdef"  # demo key
    
    try:
        import requests
        
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": api_key,
            "q": term,
            "per_page": 1,
            "video_type": "all",
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            return False
        
        data = response.json()
        if not data.get("hits"):
            return False
        
        video = data["hits"][0]
        video_file = video.get("videos", {})
        
        # Get video URL
        best_url = None
        for size, info in video_file.items():
            if info.get("width") == width and info.get("height") == height:
                best_url = info.get("url")
                break
        
        if not best_url:
            # Fallback
            if "large" in video_file:
                best_url = video_file["large"].get("url")
            elif video_file:
                best_url = list(video_file.values())[0].get("url")
        
        if not best_url:
            return False
        
        resp = requests.get(best_url, timeout=60)
        if resp.status_code != 200:
            return False
        
        with open(output_path, "wb") as f:
            f.write(resp.content)
        
        logger.info(f"Downloaded from Pixabay: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Pixabay download failed: {e}")
        return False


def _download_from_coverr(
    term: str,
    output_path: Path,
    width: int,
    height: int,
) -> bool:
    """Download from Coverr API."""
    # Coverr has limited free API
    # For now, just log and return False
    logger.warning("Coverr API not yet implemented")
    return False


def _parse_aspect(aspect: str) -> tuple:
    """Parse aspect ratio string to width, height tuple."""
    if aspect == "16:9":
        return (1920, 1080)
    elif aspect == "9:16":
        return (1080, 1920)
    elif aspect == "1:1":
        return (1080, 1080)
    elif aspect == "4:5":
        return (1080, 1350)
    else:
        return (1920, 1080)


def validate_video_file(video_path: str) -> bool:
    """Validate video file exists and is playable."""
    if not os.path.exists(video_path):
        return False
    
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False
