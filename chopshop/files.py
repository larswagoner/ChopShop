import subprocess
from pathlib import Path

from .constants import AUDIO_DIR, PRESET_DIR


def resolve_audio_dir(source_name: str, audio_dir: str | None = None) -> Path:
    """Return the directory where slice WAVs should be exported."""
    base = Path(audio_dir or AUDIO_DIR).expanduser()
    dest = base / source_name
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def resolve_preset_dir(preset_dir: str | None = None) -> Path:
    """Return the directory where .aupreset files are installed."""
    dest = Path(preset_dir or PRESET_DIR).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def install_preset(
    preset_bytes: bytes,
    preset_name: str,
    preset_dir: str | None = None,
) -> Path:
    """Write preset XML bytes to the AUSampler preset directory."""
    dest_dir = resolve_preset_dir(preset_dir)
    dest = dest_dir / f"{preset_name}.aupreset"

    # Avoid overwriting — append numeric suffix if needed
    if dest.exists():
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{preset_name}_{counter}.aupreset"
            counter += 1

    dest.write_bytes(preset_bytes)
    return dest


def open_template(template_path: str) -> None:
    """Open a .band template file in GarageBand."""
    subprocess.run(["open", template_path], check=True)
