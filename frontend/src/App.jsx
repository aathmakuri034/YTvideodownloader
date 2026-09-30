import { useRef, useState } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'
const POLL_INTERVAL_MS = 1500

function App() {
  const [url, setUrl] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | error | success
  const [errorMessage, setErrorMessage] = useState('')
  const pollTimer = useRef(null)

  const stopPolling = () => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current)
      pollTimer.current = null
    }
  }

  const fetchAndSaveFile = async (jobId) => {
    const res = await fetch(`${API_BASE}/api/jobs/${jobId}/file`)
    if (!res.ok) {
      throw new Error('Failed to fetch the downloaded file.')
    }
    const disposition = res.headers.get('Content-Disposition') || ''
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
    const plainMatch = disposition.match(/filename="?([^";]+)"?/i)
    const filename = utf8Match
      ? decodeURIComponent(utf8Match[1])
      : plainMatch
        ? plainMatch[1]
        : 'video.mp4'

    const blob = await res.blob()
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(objectUrl)
  }

  const pollJob = (jobId) => {
    pollTimer.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${jobId}`)
        const data = await res.json()

        if (data.status === 'done') {
          stopPolling()
          await fetchAndSaveFile(jobId)
          setStatus('success')
        } else if (data.status === 'error') {
          stopPolling()
          setErrorMessage(data.error || 'Something went wrong.')
          setStatus('error')
        }
      } catch {
        stopPolling()
        setErrorMessage('Lost connection to the server.')
        setStatus('error')
      }
    }, POLL_INTERVAL_MS)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMessage('')
    setStatus('loading')

    try {
      const res = await fetch(`${API_BASE}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Invalid URL or server error.')
      }

      const { job_id } = await res.json()
      pollJob(job_id)
    } catch (err) {
      setErrorMessage(err.message)
      setStatus('error')
    }
  }

  const isLoading = status === 'loading'

  return (
    <main className="page">
      <h1>YouTube to MP4 Downloader</h1>

      <form className="download-form" onSubmit={handleSubmit}>
        <input
          type="url"
          placeholder="Paste a YouTube video URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Downloading…' : 'Download'}
        </button>
      </form>

      {status === 'error' && <p className="message error">{errorMessage}</p>}
      {status === 'success' && (
        <p className="message success">Done! Your download should start automatically.</p>
      )}

      <p className="helper-text">
        Paste a public YouTube video URL above and click Download. The server fetches the
        video, merges it into a single MP4 file (up to 1080p), and your browser saves it.
        Downloading videos may conflict with YouTube's Terms of Service — only use this on
        content you have the right to download.
      </p>
    </main>
  )
}

export default App
