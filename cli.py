#!/usr/bin/env python3
"""
Command‑line interface for Reel Studio.

Example usage:
  python cli.py --topic "Why successful people wake up at 5 AM"
  python cli.py --topic "..." --stop-at visuals
  python cli.py --task-id abc123 --resume
"""

import argparse
import json
import re
import sys
from typing import Optional, Sequence

from loguru import logger

from app.config import config
from app.models.schema import (
    BGMType,
    MaterialSource,
    SubtitlePosition,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import task as tm
from app.utils import utils


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"value must be >= 1, got {parsed}")
    return parsed


def _paragraph_count(value: str) -> int:
    parsed = int(value)
    if parsed < 1 or parsed > 10:
        raise argparse.ArgumentTypeError(
            f"paragraph-number must be between 1 and 10, got {parsed}"
        )
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"value must be >= 0, got {parsed}")
    return parsed


def _percent_position(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed > 100:
        raise argparse.ArgumentTypeError(
            f"custom-position must be between 0 and 100, got {parsed}"
        )
    return parsed


def _hex_color(value: str) -> str:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise argparse.ArgumentTypeError(
            f"color must use #RRGGBB format, got {value!r}"
        )
    return value


def _transition_mode(value: str) -> Optional[str]:
    normalized = value.strip().lower()
    if normalized == "none":
        return None
    try:
        return VideoTransitionMode(normalized).value
    except ValueError:
        allowed = ", ".join(m.value for m in VideoTransitionMode)
        raise argparse.ArgumentTypeError(
            f"video-transition-mode must be one of: {allowed}"
        )


def _bgm_type(value: str) -> str:
    normalized = value.strip().lower()
    try:
        return BGMType(normalized).value
    except ValueError:
        raise argparse.ArgumentTypeError("bgm-type must be one of: none, random, custom")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reel Studio – Facebook Reels automation with templating",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ============================================================================
    # Task mode (generate new vs resume)
    # ============================================================================
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--topic",
        help="Topic for video generation (creates new task)",
    )
    mode_group.add_argument(
        "--task-id",
        help="Existing task ID to resume (requires --resume)",
    )
    mode_group.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all tasks",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a paused task (requires --task-id)",
    )

    # ============================================================================
    # Input & templating
    # ============================================================================
    input_group = parser.add_argument_group("Input & Templating")
    input_group.add_argument(
        "--custom-script",
        default="",
        help="Path to custom script file (overrides AI generation)",
    )
    input_group.add_argument(
        "--custom-prompts",
        default="",
        help="Path to custom prompts file (overrides AI generation)",
    )
    input_group.add_argument(
        "--script-template",
        default="default",
        help="Script template name (file in templates/scripts/)",
    )
    input_group.add_argument(
        "--prompt-template",
        default="default",
        help="Prompt template name (file in templates/prompts/)",
    )
    input_group.add_argument(
        "--style-config",
        default="",
        help="Style config YAML file (overrides individual templates)",
    )
    input_group.add_argument(
        "--language",
        default="vi",
        help="Language for script generation (vi, en, etc.)",
    )
    input_group.add_argument(
        "--tone",
        default="educational",
        choices=["educational", "shock", "humor", "motivational", "storytelling"],
        help="Tone of the script",
    )
    input_group.add_argument(
        "--length",
        type=_positive_int,
        default=30,
        help="Target video length in seconds",
    )
    input_group.add_argument(
        "--hook-type",
        default="question",
        choices=["question", "shock", "story", "number_list"],
        help="Type of hook for the script",
    )

    # ============================================================================
    # Visual pipeline
    # ============================================================================
    visual_group = parser.add_argument_group("Visual Pipeline")
    visual_group.add_argument(
        "--stop-at",
        default="video",
        choices=["script", "prompts", "audio", "subtitle", "materials", "video"],
        help="Pipeline stop stage",
    )
    visual_group.add_argument(
        "--upload-images",
        nargs="+",
        help="Paths to images to upload (for --resume mode)",
    )

    # ============================================================================
    # Video parameters
    # ============================================================================
    video_group = parser.add_argument_group("Video Parameters")
    video_group.add_argument(
        "--video-terms",
        default=None,
        help="Comma-separated search terms for stock footage",
    )
    video_group.add_argument(
        "--video-count",
        type=_positive_int,
        default=1,
        help="Output video count (>=1)",
    )
    video_group.add_argument(
        "--video-aspect",
        type=VideoAspect,
        default=VideoAspect.LANDSCAPE_16_9,
        help="Video aspect ratio",
    )
    video_group.add_argument(
        "--video-source",
        type=MaterialSource,
        default=MaterialSource.PEXELS,
        help="Video material source",
    )
    video_group.add_argument(
        "--video-materials",
        default="",
        help="Comma-separated local material paths (for --video-source local)",
    )
    video_group.add_argument(
        "--video-concat-mode",
        type=VideoConcatMode,
        default=None,
        help="Video concatenation mode",
    )
    video_group.add_argument(
        "--video-transition-mode",
        type=_transition_mode,
        default=None,
        metavar="{none,shuffle,fade-in,fade-out,slide-in,slide-out}",
        help="Video transition mode",
    )
    video_group.add_argument(
        "--video-clip-duration",
        type=_positive_int,
        default=None,
        help="Maximum duration of each source clip in seconds",
    )
    video_group.add_argument(
        "--match-materials-to-script",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Match generated/search materials to script order",
    )

    # ============================================================================
    # Audio parameters
    # ============================================================================
    audio_group = parser.add_argument_group("Audio Parameters")
    audio_group.add_argument(
        "--voice-name",
        default="",
        help="TTS voice name (default from config)",
    )
    audio_group.add_argument(
        "--voice-volume",
        type=_non_negative_float,
        default=None,
        help="Speech volume multiplier",
    )
    audio_group.add_argument(
        "--voice-rate",
        type=_non_negative_float,
        default=None,
        help="Speech rate multiplier",
    )
    audio_group.add_argument(
        "--bgm-type",
        type=_bgm_type,
        default=None,
        metavar="{none,random,custom}",
        help="Background music mode",
    )
    audio_group.add_argument(
        "--bgm-file",
        default=None,
        help="Custom background music file",
    )
    audio_group.add_argument(
        "--bgm-volume",
        type=_non_negative_float,
        default=None,
        help="Background music volume multiplier",
    )

    # ============================================================================
    # Subtitle parameters
    # ============================================================================
    subtitle_group = parser.add_argument_group("Subtitle Parameters")
    subtitle_group.add_argument(
        "--subtitle-enabled",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Enable subtitles",
    )
    subtitle_group.add_argument(
        "--font-name",
        default=None,
        help="Subtitle font file name",
    )
    subtitle_group.add_argument(
        "--subtitle-position",
        type=SubtitlePosition,
        default=None,
        help="Subtitle position",
    )
    subtitle_group.add_argument(
        "--custom-position",
        type=_percent_position,
        default=None,
        help="Custom subtitle position as percent from top, 0-100",
    )
    subtitle_group.add_argument(
        "--text-fore-color",
        type=_hex_color,
        default=None,
        help="Subtitle text color in #RRGGBB format",
    )
    subtitle_group.add_argument(
        "--font-size",
        type=_positive_int,
        default=None,
        help="Subtitle font size",
    )
    subtitle_group.add_argument(
        "--stroke-color",
        type=_hex_color,
        default=None,
        help="Subtitle outline color in #RRGGBB format",
    )
    subtitle_group.add_argument(
        "--stroke-width",
        type=_non_negative_float,
        default=None,
        help="Subtitle outline width",
    )
    subtitle_group.add_argument(
        "--subtitle-background-enabled",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Enable subtitle background",
    )
    subtitle_group.add_argument(
        "--subtitle-background-color",
        type=_hex_color,
        default=None,
        help="Subtitle background color in #RRGGBB format",
    )
    subtitle_group.add_argument(
        "--rounded-subtitle-background",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Enable rounded translucent subtitle background",
    )

    # ============================================================================
    # Miscellaneous
    # ============================================================================
    misc_group = parser.add_argument_group("Miscellaneous")
    misc_group.add_argument(
        "--task-id-custom",
        default="",
        help="Custom task ID (auto-generated if empty)",
    )
    misc_group.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv)",
    )

    args = parser.parse_args(argv)

    # Validation
    if args.task_id and not args.resume and not args.list_tasks:
        parser.error("--task-id requires --resume or --list-tasks")

    if args.resume and not args.task_id:
        parser.error("--resume requires --task-id")

    if args.video_source == MaterialSource.LOCAL and not args.video_materials.strip():
        parser.error("--video-materials is required when --video-source is local")

    return args


def setup_logging(verbosity: int) -> None:
    """Configure loguru based on verbosity level."""
    level = "INFO"
    if verbosity == 1:
        level = "DEBUG"
    elif verbosity >= 2:
        level = "TRACE"

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )


def build_video_params(args: argparse.Namespace) -> VideoParams:
    """Build VideoParams from CLI arguments."""
    video_terms = None
    if args.video_terms:
        video_terms = [term.strip() for term in args.video_terms.split(",") if term.strip()]

    video_materials = None
    materials_arg = args.video_materials or ""
    if materials_arg.strip():
        video_materials = [
            # Actual duration will be detected during video processing; use 0 as placeholder.
            MaterialInfo(provider="local", url=item.strip(), duration=0)
            for item in materials_arg.split(",")
            if item.strip()
        ]

    # Custom script/prompts
    video_script = ""
    if args.custom_script:
        try:
            with open(args.custom_script, "r", encoding="utf-8") as f:
                video_script = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read custom script {args.custom_script}: {e}")
            raise

    params_kwargs = {
        "video_subject": args.topic or "",
        "video_script": video_script,
        "video_terms": video_terms,
        "video_source": args.video_source,
        "video_materials": video_materials,
        "video_count": args.video_count,
        "video_aspect": args.video_aspect,
        "voice_name": args.voice_name,
        "subtitle_enabled": args.subtitle_enabled,
        "script_template": args.script_template,
        "prompt_template": args.prompt_template,
        "style_config": args.style_config,
        "language": args.language,
        "tone": args.tone,
        "length": args.length,
        "hook_type": args.hook_type,
        "stop_at": args.stop_at,
    }

    # Optional arguments
    optional_arg_names = [
        "video_concat_mode",
        "video_transition_mode",
        "video_clip_duration",
        "match_materials_to_script",
        "voice_volume",
        "voice_rate",
        "bgm_type",
        "bgm_file",
        "bgm_volume",
        "font_name",
        "subtitle_position",
        "custom_position",
        "text_fore_color",
        "font_size",
        "stroke_color",
        "stroke_width",
        "rounded_subtitle_background",
    ]
    for name in optional_arg_names:
        value = getattr(args, name)
        if value is not None:
            params_kwargs[name] = value

    # Subtitle background
    if args.subtitle_background_enabled is False:
        params_kwargs["text_background_color"] = False
        params_kwargs["rounded_subtitle_background"] = False
    elif args.subtitle_background_color is not None:
        params_kwargs["text_background_color"] = args.subtitle_background_color
    elif args.subtitle_background_enabled is True:
        params_kwargs["text_background_color"] = True

    return VideoParams(**params_kwargs)


def run_cli(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point."""
    args = parse_args(argv)
    setup_logging(args.verbose)

    if args.list_tasks:
        logger.info("Listing tasks is not yet implemented")
        return 0

    if args.task_id and args.resume:
        # Resume existing task
        logger.info(f"Resuming task {args.task_id}")
        if args.upload_images:
            logger.info(f"Uploading {len(args.upload_images)} images")
            # TODO: Implement image upload for resume
        result = tm.resume_task(task_id=args.task_id, images=args.upload_images)
        if not result:
            logger.error("Task resume failed")
            return 1
        print(json.dumps({"task_id": args.task_id, "result": result}, ensure_ascii=False))
        return 0

    # New task generation
    params = build_video_params(args)
    task_id = args.task_id_custom or utils.get_uuid()
    logger.info(f"Starting task {task_id}, stop_at: {args.stop_at}")

    result = tm.start(task_id=task_id, params=params, stop_at=args.stop_at)
    if not result:
        logger.error("Video generation failed")
        return 1

    print(json.dumps({"task_id": task_id, "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
