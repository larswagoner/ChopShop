# ChopShop

Chop audio samples and generate [AUSampler](https://developer.apple.com/documentation/audiotoolbox/ausampler) `.aupreset` files for GarageBand and Logic Pro.

Load a breakbeat, vocal, or melodic loop — ChopShop slices it by transient detection, rhythmic grid, or equal division, exports individual WAVs, and builds a ready-to-play sampler preset with one key per chop.

## Features

- **Three slicing modes**: onset (transient detection), grid (BPM-locked subdivisions), equal (uniform)
- **AUSampler preset generation**: one-click `.aupreset` that loads directly in GarageBand / Logic
- **Cue zones**: optional keys that play from each onset to the end of the file
- **GUI** with interactive waveform, draggable slice markers, and live audio preview
- **CLI** for scripting and batch workflows
- **Fade-out** per chop (linear ramp, configurable in ms)
- **BPM detection** via librosa with manual override

## Install

Requires Python 3.10+.

```bash
# Clone
git clone https://github.com/larswagoner/sample-chopper.git
cd sample-chopper

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# For the GUI
pip install -e ".[gui]"
```

## Usage

### GUI

```bash
# If venv is activated:
chopshop-gui

# Or run directly without activating:
.venv/bin/chopshop-gui
```

Open a WAV, pick your mode and settings, click **Analyze** to see slices on the waveform. Click any slice to preview it. Drag markers to adjust boundaries. Hit **Generate Preset** when you're happy.

### CLI

```bash
# Onset detection (default)
chopshop my_break.wav

# Grid mode at 165 BPM, 16th notes
chopshop my_break.wav --mode grid --bpm 165 --grid-resolution 16th

# Equal division into 8 slices
chopshop my_break.wav --mode equal --num-slices 8

# With fade-out and cue zones
chopshop vocals.wav --mode grid --bpm 124 --grid-resolution 8th --fade-ms 10 --cue-zones

# Preview slices before generating
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

## Output

- **Preset**: `~/Library/Audio/Presets/Apple/AUSampler/<name>.aupreset`
- **Audio**: `~/Library/Audio/Sounds/ChopShop/<name>/`

Open GarageBand, add an **AUSampler** instrument, and load the preset from the browser.

## Project Structure

```
chopshop/
  analysis.py    # Slice detection (onset/grid/equal)
  cli.py         # Command-line interface
  constants.py   # MIDI maps, AUSampler boilerplate, defaults
  export.py      # WAV export with fade-out
  files.py       # File I/O, preset installation
  preset.py      # AUSampler .aupreset generation
  preview.py     # Terminal playback preview
  labeler.py     # Auto-labeler (spectral heuristics)
  chopmap.py     # Chopmap JSON export
  midi_gen.py    # MIDI file generation from chopmaps
  patterns/      # Built-in drum pattern presets (JSON)
  gui/
    waveform.py  # Interactive waveform widget (label pills, click-to-edit)
    window.py    # Main GUI window
tests/
  test_analysis.py
  test_export.py
  test_files.py
  test_preset.py
```

## Version History

ChopShop has been built iteratively, feature by feature. Here's the chronological record of what was added and when.

### v0.1 — Core CLI (foundation)
**Status: stable, well-tested (30 tests passing)**

The original version. Load a WAV file, chop it into slices, export individual WAVs, and generate an AUSampler `.aupreset` for GarageBand.

- Three slicing modes: **onset** (transient/beat detection via librosa), **grid** (BPM-locked subdivisions at 4th/8th/16th/32nd), **equal** (uniform division into N slices)
- BPM auto-detection with manual override
- AUSampler `.aupreset` generation with proper plist XML, indirect file references, and MIDI zone mapping
- Chop zones (one key per slice) and cue zones (each key plays from that onset to end of file)
- Full-file key zone (optional, plays the entire unsliced sample)
- Configurable MIDI root notes for chops and cues
- Fade-out per chop (linear ramp, configurable in ms)
- `--preview` flag to audition slices in the terminal before committing
- `--dry-run` for analysis-only output
- Automatic preset installation to `~/Library/Audio/Presets/Apple/AUSampler/`
- Audio export to `~/Library/Audio/Sounds/ChopShop/<name>/`
- Full test suite: `test_analysis.py` (11 tests), `test_export.py` (7 tests), `test_files.py` (4 tests), `test_preset.py` (8 tests)

### v0.2 — GUI
**Status: stable, well-tested**

A full native desktop GUI built with PySide6.

- Interactive waveform display with QPainter rendering
- Colored alternating slice regions on the waveform
- All CLI options exposed as GUI controls (mode, threshold, BPM, grid resolution, slice count, MIDI roots, fade, cue zones, full key toggle)
- Click any slice on the waveform to preview/audition it
- Play All button with animated playhead tracking
- Preset name text field (auto-fills from filename)
- File info display (duration, sample rate)
- Status bar with operation feedback

### v0.3 — Interactive Slice Editing
**Status: stable, well-tested**

Made the waveform fully interactive — you can now sculpt your chop points by hand.

- **Drag markers**: grab any slice boundary on the waveform and drag to reposition
- **Double-click to add**: double-click anywhere on the waveform to insert a new slice marker
- **Right-click to delete**: right-click a marker to remove it
- Visual marker handles at the top of each boundary line
- Hover highlighting on markers
- SliceMap rebuilds automatically when markers change

### v0.4 — Auto-Labeler & Semantic Slicing *(experimental)*
**Status: experimental — auto-detection is heuristic-based and works as suggestions, not ground truth**

Slice labeling, chopmap export, and MIDI pattern generation. The vision: label your chops semantically (kick, snare, hat, etc.), export a `.chopmap.json`, then generate `.mid` files with drum patterns that use your actual chopped sounds.

- **Auto-labeler** (`chopshop/labeler.py`): classifies each slice using spectral features (centroid, zero-crossing rate, RMS energy, low/high band energy, duration). Uses adaptive file-relative thresholds so it works across different recordings. 12 standard labels: kick, snare, snare_ghost, hat_closed, hat_open, ride, crash, tom_high, tom_mid, tom_low, combo, other
- **Colored label pills** on the waveform — each label has a category color (orange=kick, gold=snare, cyan=hats/cymbals, green=toms, grey=other)
- **Click-to-edit labels**: click any label pill on the waveform to change it via dropdown
- **Slice list panel**: collapsible table below the waveform showing index, start, end, duration, and an editable label combobox per slice
- **Re-label All** button to re-run auto-detection on all slices
- **Chopmap JSON export** (`chopshop/chopmap.py`): saves a `.chopmap.json` alongside the audio files mapping each slice to its MIDI note, label, timing, and filename
- **MIDI generation CLI** (`chopshop-midi`): reads a chopmap + pattern preset, generates a `.mid` file with the drum pattern mapped to your actual chop notes
- **Built-in pattern presets**: `basic-jungle`, `amen-classic`, `halftime`, `roller` — JSON files defining step patterns by label
- **Copy MIDI Command / Copy Chopmap Path** buttons in the export success dialog for easy workflow
- Source BPM field in export settings

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
