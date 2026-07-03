"""File security utilities."""

import os
from pathlib import Path
from typing import Optional


def resolve_path_within_directory(
    directory: str,
    requested_path: str,
) -> str:
    """Resolve a path within a directory, ensuring it stays inside."""
    directory = Path(directory).resolve()
    target = (directory / requested_path).resolve()
    
    try:
        target.relative_to(directory)
    except ValueError:
        raise ValueError(f"Path {target} is outside base directory {directory}")
    
    return str(target)


def is_safe_path(base: str, test_path: str) -> bool:
    """Check if test_path is within base directory."""
    try:
        base_resolved = Path(base).resolve()
        test_resolved = Path(test_path).resolve()
        return base_resolved in test_resolved.parents or base_resolved == test_resolved
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filename."""
    # Remove path separators and other dangerous characters
    unsafe = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
    for char in unsafe:
        filename = filename.replace(char, '_')
    return filename