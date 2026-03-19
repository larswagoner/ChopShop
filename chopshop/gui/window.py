import time
from pathlib import Path

import librosa
import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..analysis import Slice, SliceMap, analyze
from ..cli import note_name
from ..constants import (
    DEFAULT_CHOP_ROOT,
    DEFAULT_CUE_ROOT,
    DEFAULT_GRID_RESOLUTION,
    DEFAULT_MODE,
    DEFAULT_THRESHOLD,
    GRID_SUBDIVISIONS,
    MIDI_NOTE_NAMES,
    MIDI_NOTES,
)
from ..chopmap import export_chopmap
from ..export import export_slices
from ..files import install_preset, resolve_audio_dir
from ..labeler import STANDARD_LABELS, auto_label, auto_label_single
from ..preset import generate_preset
from .waveform import WaveformWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChopShop")
        self.setMinimumSize(900, 560)
        self.resize(1100, 640)

        # State
        self._y: np.ndarray | None = None
        self._sr: int = 44100
        self._input_path: Path | None = None
        self._slice_map: SliceMap | None = None
        self._playing: bool = False

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)

        # --- Top bar: file picker ---
        file_row = QHBoxLayout()
        self._btn_open = QPushButton("Open WAV...")
        self._btn_open.setFixedWidth(110)
        self._lbl_file = QLabel("No file loaded")
        self._lbl_file.setStyleSheet("color: #999;")
        file_row.addWidget(self._btn_open)
        file_row.addWidget(self._lbl_file, 1)
        root.addLayout(file_row)

        # --- Waveform ---
        self._waveform = WaveformWidget()
        root.addWidget(self._waveform, 1)

        # --- Slice table ---
        self._btn_toggle_table = QPushButton("Show Slice List")
        self._btn_toggle_table.setCheckable(True)
        self._btn_toggle_table.setFixedWidth(140)
        table_header = QHBoxLayout()
        table_header.addWidget(self._btn_toggle_table)
        self._btn_relabel = QPushButton("Re-label All")
        self._btn_relabel.setFixedWidth(100)
        self._btn_relabel.setEnabled(False)
        table_header.addWidget(self._btn_relabel)
        table_header.addStretch()
        root.addLayout(table_header)

        self._slice_table = QTableWidget(0, 5)
        self._slice_table.setHorizontalHeaderLabels(["#", "Start", "End", "Duration", "Label"])
        self._slice_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._slice_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._slice_table.setMaximumHeight(180)
        self._slice_table.setVisible(False)
        self._slice_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self._slice_table)

        # --- Controls row ---
        controls = QHBoxLayout()

        # Mode
        mode_grp = self._group("Mode")
        ml = QVBoxLayout()
        self._combo_mode = QComboBox()
        self._combo_mode.addItems(["onset", "grid", "equal"])
        ml.addWidget(self._combo_mode)
        mode_grp.setLayout(ml)
        controls.addWidget(mode_grp)

        # Analysis params
        analysis_grp = self._group("Analysis")
        al = QVBoxLayout()

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Threshold"))
        self._spin_threshold = QDoubleSpinBox()
        self._spin_threshold.setRange(0.0, 1.0)
        self._spin_threshold.setSingleStep(0.05)
        self._spin_threshold.setValue(DEFAULT_THRESHOLD)
        r1.addWidget(self._spin_threshold)
        al.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("BPM"))
        self._spin_bpm = QDoubleSpinBox()
        self._spin_bpm.setRange(0.0, 300.0)
        self._spin_bpm.setSpecialValueText("auto")
        self._spin_bpm.setValue(0.0)
        r2.addWidget(self._spin_bpm)
        al.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Grid"))
        self._combo_grid = QComboBox()
        self._combo_grid.addItems(list(GRID_SUBDIVISIONS.keys()))
        self._combo_grid.setCurrentText(DEFAULT_GRID_RESOLUTION)
        r3.addWidget(self._combo_grid)
        al.addLayout(r3)

        r4 = QHBoxLayout()
        r4.addWidget(QLabel("Slices"))
        self._spin_num_slices = QSpinBox()
        self._spin_num_slices.setRange(0, 64)
        self._spin_num_slices.setSpecialValueText("auto")
        self._spin_num_slices.setValue(0)
        r4.addWidget(self._spin_num_slices)
        al.addLayout(r4)

        analysis_grp.setLayout(al)
        controls.addWidget(analysis_grp)

        # MIDI mapping
        midi_grp = self._group("MIDI")
        midl = QVBoxLayout()

        r5 = QHBoxLayout()
        r5.addWidget(QLabel("Chop Root"))
        self._combo_chop_root = QComboBox()
        self._populate_note_combo(self._combo_chop_root, DEFAULT_CHOP_ROOT)
        r5.addWidget(self._combo_chop_root)
        midl.addLayout(r5)

        r6 = QHBoxLayout()
        r6.addWidget(QLabel("Cue Root"))
        self._combo_cue_root = QComboBox()
        self._populate_note_combo(self._combo_cue_root, DEFAULT_CUE_ROOT)
        r6.addWidget(self._combo_cue_root)
        midl.addLayout(r6)

        self._chk_cue_zones = QCheckBox("Cue zones")
        midl.addWidget(self._chk_cue_zones)
        self._chk_no_full = QCheckBox("No full key")
        midl.addWidget(self._chk_no_full)

        midi_grp.setLayout(midl)
        controls.addWidget(midi_grp)

        # Export options
        export_grp = self._group("Export")
        el = QVBoxLayout()

        rn = QHBoxLayout()
        rn.addWidget(QLabel("Name"))
        self._txt_preset_name = QLineEdit()
        self._txt_preset_name.setPlaceholderText("(from filename)")
        rn.addWidget(self._txt_preset_name)
        el.addLayout(rn)

        r7 = QHBoxLayout()
        r7.addWidget(QLabel("Fade (ms)"))
        self._spin_fade = QDoubleSpinBox()
        self._spin_fade.setRange(0.0, 100.0)
        self._spin_fade.setValue(0.0)
        r7.addWidget(self._spin_fade)
        el.addLayout(r7)

        r_sbpm = QHBoxLayout()
        r_sbpm.addWidget(QLabel("Source BPM"))
        self._spin_source_bpm = QDoubleSpinBox()
        self._spin_source_bpm.setRange(0.0, 300.0)
        self._spin_source_bpm.setSpecialValueText("none")
        self._spin_source_bpm.setValue(0.0)
        r_sbpm.addWidget(self._spin_source_bpm)
        el.addLayout(r_sbpm)

        export_grp.setLayout(el)
        controls.addWidget(export_grp)

        root.addLayout(controls)

        # --- Bottom buttons ---
        bottom = QHBoxLayout()
        self._btn_analyze = QPushButton("Analyze")
        self._btn_analyze.setEnabled(False)
        self._btn_play_all = QPushButton("Play All")
        self._btn_play_all.setEnabled(False)
        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setEnabled(False)
        self._btn_generate = QPushButton("Generate Preset")
        self._btn_generate.setEnabled(False)
        self._btn_generate.setStyleSheet("font-weight: bold;")
        self._btn_midi_gui = QPushButton("MIDI Tool")
        self._btn_midi_gui.setToolTip("Open the MIDI pattern generator")

        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet("color: #aaa;")

        bottom.addWidget(self._btn_analyze)
        bottom.addWidget(self._btn_play_all)
        bottom.addWidget(self._btn_stop)
        bottom.addStretch()
        bottom.addWidget(self._lbl_info)
        bottom.addStretch()
        bottom.addWidget(self._btn_generate)
        bottom.addWidget(self._btn_midi_gui)
        root.addLayout(bottom)

        # Status bar
        self.setStatusBar(QStatusBar())

    def _group(self, title: str) -> QGroupBox:
        g = QGroupBox(title)
        g.setMaximumWidth(220)
        return g

    def _populate_note_combo(self, combo: QComboBox, default_midi: int):
        for midi in range(24, 96):
            name = MIDI_NOTE_NAMES.get(midi, str(midi))
            combo.addItem(f"{name} ({midi})", midi)
        idx = combo.findData(default_midi)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self._btn_open.clicked.connect(self._open_file)
        self._btn_analyze.clicked.connect(self._run_analysis)
        self._btn_play_all.clicked.connect(self._play_all_slices)
        self._btn_stop.clicked.connect(self._stop_playback)
        self._btn_generate.clicked.connect(self._generate_preset)
        self._btn_midi_gui.clicked.connect(self._open_midi_gui)
        self._waveform.slice_clicked.connect(self._play_slice)
        self._waveform.markers_changed.connect(self._on_markers_changed)
        self._waveform.marker_added.connect(self._on_marker_added)
        self._waveform.label_changed.connect(self._on_waveform_label_changed)
        self._combo_mode.currentTextChanged.connect(self._on_mode_changed)
        self._btn_toggle_table.toggled.connect(self._toggle_slice_table)
        self._btn_relabel.clicked.connect(self._relabel_all)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "",
            "Audio Files (*.wav *.aif *.aiff *.flac *.mp3);;All Files (*)",
        )
        if not path:
            return
        self._input_path = Path(path)
        self.statusBar().showMessage(f"Loading {self._input_path.name}...")

        try:
            y, sr = librosa.load(str(self._input_path), sr=None, mono=True)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            return

        self._y = y
        self._sr = sr
        self._slice_map = None
        self._txt_preset_name.setText(self._input_path.stem)
        self._lbl_file.setText(f"{self._input_path.name}  ({len(y)/sr:.2f}s, {sr}Hz)")
        self._lbl_file.setStyleSheet("color: #eee;")
        self._waveform.set_audio(y, sr)
        self._waveform.set_markers([])
        self._waveform.set_labels([])
        self._btn_analyze.setEnabled(True)
        self._btn_generate.setEnabled(False)
        self._btn_play_all.setEnabled(False)
        self._btn_relabel.setEnabled(False)
        self._slice_table.setRowCount(0)
        self._lbl_info.setText("")
        self.statusBar().showMessage("File loaded.", 3000)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _on_mode_changed(self, mode: str):
        is_onset = mode == "onset"
        is_grid = mode == "grid"
        is_equal = mode == "equal"
        self._spin_threshold.setEnabled(is_onset)
        self._combo_grid.setEnabled(is_grid or is_onset)
        self._spin_num_slices.setEnabled(is_onset or is_equal)

    def _run_analysis(self):
        if self._y is None:
            return

        mode = self._combo_mode.currentText()
        threshold = self._spin_threshold.value()
        bpm_val = self._spin_bpm.value()
        quantize_bpm = bpm_val if bpm_val > 0 else None
        grid_res = self._combo_grid.currentText()
        num_slices_val = self._spin_num_slices.value()
        num_slices = num_slices_val if num_slices_val > 0 else None

        if mode == "equal" and num_slices is None:
            QMessageBox.warning(self, "Missing Parameter", "Equal mode requires a slice count.")
            return

        self.statusBar().showMessage("Analyzing...")

        try:
            sm = analyze(
                self._y, self._sr,
                source_path=str(self._input_path) if self._input_path else "",
                mode=mode,
                threshold=threshold,
                num_slices=num_slices,
                quantize_bpm=quantize_bpm,
                grid_resolution=grid_res,
            )
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", str(e))
            return

        self._slice_map = sm

        # Auto-label slices
        labels = auto_label(self._y, self._sr, sm.slices)
        for i, s in enumerate(sm.slices):
            s.label = labels[i] if i < len(labels) else ""

        # Update waveform markers and labels
        markers = [s.start_sample for s in sm.slices]
        self._waveform.set_markers(markers)
        self._waveform.set_labels(labels)

        self._btn_generate.setEnabled(True)
        self._btn_play_all.setEnabled(True)
        self._btn_relabel.setEnabled(True)

        bpm_str = f"{sm.bpm:.1f}"
        if quantize_bpm:
            bpm_str += " (user)"
        else:
            bpm_str += " (detected)"
        self._lbl_info.setText(
            f"{len(sm.slices)} slices  |  BPM: {bpm_str}  |  {sm.duration:.2f}s"
        )
        self._rebuild_slice_table()
        self.statusBar().showMessage("Analysis complete.", 3000)

    def _on_markers_changed(self):
        """Rebuild SliceMap from user-dragged markers."""
        if self._y is None:
            return
        markers = self._waveform.get_markers()
        labels = self._waveform.get_labels()
        total = len(self._y)
        slices = []
        for i, start in enumerate(markers):
            end = markers[i + 1] if i + 1 < len(markers) else total
            slices.append(Slice(
                index=i,
                start_sample=int(start),
                end_sample=int(end),
                start_seconds=start / self._sr,
                end_seconds=end / self._sr,
                label=labels[i] if i < len(labels) else "",
            ))
        if self._slice_map is not None:
            self._slice_map.slices = slices
        self._lbl_info.setText(
            f"{len(slices)} slices  |  BPM: {self._slice_map.bpm:.1f if self._slice_map else '?'}  |  markers adjusted"
        )
        self._rebuild_slice_table()

    def _on_marker_added(self, index: int):
        """Auto-label a newly added slice."""
        if self._y is None or self._slice_map is None:
            return
        markers = self._waveform.get_markers()
        total = len(self._y)
        start = markers[index]
        end = markers[index + 1] if index + 1 < len(markers) else total
        label = auto_label_single(self._y, self._sr, start, end)
        # Update waveform labels
        labels = self._waveform.get_labels()
        if index < len(labels):
            labels[index] = label
        self._waveform.set_labels(labels)
        # Rebuild slice map
        self._on_markers_changed()

    def _on_waveform_label_changed(self, index: int, label: str):
        """Handle label change from clicking a pill on the waveform."""
        if self._slice_map is not None and index < len(self._slice_map.slices):
            self._slice_map.slices[index].label = label
        self._rebuild_slice_table()

    # ------------------------------------------------------------------
    # Slice table
    # ------------------------------------------------------------------

    def _toggle_slice_table(self, checked: bool):
        self._slice_table.setVisible(checked)
        self._btn_toggle_table.setText("Hide Slice List" if checked else "Show Slice List")

    def _rebuild_slice_table(self):
        """Rebuild the table from current slice map."""
        self._slice_table.blockSignals(True)
        if self._slice_map is None:
            self._slice_table.setRowCount(0)
            self._slice_table.blockSignals(False)
            return

        slices = self._slice_map.slices
        self._slice_table.setRowCount(len(slices))

        for i, s in enumerate(slices):
            # Index
            item_idx = QTableWidgetItem(str(i))
            item_idx.setFlags(item_idx.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._slice_table.setItem(i, 0, item_idx)
            # Start
            item_start = QTableWidgetItem(f"{s.start_seconds:.3f}s")
            item_start.setFlags(item_start.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._slice_table.setItem(i, 1, item_start)
            # End
            item_end = QTableWidgetItem(f"{s.end_seconds:.3f}s")
            item_end.setFlags(item_end.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._slice_table.setItem(i, 2, item_end)
            # Duration
            dur = s.end_seconds - s.start_seconds
            item_dur = QTableWidgetItem(f"{dur:.3f}s")
            item_dur.setFlags(item_dur.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._slice_table.setItem(i, 3, item_dur)
            # Label combo
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(STANDARD_LABELS)
            if s.label and s.label not in STANDARD_LABELS:
                combo.addItem(s.label)
            combo.setCurrentText(s.label)
            combo.currentTextChanged.connect(lambda text, idx=i: self._on_label_changed(idx, text))
            self._slice_table.setCellWidget(i, 4, combo)

        self._slice_table.blockSignals(False)

    def _on_label_changed(self, index: int, label: str):
        """Handle label change from the table combo box."""
        if self._slice_map is None or index >= len(self._slice_map.slices):
            return
        self._slice_map.slices[index].label = label
        labels = self._waveform.get_labels()
        if index < len(labels):
            labels[index] = label
            self._waveform.set_labels(labels)

    def _relabel_all(self):
        """Re-run auto-labeling on all current slices."""
        if self._y is None or self._slice_map is None:
            return
        labels = auto_label(self._y, self._sr, self._slice_map.slices)
        for i, s in enumerate(self._slice_map.slices):
            s.label = labels[i] if i < len(labels) else ""
        self._waveform.set_labels(labels)
        self._rebuild_slice_table()
        self.statusBar().showMessage("Labels updated.", 3000)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _play_slice(self, index: int):
        if self._y is None or self._slice_map is None:
            return
        if index >= len(self._slice_map.slices):
            return
        s = self._slice_map.slices[index]
        chunk = self._y[s.start_sample:s.end_sample]
        self._start_playback(chunk, s.start_sample)

    def _play_all_slices(self):
        if self._y is None:
            return
        self._start_playback(self._y, 0)

    def _start_playback(self, audio: np.ndarray, offset_sample: int):
        sd.stop()
        self._playing = True
        self._btn_stop.setEnabled(True)
        self._playback_offset = offset_sample
        self._playback_length = len(audio)
        self._playback_start_time = time.monotonic()
        sd.play(audio, self._sr)

        self._playhead_timer = QTimer(self)
        self._playhead_timer.setInterval(30)  # ~33 fps
        self._playhead_timer.timeout.connect(self._update_playhead)
        self._playhead_timer.start()

    def _update_playhead(self):
        if not self._playing:
            return
        elapsed_s = time.monotonic() - self._playback_start_time
        pos = self._playback_offset + int(elapsed_s * self._sr)
        end = self._playback_offset + self._playback_length

        if pos >= end:
            self._stop_playback()
            return
        self._waveform.set_playhead(pos)

    def _stop_playback(self):
        sd.stop()
        self._playing = False
        self._btn_stop.setEnabled(False)
        if hasattr(self, '_playhead_timer') and self._playhead_timer is not None:
            self._playhead_timer.stop()
        self._waveform.set_playhead(-1)

    # ------------------------------------------------------------------
    # Preset generation
    # ------------------------------------------------------------------

    def _generate_preset(self):
        if self._y is None or self._slice_map is None or self._input_path is None:
            return

        source_name = self._input_path.stem
        preset_name = self._txt_preset_name.text().strip() or source_name
        chop_root = self._combo_chop_root.currentData()
        cue_root = self._combo_cue_root.currentData()
        include_full = not self._chk_no_full.isChecked()
        cue_zones = self._chk_cue_zones.isChecked()
        fade_ms = self._spin_fade.value()

        self.statusBar().showMessage("Exporting slices...")

        try:
            audio_dir = resolve_audio_dir(source_name)
            export_result = export_slices(
                self._y, self._sr, self._slice_map, audio_dir, source_name,
                fade_ms=fade_ms,
                cue_zones=cue_zones,
                include_full=include_full,
            )

            preset_bytes = generate_preset(
                export_result, self._slice_map, preset_name,
                chop_root=chop_root,
                cue_root=cue_root,
                include_full_key=include_full,
            )
            preset_path = install_preset(preset_bytes, preset_name)

            # Export chopmap JSON
            source_bpm_val = self._spin_source_bpm.value()
            source_bpm = source_bpm_val if source_bpm_val > 0 else None
            chopmap_path = export_chopmap(
                self._slice_map, export_result, preset_name,
                chop_root=chop_root, source_bpm=source_bpm,
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            return

        n_zones = len(export_result.chop_paths) + len(export_result.cue_paths)
        if include_full and export_result.full_path:
            n_zones += 1

        chop_start = note_name(chop_root)
        chop_end = note_name(chop_root + len(self._slice_map.slices) - 1)

        midi_cmd = f"chopshop-midi --map \"{chopmap_path}\" --preset basic-jungle --bpm 170 --bars 4 -o drums.mid"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Preset Generated")
        msg.setText(
            f"Preset: {preset_path.name}\n"
            f"Chopmap: {chopmap_path.name}\n"
            f"Audio: {audio_dir}\n"
            f"Zones: {n_zones} ({len(export_result.chop_paths)} chops)\n"
            f"Keys: {chop_start} - {chop_end}"
        )
        msg.setInformativeText(
            "Open GarageBand and load the preset from the AUSampler browser."
        )
        msg.setDetailedText(
            f"MIDI generation command:\n{midi_cmd}\n\n"
            f"Chopmap path (for Claude or scripts):\n{chopmap_path}"
        )
        btn_ok = msg.addButton(QMessageBox.StandardButton.Ok)
        btn_copy = msg.addButton("Copy MIDI Command", QMessageBox.ButtonRole.ActionRole)
        btn_copy_path = msg.addButton("Copy Chopmap Path", QMessageBox.ButtonRole.ActionRole)
        msg.exec()

        if msg.clickedButton() == btn_copy:
            QApplication.clipboard().setText(midi_cmd)
            self.statusBar().showMessage("MIDI command copied to clipboard.", 5000)
        elif msg.clickedButton() == btn_copy_path:
            QApplication.clipboard().setText(str(chopmap_path))
            self.statusBar().showMessage("Chopmap path copied to clipboard.", 5000)
        else:
            self.statusBar().showMessage(f"Preset saved: {preset_path}", 5000)

    def _open_midi_gui(self):
        """Launch the MIDI pattern generator window."""
        from .midi_window import MidiWindow
        self._midi_win = MidiWindow()
        self._midi_win.show()
