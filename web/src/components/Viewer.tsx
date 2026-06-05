"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { getAnalysis } from "@/lib/analysis-store"
import { drawOverlay, pickKeypoint, type HoverState, type OverlayToggles } from "@/lib/overlays"
import { fmtTime, fmtClock } from "@/lib/format"
import type { AnalysisResponse } from "@/lib/types"
import { Chart, type Series } from "./Chart"
import { ChartCard } from "./ChartCard"
import { RawJsonModal } from "./RawJsonModal"
import { Scrubber } from "./Scrubber"
import { TrickSummaryCard } from "./TrickSummaryCard"
import { IconPlay, IconPause, IconStepBack, IconStepFwd, IconLoop, IconVolume, IconBody, IconBoard, IconMask, IconAxes, IconKnee, IconCoM } from "./icons"

const OVERLAY_DEFS: { key: keyof OverlayToggles; label: string; color: string; hotkey: string; Icon: React.FC<React.SVGProps<SVGSVGElement>> }[] = [
  { key: "skeleton", label: "Human skeleton", color: "var(--c-skeleton)", hotkey: "1", Icon: IconBody },
  { key: "board", label: "Board skeleton", color: "var(--c-board)", hotkey: "2", Icon: IconBoard },
  { key: "mask", label: "Board segmentation", color: "var(--c-mask)", hotkey: "3", Icon: IconMask },
  { key: "pcaKpts", label: "PCA (kpts)", color: "var(--c-pca-kpts)", hotkey: "4", Icon: IconAxes },
  { key: "pcaSeg", label: "PCA (seg)", color: "var(--c-pca-seg)", hotkey: "5", Icon: IconAxes },
  { key: "knee", label: "Knee angle", color: "var(--c-knee)", hotkey: "6", Icon: IconKnee },
  { key: "com", label: "Body center of mass", color: "var(--c-com)", hotkey: "7", Icon: IconCoM },
  { key: "skateCom", label: "Board center of mass", color: "var(--c-skate-com)", hotkey: "8", Icon: IconCoM },
  { key: "comOffset", label: "CoM offset", color: "var(--c-com)", hotkey: "9", Icon: IconCoM }
]

const COLOR_YAW = "oklch(0.66 0.20 128)"
const COLOR_JUMP = "oklch(0.64 0.18 220)"
const COLOR_KNEEL = "oklch(0.55 0.18 205)"
const COLOR_KNEER = "oklch(0.55 0.18 290)"
const COLOR_FLIP_MEAN = "oklch(0.68 0.20 60)"
const COLOR_FLIP_L = "oklch(0.68 0.22 145)"
const COLOR_FLIP_R = "oklch(0.62 0.16 260)"
const COLOR_FLIP_DIFF = "oklch(0.66 0.22 0)"
const COLOR_WRIST = "oklch(0.68 0.22 40)"
const COLOR_SHOULDER = "oklch(0.68 0.22 0)"
const COLOR_HIP = "oklch(0.58 0.25 295)"
const COLOR_ANKLE = "oklch(0.78 0.16 175)"

interface Props {
  analysis: AnalysisResponse
  videoUrl: string
  videoName: string
}

export function ViewerInner({ analysis, videoUrl, videoName }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [duration, setDuration] = useState(0)
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [rate, setRate] = useState(1)
  const [loop, setLoop] = useState(true)
  const [volume, setVolume] = useState(0)
  const [toggles, setToggles] = useState<OverlayToggles>({
    skeleton: true,
    board: true,
    mask: true,
    pcaKpts: true,
    pcaSeg: false,
    knee: true,
    com: true,
    skateCom: true,
    comOffset: true
  })
  const [showRaw, setShowRaw] = useState(false)
  const hoverRef = useRef<HoverState | null>(null)

  const fps = analysis.fps
  const tricks = analysis.tricks

  const trickBands: [number, number][] = useMemo(() => tricks.map(t => [t.start_time_s, t.end_time_s] as [number, number]), [tricks])

  const activeTrickIdx = useMemo(() => {
    for (let i = 0; i < tricks.length; i++) {
      if (time >= tricks[i].start_time_s && time <= tricks[i].end_time_s) return i
    }
    return -1
  }, [tricks, time])

  // Build chart series from timeline
  const series = useMemo(() => {
    const t = analysis.timeline
    const make = (arr: (number | null)[] | undefined): { t: number; v: number | null }[] => {
      if (!arr) return t.times_s.map(ts => ({ t: ts, v: null }))
      return t.times_s.map((ts, i) => ({ t: ts, v: arr[i] }))
    }

    // Normalize body dx by median(|dx|) per segment so all 4 lines share a
    // ~[-1, 1] scale. Sign-flip == 180° body rotation.
    const normalizeByMedAbs = (arr: (number | null)[]) => {
      const valid = arr.filter((v): v is number => v != null && isFinite(v))
      if (!valid.length) return arr
      const abs = valid.map(Math.abs).sort((a, b) => a - b)
      const med = abs[Math.floor(abs.length / 2)]
      if (!isFinite(med) || med <= 1) return arr
      return arr.map(v => (v == null ? null : v / med))
    }

    return {
      yaw: make(t.board_yaw_deg),
      jump: make(t.height_cm),
      kneeL: make(t.left_knee_angle_deg),
      kneeR: make(t.right_knee_angle_deg),
      flipMean: make(t.flip_signal_mean),
      flipL: make(t.flip_signal_left),
      flipR: make(t.flip_signal_right),
      flipDiff: make(t.flip_signal_diff),
      wrist: make(normalizeByMedAbs(t.wrist_dx)),
      shoulder: make(normalizeByMedAbs(t.shoulder_dx)),
      hip: make(normalizeByMedAbs(t.hip_dx)),
      ankle: make(normalizeByMedAbs(t.ankle_dx))
    }
  }, [analysis.timeline])

  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    const onMeta = () => setDuration(v.duration || 0)
    const onTime = () => setTime(v.currentTime)
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    v.addEventListener("loadedmetadata", onMeta)
    v.addEventListener("timeupdate", onTime)
    v.addEventListener("play", onPlay)
    v.addEventListener("pause", onPause)
    return () => {
      v.removeEventListener("loadedmetadata", onMeta)
      v.removeEventListener("timeupdate", onTime)
      v.removeEventListener("play", onPlay)
      v.removeEventListener("pause", onPause)
    }
  }, [])

  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.muted = volume === 0
    v.volume = volume
    v.playbackRate = rate
    v.loop = loop
  }, [rate, loop, volume])

  // Canvas overlay
  useEffect(() => {
    const v = videoRef.current,
      c = canvasRef.current
    if (!v || !c) return
    const ctx = c.getContext("2d")
    if (!ctx) return
    let raf = 0
    const tick = () => {
      drawOverlay(c, v, ctx, analysis.timeline, fps, toggles, hoverRef.current)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [analysis.timeline, fps, toggles])

  const onCanvasMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const v = videoRef.current
      if (!v) return
      const rect = v.getBoundingClientRect()
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top
      const next = pickKeypoint(v, analysis.timeline, fps, mx, my, toggles)
      hoverRef.current = next
      e.currentTarget.style.cursor = next ? "pointer" : "default"
    },
    [analysis.timeline, fps, toggles]
  )

  const onCanvasLeave = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    hoverRef.current = null
    e.currentTarget.style.cursor = "default"
  }, [])

  // Keyboard shortcuts
  const togglePlay = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) v.play()
    else v.pause()
  }, [])
  const seek = useCallback(
    (t: number) => {
      const v = videoRef.current
      if (!v) return
      v.currentTime = Math.max(0, Math.min(duration, t))
    },
    [duration]
  )
  const step = useCallback(
    (dirFrames: number) => {
      const v = videoRef.current
      if (!v) return
      seek(v.currentTime + dirFrames / fps)
    },
    [seek, fps]
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return
      if (e.key === " ") {
        e.preventDefault()
        togglePlay()
        return
      }
      if (e.key === "ArrowLeft") {
        step(-1)
        return
      }
      if (e.key === "ArrowRight") {
        step(+1)
        return
      }
      if (e.key === "l" || e.key === "L") {
        setLoop(l => !l)
        return
      }
      const found = OVERLAY_DEFS.find(o => o.hotkey === e.key)
      if (found) setToggles(t => ({ ...t, [found.key]: !t[found.key] }))
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [togglePlay, step])

  const currentVal = (data: { t: number; v: number | null }[]) => {
    if (!data.length) return null
    const idx = Math.max(0, Math.min(data.length - 1, Math.round((time / (duration || 1)) * (data.length - 1))))
    return data[idx]?.v ?? null
  }

  const fmt = (v: number | null, unit = "", digits = 1) => (v == null || !isFinite(v) ? "n/a" : `${v.toFixed(digits)}${unit}`)

  return (
    <div className="viewer">
      <div className="viewer-left">
        <div className="video-frame">
          <video ref={videoRef} src={videoUrl} playsInline autoPlay muted />
          <canvas ref={canvasRef} className="overlay-canvas" onMouseMove={onCanvasMove} onMouseLeave={onCanvasLeave} />
          <div className="video-hud">
            <span className="tag">{Math.round(fps)} fps</span>
            <span className="tag">{analysis.direction}</span>
            <span className="tag">stance: {analysis.stance}</span>
          </div>
          <div className="video-corner-readout">
            <div>
              <span className="lbl">yaw </span>&nbsp;&nbsp;{fmt(currentVal(series.yaw), "°", 1)}
            </div>
            <div>
              <span className="lbl">h </span>&nbsp;&nbsp;&nbsp;{fmt(currentVal(series.jump), " cm", 1)}
            </div>
            <div>
              <span className="lbl">file</span>&nbsp;&nbsp;{videoName.slice(-20)}
            </div>
          </div>
        </div>

        <Scrubber time={time} duration={duration} trickBands={trickBands} onSeek={seek} />

        <div className="player-chrome">
          <div className="controls-row">
            <button className="icon-btn" onClick={() => step(-1)} title="Prev frame (←)">
              <IconStepBack />
            </button>
            <button className="icon-btn" onClick={togglePlay} title="Play/pause (space)" aria-pressed={playing}>
              {playing ? <IconPause /> : <IconPlay />}
            </button>
            <button className="icon-btn" onClick={() => step(+1)} title="Next frame (→)">
              <IconStepFwd />
            </button>
            <div className="timecode mono">
              {fmtTime(time, fps)} / {fmtTime(duration, fps)}
            </div>
            <button className="icon-btn" onClick={() => setLoop(l => !l)} aria-pressed={loop} title="Loop (L)">
              <IconLoop />
            </button>
            <select className="mono" value={rate} onChange={e => setRate(parseFloat(e.target.value))} title="Playback speed">
              {[0.25, 0.5, 1, 1.5, 2].map(r => (
                <option key={r} value={r}>
                  {r}x
                </option>
              ))}
            </select>
            <div className="vol">
              <button className="icon-btn" onClick={() => setVolume(v => (v > 0 ? 0 : 1))} title="Mute">
                <IconVolume />
              </button>
              <input type="range" min={0} max={1} step={0.01} value={volume} onChange={e => setVolume(parseFloat(e.target.value))} />
            </div>
            <div className="grow" />
          </div>
        </div>

        <div className="overlay-bar">
          {OVERLAY_DEFS.map(o => (
            <button key={o.key} className="tg" style={{ "--c": o.color } as React.CSSProperties} aria-pressed={toggles[o.key]} onClick={() => setToggles(t => ({ ...t, [o.key]: !t[o.key] }))} title={`${o.label} (${o.hotkey})`}>
              <span className="swatch" />
              <span style={{ display: "inline-flex" }}>
                <o.Icon />
              </span>
              <span className="lbl">{o.label}</span>
              <span className="hot">{o.hotkey}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="viewer-right">
        <div className="right-scroll">
          {tricks.length > 0 && (
            <div className="tricks-head">
              <h4>Detected tricks · {tricks.length}</h4>
            </div>
          )}
          {tricks.length > 0 && (
            <div className="tricks-list">
              {tricks.map((t, i) => (
                <TrickSummaryCard key={`${t.start_frame}-${t.end_frame}`} trick={t} stance={analysis.stance} index={i + 1} total={tricks.length} active={i === activeTrickIdx} onClick={() => seek(t.start_time_s)} />
              ))}
            </div>
          )}
          {tricks.length === 0 && (
            <div className="trick-card">
              <div className="label-row">
                <span>No tricks detected</span>
              </div>
              <div className="name">—</div>
              <div className="muted" style={{ fontSize: 12 }}>
                Could be a flat clip with no jumps, or the height threshold was too high.
              </div>
            </div>
          )}

          <div className="charts-head">
            <h4>Time series · synchronized</h4>
            <button className="btn btn-sm mono" onClick={() => setShowRaw(true)} title="View the full analysis payload (JSON.stringify)">{`{ raw json }`}</button>
          </div>

          <ChartCard title="Board yaw" yLabel="degrees" legend={[{ name: "yaw (unwrapped)", color: COLOR_YAW }]} readout={[["yaw", fmt(currentVal(series.yaw), "°")]]}>
            <Chart height={92} duration={duration} time={time} trickBands={trickBands} onSeek={seek} series={[{ name: "yaw", color: COLOR_YAW, data: series.yaw } as Series]} />
          </ChartCard>

          <ChartCard title="Jump height" yLabel="cm" legend={[{ name: "height", color: COLOR_JUMP }]} readout={[["h", fmt(currentVal(series.jump), " cm", 0)]]}>
            <Chart height={84} duration={duration} time={time} trickBands={trickBands} onSeek={seek} fillUnderIdx={0} series={[{ name: "height", color: COLOR_JUMP, data: series.jump } as Series]} />
          </ChartCard>

          <ChartCard
            title="Knee angles"
            yLabel="degrees"
            legend={[
              { name: "L", color: COLOR_KNEEL },
              { name: "R", color: COLOR_KNEER }
            ]}
            readout={[
              ["L", fmt(currentVal(series.kneeL), "°", 0)],
              ["R", fmt(currentVal(series.kneeR), "°", 0)]
            ]}
          >
            <Chart
              height={84}
              duration={duration}
              time={time}
              trickBands={trickBands}
              onSeek={seek}
              series={
                [
                  { name: "L", color: COLOR_KNEEL, data: series.kneeL },
                  { name: "R", color: COLOR_KNEER, data: series.kneeR }
                ] as Series[]
              }
            />
          </ChartCard>

          <ChartCard
            title="Board flip signal"
            yLabel="px"
            legend={[
              { name: "mean (L+R)/2", color: COLOR_FLIP_MEAN },
              { name: "L wheels", color: COLOR_FLIP_L },
              { name: "R wheels", color: COLOR_FLIP_R },
              { name: "diff (L−R)", color: COLOR_FLIP_DIFF }
            ]}
            readout={[
              ["mean", fmt(currentVal(series.flipMean), "", 0)],
              ["Δ", fmt(currentVal(series.flipDiff), "", 0)]
            ]}
          >
            <Chart
              height={110}
              duration={duration}
              time={time}
              trickBands={trickBands}
              onSeek={seek}
              series={
                [
                  { name: "mean", color: COLOR_FLIP_MEAN, data: series.flipMean, width: 1.5 },
                  { name: "L", color: COLOR_FLIP_L, data: series.flipL, width: 1.0, opacity: 0.85 },
                  { name: "R", color: COLOR_FLIP_R, data: series.flipR, width: 1.0, opacity: 0.85 },
                  { name: "L−R", color: COLOR_FLIP_DIFF, data: series.flipDiff, width: 1.3, dashed: true, opacity: 0.9 }
                ] as Series[]
              }
            />
          </ChartCard>

          <ChartCard
            title="Body rotation"
            yLabel="norm dx"
            legend={[
              { name: "wrists", color: COLOR_WRIST },
              { name: "shoulders", color: COLOR_SHOULDER },
              { name: "hips", color: COLOR_HIP },
              { name: "ankles", color: COLOR_ANKLE }
            ]}
            readout={[
              ["S", fmt(currentVal(series.shoulder), "", 2)],
              ["H", fmt(currentVal(series.hip), "", 2)]
            ]}
          >
            <Chart
              height={110}
              duration={duration}
              time={time}
              trickBands={trickBands}
              onSeek={seek}
              series={
                [
                  { name: "wrists", color: COLOR_WRIST, data: series.wrist, width: 1.2, opacity: 0.85 },
                  { name: "shoulders", color: COLOR_SHOULDER, data: series.shoulder, width: 1.4 },
                  { name: "hips", color: COLOR_HIP, data: series.hip, width: 1.4 },
                  { name: "ankles", color: COLOR_ANKLE, data: series.ankle, width: 1.2, opacity: 0.85 }
                ] as Series[]
              }
            />
          </ChartCard>

          {trickBands.length > 0 && (
            <div style={{ display: "flex", gap: 8, marginTop: 6, marginBottom: 24, color: "var(--muted)", fontSize: 11.5, alignItems: "center" }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  background: "color-mix(in oklch, var(--accent) 35%, transparent)",
                  border: "1px solid color-mix(in oklch, var(--accent) 60%, transparent)"
                }}
              />
              <span>
                Highlighted band{trickBands.length > 1 ? "s" : ""} = detected trick interval
                {trickBands.length === 1 && ` (${fmtClock(trickBands[0][0])}–${fmtClock(trickBands[0][1])})`}
              </span>
            </div>
          )}
        </div>
      </div>

      <RawJsonModal open={showRaw} onClose={() => setShowRaw(false)} data={analysis} title={`Raw analysis · ${videoName}`} />
    </div>
  )
}

export function Viewer() {
  const router = useRouter()
  const [stored, setStored] = useState<ReturnType<typeof getAnalysis>>(null)

  useEffect(() => {
    const s = getAnalysis()
    if (!s) {
      router.replace("/")
      return
    }
    setStored(s)
  }, [router])

  if (!stored) return null
  return <ViewerInner analysis={stored.analysis} videoUrl={stored.videoUrl} videoName={stored.videoName} />
}
