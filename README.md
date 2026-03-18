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
chopshop-gui
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
  gui/
    waveform.py  # Interactive waveform widget
    window.py    # Main GUI window
tests/
  test_analysis.py
  test_export.py
  test_files.py
  test_preset.py
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
