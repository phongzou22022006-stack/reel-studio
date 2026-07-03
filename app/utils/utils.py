import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger


def get_uuid() -> str:
    """Generate a unique task ID."""
    return str(uuid.uuid4())[:8]


def get_current_time() -> str:
    """Return current time in ISO format."""
    return datetime.now().isoformat()


def to_json(data: Any, indent: int = 2, ensure_ascii: bool = False) -> str:
    """Convert object to JSON string."""
    return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)


def from_json(json_str: str) -> Any:
    """Parse JSON string."""
    return json.loads(json_str)


def root_dir() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


def task_dir(task_id: str) -> Path:
    """Get task directory path."""
    from app.config import config

    task_root = Path(config.storage.task_dir)
    task_root.mkdir(parents=True, exist_ok=True)
    return task_root / task_id


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_dir(path: Union[str, Path]) -> Path:
    """Clean directory (remove all contents)."""
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_safe_path(base: Path, test_path: Path) -> bool:
    """Check if test_path is within base directory (security check)."""
    try:
        base_resolved = base.resolve()
        test_resolved = test_path.resolve()
        return base_resolved in test_resolved.parents or base_resolved == test_resolved
    except Exception:
        return False


def resolve_within_base(base: Path, subpath: str) -> Path:
    """Resolve a subpath within a base directory, ensuring it stays inside."""
    base = base.resolve()
    target = (base / subpath).resolve()
    if not is_safe_path(base, target):
        raise ValueError(f"Path {target} is outside base directory {base}")
    return target


def run_command(
    cmd: Union[str, List[str]],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run shell command with error handling."""
    logger.debug(f"Running command: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if check and result.returncode != 0:
            logger.error(f"Command failed: {cmd}")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )
        return result
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timeout: {cmd}")
        raise
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        raise


def get_ffmpeg_path() -> Optional[str]:
    """Get ffmpeg executable path."""
    from app.config import config

    if config.app.ffmpeg_path:
        return config.app.ffmpeg_path

    # Try to find ffmpeg in PATH
    for cmd in ["ffmpeg", "ffmpeg.exe"]:
        try:
            result = run_command([cmd, "-version"], check=False, timeout=5)
            if result.returncode == 0:
                return cmd
        except Exception:
            continue

    logger.warning("ffmpeg not found in PATH")
    return None


def get_file_size(path: Union[str, Path]) -> int:
    """Get file size in bytes."""
    return Path(path).stat().st_size


def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def format_duration(seconds: float) -> str:
    """Format duration to MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def read_lines(file_path: Union[str, Path]) -> List[str]:
    """Read all lines from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def write_lines(file_path: Union[str, Path], lines: List[str]) -> None:
    """Write lines to a file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def read_text(file_path: Union[str, Path]) -> str:
    """Read entire text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(file_path: Union[str, Path], content: str) -> None:
    """Write text to a file."""
    ensure_dir(Path(file_path).parent)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """Copy file with parent directory creation."""
    dst_path = Path(dst)
    ensure_dir(dst_path.parent)
    shutil.copy2(src, dst)


def move_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """Move file with parent directory creation."""
    dst_path = Path(dst)
    ensure_dir(dst_path.parent)
    shutil.move(src, dst)


def list_files(
    directory: Union[str, Path],
    extensions: Optional[List[str]] = None,
    recursive: bool = False,
) -> List[Path]:
    """List files in directory with optional filtering."""
    directory = Path(directory)
    if not directory.exists():
        return []

    if recursive:
        files = list(directory.rglob("*"))
    else:
        files = list(directory.iterdir())

    files = [f for f in files if f.is_file()]
    if extensions:
        files = [f for f in files if f.suffix.lower() in extensions]
    return sorted(files)


def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load YAML file."""
    import yaml

    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(file_path: Union[str, Path], data: Dict[str, Any]) -> None:
    """Save data to YAML file."""
    import yaml

    ensure_dir(Path(file_path).parent)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_template(template_name: str, template_type: str = "script") -> Optional[str]:
    """Load a template from templates directory."""
    from app.config import config

    templates_dir = root_dir() / "templates" / f"{template_type}s"
    template_path = templates_dir / f"{template_name}.md"

    if not template_path.exists():
        # Try .txt for prompt templates
        template_path = templates_dir / f"{template_name}.txt"

    if not template_path.exists():
        logger.warning(f"Template not found: {template_name} ({template_type})")
        return None

    return read_text(template_path)


def save_task_metadata(task_id: str, metadata: Dict[str, Any]) -> None:
    """Save task metadata to JSON file."""
    metadata_file = task_dir(task_id) / "metadata.json"
    write_text(metadata_file, to_json(metadata))


def load_task_metadata(task_id: str) -> Dict[str, Any]:
    """Load task metadata from JSON file."""
    metadata_file = task_dir(task_id) / "metadata.json"
    if not metadata_file.exists():
        return {}
    return from_json(read_text(metadata_file))


def validate_image_file(path: Union[str, Path]) -> bool:
    """Validate image file."""
    from app.models.const import IMAGE_EXTENSIONS

    path = Path(path)
    if not path.exists():
        return False
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    if get_file_size(path) > 10 * 1024 * 1024:  # 10MB
        return False
    return True


def validate_video_file(path: Union[str, Path]) -> bool:
    """Validate video file."""
    from app.models.const import VIDEO_EXTENSIONS

    path = Path(path)
    if not path.exists():
        return False
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        return False
    return True
