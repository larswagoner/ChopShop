# Making a Basic 90s Jungle Track with ChopShop + GarageBand

A step-by-step guide to building an authentic-sounding 90s jungle/drum & bass track using chopped breaks, ambient pads, and keys — no vocals.

---

## What You Need

- ChopShop (installed with GUI)
- GarageBand (or Logic Pro)
- A breakbeat sample (Amen break, Think break, Apache, etc.)
- Headphones or monitors

---

## Step 1: Find a Breakbeat

Classic jungle breaks:
- **Amen Break** — "Amen, Brother" by The Winstons (the quintessential jungle break)
- **Think Break** — "Think (About It)" by Lyn Collins
- **Apache** — "Apache" by The Incredible Bongo Band
- **Funky Drummer** — James Brown

Search for royalty-free versions or sample packs. You want a clean, isolated drum loop — ideally 1-4 bars at a known BPM.

---

## Step 2: Chop the Break

Open ChopShop GUI:

```bash
.venv/bin/chopshop-gui
```

1. **Open WAV** — load your break
2. **Mode**: onset
3. **Threshold**: start at 0.3 — adjust up if too many slices, down if it's missing hits
4. Click **Analyze**
5. Click each slice to preview — every drum hit should be cleanly isolated
6. Drag markers to fix any cuts that landed in the wrong spot
7. Double-click to add cuts the detector missed, right-click to remove extras
8. **Name**: something like "amen_chops"
9. Click **Generate Preset**

---

## Step 3: Set Up GarageBand

1. Open GarageBand, create an **Empty Project**
2. Set the **tempo to 160-170 BPM** (classic jungle tempo)
3. Set time signature to **4/4**

### Load Your Break

1. Add a **Software Instrument** track
2. Click the instrument slot, choose **AU Instruments > AUSampler**
3. In AUSampler, browse presets and find your "amen_chops" preset
4. Play your MIDI keyboard — each key from C3 up triggers a different drum hit

---

## Step 4: Program the Drums

This is where jungle gets its character. Take the individual hits from the break and rearrange them into new patterns at 160+ BPM.

### Hands-On: Your First 2-Bar Pattern

Open the piano roll on your AUSampler track. Play through your chop keys (C3 upward) to find which key has which hit. For a typical Amen break you'll find something like:

```
C3  = Kick
C#3 = Kick + hat
D3  = Snare
D#3 = Snare (ghost)
E3  = Hat
F3  = Ride
...etc — yours will vary depending on where the slices landed
```

Once you know your hits, draw this 2-bar pattern in the piano roll (each position is a 16th note):

```
Beat:  1 . . . 2 . . . 3 . . . 4 . . . | 1 . . . 2 . . . 3 . . . 4 . . .
Kick:  C3          C3                    | C3          C3
Snare:      D#3         D#3             |      D#3         D#3    A#3
Hats:  A3 A3 A3 A3 A3 A3 A3 A3          | A3 A3 A3 A3 A3 A3 A3 A3
```

The exact keys depend on which slice has which hit — play through C3 onward to find your kick, snare, and hat slices. Make notes short (16th notes) for that choppy jungle feel. **Loop this 2-bar region.**

### Building It Up

Once the foundation is looping, add ghost notes, offbeat hits, and rolls:

```
Beat:  1 . . . 2 . . . 3 . . . 4 . . .
Kick:  X . . X . . . . X . . . . . X .
Snare: . . . . X . . . . . X . X . . .
Hat:   X X . X X . X . X X . X X . X X
Ghost: . . X . . . X X . . . X . X . .
```

The ghost notes are quieter hits (lower velocity) from the break — ride cymbal taps, open hats, whatever's in your chops. Set their velocity to 60-80 (out of 127) so they sit behind the main hits.

### Jungle Drum Tips
- **Time-stretch** is your friend — if the original break was 165 BPM and your project is 170, GarageBand will stretch it
- **Rolls and fills**: program rapid 32nd-note snare or hat rolls at the end of every 4 or 8 bars
- **Velocity variation**: don't keep all hits at max velocity — vary between 80-127 for a human feel
- **Double-time sections**: program some bars at twice the density for energy lifts

---

## Step 5: Add a Sub Bass

Jungle needs deep, rolling sub bass.

1. Add a new **Software Instrument** track
2. Choose a simple sine wave synth (Alchemy > Bass > Sub Bass, or any basic synth)
3. Set the oscillator to a **pure sine or triangle wave**
4. No filter, no effects — just deep low end

### Bass Pattern
The bass follows the kick loosely but adds movement:
```
Beat:  1 . . . 2 . . . 3 . . . 4 . . .
Bass:  C . . E . . . . C . . . G . . .
```

- Keep it in the **C1-C2 range** (low)
- Use **long sustained notes** that glide between pitches
- Add **portamento/glide** if your synth supports it — that sliding bass sound is classic jungle

---

## Step 6: Add Atmospheric Pads

Jungle tracks live on atmosphere — dark, reverb-soaked pads and strings.

1. Add a new **Software Instrument** track
2. Choose a pad sound (Alchemy > Pad > Atmospheric, or Vintage Electric Piano with heavy reverb)
3. Play **simple minor chords** — Am, Em, Dm work well
4. Hold each chord for 2-4 bars

### Pad Settings
- **Reverb**: crank it. 60-80% wet. Big, dark hall reverb.
- **Low-pass filter**: roll off everything above 3-4kHz for that murky, distant sound
- **Slow attack**: 200-500ms so the pad fades in gently

### Classic Jungle Chord Progressions
- **Am - G - F - E** (dark, driving)
- **Cm - Gm - Ab - Bb** (moody)
- **Am - Em** (minimal, hypnotic — just two chords looping)

---

## Step 7: Add Keys/Stabs

Short, punchy chord stabs or piano hits that cut through the mix.

1. Add another **Software Instrument** track
2. Choose an electric piano or organ sound
3. Program **short staccato chords** on offbeats

### Stab Pattern
```
Beat:  1 . . . 2 . . . 3 . . . 4 . . .
Stab:  . . X . . . . X . . X . . . . .
```

- Keep the notes short (1/16th or 1/8th)
- Same chord progression as your pad but as quick hits
- Add a touch of reverb and delay

---

## Step 8: Add Atmosphere

Optional but makes a big difference:

1. Find a vinyl crackle or rain ambience (search "vinyl noise" on Freesound.org)
2. Drop it on an audio track, loop it, keep it quiet underneath everything
3. This gives the track that dusty, underground feel

---

## Step 9: Arrangement

Keep it simple — jungle arrangements are straightforward:

```
Intro (8 bars):     Pad + atmosphere only
Drop (16 bars):     Add break + sub bass
Breakdown (8 bars): Drop the break, keep pad + atmosphere
Drop 2 (16 bars):   Break + sub + pad, maybe vary the break pattern
Outro (8 bars):     Strip back to pad, fade out
```

### Arrangement Tips
- **Filter sweeps**: automate a low-pass filter on the break — sweep it open on the drop
- **Drops hit harder with silence**: leave a half-beat of silence right before the drop
- **Fills**: use snare rolls or reverse cymbal samples at section transitions
- **Double the break**: layer two copies of your chopped break, one panned left, one right, with slight timing offsets for width

---

## Step 10: Mix

Keep it rough — jungle isn't supposed to be pristine. The whole thing should feel like it's coming out of a smoke-filled warehouse.

- **Break**: loud and upfront. Slight compression, maybe a touch of distortion/saturation. EQ out mud around 300Hz.
- **Sub bass**: quiet but *felt*. High-pass at 30Hz to remove rumble. Don't let it compete with the kick — it should sit underneath.
- **Pads**: low-pass filter, heavy reverb, keep them quiet — they're atmosphere, not lead. Sits behind everything, lots of reverb.
- **Stabs**: short reverb, slight delay, medium volume
- **Master**: light compression on the master bus. Don't over-compress — jungle has dynamics.

---

## Quick Reference

| Element | Sound | Key Characteristics |
|---------|-------|-------------------|
| Drums | Chopped breakbeat | 160-170 BPM, ghost notes, rolls, human feel |
| Bass | Sine/triangle sub | C1-C2, sustained, gliding between notes |
| Pads | Dark atmospheric | Minor chords, heavy reverb, filtered |
| Stabs | Electric piano/organ | Short, offbeat, punchy |
| Tempo | 160-170 BPM | Classic jungle range |
| Key | Minor keys | Am, Cm, Em — dark and moody |
