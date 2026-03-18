from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf

from .analysis import SliceMap


@dataclass
class ExportResult:
    output_dir: Path
    chop_paths: list[Path]
    cue_paths: list[Path] = field(default_factory=list)
    full_path: Path | None = None
    sample_rate: int = 44100
    source_name: str = ""


def export_slices(
    y: np.ndarray,
    sr: int,
    slice_map: SliceMap,
    output_dir: Path,
    source_name: str,
    fade_ms: float = 0.0,
    cue_zones: bool = False,
    include_full: bool = True,
) -> ExportResult:
    """Export individual WAV files for each slice.

    Args:
        y: Mono audio array.
        sr: Sample rate.
        slice_map: Analysis result with slice boundaries.
        output_dir: Directory to write WAV files into.
        source_name: Base name for files (e.g. "cw_amen02_165").
        fade_ms: Linear fade-out duration in ms applied to each chop.
        cue_zones: If True, also export cue WAVs (onset to EOF).
        include_full: If True, write the full audio as {source_name}_full.wav.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fade_samples = int(fade_ms / 1000.0 * sr) if fade_ms > 0 else 0
    pad_width = 2 if len(slice_map.slices) < 100 else 3

    chop_paths = []
    cue_paths = []

    for s in slice_map.slices:
        # --- Chop WAV (isolated slice) ---
        chop = y[s.start_sample : s.end_sample].copy()
        if fade_samples > 0 and len(chop) > 0:
            _apply_fade(chop, fade_samples)
        chop_name = f"{source_name}_chop_{s.index:0{pad_width}d}.wav"
        chop_path = output_dir / chop_name
        sf.write(str(chop_path), chop, sr)
        chop_paths.append(chop_path)

        # --- Cue WAV (onset to end of file) ---
        if cue_zones:
            cue = y[s.start_sample :]
            cue_name = f"{source_name}_cue_{s.index:0{pad_width}d}.wav"
            cue_path = output_dir / cue_name
            sf.write(str(cue_path), cue, sr)
            cue_paths.append(cue_path)

    # --- Full file WAV ---
    full_path = None
    if include_full:
        full_path = output_dir / f"{source_name}_full.wav"
        sf.write(str(full_path), y, sr)

    return ExportResult(
        output_dir=output_dir,
        chop_paths=chop_paths,
        cue_paths=cue_paths,
        full_path=full_path,
        sample_rate=sr,
        source_name=source_name,
    )


def _apply_fade(samples: np.ndarray, fade_samples: int) -> None:
    """Apply a linear fade-out to the end of the sample array (in-place)."""
    fade_len = min(fade_samples, len(samples))
    fade_curve = np.linspace(1.0, 0.0, fade_len)
    samples[-fade_len:] *= fade_curve
