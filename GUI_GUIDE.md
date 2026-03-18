# ChopShop GUI Guide

## Quick Start

```bash
.venv/bin/chopshop-gui
```

1. Click **Open WAV** and pick an audio file
2. Choose your slicing mode and settings
3. Click **Analyze** — slice markers appear on the waveform
4. Adjust markers if needed, preview by clicking slices
5. Name your preset and click **Generate Preset**
6. Open GarageBand, add an AUSampler instrument, load the preset

---

## The Waveform

The big dark panel shows your audio waveform. After analysis, coloured regions show each slice and red vertical lines mark the cut points.

### Mouse Controls

| Action | What it does |
|--------|-------------|
| **Click** a slice region | Plays that slice through your speakers |
| **Drag** a red marker | Moves the cut point — adjusts where one slice ends and the next begins |
| **Double-click** empty space | Adds a new cut point at that position |
| **Right-click** a marker | Deletes that cut point (merges the two slices on either side) |

The first marker (at the very start) can't be moved or deleted — every chop set needs to begin at the start of the file.

The orange line that appears during playback is the **playhead** showing your current position.

---

## Controls

### Mode

How ChopShop decides where to place slice boundaries.

| Mode | Technical | Plain English |
|------|-----------|---------------|
| **onset** | Detects transients using librosa's spectral flux onset detector. Places a cut at each detected attack. | Finds the "hits" — every drum hit, note start, or sharp sound gets its own slice. Best for breaks and percussion. |
| **grid** | Divides audio at fixed rhythmic intervals based on BPM and subdivision (4th/8th/16th/32nd notes). | Cuts at regular musical intervals like a metronome. Best when you know the BPM and want evenly-spaced rhythmic chops. |
| **equal** | Divides the total sample count into N equal-length segments. | Cuts the audio into a specific number of equal-sized pieces, regardless of musical content. |

### Analysis Settings

**Threshold** (onset mode only)
- *Technical*: Controls the `delta` parameter of the onset detection algorithm. Lower values detect quieter/softer transients; higher values only trigger on strong attacks.
- *Plain English*: How sensitive the hit detection is. Low = finds everything (more slices). High = only finds the loudest hits (fewer slices).
- Range: 0.0 to 1.0. Default: 0.3.

**BPM**
- *Technical*: Sets beats per minute for grid mode intervals and onset quantization. When set to 0 (auto), librosa's `beat_track()` estimates the tempo.
- *Plain English*: The tempo of your audio. Leave at 0 to let ChopShop guess, or type in the exact BPM if you know it. Auto-detection can sometimes guess half or double the real tempo — if your grid slices look wrong, try setting this manually.

**Grid** (grid and onset modes)
- *Technical*: The rhythmic subdivision — determines the interval between grid lines as a fraction of one beat.
- *Plain English*: How fine the grid is.
  - **4th** = one cut per beat (quarter notes)
  - **8th** = two cuts per beat
  - **16th** = four cuts per beat (default, good for chopping breaks)
  - **32nd** = eight cuts per beat (very fine, for glitch/granular effects)

**Slices**
- *Technical*: In onset mode, limits output to the N strongest onsets by spectral flux magnitude. In equal mode, this is required — it's the exact number of equal divisions. Ignored in grid mode.
- *Plain English*: How many slices you want. In onset mode, leave at 0 for "as many as detected" or set a number to keep only the strongest hits. In equal mode, you must set this.

### MIDI Settings

**Chop Root**
- *Technical*: The MIDI note number assigned to the first slice. Subsequent slices increment chromatically (C3, C#3, D3, ...).
- *Plain English*: Which key on your MIDI keyboard triggers the first chop. Default is C3 (middle C). Slice 1 = C3, slice 2 = C#3, slice 3 = D3, and so on.

**Cue Root**
- *Technical*: The starting MIDI note for cue zones (only used when cue zones are enabled).
- *Plain English*: Which key triggers the first cue zone. Default is C1 (two octaves below the chops), so cues and chops don't overlap.

**Cue Zones**
- *Technical*: When enabled, generates an additional set of zones where each zone plays from its onset point to the end of the audio file, mapped starting at cue root.
- *Plain English*: Gives you a second set of keys where each key plays from that chop's start point all the way to the end of the file. Example: if you have a drum break chopped into 8 hits, pressing cue key 3 plays from hit 3 through the rest of the break. Great for triggering a loop from any point.

**No Full Key**
- *Technical*: When checked, omits the full-audio zone that is normally mapped to `chop_root - 1`.
- *Plain English*: By default, ChopShop puts the entire unsliced audio on one key just below your first chop (e.g. B2 if chops start at C3). Check this box to skip that.

### Export Settings

**Name**
- The name for your preset file. Auto-fills from the audio filename, but you can change it to whatever you want. This is what shows up in GarageBand's preset browser.

**Fade (ms)**
- *Technical*: Applies a linear amplitude ramp-down to the final N milliseconds of each exported chop WAV file.
- *Plain English*: A quick volume fade at the end of each slice to prevent clicks or pops. Set to 0 for hard cuts (good for drums). Set to 5-10ms for vocals or melodic content where slices might click at the boundaries.

---

## Buttons

| Button | What it does |
|--------|-------------|
| **Open WAV** | Load an audio file (WAV, AIFF, FLAC, MP3) |
| **Analyze** | Run the slicer with current settings — places markers on the waveform |
| **Play All** | Plays the entire audio file with an animated playhead |
| **Stop** | Stops any currently playing audio |
| **Generate Preset** | Exports slice WAVs and creates the .aupreset file for GarageBand |

---

## Typical Workflows

### Chopping a drum break
1. Open your break WAV
2. Mode: **onset**, Threshold: **0.3**
3. Click Analyze
4. Click slices to preview — each hit should be isolated
5. If too many slices: raise threshold or set a slice count
6. If a cut is in the wrong place: drag the marker
7. Generate Preset, load in GarageBand

### Chopping vocals to a grid
1. Open your vocal WAV
2. Mode: **grid**, BPM: (your song's BPM), Grid: **8th**
3. Fade: **5-10ms** (prevents clicks between syllables)
4. Click Analyze
5. Double-click to add cuts where the grid missed something, right-click to remove unnecessary ones
6. Generate Preset

### Making equal-length slices
1. Open any audio file
2. Mode: **equal**, Slices: (pick a number, e.g. 16)
3. Click Analyze — you'll get perfectly uniform slices
4. Generate Preset

---

## Where Files Go

- **Preset**: `~/Library/Audio/Presets/Apple/AUSampler/`
- **Audio slices**: `~/Library/Audio/Sounds/ChopShop/<name>/`

In GarageBand: create a **Software Instrument** track, open the instrument picker, choose **AUSampler**, then browse presets to find yours.
