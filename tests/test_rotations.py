"""Tests for rotations.py."""

import numpy as np
import pytest

from skate_analysis.rotations import (
    _count_body_half_rotations,
    _count_flip_zero_crossings,
)


# ── _count_flip_zero_crossings ─────────────────────────────────────────
class TestCountFlipZeroCrossings:
    def test_empty(self):
        assert _count_flip_zero_crossings(np.array([]), min_amp=10, min_dur=3) == 0

    def test_no_zero_crossings_is_zero(self):
        # Constant-sign signal — no flip.
        sig = np.full(20, -30.0)
        assert _count_flip_zero_crossings(sig, min_amp=10, min_dur=3) == 0

    def test_single_half_rotation_is_zero(self):
        # 2 runs: -+. A 180-degree yaw with wheels going below→above; not a flip.
        sig = np.array([-30.0] * 10 + [+30.0] * 10)
        assert _count_flip_zero_crossings(sig, min_amp=10, min_dur=3) == 0

    def test_full_flip_is_one(self):
        # 3 runs: -+-, mean wheel sweeps below→above→below.
        sig = np.array([-30.0] * 5 + [+30.0] * 5 + [-30.0] * 5)
        assert _count_flip_zero_crossings(sig, min_amp=10, min_dur=3) == 1

    def test_double_flip_is_two(self):
        # 5 runs: -+-+-
        sig = np.tile([[-30.0]*5, [+30.0]*5], (2, 1)).flatten()
        sig = np.concatenate([sig, np.full(5, -30.0)])
        assert _count_flip_zero_crossings(sig, min_amp=10, min_dur=3) == 2

    def test_short_run_filtered_by_min_dur(self):
        # Middle positive run is only 1 frame, below min_dur=3.
        sig = np.array([-30.0]*10 + [+30.0]*1 + [-30.0]*10)
        assert _count_flip_zero_crossings(sig, min_amp=10, min_dur=3) == 0

    def test_low_amplitude_filtered(self):
        # Positive run has amplitude 5, below min_amp=10.
        sig = np.array([-30.0]*5 + [+5.0]*5 + [-30.0]*5)
        assert _count_flip_zero_crossings(sig, min_amp=10, min_dur=3) == 0

    def test_asymmetric_amplitudes_still_count(self):
        # The docstring's key case: -49 peak, +18 peak. Both above min_amp=10.
        sig = np.array([-49.0]*5 + [+18.0]*5 + [-49.0]*5)
        assert _count_flip_zero_crossings(sig, min_amp=10, min_dur=3) == 1


# ── _count_body_half_rotations ─────────────────────────────────────────
class TestCountBodyHalfRotations:
    def test_empty(self):
        assert _count_body_half_rotations([]) == 0

    def test_all_nan_returns_zero(self):
        assert _count_body_half_rotations([float('nan')] * 10) == 0

    def test_no_sign_flip_is_zero(self):
        # Steady positive dx — same stance throughout.
        assert _count_body_half_rotations([10.0] * 20, min_dur=3) == 0

    def test_one_half_rotation(self):
        # Sustained +→sustained −. Threshold = max(|10|) * 0.3 = 3.
        # Both runs are well clear of ±3, with >= min_dur=3 frames.
        dx = [10.0]*5 + [-10.0]*5
        assert _count_body_half_rotations(dx, min_dur=3) == 1

    def test_two_half_rotations(self):
        # +→−→+, three sustained zones.
        dx = [10.0]*5 + [-10.0]*5 + [10.0]*5
        assert _count_body_half_rotations(dx, min_dur=3) == 2

    def test_brief_flicker_does_not_count(self):
        # One frame of negative is below min_dur=3.
        dx = [10.0]*10 + [-10.0]*1 + [10.0]*10
        assert _count_body_half_rotations(dx, min_dur=3) == 0

    def test_below_threshold_floor_returns_zero(self):
        # max(|dx|)*0.3 < 2.0 → function returns 0 by design.
        dx = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
        assert _count_body_half_rotations(dx, min_dur=1) == 0
