"""Tests for detection.py"""

import numpy as np
import pytest

from skate_analysis.data_structures import TrickInterval
from skate_analysis.detection import (
    _combine_stance,
    _find_jump_peaks,
    _find_trick_intervals,
    _trick_frames,
)


# ── _find_jump_peaks ───────────────────────────────────────────────────
class TestFindJumpPeaks:
    def test_single_peak_found(self):
        arr = np.array([0.0, 0.0, 5.0, 0.0, 0.0])
        peaks = _find_jump_peaks(arr, min_height=1.0, min_dist=1)
        assert peaks == [2]

    def test_below_min_height_ignored(self):
        arr = np.array([0.0, 0.5, 0.0, 5.0, 0.0])
        peaks = _find_jump_peaks(arr, min_height=1.0, min_dist=1)
        assert peaks == [3]

    def test_min_distance_filters_close_peaks(self):
        # Two peaks 1 frame apart — min_dist=3 must keep only one.
        arr = np.array([0.0, 5.0, 0.0, 4.0, 0.0, 0.0, 0.0])
        peaks = _find_jump_peaks(arr, min_height=1.0, min_dist=3)
        assert len(peaks) == 1

    def test_nan_handled(self):
        arr = np.array([np.nan, 0.0, 5.0, 0.0, np.nan])
        peaks = _find_jump_peaks(arr, min_height=1.0, min_dist=1)
        assert peaks == [2]


# ── _find_trick_intervals ──────────────────────────────────────────────
class TestFindTrickIntervals:
    def test_empty_returns_empty(self):
        out = _find_trick_intervals(
            height_cm=np.array([]),
            times=np.array([]),
            frame_numbers=[],
            fps=30.0,
            threshold=10.0,
        )
        assert out == []

    def test_all_below_threshold_returns_empty(self):
        height = np.array([0.0, 1.0, 2.0, 1.0, 0.0])
        out = _find_trick_intervals(
            height_cm=height,
            times=np.arange(5) / 30.0,
            frame_numbers=list(range(5)),
            fps=30.0,
            threshold=10.0,
        )
        assert out == []

    def test_single_interval_detected_with_correct_peak(self):
        # Peak at index 3 (height 25).
        height        = np.array([0.0, 12.0, 18.0, 25.0, 15.0, 0.0])
        frame_numbers = [10, 11, 12, 13, 14, 15]
        times         = np.array(frame_numbers, dtype=float) / 30.0
        out = _find_trick_intervals(height, times, frame_numbers, fps=30.0, threshold=10.0)
        assert len(out) == 1
        t = out[0]
        assert isinstance(t, TrickInterval)
        assert t.start_frame == 11
        assert t.end_frame == 14
        assert t.peak_frame == 13
        assert t.peak_height_cm == pytest.approx(25.0)

    def test_nan_treated_as_below_threshold(self):
        height        = np.array([0.0, 20.0, np.nan, 20.0, 0.0])
        frame_numbers = [0, 1, 2, 3, 4]
        times         = np.array(frame_numbers, dtype=float) / 30.0
        out = _find_trick_intervals(height, times, frame_numbers, fps=1.0, threshold=10.0)
        assert len(out) >= 1


# ── _combine_stance ────────────────────────────────────────────────────
class TestCombineStance:
    def test_signal_a_none_returns_unknown(self):
        # natural_fwd is None and signal_b alone cannot decide stance.
        assert _combine_stance(None, True, is_regular=True, direction="rtl") == "unknown"
        assert _combine_stance(None, None, is_regular=True, direction="rtl") == "unknown"

    @pytest.mark.parametrize("signal_a,signal_b,expected", [
        # is_regular=True, direction="rtl"  → natural_fwd = signal_a
        (True,  True,  "normal"),
        (False, True,  "switch"),
        (True,  False, "nollie"),
        (False, False, "fakie"),
    ])
    def test_truth_table_regular_rtl(self, signal_a, signal_b, expected):
        assert _combine_stance(signal_a, signal_b, is_regular=True, direction="rtl") == expected

    def test_regular_ltr_inverts_signal_a(self):
        # ltr+regular: natural_fwd = not signal_a, so signal_a=True flips the row.
        assert _combine_stance(True,  True,  is_regular=True, direction="ltr") == "switch"
        assert _combine_stance(False, True,  is_regular=True, direction="ltr") == "normal"

    def test_goofy_inverts_signal_a(self):
        # goofy: natural_fwd = not signal_a.
        assert _combine_stance(True,  True,  is_regular=False, direction="rtl") == "switch"
        assert _combine_stance(False, True,  is_regular=False, direction="rtl") == "normal"

    def test_signal_b_none_falls_back_to_signal_a_only(self):
        assert _combine_stance(True,  None, is_regular=True, direction="rtl") == "normal"
        assert _combine_stance(False, None, is_regular=True, direction="rtl") == "switch"


# ── _trick_frames ──────────────────────────────────────────────────────
def _make_trick(start: int, end: int) -> TrickInterval:
    return TrickInterval(
        start_frame=start, end_frame=end,
        start_time=0.0, end_time=0.0, duration_s=0.0,
        peak_height_cm=0.0, peak_frame=start, peak_time=0.0,
    )


class TestTrickFrames:
    def test_empty_tricks_returns_empty_set(self):
        assert _trick_frames(None, [1, 2, 3]) == set()
        assert _trick_frames([], [1, 2, 3]) == set()

    def test_collects_frames_inside_interval(self):
        tricks = [_make_trick(5, 10)]
        frame_numbers = [3, 5, 7, 10, 12]
        assert _trick_frames(tricks, frame_numbers) == {5, 7, 10}

    def test_multiple_tricks_union(self):
        tricks = [_make_trick(0, 2), _make_trick(8, 9)]
        frame_numbers = [0, 1, 2, 3, 7, 8, 9, 10]
        assert _trick_frames(tricks, frame_numbers) == {0, 1, 2, 8, 9}
