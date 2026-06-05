import logging

import numpy as np

from .config import (
    BODY_ROT_MIN_DUR_SECONDS,
    FLIP_AMP_RATIO,
    FLIP_MIN_DUR_SECONDS,
    MIN_FLIP_AMPLITUDE_PX,
    ROTATION_PRE_TRICK_SECONDS,
    YAW_EXTRA_SECONDS,
)
from .data_structures import SkateAnalysis, TrickInterval
from .geometry import _board_flip_direction_signal

log = logging.getLogger(__name__)


def _count_flip_zero_crossings(signal: np.ndarray, min_amp: float, min_dur: int) -> int:
    """Count flips as half the alternating zero-crossings of `signal`.

    A full 360 deg flip drives the mean wheel projection through the deck plane
    twice.
    Counting alternating polarity runs gives:
        - 1 run  -> board never returned (or stayed one side) -> 0 flips
        - 2 runs -> a single half-rotation (180 deg yaw)       -> 0 flips
        - 3 runs ('-+-' or '+-+')                              -> 1 flip
        - 5 runs                                                -> 2 flips
        - flip_count = (alternating_run_count - 1) // 2

    `min_amp` filters runs whose peak is below the noise floor; `min_dur` is the
    shortest polarity run that counts as a flip phase.
    """
    n = len(signal)
    if n < min_dur:
        return 0
    runs: list[str] = []
    i = 0
    while i < n:
        s = signal[i]
        if s > 0:
            j = i + 1
            while j < n and signal[j] > 0:
                j += 1
            peak = float(np.max(signal[i:j]))
            if (j - i) >= min_dur and peak >= min_amp and (not runs or runs[-1] != '+'):
                runs.append('+')
            i = j
        elif s < 0:
            j = i + 1
            while j < n and signal[j] < 0:
                j += 1
            peak = float(abs(np.min(signal[i:j])))
            if (j - i) >= min_dur and peak >= min_amp and (not runs or runs[-1] != '-'):
                runs.append('-')
            i = j
        else:
            i += 1
    if len(runs) < 3:
        return 0
    return (len(runs) - 1) // 2


# ── Helpers used by compute_trick_rotations ────────────────────────────
def _collect_flip_signals(
    analyses:  list[SkateAnalysis],
    frame_idx: list[int],
) -> tuple[np.ndarray, np.ndarray]:
    """Per-frame (mean_wheel_proj, left_minus_right_proj) over a window.

    Returns NaN where the board's flip-direction signal cannot be computed.
    """
    lp_raw, rp_raw, diff_raw = [], [], []
    for i in frame_idx:
        kp = analyses[i].norm_kpts
        lp, rp, d = _board_flip_direction_signal(kp) if kp is not None else (None, None, None)
        lp_raw.append(lp if lp is not None else np.nan)
        rp_raw.append(rp if rp is not None else np.nan)
        diff_raw.append(d if d is not None else np.nan)
    flip_arr = (np.array(lp_raw, dtype=float) + np.array(rp_raw, dtype=float)) / 2
    diff_arr = np.array(diff_raw, dtype=float)
    return flip_arr, diff_arr


def _trick_yaw(
    yaw_series: np.ndarray | None,
    yaw_idx:    list[int],
) -> tuple[np.ndarray, float | None]:
    """Per-trick yaw values rebased to 0 at the first valid frame.

    Returns (yaw_trick, yaw_deg). yaw_deg is the last valid value (the trick delta),
    or None if there are fewer than 2 valid frames or no yaw_series was provided.
    """
    n = len(yaw_idx)
    if yaw_series is None:
        return np.full(n, np.nan), None
    raw = np.array([yaw_series[i] for i in yaw_idx], dtype=float)
    valid = ~np.isnan(raw)
    if valid.sum() < 2:
        return np.full(n, np.nan), None
    base   = float(raw[valid][0])
    rebased = raw - base
    return rebased, float(rebased[~np.isnan(rebased)][-1])


def _pre_trick_diff_baseline(
    analyses: list[SkateAnalysis],
    pre_idx:  list[int],
    flip_arr: np.ndarray,
    diff_arr: np.ndarray,
) -> float:
    """Median pre-trick left-minus-right projection.

    Falls back to the first valid in-trick value if there is no pre-trick data.
    """
    pre_diff = []
    for i in pre_idx:
        kp = analyses[i].norm_kpts
        if kp is None:
            continue
        _, _, d = _board_flip_direction_signal(kp)
        if d is not None:
            pre_diff.append(d)
    if pre_diff:
        return float(np.median(pre_diff))
    valid_d = ~np.isnan(diff_arr)
    return float(diff_arr[valid_d][0]) if valid_d.any() else 0.0


def _flip_direction(diff_arr: np.ndarray, diff_baseline: float) -> str | None:
    """Determine flip direction from the centred diff signal.

    Whichever extremum (global min or global max) comes first wins.
    More robust than first-crossing: pitch spikes are small compared to flip
    peaks, so argmin/argmax are not confused by early noise.
    """
    centered = diff_arr - diff_baseline
    valid    = ~np.isnan(centered)
    if valid.sum() < 2:
        return None
    valid_cd = centered[valid]
    return '-' if int(np.argmin(valid_cd)) < int(np.argmax(valid_cd)) else '+'


def compute_trick_rotations(
    analyses:           list[SkateAnalysis],
    trick:              TrickInterval,
    frame_numbers:      list[int],
    fps:                float,
    yaw_series:         np.ndarray | None = None,
    min_flip_amplitude: float = MIN_FLIP_AMPLITUDE_PX,
) -> dict:
    """Compute yaw spin and flip count for a single TrickInterval.

    Requires norm_kpts to be populated via apply_norm_keypoints().

    Yaw is the trick-window delta of a precomputed video-wide yaw series
    (typically from `_board_yaw_atan2_video`). The series convention:
    unwrapped degrees, 0 at the first valid frame of the video. The per-trick
    delta is `last_valid - first_valid` within the trick window (extended by
    YAW_EXTRA_SECONDS to capture late-landing yaw). If `yaw_series` is None,
    `yaw_deg` is None.

    Returns dict with keys yaw_deg, flip_count, flip_dir.
    `flip_count` is SIGNED:
      +N = N flips rotating CW around tail-nose vector (left wheels rise first).
      -N = N flips rotating CCW around tail-nose (right wheels rise first).
    `flip_dir` ('+' / '-') is kept as a string for trick classification.

    Enable debug logging with logging.getLogger("skate_analysis.rotations").
    """
    trick_idx = [i for i, fn in enumerate(frame_numbers)
                 if trick.start_frame <= fn <= trick.end_frame]
    if not trick_idx:
        return {'yaw_deg': None, 'flip_count': None, 'flip_dir': None}

    yaw_extra  = int(fps * YAW_EXTRA_SECONDS)
    yaw_end_fn = trick.end_frame + yaw_extra
    yaw_idx    = [i for i, fn in enumerate(frame_numbers)
                  if trick.start_frame <= fn <= yaw_end_fn]

    pre_start = trick.start_frame - int(fps * ROTATION_PRE_TRICK_SECONDS)
    pre_idx   = [i for i, fn in enumerate(frame_numbers)
                 if pre_start <= fn < trick.start_frame]

    flip_arr, diff_arr = _collect_flip_signals(analyses, trick_idx)
    _, yaw_deg         = _trick_yaw(yaw_series, yaw_idx)

    flip_count: int | None = None
    flip_dir:   str | None = None

    valid_f = ~np.isnan(flip_arr)
    if valid_f.sum() < 4:
        log.debug("Trick @%d: too few valid flip frames (%d)", trick.start_frame, valid_f.sum())
    else:
        # During a 360 deg flip flip_arr ~ -h*cos(theta) traces -h -> 0 -> +h -> 0 -> -h.
        # It is symmetric around 0, NOT around the pre-trick baseline (which sits at -h).
        # So count polarity events on flip_arr itself, with 0 as the natural anchor.
        signal  = flip_arr[valid_f]
        sig_amp = float(max(abs(np.nanmin(signal)), abs(np.nanmax(signal))))
        min_amp = max(min_flip_amplitude, sig_amp * FLIP_AMP_RATIO)
        min_dur = max(3, int(fps * FLIP_MIN_DUR_SECONDS))
        flip_count = _count_flip_zero_crossings(signal, min_amp, min_dur)

        if flip_count > 0:
            diff_baseline = _pre_trick_diff_baseline(analyses, pre_idx, flip_arr, diff_arr)
            flip_dir = _flip_direction(diff_arr, diff_baseline)

        log.debug("Trick @%d: flip_count=%d flip_dir=%s (signal min=%+.1f max=%+.1f, min_amp=%.1f)",
                  trick.start_frame, flip_count, flip_dir,
                  float(signal.min()), float(signal.max()), min_amp)

    if flip_count is not None and flip_count > 0 and flip_dir is not None:
        flip_count = flip_count if flip_dir == '+' else -flip_count

    return {'yaw_deg': yaw_deg, 'flip_count': flip_count, 'flip_dir': flip_dir}


def _count_body_half_rotations(dx_arr, threshold_ratio: float = 0.3, min_dur: int = 3) -> int:
    """Count 180-degree body rotation increments from a right-minus-left dx signal.

    dx = right_x - left_x follows cos(body_yaw): positive at one stance, near zero at
    90 degrees, negative at 180 degrees. Each confirmed sign flip = one half-rotation.

    Scale and initial sign are derived from dx_arr itself (no pre-trick baseline).
    """
    valid = [v for v in dx_arr if v == v]
    if not valid:
        return 0
    scale     = max(abs(v) for v in valid)
    threshold = scale * threshold_ratio
    if threshold < 2.0:
        return 0

    sign_bl  = None
    init_idx = None
    run_val  = 0
    for i, v in enumerate(dx_arr):
        if v != v:
            run_val = 0
            continue
        if abs(v) > threshold:
            run_val += 1
            if run_val >= min_dur:
                sign_bl  = 1.0 if v >= 0 else -1.0
                init_idx = i - min_dur + 1
                break
        else:
            run_val = 0
    if sign_bl is None:
        return 0

    signed = [v * sign_bl if v == v else float("nan") for v in dx_arr[init_idx:]]
    half_rotations  = 0
    in_positive     = True
    run_in_new_zone = 0

    for val in signed:
        if val != val:
            run_in_new_zone = 0
            continue
        if in_positive:
            if val < -threshold:
                run_in_new_zone += 1
                if run_in_new_zone >= min_dur:
                    in_positive = False
                    half_rotations += 1
                    run_in_new_zone = 0
            else:
                run_in_new_zone = 0
        else:
            if val > threshold:
                run_in_new_zone += 1
                if run_in_new_zone >= min_dur:
                    in_positive = True
                    half_rotations += 1
                    run_in_new_zone = 0
            else:
                run_in_new_zone = 0

    return half_rotations


def compute_body_rotation(
    analyses:      list[SkateAnalysis],
    trick:         TrickInterval,
    frame_numbers: list[int],
    fps:           float,
    yaw_sign:      int = 1,
) -> dict:
    """Compute body-segment rotation count for a single TrickInterval.

    Uses right-minus-left horizontal distance (dx) as a cosine-like yaw proxy.
    Each confirmed sign flip during the trick window = one 180-degree increment.

    Returns dict with wrist/shoulder/hip/ankle _rot_deg keys; values are signed
    multiples of 180 (int), or None if fewer than 4 valid frames.
    Sign is taken from `yaw_sign` (+1 = CW on screen, -1 = CCW).
    """
    yaw_extra  = int(fps * YAW_EXTRA_SECONDS)
    yaw_end_fn = trick.end_frame + yaw_extra
    trick_idx  = [i for i, fn in enumerate(frame_numbers)
                  if trick.start_frame <= fn <= yaw_end_fn]

    min_dur = max(3, int(fps * BODY_ROT_MIN_DUR_SECONDS))
    result: dict = {}

    for attr, key in [
        ('wrist_dx',    'wrist_rot_deg'),
        ('shoulder_dx', 'shoulder_rot_deg'),
        ('hip_dx',      'hip_rot_deg'),
        ('ankle_dx',    'ankle_rot_deg'),
    ]:
        dx_arr = [getattr(analyses[i].human, attr) for i in trick_idx]
        dx_arr = [float(v) if v is not None else float('nan') for v in dx_arr]

        valid_count = sum(1 for v in dx_arr if v == v)
        if valid_count < 4:
            result[key] = None
            continue

        half_rots   = _count_body_half_rotations(dx_arr, min_dur=min_dur)
        result[key] = int(half_rots * 180 * yaw_sign)

    return result
