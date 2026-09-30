"""yt-dlp wrapper: downloads a YouTube URL as a single MP4 file, capped at 1080p.

The output is always H.264 video + AAC audio so it plays in QuickTime and other
Apple players. YouTube also serves VP9/AV1 inside MP4 containers, which QuickTime
can't decode, so we prefer H.264 (avc1) streams and re-encode as a last resort.
"""
import os
import shutil
import subprocess
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

# Prefer H.264 (avc1) + AAC (m4a); both are QuickTime-compatible and need no re-encode.
# The final fallbacks may pick VP9/AV1, which _ensure_quicktime_compatible fixes up.
FORMAT_SELECTOR = (
    "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[ext=m4a]"
    "/best[height<=1080][vcodec^=avc1]"
    "/bestvideo[height<=1080]+bestaudio"
    "/best[height<=1080]"
)


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


def _probe_codec(path: str, stream: str) -> str:
    """Returns the codec name of the first `stream` ('v' or 'a') in `path`, or ''."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", f"{stream}:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=nw=1:nk=1",
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _ensure_quicktime_compatible(path: str) -> str:
    """Re-encodes `path` to H.264/AAC if needed. Returns the path of the playable file."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg/ffprobe not found on PATH")

    video_codec = _probe_codec(path, "v")
    audio_codec = _probe_codec(path, "a")
    if video_codec == "h264" and audio_codec in ("aac", ""):
        return path

    base, _ext = os.path.splitext(path)
    converted = base + ".h264.mp4"
    video_args = (
        ["-c:v", "copy"]
        if video_codec == "h264"
        else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
    )
    audio_args = ["-c:a", "copy"] if audio_codec == "aac" else ["-c:a", "aac", "-b:a", "192k"]
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", path,
            *video_args, *audio_args,
            "-movflags", "+faststart",
            converted,
        ],
        check=True,
    )
    os.remove(path)
    return converted


def download_video(url: str, out_dir: str) -> tuple[str, str]:
    """Downloads `url` into `out_dir` as an MP4. Returns (file_path, display_filename)."""
    validate_youtube_url(url)

    output_template = os.path.join(out_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": FORMAT_SELECTOR,
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

        mp4_path = _ensure_quicktime_compatible(mp4_path)

        title = info.get("title") or info.get("id") or "video"
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip() or "video"
        display_filename = f"{safe_title}.mp4"

        return mp4_path, display_filename
