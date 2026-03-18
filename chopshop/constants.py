import base64

# --- MIDI ---

MIDI_NOTES = {
    "C0": 24, "C#0": 25, "D0": 26, "D#0": 27, "E0": 28, "F0": 29,
    "F#0": 30, "G0": 31, "G#0": 32, "A0": 33, "A#0": 34, "B0": 35,
    "C1": 36, "C#1": 37, "D1": 38, "D#1": 39, "E1": 40, "F1": 41,
    "F#1": 42, "G1": 43, "G#1": 44, "A1": 45, "A#1": 46, "B1": 47,
    "C2": 48, "C#2": 49, "D2": 50, "D#2": 51, "E2": 52, "F2": 53,
    "F#2": 54, "G2": 55, "G#2": 56, "A2": 57, "A#2": 58, "B2": 59,
    "C3": 60, "C#3": 61, "D3": 62, "D#3": 63, "E3": 64, "F3": 65,
    "F#3": 66, "G3": 67, "G#3": 68, "A3": 69, "A#3": 70, "B3": 71,
    "C4": 72, "C#4": 73, "D4": 74, "D#4": 75, "E4": 76, "F4": 77,
    "F#4": 78, "G4": 79, "G#4": 80, "A4": 81, "A#4": 82, "B4": 83,
    "C5": 84, "C#5": 85, "D5": 86, "D#5": 87, "E5": 88, "F5": 89,
    "F#5": 90, "G5": 91, "G#5": 92, "A5": 93, "A#5": 94, "B5": 95,
}

# Reverse lookup: MIDI number -> note name
MIDI_NOTE_NAMES = {v: k for k, v in MIDI_NOTES.items()}

# --- Defaults ---

DEFAULT_MODE = "onset"
DEFAULT_THRESHOLD = 0.3
DEFAULT_GRID_RESOLUTION = "16th"
GRID_SUBDIVISIONS = {"4th": 1, "8th": 2, "16th": 4, "32nd": 8}
DEFAULT_CUE_ROOT = 36   # C1
DEFAULT_CHOP_ROOT = 60   # C3
MAX_SLICES = 64

# --- Paths ---

PRESET_DIR = "~/Library/Audio/Presets/Apple/AUSampler/"
AUDIO_DIR = "~/Library/Audio/Sounds/ChopShop/"

# --- AUSampler preset constants ---

FILE_REF_BASE_ID = 268435457
MANUFACTURER = 1634758764
SUBTYPE = 1935764848
TYPE_ID = 1635085685
VOICE_COUNT = 64

# Opaque binary blob from reference presets (identical in all tested presets).
DATA_BLOB = base64.b64decode(
    "AAAAAAAAAAAAAAAEAAADhAAAAAAAAAOFAAAAAAAAA4YAAAAAAAADhwAAAAA="
)

# --- Layer boilerplate ---
# Extracted verbatim from reference preset layer 0 (thirrrd.aupreset).
# Connection destination/source integers are layer-0 specific.

CONNECTIONS_LAYER_0 = [
    {
        "ID": 0, "control": 0, "destination": 816840704,
        "enabled": True, "inverse": False,
        "scale": 12800.0, "source": 300, "transform": 1,
    },
    {
        "ID": 1, "control": 0, "destination": 1343225856,
        "enabled": True, "inverse": True,
        "scale": -96.0, "source": 301, "transform": 2,
    },
    {
        "ID": 2, "control": 0, "destination": 1343225856,
        "enabled": True, "inverse": True,
        "scale": -96.0, "source": 7, "transform": 2,
    },
    {
        "ID": 3, "control": 0, "destination": 1343225856,
        "enabled": True, "inverse": True,
        "scale": -96.0, "source": 11, "transform": 2,
    },
    {
        "ID": 4, "control": 0, "destination": 1344274432,
        "enabled": True, "inverse": False,
        "max value": 0.50800001621246338, "min value": -0.50800001621246338,
        "source": 10, "transform": 1,
    },
    {
        "ID": 7, "control": 241, "destination": 816840704,
        "enabled": True, "inverse": False,
        "max value": 12800.0, "min value": -12800.0,
        "source": 224, "transform": 1,
    },
    {
        "ID": 8, "control": 0, "destination": 816840704,
        "enabled": True, "inverse": False,
        "max value": 100.0, "min value": -100.0,
        "source": 242, "transform": 1,
    },
    {
        "ID": 6, "control": 1, "destination": 816840704,
        "enabled": True, "inverse": False,
        "max value": 50.0, "min value": -50.0,
        "source": 268435456, "transform": 1,
    },
    {
        "ID": 5, "control": 0, "destination": 1343225856,
        "enabled": True, "inverse": True,
        "scale": -96.0, "source": 536870912, "transform": 1,
    },
]

ENVELOPES_DEFAULT = [
    {
        "ID": 0,
        "Stages": [
            {"curve": 20, "stage": 0, "time": 0.0},
            {"curve": 22, "stage": 1, "time": 0.0},
            {"curve": 20, "stage": 2, "time": 0.0},
            {"curve": 20, "stage": 3, "time": 0.0},
            {"level": 1.0, "stage": 4},
            {"curve": 20, "stage": 5, "time": 0.0},
            {"curve": 20, "stage": 6, "time": 0.004999999888241291},
        ],
        "enabled": True,
    }
]

FILTERS_DEFAULT = {
    "ID": 0,
    "cutoff": 20000.0,
    "enabled": False,
    "resonance": -3.0,
}

LFOS_DEFAULT = [{"ID": 0, "enabled": True}]

OSCILLATOR_DEFAULT = {"ID": 0, "enabled": True}
