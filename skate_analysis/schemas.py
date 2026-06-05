"""Pydantic v2 response schemas for the FastAPI backend."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Direction = Literal["ltr", "rtl", "toward", "away", "unknown"]
Stance    = Literal["normal", "switch", "fakie", "nollie", "unknown"]
FlipDir   = Literal["+", "-"]


class PcaPoint(BaseModel):
    """PCA result for a 2D point cloud.

    eigenvalues are sorted in descending order; eigenvectors[0] is PC1, [1] is PC2.
    """
    centroid:     list[float] = Field(..., description="[x, y] in original-frame pixels")
    eigenvalues:  list[float] = Field(..., description="[lambda1, lambda2] descending")
    eigenvectors: list[list[float]] = Field(
        ..., description="[[PC1x, PC1y], [PC2x, PC2y]]"
    )


class Timeline(BaseModel):
    """Per-frame time-series data aligned by index.

    All arrays have the same length (= frame_count).
    """
    times_s:              list[float]
    frame_numbers:        list[int]

    # Board geometry
    board_kpts_angle_deg: list[float | None]
    board_seg_angle_deg:  list[float | None]
    angle_diff_deg:       list[float | None]
    board_yaw_deg:        list[float | None] = Field(
        ..., description="Unwrapped yaw angle in degrees, 0 at first valid frame, + = CW on screen"
    )

    # Vertical
    height_cm:            list[float | None] = Field(
        ..., description="Board height above baseline, perspective-compensated cm"
    )
    com_height_cm:        list[float | None]

    # Human pose
    left_knee_angle_deg:  list[float | None]
    right_knee_angle_deg: list[float | None]
    com_offset_px:        list[float | None]

    wrist_dx:             list[float | None]
    shoulder_dx:          list[float | None]
    hip_dx:               list[float | None]
    ankle_dx:             list[float | None]

    # Board flip signals
    flip_signal_mean:     list[float | None] = Field(..., description="Mean of all 4 wheels")
    flip_signal_left:     list[float | None] = Field(default_factory=list, description="Mean of front_left + back_left wheels")
    flip_signal_right:    list[float | None] = Field(default_factory=list, description="Mean of front_right + back_right wheels")
    flip_signal_diff:     list[float | None] = Field(..., description="left - right")

    # Per-frame keypoints for frontend overlay on the original video.
    skate_keypoints:      list[list[list[float]] | None]
    human_keypoints:      list[list[list[float]] | None]

    # Per-frame board geometry
    board_kpts_pca:       list[PcaPoint | None] = Field(default_factory=list)
    board_seg_pca:        list[PcaPoint | None] = Field(default_factory=list)
    board_seg_contour:    list[list[list[float]] | None] = Field(default_factory=list)


class TrickReport(BaseModel):
    """Aggregate metrics for a single detected trick interval."""
    start_frame:      int
    end_frame:        int
    start_time_s:     float
    end_time_s:       float
    duration_s:       float
    peak_frame:       int
    peak_time_s:      float
    peak_height_cm:   float

    board_yaw_deg:    float | None = Field(
        None, description="Total board yaw delta over the trick window, signed degrees (+ = CW on screen)"
    )
    flip_count:       int | None = Field(
        None, description="Signed flip count: + = CW around tail->nose, - = CCW"
    )
    flip_dir:         FlipDir | None = None

    wrist_rot_deg:    int | None = Field(None, description="Body rotation, signed multiple of 180")
    shoulder_rot_deg: int | None = None
    hip_rot_deg:      int | None = None
    ankle_rot_deg:    int | None = None

    trick_name:       str


class AnalysisResponse(BaseModel):
    """Top-level response for POST /analyze_video."""
    video_path:           str
    annotated_video_path: str | None = None
    fps:                  float
    frame_count:          int
    is_regular:           bool
    direction:            Direction
    stance:               Stance
    timeline:             Timeline
    tricks:               list[TrickReport]
