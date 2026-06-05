import type { Timeline } from "./types"

export interface OverlayToggles {
  skeleton: boolean
  board: boolean
  mask: boolean
  pcaKpts: boolean
  pcaSeg: boolean
  knee: boolean
  com: boolean
  skateCom: boolean
  comOffset: boolean
}

// Human-readable names — mirror skate_analysis/constants.py for hover labels.
const COCO_KEYPOINT_NAMES = ["nose", "left eye", "right eye", "left ear", "right ear", "left shoulder", "right shoulder", "left elbow", "right elbow", "left wrist", "right wrist", "left hip", "right hip", "left knee", "right knee", "left ankle", "right ankle"]

const SKATE_KEYPOINT_NAMES = ["nose", "tail", "front left wheel", "front right wheel", "back left wheel", "back right wheel"]

export type HoverState = { kind: "skate" | "human"; index: number }

// COCO 17-point skeleton connections (subset used by the model).
const COCO_SKELETON: [number, number][] = [
  [5, 7],
  [7, 9], // left arm
  [6, 8],
  [8, 10], // right arm
  [5, 6], // shoulders
  [5, 11],
  [6, 12], // torso
  [11, 12], // hips
  [11, 13],
  [13, 15], // left leg
  [12, 14],
  [14, 16] // right leg
]

const COCO = {
  LEFT_SHOULDER: 5,
  RIGHT_SHOULDER: 6,
  LEFT_ELBOW: 7,
  RIGHT_ELBOW: 8,
  LEFT_WRIST: 9,
  RIGHT_WRIST: 10,
  LEFT_HIP: 11,
  RIGHT_HIP: 12,
  LEFT_KNEE: 13,
  RIGHT_KNEE: 14,
  LEFT_ANKLE: 15,
  RIGHT_ANKLE: 16
}

const COLORS = {
  skeleton: "oklch(0.86 0.23 145)",
  board: "oklch(0.88 0.20 80)",
  mask: "oklch(0.74 0.20 25)",
  pcaKpts: "oklch(0.80 0.22 320)",
  pcaSeg: "oklch(0.82 0.18 200)",
  knee: "oklch(0.85 0.18 205)",
  com: "oklch(0.97 0 0)",
  skateCom: "oklch(0.88 0.20 80)"
}

interface RenderedRect {
  offsetX: number
  offsetY: number
  width: number
  height: number
}

/**
 * Compute the rectangle the video occupies inside its element
 */
export function videoRenderedRect(video: HTMLVideoElement): RenderedRect | null {
  const vw = video.videoWidth
  const vh = video.videoHeight
  if (!vw || !vh) return null
  const er = video.getBoundingClientRect()
  const ew = er.width
  const eh = er.height
  const videoAR = vw / vh
  const elemAR = ew / eh
  let renderedW: number, renderedH: number, offsetX: number, offsetY: number
  if (videoAR > elemAR) {
    renderedW = ew
    renderedH = ew / videoAR
    offsetX = 0
    offsetY = (eh - renderedH) / 2
  } else {
    renderedW = eh * videoAR
    renderedH = eh
    offsetX = (ew - renderedW) / 2
    offsetY = 0
  }
  return { offsetX, offsetY, width: renderedW, height: renderedH }
}

/**
 * Find the timeline index whose frame_number is closest to the target frame.
 */
export function findFrameIdx(timeline: Timeline, currentTime: number, fps: number): number {
  if (timeline.frame_numbers.length === 0) return -1
  const target = Math.round(currentTime * fps)
  const fns = timeline.frame_numbers
  // Fast path: frame_step=1 → index === frame number
  if (fns.length > 1 && fns[1] - fns[0] === 1) {
    return Math.max(0, Math.min(fns.length - 1, target))
  }
  // Binary search
  let lo = 0,
    hi = fns.length - 1
  while (lo < hi) {
    const mid = (lo + hi) >>> 1
    if (fns[mid] < target) lo = mid + 1
    else hi = mid
  }
  // pick lo or lo-1 — whichever is closer
  if (lo > 0 && Math.abs(fns[lo - 1] - target) < Math.abs(fns[lo] - target)) lo -= 1
  return lo
}

export function drawOverlay(canvas: HTMLCanvasElement, video: HTMLVideoElement, ctx: CanvasRenderingContext2D, timeline: Timeline, fps: number, toggles: OverlayToggles, hover: HoverState | null = null): void {
  const rect = videoRenderedRect(video)
  if (!rect) return

  const dpr = window.devicePixelRatio || 1
  const elemRect = video.getBoundingClientRect()
  const cssW = elemRect.width
  const cssH = elemRect.height
  if (canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
    canvas.width = Math.round(cssW * dpr)
    canvas.height = Math.round(cssH * dpr)
    canvas.style.width = `${cssW}px`
    canvas.style.height = `${cssH}px`
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, cssW, cssH)

  const idx = findFrameIdx(timeline, video.currentTime, fps)
  if (idx < 0) return

  const vw = video.videoWidth || 1
  const vh = video.videoHeight || 1
  const sx = rect.width / vw
  const sy = rect.height / vh
  const map = (x: number, y: number): [number, number] => [rect.offsetX + x * sx, rect.offsetY + y * sy]

  const skate = timeline.skate_keypoints[idx] // (6, 2)
  const human = timeline.human_keypoints[idx] // (17, 3) [x, y, conf]
  const pcaKpts = timeline.board_kpts_pca?.[idx] ?? null
  const pcaSeg = timeline.board_seg_pca?.[idx] ?? null
  const contour = timeline.board_seg_contour?.[idx] ?? null

  // Human CoM in original-frame pixels
  let humanCom: [number, number] | null = null
  if (human) {
    let sx2 = 0,
      sy2 = 0,
      n = 0
    for (let i = 5; i < 17; i++) {
      const p = human[i]
      if (!p || p[2] < 0.3) continue
      sx2 += p[0]
      sy2 += p[1]
      n += 1
    }
    if (n > 0) humanCom = [sx2 / n, sy2 / n]
  }

  // Board CoM (kpts PCA centroid preferred, seg PCA fallback)
  const boardCom: [number, number] | null = pcaKpts?.centroid ?? pcaSeg?.centroid ?? null

  // Board mask: real segmentation contour polygon
  if (toggles.mask && contour && contour.length >= 3) {
    ctx.beginPath()
    contour.forEach((p, i) => {
      const [x, y] = map(p[0], p[1])
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.closePath()
    ctx.fillStyle = "oklch(0.74 0.20 25 / 0.32)"
    ctx.fill()
    ctx.strokeStyle = "oklch(0.74 0.20 25 / 0.7)"
    ctx.lineWidth = 1.2
    ctx.stroke()
  }

  // Human skeleton
  if (toggles.skeleton && human) {
    ctx.strokeStyle = COLORS.skeleton
    ctx.lineWidth = 2
    ctx.lineCap = "round"
    for (const [i, j] of COCO_SKELETON) {
      const a = human[i],
        b = human[j]
      if (!a || !b) continue
      if (a[2] < 0.3 || b[2] < 0.3) continue
      const [ax, ay] = map(a[0], a[1])
      const [bx, by] = map(b[0], b[1])
      ctx.beginPath()
      ctx.moveTo(ax, ay)
      ctx.lineTo(bx, by)
      ctx.stroke()
    }
    ctx.fillStyle = COLORS.skeleton
    for (let i = 5; i < 17; i++) {
      const p = human[i]
      if (!p || p[2] < 0.3) continue
      const [x, y] = map(p[0], p[1])
      ctx.beginPath()
      ctx.arc(x, y, 2.4, 0, Math.PI * 2)
      ctx.fill()
    }
    // Nose
    if (human[0] && human[0][2] >= 0.3) {
      const [x, y] = map(human[0][0], human[0][1])
      ctx.fillStyle = "oklch(0.72 0.22 25)"
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  // Board skeleton
  if (toggles.board && skate) {
    ctx.strokeStyle = COLORS.board
    ctx.lineWidth = 1.6
    // Nose-tail axis
    const nose = skate[0],
      tail = skate[1]
    if (nose && tail && (nose[0] !== 0 || nose[1] !== 0) && (tail[0] !== 0 || tail[1] !== 0)) {
      const [nx, ny] = map(nose[0], nose[1])
      const [tx, ty] = map(tail[0], tail[1])
      ctx.beginPath()
      ctx.moveTo(nx, ny)
      ctx.lineTo(tx, ty)
      ctx.stroke()
    }
    // Wheel pairs
    const conns: [number, number][] = [
      [2, 3],
      [4, 5]
    ]
    for (const [i, j] of conns) {
      const a = skate[i],
        b = skate[j]
      if (!a || !b) continue
      if ((a[0] === 0 && a[1] === 0) || (b[0] === 0 && b[1] === 0)) continue
      const [ax, ay] = map(a[0], a[1])
      const [bx, by] = map(b[0], b[1])
      ctx.beginPath()
      ctx.moveTo(ax, ay)
      ctx.lineTo(bx, by)
      ctx.stroke()
    }
    // Keypoint dots
    ctx.fillStyle = COLORS.board
    for (const p of skate) {
      if (!p || (p[0] === 0 && p[1] === 0)) continue
      const [x, y] = map(p[0], p[1])
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  // PCA from keypoints
  if (toggles.pcaKpts && pcaKpts) {
    drawPca(ctx, pcaKpts, COLORS.pcaKpts, "kpts", map)
  }

  // PCA from segmentation
  if (toggles.pcaSeg && pcaSeg) {
    drawPca(ctx, pcaSeg, COLORS.pcaSeg, "seg", map)
  }

  // Skateboard CoM (PCA centroid, kpts preferred)
  if (toggles.skateCom && boardCom) {
    const [x, y] = map(boardCom[0], boardCom[1])
    ctx.strokeStyle = COLORS.skateCom
    ctx.lineWidth = 1.4
    ctx.beginPath()
    ctx.arc(x, y, 8, 0, Math.PI * 2)
    ctx.stroke()
    ctx.fillStyle = "oklch(0 0 0 / 0.4)"
    ctx.beginPath()
    ctx.arc(x, y, 8, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = COLORS.skateCom
    ctx.beginPath()
    ctx.arc(x, y, 2.4, 0, Math.PI * 2)
    ctx.fill()
    ctx.font = "11px 'IBM Plex Mono', monospace"
    ctx.lineWidth = 3
    ctx.strokeStyle = "oklch(0 0 0 / 0.55)"
    ctx.strokeText("board CoM", x + 11, y + 4)
    ctx.fillText("board CoM", x + 11, y + 4)
  }

  // CoM offset
  if (toggles.comOffset && humanCom && boardCom) {
    const [hx, hy] = map(humanCom[0], humanCom[1])
    const [bx, by] = map(boardCom[0], boardCom[1])

    const precomputed = timeline.com_offset_px?.[idx]
    const dist = precomputed != null && isFinite(precomputed) ? precomputed : Math.hypot(humanCom[0] - boardCom[0], humanCom[1] - boardCom[1])

    ctx.strokeStyle = COLORS.com
    ctx.lineWidth = 1.4
    ctx.setLineDash([4, 3])
    ctx.beginPath()
    ctx.moveTo(hx, hy)
    ctx.lineTo(bx, by)
    ctx.stroke()
    ctx.setLineDash([])

    const mx = (hx + bx) / 2
    const my = (hy + by) / 2
    const text = `${Math.round(dist)} px`
    ctx.font = "11px 'IBM Plex Mono', monospace"
    ctx.lineWidth = 3
    ctx.strokeStyle = "oklch(0 0 0 / 0.7)"
    ctx.strokeText(text, mx + 6, my - 4)
    ctx.fillStyle = COLORS.com
    ctx.fillText(text, mx + 6, my - 4)
  }

  // Knee angle labels
  if (toggles.knee && human) {
    const kL = human[COCO.LEFT_KNEE]
    const kR = human[COCO.RIGHT_KNEE]
    const aL = jointAngle(human, COCO.LEFT_HIP, COCO.LEFT_KNEE, COCO.LEFT_ANKLE)
    const aR = jointAngle(human, COCO.RIGHT_HIP, COCO.RIGHT_KNEE, COCO.RIGHT_ANKLE)

    ctx.font = "11px 'IBM Plex Mono', monospace"
    const drawL = (k: number[] | undefined, angle: number | null, label: string) => {
      if (!k || k[2] < 0.3 || angle == null) return
      const [x, y] = map(k[0], k[1])
      const text = `${label} ${Math.round(angle)}°`
      ctx.lineWidth = 3
      ctx.strokeStyle = "oklch(0 0 0 / 0.55)"
      ctx.strokeText(text, x + 8, y)
      ctx.fillStyle = COLORS.knee
      ctx.fillText(text, x + 8, y)
      ctx.strokeStyle = COLORS.knee
      ctx.lineWidth = 1.2
      ctx.beginPath()
      ctx.arc(x, y, 9, -0.5, 1.2)
      ctx.stroke()
    }
    drawL(kL, aL, "L")
    drawL(kR, aR, "R")
  }

  // Body CoM
  if (toggles.com && humanCom) {
    const [x, y] = map(humanCom[0], humanCom[1])
    ctx.strokeStyle = COLORS.com
    ctx.lineWidth = 1.4
    ctx.beginPath()
    ctx.arc(x, y, 9, 0, Math.PI * 2)
    ctx.stroke()
    ctx.fillStyle = "oklch(0 0 0 / 0.4)"
    ctx.beginPath()
    ctx.arc(x, y, 9, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = COLORS.com
    ctx.beginPath()
    ctx.arc(x, y, 2.4, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = "oklch(0.97 0 0 / 0.4)"
    ctx.setLineDash([3, 3])
    ctx.beginPath()
    ctx.moveTo(x, y + 10)
    ctx.lineTo(x, y + 80)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = COLORS.com
    ctx.font = "11px 'IBM Plex Mono', monospace"
    ctx.fillText("CoM", x + 12, y + 4)
  }

  // Hover highlight
  if (hover) {
    if (hover.kind === "skate" && skate && toggles.board) {
      const p = skate[hover.index]
      if (p && (p[0] !== 0 || p[1] !== 0)) {
        const [x, y] = map(p[0], p[1])
        drawHoverHighlight(ctx, x, y, COLORS.board, SKATE_KEYPOINT_NAMES[hover.index] ?? `kp ${hover.index}`)
      }
    } else if (hover.kind === "human" && human && toggles.skeleton) {
      const p = human[hover.index]
      if (p && p[2] >= 0.3) {
        const [x, y] = map(p[0], p[1])
        const label = `${COCO_KEYPOINT_NAMES[hover.index] ?? `kp ${hover.index}`}  ${(p[2] * 100).toFixed(0)}%`
        drawHoverHighlight(ctx, x, y, COLORS.skeleton, label)
      }
    }
  }
}

/**
 * Hit-test the closest visible keypoint
 */
export function pickKeypoint(video: HTMLVideoElement, timeline: Timeline, fps: number, mouseX: number, mouseY: number, toggles: OverlayToggles, threshold = 14): HoverState | null {
  const rect = videoRenderedRect(video)
  if (!rect) return null
  const idx = findFrameIdx(timeline, video.currentTime, fps)
  if (idx < 0) return null

  const vw = video.videoWidth || 1
  const vh = video.videoHeight || 1
  const sx = rect.width / vw
  const sy = rect.height / vh
  const map = (x: number, y: number): [number, number] => [rect.offsetX + x * sx, rect.offsetY + y * sy]

  const skate = timeline.skate_keypoints[idx]
  const human = timeline.human_keypoints[idx]

  let best: HoverState | null = null
  let bestDist = threshold

  if (skate && toggles.board) {
    for (let i = 0; i < skate.length; i++) {
      const p = skate[i]
      if (!p || (p[0] === 0 && p[1] === 0)) continue
      const [mx, my] = map(p[0], p[1])
      const d = Math.hypot(mx - mouseX, my - mouseY)
      if (d < bestDist) {
        bestDist = d
        best = { kind: "skate", index: i }
      }
    }
  }

  if (human && toggles.skeleton) {
    for (let i = 0; i < human.length; i++) {
      const p = human[i]
      if (!p || p[2] < 0.3) continue
      const [mx, my] = map(p[0], p[1])
      const d = Math.hypot(mx - mouseX, my - mouseY)
      if (d < bestDist) {
        bestDist = d
        best = { kind: "human", index: i }
      }
    }
  }

  return best
}

function drawHoverHighlight(ctx: CanvasRenderingContext2D, x: number, y: number, color: string, label: string): void {
  // Enlarged dot with glow ring
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.arc(x, y, 9, 0, Math.PI * 2)
  ctx.stroke()
  ctx.fillStyle = "oklch(0 0 0 / 0.45)"
  ctx.beginPath()
  ctx.arc(x, y, 9, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.arc(x, y, 4, 0, Math.PI * 2)
  ctx.fill()

  // Label tooltip
  ctx.font = "11px 'IBM Plex Mono', monospace"
  const pad = 6
  const lh = 18
  const tw = ctx.measureText(label).width
  const lx = x + 12
  const ly = y - 12 - lh
  ctx.fillStyle = "oklch(0 0 0 / 0.82)"
  ctx.fillRect(lx, ly, tw + pad * 2, lh)
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.strokeRect(lx + 0.5, ly + 0.5, tw + pad * 2 - 1, lh - 1)
  ctx.fillStyle = "oklch(0.97 0 0)"
  ctx.textBaseline = "middle"
  ctx.fillText(label, lx + pad, ly + lh / 2 + 0.5)
  ctx.textBaseline = "alphabetic"
}

function jointAngle(human: number[][], hipI: number, kneeI: number, ankleI: number): number | null {
  const h = human[hipI],
    k = human[kneeI],
    a = human[ankleI]
  if (!h || !k || !a || h[2] < 0.3 || k[2] < 0.3 || a[2] < 0.3) return null
  const v1x = h[0] - k[0],
    v1y = h[1] - k[1]
  const v2x = a[0] - k[0],
    v2y = a[1] - k[1]
  const dot = v1x * v2x + v1y * v2y
  const mag = Math.sqrt(v1x * v1x + v1y * v1y) * Math.sqrt(v2x * v2x + v2y * v2y) + 1e-8
  const c = Math.max(-1, Math.min(1, dot / mag))
  return (Math.acos(c) * 180) / Math.PI
}

function drawPca(ctx: CanvasRenderingContext2D, pca: { centroid: [number, number]; eigenvalues: [number, number]; eigenvectors: [[number, number], [number, number]] }, color: string, label: string, map: (x: number, y: number) => [number, number]): void {
  const [cx, cy] = map(pca.centroid[0], pca.centroid[1])

  for (let i = 0; i < 2; i++) {
    const vec = pca.eigenvectors[i]
    const len = Math.sqrt(Math.max(pca.eigenvalues[i], 0)) * 2
    const tipX = pca.centroid[0] + vec[0] * len
    const tipY = pca.centroid[1] + vec[1] * len
    const [tx, ty] = map(tipX, tipY)

    ctx.strokeStyle = i === 0 ? color : `color-mix(in oklch, ${color} 55%, transparent)`
    ctx.lineWidth = i === 0 ? 1.6 : 1.2
    ctx.setLineDash(i === 0 ? [] : [3, 3])
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(tx, ty)
    ctx.stroke()
    ctx.setLineDash([])

    // Arrowhead on PC1
    if (i === 0) {
      const angle = Math.atan2(ty - cy, tx - cx)
      const ah = 7
      ctx.beginPath()
      ctx.moveTo(tx, ty)
      ctx.lineTo(tx - ah * Math.cos(angle - 0.4), ty - ah * Math.sin(angle - 0.4))
      ctx.moveTo(tx, ty)
      ctx.lineTo(tx - ah * Math.cos(angle + 0.4), ty - ah * Math.sin(angle + 0.4))
      ctx.stroke()
    }
  }

  // Centroid dot
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.arc(cx, cy, 3.5, 0, Math.PI * 2)
  ctx.fill()
  ctx.strokeStyle = "oklch(1 0 0 / 0.6)"
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.arc(cx, cy, 5, 0, Math.PI * 2)
  ctx.stroke()

  // Label
  ctx.font = "11px 'IBM Plex Mono', monospace"
  ctx.lineWidth = 3
  ctx.strokeStyle = "oklch(0 0 0 / 0.55)"
  ctx.strokeText(label, cx + 7, cy - 7)
  ctx.fillStyle = color
  ctx.fillText(label, cx + 7, cy - 7)
}
