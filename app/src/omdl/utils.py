from __future__ import annotations
import os
import shutil
import re
from typing import Optional
from rich.console import Console

console = Console()

DOMAIN_PROVIDER_MAP = {
    # YouTube
    r"(?:^|//)youtu\.be/": "youtube",
    r"(?:^|//)(?:www\.)?youtube\.com/": "youtube",
    # Instagram
    r"(?:^|//)(?:www\.)?instagram\.com/": "instagram",
    # TikTok
    r"(?:^|//)(?:www\.)?tiktok\.com/": "tiktok",
    # Facebook
    r"(?:^|//)(?:www\.)?facebook\.com/": "facebook",
    r"(?:^|//)fb\.watch/": "facebook",
    # X/Twitter
    r"(?:^|//)(?:www\.)?twitter\.com/": "x",
    r"(?:^|//)(?:www\.)?x\.com/": "x",
}

_PROVIDER_STYLE = {
    "youtube": ("🟥 YOUTUBE", "red"),
    "instagram": ("🟣 INSTAGRAM", "magenta"),
    "tiktok": ("⬛ TIKTOK", "white"),
    "facebook": ("🟦 FACEBOOK", "blue"),
    "x": ("⬛ X / TWITTER", "white"),
}

def clear_screen() -> None:
    """Bersihkan layar terminal agar menu tampil single-screen."""
    try:
        console.clear()
    except Exception:
        os.system("cls" if os.name == "nt" else "clear")

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def validate_url(url: str) -> bool:
    return bool(url and "://" in url)

def detect_provider(url: str) -> Optional[str]:
    for pattern, provider in DOMAIN_PROVIDER_MAP.items():
        if re.search(pattern, url):
            return provider
    return None

def shorten_path(path: str, max_len: int = 90) -> str:
    """
    Potong path panjang di tengah agar tetap terbaca.
    contoh: /very/long/.../deep/file.ext -> /very/long/…/deep/file.ext
    """
    text = os.path.expanduser(path)
    if len(text) <= max_len:
        return text
    keep = max_len - 1
    left = keep // 2
    right = keep - left
    return text[:left] + "…" + text[-right:]

def _emoji_enabled() -> bool:
    # set OMDL_NO_EMOJI=1 untuk mematikan emoji
    return os.environ.get("OMDL_NO_EMOJI", "").lower() not in ("1","true","yes","y")

def provider_badge(provider: str) -> str:
    name, color = _PROVIDER_STYLE.get(provider, (provider.upper(), "cyan"))
    if not _emoji_enabled():
        # buang emoji di depan (format kita: "<emoji> NAMA")
        parts = name.split(" ", 1)
        if len(parts) == 2:
            name = parts[1]
    return f"[bold {color}]{name}[/bold {color}]"