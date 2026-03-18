import numpy as np
import pytest

from chopshop.analysis import SliceMap, analyze


def _make_clicks(sr=44100, duration=2.0, click_times=None):
    """Generate synthetic audio with sharp clicks at specified times."""
    if click_times is None:
        click_times = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75]
    total = int(duration * sr)
    y = np.zeros(total, dtype=np.float32)
    for t in click_times:
        idx = int(t * sr)
        if idx < total:
            # Short burst of noise to simulate a transient
            end = min(idx + 200, total)
            y[idx:end] = np.random.default_rng(42).uniform(-1, 1, end - idx).astype(np.float32)
    return y, sr


def _make_sine(sr=44100, duration=2.0, freq=440.0):
    """Generate a pure sine wave (no transients)."""
    t = np.linspace(0, duration, int(duration * sr), dtype=np.float32)
    return np.sin(2 * np.pi * freq * t).astype(np.float32), sr


class TestOnsetMode:
    def test_basic_onset_detection(self):
        y, sr = _make_clicks()
        sm = analyze(y, sr, mode="onset")
        assert sm.mode == "onset"
        assert len(sm.slices) >= 2
        # Slices are chronologically ordered
        for i in range(1, len(sm.slices)):
            assert sm.slices[i].start_sample > sm.slices[i - 1].start_sample
        # Last slice ends at total samples
        assert sm.slices[-1].end_sample == sm.total_samples

    def test_threshold_sensitivity(self):
        y, sr = _make_clicks()
        low = analyze(y, sr, mode="onset", threshold=0.1)
        high = analyze(y, sr, mode="onset", threshold=0.9)
        assert len(low.slices) >= len(high.slices)

    def test_num_slices_override(self):
        y, sr = _make_clicks()
        sm = analyze(y, sr, mode="onset", num_slices=4)
        assert len(sm.slices) == 4
        # Still chronological
        for i in range(1, len(sm.slices)):
            assert sm.slices[i].start_sample > sm.slices[i - 1].start_sample


class TestGridMode:
    def test_grid_16th(self):
        sr = 44100
        bpm = 120.0
        duration = 4.0
        y = np.zeros(int(duration * sr), dtype=np.float32)
        sm = analyze(y, sr, mode="grid", quantize_bpm=bpm, grid_resolution="16th")
        assert sm.mode == "grid"
        # At 120 BPM, 16th note = 5512 samples. Grid trims tiny trailing slices.
        assert 30 <= len(sm.slices) <= 33
        # All slices have non-negligible duration
        for s in sm.slices:
            assert s.end_sample > s.start_sample

    def test_grid_8th(self):
        sr = 44100
        bpm = 120.0
        duration = 4.0
        y = np.zeros(int(duration * sr), dtype=np.float32)
        sm = analyze(y, sr, mode="grid", quantize_bpm=bpm, grid_resolution="8th")
        # 8th notes = half as many slices as 16th
        assert len(sm.slices) == 16

    def test_grid_with_explicit_bpm(self):
        sr = 44100
        duration = 4.0
        y = np.zeros(int(duration * sr), dtype=np.float32)
        sm = analyze(y, sr, mode="grid", quantize_bpm=130.0, grid_resolution="16th")
        interval_samples = int(60.0 / 130.0 / 4 * sr)
        expected = len(range(0, int(duration * sr), interval_samples))
        assert len(sm.slices) == expected


class TestEqualMode:
    def test_equal_division(self):
        sr = 44100
        y = np.zeros(sr * 2, dtype=np.float32)  # 2 seconds
        sm = analyze(y, sr, mode="equal", num_slices=8)
        assert sm.mode == "equal"
        assert len(sm.slices) == 8
        # All slices have equal duration (within 1 sample)
        lengths = [s.end_sample - s.start_sample for s in sm.slices]
        assert max(lengths) - min(lengths) <= 1

    def test_equal_requires_num_slices(self):
        sr = 44100
        y = np.zeros(sr, dtype=np.float32)
        with pytest.raises(ValueError, match="num-slices"):
            analyze(y, sr, mode="equal")


class TestGeneral:
    def test_start_end_trimming(self):
        sr = 44100
        duration = 4.0
        y = np.zeros(int(duration * sr), dtype=np.float32)
        # Trim to 1.0-3.0 (2 seconds)
        trimmed = y[int(1.0 * sr) : int(3.0 * sr)]
        sm = analyze(trimmed, sr, mode="equal", num_slices=4)
        assert abs(sm.duration - 2.0) < 0.01
        for s in sm.slices:
            assert s.start_seconds <= 2.0

    def test_mode_field_consistency(self):
        sr = 44100
        y = np.zeros(sr * 2, dtype=np.float32)
        for mode in ["onset", "grid", "equal"]:
            kwargs = {"mode": mode}
            if mode == "equal":
                kwargs["num_slices"] = 4
            if mode == "grid":
                kwargs["quantize_bpm"] = 120.0
            sm = analyze(y, sr, **kwargs)
            assert sm.mode == mode

    def test_slices_cover_full_range(self):
        """First slice starts at 0, last slice ends at total_samples."""
        y, sr = _make_clicks()
        sm = analyze(y, sr, mode="onset")
        assert sm.slices[0].start_sample == 0
        assert sm.slices[-1].end_sample == sm.total_samples
