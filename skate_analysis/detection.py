import logging

import numpy as np

from .config import (
    ANKLE_CONF,
    BOARD_LENGTH_CM,
    DIR_DX_PX_THRESHOLD,
    DIR_LEN_CHANGE_RATIO,
    GAP_FILL_SECONDS,
    HEIGHT_THRESHOLD_CM,
    KPT_CONF,
    PRE_TRICK_WINDOW_SECONDS,
    STANCE_DIV_THRESHOLD,
)
from .constants import SKATE_KP_SWAP
from .data_structures import SkateAnalysis, SkateboardKeypoints, TrickInterval
from .geometry import is_valid_kp

log = logging.getLogger(__name__)


def _board_length_px(skate_kpts: SkateboardKeypoints | None) -> float:
    """Projected nose-to-tail length in pixels, or NaN if not detectable."""
    if skate_kpts is None or not skate_kpts.has_visible_nose_tail(KPT_CONF):
        return float('nan')
    nose, tail = skate_kpts.xy[0], skate_kpts.xy[1]
    return float(np.linalg.norm(nose - tail))


def _compute_jump_height(
    analyses:        list[SkateAnalysis],
    board_length_cm: float = BOARD_LENGTH_CM,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Perspective-compensated vertical heights (board + CoM) in cm.

    Returns (height_cm, com_height_cm, median_len_px, baseline_y).
    """
    n = len(analyses)
    board_y   = np.full(n, np.nan)
    com_y     = np.full(n, np.nan)
    board_len = np.full(n, np.nan)

    for i, a in enumerate(analyses):
        c = a.board.centroid
        if c is not None:
            board_y[i] = c[1]
        if a.human.com is not None:
            com_y[i] = a.human.com[1]
        board_len[i] = _board_length_px(a.skate_kpts)

    median_len  = float(np.nanmedian(board_len))
    baseline_y  = float(np.nanmedian(board_y))
    baseline_cy = float(np.nanmedian(com_y))

    if not np.isnan(median_len) and median_len > 0:
        height_cm     = (baseline_y  - board_y) / median_len * board_length_cm
        com_height_cm = (baseline_cy - com_y)   / median_len * board_length_cm
    else:
        height_cm     = baseline_y  - board_y
        com_height_cm = baseline_cy - com_y

    return height_cm, com_height_cm, median_len, baseline_y


def _append_trick(tricks, height_cm, times, frame_numbers, start_idx, end_idx):
    seg = height_cm[start_idx:end_idx + 1]
    peak_offset = int(np.argmax(seg))
    peak_idx = start_idx + peak_offset
    tricks.append(TrickInterval(
        start_frame=frame_numbers[start_idx],
        end_frame=frame_numbers[end_idx],
        start_time=float(times[start_idx]),
        end_time=float(times[end_idx]),
        duration_s=float(times[end_idx] - times[start_idx]),
        peak_height_cm=float(height_cm[peak_idx]),
        peak_frame=frame_numbers[peak_idx],
        peak_time=float(times[peak_idx]),
    ))


def _find_trick_intervals(
    height_cm:     np.ndarray,
    times:         np.ndarray,
    frame_numbers: list[int],
    fps:           float,
    threshold:     float,
) -> list[TrickInterval]:
    """Return TrickInterval list for contiguous segments where height_cm > threshold.

    Small gaps (< fps * GAP_FILL_SECONDS frames) are bridged to handle brief
    detection dropouts while the board is airborne.
    """
    h = np.where(np.isnan(height_cm), 0.0, height_cm) # convert NaN to 0
    above = h > threshold

    fill = max(1, int(fps * GAP_FILL_SECONDS))
    for i in range(1, len(above) - 1):
        if not above[i]: # below threshold
            lo, hi = max(0, i - fill), min(len(above), i + fill + 1)
            if above[lo:i].any() and above[i + 1:hi].any():
                above[i] = True # fill the gap, if T in left or right window

    tricks = []
    in_trick = False
    start_idx = None
    for i, a in enumerate(above):
        if not in_trick and a: # start of trick
            in_trick = True
            start_idx = i
        elif in_trick and not a: # end of trick
            in_trick = False
            _append_trick(tricks, height_cm, times, frame_numbers, start_idx, i - 1)
    if in_trick: # handle trick that ends at the last frame
        _append_trick(tricks, height_cm, times, frame_numbers, start_idx, len(above) - 1)
    return tricks


def _find_jump_peaks(arr: np.ndarray, min_height: float, min_dist: int) -> list[int]:
    """Local maxima above `min_height`, spaced by at least `min_dist` frames."""
    try:
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(np.where(np.isnan(arr), -np.inf, arr),
                              height=min_height, distance=max(1, min_dist))
        return peaks.tolist()
    except ImportError:
        # Fallback if scipy is unavailable.
        n = len(arr)
        candidates = []
        for i in range(n):
            if np.isnan(arr[i]) or arr[i] < min_height:
                continue
            lo, hi = max(0, i - min_dist), min(n, i + min_dist + 1)
            if arr[i] == np.nanmax(arr[lo:hi]):
                candidates.append(i)
        peaks, last = [], -min_dist - 1
        for c in candidates:
            if c - last >= min_dist:
                peaks.append(c)
                last = c
        return peaks


def detect_tricks(
    analyses:            list[SkateAnalysis],
    frame_numbers:       list[int],
    fps:                 float,
    board_length_cm:     float = BOARD_LENGTH_CM,
    height_threshold_cm: float = HEIGHT_THRESHOLD_CM,
) -> list[TrickInterval]:
    """Detect trick intervals from video analysis.

    Computes board height per frame and returns contiguous airborne segments.

    Warning:
        Unreliable for toward/away shots (see plot_jump_height).
    """
    times = np.array([fn / fps for fn in frame_numbers])
    height_cm, _, _, _ = _compute_jump_height(analyses, board_length_cm)
    return _find_trick_intervals(height_cm, times, frame_numbers, fps, height_threshold_cm)


def detect_direction(
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    fps:           float,
) -> str:
    """Detect the primary direction of travel from board position over time.

    Returns:
        "ltr"     — left to right (board X increasing)
        "rtl"     — right to left (board X decreasing)
        "toward"  — toward the camera (board apparent size increasing)
        "away"    — away from the camera (board apparent size decreasing)
        "unknown" — insufficient data

    Note:
        Horizontal displacement is checked first. The toward/away classification
        is only attempted when horizontal movement is small, which avoids
        misclassifying tricks like FS/BS 180 as toward/away.
    """
    board_x = np.array(
        [a.board.centroid[0] if a.board.centroid is not None else np.nan for a in analyses],
        dtype=float,
    )
    board_len = np.array(
        [_board_length_px(a.skate_kpts) for a in analyses],
        dtype=float,
    )

    valid_x   = board_x[~np.isnan(board_x)]
    valid_len = board_len[~np.isnan(board_len)]

    if len(valid_x) < 2:
        return "unknown"

    dx = valid_x[-1] - valid_x[0]
    if abs(dx) > DIR_DX_PX_THRESHOLD:
        return "ltr" if dx > 0 else "rtl"

    if len(valid_len) >= 2:
        median_len = float(np.median(valid_len))
        dl_range   = (float(np.max(valid_len)) - float(np.min(valid_len))) / (median_len + 1e-8)
        if dl_range > DIR_LEN_CHANGE_RATIO:
            dl = valid_len[-1] - valid_len[0]
            return "toward" if dl > 0 else "away"

    return "unknown"


def normalize_board_keypoints(
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    fps:           float,
) -> list[np.ndarray | None]:
    """Return per-frame board keypoints with nose = front in direction of travel.

    Uses direction-based initialization for the first valid frame, then temporal
    tracking (minimum squared distance for nose + tail) to stay consistent across
    frames — including during flips and rotations.

    When a swap is applied, ALL 6 keypoints are remapped via SKATE_KP_SWAP so that
    front/back and left/right wheel labels remain geometrically correct.
    """
    direction = detect_direction(analyses, frame_numbers, fps)
    result:  list[np.ndarray | None] = []
    prev_kp: np.ndarray | None       = None

    for a in analyses:
        if a.skate_kpts is None or not a.skate_kpts.has_visible_nose_tail(KPT_CONF):
            result.append(None)
            continue
        kp = a.skate_kpts.xy.copy()
        kp_swap = kp[SKATE_KP_SWAP]

        if prev_kp is None: # initialization
            if direction == "ltr" and kp[0, 0] < kp[1, 0]:
                kp = kp_swap   # model nose is to the left → swap
            elif direction == "rtl" and kp[0, 0] > kp[1, 0]:
                kp = kp_swap   # model nose is to the right → swap
        else: # tracking
            cost_keep = np.sum((prev_kp[0] - kp[0]) ** 2) + np.sum((prev_kp[1] - kp[1]) ** 2)
            cost_swap = np.sum((prev_kp[0] - kp[1]) ** 2) + np.sum((prev_kp[1] - kp[0]) ** 2)
            if cost_swap < cost_keep:
                kp = kp_swap

        prev_kp = kp
        result.append(kp)

    return result


def apply_norm_keypoints(
    analyses:       list[SkateAnalysis],
    norm_kpts_list: list[np.ndarray | None],
) -> None:
    """Populate SkateAnalysis.norm_kpts from normalize_board_keypoints() output."""
    for a, kp in zip(analyses, norm_kpts_list):
        a.norm_kpts = kp


# ── Stance detection ───────────────────────────────────────────────────


def _trick_frames(tricks: list[TrickInterval] | None, frame_numbers: list[int]) -> set[int]:
    """Frame numbers that fall inside any trick interval."""
    out: set[int] = set()
    if not tricks:
        return out
    for t in tricks:
        for fn in frame_numbers:
            if t.start_frame <= fn <= t.end_frame:
                out.add(fn)
    return out


def _stance_signal_a(
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    trick_frames:  set[int],
) -> bool | None:
    """Foot-position signal: left ankle closer to norm_nose on ground frames?

    Returns True/False (majority vote) or None when no usable frames are found.
    """
    left_forward_votes: list[bool] = []
    for fn, a in zip(frame_numbers, analyses):
        if fn in trick_frames or a.norm_kpts is None or a.human_kpts is None:
            continue
        conf = a.human_kpts.conf
        xy   = a.human_kpts.xy
        if conf[15] < ANKLE_CONF or conf[16] < ANKLE_CONF:
            continue
        norm_nose = a.norm_kpts[0]
        d_left  = float(np.linalg.norm(xy[15] - norm_nose)) # left ankle
        d_right = float(np.linalg.norm(xy[16] - norm_nose)) # right ankle
        left_forward_votes.append(d_left < d_right)

    if not left_forward_votes:
        log.debug("Signal A: no valid ground frames with both ankles visible")
        return None

    mean_a   = float(np.mean(left_forward_votes))
    signal_a = mean_a > 0.5
    log.debug(
        "Signal A: %d ground frames, left_forward_ratio=%.2f → signal_a=%s (%s foot closer to norm_nose)",
        len(left_forward_votes), mean_a, signal_a, "left" if signal_a else "right",
    )
    return signal_a


def _pop_vote_for_trick(
    trick:         TrickInterval,
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    trick_frames:  set[int],
    fps:           float,
) -> bool | None:
    """One pop vote: True = tail-first, False = nose-first, None = inconclusive."""
    win_start = trick.start_frame - int(fps * PRE_TRICK_WINDOW_SECONDS) # pre-trick window
    win_end   = trick.start_frame
    win_idx   = [i for i, fn in enumerate(frame_numbers)
                 if win_start <= fn <= win_end and fn not in trick_frames]

    if len(win_idx) < 2:
        log.debug("Pop window for trick @%d too small (%d frames)", trick.start_frame, len(win_idx))
        return None

    div_total = 0.0
    for step in range(1, len(win_idx)):
        prev_kp = analyses[win_idx[step - 1]].norm_kpts
        curr_kp = analyses[win_idx[step    ]].norm_kpts
        if prev_kp is None or curr_kp is None:
            continue
        dy_nose = curr_kp[0, 1] - prev_kp[0, 1] # positive = nose moves down
        dy_tail = curr_kp[1, 1] - prev_kp[1, 1] # positive = tail moves down
        div_total += dy_tail - dy_nose

    if div_total > STANCE_DIV_THRESHOLD:
        log.debug("Trick @%d cumulative_div=%+.1f → tail_first", trick.start_frame, div_total)
        return True
    if div_total < -STANCE_DIV_THRESHOLD:
        log.debug("Trick @%d cumulative_div=%+.1f → nose_first", trick.start_frame, div_total)
        return False
    log.debug("Trick @%d cumulative_div=%+.1f → inconclusive", trick.start_frame, div_total)
    return None


def _stance_signal_b(
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    fps:           float,
    tricks:        list[TrickInterval],
    trick_frames:  set[int],
) -> bool | None:
    """Pop-direction signal across all tricks. True = tail-first majority."""
    votes = [v for v in (_pop_vote_for_trick(t, analyses, frame_numbers, trick_frames, fps)
                         for t in tricks) if v is not None]
    if not votes:
        log.debug("Signal B: no valid pop votes")
        return None
    mean_b   = float(np.mean(votes))
    signal_b = mean_b >= 0.5
    log.debug("Signal B: %d tricks, tail_first_ratio=%.2f → signal_b=%s",
              len(votes), mean_b, signal_b)
    return signal_b


def _combine_stance(
    signal_a:   bool | None,
    signal_b:   bool | None,
    is_regular: bool,
    direction:  str,
) -> str:
    """Combine the two signals into a stance label."""
    if signal_a is None:
        natural_fwd: bool | None = None
    elif direction == "ltr" and is_regular:
        # ltr: skater faces away; COCO inverts anatomical left/right for regular.
        natural_fwd = not signal_a
    else:
        natural_fwd = signal_a if is_regular else not signal_a

    log.debug("Combine: is_regular=%s signal_a=%s signal_b=%s natural_fwd=%s",
             is_regular, signal_a, signal_b, natural_fwd)

    if natural_fwd is not None and signal_b is not None:
        if signal_b and natural_fwd:       return "normal"
        if signal_b and not natural_fwd:   return "switch"
        if not signal_b and natural_fwd:   return "nollie"
        return "fakie"
    if signal_b is None and natural_fwd is not None:
        return "normal" if natural_fwd else "switch"
    return "unknown"


def detect_stance(
    analyses:      list[SkateAnalysis],
    frame_numbers: list[int],
    fps:           float,
    is_regular:    bool = True,
    tricks:        list[TrickInterval] | None = None,
    direction:     str  = "unknown",
) -> str:
    """Detect skater stance using two independent signals.

    Signal A — foot position: which ankle is closer to norm_nose on ground frames.
    Signal B — pop direction: cumulative divergence (Σ dy_tail − dy_nose) over the
               pre-trick window. Positive → tail-first; negative → nose-first;
               near-zero → inconclusive, no vote cast.

    Truth table:
        natural foot near norm_nose + tail pops first → "normal"
        natural foot near norm_nose + nose pops first → "nollie"
        other foot near norm_nose   + tail pops first → "switch"
        other foot near norm_nose   + nose pops first → "fakie"

    Requires norm_kpts to be populated via apply_norm_keypoints().
    Enable debug output with `logging.getLogger("skate_analysis.detection").setLevel(logging.DEBUG)`.
    """
    if all(a.norm_kpts is None for a in analyses):
        log.debug("No norm_kpts → unknown")
        return "unknown"

    frames = _trick_frames(tricks, frame_numbers)
    signal_a = _stance_signal_a(analyses, frame_numbers, frames)
    signal_b = _stance_signal_b(analyses, frame_numbers, fps, tricks, frames) if tricks else None
    return _combine_stance(signal_a, signal_b, is_regular, direction)
