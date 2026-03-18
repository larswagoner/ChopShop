"""Simple heuristic auto-labeler for drum slice classification."""

from __future__ import annotations

import librosa
import numpy as np

from .analysis import Slice

STANDARD_LABELS = [
    "kick", "snare", "snare_ghost", "hat_closed", "hat_open",
    "ride", "crash", "tom_high", "tom_mid", "tom_low", "combo", "other",
]

# Color map for GUI display (hex colors by label category)
LABEL_COLORS = {
    "kick":         "#FF8C00",
    "snare":        "#FFD700",
    "snare_ghost":  "#FFD700",
    "hat_closed":   "#00CED1",
    "hat_open":     "#00CED1",
    "ride":         "#00CED1",
    "crash":        "#00CED1",
    "tom_high":     "#32CD32",
    "tom_mid":      "#32CD32",
    "tom_low":      "#32CD32",
    "combo":        "#A0A0A0",
    "other":        "#A0A0A0",
}

DEFAULT_LABEL_COLOR = "#A0A0A0"


def auto_label(y: np.ndarray, sr: int, slices: list[Slice]) -> list[str]:
    """Classify each slice using spectral features.

    Returns a list of label strings, one per slice.  Thresholds are
    relative to the file's overall statistics so the heuristic adapts
    to different recordings.
    """
    if not slices:
        return []

    # Gather per-slice features
    features = []
    for s in slices:
        seg = y[s.start_sample:s.end_sample]
        if len(seg) < 64:
            features.append(None)
            continue
        features.append(_extract_features(seg, sr))

    # Compute file-wide medians for relative thresholds
    centroids = [f["centroid"] for f in features if f is not None]
    zcrs = [f["zcr"] for f in features if f is not None]
    low_energies = [f["low_energy"] for f in features if f is not None]

    if not centroids:
        return ["other"] * len(slices)

    med_centroid = float(np.median(centroids))
    med_zcr = float(np.median(zcrs))
    med_low = float(np.median(low_energies))

    labels = []
    for f in features:
        if f is None:
            labels.append("other")
            continue
        labels.append(_classify(f, med_centroid, med_zcr, med_low))

    return labels


def auto_label_single(y: np.ndarray, sr: int, start: int, end: int) -> str:
    """Classify a single audio region. Used when a new marker is added."""
    seg = y[start:end]
    if len(seg) < 64:
        return "other"
    f = _extract_features(seg, sr)
    # Without file-wide context, use absolute thresholds
    return _classify_absolute(f)


def _extract_features(seg: np.ndarray, sr: int) -> dict:
    """Extract audio features from a short segment."""
    # Spectral centroid (mean frequency)
    cent = librosa.feature.spectral_centroid(y=seg, sr=sr)
    centroid = float(np.mean(cent)) if cent.size > 0 else 0.0

    # Zero-crossing rate
    zcr_arr = librosa.feature.zero_crossing_rate(seg)
    zcr = float(np.mean(zcr_arr)) if zcr_arr.size > 0 else 0.0

    # RMS energy
    rms = float(np.sqrt(np.mean(seg ** 2)))

    # Low-band energy (<200Hz)
    n_fft = min(2048, len(seg))
    if n_fft >= 64:
        S = np.abs(librosa.stft(seg, n_fft=n_fft))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        low_mask = freqs < 200
        high_mask = freqs > 5000
        low_energy = float(np.mean(S[low_mask])) if low_mask.any() else 0.0
        high_energy = float(np.mean(S[high_mask])) if high_mask.any() else 0.0
    else:
        low_energy = 0.0
        high_energy = 0.0

    duration = len(seg) / sr

    return {
        "centroid": centroid,
        "zcr": zcr,
        "rms": rms,
        "low_energy": low_energy,
        "high_energy": high_energy,
        "duration": duration,
    }


def _classify(f: dict, med_centroid: float, med_zcr: float, med_low: float) -> str:
    """Classify using thresholds relative to file medians."""
    centroid = f["centroid"]
    zcr = f["zcr"]
    low_e = f["low_energy"]
    high_e = f["high_energy"]
    rms = f["rms"]
    dur = f["duration"]

    # Very short segments are hard to classify
    if dur < 0.01:
        return "other"

    # Kick: low centroid, strong low-frequency energy
    if centroid < med_centroid * 0.7 and low_e > med_low * 1.3:
        return "kick"

    # Crash: bright, noisy, long
    if centroid > med_centroid * 1.5 and zcr > med_zcr * 1.2 and dur > 0.15:
        return "crash"

    # Hat open: bright, noisy, medium duration
    if centroid > med_centroid * 1.3 and zcr > med_zcr * 1.1 and dur > 0.05:
        if dur > 0.12:
            return "hat_open"
        return "hat_closed"

    # Ride: bright but less noisy than hats
    if centroid > med_centroid * 1.4 and zcr < med_zcr * 1.1 and dur > 0.08:
        return "ride"

    # Snare: mid centroid, noisy (high ZCR), decent energy
    if zcr > med_zcr * 1.0 and centroid > med_centroid * 0.6:
        if rms < 0.05:
            return "snare_ghost"
        return "snare"

    # Toms: moderate centroid, tonal (low ZCR)
    if zcr < med_zcr * 0.8 and centroid > med_centroid * 0.4:
        if centroid > med_centroid * 0.8:
            return "tom_high"
        elif centroid > med_centroid * 0.6:
            return "tom_mid"
        else:
            return "tom_low"

    return "other"


def _classify_absolute(f: dict) -> str:
    """Classify using absolute thresholds (no file context)."""
    centroid = f["centroid"]
    zcr = f["zcr"]
    low_e = f["low_energy"]
    dur = f["duration"]

    if dur < 0.01:
        return "other"
    if centroid < 1500 and low_e > 0.01:
        return "kick"
    if centroid > 6000 and zcr > 0.15:
        if dur > 0.12:
            return "hat_open"
        return "hat_closed"
    if zcr > 0.1 and centroid > 2000:
        return "snare"
    return "other"
