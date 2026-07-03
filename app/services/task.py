"""
Main task orchestration service.
"""

import math
import os
import re
from os import path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.config import config
from app.models.const import TaskState, PipelineStage
from app.models.schema import TaskData, VideoParams, TaskStatus
from app.services import (
    llm,
    voice,
    subtitle,
    video as video_service,
    material,
    templating,
    state as sm,
)
from app.utils import file_security, utils


def start(
    task_id: str,
    params: VideoParams,
    stop_at: str = "video",
) -> Optional[Dict[str, Any]]:
    """
    Start a new video generation task.
    
    Returns:
        Task result dict with outputs up to stop_at stage
    """
    logger.info(f"Starting task {task_id}: {params.video_subject}")
    
    # Initialize task
    task_dir = utils.task_dir(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=5,
    )
    
    # ============================================================================
    # 1. Script generation
    # ============================================================================
    video_script = params.video_script.strip()
    if not video_script:
        logger.info("## Generating video script")
        
        # Load style config if provided
        script_template = params.script_template
        if params.style_config:
            style = templating.engine.load_style_config(params.style_config)
            if style:
                script_template = style.script_template
        
        video_script = llm.generate_script(
            video_subject=params.video_subject,
            language=params.language,
            tone=params.tone,
            length=params.length,
            hook_type=params.hook_type,
            script_template=script_template,
        )
    else:
        logger.debug(f"Using custom script: {video_script[:100]}...")
    
    if not video_script:
        sm.state.update_task(task_id, status=TaskStatus.FAILED, error="Failed to generate script")
        return None
    
    # Save script
    script_file = task_dir / "script.txt"
    utils.write_text(script_file, video_script)
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=15,
        script=video_script,
        script_template_used=params.script_template,
    )
    
    if stop_at == "script":
        sm.state.update_task(
            task_id,
            status=TaskStatus.COMPLETE,
            progress=100,
        )
        return {
            "script": video_script,
            "script_file": str(script_file),
        }
    
    # ============================================================================
    # 2. Visual prompts generation
    # ============================================================================
    logger.info("## Generating visual prompts")
    
    # Load prompt template
    prompt_template = params.prompt_template
    if params.style_config:
        style = templating.engine.load_style_config(params.style_config)
        if style:
            prompt_template = style.prompt_template
    
    # Determine number of prompts based on video length
    # Rough estimate: 1 prompt per 5-8 seconds
    num_prompts = max(3, math.ceil(params.length / 6))
    
    prompts = []
    if params.video_terms and len(params.video_terms) >= num_prompts:
        # Use provided terms as prompts (simplified)
        prompts = params.video_terms[:num_prompts]
    else:
        # Generate prompts from script
        context = {
            "topic": params.video_subject,
            "language": params.language,
            "tone": params.tone,
            "length": params.length,
            "hook_type": params.hook_type,
        }
        
        prompts = llm.generate_prompts(
            script=video_script,
            num_prompts=num_prompts,
            prompt_template=prompt_template,
            context=context,
        )
    
    if not prompts:
        logger.warning("No prompts generated, using fallback prompts")
        prompts = [params.video_subject] * num_prompts
    
    # Save prompts
    prompts_file = task_dir / "prompts.txt"
    utils.write_lines(prompts_file, prompts)
    
    # Create images directory for user uploads
    images_dir = task_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=25,
        prompts=prompts,
        prompt_template_used=prompt_template,
    )
    
    if stop_at == "prompts":
        sm.state.update_task(
            task_id,
            status=TaskStatus.PAUSED,  # Waiting for user images
            progress=100,
        )
        return {
            "script": video_script,
            "prompts": prompts,
            "prompts_file": str(prompts_file),
            "images_dir": str(images_dir),
            "instructions": f"Generate images for prompts and place in {images_dir} as 001.png, 002.png, ...",
        }
    
    # ============================================================================
    # 3. Image handling (user-provided or AI-generated)
    # ============================================================================
    logger.info("## Processing images")
    
    image_files = list(images_dir.iterdir())
    image_files = [f for f in image_files if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    image_files.sort()
    
    if not image_files:
        # No images provided, task should have stopped at "prompts"
        # But if we're here, we'll use stock footage as fallback
        logger.warning("No images found, will use stock footage")
        images = None
    else:
        # Rename images to sequential numbers
        images = []
        for i, img_path in enumerate(image_files, 1):
            new_name = images_dir / f"{i:03d}{img_path.suffix}"
            if img_path != new_name:
                img_path.rename(new_name)
            images.append(str(new_name))
        
        logger.info(f"Found {len(images)} user-provided images")
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=30,
        images=images,
    )
    
    # ============================================================================
    # 4. Audio generation
    # ============================================================================
    logger.info("## Generating audio")
    
    audio_file = task_dir / "audio.mp3"
    sub_maker = voice.tts(
        text=video_script,
        voice_name=voice.parse_voice_name(params.voice_name),
        voice_rate=params.voice_rate,
        voice_file=str(audio_file),
    )
    
    if sub_maker is None:
        sm.state.update_task(task_id, status=TaskStatus.FAILED, error="Failed to generate audio")
        return None
    
    audio_duration = math.ceil(voice.get_audio_duration(sub_maker))
    if audio_duration == 0:
        sm.state.update_task(task_id, status=TaskStatus.FAILED, error="Failed to get audio duration")
        return None
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=40,
        audio_file=str(audio_file),
        audio_duration=audio_duration,
    )
    
    if stop_at == "audio":
        sm.state.update_task(
            task_id,
            status=TaskStatus.COMPLETE,
            progress=100,
        )
        return {
            "audio_file": str(audio_file),
            "audio_duration": audio_duration,
        }
    
    # ============================================================================
    # 5. Subtitle generation
    # ============================================================================
    logger.info("## Generating subtitles")
    
    subtitle_path = ""
    if params.subtitle_enabled:
        subtitle_path = task_dir / "subtitle.srt"
        
        if config.subtitle.provider == "whisper":
            subtitle.create(
                audio_file=str(audio_file),
                subtitle_file=str(subtitle_path),
            )
            subtitle.correct(
                subtitle_file=str(subtitle_path),
                video_script=video_script,
            )
        else:
            # Edge TTS subtitle
            voice.create_subtitle(
                text=video_script,
                sub_maker=sub_maker,
                subtitle_file=str(subtitle_path),
            )
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=50,
        subtitle_path=str(subtitle_path) if subtitle_path else None,
    )
    
    if stop_at == "subtitle":
        sm.state.update_task(
            task_id,
            status=TaskStatus.COMPLETE,
            progress=100,
        )
        return {
            "subtitle_path": str(subtitle_path),
        }
    
    # ============================================================================
    # 6. Video materials collection
    # ============================================================================
    logger.info("## Collecting video materials")
    
    video_materials = []
    
    # If we have user images, use them as primary materials
    if images:
        for img_path in images:
            # Convert images to video clips (will be done during assembly)
            video_materials.append(str(img_path))
    elif params.video_source != "local":
        # Download stock footage
        video_terms = params.video_terms or prompts[:5]  # Use prompts as search terms
        
        downloaded_videos = material.download_videos(
            task_id=task_id,
            search_terms=video_terms,
            source=params.video_source.value,
            video_aspect=params.video_aspect.value,
            audio_duration=audio_duration * params.video_count,
            max_clip_duration=params.video_clip_duration,
        )
        
        if downloaded_videos:
            video_materials = downloaded_videos
    else:
        # Local materials
        if params.video_materials:
            video_materials = [m.url for m in params.video_materials]
    
    if not video_materials:
        logger.error("No video materials available")
        sm.state.update_task(task_id, status=TaskStatus.FAILED, error="No video materials")
        return None
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=60,
        materials=video_materials,
    )
    
    if stop_at == "materials":
        sm.state.update_task(
            task_id,
            status=TaskStatus.COMPLETE,
            progress=100,
        )
        return {
            "materials": video_materials,
        }
    
    # ============================================================================
    # 7. Video assembly
    # ============================================================================
    logger.info("## Assembling video")
    
    final_videos = []
    combined_videos = []
    
    for i in range(params.video_count):
        index = i + 1
        combined_path = task_dir / f"combined-{index}.mp4"
        final_path = task_dir / f"final-{index}.mp4"
        
        logger.info(f"### Creating video {index}")
        
        # Combine video materials
        video_service.combine_videos(
            combined_video_path=str(combined_path),
            video_paths=video_materials,
            audio_file=str(audio_file),
            video_aspect=params.video_aspect.value,
            video_concat_mode=params.video_concat_mode.value if params.video_concat_mode else "random",
            video_transition_mode=params.video_transition_mode.value if params.video_transition_mode else None,
            max_clip_duration=params.video_clip_duration,
            threads=params.n_threads,
        )
        
        # Add subtitles and finalize
        video_service.add_subtitles(
            input_video=str(combined_path),
            output_video=str(final_path),
            subtitle_file=str(subtitle_path) if subtitle_path and path.exists(subtitle_path) else None,
            subtitle_style={
                "position": params.subtitle_position.value if params.subtitle_position else "bottom",
                "font_name": params.font_name,
                "font_size": params.font_size,
                "fore_color": params.text_fore_color,
                "stroke_color": params.stroke_color,
                "stroke_width": params.stroke_width,
            } if params.subtitle_enabled else None,
        )
        
        combined_videos.append(str(combined_path))
        final_videos.append(str(final_path))
        
        # Update progress
        progress = 60 + (40 * (i + 1) / params.video_count)
        sm.state.update_task(task_id, progress=progress)
    
    logger.success(f"Task {task_id} finished, generated {len(final_videos)} videos")
    
    result = {
        "videos": final_videos,
        "combined_videos": combined_videos,
        "script": video_script,
        "prompts": prompts,
        "audio_file": str(audio_file),
        "audio_duration": audio_duration,
        "subtitle_path": str(subtitle_path) if subtitle_path else None,
        "materials": video_materials,
        "images": images,
    }
    
    sm.state.update_task(
        task_id,
        status=TaskStatus.COMPLETE,
        progress=100,
        **{k: v for k, v in result.items() if v is not None},
    )
    
    return result


def resume_task(
    task_id: str,
    images: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Resume a paused task (after user uploads images).
    
    Args:
        task_id: Task ID to resume
        images: List of image file paths (optional, will use images in task directory)
    
    Returns:
        Task result dict
    """
    logger.info(f"Resuming task {task_id}")
    
    # Load task data
    task_data = sm.state.get_task(task_id)
    if not task_data:
        logger.error(f"Task {task_id} not found")
        return None
    
    if task_data.status != TaskStatus.PAUSED:
        logger.warning(f"Task {task_id} is not paused (status: {task_data.status})")
    
    task_dir = utils.task_dir(task_id)
    
    # Handle image uploads
    if images:
        images_dir = task_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        for i, img_path in enumerate(images, 1):
            dst_path = images_dir / f"{i:03d}{Path(img_path).suffix}"
            try:
                shutil.copy2(img_path, dst_path)
                logger.info(f"Copied image to {dst_path}")
            except Exception as e:
                logger.error(f"Failed to copy image {img_path}: {e}")
    
    # Check if we have images now
    images_dir = task_dir / "images"
    image_files = list(images_dir.iterdir())
    image_files = [f for f in image_files if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    
    if not image_files:
        logger.error(f"No images found in {images_dir}")
        return None
    
    # Load params from metadata
    metadata_file = task_dir / "metadata.json"
    if not metadata_file.exists():
        logger.error(f"Metadata not found for task {task_id}")
        return None
    
    metadata = utils.load_task_metadata(task_id)
    params_data = metadata.get("params", {})
    
    # Recreate VideoParams
    # (This is simplified; in production you'd serialize/deserialize properly)
    params = VideoParams(**params_data)
    
    # Continue from where we left off (after prompts)
    return start(task_id, params, stop_at="video")


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status and outputs."""
    return sm.state.get_task(task_id)


def list_tasks(limit: int = 50, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
    """List tasks with optional filtering."""
    return sm.state.list_tasks(limit=limit, status=status)


def cancel_task(task_id: str) -> bool:
    """Cancel a running task."""
    # Implementation depends on your task runner
    # For now, just mark as failed
    sm.state.update_task(task_id, status=TaskStatus.FAILED, error="Cancelled by user")
    return True


# Import shutil and Path for resume_task
import shutil
from pathlib import Path
