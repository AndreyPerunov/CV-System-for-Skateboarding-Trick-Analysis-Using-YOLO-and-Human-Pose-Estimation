"use client"

import { useMemo } from "react"

export interface Series {
  name: string
  color: string
  data: { t: number; v: number | null }[]
  dashed?: boolean
  width?: number
  opacity?: number
}

interface Props {
  height?: number
  series: Series[]
  trickBands?: [number, number][]
  time: number
  duration: number
  onSeek?: (t: number) => void
  fillUnderIdx?: number
}

const W = 600
const PAD_L = 24,
  PAD_R = 8,
  PAD_T = 6,
  PAD_B = 14

export function Chart({ height = 120, series, trickBands = [], time, duration, onSeek, fillUnderIdx }: Props) {
  const H = height
  const innerW = W - PAD_L - PAD_R
  const innerH = H - PAD_T - PAD_B

  const { minV, maxV } = useMemo(() => {
    let mn = Infinity,
      mx = -Infinity
    for (const s of series) {
      for (const p of s.data) {
        if (p.v == null || !isFinite(p.v)) continue
        if (p.v < mn) mn = p.v
        if (p.v > mx) mx = p.v
      }
    }
    if (!isFinite(mn) || !isFinite(mx)) return { minV: -1, maxV: 1 }
    const pad = (mx - mn) * 0.12 || Math.max(1, Math.abs(mx) * 0.1)
    return { minV: mn - pad, maxV: mx + pad }
  }, [series])

  const xOf = (t: number) => PAD_L + (duration > 0 ? (t / duration) * innerW : 0)
  const yOf = (v: number) => PAD_T + (1 - (v - minV) / (maxV - minV || 1)) * innerH

  function pathFor(data: Series["data"]) {
    let d = ""
    let started = false
    for (const p of data) {
      if (p.v == null || !isFinite(p.v)) {
        started = false
        continue
      }
      const x = xOf(p.t).toFixed(2)
      const y = yOf(p.v).toFixed(2)
      d += `${started ? "L" : "M"}${x} ${y} `
      started = true
    }
    return d.trim()
  }

  function handleClick(e: React.MouseEvent<SVGSVGElement>) {
    if (!onSeek) return
    const svg = e.currentTarget
    const rect = svg.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * W
    const t = ((x - PAD_L) / innerW) * duration
    onSeek(Math.max(0, Math.min(duration, t)))
  }

  const playheadX = xOf(time)
  const ticks = [maxV, (minV + maxV) / 2, minV]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" onClick={handleClick} style={{ cursor: "pointer" }}>
      {trickBands.map(([a, b], i) => (
        <rect key={i} x={xOf(a)} y={PAD_T} width={Math.max(0, xOf(b) - xOf(a))} height={innerH} fill="color-mix(in oklch, var(--accent) 18%, transparent)" />
      ))}

      {ticks.map((tk, i) => (
        <g key={i}>
          <line x1={PAD_L} y1={yOf(tk)} x2={W - PAD_R} y2={yOf(tk)} stroke="var(--border)" strokeDasharray="2 4" strokeWidth={0.6} />
          <text x={PAD_L - 4} y={yOf(tk) + 3} fontSize={9} fill="var(--muted-2)" textAnchor="end" fontFamily="var(--font-mono)">
            {Math.round(tk)}
          </text>
        </g>
      ))}
      <line x1={PAD_L} y1={H - PAD_B} x2={W - PAD_R} y2={H - PAD_B} stroke="var(--border)" strokeWidth={0.6} />

      {fillUnderIdx != null && series[fillUnderIdx] && <path d={`${pathFor(series[fillUnderIdx].data)} L${xOf(duration)} ${yOf(minV)} L${xOf(0)} ${yOf(minV)} Z`} fill={series[fillUnderIdx].color} opacity={0.1} />}

      {series.map((s, i) => (
        <path key={i} d={pathFor(s.data)} fill="none" stroke={s.color} strokeWidth={s.width ?? 1.4} strokeOpacity={s.opacity ?? 1} strokeDasharray={s.dashed ? "4 3" : undefined} strokeLinejoin="round" strokeLinecap="round" />
      ))}

      <line x1={playheadX} y1={PAD_T} x2={playheadX} y2={H - PAD_B} stroke="var(--accent)" strokeWidth={1} />
      <circle cx={playheadX} cy={PAD_T} r={2.4} fill="var(--accent)" />
    </svg>
  )
}
