"""Per-frame cv2 overlays drawn onto an RGB image."""

import cv2
import numpy as np

from ..config import KPT_CONF
from ..constants import (
    COCO_KEYPOINT_NAMES,
    COCO_SKELETON,
    SKATE_CONNECTIONS,
    SKATE_KEYPOINT_COLORS,
    SKATE_KEYPOINT_NAMES,
)
from ..data_structures import (
    BoardData,
    HumanData,
    HumanKeypoints,
    PCAResult,
    SkateAnalysis,
    SkateboardKeypoints,
)
from ..geometry import _pca_angle, is_valid_kp


def _draw_human_pose(vis: np.ndarray, human_kpts: HumanKeypoints | None) -> None:
    if human_kpts is None:
        return
    xy, conf = human_kpts.xy, human_kpts.conf
    for i, j in COCO_SKELETON:
        if conf[i] > KPT_CONF and conf[j] > KPT_CONF:
            cv2.line(vis,
                     (int(xy[i][0]), int(xy[i][1])),
                     (int(xy[j][0]), int(xy[j][1])),
                     (0, 255, 0), 2)
    for idx, ((x, y), c) in enumerate(zip(xy, conf)):
        if c > KPT_CONF:
            cv2.circle(vis, (int(x), int(y)), 3, (0, 255, 0), -1)
            cv2.putText(vis, COCO_KEYPOINT_NAMES[idx],
                        (int(x) + 4, int(y) - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1, cv2.LINE_AA)


def _draw_skate_segmentation(vis: np.ndarray, mask: np.ndarray | None) -> None:
    if mask is None:
        return
    overlay = np.zeros_like(vis)
    overlay[mask] = [255, 0, 0]
    vis[:] = cv2.addWeighted(vis, 1.0, overlay, 0.4, 0)


def _draw_skate_keypoints(
    vis:        np.ndarray,
    skate_kpts: SkateboardKeypoints | None,
    norm_kp:    np.ndarray | None = None,
) -> None:
    if norm_kp is not None:
        xy   = norm_kp
        conf = None
    elif skate_kpts is not None:
        xy   = skate_kpts.xy
        conf = skate_kpts.conf
    else:
        return

    board_int = xy.astype(int)
    for i, j in SKATE_CONNECTIONS:
        if conf is not None and (conf[i] < KPT_CONF or conf[j] < KPT_CONF):
            continue
        if not is_valid_kp(xy[i]) or not is_valid_kp(xy[j]):
            continue
        x1, y1 = board_int[i]; x2, y2 = board_int[j]
        cv2.line(vis, (x1, y1), (x2, y2), (255, 255, 0), 2)
    for idx, (x, y) in enumerate(board_int):
        if conf is not None and conf[idx] < KPT_CONF:
            continue
        if not is_valid_kp(xy[idx]):
            continue
        name  = SKATE_KEYPOINT_NAMES[idx]
        color = SKATE_KEYPOINT_COLORS[name]
        cv2.circle(vis, (x, y), 6, color, -1)
        cv2.putText(vis, name, (x + 6, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)


def _draw_pca(
    vis:            np.ndarray,
    pca:            PCAResult | None,
    pc1_color:      tuple[int, int, int],
    pc2_color:      tuple[int, int, int],
    centroid_color: tuple[int, int, int],
    label_prefix:   str,
) -> None:
    if pca is None:
        return
    cx, cy = int(pca.centroid[0]), int(pca.centroid[1])

    cv2.circle(vis, (cx, cy), 8, centroid_color, -1)
    cv2.circle(vis, (cx, cy), 10, (255, 255, 255), 2)
    cv2.putText(vis, f"centroid ({label_prefix})", (cx + 12, cy - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, centroid_color, 1, cv2.LINE_AA)

    angle  = _pca_angle(pca)
    labels = [
        f"PC1 ({label_prefix})  {angle:.1f}deg" if angle is not None else f"PC1 ({label_prefix})",
        f"PC2 ({label_prefix})",
    ]
    for i, (color, label) in enumerate(zip([pc1_color, pc2_color], labels)):
        vec    = pca.eigenvectors[:, i]
        length = np.sqrt(max(pca.eigenvalues[i], 0)) * 2
        ex = int(cx + vec[0] * length)
        ey = int(cy + vec[1] * length)
        cv2.arrowedLine(vis, (cx, cy), (ex, ey), color, 2, tipLength=0.25)
        cv2.putText(vis, label, (ex + 4, ey - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def _draw_angle_diff(vis: np.ndarray, board: BoardData) -> None:
    kpts_angle = board.kpts_angle
    seg_angle  = board.seg_angle
    diff       = board.angle_diff

    if kpts_angle is None and seg_angle is None:
        return

    if diff is None:
        diff_color = (180, 180, 180)
    elif diff < 10:
        diff_color = (0, 220, 0)
    elif diff < 20:
        diff_color = (255, 200, 0)
    else:
        diff_color = (255, 60, 60)

    lines = [
        (f"kpts: {kpts_angle:.1f}deg" if kpts_angle is not None else "kpts: n/a", (0, 200, 255)),
        (f"seg:  {seg_angle:.1f}deg"  if seg_angle  is not None else "seg:  n/a",  (0, 255, 100)),
        (f"diff: {diff:.1f}deg"       if diff       is not None else "diff: n/a",  diff_color),
    ]
    x, y = 12, 30
    for text, color in lines:
        cv2.putText(vis, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(vis, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color,     1, cv2.LINE_AA)
        y += 26


def _draw_human_metrics(vis: np.ndarray, human: HumanData) -> None:
    if human.com is None:
        return
    cx, cy = int(human.com[0]), int(human.com[1])

    cv2.circle(vis, (cx, cy), 10, (0, 0, 0),       -1)
    cv2.circle(vis, (cx, cy), 10, (255, 255, 255),  2)
    cv2.circle(vis, (cx, cy),  4, (255, 255, 255), -1)
    cv2.putText(vis, "CoM", (cx + 13, cy - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    if human.com_offset is not None:
        bx = int(cx - human.com_offset[0])
        by = int(cy - human.com_offset[1])
        dist = float(np.linalg.norm(human.com_offset))
        cv2.line(vis, (cx, cy), (bx, by), (255, 255, 255), 1, cv2.LINE_AA)
        mx, my = (cx + bx) // 2, (cy + by) // 2
        cv2.putText(vis, f"{dist:.0f}px", (mx + 4, my - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    for angle, pos, label in [
        (human.left_knee_angle,  human.left_knee_pos,  "L"),
        (human.right_knee_angle, human.right_knee_pos, "R"),
    ]:
        if angle is None or pos is None:
            continue
        kx, ky = int(pos[0]), int(pos[1])
        if angle < 100:
            color = (180, 180, 180)
        elif angle < 160:
            color = (255, 255, 255)
        else:
            color = (255, 220, 0)
        text = f"{label}: {angle:.0f}deg"
        cv2.putText(vis, text, (kx + 6, ky - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(vis, text, (kx + 6, ky - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color,     1, cv2.LINE_AA)


def render_frame(
    frame_bgr:               np.ndarray,
    result:                  SkateAnalysis,
    show_human_pose:         bool = True,
    show_skate_segmentation: bool = True,
    show_skate_keypoints:    bool = True,
    show_kpts_pca:           bool = True,
    show_seg_pca:            bool = True,
    show_angle_diff:         bool = True,
    show_human_metrics:      bool = True,
) -> np.ndarray:
    """Render all annotations onto a BGR frame.

    Uses result.norm_kpts for skateboard keypoints if populated (via
    apply_norm_keypoints), otherwise falls back to raw model output.

    Returns annotated RGB image (H x W x 3, uint8).
    """
    vis = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    if show_human_pose:
        _draw_human_pose(vis, result.human_kpts)
    if show_skate_segmentation:
        _draw_skate_segmentation(vis, result.skate_mask)
    if show_skate_keypoints:
        _draw_skate_keypoints(vis, result.skate_kpts, norm_kp=result.norm_kpts)
    if show_kpts_pca:
        _draw_pca(vis, result.board.kpts_pca,
                  pc1_color=(0, 200, 255), pc2_color=(255, 0, 200),
                  centroid_color=(255, 165, 0), label_prefix="kpts")
    if show_seg_pca:
        _draw_pca(vis, result.board.seg_pca,
                  pc1_color=(0, 255, 100), pc2_color=(180, 255, 0),
                  centroid_color=(255, 255, 255), label_prefix="seg")
    if show_angle_diff:
        _draw_angle_diff(vis, result.board)
    if show_human_metrics:
        _draw_human_metrics(vis, result.human)

    return vis
