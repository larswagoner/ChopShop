from dataclasses import dataclass

import librosa
import numpy as np

from .constants import (
    DEFAULT_GRID_RESOLUTION,
    DEFAULT_MODE,
    DEFAULT_THRESHOLD,
    GRID_SUBDIVISIONS,
    MAX_SLICES,
)


@dataclass
class Slice:
    index: int
    start_sample: int
    end_sample: int
    start_seconds: float
    end_seconds: float


@dataclass
class SliceMap:
    source_path: str
    sample_rate: int
    bpm: float
    duration: float
    total_samples: int
    mode: str
    slices: list[Slice]


def analyze(
    y: np.ndarray,
    sr: int,
    source_path: str = "",
    mode: str = DEFAULT_MODE,
    threshold: float = DEFAULT_THRESHOLD,
    num_slices: int | None = None,
    quantize_bpm: float | None = None,
    grid_resolution: str = DEFAULT_GRID_RESOLUTION,
) -> SliceMap:
    """Analyze audio and return a SliceMap with slice boundaries.

    Args:
        y: Mono audio array at native sample rate.
        sr: Sample rate.
        source_path: Original file path (stored in SliceMap for reference).
        mode: "onset", "grid", or "equal".
        threshold: Onset detection sensitivity (onset mode only).
        num_slices: Force N slices (required for equal mode).
        quantize_bpm: BPM for grid snapping (onset) or grid interval (grid).
        grid_resolution: "4th", "8th", "16th", or "32nd" (grid mode).
    """
    if mode == "equal" and num_slices is None:
        raise ValueError("Equal mode requires --num-slices to be set.")

    total_samples = len(y)
    duration = total_samples / sr

    # Detect BPM
    tempo, _beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    # librosa may return an array; extract scalar
    bpm = float(np.atleast_1d(tempo)[0])

    if mode == "onset":
        slice_points = _onset_slices(y, sr, threshold, num_slices, quantize_bpm, grid_resolution)
    elif mode == "grid":
        grid_bpm = quantize_bpm if quantize_bpm is not None else bpm
        slice_points = _grid_slices(total_samples, sr, grid_bpm, grid_resolution)
    elif mode == "equal":
        slice_points = _equal_slices(total_samples, num_slices)
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Use 'onset', 'grid', or 'equal'.")

    # Enforce MAX_SLICES
    if len(slice_points) > MAX_SLICES:
        slice_points = slice_points[:MAX_SLICES]

    # Build Slice list
    slices = []
    for i, start in enumerate(slice_points):
        end = slice_points[i + 1] if i + 1 < len(slice_points) else total_samples
        slices.append(Slice(
            index=i,
            start_sample=int(start),
            end_sample=int(end),
            start_seconds=start / sr,
            end_seconds=end / sr,
        ))

    return SliceMap(
        source_path=source_path,
        sample_rate=sr,
        bpm=bpm,
        duration=duration,
        total_samples=total_samples,
        mode=mode,
        slices=slices,
    )


def _onset_slices(
    y: np.ndarray,
    sr: int,
    threshold: float,
    num_slices: int | None,
    quantize_bpm: float | None,
    grid_resolution: str,
) -> list[int]:
    """Detect onsets and return sorted sample positions."""
    onsets = librosa.onset.onset_detect(
        y=y, sr=sr, delta=threshold, units="samples",
    )
    onsets = list(onsets.astype(int))

    if not onsets:
        return [0]

    # Ensure 0 is included as the first slice point
    if onsets[0] != 0:
        onsets.insert(0, 0)

    # If num_slices requested, keep strongest N (plus the 0 start)
    if num_slices is not None and len(onsets) > num_slices:
        # Get onset strength envelope
        strength_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, delta=threshold)

        # Map each onset (except 0) to its strength
        strengths = {}
        for sample_pos in onsets:
            if sample_pos == 0:
                continue
            frame = librosa.samples_to_frames(sample_pos)
            frame = min(frame, len(strength_env) - 1)
            strengths[sample_pos] = strength_env[frame]

        # Keep top N-1 by strength (plus the 0 start = N total)
        ranked = sorted(strengths.keys(), key=lambda s: strengths[s], reverse=True)
        kept = sorted(ranked[: num_slices - 1])
        onsets = [0] + kept

    # Quantize to BPM grid if requested
    if quantize_bpm is not None:
        subdivisions = GRID_SUBDIVISIONS[grid_resolution]
        interval_samples = int(60.0 / quantize_bpm / subdivisions * sr)
        quantized = []
        for pos in onsets:
            nearest = round(pos / interval_samples) * interval_samples
            quantized.append(nearest)
        onsets = sorted(set(quantized))

    return onsets


def _grid_slices(
    total_samples: int,
    sr: int,
    bpm: float,
    grid_resolution: str,
) -> list[int]:
    """Place slices on a rhythmic grid."""
    subdivisions = GRID_SUBDIVISIONS[grid_resolution]
    interval_seconds = 60.0 / bpm / subdivisions
    interval_samples = int(interval_seconds * sr)

    points = list(range(0, total_samples, interval_samples))
    return points


def _equal_slices(total_samples: int, num_slices: int) -> list[int]:
    """Divide audio into N equal segments."""
    segment_length = total_samples // num_slices
    return [i * segment_length for i in range(num_slices)]
