"""yt-dlp wrapper: downloads a YouTube URL as a single MP4 file, capped at 1080p."""
import os
from urllib.parse import urlparse

import yt_dlp

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

# Videos longer than this are rejected to keep the demo's disk/time usage bounded.
MAX_DURATION_SECONDS = 3 * 60 * 60  # 3 hours


class InvalidUrlError(ValueError):
    pass


class VideoTooLongError(ValueError):
    pass


def validate_youtube_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidUrlError("URL must start with http:// or https://")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise InvalidUrlError("URL must be a youtube.com or youtu.be link")


def download_video(url: str, out_dir: str) -> tuple[str, str]:
    """Downloads `url` into `out_dir` as an MP4. Returns (file_path, display_filename)."""
    validate_youtube_url(url)

    output_template = os.path.join(out_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "restrictfilenames": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        duration = info.get("duration") or 0
        if duration > MAX_DURATION_SECONDS:
            raise VideoTooLongError(
                f"Video is too long ({duration}s); max allowed is {MAX_DURATION_SECONDS}s"
            )

        ydl.download([url])
        file_path = ydl.prepare_filename(info)
        # prepare_filename doesn't know about post-processing merge, force .mp4
        base, _ext = os.path.splitext(file_path)
        mp4_path = base + ".mp4"
        if not os.path.exists(mp4_path) and os.path.exists(file_path):
            mp4_path = file_path

        title = info.get("title") or info.get("id") or "video"
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip() or "video"
        display_filename = f"{safe_title}.mp4"

        return mp4_path, display_filename
