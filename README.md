# ChopShop

Chop audio samples and generate [AUSampler](https://developer.apple.com/documentation/audiotoolbox/ausampler) `.aupreset` files for GarageBand and Logic Pro.

Load a breakbeat, vocal, or melodic loop — ChopShop slices it by transient detection, rhythmic grid, or equal division, exports individual WAVs, and builds a ready-to-play sampler preset with one key per chop.

---

## Getting Started

Requires **Python 3.10+** and **macOS** (for GarageBand/AUSampler).

```bash
# Clone
git clone https://github.com/larswagoner/sample-chopper.git
cd sample-chopper

# Create venv and install everything
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[gui]"
```

That's it. You now have four commands available:

| Command | What it is |
|---------|------------|
| `chopshop` | CLI tool — chop audio and generate presets from the terminal |
| `chopshop-gui` | Main GUI — interactive waveform, slice editing, preset generation |
| `chopshop-midi-gui` | MIDI GUI — load a chopmap, pick a pattern, tweak beats, export .mid |
| `chopshop-midi` | MIDI CLI — generate .mid files from the terminal |

> **If your terminal says "command not found"**, you probably haven't activated the venv. Either run `source .venv/bin/activate` first, or use the full path: `.venv/bin/chopshop-gui`

---

## How to Use It (The Short Version)

### 1. Chop your audio

```bash
.venv/bin/chopshop-gui
```

Open a WAV, click **Analyze**, adjust the slice markers if needed, then click **Generate Preset**. This creates:
- A `.aupreset` file (installed to GarageBand's preset folder)
- Individual `.wav` files for each slice
- A `.chopmap.json` file (maps each slice to a label and MIDI note)

### 2. Load in GarageBand

Open GarageBand, create a **Software Instrument** track, open the instrument picker, choose **AUSampler**, and browse presets to find yours. Each slice is mapped to a key starting at C3.

### 3. Generate drum patterns (optional)

```bash
.venv/bin/chopshop-midi-gui
```

Load the `.chopmap.json` from step 1, pick a built-in pattern (amen-classic, basic-jungle, halftime, roller), adjust BPM and bars, then export a `.mid` file. Drag it onto your GarageBand track.

---

## Detailed Guides

- **[GUI Guide](docs/GUI_GUIDE.md)** — Every control in the main GUI explained (technical + plain English)
- **[MIDI Guide](docs/MIDI_GUIDE.md)** — How to use the MIDI pattern generator
- **[Jungle Guide](docs/JUNGLE_GUIDE.md)** — Step-by-step guide to making 90s jungle in GarageBand with ChopShop

---

## CLI Usage

For scripting, batch processing, or if you prefer the terminal:

```bash
# Onset detection (default — finds drum hits automatically)
chopshop my_break.wav

# Grid mode at 165 BPM, 16th notes
chopshop my_break.wav --mode grid --bpm 165 --grid-resolution 16th

# Equal division into 8 slices
chopshop my_break.wav --mode equal --num-slices 8

# With fade-out and cue zones
chopshop vocals.wav --mode grid --bpm 124 --grid-resolution 8th --fade-ms 10 --cue-zones

# Preview slices in terminal before generating
chopshop my_break.wav --preview

# Dry run (analyze only, no files written)
chopshop my_break.wav --dry-run
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--mode` | `onset`, `grid`, or `equal` (default: onset) |
| `--threshold` | Onset sensitivity 0.0-1.0 (default: 0.3) |
| `--bpm` | Set BPM manually (overrides auto-detection) |
| `--grid-resolution` | `4th`, `8th`, `16th`, `32nd` (default: 16th) |
| `--num-slices` | Force exactly N slices (required for equal mode) |
| `--chop-root` | Starting MIDI note for chops (default: C3) |
| `--cue-zones` | Enable cue zones (each key plays onset to EOF) |
| `--cue-root` | Starting MIDI note for cues (default: C1) |
| `--no-full-key` | Omit the full-file zone |
| `--fade-ms` | Fade-out in ms per chop (default: 0) |
| `--preview` | Audition slices in terminal before generating |
| `--dry-run` | Analyze and print info without writing files |
| `--output` | Preset name (default: derived from filename) |
| `--output-dir` | Override preset output directory |
| `--audio-dir` | Override audio export directory |

### MIDI CLI

```bash
# Generate a MIDI pattern from a chopmap
chopshop-midi --map ~/Library/Audio/Sounds/ChopShop/my_break/my_break.chopmap.json \
  --preset amen-classic --bpm 170 --bars 4 -o drums.mid

# List available built-in presets
chopshop-midi --list-presets
```

---

## Where Files Go

| What | Location |
|------|----------|
| Presets | `~/Library/Audio/Presets/Apple/AUSampler/<name>.aupreset` |
| Audio slices | `~/Library/Audio/Sounds/ChopShop/<name>/` |
| Chopmap | `~/Library/Audio/Sounds/ChopShop/<name>/<name>.chopmap.json` |

---

## Project Structure

```
chopshop/
  analysis.py       # Slice detection (onset/grid/equal)
  cli.py            # Command-line interface
  constants.py      # MIDI maps, AUSampler boilerplate, defaults
  export.py         # WAV export with fade-out
  files.py          # File I/O, preset installation
  preset.py         # AUSampler .aupreset generation
  preview.py        # Terminal playback preview
  labeler.py        # Auto-labeler (spectral heuristics)
  chopmap.py        # Chopmap JSON export
  midi_gen.py       # MIDI file generation from chopmaps
  patterns/         # Built-in drum pattern presets (JSON)
    amen-classic.json
    basic-jungle.json
    halftime.json
    roller.json
  gui/
    window.py       # Main GUI window
    waveform.py     # Interactive waveform widget
    midi_window.py  # MIDI pattern generator GUI
    midi_main.py    # MIDI GUI entry point
docs/
  GUI_GUIDE.md      # Main GUI reference
  MIDI_GUIDE.md     # MIDI generator reference
  JUNGLE_GUIDE.md   # Tutorial: jungle production with ChopShop
tests/
  test_analysis.py  # 11 tests
  test_export.py    # 7 tests
  test_files.py     # 4 tests
  test_preset.py    # 8 tests
  test_labeler.py   # Auto-labeler tests
  test_chopmap.py   # Chopmap export tests
  test_midi_gen.py  # MIDI generation tests
```

---

## Version History

ChopShop has been built iteratively. Here's what was added and when.

### v0.1 — Core CLI
**Status: stable, tested (30 unit tests), user-tested**

The foundation. Chop audio into slices, export WAVs, generate `.aupreset` files.

- Three slicing modes: onset (transient detection), grid (BPM-locked), equal (uniform)
- BPM auto-detection with manual override
- AUSampler `.aupreset` generation (plist XML, indirect file references, MIDI zone mapping)
- Chop zones, cue zones, full-file key zone
- Configurable MIDI root notes, fade-out, preview, dry-run
- Automatic preset installation to GarageBand's preset folder

### v0.2 — GUI
**Status: stable, tested, user-tested**

A full native desktop GUI built with PySide6.

- Interactive waveform display with alternating colored slice regions
- All CLI options as GUI controls
- Click any slice to preview it, Play All with animated playhead
- Preset name field, file info display, status bar

### v0.3 — Interactive Slice Editing
**Status: stable, tested, user-tested**

Made the waveform fully interactive.

- Drag markers to reposition slice boundaries
- Double-click to add a new cut point
- Right-click to delete a cut point
- Marker hover highlighting and handles

### v0.4 — Auto-Labeler & Semantic Slicing
**Status: experimental — auto-detection works as suggestions, not ground truth. MIDI patterns are functional but could use more variety. User-tested, partially working.**

Label your chops semantically (kick, snare, hat, etc.), export a `.chopmap.json`, then generate `.mid` files with drum patterns mapped to your actual sounds.

- **Auto-labeler**: spectral heuristic classification (centroid, ZCR, band energy, duration). Adaptive to each file. 12 standard labels
- **Label pills on waveform**: color-coded by category. Click to change via dropdown menu
- **Slice list panel**: collapsible table with editable labels per slice
- **Chopmap JSON export**: semantic map saved alongside audio files
- **MIDI CLI** (`chopshop-midi`): generate .mid files from chopmap + pattern
- **MIDI GUI** (`chopshop-midi-gui`): visual step grid, preview playback, pattern editing, .mid export
- **Built-in patterns**: amen-classic, basic-jungle, halftime, roller
- **Copy buttons**: copy MIDI command or chopmap path from the export dialog

### What's next

- Improve auto-labeler accuracy (hat detection is weak on busy breaks)
- More pattern presets and better pattern variety
- Pattern editor improvements (velocity editing, step length control)
- Time-stretch integration for matching sample BPM to project BPM

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

54 tests, all passing.

## License

MIT
