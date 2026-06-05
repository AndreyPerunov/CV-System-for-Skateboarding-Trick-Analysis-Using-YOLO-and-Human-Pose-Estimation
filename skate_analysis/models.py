from functools import lru_cache
from pathlib import Path

from ultralytics import YOLO


_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

YOLO_POSE_PATH  = _MODELS_DIR / "yolo11m-pose.pt"
YOLO_SEG_PATH   = _MODELS_DIR / "yolo11m-seg.pt"
SKATE_POSE_PATH = _MODELS_DIR / "skate-pose-2.0.pt"


@lru_cache(maxsize=None)
def _load(path: str) -> YOLO:
    return YOLO(path)


def get_yolo_pose_model() -> YOLO:
    return _load(str(YOLO_POSE_PATH))


def get_yolo_seg_model() -> YOLO:
    return _load(str(YOLO_SEG_PATH))


def get_skateboard_pose_model() -> YOLO:
    return _load(str(SKATE_POSE_PATH))


def load_models() -> None:
    """Pre-load all three models. Call once on application startup to warm
    the @lru_cache so the first request doesn't pay the cold-load latency.
    """
    get_yolo_pose_model()
    get_yolo_seg_model()
    get_skateboard_pose_model()
