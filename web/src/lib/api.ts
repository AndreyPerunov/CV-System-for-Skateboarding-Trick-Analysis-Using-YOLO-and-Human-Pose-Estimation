import type { AnalysisResponse, StatsResponse } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

interface AnalyzeOptions {
  isRegular?:        boolean;
  boardLengthCm?:    number;
  heightThresholdCm?: number;
  frameStep?:        number;
}

export async function analyzeVideo(
  file: File,
  opts: AnalyzeOptions = {},
): Promise<AnalysisResponse> {
  const params = new URLSearchParams({
    is_regular:          String(opts.isRegular ?? true),
    board_length_cm:     String(opts.boardLengthCm ?? 81.0),
    height_threshold_cm: String(opts.heightThresholdCm ?? 3.0),
    frame_step:          String(opts.frameStep ?? 1),
  });
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/analyze_video?${params}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json())?.detail ?? detail; } catch {}
    throw new Error(`Analysis failed (HTTP ${res.status}): ${detail}`);
  }
  return res.json();
}

export async function getStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Stats failed: HTTP ${res.status}`);
  return res.json();
}

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Health failed: HTTP ${res.status}`);
  return res.json();
}
