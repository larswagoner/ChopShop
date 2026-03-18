# ChopShop — Implementation Plan

A command-line tool that chops audio — breakbeats, vocal phrases, melodic loops, anything — and generates ready-to-play AUSampler presets for GarageBand. Supports transient-based slicing for drums and beat-grid slicing for vocals and melodic material. Written in Python. No paid dependencies.


---

## Architecture Overview

The tool is a single Python package called `chopshop` with four internal modules and one CLI entry point. Each module handles one concern and exposes a clean interface to the next.

```
CLI (chopshop/cli.py)
 |
 v
Audio Analysis (chopshop/analysis.py)
 |   - Reads WAV files
 |   - Detects BPM
 |   - Finds onsets/transients (onset mode)
 |   - Slices on beat grid (grid mode)
 |   - Slices into equal segments (equal mode)
 |   - Detects loop repetition
 |   - Returns a SliceMap dataclass
 |
 v
Preset Builder (chopshop/preset.py)
 |   - Takes a SliceMap and config
 |   - Generates AUSampler XML (.aupreset)
 |   - Handles zone mapping, one-shot config, velocity
 |   - Writes to the correct macOS directory
 |
 v
File Manager (chopshop/files.py)
 |   - Copies WAV to canonical audio directory
 |   - Resolves paths for preset installation
 |   - Opens GarageBand template on completion
 |
 v
Preview (chopshop/preview.py)
     - Plays back slices in terminal for audition
     - Prints slice info alongside playback
```

### Core Data Structure

Everything flows through one central dataclass that the analysis module produces and other modules consume:

```python
@dataclass
class SliceMap:
    source_path: str              # absolute path to source WAV
    sample_rate: int              # e.g. 44100
    bpm: float                    # detected or user-supplied BPM
    duration: float               # total duration in seconds
    total_samples: int            # total number of samples in the (trimmed) audio
    mode: str                     # "onset", "grid", or "equal"
    slices: list[Slice]           # ordered list of slice points
    loop_bars: int | None         # detected loop length, if any
    loop_confidence: float | None # 0.0-1.0 autocorrelation score

@dataclass
class Slice:
    index: int           # 0-based slice number
    start_sample: int    # sample offset into the WAV (integer)
    end_sample: int      # sample offset for end (next onset, or EOF)
    start_seconds: float # same as above but in seconds, for readability
    end_seconds: float
```

All downstream modules operate on this structure. The preset builder reads start/end samples to set zone boundaries. The preview module reads them to extract and play audio segments. This means the analysis module is the single source of truth and nothing else touches librosa or audio math directly.

### File Layout

```
chopshop/
    __init__.py
    cli.py          # argparse entry point
    analysis.py     # audio analysis, onset detection, loop detection
    preset.py       # .aupreset XML generation
    files.py        # path management, file copying, GarageBand launch
    preview.py      # terminal playback
    constants.py    # MIDI note names, default paths, magic numbers
setup.py or pyproject.toml
tests/
    test_analysis.py
    test_preset.py
    test_files.py
    fixtures/
        amen_break.wav   # short test WAV (use a public domain break)
        vocal_phrase.wav  # short vocal sample for grid mode testing
```

### Key Architectural Decisions

**Three slicing modes, one output format.** The analysis module supports onset detection (drums), beat-grid slicing (vocals/melodic), and equal division (fallback). All three produce the same SliceMap dataclass. Everything downstream — preset generation, preview, file management — is mode-agnostic. This means adding a new slicing algorithm later is just a new code path in analysis.py with zero changes elsewhere.

**Single WAV reference, not destructive slicing.** The .aupreset file points every zone at the same source WAV with different start/end sample offsets. No audio is duplicated or re-exported. This is simpler, faster, and uses less disk space. The only file operation is copying the source WAV once to a stable location.

**Two-octave mapping scheme.** Lower octave (default C1 up): cue point zones, where each key plays from its onset to the end of the file. Upper octave (default C3 up): isolated chop zones, where each key plays from its onset to the next onset only. Both ranges are in the same preset, same instrument.

**The CLI is thin.** It parses arguments, calls analysis, passes the SliceMap to preset and files, optionally calls preview. No logic lives in the CLI module. This makes every component independently testable.

**No GarageBand project manipulation.** The tool generates standard .aupreset files and installs them to the right directory. It does not attempt to reverse-engineer or write .band files. The user creates a template project once by hand.


---

## Dependencies

All installed via pip. No compiled extensions required beyond what ships with macOS.

```
librosa>=0.10.0       # audio analysis: onset detection, BPM, beat tracking
soundfile>=0.12.0     # WAV reading/writing (used by librosa internally too)
numpy>=1.24.0         # numerical operations (librosa dependency, but pin it)
sounddevice>=0.4.6    # audio playback for preview mode
```

Install command for the plan:
```
pip install librosa soundfile numpy sounddevice --break-system-packages
```

Standard library modules used: `xml.etree.ElementTree`, `argparse`, `dataclasses`, `pathlib`, `subprocess`, `shutil`.


---

## Phase 1 — Audio Analysis Engine

**Goal:** Given a WAV file path and a slicing mode, produce a correct SliceMap. Supports three modes: onset detection for percussive material, beat-grid slicing for vocals and melodic content, and equal-division slicing as a simple fallback.

### Components

**chopshop/analysis.py**

Function: `analyze(path, mode, threshold, num_slices, quantize_bpm, grid_resolution, start, end) -> SliceMap`

Parameters and their behavior:

- `path` (str): Path to a WAV file. The function should load it as mono, at its native sample rate. Use `librosa.load(path, sr=None, mono=True)`. Preserving native sample rate is critical because AUSampler zone boundaries are defined in sample offsets — if we resample, the preset will point to wrong positions.

- `mode` (str, default "onset"): Determines how slice points are found. Three options:

  **"onset"** — Transient detection. Best for drums, percussion, and any audio with sharp attacks. Uses librosa's onset detection (described below). This is the default and the right choice for breakbeats.

  **"grid"** — Beat-grid slicing. Best for vocals, melodic loops, pads, and any sustained audio where transients are soft or absent. Ignores the audio content entirely and places slice points at regular rhythmic intervals determined by the `grid_resolution` parameter. Requires knowing the BPM — either auto-detected or supplied via `--quantize-bpm`. This is the mode for house vocal chops: take a sung phrase, slice it on every 8th note or 16th note, then play the fragments on keys to rearrange them rhythmically.

  **"equal"** — Equal division. Divides the audio into `num_slices` segments of equal length. No BPM or onset analysis needed. Useful as a quick-and-dirty fallback when you just want to break something into pieces and see what's in there.

- `grid_resolution` (str, default "16th"): Only used in grid mode. Determines the rhythmic interval between slice points. Accepted values: "4th", "8th", "16th", "32nd". The function calculates the interval in seconds as: for 4th notes, `60.0 / bpm`; for 8th notes, `60.0 / bpm / 2`; for 16th notes, `60.0 / bpm / 4`; for 32nd notes, `60.0 / bpm / 8`. Each interval becomes a slice point. For a typical 4-bar vocal phrase at 124 BPM, grid mode at 16th-note resolution produces 64 slices. At 8th-note resolution, 32 slices. The user picks the granularity that suits their rearrangement style — 8th notes give bigger, more recognizable syllable chunks; 16th notes give the rapid stutter-chop effect.

- `threshold` (float, default 0.3): Only used in onset mode. Passed to librosa's onset detection as the `delta` parameter in `librosa.onset.onset_detect()`. Higher values mean fewer, stronger onsets. Range is roughly 0.0 to 1.0 but not hard-bounded. This is the primary "sensitivity" control.

- `num_slices` (int or None, default None): Behavior depends on mode. In onset mode: detects all onsets, ranks them by onset strength, keeps only the top N. Use `librosa.onset.onset_strength()` to get the strength envelope, then sample it at each detected onset frame to rank them. After selecting the top N, re-sort by time position so slices remain in chronological order. In equal mode: required — divides the audio into exactly N equal segments. In grid mode: ignored (slice count is determined by BPM and grid resolution).

- `quantize_bpm` (float or None, default None): If provided in onset mode, after detecting onsets, snap each onset to the nearest grid position at the given BPM (using the grid_resolution interval). Calculate the interval as described above. For each onset, find the nearest grid line and move the onset there. This corrects for loose drumming. The first onset should snap to 0.0 (the downbeat). In grid mode, if provided, this value is used as the BPM instead of auto-detection. In equal mode, ignored.

- `start` (float or None): If provided, trim the audio to begin at this timestamp in seconds before analysis. Use array slicing on the loaded samples: `y = y[int(start * sr):]`. Adjust all subsequent onset times to be relative to the trimmed audio.

- `end` (float or None): If provided, trim the audio to end at this timestamp. `y = y[:int(end * sr)]`.

BPM detection: Use `librosa.beat.beat_track(y=y, sr=sr)` which returns both estimated BPM and beat frame positions. Store the BPM in the SliceMap. If the user passes `--quantize-bpm`, use their value instead for grid snapping (onset mode) or grid interval calculation (grid mode), but still report the detected BPM.

### Mode-specific slicing logic

**Onset mode** (default — for drums and percussive material):

Call `librosa.onset.onset_detect(y=y, sr=sr, delta=threshold, units='samples')` to get onset positions in sample indices. The `units='samples'` is important — we need sample-level precision for AUSampler zones. Also call with `units='time'` or convert manually for the seconds field in the Slice dataclass. If num_slices is provided, rank onsets by strength and keep only the top N (re-sorted chronologically).

**Grid mode** (for vocals, melodic material, sustained audio):

Calculate the interval between slice points based on BPM and grid_resolution. Use the detected BPM or the user-supplied value via --quantize-bpm. The interval in seconds: `60.0 / bpm / subdivisions` where subdivisions is 1 for 4th notes, 2 for 8th, 4 for 16th, 8 for 32nd. Convert to samples: `interval_samples = int(interval_seconds * sr)`. Generate slice points at every interval from 0 to the end of the file. This produces perfectly even, rhythmically meaningful slices regardless of the audio content. No onset detection is run — the grid is purely mathematical.

**Equal mode** (quick-and-dirty uniform division):

Requires num_slices to be set. Calculate `segment_length = total_samples // num_slices`. Place slice points at `0, segment_length, 2*segment_length, ...`. No BPM detection or onset analysis needed — though BPM is still detected and stored in the SliceMap for informational purposes.

### Building the Slice list (all modes)

The output is the same regardless of mode. For each slice point i, create a Slice where `start_sample` is the slice position and `end_sample` is the position of slice i+1. For the last slice, `end_sample` is the total number of samples in the file. Index is just the position in the list. The `mode` field on the SliceMap records which method was used.

**chopshop/constants.py**

Define MIDI note names and numbers. AUSampler uses MIDI note numbers (0-127) where middle C (C3) is 60. Define a list:

```python
MIDI_NOTES = {
    "C1": 36, "C#1": 37, "D1": 38, ...
    "C3": 60, "C#3": 61, "D3": 62, ...
}
```

Also define:
```python
DEFAULT_MODE = "onset"
DEFAULT_THRESHOLD = 0.3
DEFAULT_GRID_RESOLUTION = "16th"
GRID_SUBDIVISIONS = {"4th": 1, "8th": 2, "16th": 4, "32nd": 8}
DEFAULT_CUE_ROOT = 36        # C1
DEFAULT_CHOP_ROOT = 60       # C3
MAX_SLICES = 64              # safety limit (increased for grid mode)
PRESET_DIR = "~/Library/Audio/Presets/Apple/AUSampler/"
AUDIO_DIR = "~/Library/Audio/Sounds/ChopShop/"
```

### Testing Phase 1

Create `tests/test_analysis.py`. Use a known WAV file as a fixture.

**Onset mode tests:**

Test 1 — Basic onset detection: Analyze a WAV file with known, obvious transients (the Amen Break is ideal — it has well-documented hit positions). Assert that the SliceMap has a reasonable number of slices (between 4 and 32). Assert that all slice start_sample values are non-negative and strictly increasing. Assert that the last slice's end_sample equals the total sample count of the file. Assert that slice_map.mode equals "onset".

Test 2 — Threshold sensitivity: Analyze the same file with threshold=0.1 (sensitive) and threshold=0.8 (aggressive). Assert that the low-threshold run produces more slices than the high-threshold run.

Test 3 — num_slices override: Analyze with num_slices=4. Assert exactly 4 slices are returned. Assert they are still in chronological order (start times increasing).

Test 4 — Quantization: Analyze with a known BPM and quantize_bpm set. For each slice, compute the distance from start_seconds to the nearest 16th-note grid line. Assert all distances are less than 1 millisecond.

**Grid mode tests:**

Test 5 — Grid slicing at 16th notes: Create or use a test WAV at a known BPM (say 120 BPM). Analyze with mode="grid", grid_resolution="16th". At 120 BPM, a 16th note is 0.125 seconds. For a 4-second file, this should produce 32 slices. Assert slice count equals the expected value. Assert all slices have equal duration (within 1 sample tolerance from integer rounding). Assert that slice_map.mode equals "grid".

Test 6 — Grid slicing at 8th notes: Same file, mode="grid", grid_resolution="8th". Assert exactly half as many slices as the 16th-note test.

Test 7 — Grid with explicit BPM: Analyze with mode="grid" and quantize_bpm=130.0. Assert the slice intervals correspond to 130 BPM, not the auto-detected BPM.

**Equal mode tests:**

Test 8 — Equal division: Analyze with mode="equal", num_slices=8. Assert exactly 8 slices. Assert all slices have equal duration (within 1 sample tolerance). Assert that slice_map.mode equals "equal".

Test 9 — Equal mode requires num_slices: Analyze with mode="equal" and no num_slices. Assert that the function raises a ValueError or similar clear error.

**General tests (apply to all modes):**

Test 10 — Start/end trimming: Analyze with start=1.0 and end=3.0. Assert that the total duration in the SliceMap is approximately 2.0 seconds. Assert that no slice start_seconds exceeds 2.0.

Test 11 — BPM detection: Assert that detected BPM is within a plausible range for the test file. For the Amen Break at normal speed, this is roughly 130-140 BPM.

Test 12 — Mode field consistency: For each mode, verify that the SliceMap.mode field matches the mode that was requested.

All tests should run without GarageBand or any GUI. They are pure computation tests.


---

## Phase 2 — Preset Generation

**Goal:** Given a SliceMap, produce a valid .aupreset XML file that AUSampler can load.

### AUSampler Preset Format

An .aupreset file is XML with the following structure. This was determined by creating presets manually in AUSampler, saving them, and inspecting the XML. The key elements are:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Instrument</key>
    <dict>
        <key>Layers</key>
        <array>
            <dict>
                <key>Zones</key>
                <array>
                    <!-- One dict per zone (per mapped key) -->
                    <dict>
                        <key>enabled</key> <true/>
                        <key>loop enabled</key> <false/>
                        <key>trigger mode</key> <integer>0</integer>
                            <!-- 0 = normal, 11 = one-shot -->
                        <key>min key</key> <integer>36</integer>
                        <key>max key</key> <integer>36</integer>
                        <key>root key</key> <integer>36</integer>
                        <key>min vel</key> <integer>0</integer>
                        <key>max vel</key> <integer>127</integer>
                        <key>sample offset</key> <integer>0</integer>
                        <key>sample length</key> <integer>44100</integer>
                            <!-- length in samples from offset -->
                        <key>waveform</key>
                        <string>/path/to/audio.wav</string>
                    </dict>
                </array>
            </dict>
        </array>
    </dict>
</dict>
</plist>
```

CRITICAL IMPLEMENTATION NOTE: The exact key names and structure above are approximate. Before writing the preset builder, the developer MUST do the following verification step:

1. Open GarageBand, create a Software Instrument track with AUSampler.
2. Load any sample into a zone manually via the Layers/Zones panel.
3. Set it to one-shot mode if possible from the GUI.
4. Save the preset (File > Save Preset, or from the AUSampler preset dropdown).
5. Find the saved .aupreset file in ~/Library/Audio/Presets/Apple/AUSampler/.
6. Open it in a text editor and study the actual XML structure.
7. Use that exact structure as the template, not the approximation above.

This verification is essential because Apple's key names and nesting may differ from documentation. The approximation above is a starting point, but the real file is the authority.

### Components

**chopshop/preset.py**

Function: `generate_preset(slice_map, audio_dest_path, preset_name, cue_root, chop_root, fade_ms) -> str`

Returns the XML string. Parameters:

- `slice_map` (SliceMap): The analysis output.
- `audio_dest_path` (str): The absolute path where the WAV will be installed (from the files module). All zones reference this path.
- `preset_name` (str): Used for the file name.
- `cue_root` (int, default 36 / C1): MIDI note number where cue-point zones start mapping.
- `chop_root` (int, default 60 / C3): MIDI note number where isolated chop zones start mapping.
- `fade_ms` (float, default 0.0): If > 0, reduce each isolated chop's end_sample by this many milliseconds worth of samples, then apply a note that the preset should use a small release. In practice, AUSampler zone end points handle this — trim end_sample slightly. A value of 5-10ms prevents clicks. 0 means raw cuts.

Logic:

For each slice in slice_map.slices, create TWO zones:

Zone type A — Cue point:
- min key = max key = root key = cue_root + slice.index
- sample offset = slice.start_sample
- sample length = (total file samples) - slice.start_sample
- trigger mode = one-shot (value TBD from verification step above)
- loop enabled = false

Zone type B — Isolated chop:
- min key = max key = root key = chop_root + slice.index
- sample offset = slice.start_sample
- sample length = slice.end_sample - slice.start_sample (minus fade if applicable)
- trigger mode = one-shot
- loop enabled = false

All zones:
- min vel = 0, max vel = 127 (full velocity range)
- waveform = audio_dest_path

Build the XML tree using `xml.etree.ElementTree`. Use the plist dict/array structure that Apple expects. Write with `ET.tostring()` using `xml_declaration=True` and `encoding='UTF-8'`.

Function: `write_preset(xml_string, preset_name, output_dir) -> Path`

Writes the XML to `{output_dir}/{preset_name}.aupreset`. Returns the path written. If output_dir is None, use the default PRESET_DIR from constants (expanded with Path.expanduser).

### Testing Phase 2

Test 1 — Valid XML: Generate a preset from a known SliceMap (can be manually constructed, no audio needed). Parse the output with ElementTree. Assert it parses without error. Assert the root element structure matches the expected plist format.

Test 2 — Correct zone count: For a SliceMap with N slices, assert the preset contains exactly 2*N zones.

Test 3 — Zone key mapping: Assert that cue zones are mapped to consecutive MIDI notes starting from cue_root. Assert chop zones start from chop_root. Assert no two zones share the same MIDI key.

Test 4 — Cue zone lengths: For each cue zone, assert that sample offset + sample length equals the total file length in samples.

Test 5 — Chop zone boundaries: For each chop zone i, assert sample offset equals slice i's start_sample. Assert sample length equals the distance between slice i and slice i+1 (or end of file for the last slice).

Test 6 — One-shot mode: Assert every zone has trigger mode set to the one-shot value.

Test 7 — Real-world validation: Generate a preset, place it in the AUSampler preset directory, open GarageBand, load it. This is a manual test but should be documented as a gate before moving to Phase 3. Verify: every key in both octave ranges produces sound, cue keys play to the end of the file, chop keys play only their segment.


---

## Phase 3 — File Management and CLI

**Goal:** Wire everything together into a working command-line tool with correct file placement.

### Components

**chopshop/files.py**

Function: `install_audio(source_path, audio_dir) -> Path`

Copies the source WAV to the canonical audio directory. If audio_dir is None, use AUDIO_DIR from constants. Creates the directory if it doesn't exist. Returns the absolute destination path. If a file with the same name already exists, append a numeric suffix rather than overwriting (so you can have multiple versions of the same break).

Function: `install_preset(xml_string, preset_name, preset_dir) -> Path`

Writes the preset XML to the preset directory. Same defaulting and creation behavior as above.

Function: `open_template(template_path)`

Calls `subprocess.run(['open', template_path])` to launch GarageBand with the user's template project. Only called if the user passes `--open-template` with a path.

**chopshop/cli.py**

Entry point. Uses argparse. Full argument list:

```
chopshop <input_wav> [options]

Positional arguments:
  input_wav                Path to the source WAV file

Options:
  --output NAME            Preset name (default: derived from input filename)
  --mode MODE              Slicing mode: "onset", "grid", or "equal" (default: onset)
  --threshold FLOAT        Onset sensitivity, 0.0-1.0 (default: 0.3, onset mode only)
  --num-slices INT         Force exactly N slices (onset: strongest N; equal: required)
  --grid-resolution RES    Grid subdivision: "4th", "8th", "16th", "32nd" (default: 16th, grid mode only)
  --quantize-bpm FLOAT     Snap to grid at this BPM (onset mode) or set BPM (grid mode)
  --start FLOAT            Start time in seconds (trim before analysis)
  --end FLOAT              End time in seconds (trim before analysis)
  --cue-root NOTE          Starting MIDI note for cue zones (default: C1)
  --chop-root NOTE         Starting MIDI note for chop zones (default: C3)
  --fade-ms FLOAT          Fade-out in ms for isolated chops (default: 0, recommended 5-10 for vocals)
  --preview                Play back each slice before generating preset
  --open-template PATH     Open a .band template after generation
  --output-dir PATH        Override preset output directory
  --audio-dir PATH         Override audio installation directory
  --dry-run                Analyze and print slice info without writing files
```

The --cue-root and --chop-root flags accept either note names ("C1") or MIDI numbers (36). The CLI should parse both formats.

CLI flow:
1. Parse arguments.
2. Validate mode-specific constraints: if mode is "equal", require --num-slices. If mode is "grid" and no --quantize-bpm, BPM will be auto-detected (warn the user to verify). If mode is "onset", --grid-resolution is ignored.
3. Call `analysis.analyze()` with the relevant parameters.
4. Print a summary: mode used, detected BPM, number of slices, slice timestamps.
5. If `--preview`, call preview (Phase 4). User can abort after preview.
6. If `--dry-run`, stop here.
7. Call `files.install_audio()` to copy the WAV.
8. Call `preset.generate_preset()` with the SliceMap and installed audio path.
9. Call `files.install_preset()` to write the .aupreset.
10. Print confirmation: paths written, how many zones, which keys are mapped.
11. If `--open-template`, call `files.open_template()`.

**setup.py or pyproject.toml**

Configure the package so that `pip install -e .` makes the `chopshop` command available. Use a console_scripts entry point:

```toml
[project.scripts]
chopshop = "chopshop.cli:main"
```

### Testing Phase 3

Test 1 — File installation: Call install_audio with a test WAV. Assert the file exists at the destination. Assert it's a byte-for-byte copy (compare checksums). Call it again with the same file — assert a new file is created with a numeric suffix, not an overwrite.

Test 2 — Preset installation: Call install_preset with a test XML string. Assert the file exists and contains the expected content.

Test 3 — CLI dry run: Run the CLI with `--dry-run` on a test file. Capture stdout. Assert it prints mode, BPM, slice count, and timestamps. Assert no files are written to the preset or audio directories.

Test 4 — CLI end-to-end (onset): Run the CLI on a test file with default settings. Assert a .aupreset file appears in the preset directory. Assert a WAV file appears in the audio directory. Open the preset XML and verify it references the correct audio path.

Test 5 — CLI end-to-end (grid): Run the CLI with `--mode grid --quantize-bpm 120` on a test file. Assert the preset is generated. Assert the number of zones corresponds to the expected grid slice count at that BPM and resolution.

Test 6 — CLI end-to-end (equal): Run the CLI with `--mode equal --num-slices 8`. Assert the preset is generated with 16 zones (8 cue + 8 chop).

Test 7 — CLI validation: Run with `--mode equal` and no `--num-slices`. Assert the CLI exits with an error message explaining that equal mode requires --num-slices.

Test 8 — Note name parsing: Assert that "C1" parses to 36, "C#3" parses to 61, and that bare integers pass through unchanged.

Test 9 — Manual GarageBand test: Run the CLI on a real break (onset mode) and a vocal phrase (grid mode). Open GarageBand, load each preset, play keys. Document expected behavior at each key. This is the go/no-go gate for Phase 3.


---

## Phase 4 — Preview Playback

**Goal:** Add terminal-based audition so the user can hear slices before committing to a preset.

### Components

**chopshop/preview.py**

Function: `preview_slices(slice_map, audio_path, mode)`

Parameters:
- `slice_map`: The analysis result.
- `audio_path`: Path to the WAV (the original, not the installed copy).
- `mode`: "chop" (play isolated hits) or "cue" (play from onset to end). Default "chop".

Behavior:

Load the full audio with `soundfile.read()`. For each slice, extract the relevant sample range (chop mode: start to end of this slice; cue mode: start to end of file). Print the slice info, then play the audio using `sounddevice.play()` and `sounddevice.wait()`. Pause briefly between slices.

Output format per slice:
```
[3/16]  Key: D#1 / D#3  |  Start: 0.882s  |  Duration: 0.221s
        Playing...
```

After all slices play, prompt: "Generate preset? [Y/n]" — returning a boolean to the CLI.

### Testing Phase 4

Test 1 — Slice extraction: Without playing audio, verify that the sample arrays extracted for each slice have the correct length (end_sample - start_sample for chops, total_samples - start_sample for cues).

Test 2 — Manual listen: Run preview on a known break. Verify each slice sounds like a distinct drum hit. Verify cue-mode slices start at different points but all play to the end.

Playback tests are inherently manual/auditory but the extraction logic can be unit tested.


---

## Phase 5 — Loop Detection

**Goal:** Automatically detect when a break is a repeating pattern and trim to one cycle.

### Components

Add to **chopshop/analysis.py**:

Function: `detect_loop(y, sr, bpm) -> tuple[int | None, float | None]`

Returns `(loop_length_in_bars, confidence_score)` or `(None, None)` if no loop detected.

Algorithm:

1. Use the detected BPM to calculate one bar length in samples: `bar_samples = int(60.0 / bpm * 4 * sr)` (assuming 4/4 time).

2. For candidate loop lengths of 1, 2, and 4 bars:
   a. Extract the first N bars of audio.
   b. Extract the next N bars.
   c. Compute normalized cross-correlation between the two segments using `numpy.correlate` or `scipy.signal.correlate`.
   d. The peak correlation value (divided by the autocorrelation at zero lag for normalization) gives a similarity score from 0 to 1.

3. If any candidate exceeds a confidence threshold (default 0.85), report it as a detected loop. Prefer shorter loop lengths if multiple candidates pass (a 1-bar loop that repeats is more useful than detecting a 4-bar repetition).

Integration with `analyze()`:

Add a `--loop-detect` flag. When enabled, after initial onset detection, run `detect_loop()`. If a loop is found with high confidence, trim the audio and re-run onset detection on just the first loop cycle. Set `slice_map.loop_bars` and `slice_map.loop_confidence`. Print a message: "Detected 2-bar loop (confidence: 0.93) — trimming to one cycle."

Add a `--bars N` flag that overrides loop detection and forces trimming to exactly N bars from the start, using the detected BPM to calculate bar length.

### Testing Phase 5

Test 1 — Known loop: Create a test fixture by concatenating a short audio segment with itself 4 times. Run loop detection. Assert it detects a loop with confidence > 0.9. Assert loop_bars equals 1.

Test 2 — No loop: Use a test file with non-repeating audio (speech, or a drum fill that varies). Assert that no loop is detected (confidence below threshold or returns None).

Test 3 — Bars override: Run with `--bars 2` on a 4-bar file. Assert the resulting SliceMap duration is approximately 2 bars long.

Test 4 — Integration: Run with `--loop-detect` on the concatenated fixture. Assert the SliceMap only contains slices within one loop cycle.


---

## Phase 6 — Reverse Slices and Frequency Labeling

**Goal:** Add creative production features — reversed hits and basic spectral classification.

### Components

**Reverse zones** — Add to preset.py:

When a `--reverse` flag is passed, generate a THIRD octave range of zones. For reversed audio, the simplest approach is to create reversed copies of each chop as separate small WAV files (since AUSampler doesn't have a "play backwards" zone flag). Store them alongside the main WAV in the audio directory, named like `breakname_rev_00.wav`, `breakname_rev_01.wav`, etc.

Add to analysis.py or a new utility:

Function: `export_reversed_chops(y, sr, slice_map, output_dir) -> list[Path]`

For each slice, extract the samples, reverse the array with `numpy.flip()`, write as a WAV with soundfile. Return the list of paths. The preset builder then creates additional zones pointing at these individual files.

Reverse zone mapping starts at a third root note, default C5 (MIDI 84).

**Frequency labeling** — Add to analysis.py:

Function: `classify_slice(y_slice, sr) -> str`

Takes the audio samples for one slice and returns a label: "kick", "snare", "hat", or "other".

Algorithm: Compute the spectral centroid of the slice using `librosa.feature.spectral_centroid()`. This gives a single number representing the "center of mass" of the frequency spectrum.

- Spectral centroid below ~500 Hz: likely a kick drum.
- Between ~500 Hz and ~3000 Hz: likely a snare.
- Above ~3000 Hz: likely a hi-hat or cymbal.
- If the slice is long (>200ms) and has broad spectrum: likely "other" (a complex hit or combination).

These thresholds are approximate and should be tunable. The labels are informational — printed during analysis and preview, not used for zone mapping. They help the user understand what's on each key.

Print format:
```
Slice  0: 0.000s - 0.221s  [kick]    -> C1 / C3
Slice  1: 0.221s - 0.442s  [hat]     -> C#1 / C#3
Slice  2: 0.442s - 0.663s  [snare]   -> D1 / D3
```

### Testing Phase 6

Test 1 — Reversed audio: Export a reversed chop. Load both original and reversed WAVs. Assert they have the same length. Assert the reversed version's first sample equals the original's last sample.

Test 2 — Classification sanity: Create or obtain isolated kick, snare, and hi-hat samples. Run classify_slice on each. Assert correct labels. These won't be 100% accurate on ambiguous sounds, but clear cases should classify correctly.

Test 3 — Reverse preset zones: Generate a preset with --reverse. Assert it contains 3*N zones. Assert the third octave zones reference the reversed WAV files. Manual GarageBand test: play the reverse keys and verify they sound backwards.


---

## Summary of All CLI Flags by Phase

Phase 1: --mode, --threshold, --num-slices, --quantize-bpm, --grid-resolution, --start, --end
Phase 2: --cue-root, --chop-root, --fade-ms
Phase 3: --output, --output-dir, --audio-dir, --open-template, --dry-run
Phase 4: --preview
Phase 5: --loop-detect, --bars
Phase 6: --reverse


---

## Notes for the Developer

On the .aupreset format: Do not trust the XML structure described in this document as gospel. The first task in Phase 2, before writing any code, is to create a reference preset by hand in GarageBand and inspect its XML. The field names, nesting, and value types must come from that reference file. Save the reference preset in the repo as `reference/manual_preset.aupreset` for future comparison.

On sample rates: Never resample audio. Load at native sample rate, report it, and let AUSampler handle playback. If a user loads a 48kHz file, everything should still work because zone boundaries are in sample counts, not seconds.

On the Amen Break: A clean, public-domain Amen Break WAV is widely available and is the ideal primary test fixture. It's the canonical jungle breakbeat, it has well-known structure (roughly 4 bars at ~136 BPM, 16 main hits), and the user is specifically working with it.

On error handling: Every phase should validate inputs early. If the WAV is stereo, convert to mono silently (sum and normalize). If the file isn't WAV, fail with a clear message — don't attempt to handle MP3 or FLAC in v1. If onset detection finds zero onsets, report it and suggest lowering the threshold rather than producing an empty preset.

On the GarageBand template: Include instructions in the README for creating the template project. It takes about 60 seconds: open GarageBand, create empty project, add Software Instrument track, select AUSampler from the instrument menu, save project, close. The CLI's `--open-template` flag points to this saved .band file.

On vocal chopping and grid mode: Grid mode exists because vocals and melodic material don't have sharp transients for onset detection to find. The musically interesting chop points in a vocal phrase are often mid-syllable or mid-word, which means they don't correspond to any acoustic event — they're rhythmic decisions. Grid mode lets the user make those decisions by choosing a resolution (8th notes for bigger chunks, 16th notes for stutter chops) and then cherry-picking which slices to use by playing through the keys. The user will typically want to combine grid mode with --start and --end to isolate a specific vocal phrase before chopping.

On fade-ms for vocals: When chopping drums, raw cuts (fade-ms=0) sound fine because the transients mask the discontinuity. With vocals, cutting mid-waveform produces audible clicks. Recommend 5-10ms for vocal work in the README and in the CLI help text. The fade should be applied as a linear amplitude ramp at the end of each isolated chop zone (not the cue zones, which play to the end of the file anyway).

On pitch and speed in AUSampler: AUSampler uses simple resampling for pitch shifting — playing a key above the root key plays the sample faster and higher, playing below plays it slower and lower. This is not a bug, it's the classic sampler behavior. For vocal chops in house music this is exactly the desired effect: playing fragments up an octave gives the sped-up chipmunk vocal texture, playing them lower gives a slowed-down effect. The root key for each zone determines the "native pitch" point. The tool maps each slice's root key to match its min/max key, meaning the original pitch is heard at the mapped key and the user transposes by playing other keys. No special handling is needed — AUSampler does this automatically.
