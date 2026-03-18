"""Generate MIDI files from chopmap + pattern definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mido


PATTERNS_DIR = Path(__file__).parent / "patterns"


def load_chopmap(path: str | Path) -> dict:
    """Load and return a chopmap JSON file."""
    return json.loads(Path(path).read_text())


def load_pattern(source: str) -> dict:
    """Load a pattern from file path or built-in preset name."""
    # Try as file path first
    p = Path(source)
    if p.exists():
        return json.loads(p.read_text())
    # Try as built-in preset
    builtin = PATTERNS_DIR / f"{source}.json"
    if builtin.exists():
        return json.loads(builtin.read_text())
    raise FileNotFoundError(
        f"Pattern not found: {source!r}. "
        f"Not a file path and not a built-in preset. "
        f"Built-in presets: {list_presets()}"
    )


def list_presets() -> list[str]:
    """Return names of built-in pattern presets."""
    return sorted(p.stem for p in PATTERNS_DIR.glob("*.json"))


def build_label_map(chopmap: dict) -> dict[str, int]:
    """Build label -> MIDI note lookup from a chopmap.

    If multiple slices share a label, the first one wins.
    """
    label_to_note: dict[str, int] = {}
    for s in chopmap["slices"]:
        label = s.get("label", "")
        if label and label not in label_to_note:
            label_to_note[label] = s["midi_note"]
    return label_to_note


def generate_midi(
    chopmap: dict,
    pattern: dict,
    bpm: float | None = None,
    bars: int | None = None,
    output: str | Path = "output.mid",
) -> Path:
    """Generate a MIDI file from a chopmap and pattern.

    Args:
        chopmap: Parsed chopmap dict.
        pattern: Parsed pattern dict.
        bpm: Override BPM (defaults to pattern's BPM).
        bars: Override bar count (defaults to pattern's bars).
        output: Output file path.

    Returns:
        Path to the written MIDI file.
    """
    bpm = bpm or pattern.get("bpm", 120)
    bars = bars or pattern.get("bars", 1)
    resolution = pattern.get("resolution", 16)
    time_sig = pattern.get("time_signature", [4, 4])
    beats_per_bar = time_sig[0]

    # Steps per bar at the given resolution
    steps_per_bar = beats_per_bar * (resolution // time_sig[1])
    pattern_steps = steps_per_bar * pattern.get("bars", 1)

    label_map = build_label_map(chopmap)

    # MIDI ticks per beat
    ticks_per_beat = 480
    ticks_per_step = ticks_per_beat * time_sig[1] // resolution

    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)

    # Tempo track
    tempo_track = mido.MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    tempo_track.append(mido.MetaMessage(
        "time_signature",
        numerator=time_sig[0],
        denominator=time_sig[1],
        time=0,
    ))

    # Default note length in ticks (1 step)
    default_note_ticks = ticks_per_step

    warnings = []

    for track_def in pattern.get("tracks", []):
        track = mido.MidiTrack()
        mid.tracks.append(track)

        track_name = track_def.get("name", "drums")
        track.append(mido.MetaMessage("track_name", name=track_name, time=0))

        channel = track_def.get("channel", 9)  # default to drum channel

        # Collect all note events across all bar repetitions
        events = []  # (abs_tick, 'on'|'off', note, velocity)

        steps = track_def.get("steps", [])
        for bar_rep in range(bars):
            bar_offset = bar_rep * pattern_steps
            for step in steps:
                pos = step["pos"]
                actual_pos = (bar_offset + pos) % (steps_per_bar * bars)
                if bar_rep > 0:
                    actual_pos = bar_offset + (pos % pattern_steps)

                label = step["label"]
                velocity = step.get("velocity", 100)

                note = label_map.get(label)
                if note is None:
                    if label not in [w for w in warnings]:
                        warnings.append(label)
                    continue

                tick_on = actual_pos * ticks_per_step
                tick_off = tick_on + default_note_ticks

                events.append((tick_on, "on", note, velocity))
                events.append((tick_off, "off", note, velocity))

        # Sort events by time, with 'off' before 'on' at same tick
        events.sort(key=lambda e: (e[0], 0 if e[1] == "off" else 1))

        # Convert to delta times
        last_tick = 0
        for tick, kind, note, vel in events:
            delta = tick - last_tick
            if kind == "on":
                track.append(mido.Message("note_on", note=note, velocity=vel, time=delta, channel=channel))
            else:
                track.append(mido.Message("note_off", note=note, velocity=0, time=delta, channel=channel))
            last_tick = tick

    if warnings:
        available = sorted(set(s.get("label", "") for s in chopmap.get("slices", []) if s.get("label")))
        print(f"Warning: labels not found in chopmap (skipped): {', '.join(warnings)}", file=sys.stderr)
        print(f"  Available labels in chopmap: {', '.join(available) if available else '(none)'}", file=sys.stderr)
        print(f"  Tip: edit labels in the GUI or re-label slices to match the pattern.", file=sys.stderr)

    out_path = Path(output)
    mid.save(str(out_path))
    return out_path


def main():
    parser = argparse.ArgumentParser(
        prog="chopshop-midi",
        description="Generate MIDI files from ChopShop chopmaps and patterns.",
    )
    parser.add_argument("--map", help="Path to .chopmap.json file")
    parser.add_argument("--pattern", help="Pattern file path or built-in preset name")
    parser.add_argument("--preset", help="Built-in preset name (alias for --pattern)")
    parser.add_argument("--bpm", type=float, help="Override BPM")
    parser.add_argument("--bars", type=int, help="Override number of bars")
    parser.add_argument("--output", "-o", default="output.mid", help="Output MIDI file path")
    parser.add_argument("--list-presets", action="store_true", help="List built-in presets and exit")

    args = parser.parse_args()

    if args.list_presets:
        for name in list_presets():
            p = load_pattern(name)
            desc = p.get("description", "")
            print(f"  {name:20s} {desc}")
        return

    if not args.map:
        parser.error("--map is required (path to .chopmap.json)")

    pattern_source = args.pattern or args.preset
    if not pattern_source:
        parser.error("Either --pattern or --preset is required")

    chopmap = load_chopmap(args.map)
    pattern = load_pattern(pattern_source)

    out_path = generate_midi(
        chopmap=chopmap,
        pattern=pattern,
        bpm=args.bpm,
        bars=args.bars,
        output=args.output,
    )
    print(f"MIDI file written: {out_path}")
    print(f"  BPM: {args.bpm or pattern.get('bpm', 120)}")
    print(f"  Bars: {args.bars or pattern.get('bars', 1)}")
    print(f"  Pattern: {pattern.get('name', pattern_source)}")


if __name__ == "__main__":
    main()
