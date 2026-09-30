"""In-memory job store for tracking download progress.

Single-process only: state is lost on restart and isn't shared across
worker processes. That's fine for this MVP (one uvicorn worker).
"""
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.QUEUED
    file_path: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    tmp_dir: Optional[str] = None


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job() -> Job:
    job = Job(id=str(uuid.uuid4()))
    with _lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id: str, **fields) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        for key, value in fields.items():
            setattr(job, key, value)


def delete_job(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)
