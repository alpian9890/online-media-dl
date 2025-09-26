from __future__ import annotations
from typing import Dict, Any

class BaseProvider:
    name: str = "base"

    def __init__(self, cfg: Dict[str, Any], provider_cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self.provider_cfg = provider_cfg or {}

    # ===== Format selection =====
    def select_format(self, mode: str, quality: str) -> str:
        """
        mode: 'auto' (media asli video/foto) atau 'audio'
        quality:
          - 'auto'  -> gunakan default per provider
          - 'best'  -> bestvideo*+bestaudio/best (video) atau bestaudio/best (audio)
          - string  -> format yt-dlp eksplisit, gunakan apa adanya
        """
        if quality and quality not in ("auto", "best"):
            return quality  # eksplisit dari user/menu

        if mode == "audio":
            if quality == "best":
                return self.provider_cfg.get("format_audio") or "bestaudio/best"
            # auto
            return self.provider_cfg.get("format_audio") or "bestaudio/best"

        # mode auto (video/media)
        if quality == "best":
            return "bestvideo*+bestaudio/best"
        # auto → dari provider defaults atau config global
        return (
            self.provider_cfg.get("format_video")
            or self.cfg.get("provider_defaults", {}).get(self.name, "best")
        )

    # ===== ydl options base =====
    def ydl_base_opts(self) -> Dict[str, Any]:
        return {
            "restrictfilenames": bool(self.cfg.get("restrict_filenames", False)),
            "concurrent_fragment_downloads": int(self.cfg.get("concurrent_fragment_downloads", 5)),
            "socket_timeout": int(self.cfg.get("socket_timeout", 30)),
            "quiet": False,
            "no_warnings": False,
        }

    def apply_provider_extra(self, ydl_opts: Dict[str, Any]) -> Dict[str, Any]:
        extra = self.provider_cfg.get("extra") or {}
        ydl_opts.update(extra)
        return ydl_opts
