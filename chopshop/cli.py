import argparse
import sys
from pathlib import Path

import librosa
import numpy as np

from .analysis import SliceMap, analyze
from .constants import (
    DEFAULT_CHOP_ROOT,
    DEFAULT_CUE_ROOT,
    DEFAULT_GRID_RESOLUTION,
    DEFAULT_MODE,
    DEFAULT_THRESHOLD,
    GRID_SUBDIVISIONS,
    MIDI_NOTE_NAMES,
    MIDI_NOTES,
)
from .chopmap import export_chopmap
from .export import export_slices
from .files import install_preset, open_template, resolve_audio_dir
from .labeler import auto_label
from .preset import generate_preset


def parse_note(value: str) -> int:
    """Parse a MIDI note name ('C3') or integer ('60') into a MIDI number."""
    upper = value.upper()
    if upper in MIDI_NOTES:
        return MIDI_NOTES[upper]
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid note: {value!r}. Use a note name (C3, D#1) or MIDI number (60)."
        )


def note_name(midi: int) -> str:
    """Return the note name for a MIDI number, or the number as string."""
    return MIDI_NOTE_NAMES.get(midi, str(midi))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chopshop",
        description="Chop audio and generate AUSampler presets for GarageBand.",
    )
    p.add_argument("input_wav", help="Path to the source WAV file")
    p.add_argument("--output", help="Preset name (default: derived from filename)")
    p.add_argument(
        "--mode", choices=["onset", "grid", "equal"],
        default=DEFAULT_MODE, help="Slicing mode (default: onset)",
    )
    p.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help="Onset sensitivity 0.0-1.0 (default: 0.3, onset mode only)",
    )
    p.add_argument("--num-slices", type=int, help="Force exactly N slices")
    p.add_argument(
        "--grid-resolution", choices=list(GRID_SUBDIVISIONS.keys()),
        default=DEFAULT_GRID_RESOLUTION,
        help="Grid subdivision (default: 16th, grid mode only)",
    )
    p.add_argument("--bpm", type=float, help="Set BPM (overrides auto-detection)")
    p.add_argument("--quantize-bpm", type=float, help="Alias for --bpm")
    p.add_argument("--start", type=float, help="Trim start time (seconds)")
    p.add_argument("--end", type=float, help="Trim end time (seconds)")
    p.add_argument(
        "--chop-root", type=parse_note, default=DEFAULT_CHOP_ROOT,
        help="Starting MIDI note for chops (default: C3)",
    )
    p.add_argument(
        "--cue-zones", action="store_true",
        help="Enable cue zones (each key plays from onset to end of file)",
    )
    p.add_argument(
        "--cue-root", type=parse_note, default=DEFAULT_CUE_ROOT,
        help="Starting MIDI note for cue zones (default: C1, requires --cue-zones)",
    )
    p.add_argument(
        "--no-full-key", action="store_true",
        help="Omit the full-file zone",
    )
    p.add_argument(
        "--fade-ms", type=float, default=0.0,
        help="Fade-out in ms for each chop (default: 0, recommended 5-10 for vocals)",
    )
    p.add_argument("--source-bpm", type=float, help="Original BPM of the source sample (stored in chopmap)")
    p.add_argument("--open-template", help="Path to .band template to open after")
    p.add_argument("--output-dir", help="Override preset output directory")
    p.add_argument("--audio-dir", help="Override audio directory")
    p.add_argument(
        "--preview", action="store_true",
        help="Play back each slice in the terminal before generating preset",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Analyze and print slice info without writing files",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate
    input_path = Path(args.input_wav)
    if not input_path.exists():
        parser.error(f"File not found: {input_path}")

    if args.mode == "equal" and args.num_slices is None:
        parser.error("Equal mode requires --num-slices.")

    # Resolve --bpm and --quantize-bpm (--bpm takes precedence)
    effective_bpm = args.bpm or args.quantize_bpm
    args.quantize_bpm = effective_bpm

    if args.mode == "grid" and effective_bpm is None:
        print("Note: Grid mode with auto-detected BPM. Use --bpm for accuracy.",
              file=sys.stderr)

    source_name = input_path.stem
    preset_name = args.output or source_name

    # Load audio
    print(f"Loading {input_path.name}...")
    y, sr = librosa.load(str(input_path), sr=None, mono=True)

    # Trim
    if args.start is not None:
        y = y[int(args.start * sr) :]
    if args.end is not None:
        end_sample = int(args.end * sr)
        if args.start is not None:
            end_sample -= int(args.start * sr)
        y = y[:end_sample]

    # Analyze
    print(f"Analyzing ({args.mode} mode)...")
    slice_map = analyze(
        y, sr,
        source_path=str(input_path.resolve()),
        mode=args.mode,
        threshold=args.threshold,
        num_slices=args.num_slices,
        quantize_bpm=args.quantize_bpm,
        grid_resolution=args.grid_resolution,
    )

    # Auto-label slices
    labels = auto_label(y, sr, slice_map.slices)
    for i, s in enumerate(slice_map.slices):
        s.label = labels[i] if i < len(labels) else ""

    # Print summary
    if effective_bpm:
        print(f"\nBPM: {effective_bpm:.1f} (user-supplied)")
    else:
        print(f"\nBPM: {slice_map.bpm:.1f} (detected)")
        print(f"  Hint: If this seems wrong (e.g. half-tempo), use --bpm {slice_map.bpm * 2:.0f} or --bpm {slice_map.bpm * 1.5:.0f}")
    print(f"Duration: {slice_map.duration:.3f}s ({slice_map.total_samples} samples @ {sr}Hz)")
    print(f"Slices: {len(slice_map.slices)}")
    print()
    for s in slice_map.slices:
        chop_note = note_name(args.chop_root + s.index)
        dur = s.end_seconds - s.start_seconds
        label_str = f"  [{s.label}]" if s.label else ""
        line = f"  [{s.index:2d}]  {s.start_seconds:.3f}s - {s.end_seconds:.3f}s  ({dur:.3f}s)  -> {chop_note}{label_str}"
        if args.cue_zones:
            cue_note = note_name(args.cue_root + s.index)
            line += f" / {cue_note}"
        print(line)

    if args.preview:
        from .preview import preview_slices
        if not preview_slices(y, sr, slice_map, args.chop_root):
            print("\nAborted.")
            return

    if args.dry_run:
        print("\n--dry-run: No files written.")
        return

    # Export slices
    audio_dir = resolve_audio_dir(source_name, args.audio_dir)
    print(f"\nExporting slices to {audio_dir}...")
    export_result = export_slices(
        y, sr, slice_map, audio_dir, source_name,
        fade_ms=args.fade_ms,
        cue_zones=args.cue_zones,
        include_full=not args.no_full_key,
    )

    # Generate and install preset
    print("Generating preset...")
    preset_bytes = generate_preset(
        export_result, slice_map, preset_name,
        chop_root=args.chop_root,
        cue_root=args.cue_root,
        include_full_key=not args.no_full_key,
    )
    preset_path = install_preset(preset_bytes, preset_name, args.output_dir)

    # Export chopmap
    chopmap_path = export_chopmap(
        slice_map, export_result, preset_name,
        chop_root=args.chop_root,
        source_bpm=args.source_bpm,
    )

    # Summary
    total_zones = len(export_result.chop_paths) + len(export_result.cue_paths)
    if not args.no_full_key and export_result.full_path:
        total_zones += 1
    print(f"\nPreset written: {preset_path}")
    print(f"Chopmap written: {chopmap_path}")
    print(f"Audio directory: {audio_dir}")
    print(f"Zones: {total_zones} ({len(export_result.chop_paths)} chops", end="")
    if export_result.cue_paths:
        print(f" + {len(export_result.cue_paths)} cues", end="")
    if export_result.full_path:
        print(" + 1 full", end="")
    print(")")

    chop_start = note_name(args.chop_root)
    chop_end = note_name(args.chop_root + len(slice_map.slices) - 1)
    print(f"Chop keys: {chop_start} - {chop_end}")
    if args.cue_zones:
        cue_start = note_name(args.cue_root)
        cue_end = note_name(args.cue_root + len(slice_map.slices) - 1)
        print(f"Cue keys:  {cue_start} - {cue_end}")
    if not args.no_full_key:
        print(f"Full key:  {note_name(args.chop_root - 1)}")

    if args.open_template:
        open_template(args.open_template)


if __name__ == "__main__":
    main()
