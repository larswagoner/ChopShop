"""MIDI pattern generator GUI — load a chopmap, pick a pattern, tweak, preview, export."""

import json
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..midi_gen import (
    build_label_map,
    generate_midi,
    list_presets,
    load_chopmap,
    load_pattern,
)
from ..labeler import LABEL_COLORS, DEFAULT_LABEL_COLOR


# ---------------------------------------------------------------------------
# Step grid widget — visual representation of the pattern
# ---------------------------------------------------------------------------

GRID_BG = QColor(28, 28, 30)
GRID_LINE = QColor(60, 60, 65)
GRID_BEAT_LINE = QColor(90, 90, 95)
GRID_BAR_LINE = QColor(140, 140, 145)
CELL_FONT = QFont()
CELL_FONT.setPointSize(8)


class StepGridWidget(QWidget):
    """Draws a piano-roll-style step grid for the drum pattern."""

    step_toggled = Signal(int, int)  # (row, step) — emitted when user clicks a cell

    ROW_HEIGHT = 28
    STEP_WIDTH = 22
    LABEL_WIDTH = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)

        # Data
        self._labels: list[str] = []       # row labels (kick, snare, etc.)
        self._steps_per_bar: int = 16
        self._bars: int = 2
        self._grid: dict[tuple[int, int], int] = {}  # (row, step) -> velocity
        self._label_colors: dict[str, str] = {}

    def set_pattern(self, labels: list[str], steps_per_bar: int, bars: int,
                    grid: dict[tuple[int, int], int], label_colors: dict[str, str]):
        self._labels = labels
        self._steps_per_bar = steps_per_bar
        self._bars = bars
        self._grid = dict(grid)
        self._label_colors = label_colors
        total_steps = steps_per_bar * bars
        w = self.LABEL_WIDTH + total_steps * self.STEP_WIDTH + 2
        h = max(len(labels) * self.ROW_HEIGHT + 2, 100)
        self.setMinimumSize(w, h)
        self.setFixedSize(w, h)
        self.update()

    def get_grid(self) -> dict[tuple[int, int], int]:
        return dict(self._grid)

    def clear(self):
        self._labels = []
        self._grid = {}
        self.update()

    def paintEvent(self, event):
        if not self._labels:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(CELL_FONT)
        fm = QFontMetrics(CELL_FONT)
        total_steps = self._steps_per_bar * self._bars

        # Background
        p.fillRect(self.rect(), GRID_BG)

        # Row labels
        for row, label in enumerate(self._labels):
            y = row * self.ROW_HEIGHT
            hex_c = self._label_colors.get(label, DEFAULT_LABEL_COLOR)
            p.setPen(QColor(hex_c))
            p.drawText(4, y + self.ROW_HEIGHT // 2 + fm.ascent() // 2, label)

        # Grid lines
        x0 = self.LABEL_WIDTH
        for step in range(total_steps + 1):
            x = x0 + step * self.STEP_WIDTH
            if step % self._steps_per_bar == 0:
                p.setPen(QPen(GRID_BAR_LINE, 2))
            elif step % (self._steps_per_bar // 4) == 0:
                p.setPen(QPen(GRID_BEAT_LINE, 1))
            else:
                p.setPen(QPen(GRID_LINE, 1))
            p.drawLine(x, 0, x, len(self._labels) * self.ROW_HEIGHT)

        # Horizontal row lines
        p.setPen(QPen(GRID_LINE, 1))
        for row in range(len(self._labels) + 1):
            y = row * self.ROW_HEIGHT
            p.drawLine(x0, y, x0 + total_steps * self.STEP_WIDTH, y)

        # Filled cells
        for (row, step), vel in self._grid.items():
            if row >= len(self._labels):
                continue
            label = self._labels[row]
            hex_c = self._label_colors.get(label, DEFAULT_LABEL_COLOR)
            cell_color = QColor(hex_c)
            # Brightness based on velocity
            alpha = int(80 + (vel / 127) * 175)
            cell_color.setAlpha(alpha)
            x = x0 + step * self.STEP_WIDTH + 1
            y = row * self.ROW_HEIGHT + 1
            p.fillRect(x, y, self.STEP_WIDTH - 2, self.ROW_HEIGHT - 2, cell_color)

        p.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x = event.position().x() - self.LABEL_WIDTH
        y = event.position().y()
        if x < 0:
            return
        step = int(x / self.STEP_WIDTH)
        row = int(y / self.ROW_HEIGHT)
        total_steps = self._steps_per_bar * self._bars
        if step < 0 or step >= total_steps or row < 0 or row >= len(self._labels):
            return
        key = (row, step)
        if key in self._grid:
            del self._grid[key]
        else:
            self._grid[key] = 100
        self.update()
        self.step_toggled.emit(row, step)


# ---------------------------------------------------------------------------
# Main MIDI window
# ---------------------------------------------------------------------------

class MidiWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChopShop MIDI")
        self.setMinimumSize(700, 480)
        self.resize(1000, 550)

        self._chopmap: dict | None = None
        self._chopmap_path: Path | None = None
        self._pattern: dict | None = None
        self._label_map: dict[str, int] = {}
        self._audio_cache: dict[int, np.ndarray] = {}
        self._sr: int = 44100

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)

        # --- Top: chopmap file ---
        file_row = QHBoxLayout()
        self._btn_open = QPushButton("Open Chopmap...")
        self._btn_open.setFixedWidth(140)
        self._lbl_file = QLabel("No chopmap loaded")
        self._lbl_file.setStyleSheet("color: #999;")
        file_row.addWidget(self._btn_open)
        file_row.addWidget(self._lbl_file, 1)
        root.addLayout(file_row)

        # --- Controls row ---
        controls = QHBoxLayout()

        # Pattern preset
        pat_grp = QGroupBox("Pattern")
        pl = QVBoxLayout()
        self._combo_preset = QComboBox()
        for name in list_presets():
            pat = load_pattern(name)
            desc = pat.get("description", "")
            self._combo_preset.addItem(f"{name}", name)
        self._combo_preset.addItem("Load from file...", "__file__")
        pl.addWidget(self._combo_preset)
        pat_grp.setLayout(pl)
        controls.addWidget(pat_grp)

        # BPM / bars
        settings_grp = QGroupBox("Settings")
        sl = QVBoxLayout()

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("BPM"))
        self._spin_bpm = QDoubleSpinBox()
        self._spin_bpm.setRange(60, 300)
        self._spin_bpm.setValue(170)
        r1.addWidget(self._spin_bpm)
        sl.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Bars"))
        self._spin_bars = QSpinBox()
        self._spin_bars.setRange(1, 16)
        self._spin_bars.setValue(4)
        r2.addWidget(self._spin_bars)
        sl.addLayout(r2)

        settings_grp.setLayout(sl)
        controls.addWidget(settings_grp)

        # Output
        out_grp = QGroupBox("Output")
        ol = QVBoxLayout()
        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Filename"))
        self._txt_output = QLineEdit("drums.mid")
        r3.addWidget(self._txt_output)
        ol.addLayout(r3)
        out_grp.setLayout(ol)
        controls.addWidget(out_grp)

        controls.addStretch()
        root.addLayout(controls)

        # --- Step grid in scroll area ---
        self._grid_widget = StepGridWidget()
        scroll = QScrollArea()
        scroll.setWidget(self._grid_widget)
        scroll.setWidgetResizable(False)
        scroll.setMinimumHeight(180)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        root.addWidget(scroll, 1)

        # --- Info label ---
        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet("color: #aaa;")
        root.addWidget(self._lbl_info)

        # --- Bottom buttons ---
        bottom = QHBoxLayout()
        self._btn_load_pattern = QPushButton("Load Pattern")
        self._btn_load_pattern.setEnabled(False)
        self._btn_preview = QPushButton("Preview")
        self._btn_preview.setEnabled(False)
        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setEnabled(False)
        self._btn_export = QPushButton("Export MIDI")
        self._btn_export.setEnabled(False)
        self._btn_export.setStyleSheet("font-weight: bold;")

        bottom.addWidget(self._btn_load_pattern)
        bottom.addWidget(self._btn_preview)
        bottom.addWidget(self._btn_stop)
        bottom.addStretch()
        bottom.addWidget(self._btn_export)
        root.addLayout(bottom)

        self.setStatusBar(QStatusBar())

    def _connect_signals(self):
        self._btn_open.clicked.connect(self._open_chopmap)
        self._btn_load_pattern.clicked.connect(self._load_selected_pattern)
        self._btn_preview.clicked.connect(self._preview_pattern)
        self._btn_stop.clicked.connect(self._stop_preview)
        self._btn_export.clicked.connect(self._export_midi)
        self._combo_preset.currentIndexChanged.connect(self._on_preset_changed)

    # ------------------------------------------------------------------
    # Chopmap loading
    # ------------------------------------------------------------------

    def _open_chopmap(self):
        # Default to ChopShop sounds directory
        start_dir = str(Path.home() / "Library/Audio/Sounds/ChopShop")
        if not Path(start_dir).exists():
            start_dir = ""

        path, _ = QFileDialog.getOpenFileName(
            self, "Open Chopmap", start_dir,
            "Chopmap Files (*.chopmap.json);;JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return

        try:
            self._chopmap = load_chopmap(path)
            self._chopmap_path = Path(path)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            return

        self._label_map = build_label_map(self._chopmap)
        name = self._chopmap.get("name", self._chopmap_path.stem)
        n_slices = self._chopmap.get("num_slices", 0)
        labels = sorted(set(s.get("label", "") for s in self._chopmap.get("slices", []) if s.get("label")))

        self._lbl_file.setText(f"{name}  —  {n_slices} slices  —  labels: {', '.join(labels)}")
        self._lbl_file.setStyleSheet("color: #eee;")

        self._txt_output.setText(f"{name}_drums.mid")

        # Load audio files for preview
        self._load_audio_cache()

        self._btn_load_pattern.setEnabled(True)
        self._btn_export.setEnabled(False)
        self._btn_preview.setEnabled(False)

        # Auto-load the selected pattern
        self._load_selected_pattern()
        self.statusBar().showMessage("Chopmap loaded.", 3000)

    def _load_audio_cache(self):
        """Load the chopped WAV files for playback preview."""
        self._audio_cache = {}
        if self._chopmap is None or self._chopmap_path is None:
            return
        audio_dir = self._chopmap_path.parent
        try:
            import soundfile as sf
        except ImportError:
            return
        for s in self._chopmap.get("slices", []):
            note = s.get("midi_note")
            fname = s.get("file", "")
            if note is None or not fname:
                continue
            fpath = audio_dir / fname
            if fpath.exists():
                try:
                    data, sr = sf.read(str(fpath), dtype="float32")
                    if data.ndim > 1:
                        data = data.mean(axis=1)
                    self._audio_cache[note] = data
                    self._sr = sr
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Pattern loading
    # ------------------------------------------------------------------

    def _on_preset_changed(self, index: int):
        pass  # Just tracks selection; load happens on button click

    def _load_selected_pattern(self):
        if self._chopmap is None:
            return
        preset_key = self._combo_preset.currentData()
        if preset_key == "__file__":
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Pattern File", "",
                "JSON Files (*.json);;All Files (*)",
            )
            if not path:
                return
            try:
                self._pattern = load_pattern(path)
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))
                return
        else:
            try:
                self._pattern = load_pattern(preset_key)
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))
                return

        self._build_grid_from_pattern()
        self._btn_export.setEnabled(True)
        self._btn_preview.setEnabled(True)
        self.statusBar().showMessage(f"Pattern loaded: {self._pattern.get('name', '?')}", 3000)

    def _build_grid_from_pattern(self):
        """Convert pattern JSON into the step grid visual."""
        if self._pattern is None or self._chopmap is None:
            return

        resolution = self._pattern.get("resolution", 16)
        time_sig = self._pattern.get("time_signature", [4, 4])
        pattern_bars = self._pattern.get("bars", 1)
        steps_per_bar = time_sig[0] * (resolution // time_sig[1])

        # Use the bar count from the spinner
        display_bars = self._spin_bars.value()

        # Collect all unique labels used in the pattern that exist in chopmap
        all_labels = []
        for track in self._pattern.get("tracks", []):
            for step in track.get("steps", []):
                label = step["label"]
                if label in self._label_map and label not in all_labels:
                    all_labels.append(label)

        if not all_labels:
            QMessageBox.warning(
                self, "No Matching Labels",
                "None of the labels in this pattern match your chopmap.\n"
                f"Pattern needs: {sorted(set(s['label'] for t in self._pattern.get('tracks', []) for s in t.get('steps', [])))}\n"
                f"Chopmap has: {sorted(self._label_map.keys())}",
            )
            return

        # Build grid: (row_index, step_position) -> velocity
        grid: dict[tuple[int, int], int] = {}
        total_steps = steps_per_bar * display_bars
        pattern_steps = steps_per_bar * pattern_bars

        for track in self._pattern.get("tracks", []):
            for step in track.get("steps", []):
                label = step["label"]
                if label not in all_labels:
                    continue
                row = all_labels.index(label)
                vel = step.get("velocity", 100)
                pos = step["pos"]

                # Tile across display bars
                for bar_rep in range(display_bars):
                    actual_pos = bar_rep * pattern_steps + pos
                    if actual_pos < total_steps:
                        grid[(row, actual_pos)] = vel

        # Update BPM from pattern if not already set
        if self._pattern.get("bpm"):
            self._spin_bpm.setValue(self._pattern["bpm"])

        label_colors = {l: LABEL_COLORS.get(l, DEFAULT_LABEL_COLOR) for l in all_labels}
        self._grid_widget.set_pattern(all_labels, steps_per_bar, display_bars, grid, label_colors)

        self._lbl_info.setText(
            f"Pattern: {self._pattern.get('name', '?')}  |  "
            f"{len(all_labels)} voices  |  "
            f"{sum(1 for _ in grid)} hits across {display_bars} bars"
        )

    # ------------------------------------------------------------------
    # Preview playback
    # ------------------------------------------------------------------

    def _preview_pattern(self):
        """Play back the pattern using the cached audio slices."""
        if not self._audio_cache or self._chopmap is None:
            self.statusBar().showMessage("No audio files loaded for preview.", 3000)
            return

        grid = self._grid_widget.get_grid()
        labels = self._grid_widget._labels
        if not grid or not labels:
            return

        bpm = self._spin_bpm.value()
        resolution = self._pattern.get("resolution", 16) if self._pattern else 16
        time_sig = self._pattern.get("time_signature", [4, 4]) if self._pattern else [4, 4]

        # Seconds per step
        beats_per_sec = bpm / 60
        steps_per_beat = resolution / time_sig[1]
        sec_per_step = 1.0 / (beats_per_sec * steps_per_beat)

        # Find total steps
        max_step = max(s for (_, s) in grid.keys()) + 1 if grid else 0
        total_duration = max_step * sec_per_step + 0.5  # add tail

        # Mix down to a single buffer
        total_samples = int(total_duration * self._sr)
        mix = np.zeros(total_samples, dtype=np.float32)

        for (row, step), vel in grid.items():
            if row >= len(labels):
                continue
            label = labels[row]
            note = self._label_map.get(label)
            if note is None or note not in self._audio_cache:
                continue
            sample = self._audio_cache[note]
            offset = int(step * sec_per_step * self._sr)
            gain = vel / 127.0
            end = min(offset + len(sample), total_samples)
            chunk_len = end - offset
            if chunk_len > 0:
                mix[offset:end] += sample[:chunk_len] * gain

        # Normalize to prevent clipping
        peak = np.abs(mix).max()
        if peak > 0.9:
            mix = mix * (0.9 / peak)

        sd.stop()
        sd.play(mix, self._sr)
        self._btn_stop.setEnabled(True)
        self.statusBar().showMessage("Playing preview...", int(total_duration * 1000))

    def _stop_preview(self):
        sd.stop()
        self._btn_stop.setEnabled(False)
        self.statusBar().showMessage("Stopped.", 2000)

    # ------------------------------------------------------------------
    # MIDI export
    # ------------------------------------------------------------------

    def _export_midi(self):
        if self._chopmap is None:
            return

        # Rebuild pattern from the grid (in case user toggled cells)
        grid = self._grid_widget.get_grid()
        labels = self._grid_widget._labels
        resolution = self._pattern.get("resolution", 16) if self._pattern else 16
        time_sig = self._pattern.get("time_signature", [4, 4]) if self._pattern else [4, 4]
        bars = self._spin_bars.value()
        bpm = self._spin_bpm.value()

        # Convert grid back to pattern format
        steps = []
        for (row, step_pos), vel in sorted(grid.items()):
            if row >= len(labels):
                continue
            steps.append({
                "pos": step_pos,
                "label": labels[row],
                "velocity": vel,
            })

        pattern = {
            "name": self._pattern.get("name", "Custom") if self._pattern else "Custom",
            "bpm": bpm,
            "bars": bars,
            "time_signature": time_sig,
            "resolution": resolution,
            "tracks": [{"name": "drums", "channel": 9, "steps": steps}],
        }

        output_name = self._txt_output.text().strip() or "drums.mid"
        if not output_name.endswith(".mid"):
            output_name += ".mid"

        # Ask where to save
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save MIDI File", output_name,
            "MIDI Files (*.mid);;All Files (*)",
        )
        if not save_path:
            return

        try:
            out = generate_midi(
                chopmap=self._chopmap,
                pattern=pattern,
                bpm=bpm,
                bars=bars,
                output=save_path,
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            return

        QMessageBox.information(
            self, "MIDI Exported",
            f"Saved: {out}\n"
            f"BPM: {bpm}  |  Bars: {bars}  |  Hits: {len(steps)}\n\n"
            f"Drag this .mid file onto a GarageBand track.",
        )
        self.statusBar().showMessage(f"MIDI saved: {out}", 5000)
