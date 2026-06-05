"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { LIBRARY, type LibraryItem } from "@/lib/library"
import { setAnalysis } from "@/lib/analysis-store"
import type { AnalysisResponse } from "@/lib/types"
import { IconGrid } from "./icons"
import { ThumbFig } from "./ThumbFig"

export function BrowseCard() {
  const router = useRouter()
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const playable = LIBRARY.filter((g): g is Required<LibraryItem> => !!g.videoUrl && !!g.analysisUrl).length

  async function openItem(g: LibraryItem) {
    if (!g.videoUrl || !g.analysisUrl) return
    setError(null)
    setLoadingId(g.id)
    try {
      const res = await fetch(g.analysisUrl, { cache: "force-cache" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const analysis: AnalysisResponse = await res.json()
      setAnalysis({ analysis, videoUrl: g.videoUrl, videoName: g.name })
      router.push("/viewer")
    } catch (err) {
      setLoadingId(null)
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <div className="action-card" style={{ background: "linear-gradient(180deg, var(--surface-2), var(--surface))" }}>
      <div className="card-eyebrow">
        <IconGrid />
        <span>Library</span>
      </div>
      <h2 style={{ marginTop: 6 }}>Browse analyses</h2>
      <p>
        {playable === 1 ? "1 sample clip" : `${playable} sample clips`} bundled in <span className="mono">public/</span>
      </p>
      {error && <div className="error-banner">{error}</div>}
      <div
        style={{
          flex: 1,
          marginTop: 18,
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gridTemplateRows: "repeat(3, 1fr)",
          gap: 8
        }}
      >
        {LIBRARY.map((g, i) => {
          const isPlayable = !!g.videoUrl && !!g.analysisUrl
          const isLoading = loadingId === g.id
          return (
            <button
              key={g.id}
              onClick={isPlayable ? () => openItem(g) : undefined}
              disabled={!isPlayable || loadingId !== null}
              title={isPlayable ? `Open ${g.name}` : "Placeholder — not playable"}
              style={{
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--bg-2)",
                position: "relative",
                overflow: "hidden",
                cursor: isPlayable ? "pointer" : "default",
                opacity: isPlayable ? 1 : 0.5,
                padding: 0,
                color: "inherit",
                textAlign: "left",
                transition: "transform 120ms, border-color 120ms"
              }}
              onMouseEnter={e => {
                if (isPlayable) e.currentTarget.style.borderColor = "var(--accent)"
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = "var(--border)"
              }}
            >
              <ThumbFig color={g.color} variant={i} />
              {isLoading && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    display: "grid",
                    placeItems: "center",
                    background: "color-mix(in oklch, var(--bg) 70%, transparent)",
                    fontSize: 11,
                    color: "var(--text)"
                  }}
                >
                  <span className="spinner" />
                </div>
              )}
              {!isPlayable && (
                <span
                  style={{
                    position: "absolute",
                    top: 6,
                    right: 6,
                    fontSize: 9,
                    fontWeight: 600,
                    letterSpacing: ".06em",
                    padding: "1px 5px",
                    borderRadius: 4,
                    background: "color-mix(in oklch, var(--bg) 75%, transparent)",
                    color: "var(--muted)",
                    textTransform: "uppercase"
                  }}
                >
                  demo
                </span>
              )}
              <div
                style={{
                  position: "absolute",
                  bottom: 6,
                  left: 8,
                  right: 8,
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 10,
                  color: "var(--text-2)"
                }}
              >
                <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{g.trick}</span>
                <span className="mono">{g.duration.toFixed(1)}s</span>
              </div>
            </button>
          )
        })}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 14, alignItems: "center" }}>
        <div style={{ flex: 1, color: "var(--muted)", fontSize: 12 }}>{playable > 0 ? "Click a sample to open it in the viewer" : "Add videos + JSON to public/ to populate the library"}</div>
      </div>
    </div>
  )
}
