"""Tests for classification.py"""

import pytest

from skate_analysis.classification import (
    _board_spin_label,
    _body_spin_label,
    _fs_bs_label,
    classify_trick,
    flip_label,
)


# ── flip_label ─────────────────────────────────────────────────────────
class TestFlipLabel:
    def test_zero_or_none_returns_none(self):
        assert flip_label(0, "normal", True) is None
        assert flip_label(None, "normal", True) is None

    def test_unknown_stance_returns_none(self):
        assert flip_label(1, "unknown", True) is None
        assert flip_label(1, "", False) is None

    @pytest.mark.parametrize("stance,is_regular,flip,expected", [
        # Regular, natural stance: +flip → heelflip, −flip → kickflip
        ("normal", True,  +1, "heelflip"),
        ("normal", True,  -1, "kickflip"),
        ("nollie", True,  +1, "heelflip"),
        ("nollie", True,  -1, "kickflip"),
        # Regular, reversed stance: mirrors
        ("switch", True,  +1, "kickflip"),
        ("switch", True,  -1, "heelflip"),
        ("fakie",  True,  +1, "kickflip"),
        ("fakie",  True,  -1, "heelflip"),
        # Goofy: opposite of regular
        ("normal", False, +1, "kickflip"),
        ("normal", False, -1, "heelflip"),
        ("switch", False, +1, "heelflip"),
        ("switch", False, -1, "kickflip"),
    ])
    def test_truth_table(self, stance, is_regular, flip, expected):
        assert flip_label(flip, stance, is_regular) == expected


# ── _board_spin_label ──────────────────────────────────────────────────
class TestBoardSpinLabel:
    def test_none_passthrough(self):
        assert _board_spin_label(None) is None

    @pytest.mark.parametrize("yaw,expected", [
        (0,    0),
        (12,   0),
        (-38,  0),
        (135,  180),
        (178,  180),
        (-183, -180),
        (225,  180),
        (315,  360),
        (360,  360),
        (405,  360),
        (540,  540),
        (720,  720),
    ])
    def test_snap_to_anchor(self, yaw, expected):
        assert _board_spin_label(yaw) == expected

    @pytest.mark.parametrize("yaw", [50, 90, 270, 450, 630])
    def test_gray_zone_returns_none(self, yaw):
        # Halfway between anchors, outside ±45 tolerance.
        assert _board_spin_label(yaw) is None

    def test_sign_preserved(self):
        assert _board_spin_label(-360) == -360
        assert _board_spin_label(-540) == -540


# ── _body_spin_label ───────────────────────────────────────────────────
class TestBodySpinLabel:
    def test_none_passthrough(self):
        assert _body_spin_label(None) is None

    @pytest.mark.parametrize("v,expected", [
        (0,    0),
        (180,  180),
        (-180, -180),
        (360,  360),
        (540,  540),
    ])
    def test_identity_within_taxonomy(self, v, expected):
        assert _body_spin_label(v) == expected

    def test_out_of_taxonomy_returns_none(self):
        assert _body_spin_label(720) is None


# ── _fs_bs_label ───────────────────────────────────────────────────────
class TestFsBsLabel:
    def test_none_or_small_returns_empty(self):
        assert _fs_bs_label(None, True) == ""
        assert _fs_bs_label(45, True) == ""
        assert _fs_bs_label(-45, False) == ""

    @pytest.mark.parametrize("yaw,is_regular,expected", [
        # CW = positive. Goofy FS=CW, regular FS=CCW.
        (+180, False, "FS"),
        (-180, False, "BS"),
        (+180, True,  "BS"),
        (-180, True,  "FS"),
    ])
    def test_sign_to_label(self, yaw, is_regular, expected):
        assert _fs_bs_label(yaw, is_regular) == expected


# ── classify_trick (integration over the lookup table) ────────────────
class TestClassifyTrick:
    def test_unknown_when_board_in_gray_zone(self):
        assert classify_trick(70, 0, 0, "normal", True) == "unknown"

    def test_ollie(self):
        assert classify_trick(0, 0, 0, "normal", True) == "ollie"

    def test_kickflip_regular_normal(self):
        # flip < 0 + regular + normal → kickflip; no board/body spin
        assert classify_trick(0, -1, 0, "normal", True) == "kickflip"

    def test_heelflip_regular_normal(self):
        assert classify_trick(0, +1, 0, "normal", True) == "heelflip"

    def test_fs_180_goofy(self):
        # CW yaw, goofy, body matches board → FS 180
        assert classify_trick(180, 0, 180, "normal", False) == "FS 180"

    def test_bs_180_regular(self):
        assert classify_trick(180, 0, 180, "normal", True) == "BS 180"

    def test_switch_stance_prefix(self):
        assert classify_trick(0, 0, 0, "switch", True) == "switch ollie"

    def test_360_flip(self):
        # 360 board, 0 body, kickflip → "360 flip"
        # In regular normal stance, kickflip means flip < 0.
        assert classify_trick(360, -1, 0, "normal", True) == "BS 360 flip"
