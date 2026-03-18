import plistlib
from pathlib import Path

import pytest

from chopshop.analysis import Slice, SliceMap
from chopshop.export import ExportResult
from chopshop.preset import generate_preset


def _make_export_result(tmp_path, num_slices=4, include_full=True, cue_zones=False):
    """Create a mock ExportResult with fake WAV paths."""
    chop_paths = [tmp_path / f"test_chop_{i:02d}.wav" for i in range(num_slices)]
    for p in chop_paths:
        p.touch()

    cue_paths = []
    if cue_zones:
        cue_paths = [tmp_path / f"test_cue_{i:02d}.wav" for i in range(num_slices)]
        for p in cue_paths:
            p.touch()

    full_path = None
    if include_full:
        full_path = tmp_path / "test_full.wav"
        full_path.touch()

    return ExportResult(
        output_dir=tmp_path,
        chop_paths=chop_paths,
        cue_paths=cue_paths,
        full_path=full_path,
        sample_rate=44100,
        source_name="test",
    )


def _make_slice_map(num_slices=4):
    slices = [
        Slice(i, i * 11025, (i + 1) * 11025, i * 0.25, (i + 1) * 0.25)
        for i in range(num_slices)
    ]
    return SliceMap(
        source_path="test.wav", sample_rate=44100, bpm=120.0,
        duration=1.0, total_samples=44100, mode="equal", slices=slices,
    )


class TestPresetGeneration:
    def test_valid_plist(self, tmp_path):
        er = _make_export_result(tmp_path)
        sm = _make_slice_map()
        data = generate_preset(er, sm, "test_preset")
        parsed = plistlib.loads(data)
        assert "Instrument" in parsed
        assert "Layers" in parsed["Instrument"]

    def test_zone_count(self, tmp_path):
        er = _make_export_result(tmp_path, num_slices=4, include_full=True)
        sm = _make_slice_map(4)
        data = generate_preset(er, sm, "test")
        parsed = plistlib.loads(data)
        zones = parsed["Instrument"]["Layers"][0]["Zones"]
        assert len(zones) == 5  # 4 chops + 1 full

    def test_zone_count_no_full(self, tmp_path):
        er = _make_export_result(tmp_path, num_slices=4, include_full=False)
        sm = _make_slice_map(4)
        data = generate_preset(er, sm, "test", include_full_key=False)
        parsed = plistlib.loads(data)
        zones = parsed["Instrument"]["Layers"][0]["Zones"]
        assert len(zones) == 4

    def test_zone_count_with_cues(self, tmp_path):
        er = _make_export_result(tmp_path, num_slices=4, include_full=True, cue_zones=True)
        sm = _make_slice_map(4)
        data = generate_preset(er, sm, "test")
        parsed = plistlib.loads(data)
        zones = parsed["Instrument"]["Layers"][0]["Zones"]
        assert len(zones) == 9  # 1 full + 4 chops + 4 cues

    def test_key_mapping(self, tmp_path):
        er = _make_export_result(tmp_path, num_slices=4, include_full=True)
        sm = _make_slice_map(4)
        chop_root = 60
        data = generate_preset(er, sm, "test", chop_root=chop_root)
        parsed = plistlib.loads(data)
        zones = parsed["Instrument"]["Layers"][0]["Zones"]

        # Full key at chop_root - 1
        assert zones[0]["root key"] == 59
        assert zones[0]["min key"] == 59
        assert zones[0]["max key"] == 59

        # Chop keys at 60, 61, 62, 63
        for i in range(4):
            z = zones[1 + i]
            assert z["root key"] == chop_root + i
            assert z["min key"] == chop_root + i
            assert z["max key"] == chop_root + i

    def test_file_references(self, tmp_path):
        er = _make_export_result(tmp_path, num_slices=3, include_full=True)
        sm = _make_slice_map(3)
        data = generate_preset(er, sm, "test")
        parsed = plistlib.loads(data)

        refs = parsed["file-references"]
        zones = parsed["Instrument"]["Layers"][0]["Zones"]
        assert len(refs) == 4  # 3 chops + 1 full

        # Every zone's waveform ID should have a matching file-reference
        for z in zones:
            ref_key = f"Sample:{z['waveform']}"
            assert ref_key in refs

    def test_boilerplate_completeness(self, tmp_path):
        er = _make_export_result(tmp_path, num_slices=1, include_full=False)
        sm = _make_slice_map(1)
        data = generate_preset(er, sm, "test", include_full_key=False)
        parsed = plistlib.loads(data)
        layer = parsed["Instrument"]["Layers"][0]

        assert "Amplifier" in layer
        assert "Connections" in layer
        assert len(layer["Connections"]) == 9
        assert "Envelopes" in layer
        assert len(layer["Envelopes"]) == 1
        assert len(layer["Envelopes"][0]["Stages"]) == 7
        assert "Filters" in layer
        assert "LFOs" in layer
        assert "Oscillator" in layer
        assert "Zones" in layer

    def test_round_trip(self, tmp_path):
        er = _make_export_result(tmp_path, num_slices=4)
        sm = _make_slice_map(4)
        data = generate_preset(er, sm, "test")
        # Write and re-read
        out = tmp_path / "roundtrip.aupreset"
        out.write_bytes(data)
        parsed = plistlib.loads(out.read_bytes())
        assert parsed["name"] == "test"
        assert len(parsed["Instrument"]["Layers"][0]["Zones"]) == 5
