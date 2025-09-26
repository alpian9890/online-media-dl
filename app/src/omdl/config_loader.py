from __future__ import annotations
import os
from typing import Any, Dict, Optional

import yaml

# ===== Default Configs (dapat dioverride di config/local.yaml) =====
DEFAULTS: Dict[str, Any] = {
    # Path
    "output_dir": "downloads",
    "log_dir": "logs",
    "cookies_dir": "cookies",

    # UI & Behavior
    "rich_progress": True,
    "restrict_filenames": False,
    "concurrent_fragment_downloads": 5,
    "socket_timeout": 30,

    # Filename templates (legacy)
    "filename_template_video": "%(title)s [%(id)s].%(ext)s",
    "filename_template_audio": "%(title)s [%(id)s].%(ext)s",

    # Filename templates (styling)
    "filename_template_video_simple": "%(title)s.%(ext)s",
    "filename_template_video_nerd": "%(title)s [%(id)s] [%(format_note|resolution)s].%(ext)s",
    "filename_template_audio_simple": "%(title)s.%(ext)s",
    "filename_template_audio_nerd": "%(title)s [%(id)s] [%(acodec)s %(abr|tbr)sKbps].%(ext)s",

    # Defaults
    # - video default mp4
    # - audio default mp3
    # - bitrate default "best" (mapping ke 320 kbps untuk mp3)
    "filename_style_video": "simple",  # simple|nerdy
    "filename_style_audio": "simple",  # simple|nerdy

    "video_quality_default": "auto",   # auto|best|preset|manual (manual hanya via CLI)
    "video_resolution_default": 720,   # 144,240,360,480,720,1080 (dipakai saat preset)
    "video_codec_pref": "h264",        # h264|vp9|av1
    "allow_h265": False,               # HEVC (kompatibilitas rendah)
    "merge_output_format": "mp4",      # auto|mp4|webm (default: mp4)

    "audio_format_default": "mp3",     # best|mp3|ogg|wav|opus (default: mp3)
    "audio_bitrate_default": "best",   # 64..320 atau "best" (map ke 320 untuk mp3)
    "audio_prefer_better": True,
    "embed_thumbnail": True,

    # Mode lama untuk kompatibilitas
    "default_mode": "auto",
    "default_quality": "auto",

    # Provider defaults saat quality=auto
    "provider_defaults": {
        "youtube": "bestvideo*+bestaudio/best",
        "instagram": "best",
        "tiktok": "best",
        "facebook": "best",
        "x": "best",
    },
}

def _read_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge rekursif dict -> dict (override menang)."""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def load_config(base_dir: str) -> Dict[str, Any]:
    """
    Baca config default.yaml lalu merge dengan local.yaml jika ada.
    """
    cfg_dir = os.path.join(base_dir, "config")
    default_path = os.path.join(cfg_dir, "default.yaml")
    local_path = os.path.join(cfg_dir, "local.yaml")

    cfg = dict(DEFAULTS)
    cfg = deep_merge(cfg, _read_yaml(default_path))
    cfg = deep_merge(cfg, _read_yaml(local_path))
    return cfg

def save_config(base_dir: str, patch: Dict[str, Any]) -> str:
    """
    Simpan perubahan user ke config/local.yaml.
    Mengembalikan path file yang ditulis.
    """
    cfg_dir = os.path.join(base_dir, "config")
    os.makedirs(cfg_dir, exist_ok=True)
    local_path = os.path.join(cfg_dir, "local.yaml")

    # baca local lama, merge, lalu tulis kembali
    local = _read_yaml(local_path)
    new_local = deep_merge(local, patch or {})

    with open(local_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(new_local, f, sort_keys=False, allow_unicode=True)
    return local_path

def load_provider_cfg(base_dir: str, provider: str) -> Dict[str, Any]:
    pdir = os.path.join(base_dir, "config", "providers")
    path = os.path.join(pdir, f"{provider}.yaml")
    return _read_yaml(path)
