from __future__ import annotations
import os

def build_outtmpl(output_dir: str, provider: str, filename_template: str) -> str:
    """
    Kembalikan path outtmpl seperti:
      downloads/youtube/%(uploader|channel|creator)s/%(title)s [%(id)s].%(ext)s
    yt-dlp akan membuat subdir otomatis.
    """
    subdir = os.path.join(output_dir, provider, "%(uploader|channel|creator|uploader_id)s")
    return os.path.join(subdir, filename_template)

def choose_filename_template(mode: str, style: str, cfg: dict) -> str:
    """Pilih template nama file berdasar mode (audio/auto) & style (simple/nerd)."""
    is_audio = (mode == "audio")
    if is_audio:
        if style == "simple":
            return cfg.get("filename_template_audio_simple") or cfg.get("filename_template_audio") or "%(title)s.%(ext)s"
        elif style == "nerd":
            return cfg.get("filename_template_audio_nerd") or cfg.get("filename_template_audio") or "%(title)s.%(ext)s"
        else:
            return cfg.get("filename_template_audio") or "%(title)s.%(ext)s"
    else:
        if style == "simple":
            return cfg.get("filename_template_video_simple") or cfg.get("filename_template_video") or "%(title)s.%(ext)s"
        elif style == "nerd":
            return cfg.get("filename_template_video_nerd") or cfg.get("filename_template_video") or "%(title)s.%(ext)s"
        else:
            return cfg.get("filename_template_video") or "%(title)s.%(ext)s"
