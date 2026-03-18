import numpy as np
import soundfile as sf
import pytest
from pathlib import Path

from chopshop.analysis import Slice, SliceMap
from chopshop.export import export_slices


def _make_slice_map(sr=44100, total_samples=44100, num_slices=4):
    """Create a simple SliceMap with equal divisions."""
    seg = total_samples // num_slices
    slices = []
    for i in range(num_slices):
        start = i * seg
        end = (i + 1) * seg if i < num_slices - 1 else total_samples
        slices.append(Slice(
            index=i,
            start_sample=start,
            end_sample=end,
            start_seconds=start / sr,
            end_seconds=end / sr,
        ))
    return SliceMap(
        source_path="test.wav",
        sample_rate=sr,
        bpm=120.0,
        duration=total_samples / sr,
        total_samples=total_samples,
        mode="equal",
        slices=slices,
    )


class TestExportSlices:
    def test_basic_export(self, tmp_path):
        sr = 44100
        y = np.random.default_rng(42).uniform(-1, 1, sr).astype(np.float32)
        sm = _make_slice_map(sr=sr, total_samples=sr, num_slices=4)

        result = export_slices(y, sr, sm, tmp_path, "test", include_full=False)
        assert len(result.chop_paths) == 4
        for p in result.chop_paths:
            assert p.exists()
            data, rate = sf.read(str(p))
            assert rate == sr
            assert len(data) == sr // 4

    def test_file_naming(self, tmp_path):
        sr = 44100
        y = np.zeros(sr, dtype=np.float32)
        sm = _make_slice_map(sr=sr, total_samples=sr, num_slices=3)

        result = export_slices(y, sr, sm, tmp_path, "mybreak", include_full=False)
        names = [p.name for p in result.chop_paths]
        assert names == [
            "mybreak_chop_00.wav",
            "mybreak_chop_01.wav",
            "mybreak_chop_02.wav",
        ]

    def test_fade_application(self, tmp_path):
        sr = 44100
        y = np.ones(sr, dtype=np.float32)
        sm = _make_slice_map(sr=sr, total_samples=sr, num_slices=1)

        result = export_slices(y, sr, sm, tmp_path, "test", fade_ms=10.0, include_full=False)
        data, _ = sf.read(str(result.chop_paths[0]))
        # Last sample should be ~0
        assert abs(data[-1]) < 0.01
        # Sample well before the fade should be ~1
        fade_samples = int(0.010 * sr)
        assert data[-(fade_samples + 10)] > 0.99

    def test_full_file(self, tmp_path):
        sr = 44100
        y = np.random.default_rng(42).uniform(-1, 1, sr).astype(np.float32)
        sm = _make_slice_map(sr=sr, total_samples=sr, num_slices=2)

        result = export_slices(y, sr, sm, tmp_path, "test", include_full=True)
        assert result.full_path is not None
        assert result.full_path.exists()
        data, _ = sf.read(str(result.full_path))
        assert len(data) == sr

    def test_cue_zones(self, tmp_path):
        sr = 44100
        y = np.random.default_rng(42).uniform(-1, 1, sr).astype(np.float32)
        sm = _make_slice_map(sr=sr, total_samples=sr, num_slices=4)

        result = export_slices(y, sr, sm, tmp_path, "test", cue_zones=True, include_full=False)
        assert len(result.cue_paths) == 4
        # First cue should be the full file length
        data0, _ = sf.read(str(result.cue_paths[0]))
        assert len(data0) == sr
        # Last cue should be ~1/4 of the file
        data3, _ = sf.read(str(result.cue_paths[3]))
        assert len(data3) == sr - (3 * (sr // 4))

    def test_slice_content_accuracy(self, tmp_path):
        sr = 44100
        # Fill each quarter with a distinct value
        y = np.zeros(sr, dtype=np.float32)
        seg = sr // 4
        y[0:seg] = 0.25
        y[seg:2*seg] = 0.5
        y[2*seg:3*seg] = 0.75
        y[3*seg:] = 1.0
        sm = _make_slice_map(sr=sr, total_samples=sr, num_slices=4)

        result = export_slices(y, sr, sm, tmp_path, "test", include_full=False)
        for i, (path, expected_val) in enumerate(
            zip(result.chop_paths, [0.25, 0.5, 0.75, 1.0])
        ):
            data, _ = sf.read(str(path))
            assert np.allclose(data, expected_val, atol=0.001), f"Slice {i} content mismatch"

    def test_creates_output_dir(self, tmp_path):
        new_dir = tmp_path / "nonexistent" / "deep"
        sr = 44100
        y = np.zeros(sr, dtype=np.float32)
        sm = _make_slice_map(sr=sr, total_samples=sr, num_slices=1)

        result = export_slices(y, sr, sm, new_dir, "test", include_full=False)
        assert new_dir.exists()
        assert len(result.chop_paths) == 1
