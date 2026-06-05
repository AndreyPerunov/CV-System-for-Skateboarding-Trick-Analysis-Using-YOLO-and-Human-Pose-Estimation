"""Skateboard trick analysis pipeline.

Public API:
    analyze, analyze_with_video                       — high-level video → dict
    analyze_frame, analyze_video                      — low-level
    detect_tricks, detect_direction, normalize_board_keypoints,
        apply_norm_keypoints, detect_stance
    compute_trick_rotations, compute_body_rotation
    flip_label, classify_trick
    render_frame, save_annotated_video, plot_metrics, plot_jump_height
    load_models                                       — FastAPI lifespan warm-up

Pydantic response schemas (FastAPI contract):
    AnalysisResponse, Timeline, TrickReport, PcaPoint

Dataclasses (internal numpy domain):
    PCAResult, BoardData, HumanData, SkateAnalysis, TrickInterval,
    VideoAnalysis, SkateboardKeypoints, HumanKeypoints

Internal helpers used by the demo notebook are also re-exported here:
    _board_yaw_atan2_video
"""

from .analyze import analyze, analyze_frame, analyze_video, analyze_with_video
from .classification import classify_trick, flip_label
from .detection import (
    apply_norm_keypoints,
    detect_direction,
    detect_stance,
    detect_tricks,
    normalize_board_keypoints,
)
from .geometry import _board_yaw_atan2_video
from .models import load_models
from .rotations import compute_body_rotation, compute_trick_rotations
from .schemas import AnalysisResponse, PcaPoint, Timeline, TrickReport
from .data_structures import (
    BoardData,
    HumanData,
    HumanKeypoints,
    PCAResult,
    SkateAnalysis,
    SkateboardKeypoints,
    TrickInterval,
    VideoAnalysis,
)
from .visualization import (
    plot_jump_height,
    plot_metrics,
    render_frame,
    save_annotated_video,
)

__all__ = [
    "analyze",
    "analyze_frame",
    "analyze_video",
    "analyze_with_video",
    "AnalysisResponse",
    "apply_norm_keypoints",
    "BoardData",
    "classify_trick",
    "compute_body_rotation",
    "compute_trick_rotations",
    "detect_direction",
    "detect_stance",
    "detect_tricks",
    "flip_label",
    "HumanData",
    "HumanKeypoints",
    "load_models",
    "normalize_board_keypoints",
    "PCAResult",
    "PcaPoint",
    "plot_jump_height",
    "plot_metrics",
    "render_frame",
    "save_annotated_video",
    "SkateAnalysis",
    "SkateboardKeypoints",
    "Timeline",
    "TrickInterval",
    "TrickReport",
    "VideoAnalysis",
    "_board_yaw_atan2_video",
]
