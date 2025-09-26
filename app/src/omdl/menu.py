from __future__ import annotations
import os
from typing import Optional, Dict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

from .utils import validate_url, check_ffmpeg, clear_screen, detect_provider, ensure_dir, shorten_path, provider_badge
from .config_loader import load_config, load_provider_cfg, save_config
from .providers import PROVIDER_CLASS_MAP
from .output import build_outtmpl, choose_filename_template
from .downloader import run_download
import sys, shutil, subprocess, yaml


console = Console()

VIDEO_PRESETS: Dict[str, str] = {
    "1": "1080p",
    "2": "720p",
    "3": "480p",
    "4": "360p",
    "5": "240p",
    "6": "144p",
}
VIDEO_PRESET_TO_FORMAT: Dict[str, str] = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "240p":  "bestvideo[height<=240]+bestaudio/best[height<=240]",
    "144p":  "bestvideo[height<=144]+bestaudio/best[height<=144]",
}
AUDIO_PRESETS: Dict[str, str] = {
    "1": "320",
    "2": "192",
    "3": "128",
}

def _table(title: str, data: Dict[str, str], footer: Optional[str] = None) -> None:
    table = Table(title=title, show_header=True, header_style="bold cyan", expand=True, box=box.ROUNDED)
    table.add_column("No", style="magenta", justify="center", width=4)
    table.add_column("Opsi", style="white")
    for k, v in data.items():
        table.add_row(k, v)
    if footer:
        table.caption = f"[dim]{footer}[/dim]"
    console.print(table)

def _choose(title: str, data: Dict[str, str], default_key: Optional[str] = None, allow_back=True) -> Optional[str]:
    clear_screen()
    _table(f"📋 {title}", data, footer="0 = Kembali • q = Keluar" if allow_back else None)
    while True:
        raw = Prompt.ask("Pilih")
        if allow_back and raw == "0":
            return None
        if raw.lower() == "q":
            raise SystemExit(0)
        if raw in data:
            return raw
        console.print("[yellow]Input tidak valid.[/yellow]")

def _get_provider(provider_name: str, cfg: dict):
    provider_cfg = load_provider_cfg(os.getcwd(), provider_name)
    klass = PROVIDER_CLASS_MAP[provider_name]
    return klass(cfg, provider_cfg)

def _resolve_cookies(cfg: dict, provider: str) -> Optional[str]:
    cdir = cfg.get("cookies_dir", "cookies")
    path = os.path.join(os.getcwd(), cdir, f"{provider}.txt")
    return path if os.path.exists(path) else None

def _settings_filename_style(cfg: dict) -> None:
    while True:
        clear_screen()
        console.rule("[b]Settings • Filename style[/b]")
        console.print(f"Sekarang: video=[bold]{cfg.get('filename_style_video','simple')}[/bold], audio=[bold]{cfg.get('filename_style_audio','simple')}[/bold]")
        key = _choose("Pilih style", {"1": "Video: simple", "2": "Video: nerd", "3": "Audio: simple", "4": "Audio: nerd"}, allow_back=True)
        if key is None:
            return
        patch = {}
        if key == "1":
            patch["filename_style_video"] = "simple"
        elif key == "2":
            patch["filename_style_video"] = "nerd"
        elif key == "3":
            patch["filename_style_audio"] = "simple"
        elif key == "4":
            patch["filename_style_audio"] = "nerd"
        save_config(os.getcwd(), patch)
        cfg.update(patch)

def _settings_video(cfg: dict) -> None:
    while True:
        clear_screen()
        console.rule("[b]Settings • Video[/b]")
        console.print(
            f"Quality=[bold]{cfg.get('video_quality_default')}[/bold], "
            f"Resolution=[bold]{cfg.get('video_resolution_default')}p[/bold], "
            f"Codec=[bold]{cfg.get('video_codec_pref')}[/bold], "
            f"HEVC=[bold]{'on' if cfg.get('allow_h265') else 'off'}[/bold], "
            f"Container=[bold]{cfg.get('merge_output_format','mp4')}[/bold]"
        )
        key = _choose("Pilih opsi", {
            "1": "Quality default (auto/best/preset)",
            "2": "Preset resolusi (144–1080p)",
            "3": "Codec preferensi (h264/av1/vp9)",
            "4": "High efficiency (HEVC/H.265) on/off",
            "5": "Container (auto/mp4/webm)",
        }, allow_back=True)
        if key is None:
            return
        if key == "1":
            val = Prompt.ask("Masukkan: auto|best|preset", default=str(cfg.get("video_quality_default","auto")))
            if val not in ("auto","best","preset"):
                console.print("[yellow]Nilai tidak valid[/yellow]"); continue
            save_config(os.getcwd(), {"video_quality_default": val}); cfg["video_quality_default"] = val
        elif key == "2":
            val = Prompt.ask("Resolusi (144|240|360|480|720|1080)", default=str(cfg.get("video_resolution_default",720)))
            try:
                ival = int(val)
                if ival not in (144,240,360,480,720,1080):
                    raise ValueError
            except Exception:
                console.print("[yellow]Nilai tidak valid[/yellow]"); continue
            save_config(os.getcwd(), {"video_resolution_default": ival}); cfg["video_resolution_default"] = val
        elif key == "3":
            val = Prompt.ask("Codec (h264|av1|vp9)", default=str(cfg.get("video_codec_pref","h264")))
            if val not in ("h264","av1","vp9"):
                console.print("[yellow]Nilai tidak valid[/yellow]"); continue
            save_config(os.getcwd(), {"video_codec_pref": val}); cfg["video_codec_pref"] = val
        elif key == "4":
            val = Prompt.ask("allow_h265? (on/off)", default="on" if cfg.get("allow_h265") else "off")
            b = (val.lower() in ("on","true","1","yes","y"))
            save_config(os.getcwd(), {"allow_h265": b}); cfg["allow_h265"] = b
        elif key == "5":
            val = Prompt.ask("Container (auto|mp4|webm)", default=str(cfg.get("merge_output_format","mp4")))
            if val not in ("auto","mp4","webm"):
                console.print("[yellow]Nilai tidak valid[/yellow]"); continue
            save_config(os.getcwd(), {"merge_output_format": val}); cfg["merge_output_format"] = val

def _settings_audio(cfg: dict) -> None:
    while True:
        clear_screen()
        console.rule("[b]Settings • Audio[/b]")
        console.print(
            f"Format=[bold]{cfg.get('audio_format_default')}[/bold], "
            f"Bitrate=[bold]{cfg.get('audio_bitrate_default')}[/bold], "
            f"Prefer better=[bold]{'on' if cfg.get('audio_prefer_better') else 'off'}[/bold], "
            f"Embed thumbnail=[bold]{'on' if cfg.get('embed_thumbnail') else 'off'}[/bold]"
        )
        key = _choose("Pilih opsi", {
            "1": "Format (best/mp3/ogg/wav/opus)",
            "2": "Bitrate (best/64–320)",
            "3": "Prefer better (on/off)",
            "4": "Embed thumbnail (on/off)",
        }, allow_back=True)
        if key is None:
            return
        if key == "1":
            val = Prompt.ask("Audio format", default=str(cfg.get("audio_format_default","mp3")))
            if val not in ("best","mp3","ogg","wav","opus"):
                console.print("[yellow]Nilai tidak valid[/yellow]"); continue
            save_config(os.getcwd(), {"audio_format_default": val}); cfg["audio_format_default"] = val
        elif key == "2":
            val = Prompt.ask("Bitrate (best atau angka 64–320)", default=str(cfg.get("audio_bitrate_default","best")))
            if val != "best":
                try:
                    ival = int(val)
                    if ival < 64 or ival > 320:
                        raise ValueError
                except Exception:
                    console.print("[yellow]Nilai tidak valid[/yellow]"); continue
            save_config(os.getcwd(), {"audio_bitrate_default": val}); cfg["audio_bitrate_default"] = val
        elif key == "3":
            val = Prompt.ask("Prefer better? (on/off)", default="on" if cfg.get("audio_prefer_better") else "off")
            b = (val.lower() in ("on","true","1","yes","y"))
            save_config(os.getcwd(), {"audio_prefer_better": b}); cfg["audio_prefer_better"] = b
        elif key == "4":
            val = Prompt.ask("Embed thumbnail? (on/off)", default="on" if cfg.get("embed_thumbnail") else "off")
            b = (val.lower() in ("on","true","1","yes","y"))
            save_config(os.getcwd(), {"embed_thumbnail": b}); cfg["embed_thumbnail"] = b

def _settings_output(cfg: dict) -> None:
    while True:
        clear_screen()
        console.rule("[b]Settings • Output path[/b]")
        console.print(f"Sekarang: [bold]{cfg.get('output_dir')}[/bold]")
        key = _choose("Aksi", {"1": "Ubah folder output"}, allow_back=True)
        if key is None:
            return
        if key == "1":
            path = Prompt.ask("Masukkan path folder (contoh: ~/Downloads/omdl)", default=cfg.get("output_dir","downloads"))
            path = os.path.expanduser(path)
            try:
                ensure_dir(path)
            except Exception as e:
                console.print(f"[red]Gagal membuat folder: {e}[/red]"); continue
            save_config(os.getcwd(), {"output_dir": path}); cfg["output_dir"] = path
            console.print(Panel.fit(f"Output path diubah ke [bold]{path}[/bold]", style="green"))
            Prompt.ask("Enter untuk lanjut")
            
def _ensure_batch_file(base_dir: str) -> str:
    """
    Pastikan file batch_downloads.yaml ada di root project.
    Jika belum ada, buat dengan template yang menyertakan komentar dan contoh URL.
    """
    path = os.path.join(base_dir, "batch_downloads.yaml")
    if os.path.exists(path):
        return path

    template_text = (
        "# Online Media Downloader — Batch file\n"
        "#\n"
        "# Cara pakai:\n"
        "# 1) Pilih 'mode':\n"
        "#    - auto  : download media asli (original) sesuai sumber\n"
        "#    - audio : ekstrak audio saja (mis. untuk YouTube -> MP3/format audio lainnya)\n"
        "# 2) Pilih 'quality':\n"
        "#    - Untuk mode auto : 'auto' (biarkan yt-dlp memilih terbaik) atau format-string yt-dlp\n"
        "#      Contoh format-string (video <=1080p): bestvideo[height<=1080]+bestaudio/best\n"
        "#    - Untuk mode audio: 'best' atau 'bestaudio/best' (default akan dinormalisasi ke 'bestaudio/best')\n"
        "# 3) Tambahkan URL di bawah 'urls:' satu baris per URL (gunakan tanda ' - ').\n"
        "#\n"
        "\n"
        "\n"
        "mode: auto        # auto | audio\n"
        "quality: auto     # 'auto' | 'best' | format-string yt-dlp\n"
        "\n"
        "urls:\n"
        "  - https://youtu.be/xxxxxxxxxxx\n"
        "  - https://facebook.com/xxxxxx\n"
        "  - https://tiktok.com/xxxxxxxxx\n"
        ""
    )

    # Tulis file dengan konten template (mempertahankan komentar)
    with open(path, "w", encoding="utf-8") as f:
        f.write(template_text)

    return path

def _open_file_external(path: str) -> bool:
    """
    Buka file menggunakan aplikasi eksternal:
    - Termux: termux-open (butuh paket termux-api & aplikasi Termux:API)
    - Linux: xdg-open
    - macOS: open
    - Windows: start (os.startfile)
    """
    try:
        if shutil.which("termux-open"):
            subprocess.run(["termux-open", path], check=False)
            return True
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
            return True
        if shutil.which("xdg-open"):
            subprocess.run(["xdg-open", path], check=False)
            return True
        if shutil.which("open"):
            subprocess.run(["open", path], check=False)
            return True
    except Exception:
        pass
    console.print(Panel.fit(f"Tidak bisa membuka file secara eksternal.\nLokasi: [bold]{path}[/bold]", style="yellow"))
    return False

def _read_batch_file(path: str) -> tuple[list[str], str, str]:
    """
    Kembalikan (urls, mode, quality) dari file YAML.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return [], "auto", "auto"
    urls = data.get("urls") or []
    if not isinstance(urls, list):
        urls = []
    urls = [u for u in urls if isinstance(u, str) and u.strip()]
    mode = str(data.get("mode") or "auto").lower()
    quality = str(data.get("quality") or "auto")
    if mode not in ("auto", "audio"):
        mode = "auto"
    return urls, mode, quality

def _batch_download(urls: list[str], cfg: dict, mode: str, quality: str) -> None:
    """
    Jalankan unduhan batch secara berurutan.
    - mode: 'auto' atau 'audio'
    - quality:
        * untuk 'auto' → biasanya 'auto' atau format-string yt-dlp
        * untuk 'audio' → 'best' atau 'bestaudio/best' (akan dinormalisasi)
    """
    if not urls:
        console.print(Panel.fit("Daftar URL kosong.", style="yellow"))
        return

    outdir = cfg.get("output_dir", "downloads")

    # Normalisasi quality untuk audio
    if mode == "audio":
        if quality.strip().lower() in ("auto", "best", "bestaudio", "bestaudio/best"):
            q_use = "bestaudio/best"
        else:
            q_use = quality
    else:
        q_use = quality or "auto"

    total = len(urls)
    for idx, url in enumerate(urls, start=1):
        prov = detect_provider(url) or "unknown"
        if prov not in PROVIDER_CLASS_MAP:
            console.print(Panel.fit(f"[yellow]Lewati:[/yellow] Provider tidak dikenali untuk URL:\n{url}", style="yellow"))
            continue

        style_key = "filename_style_audio" if mode == "audio" else "filename_style_video"
        style_val = cfg.get(style_key, "simple")
        template = choose_filename_template(mode, style_val, cfg)
        outtmpl = build_outtmpl(outdir, prov, template)
        cookies_path = _resolve_cookies(cfg, prov)
        provider_obj = _get_provider(prov, cfg)

        console.rule(f"[b]Batch {idx}/{total}[/b] • {provider_badge(prov)}")
        run_download(
            provider_name=prov,
            provider_obj=provider_obj,
            url=url,
            mode=mode,
            quality=q_use,
            outtmpl=outtmpl,
            cookies_path=cookies_path,
            audio_codec=cfg.get("audio_format_default", "mp3"),
            audio_quality=cfg.get("audio_bitrate_default", "best"),
            embed_thumbnail=cfg.get("embed_thumbnail", True),
        )

def _batch_input_wizard(cfg: dict) -> None:
    """
    Mode input manual: user memasukkan URL satu per satu, lalu bisa mengeksekusi semuanya.
    """
    urls: list[str] = []
    while True:
        clear_screen()
        console.rule("[b]Batch • Input manual[/b]")

        # Tabel daftar URL
        tbl = Table(title="Daftar URL", show_header=True, header_style="bold cyan", expand=True, box=box.ROUNDED)
        tbl.add_column("No", style="magenta", justify="center", width=4)
        tbl.add_column("Provider", style="white", width=12)
        tbl.add_column("URL", style="white")
        if urls:
            for i, u in enumerate(urls, start=1):
                prov = detect_provider(u) or "-"
                tbl.add_row(str(i), provider_badge(prov) if prov in PROVIDER_CLASS_MAP else prov, u)
        else:
            tbl.caption = "[dim]Belum ada URL. Pilih '1' untuk menambah.[/dim]"
        console.print(tbl)

        # Opsi
        ops = {
            "1": "Tambah URL",
            "2": "Hapus terakhir",
            "3": "Bersihkan daftar",
            "4": "Lanjut download",
        }
        key = _choose("Aksi", ops, allow_back=True)
        if key is None:
            return
        if key == "1":
            u = Prompt.ask("Tempel URL (kosong=batalkan)")
            if not u:
                continue
            if not validate_url(u):
                console.print(Panel.fit("URL tidak valid.", style="yellow")); Prompt.ask("Enter untuk lanjut"); continue
            urls.append(u.strip())
        elif key == "2":
            if urls: urls.pop()
        elif key == "3":
            urls.clear()
        elif key == "4":
            if not urls:
                console.print(Panel.fit("Daftar kosong.", style="yellow")); Prompt.ask("Enter untuk lanjut"); continue
            # Pilih mode (sekali untuk semua)
            mode_key = _choose("Pilih Mode", {
                "1": "auto (media asli: original)",
                "2": "audio (ekstrak audio)"
            }, allow_back=False)
            mode = "audio" if mode_key == "2" else "auto"
            # Quality default
            quality = "auto" if mode == "auto" else "best"
            # Konfirmasi ringkasan
            console.print(Panel.fit(
                f"Akan mengunduh [bold]{len(urls)}[/bold] URL.\n"
                f"Mode: [bold]{mode}[/bold] • Quality: [bold]{quality}[/bold]\n"
                f"Output: [dim]{shorten_path(cfg.get('output_dir','downloads'), 72)}[/dim]",
                title="Ringkasan Batch",
                border_style="cyan"
            ))
            ok = Confirm.ask("Mulai sekarang?", default=True)
            if not ok:
                continue
            _batch_download(urls, cfg, mode, quality)
            Prompt.ask("Selesai. Enter untuk kembali ke menu Batch.")
            return

def batch_menu():
    """
    Menu utama untuk fitur Batch Downloads.
    """
    base_dir = os.getcwd()
    cfg = load_config(base_dir)
    while True:
        clear_screen()
        console.rule("[b]Batch Downloads[/b]")
        key = _choose("Pilih opsi", {
            "1": "Buka batch_downloads.yaml",
            "2": "Input manual",
        }, allow_back=True)
        if key is None:
            return
        if key == "1":
            path = _ensure_batch_file(base_dir)
            _open_file_external(path)
            console.print(Panel.fit("Setelah selesai mengedit file, kembali ke sini.", style="cyan"))
            if Confirm.ask("Jalankan unduhan berdasarkan file sekarang?", default=False):
                urls, mode, quality = _read_batch_file(path)
                if not urls:
                    console.print(Panel.fit("Daftar URL di file kosong.", style="yellow"))
                    Prompt.ask("Enter untuk kembali")
                    continue
                _batch_download(urls, cfg, mode, quality)
                Prompt.ask("Selesai. Enter untuk kembali ke menu Batch.")
        elif key == "2":
            _batch_input_wizard(cfg)


def settings_menu():
    base_dir = os.getcwd()
    cfg = load_config(base_dir)
    while True:
        clear_screen()
        console.rule("[b]Settings[/b]")
        key = _choose("Pilih kategori", {
            "1": "Filename style",
            "2": "Video",
            "3": "Audio",
            "4": "Output path",
        }, allow_back=True)
        if key is None:
            return
        if key == "1":
            _settings_filename_style(cfg)
        elif key == "2":
            _settings_video(cfg)
        elif key == "3":
            _settings_audio(cfg)
        elif key == "4":
            _settings_output(cfg)

def _build_format_from_settings(cfg: dict, mode: str) -> str:
    """
    Ketika user pilih 'Auto' di menu kualitas, kita gunakan pengaturan default dari Settings.
    """
    if mode == "audio":
        return "bestaudio/best"
    # video
    q = cfg.get("video_quality_default","auto")
    if q == "best":
        return "bestvideo*+bestaudio/best"
    if q == "preset":
        res = int(cfg.get("video_resolution_default", 720))
        fmt = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]"
        # Filter codec preferensi dilakukan oleh yt-dlp saat pemilihan format; kita cukup batasi kontainer via merge_output_format
        return fmt
    # auto → gunakan provider default (nanti di BaseProvider)
    return "auto"

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
    return Panel(tbl, title="Ringkasan", subtitle="Enter untuk mulai", border_style="cyan", box=box.ROUNDED)

def interactive_menu():
    base_dir = os.getcwd()
    cfg = load_config(base_dir)

    if not check_ffmpeg():
        console.print(Panel.fit("[red]ffmpeg tidak ditemukan. Install ffmpeg terlebih dahulu.[/red]"))
        return

    # ===== Main Loop =====
    while True:
        clear_screen()
        console.rule("[b]Online Media Downloader[/b]")
        choice = _choose("Menu", {
            "1": "📥 Download",
            "2": "📦 Batch Downloads",
            "3": "⚙️ Settings"
            }, allow_back=False)
        if choice == "1":
            # ---- step: URL ----
            clear_screen()
            console.rule("[b]Download[/b]")
            url = Prompt.ask("Tempel URL (0=Kembali, q=Keluar)")
            if url == "0":
                continue
            if url.lower() == "q":
                raise SystemExit(0)
            if not validate_url(url):
                console.print("[red]URL tidak valid[/red]"); Prompt.ask("Enter untuk kembali"); continue
            provider = detect_provider(url)
            if not provider:
                console.print("[red]Provider tidak terdeteksi dari URL[/red]"); Prompt.ask("Enter untuk kembali"); continue

            # ---- step: mode ----
            mode_key = _choose("Pilih Mode", {"1": "auto (media asli: original)", "2": "audio (ekstrak audio)"})
            if mode_key is None:
                continue
            mode = "auto" if mode_key == "1" else "audio"

            # ---- step: kualitas ----
            if mode == "audio":
                kq = _choose("Pilih Kualitas Audio", {"1": "Auto (bestaudio/best)", "2": "Best", "3": "Preset bitrate"}, default_key="1")
                preset_choice = None
                if kq == "3":
                    preset_choice = _choose("Pilih Bitrate", {"1": "320 Kbps", "2": "192 Kbps", "3": "128 Kbps"}, default_key="1")
                if kq is None:
                    continue
                if kq == "1":
                    fmt = "bestaudio/best"
                    audio_quality = cfg.get("audio_bitrate_default","best")
                elif kq == "2":
                    fmt = "bestaudio/best"
                    audio_quality = "best"
                else:
                    fmt = "bestaudio/best"
                    audio_quality = {"1":"320","2":"192","3":"128"}[preset_choice]
            else:
                kq = _choose("Pilih Kualitas Video/Media", {"1": "Auto (pakai Settings)", "2": "Best", "3": "Preset resolusi", "4": "Format manual (yt-dlp)"}, default_key="1")
                if kq is None:
                    continue
                if kq == "1":
                    fmt = _build_format_from_settings(cfg, "auto")
                elif kq == "2":
                    fmt = "bestvideo*+bestaudio/best"
                elif kq == "3":
                    res_key = _choose("Pilih Preset Resolusi", {k:v for k,v in VIDEO_PRESETS.items()}, default_key="2")
                    if res_key is None:
                        continue
                    res_label = VIDEO_PRESETS[res_key]
                    fmt = VIDEO_PRESET_TO_FORMAT[res_label]
                else:
                    fmt = Prompt.ask("Masukkan format yt-dlp")
                audio_quality = cfg.get("audio_bitrate_default","best")

            # ---- step: filename style ----
            ns_key = _choose("Pilih Gaya Nama File", {"1": "simple (judul saja)", "2": "nerd (judul + info teknis)"}, default_key="1")
            if ns_key is None:
                continue
            style = "simple" if ns_key == "1" else "nerd"
            template = choose_filename_template(mode, style, cfg)

            # ---- summary ----
            outdir = cfg.get("output_dir","downloads")
            outtmpl = build_outtmpl(outdir, provider, template)
            cookies_path = _resolve_cookies(cfg, provider)

            clear_screen()
            console.print(_summary_panel(url, provider, mode, fmt, audio_quality, style, outtmpl))
            ok = Confirm.ask("Lanjutkan unduh?", default=True)
            if not ok:
                continue

            provider_obj = _get_provider(provider, cfg)

            console.rule(provider_badge(provider))
            run_download(
                provider_name=provider,
                provider_obj=provider_obj,
                url=url,
                mode=mode,
                quality=fmt,
                outtmpl=outtmpl,
                cookies_path=cookies_path,
                audio_codec=cfg.get("audio_format_default","mp3"),
                audio_quality=audio_quality,
                embed_thumbnail=cfg.get("embed_thumbnail", True),
            )
            Prompt.ask("Selesai. Enter untuk kembali ke menu utama.")
        elif choice == "2":
            batch_menu()
        elif choice == "3":
            settings_menu()
