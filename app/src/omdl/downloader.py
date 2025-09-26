from __future__ import annotations

import os
from collections import deque
from pathlib import Path
from typing import Dict, Any, Optional, List

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.text import Text
from rich.live import Live
from yt_dlp import YoutubeDL

console = Console()


def _pretty_panel(text: str, title: str = "", style: str = "cyan") -> Panel:
    return Panel.fit(text, title=title, border_style=style)


def _postprocessors_for_audio(codec: str, bitrate_pref: str, embed_thumbnail: bool) -> List[Dict[str, Any]]:
    """
    Bangun postprocessors untuk mode audio.
    - bitrate_pref: "best" atau angka string ("320","192","128",..., "64")
      "best" map ke 320 kbps.
    """
    kbps = "320" if str(bitrate_pref) == "best" else str(bitrate_pref)
    pp: List[Dict[str, Any]] = [
        {"key": "FFmpegExtractAudio", "preferredcodec": codec, "preferredquality": kbps}
    ]
    if embed_thumbnail:
        pp.append({"key": "EmbedThumbnail"})
    return pp


def _merge_output_format(codec_pref: str, cfg: Dict[str, Any]) -> Optional[str]:
    """
    Tentukan kontainer final.
    - Jika cfg['merge_output_format'] = 'auto':
        h264 -> mp4 ; vp9/av1 -> webm ; h265 -> mp4
    - Jika 'mp4'/'webm' → pakai itu.
    - Jika None → biarkan yt-dlp menentukan.
    """
    mo = (cfg.get("merge_output_format") or "").lower()
    if mo in ("mp4", "webm"):
        return mo
    if mo == "auto" or not mo:
        if codec_pref in ("vp9", "av1"):
            return "webm"
        return "mp4"
    return None


class RichYDLLogger:
    """
    Logger untuk yt-dlp → meneruskan pesan penting ke panel Log.
    """
    def __init__(self, log_fn, debug: bool = False):
        self._log = log_fn
        self._debug = debug

    def debug(self, msg):
        msg = str(msg)
        keywords = (
            "Extracting ", "Downloading ", "Writing ", "Destination",
            "m3u8", "player API", "tv client", "thumbnail", "format(s)"
        )
        if self._debug or any(k in msg for k in keywords):
            self._log(f"[dim]{msg}[/dim]")

    def info(self, msg):
        self._log(str(msg))

    def warning(self, msg):
        self._log(f"[yellow]{msg}[/yellow]")

    def error(self, msg):
        self._log(f"[red]{msg}[/red]")


def run_download(
    provider_name: str,
    provider_obj,
    url: str,
    mode: str,
    quality: str,
    outtmpl: str,
    cookies_path: Optional[str],
    audio_codec: Optional[str],
    audio_quality: Optional[str],
    embed_thumbnail: Optional[bool] = None,
) -> None:
    """
    Eksekusi unduhan menggunakan yt-dlp.
    - mode: 'auto' (video/media) atau 'audio'
    - quality: 'auto'|'best'|format-string (yt-dlp)
    """
    cfg = provider_obj.cfg

    # ===== Format =====
    format_string = provider_obj.select_format(mode, quality)

    # ===== Base options =====
    ydl_opts: Dict[str, Any] = provider_obj.ydl_base_opts()
    ydl_opts["outtmpl"] = outtmpl
    ydl_opts["format"] = format_string

    # ===== Kontainer =====
    vcodec_pref = (cfg.get("video_codec_pref") or "h264").lower()
    merge_to = _merge_output_format(vcodec_pref, cfg)
    if merge_to:
        ydl_opts["merge_output_format"] = merge_to

    # ===== Cookies =====
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    # ===== Audio postprocessors =====
    audio_codec_selected: Optional[str] = None
    if mode == "audio":
        audio_codec_selected = (audio_codec or cfg.get("audio_format_default") or "mp3").lower()
        aq = (audio_quality or cfg.get("audio_bitrate_default") or "best")
        emb = cfg.get("embed_thumbnail") if embed_thumbnail is None else embed_thumbnail
        ydl_opts["postprocessors"] = _postprocessors_for_audio(audio_codec_selected, str(aq), bool(emb))

    # ===== Kontrol output bawaan yt-dlp =====
    debug = os.environ.get("OMDL_DEBUG", "").lower() in ("1", "true", "yes", "y")
    ydl_opts["noprogress"] = True     # pakai progress kustom
    ydl_opts["quiet"] = True          # cegah stdout bawaan
    ydl_opts["no_warnings"] = not debug

    # ===== Progress bar =====
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("• {task.fields[speed]}"),
        TextColumn("• ETA {task.fields[eta]}"),
        TimeRemainingColumn(),
        refresh_per_second=8,
        transient=False,   # Live yang akan meng-clear
        console=console,
    )

    # ===== Log buffer (dirender dalam Panel, bukan print langsung) =====
    log_lines: deque[str] = deque(maxlen=200)

    def render_ui() -> Group:
        log_text = Text("\n".join(log_lines)) if log_lines else Text("Menunggu…")
        return Group(
            Panel(progress, title="Progres", border_style="cyan"),
            Panel(log_text, title="Log", border_style="magenta"),
        )

    # ===== State =====
    last_filename: Optional[str] = None
    final_path: Optional[str] = None
    pp_started_once: set[str] = set()
    pp_finished_once: set[str] = set()
    download_task_id: Optional[int] = None
    post_task_id: Optional[int] = None

    # ------ LOG APPENDER (tidak pernah print ke console saat Live aktif) ------
    live: Optional[Live] = None

    def log_line(msg: str):
        # Satu-satunya pintu masuk log
        log_lines.append(f"• {msg}")
        if live is not None:
            live.update(render_ui(), refresh=True)

    # Pasang logger ke yt-dlp
    ydl_opts["logger"] = RichYDLLogger(log_line, debug=debug)

    # ------ HOOKS ------
    def _progress_hook(d: Dict[str, Any]):
        nonlocal last_filename, download_task_id
        status = d.get("status")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed_str = (d.get("_speed_str") or "").strip() or "-"
            eta_str = (d.get("_eta_str") or "--:--").strip() or "--:--"

            if download_task_id is None:
                download_task_id = progress.add_task(
                    "Mengunduh",
                    total=total or 100,   # jika unknown, tetap render bar
                    speed=speed_str,
                    eta=eta_str,
                )
            if total:
                progress.update(download_task_id, total=total)
            progress.update(download_task_id, completed=downloaded, speed=speed_str, eta=eta_str)

        elif status == "finished":
            last_filename = d.get("filename", last_filename)

        elif status == "error":
            log_line("[red]Terjadi kesalahan saat mengunduh.[/red]")

    def _postprocessor_hook(d: Dict[str, Any]):
        nonlocal final_path, post_task_id
        st = d.get("status")
        pp = str(d.get("postprocessor") or "Post-Processing")
        info = d.get("info_dict") or {}
        base = last_filename or info.get("filepath") or info.get("_filename") or ""

        if post_task_id is None:
            post_task_id = progress.add_task(
                "Post-processing",
                total=None,
                speed="-",
                eta="--:--",
            )

        if st == "started":
            if pp not in pp_started_once:
                pp_started_once.add(pp)
                log_line(f"[cyan]↻ {pp}[/cyan] [dim]{base}[/dim]")

        elif st == "finished":
            if pp not in pp_finished_once:
                pp_finished_once.add(pp)
                cand = info.get("filepath") or info.get("_filename")
                if cand:
                    final_path = cand
                # Opsional: beri tanda selesai per-PP
                log_line(f"[green]✓ {pp} selesai[/green]")
                 

    # Pasang hooks
    ydl_opts["progress_hooks"] = [_progress_hook]
    ydl_opts["postprocessor_hooks"] = [_postprocessor_hook]

    # Panel "memulai" (sebelum Live)
    console.print(_pretty_panel("Memulai unduhan…", style="cyan"))

    # Provider extra
    ydl_opts = provider_obj.apply_provider_extra(ydl_opts)

    # ==== Jalankan dengan Live layout (Progress + Log terpadu) ====
    # Penting: tidak ada console.print di dalam blok Live.
    with Live(render_ui(), console=console, refresh_per_second=10, transient=True) as _live:
        live = _live
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        live = None  # hentikan update manual setelah keluar

    # Tentukan path akhir (fallback ke last_filename)
    if not final_path:
        if mode == "audio" and last_filename and audio_codec_selected:
            try:
                final_path = str(Path(last_filename).with_suffix(f".{audio_codec_selected}"))
            except Exception:
                final_path = last_filename
        else:
            final_path = last_filename or "-"

    # Panel keberhasilan akhir — dicetak sekali saja di luar Live
    console.print(
        _pretty_panel(
            f"[bold green]✔ Berhasil[/bold green]\nDisimpan ke:\n[white]{final_path}[/white]",
            title="Selesai",
            style="green",
        )
    )
