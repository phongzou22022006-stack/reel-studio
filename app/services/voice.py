"""
Text-to-speech service using Edge TTS.
"""

import asyncio
import math
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional, Tuple

import edge_tts
from loguru import logger

from app.config import config
from app.models.const import TTSProvider


def parse_voice_name(voice_name: str) -> str:
    """Parse voice name, falling back to config default."""
    if voice_name and voice_name.strip():
        return voice_name.strip()
    return config.tts.voice_name


async def _edge_tts_async(
    text: str,
    voice_name: str,
    voice_rate: float = 1.0,
    voice_file: Optional[str] = None,
) -> Optional[Any]:
    """Async Edge TTS generation."""
    try:
        communicate = edge_tts.Communicate(text, voice_name, rate=f"{voice_rate:+d}%")
        
        if voice_file:
            await communicate.save(voice_file)
            return communicate
        else:
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            await communicate.save(tmp_path)
            return tmp_path
    except Exception as e:
        logger.error(f"Edge TTS failed: {e}")
        return None


def tts(
    text: str,
    voice_name: str = "",
    voice_rate: Optional[float] = None,
    voice_volume: Optional[float] = None,
    voice_file: Optional[str] = None,
) -> Optional[Any]:
    """
    Generate speech from text using Edge TTS.
    
    Args:
        text: Text to speak
        voice_name: Voice identifier (e.g., "vi-VN-HoaiMyNeural")
        voice_rate: Speech rate multiplier (1.0 = normal)
        voice_volume: Volume multiplier (1.0 = normal) - not supported by Edge TTS
        voice_file: Output file path (optional, creates temp file if None)
        
    Returns:
        Edge TTS communicate object (for subtitle timing) or None on failure
    """
    provider = config.tts.provider
    if provider != TTSProvider.EDGE:
        logger.warning(f"TTS provider {provider} not yet implemented, using Edge TTS")
    
    voice = parse_voice_name(voice_name)
    rate = voice_rate or config.tts.voice_rate
    volume = voice_volume or config.tts.voice_volume
    
    logger.info(f"Generating TTS with voice {voice}, rate {rate}")
    
    # Edge TTS doesn't support volume control directly
    # We'll adjust volume during audio processing if needed
    
    # Run async function
    try:
        result = asyncio.run(_edge_tts_async(text, voice, rate, voice_file))
        return result
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return None


def get_audio_duration(audio_source: Any) -> float:
    """
    Get audio duration in seconds.
    
    Args:
        audio_source: Either a file path or Edge TTS communicate object
        
    Returns:
        Duration in seconds, 0 on failure
    """
    try:
        if isinstance(audio_source, str) and os.path.exists(audio_source):
            # Use ffprobe to get duration
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_source,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        elif hasattr(audio_source, 'sub_maker'):
            # Edge TTS communicate object
            # Estimate duration from text length (rough)
            # Edge TTS doesn't expose duration before saving
            # This is a rough estimate: 150 words per minute
            text = getattr(audio_source, 'text', '')
            word_count = len(text.split())
            return word_count / 2.5  # ~150 WPM = 2.5 words per second
    except Exception as e:
        logger.error(f"Failed to get audio duration: {e}")
    
    return 0.0


def create_subtitle(
    text: str,
    sub_maker: Any,
    subtitle_file: str,
) -> bool:
    """
    Create subtitle file from Edge TTS timing data.
    
    Args:
        text: Original text
        sub_maker: Edge TTS communicate object
        subtitle_file: Output SRT file path
        
    Returns:
        True if successful
    """
    try:
        # Edge TTS doesn't directly provide word-level timing
        # This is a simplified implementation
        # In MPT, they have a more sophisticated approach
        
        # For now, create a simple subtitle with whole text
        # Duration from get_audio_duration
        duration = get_audio_duration(sub_maker)
        if duration == 0:
            duration = 10.0  # fallback
        
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write("1\n")
            f.write(f"00:00:00,000 --> 00:00:{duration:06.3f}\n")
            f.write(f"{text}\n")
        
        logger.info(f"Created subtitle file: {subtitle_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to create subtitle: {e}")
        return False


def list_voices(language: str = "") -> list:
    """List available TTS voices."""
    try:
        # Edge TTS voices are built-in
        # This would require querying Edge TTS API
        # For now, return common Vietnamese voices
        vietnamese_voices = [
            "vi-VN-HoaiMyNeural",
            "vi-VN-NamMinhNeural",
            "vi-VN-VanMinhNeural",
            "vi-VN-ThuHangNeural",
        ]
        
        english_voices = [
            "en-US-AriaNeural",
            "en-US-GuyNeural",
            "en-GB-SoniaNeural",
            "en-AU-NatashaNeural",
        ]
        
        all_voices = vietnamese_voices + english_voices
        
        if language:
            if "vi" in language.lower():
                return vietnamese_voices
            elif "en" in language.lower():
                return english_voices
        
        return all_voices
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        return []


def adjust_volume(
    input_file: str,
    output_file: str,
    volume_multiplier: float,
) -> bool:
    """
    Adjust audio volume using ffmpeg.
    
    Args:
        input_file: Input audio file
        output_file: Output audio file
        volume_multiplier: Volume multiplier (0.5 = half, 2.0 = double)
        
    Returns:
        True if successful
    """
    try:
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-filter:a", f"volume={volume_multiplier}",
            "-y",  # Overwrite output
            output_file,
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            logger.error(f"Volume adjustment failed: {result.stderr}")
            return False
        
        logger.info(f"Adjusted volume to {volume_multiplier}x")
        return True
    except Exception as e:
        logger.error(f"Volume adjustment error: {e}")
        return False
