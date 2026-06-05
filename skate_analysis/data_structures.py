from dataclasses import dataclass, field
import numpy as np


@dataclass
class PCAResult:
    centroid:     np.ndarray   # (2,)
    eigenvalues:  np.ndarray   # (2,)
    eigenvectors: np.ndarray   # (2, 2)


@dataclass
class SkateboardKeypoints:
    """Per-frame board pose. Order matches SKATE_KEYPOINT_NAMES."""
    xy:   np.ndarray              # (6, 2) float
    conf: np.ndarray | None       # (6,) float, or None when the model
                                  # produced no confidence tensor

    def visible(self, threshold: float) -> np.ndarray:
        """Indices where conf >= threshold or not (x,y) == (0,0)."""
        if self.conf is not None:
            return np.where(self.conf >= threshold)[0]
        return np.where((self.xy[:, 0] != 0) | (self.xy[:, 1] != 0))[0]

    def has_visible_nose_tail(self, threshold: float) -> bool:
        if self.conf is not None and (self.conf[0] < threshold or self.conf[1] < threshold):
            return False
        x0, y0 = self.xy[0] # nose
        x1, y1 = self.xy[1] # tail
        return not (x0 == 0 and y0 == 0) and not (x1 == 0 and y1 == 0)


@dataclass
class HumanKeypoints:
    """Per-frame COCO 17-keypoint pose for the primary skater."""
    xy:   np.ndarray   # (17, 2)
    conf: np.ndarray   # (17,)


@dataclass
class BoardData:
    kpts_pca:   PCAResult | None 
    seg_pca:    PCAResult | None 
    kpts_angle: float | None  
    seg_angle:  float | None  

    @property
    def angle_diff(self) -> float | None:
        if self.kpts_angle is None or self.seg_angle is None:
            return None
        return abs(self.kpts_angle - self.seg_angle)

    @property
    def centroid(self) -> np.ndarray | None:
        if self.kpts_pca is not None:
            return self.kpts_pca.centroid
        if self.seg_pca is not None:
            return self.seg_pca.centroid
        return None


@dataclass
class HumanData:
    com:              np.ndarray | None  
    com_offset:       np.ndarray | None  
    left_knee_angle:  float | None       
    right_knee_angle: float | None       
    left_knee_pos:    np.ndarray | None  
    right_knee_pos:   np.ndarray | None  
    wrist_dx:         float | None       
    shoulder_dx:      float | None       
    hip_dx:           float | None       
    ankle_dx:         float | None       

    @classmethod
    def empty(cls) -> "HumanData":
        return cls(None, None, None, None, None, None, None, None, None, None)


@dataclass
class SkateAnalysis:
    """Per-frame analysis result — pure numpy, no Ultralytics objects."""
    skate_kpts: SkateboardKeypoints | None   # board keypoints (6, 2) + conf (6,) or None
    human_kpts: HumanKeypoints | None        # human COCO pose (17, 2) + conf (17,) or None
    skate_mask: np.ndarray | None            # skateboard segmentation boolean mask
    board:      BoardData
    human:      HumanData
    norm_kpts:  np.ndarray | None = None     # (6, 2) board kpts after orientation normalisation


@dataclass
class VideoAnalysis:
    """Bundle of per-frame analyses with their frame numbers and source fps."""
    analyses:      list[SkateAnalysis] = field(default_factory=list)
    frame_numbers: list[int]           = field(default_factory=list)
    fps:           float               = 0.0

    def __iter__(self):
        # Support tuple unpacking: `analyses, frame_numbers, fps = video_analysis`.
        yield self.analyses
        yield self.frame_numbers
        yield self.fps

    @property
    def times(self) -> np.ndarray:
        return np.array([fn / self.fps for fn in self.frame_numbers], dtype=float)


@dataclass
class TrickInterval:
    start_frame:    int
    end_frame:      int
    start_time:     float
    end_time:       float
    duration_s:     float
    peak_height_cm: float
    peak_frame:     int
    peak_time:      float
