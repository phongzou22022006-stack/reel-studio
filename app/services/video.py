"""
Video assembly and processing service.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger

from app.config import config
from app.utils import utils


def combine_videos(
    combined_video_path: str,
    video_paths: List[str],
    audio_file: str,
    video_aspect: str = "16:9",
    video_concat_mode: str = "random",
    video_transition_mode: Optional[str] = None,
    max_clip_duration: Optional[int] = None,
    threads: int = 4,
) -> bool:
    """
    Combine multiple video clips into one.
    
    Args:
        combined_video_path: Output video path
        video_paths: List of input video/image paths
        audio_file: Audio file path
        video_aspect: Aspect ratio (e.g., "16:9", "9:16")
        video_concat_mode: Concatenation mode ("random", "sequential")
        video_transition_mode: Transition effect (None, "fade-in", "fade-out", etc.)
        max_clip_duration: Max duration for each clip in seconds
        threads: Number of FFmpeg threads
        
    Returns:
        True if successful
    """
    if not video_paths:
        logger.error("No video paths provided")
        return False
    
    # Parse aspect ratio
    width, height = _parse_aspect(video_aspect)
    logger.info(f"Creating video {width}x{height} ({video_aspect})")
    
    # Prepare input files for FFmpeg
    input_args = []
    filter_complex_parts = []
    
    for i, video_path in enumerate(video_paths):
        if not os.path.exists(video_path):
            logger.warning(f"Input file not found: {video_path}")
            continue
        
        # Determine if file is image or video
        ext = Path(video_path).suffix.lower()
        is_image = ext in {".png", ".jpg", ".jpeg", ".webp"}
        
        # Add input
        input_args.extend(["-i", video_path])
        
        # Set duration for images
        if is_image:
            duration = max_clip_duration or 5
            filter_complex_parts.append(
                f"[{i}:v]setpts=PTS-STARTPTS,scale={width}:{height},format=yuv420p,fade=t=in:st=0:d=0.5,loop=loop=1:size=1:stop=1, setpts=N/FRAME_RATE/TB, trim=duration={duration}[v{i}]"
            )
        else:
            filter_complex_parts.append(
                f"[{i}:v]setpts=PTS-STARTPTS,scale={width}:{height},format=yuv420p,fade=t=in:st=0:d=0.5[v{i}]"
            )
    
    if not filter_complex_parts:
        logger.error("No valid input files")
        return False
    
    # Concatenate videos
    if len(filter_complex_parts) == 1:
        # Single input - no concatenation needed
        filter_complex = ";".join(filter_complex_parts)
        concat_part = f"[v0]out"
    else:
        # Multiple inputs - concatenate
        concat_inputs = " ".join(f"[v{i}]" for i in range(len(filter_complex_parts)))
        filter_complex = ";".join(filter_complex_parts) + f";{concat_inputs}concat=n={len(filter_complex_parts)}:v=1:a=0[outv]"
        
        # Add transition if specified
        if video_transition_mode and len(filter_complex_parts) > 1:
            filter_complex = _add_transitions(filter_complex, len(filter_complex_parts), video_transition_mode)
        
        concat_part = "[outv]out"
    
    # Get audio duration
    audio_duration = utils.get_file_size(audio_file) / 100000  # rough estimate
    # Actually get real duration
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            audio_duration = float(result.stdout.strip())
    except Exception:
        pass
    
    # Build FFmpeg command
    cmd = ["ffmpeg", "-y"]
    cmd.extend(input_args)
    
    # Add filter complex
    cmd.extend(["-filter_complex", filter_complex + f";{concat_part},fps=30,scale={width}:{height},format=yuv420p[v]"])
    
    # Map output
    cmd.extend([
        "-map", "[v]",
        "-i", audio_file,
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-audio_shift", "0",
        "-shortest",
        "-threads", str(threads),
        combined_video_path,
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr}")
            return False
        logger.info(f"Combined video created: {combined_video_path}")
        return True
    except Exception as e:
        logger.error(f"Video combination failed: {e}")
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
        # Default to 16:9
        return (1920, 1080)


def _add_transitions(filter_complex: str, num_clips: int, mode: str) -> str:
    """Add transition effects to filter graph."""
    # Simplified transition handling
    # In production, you'd implement proper crossfade transitions
    return filter_complex


def add_subtitles(
    input_video: str,
    output_video: str,
    subtitle_file: Optional[str] = None,
    subtitle_style: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Burn subtitles into video.
    
    Args:
        input_video: Input video path
        output_video: Output video path
        subtitle_file: SRT subtitle file path (optional)
        subtitle_style: Subtitle styling options
        
    Returns:
        True if successful
    """
    if subtitle_file and os.path.exists(subtitle_file):
        style = subtitle_style or {}
        
        # Parse subtitle position
        position = style.get("position", "bottom")
        if position == "top":
            y_offset = 50
        elif position == "center":
            y_offset = "h-100"  # center
        else:  # bottom
            y_offset = "h-100"
        
        # Build filter complex for subtitles
        font_name = style.get("font_name", "Roboto-Bold")
        font_size = style.get("font_size", 24)
        fore_color = style.get("fore_color", "#FFFFFF")
        stroke_color = style.get("stroke_color", "#000000")
        stroke_width = style.get("stroke_width", 1.0)
        
        # Map colors
        color_map = {
            "#FFFFFF": "white",
            "#000000": "black",
            "#FF0000": "red",
            "#00FF00": "lime",
            "#0000FF": "blue",
            "#FFFF00": "yellow",
        }
        
        fore_color_hex = color_map.get(fore_color, fore_color)
        stroke_color_hex = color_map.get(stroke_color, stroke_color)
        
        # Build subtitle filter
        subtitle_filter = f"subtitles={subtitle_file}:fontsdir=./fonts:force_style='FontName={font_name},FontSize={font_size},PrimaryColour=&H00{fore_color_hex[1:]},OutlineColour=&H00{stroke_color_hex[1:]},Outline={stroke_width},Shadow=0'"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-vf", subtitle_filter,
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-threads", "4",
            output_video,
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                logger.error(f"Subtitle burn failed: {result.stderr}")
                return False
            logger.info(f"Video with subtitles created: {output_video}")
            return True
        except Exception as e:
            logger.error(f"Subtitle burn error: {e}")
            return False
    else:
        # No subtitles, just re-encode
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-threads", "4",
            output_video,
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                logger.error(f"Video re-encode failed: {result.stderr}")
                return False
            logger.info(f"Video processed: {output_video}")
            return True
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            return False


def preprocess_video(
    materials: List[Any],
    clip_duration: Optional[int] = None,
) -> List[Any]:
    """
    Preprocess local video materials.
    
    Args:
        materials: List of MaterialInfo objects
        clip_duration: Maximum duration for each clip
        
    Returns:
        List of processed material paths
    """
    processed = []
    
    for material in materials:
        if os.path.exists(material.url):
            # Check duration
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", material.url],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    duration = float(result.stdout.strip())
                    material.duration = duration
                    
                    # Split into clips if needed
                    if clip_duration and duration > clip_duration:
                        # Split logic would go here
                        pass
                    
                    processed.append(material)
            except Exception:
                processed.append(material)
    
    return processed


def extract_audio(
    video_file: str,
    output_audio_file: str,
) -> bool:
    """Extract audio from video."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
        output_audio_file,
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"Audio extraction failed: {result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"Audio extraction error: {e}")
        return False


def trim_video(
    input_video: str,
    output_video: str,
    start_time: float,
    end_time: float,
) -> bool:
    """Trim video to specified time range."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-ss", str(start_time),
        "-to", str(end_time),
        "-c:v", "libx264",
        "-c:a", "aac",
        output_video,
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"Video trimming failed: {result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"Video trimming error: {e}")
        return False
