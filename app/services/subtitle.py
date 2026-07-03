"""
Subtitle generation service using Whisper.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger

from app.config import config
from app.models.const import SubtitleProvider
from app.utils import utils


def create(
    audio_file: str,
    subtitle_file: str,
    language: Optional[str] = None,
) -> bool:
    """
    Create subtitle file from audio using Whisper.
    
    Args:
        audio_file: Input audio file path
        subtitle_file: Output subtitle file path (SRT format)
        language: Language code (e.g., "vi", "en") - auto-detect if None
        
    Returns:
        True if successful
    """
    provider = config.subtitle.provider
    if provider != SubtitleProvider.WHISPER:
        logger.warning(f"Subtitle provider {provider} not yet implemented, using Whisper")
    
    model_size = config.subtitle.model_size
    lang = language or config.subtitle.language
    
    logger.info(f"Generating subtitle with Whisper ({model_size}), language: {lang or 'auto'}")
    
    try:
        from faster_whisper import WhisperModel
        
        # Load model
        model = WhisperModel(
            model_size_or_path=model_size,
            device="cpu",  # Use "cuda" if GPU available
            compute_type="int8",  # Use "float16" for GPU
        )
        
        # Transcribe
        segments, info = model.transcribe(
            audio_file,
            language=lang if lang else None,
            beam_size=5,
            vad_filter=True,
        )
        
        # Write SRT file
        with open(subtitle_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                # Convert seconds to SRT timestamp
                start_time = _seconds_to_srt(segment.start)
                end_time = _seconds_to_srt(segment.end)
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment.text.strip()}\n\n")
        
        logger.info(f"Subtitle created: {subtitle_file}")
        return True
        
    except ImportError:
        logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
        return False
    except Exception as e:
        logger.error(f"Whisper subtitle generation failed: {e}")
        return False


def correct(
    subtitle_file: str,
    video_script: str,
) -> bool:
    """
    Correct subtitle text using original script.
    
    Args:
        subtitle_file: Subtitle file path
        video_script: Original video script
        
    Returns:
        True if successful
    """
    if not os.path.exists(subtitle_file):
        return False
    
    try:
        # Load subtitle lines
        subtitles = file_to_subtitles(subtitle_file)
        if not subtitles:
            return False
        
        # Simple correction: just use the script as single subtitle
        # In production, you'd align script sentences with audio timing
        # This is a simplified implementation
        
        # For now, replace all subtitles with script chunks
        # based on timing distribution
        script_lines = _split_script_by_time(video_script, len(subtitles))
        
        # Write corrected subtitles
        with open(subtitle_file, "w", encoding="utf-8") as f:
            for i, (start, end, _) in enumerate(subtitles):
                if i < len(script_lines):
                    text = script_lines[i]
                else:
                    text = video_script.split(".")[0] if "." in video_script else video_script
                
                f.write(f"{i+1}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text.strip()}\n\n")
        
        logger.info(f"Subtitle corrected: {subtitle_file}")
        return True
    except Exception as e:
        logger.error(f"Subtitle correction failed: {e}")
        return False


def file_to_subtitles(subtitle_file: str) -> List[Tuple[str, str, str]]:
    """
    Parse SRT file to list of (start_time, end_time, text).
    
    Args:
        subtitle_file: SRT file path
        
    Returns:
        List of subtitle tuples
    """
    if not os.path.exists(subtitle_file):
        return []
    
    try:
        with open(subtitle_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse SRT format
        subtitles = []
        blocks = re.split(r"\n\s*\n", content.strip())
        
        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if len(lines) >= 3:
                # Lines: index, time, text(s)
                time_line = lines[1]
                text = " ".join(lines[2:])
                
                # Parse time range
                if " --> " in time_line:
                    start, end = time_line.split(" --> ", 1)
                    subtitles.append((start, end, text))
        
        return subtitles
    except Exception as e:
        logger.error(f"Failed to parse subtitle file {subtitle_file}: {e}")
        return []


def _seconds_to_srt(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _srt_to_seconds(timestamp: str) -> float:
    """Convert SRT timestamp to seconds."""
    try:
        # Handle HH:MM:SS,mmm or HH:MM:SS.mmm
        timestamp = timestamp.replace(".", ",")
        time_part, millis_part = timestamp.split(",")
        
        # Parse HH:MM:SS
        parts = time_part.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = map(int, parts)
        else:
            return 0.0
        
        millis = int(millis_part)
        return hours * 3600 + minutes * 60 + seconds + millis / 1000.0
    except Exception:
        return 0.0


def _split_script_by_time(script: str, num_chunks: int) -> List[str]:
    """
    Split script into approximately equal text chunks.
    
    Args:
        script: Full script text
        num_chunks: Number of chunks to create
        
    Returns:
        List of script chunks
    """
    if num_chunks <= 1:
        return [script]
    
    # Split by sentences
    sentences = re.split(r'[.!?]+', script)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [script] * num_chunks
    
    # Distribute sentences across chunks
    chunks = []
    sentences_per_chunk = max(1, len(sentences) // num_chunks)
    
    for i in range(0, len(sentences), sentences_per_chunk):
        chunk = " ".join(sentences[i:i + sentences_per_chunk])
        if chunk:
            chunks.append(chunk)
    
    # Ensure we have exactly num_chunks
    while len(chunks) < num_chunks:
        chunks.append(sentences[-1] if sentences else script[:50])
    
    return chunks[:num_chunks]


def validate_subtitle_file(subtitle_file: str) -> bool:
    """Validate subtitle file format."""
    if not os.path.exists(subtitle_file):
        return False
    
    subtitles = file_to_subtitles(subtitle_file)
    return len(subtitles) > 0


def get_subtitle_duration(subtitle_file: str) -> float:
    """Get total duration covered by subtitles."""
    subtitles = file_to_subtitles(subtitle_file)
    if not subtitles:
        return 0.0
    
    # Get last end time
    last_end = _srt_to_seconds(subtitles[-1][1])
    return last_end


def merge_subtitle_files(files: List[str], output_file: str) -> bool:
    """Merge multiple subtitle files."""
    try:
        all_subtitles = []
        time_offset = 0.0
        
        for file in files:
            subtitles = file_to_subtitles(file)
            if not subtitles:
                continue
            
            # Adjust timestamps
            for start, end, text in subtitles:
                start_sec = _srt_to_seconds(start) + time_offset
                end_sec = _srt_to_seconds(end) + time_offset
                
                all_subtitles.append((
                    _seconds_to_srt(start_sec),
                    _seconds_to_srt(end_sec),
                    text
                ))
            
            # Update offset for next file
            time_offset += get_subtitle_duration(file)
        
        # Write merged file
        with open(output_file, "w", encoding="utf-8") as f:
            for i, (start, end, text) in enumerate(all_subtitles, 1):
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
        
        return True
    except Exception as e:
        logger.error(f"Failed to merge subtitle files: {e}")
        return False
