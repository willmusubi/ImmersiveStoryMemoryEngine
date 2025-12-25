"""
Core 模块
"""
from .state_manager import apply_state_patch, apply_multiple_patches, _ensure_location_references

__all__ = [
    "apply_state_patch",
    "apply_multiple_patches",
    "_ensure_location_references",
]

