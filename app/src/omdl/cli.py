from __future__ import annotations

import os
from typing import Optional, Dict

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich import print as rprint
from rich import box

from .config_loader import load_config, load_provider_cfg
from .providers import PROVIDER_CLASS_MAP
from .downloader import run_download
from .output import build_outtmpl, choose_filename_template
from .utils import check_ffmpeg, detect_provider, shorten_path, provider_badge

app = typer.Typer(help="Online Media Downloader (yt-dlp wrapper)")
console = Console()


VIDEO_PRESETS: Dict[str, str] = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "240p":  "bestvideo[height<=240]+bestaudio/best[height<=240]",
    "144p":  "bestvideo[height<=144]+bestaudio/best[height<=144]",
}

AUDIO_PRESETS: Dict[str, str] = {
    "320": "320",
    "192": "192",
    "128": "128",
}

VALID_MODES = {"auto", "audio"}

def _get_provider(provider_name: str, cfg: dict):
    provider_cfg = load_provider_cfg(os.getcwd(), provider_name)
    klass = PROVIDER_CLASS_MAP[provider_name]
    return klass(cfg, provider_cfg)

def _resolve_cookies(cfg: dict, provider: str) -> Optional[str]:
    cdir = cfg.get("cookies_dir", "cookies")
    path = os.path.join(os.getcwd(), cdir, f"{provider}.txt")
    return path if os.path.exists(path) else None

def _apply_presets_for_cli(mode: str,
                           preset: Optional[str],
                           quality: Optional[str],
                           audio_quality_cfg: str) -> tuple[str, Optional[str]]:
    """
    Kembalikan (format_string, audio_quality_override).
    - mode 'audio': preset 320/192/128 → audio_quality_override; format_string 'bestaudio/best' bila quality=auto.
    - mode 'auto' : preset resolusi → format_string.
    """
    fmt = quality or "auto"
    aq_override: Optional[str] = None

    if mode == "audio":
        if preset:
            key = preset.strip().replace("kbps","").replace("Kbps","").replace("k","")
            if key in AUDIO_PRESETS:
                aq_override = AUDIO_PRESETS[key]
                if fmt in ("auto", None):
                    fmt = "bestaudio/best"
        else:
            if fmt in ("auto", None):
                fmt = "bestaudio/best"
    else:
        if preset:
            p = preset.strip().lower()
            if p in VIDEO_PRESETS:
                fmt = VIDEO_PRESETS[p]

    return fmt, aq_override

def _summary_panel(url: str, provider: str, mode: str, fmt: str, audio_quality: str, style: str, outtmpl: str) -> Panel:
    tbl = Table.grid(padding=(0,1))
    tbl.add_column(justify="right", style="dim")
    tbl.add_column()
    tbl.add_row("URL", f"[link={url}]{url}[/link]")
    tbl.add_row("Provider", provider_badge(provider))
    tbl.add_row("Mode", f"{mode}")
    tbl.add_row("Quality", f"{fmt}")
    tbl.add_row("Audio bitrate", f"{audio_quality}")
    tbl.add_row("Filename style", f"{style}")
    tbl.add_row("Output", f"[dim]{shorten_path(outtmpl, 88)}[/dim]")
    return Panel(tbl, title="Ringkasan", border_style="cyan", box=box.ROUNDED)


def _do_download(provider: str,
                 url: str,
                 mode: str,
                 quality: Optional[str],
                 output: Optional[str],
                 filename_template_cli: Optional[str],
                 cookies: Optional[str],
                 audio_codec: Optional[str],
                 audio_quality: Optional[str],
                 embed_thumbnail: Optional[bool],
                 name_style: Optional[str],
                 preset: Optional[str]) -> None:

    if mode not in VALID_MODES:
        raise typer.BadParameter("Mode harus 'auto' atau 'audio'.")

    base_dir = os.getcwd()
    cfg = load_config(base_dir)

    if not check_ffmpeg():
        rprint(Panel.fit("[red]ffmpeg tidak ditemukan. Install ffmpeg terlebih dahulu.[/red]"))
        raise typer.Exit(code=1)

    provider_obj = _get_provider(provider, cfg)
    cookies_path = cookies or _resolve_cookies(cfg, provider)

    # filename template
    style = (name_style or (cfg.get("filename_style_audio") if mode == "audio" else cfg.get("filename_style_video")) or "simple")
    template = filename_template_cli or choose_filename_template(mode, style, cfg)

    outdir = output or cfg.get("output_dir", "downloads")
    outtmpl = build_outtmpl(outdir, provider, template)

    # preset/quality handling
    fmt, aq_override = _apply_presets_for_cli(mode, preset, quality, cfg.get("audio_bitrate_default", "best"))
    aq_final = audio_quality or aq_override or cfg.get("audio_bitrate_default", "best")

    # Tampilkan ringkasan yang rapi sebelum mulai
    rprint(_summary_panel(url, provider, mode, fmt, aq_final, style, outtmpl))
    if not Confirm.ask("Lanjutkan unduh?", default=True):
        raise typer.Exit(code=0)
        
    console.rule(provider_badge(provider), style="cyan")


    run_download(
        provider_name=provider,
        provider_obj=provider_obj,
        url=url,
        mode=mode,
        quality=fmt,
        outtmpl=outtmpl,
        cookies_path=cookies_path,
        audio_codec=audio_codec,
        audio_quality=aq_final,
        embed_thumbnail=embed_thumbnail,
    )

@app.command("menu")
def menu_cmd():
    """Tampilkan menu interaktif angka dan langsung unduh."""
    from .menu import interactive_menu
    interactive_menu()

@app.command("settings")
def settings_cmd():
    """Buka halaman Settings interaktif."""
    from .menu import settings_menu
    settings_menu()

@app.command("dl")
def dl(
    url: str = typer.Argument(..., help="URL konten"),
    mode: str = typer.Option("auto", "--mode", help="auto|audio"),
    quality: Optional[str] = typer.Option(None, "--quality", help="auto|best|<format yt-dlp>"),
    preset: Optional[str] = typer.Option(None, "--preset", help="Preset kualitas: 1080p|720p|480p|360p|240p|144p|320|192|128"),
    output: Optional[str] = typer.Option(None, "--output", help="Folder output"),
    filename_template: Optional[str] = typer.Option(None, "--filename-template", help="Template nama file yt-dlp"),
    cookies: Optional[str] = typer.Option(None, "--cookies", help="Path cookies.txt (prioritas tertinggi)"),
    audio_codec: Optional[str] = typer.Option(None, "--audio-codec", help="Codec audio (default dari config)"),
    audio_quality: Optional[str] = typer.Option(None, "--audio-quality", help="Kbps untuk ekstraksi audio"),
    embed_thumbnail: Optional[bool] = typer.Option(None, "--embed-thumbnail/--no-embed-thumbnail", help="Embed thumbnail ke audio"),
    name_style: Optional[str] = typer.Option(None, "--name-style", help="simple|nerd"),
):
    """Deteksi provider dari URL lalu unduh."""
    provider = detect_provider(url)
    if not provider:
        raise typer.BadParameter("Gagal mendeteksi provider dari URL.")
    _do_download(provider, url, mode, quality, output, filename_template, cookies,
                 audio_codec, audio_quality, embed_thumbnail, name_style, preset)

def _provider_cmd(provider_name: str):
    def _cmd(
        url: str = typer.Argument(..., help=f"URL konten {provider_name}"),
        mode: str = typer.Option("auto", "--mode", help="auto|audio"),
        quality: Optional[str] = typer.Option(None, "--quality", help="auto|best|<format yt-dlp>"),
        preset: Optional[str] = typer.Option(None, "--preset", help="Preset kualitas video/audio"),
        output: Optional[str] = typer.Option(None, "--output", help="Folder output"),
        filename_template: Optional[str] = typer.Option(None, "--filename-template", help="Template nama file"),
        cookies: Optional[str] = typer.Option(None, "--cookies", help="Path cookies.txt"),
        audio_codec: Optional[str] = typer.Option(None, "--audio-codec", help="Codec audio (default dari config)"),
        audio_quality: Optional[str] = typer.Option(None, "--audio-quality", help="Kbps untuk ekstraksi audio"),
        embed_thumbnail: Optional[bool] = typer.Option(None, "--embed-thumbnail/--no-embed-thumbnail", help="Embed thumbnail ke audio"),
        name_style: Optional[str] = typer.Option(None, "--name-style", help="simple|nerd"),
    ):
        _do_download(provider_name, url, mode, quality, output, filename_template, cookies,
                     audio_codec, audio_quality, embed_thumbnail, name_style, preset)
    return _cmd

app.command("youtube")(_provider_cmd("youtube"))
app.command("instagram")(_provider_cmd("instagram"))
app.command("ig")(_provider_cmd("instagram"))
app.command("tiktok")(_provider_cmd("tiktok"))
app.command("facebook")(_provider_cmd("facebook"))
app.command("x")(_provider_cmd("x"))

def main():
    app()

if __name__ == "__main__":
    main()
