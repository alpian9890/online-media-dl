# online-media-dl

CLI **offline** (tanpa server) untuk mengunduh media dari YouTube / Instagram / TikTok / Facebook / X (Twitter),
dibangun di atas **yt-dlp + ffmpeg** dengan antarmuka yang lebih ramah (menu & subcommands).

## Fitur
- 100% lokal, jalan di **Termux** / Linux / macOS / Windows (WSL).
- Mode **Video** atau **Audio (MP3/codec lain)**.
- Template nama file fleksibel.
- Dukungan cookies (Netscape format) per provider.
- Konfigurasi YAML (default + override `config/local.yaml`).

## Instalasi (Termux)
```bash
pkg update && pkg upgrade
pkg install python ffmpeg git

# clone
git clone https://github.com/alpian9890/online-media-dl.git
cd online-media-dl

# siapkan venv & install
bash scripts/dev-setup.sh
