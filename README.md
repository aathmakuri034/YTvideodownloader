# YouTube to MP4 Downloader

Paste a public YouTube URL, click Download, get an MP4 (up to 1080p).

## Requirements

- Python 3.10+
- Node.js 18+
- **ffmpeg** installed on the system (required to merge video/audio into MP4)
  - macOS: `brew install ffmpeg`

## Backend (FastAPI + yt-dlp)

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --reload --port 8000
```

Runs at http://localhost:8000. Endpoints:
- `POST /api/download` `{ "url": "<youtube url>" }` -> `{ job_id, status }`
- `GET /api/jobs/{job_id}` -> job status (`queued` / `processing` / `done` / `error`)
- `GET /api/jobs/{job_id}/file` -> the finished MP4 (once status is `done`)

## Frontend (Vite + React)

```bash
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173 and calls the backend at http://localhost:8000.

## Notes

- yt-dlp is used instead of pytube/youtube-dl for reliability — pytube breaks often,
  and the original youtube-dl project is largely unmaintained. yt-dlp is the actively
  maintained fork.
- Downloading YouTube videos may conflict with YouTube's Terms of Service. This is a
  personal/demo tool — only use it on content you have the right to download.
- Job state is stored in memory in a single process; restarting the backend clears
  any in-progress jobs. Downloaded files are deleted from the server right after
  being sent to the browser.
