import shutil
import tempfile

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import jobs
from app.downloader import (
    InvalidUrlError,
    VideoTooLongError,
    download_video,
    validate_youtube_url,
)

app = FastAPI(title="YouTube to MP4 Downloader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


class DownloadRequest(BaseModel):
    url: str


def _run_download(job_id: str, url: str) -> None:
    jobs.update_job(job_id, status=jobs.JobStatus.PROCESSING)
    tmp_dir = tempfile.mkdtemp(prefix="ytdl_")
    try:
        file_path, display_filename = download_video(url, tmp_dir)
        jobs.update_job(
            job_id,
            status=jobs.JobStatus.DONE,
            file_path=file_path,
            filename=display_filename,
            tmp_dir=tmp_dir,
        )
    except (InvalidUrlError, VideoTooLongError) as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        jobs.update_job(job_id, status=jobs.JobStatus.ERROR, error=str(exc))
    except Exception:  # yt-dlp raises broad DownloadError etc.
        shutil.rmtree(tmp_dir, ignore_errors=True)
        jobs.update_job(
            job_id,
            status=jobs.JobStatus.ERROR,
            error="Could not download this video. It may be private, age-restricted, or unavailable.",
        )


@app.post("/api/download")
def start_download(payload: DownloadRequest, background_tasks: BackgroundTasks):
    try:
        validate_youtube_url(payload.url)
    except InvalidUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    job = jobs.create_job()
    background_tasks.add_task(_run_download, job.id, payload.url)
    return {"job_id": job.id, "status": job.status}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status, "error": job.error}


def _cleanup(tmp_dir: str, job_id: str) -> None:
    shutil.rmtree(tmp_dir, ignore_errors=True)
    jobs.delete_job(job_id)


@app.get("/api/jobs/{job_id}/file")
def get_job_file(job_id: str, background_tasks: BackgroundTasks):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != jobs.JobStatus.DONE:
        raise HTTPException(status_code=409, detail=f"Job is not ready (status: {job.status})")

    background_tasks.add_task(_cleanup, job.tmp_dir, job.id)
    return FileResponse(
        path=job.file_path,
        media_type="video/mp4",
        filename=job.filename,
        background=background_tasks,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
