import numpy as np
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush
from PySide6.QtWidgets import QWidget


# Alternate colours for adjacent slices
SLICE_COLORS = [
    QColor(65, 105, 225, 50),   # royal blue
    QColor(50, 205, 50, 50),    # lime green
]

WAVEFORM_COLOR = QColor(30, 144, 255)
MARKER_COLOR = QColor(255, 80, 80)
MARKER_HOVER_COLOR = QColor(255, 40, 40)
PLAYHEAD_COLOR = QColor(255, 165, 0)
BG_COLOR = QColor(28, 28, 30)
GRID_COLOR = QColor(255, 255, 255, 25)


class WaveformWidget(QWidget):
    """Draws an audio waveform with draggable vertical slice markers."""

    markers_changed = Signal()       # emitted when user drags a marker
    slice_clicked = Signal(int)      # emitted when user clicks inside a slice region

    MARKER_HIT_PX = 6               # grab zone half-width in pixels

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setMouseTracking(True)

        # Audio data
        self._y: np.ndarray | None = None
        self._sr: int = 44100
        self._duration: float = 0.0

        # Downsampled waveform envelope for drawing (min/max per pixel column)
        self._envelope_min: np.ndarray | None = None
        self._envelope_max: np.ndarray | None = None

        # Slice markers as sample positions (always sorted).
        # The first marker is always 0 and is not draggable.
        self._markers: list[int] = []

        # Interaction state
        self._dragging_idx: int | None = None
        self._hover_idx: int | None = None

        # Playhead position (sample index, -1 = hidden)
        self._playhead: int = -1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_audio(self, y: np.ndarray, sr: int):
        self._y = y
        self._sr = sr
        self._duration = len(y) / sr
        self._rebuild_envelope()
        self.update()

    def set_markers(self, sample_positions: list[int]):
        self._markers = sorted(sample_positions)
        self.update()

    def get_markers(self) -> list[int]:
        return list(self._markers)

    def set_playhead(self, sample: int):
        self._playhead = sample
        self.update()

    def clear(self):
        self._y = None
        self._envelope_min = None
        self._envelope_max = None
        self._markers = []
        self._playhead = -1
        self.update()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _sample_to_x(self, sample: int) -> float:
        if self._y is None or len(self._y) == 0:
            return 0.0
        return sample / len(self._y) * self.width()

    def _x_to_sample(self, x: float) -> int:
        if self._y is None or len(self._y) == 0:
            return 0
        s = int(x / self.width() * len(self._y))
        return max(0, min(s, len(self._y)))

    # ------------------------------------------------------------------
    # Envelope for fast drawing
    # ------------------------------------------------------------------

    def _rebuild_envelope(self):
        if self._y is None or len(self._y) == 0:
            self._envelope_min = None
            self._envelope_max = None
            return
        w = max(self.width(), 1)
        chunk = max(len(self._y) // w, 1)
        n_cols = len(self._y) // chunk
        trimmed = self._y[:n_cols * chunk].reshape(n_cols, chunk)
        self._envelope_min = trimmed.min(axis=1)
        self._envelope_max = trimmed.max(axis=1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rebuild_envelope()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mid = h / 2

        # Background
        p.fillRect(self.rect(), BG_COLOR)

        if self._envelope_min is None or self._envelope_max is None:
            p.setPen(QColor(120, 120, 120))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Drop or open a WAV file")
            p.end()
            return

        n = len(self._envelope_min)

        # Slice region fills
        total = len(self._y) if self._y is not None else 1
        ends = list(self._markers) + [total]
        for i in range(len(self._markers)):
            x0 = self._sample_to_x(ends[i])
            x1 = self._sample_to_x(ends[i + 1])
            color = SLICE_COLORS[i % len(SLICE_COLORS)]
            p.fillRect(int(x0), 0, int(x1 - x0), h, color)

        # Waveform
        pen = QPen(WAVEFORM_COLOR, 1)
        p.setPen(pen)
        x_scale = w / n if n > 0 else 1
        for i in range(n):
            x = i * x_scale
            y_min = mid - self._envelope_max[i] * mid
            y_max = mid - self._envelope_min[i] * mid
            p.drawLine(QPointF(x, y_min), QPointF(x, y_max))

        # Markers
        for i, s in enumerate(self._markers):
            x = self._sample_to_x(s)
            is_hover = (i == self._hover_idx)
            color = MARKER_HOVER_COLOR if is_hover else MARKER_COLOR
            pen_w = 2 if is_hover else 1
            p.setPen(QPen(color, pen_w))
            p.drawLine(QPointF(x, 0), QPointF(x, h))
            # Draw small handle at top
            if i > 0:  # first marker (0) is not draggable
                p.setBrush(QBrush(color))
                p.drawRect(int(x - 4), 0, 8, 10)
                p.setBrush(Qt.BrushStyle.NoBrush)

        # Playhead
        if self._playhead >= 0:
            x = self._sample_to_x(self._playhead)
            p.setPen(QPen(PLAYHEAD_COLOR, 2))
            p.drawLine(QPointF(x, 0), QPointF(x, h))

        # Time axis labels
        p.setPen(QColor(180, 180, 180))
        if self._duration > 0:
            step = _nice_time_step(self._duration, w)
            t = 0.0
            while t <= self._duration:
                x = t / self._duration * w
                p.drawLine(QPointF(x, h - 12), QPointF(x, h))
                label = f"{t:.1f}s" if self._duration < 10 else f"{t:.0f}s"
                p.drawText(int(x + 2), h - 2, label)
                t += step

        p.end()

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def _marker_at_x(self, x: float) -> int | None:
        for i, s in enumerate(self._markers):
            if i == 0:
                continue  # first marker not draggable
            mx = self._sample_to_x(s)
            if abs(x - mx) <= self.MARKER_HIT_PX:
                return i
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._marker_at_x(event.position().x())
        if idx is not None:
            self._dragging_idx = idx
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            # Click inside a slice region — find which slice
            sample = self._x_to_sample(event.position().x())
            for i in range(len(self._markers)):
                end = self._markers[i + 1] if i + 1 < len(self._markers) else (len(self._y) if self._y is not None else 0)
                if self._markers[i] <= sample < end:
                    self.slice_clicked.emit(i)
                    break

    def mouseMoveEvent(self, event):
        x = event.position().x()
        if self._dragging_idx is not None:
            new_sample = self._x_to_sample(x)
            # Clamp between neighbours
            prev = self._markers[self._dragging_idx - 1] + 1
            nxt = (self._markers[self._dragging_idx + 1] - 1
                   if self._dragging_idx + 1 < len(self._markers)
                   else (len(self._y) - 1 if self._y is not None else 1))
            new_sample = max(prev, min(new_sample, nxt))
            self._markers[self._dragging_idx] = new_sample
            self.update()
        else:
            idx = self._marker_at_x(x)
            if idx != self._hover_idx:
                self._hover_idx = idx
                self.setCursor(Qt.CursorShape.SizeHorCursor if idx is not None else Qt.CursorShape.ArrowCursor)
                self.update()

    def mouseReleaseEvent(self, event):
        if self._dragging_idx is not None:
            self._dragging_idx = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.markers_changed.emit()


def _nice_time_step(duration: float, width_px: int) -> float:
    """Choose a human-friendly time step for axis labels."""
    target_labels = max(width_px // 80, 2)
    raw = duration / target_labels
    for step in [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]:
        if step >= raw:
            return step
    return 60.0
