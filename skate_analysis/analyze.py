from pathlib import Path

import cv2
import numpy as np

from .config import BOARD_LENGTH_CM, HEIGHT_THRESHOLD_CM, INFERENCE_CONF, INFERENCE_IOU, KPT_CONF
from .data_structures import (
    BoardData,
    HumanData,
    HumanKeypoints,
    PCAResult,
    SkateAnalysis,
    SkateboardKeypoints,
    VideoAnalysis,
)
from .geometry import (
    _board_flip_direction_signal,
    _board_flip_signal,
    _board_yaw_atan2_video,
    _joint_angle,
    _pca,
    _pca_angle,
)
from .models import (
    get_skateboard_pose_model,
    get_yolo_pose_model,
    get_yolo_seg_model,
)


# ── YOLO → numpy extractors (boundary code; the rest of the package
#   never touches Ultralytics objects after this point) ─────────────────


def _extract_skate_kpts(skate_pose_results) -> SkateboardKeypoints | None:
    """First detected board's keypoints + confidences (max_det=1 in practice)."""
    for r in skate_pose_results:
        if r.keypoints is None or len(r.keypoints.xy) == 0:
            continue
        xy = r.keypoints.xy.cpu().numpy()[0]
        conf = r.keypoints.conf.cpu().numpy()[0] if r.keypoints.conf is not None else None
        return SkateboardKeypoints(xy=xy, conf=conf)
    return None


def _extract_human_kpts(pose_results) -> HumanKeypoints | None:
    """First detected person's COCO-17 keypoints + confidences."""
    for r in pose_results:
        if r.keypoints is None or len(r.keypoints.xy) == 0:
            continue
        xy = r.keypoints.xy.cpu().numpy()[0]
        conf = r.keypoints.conf.cpu().numpy()[0]
        return HumanKeypoints(xy=xy, conf=conf)
    return None


def _extract_skate_mask(seg_results) -> np.ndarray | None:
    """First skateboard mask in the original frame's resolution, as bool (H, W)."""
    for r in seg_results:
        if r.masks is None:
            continue
        for mask, cls in zip(r.masks.data.cpu().numpy(), r.boxes.cls.cpu().numpy()):
            if r.names[int(cls)] != "skateboard":
                continue
            h, w = r.orig_shape
            resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
            return resized > 0.5
    return None


# ── Domain computations ────────────────────────────────────────────────


def _compute_kpts_pca(skate_kpts: SkateboardKeypoints | None):
    if skate_kpts is None:
        return None
    visible_idx = skate_kpts.visible(KPT_CONF)
    if len(visible_idx) < 2:
        return None
    return _pca(skate_kpts.xy[visible_idx])


def _compute_seg_pca(skate_mask: np.ndarray | None):
    if skate_mask is None:
        return None
    coords = np.argwhere(skate_mask)
    if len(coords) < 2:
        return None
    return _pca(coords[:, [1, 0]].astype(float))


def _compute_board(
    skate_kpts: SkateboardKeypoints | None,
    skate_mask: np.ndarray | None,
) -> BoardData:
    kpts_pca = _compute_kpts_pca(skate_kpts)
    seg_pca  = _compute_seg_pca(skate_mask)
    return BoardData(
        kpts_pca=kpts_pca,
        seg_pca=seg_pca,
        kpts_angle=_pca_angle(kpts_pca),
        seg_angle=_pca_angle(seg_pca),
    )


def _compute_human(human_kpts: HumanKeypoints | None, board: BoardData) -> HumanData:
    """Compute CoM, knee angles, and body-segment yaw angles from COCO pose keypoints."""
    if human_kpts is None:
        return HumanData.empty()

    xy, conf = human_kpts.xy, human_kpts.conf
    board_centroid = board.centroid

    body_idx = list(range(5, 17)) # COCO keypoints 5-16 are the "body" keypoints (excluding face and hands)
    body_pts = xy[body_idx][conf[body_idx] >= KPT_CONF] # only include body keypoints with sufficient confidence
    com = body_pts.mean(axis=0) if len(body_pts) > 0 else None

    com_offset = com - board_centroid if com is not None and board_centroid is not None else None

    def knee_data(hip_i, knee_i, ankle_i):
        if conf[hip_i] >= KPT_CONF and conf[knee_i] >= KPT_CONF and conf[ankle_i] >= KPT_CONF:
            return _joint_angle(xy[hip_i], xy[knee_i], xy[ankle_i]), xy[knee_i].copy()
        return None, None

    def pair_dx(i_left, i_right):
        if conf[i_left] >= KPT_CONF and conf[i_right] >= KPT_CONF:
            return float(xy[i_right][0] - xy[i_left][0])
        return None

    l_angle, l_pos = knee_data(11, 13, 15)
    r_angle, r_pos = knee_data(12, 14, 16)

    return HumanData(
        com=com,
        com_offset=com_offset,
        left_knee_angle=l_angle,
        right_knee_angle=r_angle,
        left_knee_pos=l_pos,
        right_knee_pos=r_pos,
        wrist_dx=pair_dx(9, 10),
        shoulder_dx=pair_dx(5, 6),
        hip_dx=pair_dx(11, 12),
        ankle_dx=pair_dx(15, 16),
    )


# ── Public API ─────────────────────────────────────────────────────────


def analyze_frame(
    frame: np.ndarray,
    conf:  float = INFERENCE_CONF,
    iou:   float = INFERENCE_IOU,
) -> SkateAnalysis:
    """Run all models on a single BGR frame and return a numpy SkateAnalysis."""
    pose_results       = get_yolo_pose_model().predict(frame, conf=conf, verbose=False)
    seg_results        = get_yolo_seg_model().predict(frame, conf=conf, iou=iou, verbose=False)
    skate_pose_results = get_skateboard_pose_model().predict(frame, conf=conf, iou=iou, max_det=1, verbose=False)

    skate_kpts = _extract_skate_kpts(skate_pose_results)
    human_kpts = _extract_human_kpts(pose_results)
    skate_mask = _extract_skate_mask(seg_results)

    board = _compute_board(skate_kpts, skate_mask)
    human = _compute_human(human_kpts, board)
    return SkateAnalysis(
        skate_kpts=skate_kpts,
        human_kpts=human_kpts,
        skate_mask=skate_mask,
        board=board,
        human=human,
    )


def analyze_video(
    video_path: str,
    conf:       float = INFERENCE_CONF,
    iou:        float = INFERENCE_IOU,
    frame_step: int   = 1,
) -> VideoAnalysis:
    """Process a video file frame by frame.

    Returns a VideoAnalysis. The object is iterable so callers can still
    unpack as `analyses, frame_numbers, fps = analyze_video(...)`.
    """
    # initialize video capture
    cap   = cv2.VideoCapture(video_path)

    # check if video opened successfully
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        raise IOError(f"Could not open video: {video_path}")

    # get video FPS and total frame count
    fps   = cap.get(cv2.CAP_PROP_FPS)

    analyses:      list[SkateAnalysis] = []
    frame_numbers: list[int]           = []
    frame_idx = 0

    while True:
        # read next frame
        ret, frame = cap.read()

        # if frame read failed exit loop
        if not ret:
            break

        # process frame if it's on the desired step
        if frame_idx % frame_step == 0:
            analyses.append(analyze_frame(frame, conf, iou))
            frame_numbers.append(frame_idx)

        frame_idx += 1

    cap.release()
    return VideoAnalysis(analyses=analyses, frame_numbers=frame_numbers, fps=fps)


# ── High-level orchestration (JSON-ready) ──────────────────────────────


def _nan_to_none(values):
    """Convert a 1-D numeric iterable (with NaNs) to Python floats or None."""
    return [None if v != v else float(v) for v in values]


def _pca_to_dict(p: PCAResult | None) -> dict | None:
    if p is None:
        return None
    return {
        "centroid":     [float(x) for x in p.centroid.tolist()],
        "eigenvalues":  [float(x) for x in p.eigenvalues.tolist()],
        "eigenvectors": [[float(p.eigenvectors[0, 0]), float(p.eigenvectors[1, 0])],
                         [float(p.eigenvectors[0, 1]), float(p.eigenvectors[1, 1])]],
    }


def _seg_contour(mask: np.ndarray | None) -> list[list[float]] | None:
    """Largest external contour of `mask` as a polygon of [x, y] points."""
    if mask is None:
        return None
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    return [[float(pt[0][0]), float(pt[0][1])] for pt in biggest]


def _build_timeline(
    analyses:        list[SkateAnalysis],
    frame_numbers:   list[int],
    fps:             float,
    board_length_cm: float,
) -> dict:
    """Per-frame time-series data for frontend charts."""
    from .detection import _compute_jump_height

    times_s = [fn / fps for fn in frame_numbers]

    kpts_angle = [a.board.kpts_angle for a in analyses]
    seg_angle  = [a.board.seg_angle  for a in analyses]
    angle_diff = [a.board.angle_diff for a in analyses]

    left_knee  = [a.human.left_knee_angle  for a in analyses]
    right_knee = [a.human.right_knee_angle for a in analyses]
    com_offset = [
        float(np.linalg.norm(a.human.com_offset)) if a.human.com_offset is not None else None
        for a in analyses
    ]

    wrist_dx    = [a.human.wrist_dx    for a in analyses]
    shoulder_dx = [a.human.shoulder_dx for a in analyses]
    hip_dx      = [a.human.hip_dx      for a in analyses]
    ankle_dx    = [a.human.ankle_dx    for a in analyses]

    height_cm, com_height_cm, _, _ = _compute_jump_height(analyses, board_length_cm)

    yaw_unwrapped, _, _ = _board_yaw_atan2_video(analyses)

    flip_mean  = np.full(len(analyses), np.nan)
    flip_left  = np.full(len(analyses), np.nan)
    flip_right = np.full(len(analyses), np.nan)
    flip_diff  = np.full(len(analyses), np.nan)
    for i, a in enumerate(analyses):
        if a.norm_kpts is None:
            continue
        fm = _board_flip_signal(a.norm_kpts)
        if fm is not None:
            flip_mean[i] = fm
        lp, rp, fd = _board_flip_direction_signal(a.norm_kpts)
        if lp is not None: flip_left[i]  = lp
        if rp is not None: flip_right[i] = rp
        if fd is not None: flip_diff[i]  = fd

    skate_kpts = [
        a.norm_kpts.tolist() if a.norm_kpts is not None else None
        for a in analyses
    ]
    human_kpts = [
        [[float(x), float(y), float(c)] for (x, y), c in zip(a.human_kpts.xy, a.human_kpts.conf)]
        if a.human_kpts is not None else None
        for a in analyses
    ]

    board_kpts_pca = [_pca_to_dict(a.board.kpts_pca) for a in analyses]
    board_seg_pca  = [_pca_to_dict(a.board.seg_pca)  for a in analyses]
    board_seg_contour = [_seg_contour(a.skate_mask) for a in analyses]

    return {
        "times_s":              [float(t) for t in times_s],
        "frame_numbers":        [int(fn) for fn in frame_numbers],
        "board_kpts_angle_deg": [None if v is None else float(v) for v in kpts_angle],
        "board_seg_angle_deg":  [None if v is None else float(v) for v in seg_angle],
        "angle_diff_deg":       [None if v is None else float(v) for v in angle_diff],
        "board_yaw_deg":        _nan_to_none(yaw_unwrapped),
        "height_cm":            _nan_to_none(height_cm),
        "com_height_cm":        _nan_to_none(com_height_cm),
        "left_knee_angle_deg":  [None if v is None else float(v) for v in left_knee],
        "right_knee_angle_deg": [None if v is None else float(v) for v in right_knee],
        "com_offset_px":        [None if v is None else float(v) for v in com_offset],
        "wrist_dx":             [None if v is None else float(v) for v in wrist_dx],
        "shoulder_dx":          [None if v is None else float(v) for v in shoulder_dx],
        "hip_dx":               [None if v is None else float(v) for v in hip_dx],
        "ankle_dx":             [None if v is None else float(v) for v in ankle_dx],
        "flip_signal_mean":     _nan_to_none(flip_mean),
        "flip_signal_left":     _nan_to_none(flip_left),
        "flip_signal_right":    _nan_to_none(flip_right),
        "flip_signal_diff":     _nan_to_none(flip_diff),
        "skate_keypoints":      skate_kpts,
        "human_keypoints":      human_kpts,
        "board_kpts_pca":       board_kpts_pca,
        "board_seg_pca":        board_seg_pca,
        "board_seg_contour":    board_seg_contour,
    }


def _build_trick_reports(
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    fps:           float,
    tricks:        list,
    stance:        str,
    is_regular:    bool,
    yaw_series:    np.ndarray,
) -> list[dict]:
    from .classification import classify_trick
    from .rotations import compute_body_rotation, compute_trick_rotations

    reports: list[dict] = []
    for t in tricks:
        rot = compute_trick_rotations(
            analyses, t, frame_numbers, fps, yaw_series=yaw_series,
        )
        yaw_sign = 1 if (rot["yaw_deg"] is None or rot["yaw_deg"] >= 0) else -1
        brot = compute_body_rotation(analyses, t, frame_numbers, fps, yaw_sign=yaw_sign)

        body_rot = (brot.get("shoulder_rot_deg") or brot.get("hip_rot_deg")
                    or brot.get("wrist_rot_deg")  or brot.get("ankle_rot_deg"))
        name = classify_trick(
            rot["yaw_deg"], rot["flip_count"], body_rot, stance, is_regular,
        )
        reports.append({
            "start_frame":      int(t.start_frame),
            "end_frame":        int(t.end_frame),
            "start_time_s":     float(t.start_time),
            "end_time_s":       float(t.end_time),
            "duration_s":       float(t.duration_s),
            "peak_frame":       int(t.peak_frame),
            "peak_time_s":      float(t.peak_time),
            "peak_height_cm":   float(t.peak_height_cm),
            "board_yaw_deg":    None if rot["yaw_deg"] is None else float(rot["yaw_deg"]),
            "flip_count":       rot["flip_count"],
            "flip_dir":         rot["flip_dir"],
            "wrist_rot_deg":    brot.get("wrist_rot_deg"),
            "shoulder_rot_deg": brot.get("shoulder_rot_deg"),
            "hip_rot_deg":      brot.get("hip_rot_deg"),
            "ankle_rot_deg":    brot.get("ankle_rot_deg"),
            "trick_name":       name,
        })
    return reports


def analyze(
    video_path:          str,
    is_regular:          bool  = True,
    board_length_cm:     float = BOARD_LENGTH_CM,
    height_threshold_cm: float = HEIGHT_THRESHOLD_CM,
    frame_step:          int   = 1,
) -> dict:
    """Run the full pipeline on a video and return a JSON-ready result dict.

    Result keys: video_path, fps, frame_count, is_regular, direction, stance,
    timeline (per-frame arrays), tricks (per-trick aggregates).
    """
    from .detection import (
        apply_norm_keypoints,
        detect_direction,
        detect_stance,
        detect_tricks,
        normalize_board_keypoints,
    )

    analyses, frame_numbers, fps = analyze_video(video_path, frame_step=frame_step)

    norm_kpts = normalize_board_keypoints(analyses, frame_numbers, fps)
    apply_norm_keypoints(analyses, norm_kpts)

    tricks    = detect_tricks(analyses, frame_numbers, fps,
                              board_length_cm=board_length_cm,
                              height_threshold_cm=height_threshold_cm)
    direction = detect_direction(analyses, frame_numbers, fps)
    stance    = detect_stance(analyses, frame_numbers, fps,
                              is_regular=is_regular, tricks=tricks,
                              direction=direction)

    yaw_series, _, _ = _board_yaw_atan2_video(analyses)

    timeline      = _build_timeline(analyses, frame_numbers, fps, board_length_cm)
    trick_reports = _build_trick_reports(
        analyses, frame_numbers, fps, tricks, stance, is_regular, yaw_series,
    )

    return {
        "video_path":  video_path,
        "fps":         float(fps),
        "frame_count": len(analyses),
        "is_regular":  is_regular,
        "direction":   direction,
        "stance":      stance,
        "timeline":    timeline,
        "tricks":      trick_reports,
    }


def analyze_with_video(
    video_path:            str,
    annotated_output_path: str,
    is_regular:            bool  = True,
    board_length_cm:       float = BOARD_LENGTH_CM,
    height_threshold_cm:   float = HEIGHT_THRESHOLD_CM,
    frame_step:            int   = 1,
) -> dict:
    """Same as analyze(), but also writes an annotated mp4 to annotated_output_path."""
    from .detection import (
        apply_norm_keypoints,
        detect_direction,
        detect_stance,
        detect_tricks,
        normalize_board_keypoints,
    )
    from .visualization import save_annotated_video

    analyses, frame_numbers, fps = analyze_video(video_path, frame_step=frame_step)

    norm_kpts = normalize_board_keypoints(analyses, frame_numbers, fps)
    apply_norm_keypoints(analyses, norm_kpts)

    tricks    = detect_tricks(analyses, frame_numbers, fps,
                              board_length_cm=board_length_cm,
                              height_threshold_cm=height_threshold_cm)
    direction = detect_direction(analyses, frame_numbers, fps)
    stance    = detect_stance(analyses, frame_numbers, fps,
                              is_regular=is_regular, tricks=tricks,
                              direction=direction)

    yaw_series, _, _ = _board_yaw_atan2_video(analyses)

    timeline      = _build_timeline(analyses, frame_numbers, fps, board_length_cm)
    trick_reports = _build_trick_reports(
        analyses, frame_numbers, fps, tricks, stance, is_regular, yaw_series,
    )

    save_annotated_video(
        video_path, analyses, frame_numbers, annotated_output_path,
    )

    return {
        "video_path":            video_path,
        "annotated_video_path":  annotated_output_path,
        "fps":                   float(fps),
        "frame_count":           len(analyses),
        "is_regular":            is_regular,
        "direction":             direction,
        "stance":                stance,
        "timeline":              timeline,
        "tricks":                trick_reports,
    }
