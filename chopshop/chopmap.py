"""Export a .chopmap.json file alongside the AUSampler preset."""

from __future__ import annotations

import json
from pathlib import Path

from .analysis import SliceMap
from .constants import MIDI_NOTE_NAMES
from .export import ExportResult


def export_chopmap(
    slice_map: SliceMap,
    export_result: ExportResult,
    preset_name: str,
    chop_root: int,
    source_bpm: float | None = None,
) -> Path:
    """Write a chopmap JSON file to the preset directory.

    Returns the path to the written file.
    """
    slices_data = []
    for i, s in enumerate(slice_map.slices):
        midi_note = chop_root + i
        slices_data.append({
            "index": i,
            "midi_note": midi_note,
            "note_name": MIDI_NOTE_NAMES.get(midi_note, str(midi_note)),
            "label": s.label,
            "file": export_result.chop_paths[i].name if i < len(export_result.chop_paths) else "",
            "start_sec": round(s.start_seconds, 4),
            "end_sec": round(s.end_seconds, 4),
            "duration_sec": round(s.end_seconds - s.start_seconds, 4),
        })

    chopmap = {
        "chopmap_version": "1.0",
        "name": preset_name,
        "source_file": slice_map.source_path,
        "source_bpm": source_bpm,
        "detected_bpm": round(slice_map.bpm, 1),
        "num_slices": len(slice_map.slices),
        "base_note": chop_root,
        "base_note_name": MIDI_NOTE_NAMES.get(chop_root, str(chop_root)),
        "slices": slices_data,
    }

    # Write next to the audio files
    out_path = export_result.output_dir / f"{preset_name}.chopmap.json"
    out_path.write_text(json.dumps(chopmap, indent=2) + "\n")
    return out_path
