from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class VideoAspect(str, Enum):
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    INSTAGRAM_4_5 = "4:5"


class VideoConcatMode(str, Enum):
    RANDOM = "random"
    SEQUENTIAL = "sequential"


class VideoTransitionMode(str, Enum):
    NONE = "none"
    SHUFFLE = "shuffle"
    FADE_IN = "fade-in"
    FADE_OUT = "fade-out"
    SLIDE_IN = "slide-in"
    SLIDE_OUT = "slide-out"


class SubtitlePosition(str, Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    CUSTOM = "custom"


class BGMType(str, Enum):
    NONE = "none"
    RANDOM = "random"
    CUSTOM = "custom"


class MaterialSource(str, Enum):
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    COVERR = "coverr"
    LOCAL = "local"


class MaterialInfo(BaseModel):
    provider: str
    url: str
    duration: float = 0.0


class ScriptTemplate(BaseModel):
    name: str
    path: str
    description: str = ""
    variables: List[str] = Field(default_factory=list)


class PromptTemplate(BaseModel):
    name: str
    path: str
    description: str = ""
    variables: List[str] = Field(default_factory=list)


class StyleConfig(BaseModel):
    name: str
    script_template: str
    prompt_template: str
    video_aspect: VideoAspect = VideoAspect.LANDSCAPE_16_9
    visual_source: str = "ai"  # "ai", "stock", "mix"
    tone: str = "educational"
    length: int = 30


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    PAUSED = "paused"  # waiting for user images


class VideoParams(BaseModel):
    # Input
    video_subject: str = ""
    video_script: str = ""  # custom script (overrides AI generation)
    video_terms: Optional[List[str]] = None

    # Templating
    script_template: str = "default"
    prompt_template: str = "default"
    style_config: str = ""
    language: str = "vi"
    tone: str = "educational"
    length: int = 30  # seconds
    hook_type: str = "question"  # "question", "shock", "story", "number_list"

    # Video source
    video_source: MaterialSource = MaterialSource.PEXELS
    video_materials: Optional[List[MaterialInfo]] = None
    video_count: int = 1
    video_aspect: VideoAspect = VideoAspect.LANDSCAPE_16_9
    video_concat_mode: Optional[VideoConcatMode] = None
    video_transition_mode: Optional[VideoTransitionMode] = None
    video_clip_duration: Optional[int] = None
    match_materials_to_script: Optional[bool] = None

    # Audio
    voice_name: str = ""
    voice_volume: Optional[float] = None
    voice_rate: Optional[float] = None

    # Background music
    bgm_type: BGMType = BGMType.RANDOM
    bgm_file: Optional[str] = None
    bgm_volume: Optional[float] = None

    # Subtitle
    subtitle_enabled: bool = True
    font_name: Optional[str] = None
    subtitle_position: Optional[SubtitlePosition] = None
    custom_position: Optional[float] = None
    text_fore_color: Optional[str] = None
    font_size: Optional[int] = None
    stroke_color: Optional[str] = None
    stroke_width: Optional[float] = None
    text_background_color: Optional[Union[bool, str]] = None
    rounded_subtitle_background: Optional[bool] = None

    # Performance
    n_threads: int = 4

    # Stop control
    stop_at: str = "video"  # "script", "terms", "audio", "subtitle", "materials", "video"


class TaskData(BaseModel):
    task_id: str
    params: VideoParams
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    created_at: float = Field(default_factory=lambda: time.time())
    updated_at: float = Field(default_factory=lambda: time.time())

    # Output fields
    script: Optional[str] = None
    script_template_used: Optional[str] = None
    prompts: Optional[List[str]] = None
    prompt_template_used: Optional[str] = None
    audio_file: Optional[str] = None
    audio_duration: Optional[float] = None
    subtitle_path: Optional[str] = None
    materials: Optional[List[str]] = None
    images: Optional[List[str]] = None  # user‑uploaded images
    combined_videos: Optional[List[str]] = None
    videos: Optional[List[str]] = None

    # Metadata
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)


class TaskCreateRequest(BaseModel):
    video_subject: str
    video_script: Optional[str] = None
    script_template: Optional[str] = None
    prompt_template: Optional[str] = None
    style_config: Optional[str] = None
    video_aspect: VideoAspect = VideoAspect.LANDSCAPE_16_9
    video_count: int = 1
    stop_at: str = "video"


class TaskResumeRequest(BaseModel):
    task_id: str
    images: Optional[List[str]] = None  # paths to uploaded images


class TaskUpdateRequest(BaseModel):
    status: Optional[TaskStatus] = None
    progress: Optional[float] = None
    script: Optional[str] = None
    prompts: Optional[List[str]] = None
    images: Optional[List[str]] = None
    error: Optional[str] = None


# Import time at module level
import time
