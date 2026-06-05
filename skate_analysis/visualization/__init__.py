"""Drawing/plotting/encoding for skate analysis results.

Split into three modules by concern:
    overlay — per-frame cv2 overlays + render_frame
    video   — full-video re-encode (ffmpeg)
    plots   — matplotlib figures (plot_metrics, plot_jump_height)
"""

from .overlay import render_frame
from .plots import plot_jump_height, plot_metrics
from .video import save_annotated_video

__all__ = [
    "plot_jump_height",
    "plot_metrics",
    "render_frame",
    "save_annotated_video",
]
