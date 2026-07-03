import tomllib
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "reel-studio.log"
    max_size_mb: int = 100
    backup_count: int = 3


class LLMConfig(BaseModel):
    provider: str = "9router"
    api_base: str = "http://host.docker.internal:20128/v1"
    model: str = "all-in-one"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 1000


class TTSConfig(BaseModel):
    provider: str = "edge"
    voice_name: str = "vi-VN-HoaiMyNeural"
    voice_rate: float = 1.0
    voice_volume: float = 1.0


class SubtitleConfig(BaseModel):
    provider: str = "whisper"
    model_size: str = "medium"
    language: str = ""


class SubtitleStyleConfig(BaseModel):
    enabled: bool = True
    position: str = "bottom"
    font_name: str = "Roboto-Bold.ttf"
    font_size: int = 48
    fore_color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: float = 2.0
    background_color: str = ""
    rounded_background: bool = False
    custom_position: float = 90.0


class ImageConfig(BaseModel):
    provider: str = "none"


class StockConfig(BaseModel):
    enabled: bool = False
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    mix_ratio: float = 0.3
    max_clip_duration: int = 5


class VideoConfig(BaseModel):
    aspect: str = "16:9"
    concat_mode: str = "random"
    transition_mode: str = ""
    clip_duration: int = 5
    threads: int = 4
    resolution: str = "1920x1080"


class OverlayConfig(BaseModel):
    hook_text: bool = True
    hook_duration: int = 3
    hook_font: str = "Roboto-Bold.ttf"
    hook_font_size: int = 72
    hook_color: str = "#FFFFFF"
    hook_stroke: str = "#000000"
    hook_position: str = "center"

    cta_text: bool = True
    cta_duration: int = 3
    cta_font: str = "Roboto-Bold.ttf"
    cta_font_size: int = 48
    cta_color: str = "#FFFFFF"
    cta_stroke: str = "#000000"
    cta_position: str = "bottom"

    watermark: bool = False
    watermark_image: str = ""
    watermark_position: str = "top-right"


class AudioConfig(BaseModel):
    bgm_type: str = "random"
    bgm_volume: float = 0.15
    custom_bgm_file: str = ""
    sound_effects: bool = False
    sound_volume: float = 0.3


class FacebookConfig(BaseModel):
    enabled: bool = False
    page_id: str = ""
    access_token: str = ""
    privacy_status: str = "PUBLIC"
    contains_synthetic_media: bool = True


class TemplatingConfig(BaseModel):
    script_template: str = "default"
    prompt_template: str = "default"
    style_config: str = ""

    class Defaults(BaseModel):
        language: str = "vi"
        tone: str = "educational"
        length: int = 30
        hook_type: str = "question"

    defaults: Defaults = Field(default_factory=Defaults)


class StorageConfig(BaseModel):
    task_dir: str = "./tasks"
    keep_tasks: int = 7
    max_concurrent_tasks: int = 3


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    listen_host: str = "127.0.0.1"
    listen_port: int = 8080
    reload_debug: bool = False
    ffmpeg_path: str = ""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    subtitle: SubtitleConfig = Field(default_factory=SubtitleConfig)
    subtitle_style: SubtitleStyleConfig = Field(default_factory=SubtitleStyleConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    stock: StockConfig = Field(default_factory=StockConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    overlay: OverlayConfig = Field(default_factory=OverlayConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    facebook: FacebookConfig = Field(default_factory=FacebookConfig)
    templating: TemplatingConfig = Field(default_factory=TemplatingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from TOML file."""
    if config_path is None:
        config_path = Path("config.toml")
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return AppConfig(**data)


# Global config instance
config = load_config()
