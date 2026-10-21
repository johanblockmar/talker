"""Desktop app (PySide6). A thin front end over talker.synth.Synthesizer."""

from __future__ import annotations

import sys
import threading
import traceback

from PySide6.QtCore import QObject, QSettings, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

from talker.engines import ENGINES
from talker.moods import MOODS
from talker.settings import VoiceSettings
from talker.synth import Audio, Cancelled, Synthesizer

PLACEHOLDER = (
    "Type or paste text here.\n\n"
    "Optional markup: *emphasis*, [pause 500ms], [mood happy] ... [mood]"
)


class Worker(QObject):
    progress = Signal(int, int)
    finished = Signal(object)  # Audio
    failed = Signal(str)

    def __init__(self, synth: Synthesizer, text: str, settings: VoiceSettings):
        super().__init__()
        self.synth, self.text, self.settings = synth, text, settings
        self.cancel = threading.Event()

    def run(self) -> None:
        try:
            audio = self.synth.synthesize(self.text, self.settings,
                                          progress=self.progress.emit, cancel=self.cancel)
            self.finished.emit(audio)
        except Cancelled:
            self.failed.emit("")
        except Exception as e:  # shown to the user, not swallowed
            traceback.print_exc()
            self.failed.emit(str(e))


class Slider(QWidget):
    """A horizontal slider over a float range with a live value label."""

    def __init__(self, lo: float, hi: float, value: float, step: float, fmt: str = "{:.2f}"):
        super().__init__()
        self.lo, self.step, self.fmt = lo, step, fmt
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, round((hi - lo) / step))
        self.label = QLabel()
        self.label.setMinimumWidth(48)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.slider)
        row.addWidget(self.label)
        self.slider.valueChanged.connect(self._update)
        self.set(value)

    def value(self) -> float:
        return round(self.lo + self.slider.value() * self.step, 4)

    def set(self, v: float) -> None:
        self.slider.setValue(round((v - self.lo) / self.step))
        self._update()

    def _update(self) -> None:
        self.label.setText(self.fmt.format(self.value()))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Talker")
        self.resize(820, 600)
        self.synth = Synthesizer()
        self.audio: Audio | None = None
        self.audio_key: tuple | None = None  # (text, settings) that produced self.audio
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self.play_after = False
        self.store = QSettings("Talker", "Talker")

        self.text = QPlainTextEdit()
        self.text.setPlaceholderText(PLACEHOLDER)

        self.engine = QComboBox()
        for name, cls in ENGINES.items():
            ok, why = cls.available()
            self.engine.addItem(cls.label + ("" if ok else f" ({why.split(':')[0]})"), name)
        self.voice = QComboBox()
        self.voice.setEditable(True)  # also accepts a path to a .wav for cloning engines
        self.mood = QComboBox()
        for m in MOODS.values():
            self.mood.addItem(m.name.capitalize(), m.name)
            self.mood.setItemData(self.mood.count() - 1, m.description, Qt.ToolTipRole)

        self.intensity = Slider(0, 1, 0.5, 0.05)
        self.expressiveness = Slider(0, 1, 0.5, 0.05)
        self.speed = Slider(0.5, 2.0, 1.0, 0.05, "{:.2f}x")
        self.pitch = Slider(-6, 6, 0, 0.5, "{:+.1f} st")
        self.energy = Slider(0.3, 1.6, 1.0, 0.05, "{:.2f}x")
        self.pauses = Slider(0.2, 3.0, 1.0, 0.1, "{:.1f}x")
        self.caps_note = QLabel()
        self.caps_note.setWordWrap(True)
        self.caps_note.setStyleSheet("color: gray")

        voice_box = QGroupBox("Voice")
        vf = QFormLayout(voice_box)
        vf.addRow("Engine", self.engine)
        vf.addRow("Voice", self.voice)
        vf.addRow(self.caps_note)

        mood_box = QGroupBox("Mood and inflection")
        mf = QFormLayout(mood_box)
        mf.addRow("Mood", self.mood)
        mf.addRow("Intensity", self.intensity)
        mf.addRow("Expressiveness", self.expressiveness)
        mf.addRow("Speed", self.speed)
        mf.addRow("Pitch", self.pitch)
        mf.addRow("Energy", self.energy)
        mf.addRow("Pauses", self.pauses)

        self.speak_btn = QPushButton("Speak")
        self.speak_btn.setDefault(True)
        self.stop_btn = QPushButton("Stop")
        self.save_btn = QPushButton("Save audio...")
        self.reset_btn = QPushButton("Reset sliders")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.status = QLabel("Ready")

        buttons = QHBoxLayout()
        for b in (self.speak_btn, self.stop_btn, self.save_btn, self.reset_btn):
            buttons.addWidget(b)
        buttons.addStretch()

        side = QVBoxLayout()
        side.addWidget(voice_box)
        side.addWidget(mood_box)
        side.addStretch()
        top = QHBoxLayout()
        top.addWidget(self.text, 3)
        top.addLayout(side, 2)
        root = QVBoxLayout()
        root.addLayout(top)
        root.addLayout(buttons)
        root.addWidget(self.progress)
        root.addWidget(self.status)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        self.engine.currentIndexChanged.connect(self._engine_changed)
        self.speak_btn.clicked.connect(lambda: self._synthesize(play=True))
        self.stop_btn.clicked.connect(self._stop)
        self.save_btn.clicked.connect(self._save)
        self.reset_btn.clicked.connect(self._reset)
        self._restore()

    # settings <-> widgets
    def settings(self) -> VoiceSettings:
        return VoiceSettings(
            engine=self.engine.currentData(),
            voice=self.voice.currentText().strip() or None,
            mood=self.mood.currentData(),
            intensity=self.intensity.value(),
            expressiveness=self.expressiveness.value(),
            speed=self.speed.value(),
            pitch=self.pitch.value(),
            energy=self.energy.value(),
            pause_scale=self.pauses.value(),
        )

    def _apply(self, s: VoiceSettings) -> None:
        i = self.engine.findData(s.engine)
        self.engine.setCurrentIndex(max(i, 0))
        self._engine_changed()
        if s.voice:
            self.voice.setCurrentText(s.voice)
        self.mood.setCurrentIndex(max(self.mood.findData(s.mood), 0))
        self.intensity.set(s.intensity)
        self.expressiveness.set(s.expressiveness)
        self.speed.set(s.speed)
        self.pitch.set(s.pitch)
        self.energy.set(s.energy)
        self.pauses.set(s.pause_scale)

    def _restore(self) -> None:
        data = self.store.value("settings")
        s = VoiceSettings.from_dict(data) if isinstance(data, dict) else VoiceSettings()
        if not ENGINES.get(s.engine, ENGINES["tone"]).available()[0]:
            s.engine = next((n for n, c in ENGINES.items() if c.available()[0]), "tone")
        self._apply(s)
        self.text.setPlainText(self.store.value("text", "") or "")

    def _reset(self) -> None:
        cur = self.settings()
        d = VoiceSettings(engine=cur.engine, voice=cur.voice, mood=cur.mood)
        self._apply(d)

    def _engine_changed(self) -> None:
        cls = ENGINES[self.engine.currentData()]
        engine = cls()
        self.voice.clear()
        self.voice.addItems(engine.voices())
        self.voice.setCurrentText(engine.default_voice())
        caps = cls.capabilities
        self.expressiveness.setEnabled(caps.expressiveness)
        notes = []
        notes.append("Real emotion model." if caps.emotion else
                     "Mood is shaped by speed, pitch, energy and pauses.")
        if caps.voice_cloning:
            notes.append("Voice can be a path to a 5 to 15 s .wav clip.")
        if caps.emphasis:
            notes.append("Supports *emphasis*.")
        self.caps_note.setText(" ".join(notes))

    # actions
    def _key(self) -> tuple:
        return self.text.toPlainText(), tuple(sorted(self.settings().to_dict().items()))

    def _busy(self, busy: bool) -> None:
        self.speak_btn.setEnabled(not busy)
        self.save_btn.setEnabled(not busy)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)

    def _synthesize(self, play: bool) -> None:
        text = self.text.toPlainText()
        if not text.strip():
            self.status.setText("Type some text first.")
            return
        self.play_after = play
        self.status.setText("Loading model and synthesizing... (first run downloads the model)")
        self._busy(True)
        self.thread = QThread()
        self.pending_key = self._key()
        self.worker = Worker(self.synth, text, self.settings())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.start()

    def _on_progress(self, done: int, total: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.status.setText(f"Sentence {done} of {total}")

    def _on_done(self, audio: Audio) -> None:
        self._busy(False)
        self.audio, self.audio_key = audio, self.pending_key
        self.status.setText(f"Done: {audio.duration:.1f} s")
        if self.play_after:
            try:
                audio.play(blocking=False)
            except OSError as e:
                QMessageBox.warning(self, "Talker", f"Could not play audio: {e}\nYou can still save it.")
        else:
            self._save()

    def _on_failed(self, message: str) -> None:
        self._busy(False)
        self.status.setText("Stopped." if not message else "Failed.")
        if message:
            QMessageBox.warning(self, "Talker", message)

    def _stop(self) -> None:
        if self.worker is not None:
            self.worker.cancel.set()
        Audio.stop()

    def _save(self) -> None:
        if self.audio is None or self.audio_key != self._key():
            self._synthesize(play=False)
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save audio", "speech.wav",
                                              "WAV (*.wav);;FLAC (*.flac);;OGG (*.ogg)")
        if path:
            self.audio.save(path)
            self.status.setText(f"Saved {path}")

    def closeEvent(self, event) -> None:
        self.store.setValue("settings", self.settings().to_dict())
        self.store.setValue("text", self.text.toPlainText())
        self._stop()
        if self.thread is not None and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(3000)
        super().closeEvent(event)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Talker")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
