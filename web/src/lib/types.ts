// Mirror of skate_analysis/schemas.py (Pydantic v2 response models).

export type Direction = "ltr" | "rtl" | "toward" | "away" | "unknown"
export type Stance = "normal" | "switch" | "fakie" | "nollie" | "unknown"
export type FlipDir = "+" | "-"

export interface PcaPoint {
  centroid: [number, number]
  eigenvalues: [number, number]
  /** [[PC1x, PC1y], [PC2x, PC2y]] */
  eigenvectors: [[number, number], [number, number]]
}

export interface Timeline {
  times_s: number[]
  frame_numbers: number[]
  board_kpts_angle_deg: (number | null)[]
  board_seg_angle_deg: (number | null)[]
  angle_diff_deg: (number | null)[]
  board_yaw_deg: (number | null)[]
  height_cm: (number | null)[]
  com_height_cm: (number | null)[]
  left_knee_angle_deg: (number | null)[]
  right_knee_angle_deg: (number | null)[]
  com_offset_px: (number | null)[]
  wrist_dx: (number | null)[]
  shoulder_dx: (number | null)[]
  hip_dx: (number | null)[]
  ankle_dx: (number | null)[]
  flip_signal_mean: (number | null)[]
  flip_signal_left?: (number | null)[]
  flip_signal_right?: (number | null)[]
  flip_signal_diff: (number | null)[]
  skate_keypoints: (number[][] | null)[]
  human_keypoints: (number[][] | null)[]

  board_kpts_pca?: (PcaPoint | null)[]
  board_seg_pca?: (PcaPoint | null)[]
  board_seg_contour?: (number[][] | null)[]
}

export interface TrickReport {
  start_frame: number
  end_frame: number
  start_time_s: number
  end_time_s: number
  duration_s: number
  peak_frame: number
  peak_time_s: number
  peak_height_cm: number
  board_yaw_deg: number | null
  flip_count: number | null
  flip_dir: FlipDir | null
  wrist_rot_deg: number | null
  shoulder_rot_deg: number | null
  hip_rot_deg: number | null
  ankle_rot_deg: number | null
  trick_name: string
}

export interface AnalysisResponse {
  video_path: string
  annotated_video_path: string | null
  fps: number
  frame_count: number
  is_regular: boolean
  direction: Direction
  stance: Stance
  timeline: Timeline
  tricks: TrickReport[]
}

export interface StatsResponse {
  total_requests: number
  analyze_video_success: number
  analyze_video_failed: number
}
