import plistlib
from pathlib import Path

from .analysis import SliceMap
from .constants import (
    CONNECTIONS_LAYER_0,
    DATA_BLOB,
    DEFAULT_CHOP_ROOT,
    DEFAULT_CUE_ROOT,
    ENVELOPES_DEFAULT,
    FILE_REF_BASE_ID,
    FILTERS_DEFAULT,
    LFOS_DEFAULT,
    MANUFACTURER,
    OSCILLATOR_DEFAULT,
    SUBTYPE,
    TYPE_ID,
    VOICE_COUNT,
)
from .export import ExportResult


def generate_preset(
    export_result: ExportResult,
    slice_map: SliceMap,
    preset_name: str,
    chop_root: int = DEFAULT_CHOP_ROOT,
    cue_root: int = DEFAULT_CUE_ROOT,
    include_full_key: bool = True,
) -> bytes:
    """Generate an AUSampler .aupreset plist.

    Returns the XML bytes ready to write to disk.
    """
    zones = []
    file_refs = {}
    ref_id = FILE_REF_BASE_ID
    zone_id = 0

    # --- Full-file zone (one key below chop range) ---
    if include_full_key and export_result.full_path is not None:
        full_key = chop_root - 1
        file_refs[f"Sample:{ref_id}"] = str(export_result.full_path.resolve())
        zones.append(_make_zone(zone_id, full_key, ref_id))
        ref_id += 1
        zone_id += 1

    # --- Chop zones ---
    for i, chop_path in enumerate(export_result.chop_paths):
        note = chop_root + i
        file_refs[f"Sample:{ref_id}"] = str(chop_path.resolve())
        zones.append(_make_zone(zone_id, note, ref_id))
        ref_id += 1
        zone_id += 1

    # --- Cue zones (opt-in) ---
    for i, cue_path in enumerate(export_result.cue_paths):
        note = cue_root + i
        file_refs[f"Sample:{ref_id}"] = str(cue_path.resolve())
        zones.append(_make_zone(zone_id, note, ref_id))
        ref_id += 1
        zone_id += 1

    # Build the layer
    layer = {
        "Amplifier": {"ID": 0, "enabled": True},
        "Connections": CONNECTIONS_LAYER_0,
        "Envelopes": ENVELOPES_DEFAULT,
        "Filters": FILTERS_DEFAULT,
        "ID": 0,
        "LFOs": LFOS_DEFAULT,
        "Oscillator": OSCILLATOR_DEFAULT,
        "Zones": zones,
    }

    # Build the full preset dict
    preset = {
        "AU version": 1.0,
        "Instrument": {
            "Layers": [layer],
            "name": preset_name,
        },
        "coarse tune": 0,
        "data": DATA_BLOB,
        "file-references": file_refs,
        "fine tune": 0.0,
        "gain": 0.0,
        "manufacturer": MANUFACTURER,
        "name": preset_name,
        "output": 0,
        "pan": 0.0,
        "subtype": SUBTYPE,
        "type": TYPE_ID,
        "version": 0,
        "voice count": VOICE_COUNT,
    }

    return plistlib.dumps(preset, fmt=plistlib.FMT_XML)


def _make_zone(zone_id: int, midi_note: int, waveform_ref: int) -> dict:
    """Create a single AUSampler zone dict."""
    return {
        "ID": zone_id,
        "enabled": True,
        "loop enabled": False,
        "max key": midi_note,
        "min key": midi_note,
        "root key": midi_note,
        "waveform": waveform_ref,
    }
