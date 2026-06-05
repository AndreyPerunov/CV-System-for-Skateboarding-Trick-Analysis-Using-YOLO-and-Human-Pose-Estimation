from .config import FS_BS_MIN_DEG, SPIN_SNAP_TOLERANCE_DEG


def flip_label(
    flip:       int | float | None,
    stance:     str,
    is_regular: bool,
) -> str | None:
    """Return 'kickflip' or 'heelflip' from signed flip + stance + handedness.

    A kickflip rotates over the toes, a heelflip over the heels. Which on-board
    rotation that corresponds to depends on (a) which foot is in front
    (is_regular vs goofy) and (b) which end of the board the rider is currently
    facing (natural = normal/nollie; reversed = switch/fakie).

    Args:
        flip:       signed flip metric (e.g. compute_trick_rotations()['flip_count']).
                    > 0 = left wheels rise first (CW around tail->nose),
                    < 0 = right wheels rise first (CCW).
        stance:     'normal' | 'switch' | 'nollie' | 'fakie'.
        is_regular: True = regular (left foot front), False = goofy (right foot front).

    Returns:
        'kickflip' or 'heelflip', or None if flip is 0/None or stance is unknown.
    """
    if flip is None or flip == 0:
        return None
    if stance not in ('normal', 'switch', 'nollie', 'fakie'):
        return None
    natural_stance = stance in ('normal', 'nollie')
    flip_positive  = flip > 0
    is_kickflip    = (flip_positive == natural_stance) != is_regular
    return 'kickflip' if is_kickflip else 'heelflip'


def _board_spin_label(yaw_deg: float | None, tol: float = SPIN_SNAP_TOLERANCE_DEG) -> int | None:
    """Snap a signed board-yaw delta to {0, ±180, ±360, ±540, ±720} within ±tol.

    Returns the signed multiple of 180 (sign preserves CW/CCW). Returns None
    if `yaw_deg` is None or falls in a gray zone between anchors.
    """
    if yaw_deg is None:
        return None
    abs_y = abs(yaw_deg)
    for k in (0, 180, 360, 540, 720):
        if abs(abs_y - k) <= tol:
            return k if yaw_deg >= 0 else -k
    return None


def _body_spin_label(body_rot_deg: int | None, tol: float = SPIN_SNAP_TOLERANCE_DEG) -> int | None:
    """Snap signed body-rotation magnitude (multiples of 180) to {0, ±180, ±360, ±540}.

    `compute_body_rotation` already returns integer multiples of 180, so within
    the supported range this is the identity. The same ±tol gray-zone rule is
    applied for symmetry with `_board_spin_label`; values beyond 540 + tol
    return None (out of taxonomy).
    """
    if body_rot_deg is None:
        return None
    abs_v = abs(body_rot_deg)
    for k in (0, 180, 360, 540):
        if abs(abs_v - k) <= tol:
            return k if body_rot_deg >= 0 else -k
    return None


def _fs_bs_label(yaw_deg: float | None, is_regular: bool, min_deg: float = FS_BS_MIN_DEG) -> str:
    """Return 'FS' or 'BS' from board-yaw sign + handedness, or '' if indeterminate.

    Sign convention (after the rotation-logic rewrite): CW = positive.
        goofy  -> FS when yaw > 0, BS when yaw < 0.
        regular -> mirror: FS when yaw < 0, BS when yaw > 0.

    Returns '' when |yaw_deg| < min_deg (rotation too small to call) or yaw_deg is None.
    """
    if yaw_deg is None or abs(yaw_deg) < min_deg:
        return ''
    cw = yaw_deg > 0
    fs = cw if not is_regular else (not cw)
    return 'FS' if fs else 'BS'


_STANCE_PREFIX = {
    'normal': '',
    'switch': 'switch',
    'fakie':  'fakie',
    'nollie': 'nollie',
}

# (abs_board, abs_body, flip_label_or_None) -> base name (no FS/BS, no stance prefix).
_BASE_TRICK_TABLE = {
    (0,   0,   None):        'ollie',
    (0,   0,   'kickflip'):  'kickflip',
    (0,   0,   'heelflip'):  'heelflip',

    (180, 0,   None):        'pop shove-it',
    (180, 0,   'kickflip'):  'varial kickflip',
    (180, 0,   'heelflip'):  'varial heelflip',

    (180, 180, None):        '180',
    (180, 180, 'kickflip'):  '180 kickflip',
    (180, 180, 'heelflip'):  '180 heelflip',

    (360, 0,   None):        '360 shove-it',
    (360, 0,   'kickflip'):  '360 flip',
    (360, 0,   'heelflip'):  '360 heelflip',

    (360, 180, None):        'big spin',
    (360, 180, 'kickflip'):  'big flip',
    (360, 180, 'heelflip'):  'big spin heelflip',

    (360, 360, None):        '360',
    (360, 360, 'kickflip'):  '360 kickflip',
    (360, 360, 'heelflip'):  '360 heelflip',

    (540, 540, None):        '540',
}


def classify_trick(
    yaw_deg: float | None,
    flip_count: int | float | None,
    body_rot_deg: int | None,
    stance: str,
    is_regular: bool,
) -> str:
    """Compose a full trick name from kinematic measurements + stance + handedness.

    Steps:
      1. Snap board/body yaw to {0, 180, 360, 540} (_board_spin_label, _body_spin_label).
      2. Resolve flip type (flip_label).
      3. Look up base name from (abs_board, abs_body, flip) in _BASE_TRICK_TABLE.
      4. Prepend FS/BS (_fs_bs_label) when |board| >= 180.
      5. Prepend stance prefix for switch / fakie / nollie.

    Sign convention: CW = positive. Goofy FS -> yaw>0; regular FS -> yaw<0.

    Args:
        yaw_deg:      signed board-yaw delta from compute_trick_rotations().
        flip_count:   signed flip count from compute_trick_rotations().
        body_rot_deg: signed body rotation from compute_body_rotation()
                      (first non-zero of shoulder/hip/wrist/ankle).
        stance:       'normal'/'switch'/'fakie'/'nollie' from detect_stance().
        is_regular:   True = regular, False = goofy.

    Returns:
        Composed name like 'BS 180', 'switch FS 180 kickflip', 'kickflip',
        or 'unknown' when the rotation pattern is outside _BASE_TRICK_TABLE.
    """
    board = _board_spin_label(yaw_deg)
    if board is None:
        return 'unknown'

    body  = _body_spin_label(body_rot_deg)
    abs_b = abs(body) if body is not None else 0

    flip = flip_label(flip_count, stance, is_regular)

    base = _BASE_TRICK_TABLE.get((abs(board), abs_b, flip))
    if base is None:
        return 'unknown'

    parts = []
    stance_pref = _STANCE_PREFIX.get(stance, '')
    if stance_pref:
        parts.append(stance_pref)

    if abs(board) >= 180:
        side = _fs_bs_label(yaw_deg, is_regular)
        if side:
            parts.append(side)

    parts.append(base)
    return ' '.join(parts)
