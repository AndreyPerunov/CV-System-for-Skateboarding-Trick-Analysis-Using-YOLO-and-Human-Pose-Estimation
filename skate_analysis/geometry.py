import numpy as np

from .config import BOARD_ASPECT
from .data_structures import PCAResult


def is_valid_kp(p) -> bool:
    """A (0, 0) keypoint is YOLO's sentinel for 'not predicted'."""
    return not (p[0] == 0 and p[1] == 0)


def _pca(points) -> PCAResult | None:
    centroid = points.mean(axis=0)
    cov = np.cov((points - centroid).T)
    if cov.ndim < 2:
        return None
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    order = np.argsort(eigenvalues)[::-1]
    return PCAResult(centroid, eigenvalues[order], eigenvectors[:, order])


def _pca_angle(pca: PCAResult | None) -> float | None:
    """Angle of PC1 relative to horizontal in degrees, normalized to [-90, 90].

    The board is symmetric (nose/tail are interchangeable for angle purposes),
    so we fold the full [-180, 180] range into [-90, 90].
    """
    if pca is None:
        return None
    vx, vy = pca.eigenvectors[:, 0]
    angle = np.degrees(np.arctan2(vy, vx))
    if angle < -90:
        angle += 180
    if angle > 90:
        angle -= 180
    return float(angle)


def _joint_angle(a, b, c) -> float:
    """Angle at joint b formed by points a-b-c. Returns degrees in [0, 180]."""
    v1, v2 = a - b, c - b
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))


def _board_yaw_atan2_components(norm_kp):
    """Image-plane vectors for the board's long and lateral axes.

    Returns (fb_vec, rl_vec):
      fb_vec = front_proxy - back_proxy   (front/back = mean of front-pair / back-pair wheels,
                                            falling back to nose/tail if a wheel pair is missing)
      rl_vec = right_proxy - left_proxy   (only from wheels — nose/tail has no left/right)
    Either entry is None if not enough valid keypoints are present.
    """
    valid = is_valid_kp
    nose, tail = norm_kp[0], norm_kp[1]
    fl, fr, bl, br = norm_kp[2], norm_kp[3], norm_kp[4], norm_kp[5]

    fronts = [p for p in [fl, fr] if valid(p)]
    backs  = [p for p in [bl, br] if valid(p)]
    if fronts and backs:
        front = np.mean(fronts, axis=0)
        back  = np.mean(backs,  axis=0)
    elif valid(nose) and valid(tail):
        front, back = nose, tail
    else:
        return None, None
    fb = front - back

    rights = [p for p in [fr, br] if valid(p)]
    lefts  = [p for p in [fl, bl] if valid(p)]
    if not rights or not lefts:
        return fb, None
    right = np.mean(rights, axis=0)
    left  = np.mean(lefts,  axis=0)
    rl = right - left

    return fb, rl


def _board_yaw_atan2_video(analyses, board_aspect: float = BOARD_ASPECT):
    """Per-frame board yaw (degrees, unwrapped) from foreshortening + lateral sign.

    Recovers the 3D yaw angle from two image-plane projections onto the natural
    long-axis direction `e_long`:
        u(t) = (front - back) . e_long    ~ L * cos(alpha)   (signed)
        v(t) = (right - left) . e_long    ~ w * sin(alpha)   (signed)
    where e_long is the unit vector of (front - back) at the frame of maximum
    |front - back| in the video (board most "parallel to camera plane").

        alpha(t) = atan2(v(t) / w_max, u(t) / L_max)

    Then np.unwrap across the video and shift so the first valid frame reads 0.

    Sign convention: positive = CW yaw on screen (clock direction). A board
    rolling left-to-right that rotates clockwise (viewed by the camera) gives
    a positive cumulative yaw; CCW rotation gives negative.

    Returns
    -------
    yaw : np.ndarray, shape (N,)
        Cumulative yaw (degrees), NaN where keypoints are insufficient.
    L_max : float
        Calibration length in normalized-pixel units (max |front - back|).
    w_max : float
        Calibration width = L_max / board_aspect.
    """
    N = len(analyses)
    fb = [None] * N
    rl = [None] * N
    for i, a in enumerate(analyses):
        kp = a.norm_kpts
        if kp is None:
            continue
        fb_i, rl_i = _board_yaw_atan2_components(kp)
        fb[i] = fb_i
        rl[i] = rl_i

    valid_idx = [i for i in range(N) if fb[i] is not None and rl[i] is not None]
    if len(valid_idx) < 2:
        return np.full(N, np.nan), 0.0, 0.0

    i_ref  = max(valid_idx, key=lambda i: float(np.linalg.norm(fb[i]))) # frame with largest front-back vector (longest nose-tail)
    L_max  = float(np.linalg.norm(fb[i_ref])) # longest front-back vector in pixels
    if L_max < 1e-6:
        return np.full(N, np.nan), 0.0, 0.0
    e_long = fb[i_ref] / L_max
    w_max  = L_max / board_aspect

    yaw_raw = np.full(N, np.nan)
    for i in valid_idx:
        u = float(np.dot(fb[i], e_long))    # cos(alpha) * L
        v = float(np.dot(rl[i], e_long))    # sin(alpha) * w
        # Negate v so that CW yaw on screen (clock-direction) is POSITIVE.
        yaw_raw[i] = float(np.degrees(np.arctan2(-v / w_max, u / L_max)))

    yaw_out = np.full(N, np.nan)
    mask    = ~np.isnan(yaw_raw)
    if mask.sum() >= 2:
        unwrapped       = np.degrees(np.unwrap(np.radians(yaw_raw[mask])))
        unwrapped      -= unwrapped[0]
        yaw_out[mask]   = unwrapped

    return yaw_out, L_max, w_max


def _board_flip_signal(norm_kp):
    nose, tail = norm_kp[0], norm_kp[1]
    axis = tail - nose
    axis_len = float(np.linalg.norm(axis))
    if axis_len < 1.0:
        return None
    perp = np.array([-axis[1], axis[0]]) / axis_len
    # Force perp to point up in image (negative y). Wheels are always physically
    # below the deck, so this guarantees their projection is negative at rest
    # and the flip-direction sign is consistent regardless of motion direction.
    if perp[1] > 0:
        perp = -perp
    wheels = norm_kp[2:6]
    projs = [float(np.dot(w - nose, perp)) for w in wheels if is_valid_kp(w)]
    return float(np.mean(projs)) if len(projs) >= 2 else None


def _board_flip_direction_signal(norm_kp):
    """Left-minus-right wheel projection — discriminates kickflip from heelflip.

    Returns (left_proj, right_proj, diff) or (None, None, None) if not enough data.
    diff = left_proj - right_proj approximates 2w*sin(theta):
      positive peak -> left wheels were above (kickflip for specific camera/stance)
      negative peak -> right wheels were above (heelflip)
    Indices: 2=front_left, 3=front_right, 4=back_left, 5=back_right.
    """
    nose, tail = norm_kp[0], norm_kp[1]
    axis = tail - nose
    axis_len = float(np.linalg.norm(axis))
    if axis_len < 1.0:
        return None, None, None
    perp = np.array([-axis[1], axis[0]]) / axis_len
    # Force perp to point up in image (negative y) so the sign of diff is
    # consistent regardless of motion direction: diff > 0 always means left
    # wheels are physically above the deck plane.
    if perp[1] > 0:
        perp = -perp
    left  = [norm_kp[i] for i in (2, 4) if is_valid_kp(norm_kp[i])]
    right = [norm_kp[i] for i in (3, 5) if is_valid_kp(norm_kp[i])]
    if not left or not right:
        return None, None, None
    lp = float(np.mean([np.dot(w - nose, perp) for w in left]))
    rp = float(np.mean([np.dot(w - nose, perp) for w in right]))
    return lp, rp, lp - rp
