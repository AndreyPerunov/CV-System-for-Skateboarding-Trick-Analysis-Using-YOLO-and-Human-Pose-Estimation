"use client"

import { IconUpload } from "./icons"

export function UploadCard() {
  return (
    <div className="action-card is-disabled">
      <div className="card-eyebrow">
        <IconUpload />
        <span>Upload</span>
        <span className="demo-pill">disabled in demo</span>
      </div>
      <h2 style={{ marginTop: 6 }}>Upload a new video</h2>
      <p>Drop an .mp4 — we&rsquo;ll process it end-to-end on the backend.</p>

      <div className="demo-banner">
        Uploading and backend analysis are turned off in this demo. Browse the pre-analyzed clips on the right instead.
      </div>

      <div
        className="dropzone is-locked"
        aria-disabled="true"
        title="Disabled in the demo build"
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
        <input type="checkbox" defaultChecked disabled style={{ accentColor: "var(--accent)" }} />
        <span>Regular stance (left foot forward) — uncheck for goofy</span>
      </label>
    </div>
  )
}
