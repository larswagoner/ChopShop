"""Tests for MIDI generation."""

import json

import mido
import pytest

from chopshop.midi_gen import (
    build_label_map,
    generate_midi,
    list_presets,
    load_pattern,
)


def _make_chopmap(labels=None):
    if labels is None:
        labels = ["kick", "snare", "hat_closed", "hat_open"]
    slices = []
    for i, label in enumerate(labels):
        slices.append({
            "index": i,
            "midi_note": 60 + i,
            "note_name": f"note_{i}",
            "label": label,
            "file": f"chop_{i:02d}.wav",
            "start_sec": i * 0.5,
            "end_sec": (i + 1) * 0.5,
            "duration_sec": 0.5,
        })
    return {
        "chopmap_version": "1.0",
        "name": "test",
        "source_file": "test.wav",
        "source_bpm": None,
        "detected_bpm": 120.0,
        "num_slices": len(labels),
        "base_note": 60,
        "base_note_name": "C3",
        "slices": slices,
    }


def _simple_pattern():
    return {
        "name": "test",
        "bpm": 120,
        "bars": 1,
        "time_signature": [4, 4],
        "resolution": 16,
        "tracks": [{
            "name": "drums",
            "channel": 9,
            "steps": [
                {"pos": 0, "label": "kick", "velocity": 120},
                {"pos": 4, "label": "snare", "velocity": 110},
                {"pos": 8, "label": "kick", "velocity": 120},
                {"pos": 12, "label": "snare", "velocity": 110},
            ],
        }],
    }


class TestBuildLabelMap:
    def test_basic_mapping(self):
        chopmap = _make_chopmap()
        label_map = build_label_map(chopmap)
        assert label_map["kick"] == 60
        assert label_map["snare"] == 61
        assert label_map["hat_closed"] == 62

    def test_first_occurrence_wins(self):
        chopmap = _make_chopmap(["kick", "kick", "snare"])
        label_map = build_label_map(chopmap)
        assert label_map["kick"] == 60  # first kick, not second


class TestGenerateMidi:
    def test_output_file_created(self, tmp_path):
        chopmap = _make_chopmap()
        pattern = _simple_pattern()
        out = tmp_path / "test.mid"
        result = generate_midi(chopmap, pattern, output=out)
        assert result.exists()

    def test_output_parseable_by_mido(self, tmp_path):
        chopmap = _make_chopmap()
        pattern = _simple_pattern()
        out = tmp_path / "test.mid"
        generate_midi(chopmap, pattern, output=out)
        mid = mido.MidiFile(str(out))
        assert len(mid.tracks) >= 1

    def test_correct_tempo(self, tmp_path):
        chopmap = _make_chopmap()
        pattern = _simple_pattern()
        out = tmp_path / "test.mid"
        generate_midi(chopmap, pattern, bpm=170, output=out)
        mid = mido.MidiFile(str(out))
        # Check tempo message
        for msg in mid.tracks[0]:
            if msg.type == "set_tempo":
                assert msg.tempo == mido.bpm2tempo(170)
                break

    def test_bar_repetition(self, tmp_path):
        chopmap = _make_chopmap()
        pattern = _simple_pattern()
        out1 = tmp_path / "one.mid"
        out2 = tmp_path / "two.mid"
        generate_midi(chopmap, pattern, bars=1, output=out1)
        generate_midi(chopmap, pattern, bars=2, output=out2)
        mid1 = mido.MidiFile(str(out1))
        mid2 = mido.MidiFile(str(out2))
        # 2-bar version should have roughly twice the note events
        notes1 = sum(1 for msg in mid1.tracks[1] if msg.type == "note_on")
        notes2 = sum(1 for msg in mid2.tracks[1] if msg.type == "note_on")
        assert notes2 == notes1 * 2

    def test_missing_label_skipped(self, tmp_path, capsys):
        chopmap = _make_chopmap(["kick", "snare"])  # no hat_closed
        pattern = {
            "name": "test",
            "bpm": 120,
            "bars": 1,
            "time_signature": [4, 4],
            "resolution": 16,
            "tracks": [{
                "name": "drums",
                "channel": 9,
                "steps": [
                    {"pos": 0, "label": "kick", "velocity": 120},
                    {"pos": 4, "label": "hat_closed", "velocity": 90},  # not in chopmap
                ],
            }],
        }
        out = tmp_path / "test.mid"
        generate_midi(chopmap, pattern, output=out)
        captured = capsys.readouterr()
        assert "hat_closed" in captured.err

    def test_bpm_override(self, tmp_path):
        chopmap = _make_chopmap()
        pattern = _simple_pattern()
        out = tmp_path / "test.mid"
        generate_midi(chopmap, pattern, bpm=200, output=out)
        mid = mido.MidiFile(str(out))
        for msg in mid.tracks[0]:
            if msg.type == "set_tempo":
                assert msg.tempo == mido.bpm2tempo(200)
                break


class TestPresets:
    def test_list_presets(self):
        presets = list_presets()
        assert "basic-jungle" in presets
        assert "amen-classic" in presets
        assert "halftime" in presets
        assert "roller" in presets

    def test_load_builtin_preset(self):
        pattern = load_pattern("basic-jungle")
        assert "tracks" in pattern
        assert pattern["name"] == "Basic Jungle"

    def test_all_presets_valid(self, tmp_path):
        chopmap = _make_chopmap(
            ["kick", "snare", "snare_ghost", "hat_closed", "hat_open", "ride", "crash"]
        )
        for name in list_presets():
            pattern = load_pattern(name)
            out = tmp_path / f"{name}.mid"
            result = generate_midi(chopmap, pattern, output=out)
            assert result.exists()
            mid = mido.MidiFile(str(result))
            assert len(mid.tracks) >= 1
