"""Annotated-video export. Writes mp4v then re-encodes to H.264 via ffmpeg."""

import logging
import os
import shutil
import subprocess
import tempfile

import cv2
from tqdm.auto import tqdm

from ..data_structures import SkateAnalysis
from .overlay import render_frame

log = logging.getLogger(__name__)


def save_annotated_video(
    video_path:              str,
    analyses:                list[SkateAnalysis],
    frame_numbers:           list[int],
    output_path:             str,
    show_human_pose:         bool = True,
    show_skate_segmentation: bool = True,
    show_skate_keypoints:    bool = True,
    show_kpts_pca:           bool = True,
    show_seg_pca:            bool = True,
    show_angle_diff:         bool = True,
    show_human_metrics:      bool = True,
) -> None:
    """Save an annotated video using pre-computed analyses.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install it (e.g. `winget install ffmpeg` "
            "on Windows, `brew install ffmpeg` on macOS) and try again."
        )

    cap   = cv2.VideoCapture(video_path)
    fps   = cap.get(cv2.CAP_PROP_FPS)
    w     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(tmp_fd)

    out = cv2.VideoWriter(tmp_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    frame_map   = dict(zip(frame_numbers, analyses))
    frame_idx   = 0
    last_result = None

    with tqdm(total=total, desc="saving", colour="#3a3a3a") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in frame_map:
                last_result = frame_map[frame_idx]
            if last_result is not None:
                vis = render_frame(
                    frame, last_result,
                    show_human_pose, show_skate_segmentation, show_skate_keypoints,
                    show_kpts_pca, show_seg_pca, show_angle_diff, show_human_metrics,
                )
                out.write(cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
            else:
                out.write(frame)
            frame_idx += 1
            pbar.update(1)

    cap.release()
    out.release()

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", tmp_path,
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            output_path,
        ],
        check=True,
        capture_output=True,
    )
    os.remove(tmp_path)
    log.info("Saved: %s", output_path)
