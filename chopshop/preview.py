import numpy as np
import sounddevice as sd

from .analysis import SliceMap
from .constants import MIDI_NOTE_NAMES


def preview_slices(
    y: np.ndarray,
    sr: int,
    slice_map: SliceMap,
    chop_root: int = 60,
) -> bool:
    """Play each slice in the terminal for audition.

    Returns True if the user wants to proceed, False to abort.
    """
    total = len(slice_map.slices)
    print(f"\n--- Preview ({total} slices) ---\n")

    for s in slice_map.slices:
        note = MIDI_NOTE_NAMES.get(chop_root + s.index, str(chop_root + s.index))
        dur = s.end_seconds - s.start_seconds
        print(
            f"  [{s.index + 1}/{total}]  Key: {note}  |  "
            f"Start: {s.start_seconds:.3f}s  |  Duration: {dur:.3f}s"
        )

        chop = y[s.start_sample : s.end_sample]
        try:
            sd.play(chop, sr)
            sd.wait()
        except Exception as e:
            print(f"    (playback error: {e})")

    print()
    try:
        answer = input("Generate preset? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("", "y", "yes")
