"""Tests for chopmap JSON export."""

import json

import numpy as np
import pytest

from chopshop.analysis import Slice, SliceMap
from chopshop.chopmap import export_chopmap
from chopshop.export import ExportResult


def _make_slice_map(n_slices: int = 4, sr: int = 44100) -> SliceMap:
    segment = sr  # 1 second per slice
    slices = []
    for i in range(n_slices):
        slices.append(Slice(
            index=i,
            start_sample=i * segment,
            end_sample=(i + 1) * segment,
            start_seconds=i * 1.0,
            end_seconds=(i + 1) * 1.0,
            label=["kick", "snare", "hat_closed", "other"][i % 4],
        ))
    return SliceMap(
        source_path="/tmp/test.wav",
        sample_rate=sr,
        bpm=120.0,
        duration=n_slices * 1.0,
        total_samples=n_slices * segment,
        mode="onset",
        slices=slices,
    )


def _make_export_result(n_slices: int, tmp_path) -> ExportResult:
    chop_paths = []
    for i in range(n_slices):
        p = tmp_path / f"test_chop_{i:02d}.wav"
        p.write_bytes(b"RIFF")
        chop_paths.append(p)
    return ExportResult(
        output_dir=tmp_path,
        chop_paths=chop_paths,
        sample_rate=44100,
        source_name="test",
    )


class TestChopmap:
    def test_valid_json_output(self, tmp_path):
        sm = _make_slice_map(4)
        er = _make_export_result(4, tmp_path)
        path = export_chopmap(sm, er, "test_preset", chop_root=60)
        data = json.loads(path.read_text())
        assert data["chopmap_version"] == "1.0"
        assert data["name"] == "test_preset"

    def test_required_fields(self, tmp_path):
        sm = _make_slice_map(4)
        er = _make_export_result(4, tmp_path)
        path = export_chopmap(sm, er, "test_preset", chop_root=60)
        data = json.loads(path.read_text())
        required = ["chopmap_version", "name", "source_file", "source_bpm",
                     "detected_bpm", "num_slices", "base_note", "base_note_name", "slices"]
        for key in required:
            assert key in data, f"Missing key: {key}"

    def test_slice_count_matches(self, tmp_path):
        sm = _make_slice_map(6)
        er = _make_export_result(6, tmp_path)
        path = export_chopmap(sm, er, "test", chop_root=60)
        data = json.loads(path.read_text())
        assert data["num_slices"] == 6
        assert len(data["slices"]) == 6

    def test_labels_preserved(self, tmp_path):
        sm = _make_slice_map(4)
        er = _make_export_result(4, tmp_path)
        path = export_chopmap(sm, er, "test", chop_root=60)
        data = json.loads(path.read_text())
        labels = [s["label"] for s in data["slices"]]
        assert labels == ["kick", "snare", "hat_closed", "other"]

    def test_midi_notes_sequential(self, tmp_path):
        sm = _make_slice_map(4)
        er = _make_export_result(4, tmp_path)
        path = export_chopmap(sm, er, "test", chop_root=60)
        data = json.loads(path.read_text())
        notes = [s["midi_note"] for s in data["slices"]]
        assert notes == [60, 61, 62, 63]

    def test_source_bpm_included(self, tmp_path):
        sm = _make_slice_map(2)
        er = _make_export_result(2, tmp_path)
        path = export_chopmap(sm, er, "test", chop_root=60, source_bpm=165.0)
        data = json.loads(path.read_text())
        assert data["source_bpm"] == 165.0

    def test_source_bpm_none(self, tmp_path):
        sm = _make_slice_map(2)
        er = _make_export_result(2, tmp_path)
        path = export_chopmap(sm, er, "test", chop_root=60)
        data = json.loads(path.read_text())
        assert data["source_bpm"] is None
