# ChopShop MIDI Generator Guide

The MIDI generator takes your chopped and labeled audio (from the main ChopShop GUI) and creates `.mid` files with drum patterns that use your actual sounds. You can then drag these MIDI files onto GarageBand tracks.

---

## How to Open

```bash
# If venv is activated:
chopshop-midi-gui

# Or run directly (always works):
.venv/bin/chopshop-midi-gui

# Or from the main ChopShop GUI:
# Click the "MIDI Tool" button at the bottom
```

---

## Prerequisites

Before using the MIDI generator, you need a **chopmap file**. You get one by:

1. Opening audio in the main ChopShop GUI (`.venv/bin/chopshop-gui`)
2. Clicking **Analyze** to slice it
3. Checking that the labels make sense (kick, snare, etc. — fix any the auto-labeler got wrong)
4. Clicking **Generate Preset**

This creates a `.chopmap.json` file alongside your audio slices at:
```
~/Library/Audio/Sounds/ChopShop/<name>/<name>.chopmap.json
```

The chopmap maps each slice to a MIDI note and a label. The MIDI generator reads this file to know which note triggers which sound.

---

## Quick Start

1. Click **Open Chopmap** — navigate to your `.chopmap.json` file
2. Select a **Pattern** from the dropdown (amen-classic, basic-jungle, halftime, roller)
3. Click **Load Pattern** — the step grid appears showing every beat
4. Adjust **BPM** and **Bars** as needed
5. Click cells in the grid to add or remove hits
6. Click **Preview** to hear the pattern with your actual sounds
7. Set an output **Filename**
8. Click **Export MIDI** — save your `.mid` file
9. Drag the `.mid` file onto a GarageBand track that has your AUSampler preset loaded

---

## The Interface

### Top Bar

**Open Chopmap** — File picker that defaults to `~/Library/Audio/Sounds/ChopShop/`. Select any `.chopmap.json` file. After loading, you'll see the preset name, number of slices, and which labels are available.

### Controls

**Pattern** — Dropdown with built-in presets:
| Preset | Description |
|--------|-------------|
| **amen-classic** | The classic Amen break rhythm — dense, rolling, kick and snare |
| **basic-jungle** | Dense 2-bar jungle pattern — kick and snare interplay |
| **halftime** | Halftime feel — snare on beat 3, spacious but punchy |
| **roller** | Rolling breakbeat with 32nd-note snare fill at the end |
| **Load from file...** | Load a custom pattern JSON file |

**BPM** — Tempo for the MIDI file. Auto-fills from the pattern's default BPM (usually 170 for jungle presets). Change this to match your GarageBand project tempo.

**Bars** — How many bars of the pattern to generate. The pattern tiles/repeats across however many bars you set. 4 bars is a good starting point.

**Filename** — What to name the exported `.mid` file. Auto-fills from the chopmap name.

### The Step Grid

The big grid in the middle is a **drum machine / piano roll view**:

- **Rows** = different sounds (kick, snare, etc.) — only shows sounds that exist in both your chopmap and the selected pattern
- **Columns** = time steps (16th notes by default)
- **Filled cells** = hits. Brightness = velocity (brighter = louder)
- **Vertical lines**: thick = bar lines, medium = beat lines, thin = step lines

**Click any cell** to toggle a hit on or off. This lets you customize the pattern before exporting.

> **Note**: If the grid shows fewer rows than you expected, it means some labels in the pattern don't match your chopmap. Go back to the main GUI, fix the labels on your slices, re-generate the preset, then reload the chopmap.

### Buttons

| Button | What it does |
|--------|-------------|
| **Load Pattern** | Loads the selected pattern and displays it in the step grid |
| **Preview** | Plays the pattern using your actual chopped audio samples |
| **Stop** | Stops preview playback |
| **Export MIDI** | Opens a save dialog to export the pattern as a `.mid` file |

---

## Workflow: From Break to Beat

Here's the complete end-to-end workflow:

### 1. Chop your break
```bash
.venv/bin/chopshop-gui
```
- Open a breakbeat WAV
- Analyze with onset detection
- Fix labels (make sure kicks are labeled "kick", snares are "snare", etc.)
- Generate Preset

### 2. Generate a MIDI pattern
```bash
.venv/bin/chopshop-midi-gui
```
- Open the chopmap that was just created
- Pick a pattern (try "amen-classic" for a classic feel)
- Set BPM to match your GarageBand project (170 for jungle)
- Set bars to 4 or 8
- Preview it — does it sound right?
- Toggle cells to customize the beat
- Export the .mid file

### 3. Use in GarageBand
- Open GarageBand, create a **Software Instrument** track
- Load your AUSampler preset (the one you generated in step 1)
- Drag the `.mid` file from Finder onto the track
- Hit play — you should hear your chopped break playing the programmed pattern

### 4. Iterate
- Not happy with the pattern? Go back to the MIDI GUI, tweak cells, export again
- Want different sounds? Go back to the main GUI, re-label some slices, regenerate
- Want a different feel? Try a different pattern preset

---

## CLI Alternative

If you prefer the terminal, the same functionality is available as a command:

```bash
# Generate MIDI from chopmap + built-in preset
.venv/bin/chopshop-midi \
  --map ~/Library/Audio/Sounds/ChopShop/my_break/my_break.chopmap.json \
  --preset amen-classic \
  --bpm 170 \
  --bars 4 \
  -o my_drums.mid

# List available presets
.venv/bin/chopshop-midi --list-presets
```

---

## Creating Custom Patterns

Patterns are JSON files. You can create your own and load them via "Load from file..." in the dropdown, or pass them to `--pattern` on the CLI.

Here's the format:
```json
{
  "name": "My Pattern",
  "description": "What this pattern sounds like",
  "bpm": 170,
  "bars": 2,
  "time_signature": [4, 4],
  "resolution": 16,
  "tracks": [
    {
      "name": "drums",
      "channel": 9,
      "steps": [
        {"pos": 0,  "label": "kick",  "velocity": 127},
        {"pos": 4,  "label": "snare", "velocity": 120},
        {"pos": 8,  "label": "kick",  "velocity": 110},
        {"pos": 12, "label": "snare", "velocity": 127}
      ]
    }
  ]
}
```

**Fields:**
- `pos` — step number (0-based). At resolution 16, one bar = steps 0-15
- `label` — must match a label in your chopmap (kick, snare, hat_closed, etc.)
- `velocity` — 0-127, how hard the hit is
- `length` — (optional) how many steps the note should hold. If omitted, the note holds until the next hit of the same label

**Tips:**
- Use only labels that your chopmap actually has. Run `chopshop-midi --list-presets` to see what's available
- The built-in patterns use just "kick" and "snare" because those are the most reliably auto-detected labels
- Velocity variation is key to making patterns feel human — don't make every hit 127

---

## Troubleshooting

**"No chopmap loaded"** — You need to generate a preset in the main GUI first. The chopmap is created alongside the preset.

**Grid shows no rows** — The pattern uses labels that don't exist in your chopmap. Check what labels your chopmap has (shown in the info bar after loading) and make sure the pattern references those labels.

**Preview sounds wrong** — The preview mixes your chopped WAV files directly. If slices are too long or overlap, it can sound muddy. Try shorter slices or adjust the pattern.

**MIDI plays wrong sounds in GarageBand** — Make sure the GarageBand track is using the AUSampler preset that matches the chopmap you loaded. Each chopmap is tied to a specific set of slices.

**"command not found"** — Run with the full path: `.venv/bin/chopshop-midi-gui`

---

## Status

This tool is **experimental**. The patterns work but could use more variety, and the step grid is basic (no velocity editing yet, no drag-to-paint). It does the job of getting MIDI patterns onto GarageBand tracks from your chopped samples.
