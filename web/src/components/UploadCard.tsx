"use client"

import { useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { analyzeVideo } from "@/lib/api"
import { setAnalysis } from "@/lib/analysis-store"
import { IconUpload } from "./icons"

const STAGES = ["Uploading", "Pose detection", "Skateboard keypoints", "Trick classification"]

export function UploadCard() {
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [pct, setPct] = useState(0)
  const [stage, setStage] = useState(0)
  const [fileName, setFileName] = useState("")
  const [fileSize, setFileSize] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isRegular, setIsRegular] = useState(true)

  async function handle(file: File) {
    setError(null)
    setBusy(true)
    setFileName(file.name)
    setFileSize(file.size)
    setPct(0)
    setStage(0)

    // client-side simulation that completes when the request returns.
    let p = 0
    let s = 0
    const iv = setInterval(() => {
      p = Math.min(94, p + 1.8 + Math.random() * 1.2)
      setPct(p)
      const ns = p < 28 ? 0 : p < 58 ? 1 : p < 86 ? 2 : 3
      if (ns !== s) {
        s = ns
        setStage(s)
      }
    }, 180)

    try {
      const res = await analyzeVideo(file, { isRegular })
      const videoUrl = URL.createObjectURL(file)
      setAnalysis({ analysis: res, videoUrl, videoName: file.name })

      // Finish the progress animation, then navigate.
      clearInterval(iv)
      setPct(100)
      setStage(3)
      setTimeout(() => router.push("/viewer"), 400)
    } catch (err) {
      clearInterval(iv)
      setBusy(false)
      setPct(0)
      setStage(0)
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  if (busy) {
    return (
      <div className="action-card">
        <div className="card-eyebrow">
          <span className="spinner" /> <span>Analyzing</span>
        </div>
        <h2 style={{ marginTop: 6 }}>{fileName}</h2>
        <p>Running pipeline · stage {stage + 1}/4</p>
        <div className="upload-state">
          <div className="filename">
            <span className="mono">{fileName}</span>
            <span className="muted">· {(fileSize / 1024 / 1024).toFixed(1)} MB</span>
          </div>
          <div>
            <div className="progress">
              <span style={{ transform: `scaleX(${pct / 100})` }} />
            </div>
            <div className="progress-row" style={{ marginTop: 6 }}>
              <span className="mono">{Math.floor(pct)}%</span>
              <span>{STAGES[stage]}…</span>
            </div>
          </div>
          <div className="stages">
            {STAGES.map((s, i) => (
              <div key={s} className={`stage-row ${i < stage ? "done" : i === stage ? "active" : "pending"}`}>
                <span className="stage-dot" />
                <span className="stage-label">{s}</span>
                <span className="stage-time">{i < stage ? "done" : i === stage ? "running" : "queued"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="action-card">
      <div className="card-eyebrow">
        <IconUpload />
        <span>Upload</span>
      </div>
      <h2 style={{ marginTop: 6 }}>Upload a new video</h2>
      <p>Drop an .mp4 — we&rsquo;ll process it end-to-end on the backend.</p>

      {error && <div className="error-banner">{error}</div>}

      <div
        className={`dropzone ${drag ? "is-over" : ""}`}
        onDragOver={e => {
          e.preventDefault()
          setDrag(true)
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => {
          e.preventDefault()
          setDrag(false)
          const f = e.dataTransfer.files?.[0]
          if (f) handle(f)
        }}
        onClick={() => fileRef.current?.click()}
      >
        <div>
          <div className="dz-title">Drag &amp; drop a video file here</div>
          <div className="dz-sub">mp4 / mov / mkv / webm · 720p+ · 30–240 fps</div>
          <div className="dz-pick">
            <IconUpload />
            <span>Browse files</span>
          </div>
        </div>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="video/mp4,video/quicktime,video/x-matroska,video/webm,.mp4,.mov,.mkv,.webm,.avi"
        hidden
        onChange={e => {
          const f = e.target.files?.[0]
          if (f) handle(f)
          e.target.value = ""
        }}
      />

      <label
        style={{
          marginTop: 12,
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 12,
          color: "var(--muted)"
        }}
      >
        <input type="checkbox" checked={isRegular} onChange={e => setIsRegular(e.target.checked)} style={{ accentColor: "var(--accent)" }} />
        <span>Regular stance (left foot forward) — uncheck for goofy</span>
      </label>
    </div>
  )
}
