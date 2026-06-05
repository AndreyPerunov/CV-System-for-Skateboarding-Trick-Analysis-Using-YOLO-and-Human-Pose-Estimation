"""Matplotlib figures for inspecting pipeline output."""

import logging

import matplotlib.pyplot as plt
import numpy as np

from ..config import BOARD_LENGTH_CM, HEIGHT_THRESHOLD_CM
from ..data_structures import SkateAnalysis
from ..detection import _compute_jump_height, _find_jump_peaks, _find_trick_intervals

log = logging.getLogger(__name__)


def _nan_array(vals) -> np.ndarray:
    return np.array([v if v is not None else np.nan for v in vals], dtype=float)


def plot_metrics(
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    fps:           float,
    title:         str = "",
    figsize:       tuple[float, float] = (14, 10),
) -> None:
    """Plot time-series metrics from video analysis across all frames."""
    times = [fn / fps for fn in frame_numbers]

    kpts_angles = _nan_array([a.board.kpts_angle for a in analyses])
    seg_angles  = _nan_array([a.board.seg_angle  for a in analyses])
    angle_diffs = _nan_array([a.board.angle_diff for a in analyses])
    l_knee      = _nan_array([a.human.left_knee_angle  for a in analyses])
    r_knee      = _nan_array([a.human.right_knee_angle for a in analyses])
    com_offsets = _nan_array([
        float(np.linalg.norm(a.human.com_offset)) if a.human.com_offset is not None else np.nan
        for a in analyses
    ])

    with plt.style.context("dark_background"):
        fig, axes = plt.subplots(4, 1, figsize=figsize, sharex=True)
        fig.suptitle(title, fontsize=10, y=1.01)

        ax = axes[0]
        ax.plot(times, kpts_angles, color="#00C8FF", label="kpts angle", linewidth=1.5)
        ax.plot(times, seg_angles,  color="#00FF64", label="seg angle",  linewidth=1.5)
        ax.set_ylabel("degrees")
        ax.set_ylim(-90, 90)
        ax.set_title("Board angle")
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.legend(loc="upper right", fontsize=8)

        ax = axes[1]
        ax.axhspan( 0, 10, color="#00AA00", alpha=0.15)
        ax.axhspan(10, 20, color="#AAAA00", alpha=0.15)
        ax.axhspan(20, 90, color="#AA0000", alpha=0.15)
        ax.plot(times, angle_diffs, color="#FFAA00", linewidth=1.5, label="angle diff")
        ax.set_ylabel("degrees")
        ax.set_title("Angle difference  (kpts vs seg)")
        ax.legend(loc="upper right", fontsize=8)

        ax = axes[2]
        ax.plot(times, l_knee, color="#FF8C00", label="left knee",  linewidth=1.5)
        ax.plot(times, r_knee, color="#9370DB", label="right knee", linewidth=1.5)
        ax.set_ylabel("degrees")
        ax.set_ylim(0, 180)
        ax.set_title("Knee angles")
        ax.legend(loc="upper right", fontsize=8)

        ax = axes[3]
        ax.plot(times, com_offsets, color="#E0E0E0", linewidth=1.5, label="CoM offset")
        ax.set_ylabel("pixels")
        ax.set_xlabel("time (s)")
        ax.set_title("CoM offset from board centroid")
        ax.legend(loc="upper right", fontsize=8)

        plt.tight_layout()
        plt.show()


def plot_jump_height(
    analyses:            list[SkateAnalysis],
    frame_numbers:       list[int],
    fps:                 float,
    title:               str = "",
    board_length_cm:     float = BOARD_LENGTH_CM,
    height_threshold_cm: float = HEIGHT_THRESHOLD_CM,
    figsize:             tuple[float, float] = (14, 7),
) -> None:
    """Plot perspective-compensated jump height over time with trick intervals shaded.

    Height in cm = (baseline_board_Y - board_Y) / median_board_len_px * board_length_cm.
    """
    times = np.array([fn / fps for fn in frame_numbers])
    height_cm, com_height_cm, _, _ = _compute_jump_height(analyses, board_length_cm)

    tricks   = _find_trick_intervals(height_cm, times, frame_numbers, fps, height_threshold_cm)
    min_dist = max(1, int(fps * 0.3))
    peaks    = _find_jump_peaks(height_cm, min_height=height_threshold_cm, min_dist=min_dist)

    with plt.style.context("dark_background"):
        fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
        fig.suptitle(title, fontsize=10, y=1.01)

        ax = axes[0]
        for t in tricks:
            ax.axvspan(t.start_time, t.end_time, alpha=0.12, color="yellow")
        ax.plot(times, height_cm     / board_length_cm, color="#00C8FF", linewidth=1.5, label="board")
        ax.plot(times, com_height_cm / board_length_cm, color="#FFA040", linewidth=1.2, label="CoM", alpha=0.7)
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        for p in peaks:
            ax.axvline(times[p], color="white", linewidth=0.6, linestyle=":")
        ax.set_ylabel("board-length units")
        ax.set_title("Vertical position  (board-length units, perspective-compensated)")
        ax.legend(loc="upper right", fontsize=8)

        ax = axes[1]
        for t in tricks:
            ax.axvspan(t.start_time, t.end_time, alpha=0.12, color="yellow")
        ax.plot(times, height_cm, color="#00AAFF", linewidth=1.5, label="jump height")
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        for p in peaks:
            ax.axvline(times[p], color="white", linewidth=0.6, linestyle=":")
            ax.annotate(f"{height_cm[p]:.1f} cm",
                        xy=(times[p], height_cm[p]),
                        xytext=(4, 4), textcoords="offset points",
                        fontsize=8, color="white")
        ax.set_ylabel("cm")
        ax.set_xlabel("time (s)")
        ax.set_title("Jump height (cm)")
        ax.legend(loc="upper right", fontsize=8)

        plt.tight_layout()
        plt.show()

    for i, t in enumerate(tricks):
        log.info("Trick %d: %.2fs → %.2fs  (%.2fs)  peak %.1f cm",
                 i + 1, t.start_time, t.end_time, t.duration_s, t.peak_height_cm)
