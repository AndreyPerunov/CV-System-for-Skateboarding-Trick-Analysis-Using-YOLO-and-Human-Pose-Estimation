"""Centralised thresholds and heuristic coefficients.

Every magic number used by the pipeline lives here so that experiments,
ablations, and parameter sweeps can change one file instead of editing
seven modules. Group by stage; keep units in the comment.
"""

# ── Inference ──────────────────────────────────────────────────────────
INFERENCE_CONF = 0.5    # YOLO predict() conf threshold (per-frame inference)
INFERENCE_IOU  = 0.9    # YOLO predict() iou threshold (NMS)

# ── Keypoint validity ──────────────────────────────────────────────────
KPT_CONF        = 0.3    # default conf threshold for "visible" keypoint
ANKLE_CONF      = 0.15   # looser threshold for ankles (often partially occluded)

# ── Board / board-length ───────────────────────────────────────────────
BOARD_LENGTH_CM      = 81.0   # real-world nose-to-tail length
BOARD_ASPECT         = 4.0    # length / width for the 3D-yaw recovery model
HEIGHT_THRESHOLD_CM  = 3.0    # min board height to count as airborne

# ── Direction detection ────────────────────────────────────────────────
DIR_DX_PX_THRESHOLD       = 20.0   # |dx| larger than this → ltr/rtl
DIR_LEN_CHANGE_RATIO      = 0.5    # relative board-length range → toward/away

# ── Trick-interval gap fill ────────────────────────────────────────────
GAP_FILL_SECONDS  = 0.15   # bridge dropouts up to this many seconds inside a trick

# ── Stance detection (Signal B) ────────────────────────────────────────
PRE_TRICK_WINDOW_SECONDS  = 0.3   # window for pop direction signal
STANCE_DIV_THRESHOLD      = 2.0   # |cumulative dy_tail - dy_nose| to accept a vote

# ── Rotation analysis ──────────────────────────────────────────────────
YAW_EXTRA_SECONDS         = 0.12   # extend trick window for late-landing yaw
ROTATION_PRE_TRICK_SECONDS = 0.5   # baseline window for flip-signal mean
MIN_FLIP_AMPLITUDE_PX     = 10.0   # noise floor for flip-signal polarity peaks
FLIP_AMP_RATIO            = 0.20   # min_amp scales as max(MIN_FLIP_AMPLITUDE, ratio * sig_amp)
FLIP_MIN_DUR_SECONDS      = 0.025  # shortest polarity run that counts as a flip phase
BODY_ROT_MIN_DUR_SECONDS  = 0.04   # shortest sustained zone for body half-rotation

# ── Classification ─────────────────────────────────────────────────────
SPIN_SNAP_TOLERANCE_DEG  = 45.0   # how close to a {0,180,360,540,720} anchor to snap
FS_BS_MIN_DEG            = 90.0   # below this magnitude, FS/BS is indeterminate
