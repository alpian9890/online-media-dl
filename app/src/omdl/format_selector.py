from __future__ import annotations

from typing import Dict, Tuple, Optional
from .constants import CODEC_REGEX, CODEC_PREFERENCE

def _height_of(res: str) -> Optional[int]:
    # "720p" -> 720
    try:
        return int(res.lower().replace("p", "").strip())
    except Exception:
        return None

def _container_for(prefer_codec: str, container: str) -> str:
    """
    Penentuan kontainer final.
    - Jika container eksplisit mp4/webm -> gunakan itu.
    - Jika 'auto' -> pilih sesuai preferensi codec.
    """
    if container in ("mp4", "webm"):
        return container
    vkey, akey, auto_container = CODEC_PREFERENCE.get(prefer_codec, ("h264", "aac", "mp4"))
    return auto_container

def build_video_format(
    cfg_video: Dict,
    preset_res: Optional[str] = None,
    prefer_codec: Optional[str] = None,
    allow_h265: Optional[bool] = None,
    container: Optional[str] = None,
    quality_mode: Optional[str] = None,  # auto|best|preset|manual
    manual_format: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Return:
      - format string untuk yt-dlp
      - merge_output_format (mp4/webm/None)
    """
    quality_mode = quality_mode or cfg_video.get("quality", "auto")
    prefer_codec = prefer_codec or cfg_video.get("prefer_codec", "h264+aac")
    allow_h265 = cfg_video.get("allow_h265_for_videos", False) if allow_h265 is None else allow_h265
    container = _container_for(prefer_codec, cfg_video.get("container", "auto") if container is None else container)

    if quality_mode == "manual" and manual_format:
        return manual_format, container

    if quality_mode == "best":
        # Lepas filter codec, ambil bestvideo+bestaudio, tetap merge ke container target
        fmt = "bv*+ba/best"
        return fmt, container

    if quality_mode == "preset":
        # Bangun filter vcodec/acodec berdasar preferensi codec
        vkey, akey, _ = CODEC_PREFERENCE.get(prefer_codec, ("h264", "aac", "mp4"))
        vregex = CODEC_REGEX.get(vkey, CODEC_REGEX["h264"])
        aregex = CODEC_REGEX.get(akey, CODEC_REGEX["aac"])
        if allow_h265:
            # tambahkan HEVC sebagai kandidat jika preferensi bukan hevc
            vregex = f"({vregex}|{CODEC_REGEX['hevc']})"

        height = _height_of(preset_res or cfg_video.get("preset_resolution", "720p")) or 720

        # Contoh hasil:
        # bv*[vcodec~='(avc1|h264)'][height<=720]+ba[acodec~='(aac|mp4a)']/b[ext=mp4][height<=720]
        # Untuk menjaga kompatibilitas yt-dlp, gunakan kutip ganda keseluruhan dan kutip tunggal di regex.
        fmt = (
            f"bv*[vcodec~='{vregex}'][height<={height}]"
            f"+ba[acodec~='{aregex}']"
            f"/b[height<={height}]"
        )
        return fmt, container

    # quality_mode == "auto" (default)
    # biarkan yt-dlp memilih terbaik; tetap merge container agar hasil bersih/seragam
    return "bv*+ba/best", container


def build_audio_postprocessors(audio_cfg: Dict) -> Tuple[str, list]:
    """
    Menghasilkan:
      - format untuk yt-dlp (umumnya 'bestaudio/best')
      - daftar postprocessors
    Aturan:
      - Jika format=best -> tanpa transcode (postprocessor kosong)
      - Jika format spesifik (mp3/ogg/wav/opus) -> FFmpegExtractAudio
        * bitrate 'best' dipetakan ke 320 (untuk lossy) agar kualitas tinggi.
    """
    audio_format = audio_cfg.get("format", "best")
    fmt = "bestaudio/best"
    pps = []

    if audio_format == "best":
        return fmt, pps

    target = audio_format.lower()
    # Bitrate:
    br = audio_cfg.get("bitrate_kbps", "best")
    if isinstance(br, str) and br.lower() == "best":
        preferred_quality = "320"
    else:
        # jaga batas aman 64..320
        try:
            ival = int(br)
        except Exception:
            ival = 192
        ival = min(max(ival, 64), 320)
        preferred_quality = str(ival)

    pps.append({
        "key": "FFmpegExtractAudio",
        "preferredcodec": target,
        "preferredquality": preferred_quality,
    })
    # Tambahan metadata opsional (aman diaktifkan)
    pps.append({"key": "FFmpegMetadata"})
    return fmt, pps
