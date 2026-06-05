// In-memory client-side store for the latest analysis result + the source video.

import type { AnalysisResponse } from "./types"

interface StoredAnalysis {
  analysis: AnalysisResponse
  /** `blob:` object URL or a static `/public` URL. */
  videoUrl: string
  videoName: string
}

let current: StoredAnalysis | null = null

function disposeCurrent(): void {
  if (current?.videoUrl?.startsWith("blob:")) URL.revokeObjectURL(current.videoUrl)
}

export function setAnalysis(s: StoredAnalysis): void {
  disposeCurrent()
  current = s
}

export function getAnalysis(): StoredAnalysis | null {
  return current
}

export function clearAnalysis(): void {
  disposeCurrent()
  current = null
}
