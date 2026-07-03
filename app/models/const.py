"""Constants used across the application."""

from enum import Enum


class TaskState(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    PAUSED = "paused"  # waiting for user images


class PipelineStage(str, Enum):
    SCRIPT = "script"
    TERMS = "terms"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    MATERIALS = "materials"
    VIDEO = "video"


class LLMProvider(str, Enum):
    NINEROUTER = "9router"
    OPENAI = "openai"
    GOOGLE = "google"
    GROQ = "groq"
    OLLAMA = "ollama"


class TTSProvider(str, Enum):
    EDGE = "edge"
    AZURE_V2 = "azure_v2"
    ELEVENLABS = "elevenlabs"
    COQUI = "coqui"


class SubtitleProvider(str, Enum):
    WHISPER = "whisper"
    EDGE = "edge"


class ImageProvider(str, Enum):
    NONE = "none"
    GOOGLEFLOW = "googleflow"
    POLLINATIONS = "pollinations"
    SD_LOCAL = "sd_local"


# File extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}

# Default paths
DEFAULT_TASK_DIR = "./tasks"
DEFAULT_TEMPLATE_DIR = "./templates"
DEFAULT_STYLE_DIR = "./styles"
DEFAULT_RESOURCE_DIR = "./resource"

# Template file names
DEFAULT_SCRIPT_TEMPLATE = "default.md"
DEFAULT_PROMPT_TEMPLATE = "default.txt"

# Timeouts (seconds)
LLM_TIMEOUT = 60
TTS_TIMEOUT = 30
VIDEO_DOWNLOAD_TIMEOUT = 30
VIDEO_PROCESSING_TIMEOUT = 300

# Limits
MAX_SCRIPT_LENGTH = 5000  # characters
MAX_PROMPTS_PER_SCRIPT = 20
MAX_IMAGE_SIZE_MB = 10
MAX_VIDEO_DURATION = 300  # seconds (5 minutes)
MAX_CONCURRENT_TASKS = 3

# Status messages
STATUS_MESSAGES = {
    TaskState.PENDING: "Task is pending",
    TaskState.PROCESSING: "Task is in progress",
    TaskState.COMPLETE: "Task completed successfully",
    TaskState.FAILED: "Task failed",
    TaskState.PAUSED: "Waiting for user images",
}
