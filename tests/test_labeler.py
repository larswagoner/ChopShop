"""Tests for the auto-labeling heuristic."""

import numpy as np
import pytest

from chopshop.analysis import Slice
from chopshop.labeler import (
    STANDARD_LABELS,
    auto_label,
    auto_label_single,
)


def _make_slice(start: int, end: int, sr: int = 44100) -> Slice:
    return Slice(
        index=0,
        start_sample=start,
        end_sample=end,
        start_seconds=start / sr,
        end_seconds=end / sr,
    )


def _low_burst(sr: int = 44100, duration: float = 0.05, freq: float = 80.0) -> np.ndarray:
    """Generate a short low-frequency burst (kick-like)."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * np.exp(-t * 30)).astype(np.float32)


def _noise_burst(sr: int = 44100, duration: float = 0.03) -> np.ndarray:
    """Generate a short noise burst (hat-like)."""
    n = int(sr * duration)
    rng = np.random.default_rng(42)
    return (rng.standard_normal(n) * 0.3).astype(np.float32)


def _mid_noise(sr: int = 44100, duration: float = 0.05) -> np.ndarray:
    """Generate a mid-frequency noisy burst (snare-like)."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = np.sin(2 * np.pi * 200 * t) * np.exp(-t * 20)
    rng = np.random.default_rng(99)
    noise = rng.standard_normal(len(t)) * 0.2
    return (tone + noise).astype(np.float32)


class TestAutoLabel:
    def test_output_length_matches_slices(self):
        sr = 44100
        kick = _low_burst(sr)
        hat = _noise_burst(sr)
        y = np.concatenate([kick, hat, kick])
        slices = [
            _make_slice(0, len(kick), sr),
            _make_slice(len(kick), len(kick) + len(hat), sr),
            _make_slice(len(kick) + len(hat), len(y), sr),
        ]
        labels = auto_label(y, sr, slices)
        assert len(labels) == len(slices)

    def test_all_labels_are_valid(self):
        sr = 44100
        kick = _low_burst(sr)
        hat = _noise_burst(sr)
        snare = _mid_noise(sr)
        y = np.concatenate([kick, hat, snare])
        slices = [
            _make_slice(0, len(kick), sr),
            _make_slice(len(kick), len(kick) + len(hat), sr),
            _make_slice(len(kick) + len(hat), len(y), sr),
        ]
        labels = auto_label(y, sr, slices)
        for label in labels:
            assert label in STANDARD_LABELS, f"Unexpected label: {label}"

    def test_empty_slices(self):
        labels = auto_label(np.zeros(1000, dtype=np.float32), 44100, [])
        assert labels == []

    def test_low_burst_classified_as_kick(self):
        sr = 44100
        kick = _low_burst(sr, duration=0.08)
        hat = _noise_burst(sr, duration=0.03)
        # Make a file with a clear kick and a clear hat so medians differ
        y = np.concatenate([kick, hat, kick, hat])
        kl = len(kick)
        hl = len(hat)
        slices = [
            _make_slice(0, kl, sr),
            _make_slice(kl, kl + hl, sr),
            _make_slice(kl + hl, 2 * kl + hl, sr),
            _make_slice(2 * kl + hl, len(y), sr),
        ]
        labels = auto_label(y, sr, slices)
        # At least one should be kick
        assert "kick" in labels


class TestAutoLabelSingle:
    def test_returns_valid_label(self):
        sr = 44100
        seg = _low_burst(sr)
        label = auto_label_single(seg, sr, 0, len(seg))
        assert label in STANDARD_LABELS

    def test_very_short_segment_returns_other(self):
        sr = 44100
        seg = np.zeros(10, dtype=np.float32)
        label = auto_label_single(seg, sr, 0, len(seg))
        assert label == "other"
