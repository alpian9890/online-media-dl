from __future__ import annotations

from typing import Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align

from .config_loader import load_config, save_local_config

console = Console()

def _prompt(options: dict[str, str], allow_back: bool = True) -> str:
    while True:
        choice = console.input("[bold]Pilih nomor[/]: ").strip().lower()
        if allow_back and choice in ("0", "b"):
            return "back"
        if choice in options:
            return choice
        if choice == "q":
            return "quit"
        console.print("[red]Input tidak valid.[/red]")

def _draw_header(title: str, breadcrumb: str = "Settings"):
    console.clear()
    console.rule(f"[bold cyan]{title}")
    console.print(Align.left(f"[dim]{breadcrumb}[/dim]"))

def _kv_table(items: dict[str, str], title: str = "Pengaturan Saat Ini") -> Table:
    t = Table(show_header=True, header_style="bold")
    t.add_column("Kunci")
    t.add_column("Nilai")
    for k, v in items.items():
        t.add_row(k, v)
    return Panel(t, title=title)

def show_settings_menu() -> None:
    while True:
        cfg = load_config()
        _draw_header("Online Media DL — Settings", "Settings")
        cur = {
            "filename_style": cfg.get("filename_style", "simple"),
            "video.quality": cfg.get("video", {}).get("quality", "auto"),
            "video.preset_resolution": cfg.get("video", {}).get("preset_resolution", "720p"),
            "video.prefer_codec": cfg.get("video", {}).get("prefer_codec", "h264+aac"),
            "video.allow_h265_for_videos": str(cfg.get("video", {}).get("allow_h265_for_videos", False)),
            "video.container": cfg.get("video", {}).get("container", "mp4"),
            "audio.format": cfg.get("audio", {}).get("format", "mp3"),
            "audio.bitrate_kbps": str(cfg.get("audio", {}).get("bitrate_kbps", "best")),
            "audio.prefer_better_audio": str(cfg.get("audio", {}).get("prefer_better_audio", True)),
            "output_dir": cfg.get("output_dir", ""),
        }
        console.print(_kv_table(cur))

        t = Table(title="Menu Settings", show_header=True, header_style="bold")
        t.add_column("No", style="cyan")
        t.add_column("Aksi")
        t.add_row("1", "Filename style")
        t.add_row("2", "Video")
        t.add_row("3", "Audio")
        t.add_row("4", "Output path")
        t.add_row("0", "Kembali")
        t.add_row("q", "Keluar")
        console.print(t)

        sel = _prompt({"1":"1","2":"2","3":"3","4":"4","0":"0","q":"q"}, allow_back=False)
        if sel in ("q", "quit"):
            break
        if sel == "0":
            break
        if sel == "1":
            _settings_filename_style()
        elif sel == "2":
            _settings_video()
        elif sel == "3":
            _settings_audio()
        elif sel == "4":
            _settings_output()

def _settings_filename_style():
    _draw_header("Online Media DL — Settings", "Settings › Filename style")
    t = Table(show_header=True, header_style="bold")
    t.add_column("No", style="cyan")
    t.add_column("Opsi")
    t.add_row("1", "simple (default)")
    t.add_row("2", "nerdy")
    t.add_row("0", "Kembali")
    t.add_row("q", "Keluar")
    console.print(t)
    sel = _prompt({"1":"1","2":"2","0":"0","q":"q"})
    if sel in ("back", "0"):
        return
    if sel == "quit":
        raise SystemExit(0)
    style = "simple" if sel == "1" else "nerdy"
    save_local_config({"filename_style": style})
    console.print("[green]Tersimpan.[/green]")

def _settings_video():
    while True:
        _draw_header("Online Media DL — Settings", "Settings › Video")
        t = Table(show_header=True, header_style="bold")
        t.add_column("No", style="cyan")
        t.add_column("Opsi")
        t.add_row("1", "Video quality (auto/best/preset/manual)")
        t.add_row("2", "Preset resolusi (1080p..144p)")
        t.add_row("3", "Prefer codec (h264+aac / av1+opus / vp9+opus)")
        t.add_row("4", "Allow H.265/HEVC (on/off)")
        t.add_row("5", "Container (mp4/webm/auto) – default mp4")
        t.add_row("0", "Kembali")
        t.add_row("q", "Keluar")
        console.print(t)
        sel = _prompt({str(i):str(i) for i in range(6)} | {"q":"q"})
        if sel in ("back","0"):
            return
        if sel == "quit":
            raise SystemExit(0)

        if sel == "1":
            _draw_header("Online Media DL — Settings", "Settings › Video › Quality")
            t2 = Table()
            t2.add_column("No", style="cyan")
            t2.add_column("Opsi")
            t2.add_row("1", "auto (default)")
            t2.add_row("2", "best")
            t2.add_row("3", "preset")
            t2.add_row("4", "manual (format yt-dlp)")
            t2.add_row("0", "Kembali")
            t2.add_row("q", "Keluar")
            console.print(t2)
            choice = _prompt({"1":"1","2":"2","3":"3","4":"4","0":"0","q":"q"})
            if choice in ("back","0"):
                continue
            if choice == "quit":
                raise SystemExit(0)
            mapping = {"1":"auto","2":"best","3":"preset","4":"manual"}
            save_local_config({"video":{"quality": mapping[choice]}})
            console.print("[green]Tersimpan.[/green]")
        elif sel == "2":
            _draw_header("Online Media DL — Settings", "Settings › Video › Preset Resolusi")
            console.print("Masukkan salah satu: 1080p, 720p, 480p, 360p, 240p, 144p")
            val = console.input("Resolusi: ").strip().lower()
            save_local_config({"video":{"preset_resolution": val}})
            console.print("[green]Tersimpan.[/green]")
        elif sel == "3":
            _draw_header("Online Media DL — Settings", "Settings › Video › Prefer Codec")
            t3 = Table()
            t3.add_column("No", style="cyan")
            t3.add_column("Opsi")
            t3.add_row("1", "h264+aac (default, kompatibel)")
            t3.add_row("2", "av1+opus")
            t3.add_row("3", "vp9+opus")
            t3.add_row("0", "Kembali")
            t3.add_row("q", "Keluar")
            console.print(t3)
            choice = _prompt({"1":"1","2":"2","3":"3","0":"0","q":"q"})
            if choice in ("back","0"):
                continue
            if choice == "quit":
                raise SystemExit(0)
            mapping = {"1":"h264+aac","2":"av1+opus","3":"vp9+opus"}
            save_local_config({"video":{"prefer_codec": mapping[choice]}})
            console.print("[green]Tersimpan.[/green]")
        elif sel == "4":
            _draw_header("Online Media DL — Settings", "Settings › Video › Allow H.265/HEVC")
            t4 = Table()
            t4.add_column("No", style="cyan")
            t4.add_column("Opsi")
            t4.add_row("1", "off (default)")
            t4.add_row("2", "on")
            t4.add_row("0", "Kembali")
            t4.add_row("q", "Keluar")
            console.print(t4)
            choice = _prompt({"1":"1","2":"2","0":"0","q":"q"})
            if choice in ("back","0"):
                continue
            if choice == "quit":
                raise SystemExit(0)
            save_local_config({"video":{"allow_h265_for_videos": choice=="2"}})
            console.print("[green]Tersimpan.[/green]")
        elif sel == "5":
            _draw_header("Online Media DL — Settings", "Settings › Video › Container")
            t5 = Table()
            t5.add_column("No", style="cyan")
            t5.add_column("Opsi")
            t5.add_row("1", "mp4 (default)")
            t5.add_row("2", "webm")
            t5.add_row("3", "auto (mengikuti prefer codec)")
            t5.add_row("0", "Kembali")
            t5.add_row("q", "Keluar")
            console.print(t5)
            choice = _prompt({"1":"1","2":"2","3":"3","0":"0","q":"q"})
            if choice in ("back","0"):
                continue
            if choice == "quit":
                raise SystemExit(0)
            mapping = {"1":"mp4","2":"webm","3":"auto"}
            save_local_config({"video":{"container": mapping[choice]}})
            console.print("[green]Tersimpan.[/green]")

def _settings_audio():
    while True:
        _draw_header("Online Media DL — Settings", "Settings › Audio")
        t = Table(show_header=True, header_style="bold")
        t.add_column("No", style="cyan")
        t.add_column("Opsi")
        t.add_row("1", "Audio format (best/mp3/ogg/wav/opus) – default mp3")
        t.add_row("2", "Bitrate kb/s (64-320) atau 'best' – default 'best'")
        t.add_row("3", "Prefer better quality (on/off)")
        t.add_row("0", "Kembali")
        t.add_row("q", "Keluar")
        console.print(t)
        sel = _prompt({str(i):str(i) for i in range(4)} | {"q":"q"})
        if sel in ("back","0"):
            return
        if sel == "quit":
            raise SystemExit(0)
        if sel == "1":
            _draw_header("Online Media DL — Settings", "Settings › Audio › Format")
            console.print("Masukkan: best | mp3 | ogg | wav | opus (default: mp3)")
            val = console.input("Format: ").strip().lower()
            if not val:
                val = "mp3"
            save_local_config({"audio":{"format": val}})
            console.print("[green]Tersimpan.[/green]")
        elif sel == "2":
            _draw_header("Online Media DL — Settings", "Settings › Audio › Bitrate")
            console.print("Masukkan angka 64-320 atau tulis 'best' (default 'best'→320 kb/s untuk lossy).")
            val = console.input("Bitrate: ").strip().lower()
            if not val:
                val = "best"
            save_local_config({"audio":{"bitrate_kbps": val}})
            console.print("[green]Tersimpan.[/green]")
        elif sel == "3":
            _draw_header("Online Media DL — Settings", "Settings › Audio › Prefer Better Quality")
            t2 = Table()
            t2.add_column("No", style="cyan")
            t2.add_column("Opsi")
            t2.add_row("1", "on (default)")
            t2.add_row("2", "off")
            t2.add_row("0", "Kembali")
            t2.add_row("q", "Keluar")
            console.print(t2)
            choice = _prompt({"1":"1","2":"2","0":"0","q":"q"})
            if choice in ("back","0"):
                continue
            if choice == "quit":
                raise SystemExit(0)
            save_local_config({"audio":{"prefer_better_audio": choice=="1"}})
            console.print("[green]Tersimpan.[/green]")

def _settings_output():
    _draw_header("Online Media DL — Settings", "Settings › Output path")
    console.print("Masukkan path tujuan (contoh: ~/Downloads/omdl).")
    val = console.input("Path: ").strip()
    if not val:
        console.print("[yellow]Dibatalkan.[/yellow]")
        return
    save_local_config({"output_dir": val})
    console.print("[green]Tersimpan.[/green]")
