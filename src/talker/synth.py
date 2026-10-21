"""The synthesis pipeline shared by the CLI and the GUI.

text -> markup.parse -> per-sentence engine call -> prosody post-processing
(time-stretch, pitch, energy) -> sentence gaps and pauses -> one Audio clip.
"""

from __future__ import annotations

import logging
import random
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from talker import markup
from talker.engines import ENGINES, Engine
from talker.moods import get_mood
from talker.settings import VoiceSettings

log = logging.getLogger(__name__)

SENTENCE_GAP = 0.25  # seconds, before mood and pause_scale
FADE = 0.005  # seconds of fade at each sentence edge to avoid clicks

Progress = Callable[[int, int], None]


class Cancelled(Exception):
    pass


@dataclass
class Audio:
    samples: np.ndarray  # mono float32 in [-1, 1]
    sample_rate: int

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate

    def save(self, path: str | Path) -> Path:
        import soundfile as sf

        path = Path(path)
        sf.write(str(path), self.samples, self.sample_rate)
        return path

    def play(self, blocking: bool = True) -> None:
        import sounddevice as sd

        sd.play(self.samples, self.sample_rate)
        if blocking:
            sd.wait()

    @staticmethod
    def stop() -> None:
        try:
            import sounddevice as sd
        except OSError:  # no audio backend, so nothing can be playing
            return
        sd.stop()


def _librosa():
    try:
        import librosa

        return librosa
    except ImportError:
        return None


def shift_pitch(y: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    if abs(semitones) < 0.05 or len(y) == 0:
        return y
    lr = _librosa()
    if lr is None:
        log.warning("Pitch change needs librosa (pip install librosa); skipping.")
        return y
    return lr.effects.pitch_shift(y, sr=sr, n_steps=semitones).astype(np.float32)


def stretch(y: np.ndarray, rate: float) -> np.ndarray:
    if abs(rate - 1.0) < 0.01 or len(y) == 0:
        return y
    lr = _librosa()
    if lr is None:
        log.warning("Speed change for this engine needs librosa (pip install librosa); skipping.")
        return y
    return lr.effects.time_stretch(y, rate=rate).astype(np.float32)


def _fade(y: np.ndarray, sr: int) -> np.ndarray:
    n = min(int(sr * FADE), len(y) // 2)
    if n > 0:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        y = y.copy()
        y[:n] *= ramp
        y[-n:] *= ramp[::-1]
    return y


class Synthesizer:
    """Holds loaded engines so models are only loaded once per process."""

    def __init__(self, device: str | None = None):
        self.device = device
        self._engines: dict[str, Engine] = {}
        self._lock = threading.Lock()

    def engine(self, name: str) -> Engine:
        if name not in ENGINES:
            raise ValueError(f"Unknown engine {name!r}. Choose from: {', '.join(ENGINES)}")
        if name not in self._engines:
            cls = ENGINES[name]
            ok, why = cls.available()
            if not ok:
                raise RuntimeError(f"Engine {name!r} is {why}")
            self._engines[name] = cls(device=self.device)
        return self._engines[name]

    def synthesize(
        self,
        text: str,
        settings: VoiceSettings,
        progress: Progress | None = None,
        cancel: threading.Event | None = None,
    ) -> Audio:
        script = markup.parse(text)
        if not script.sentences:
            raise ValueError("Nothing to say: the text has no words.")
        with self._lock:
            return self._run(script, settings, progress, cancel)

    def _run(self, script, settings, progress, cancel) -> Audio:
        if settings.seed is not None:
            _seed(settings.seed)
        engine = self.engine(settings.engine)
        voice = settings.voice or engine.default_voice()
        caps = engine.capabilities
        pieces: list[np.ndarray] = []
        total = len(script.sentences)
        done = 0
        prev_was_sentence = False
        sr = engine.sample_rate
        for item in script.items:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            if isinstance(item, markup.Pause):
                pieces.append(np.zeros(int(sr * item.seconds), dtype=np.float32))
                prev_was_sentence = False
                continue
            mood = get_mood(item.mood or settings.mood).scaled(settings.intensity)
            speed = max(0.3, min(3.0, mood.speed * settings.speed))
            y = engine.synthesize(item, voice, mood, speed if caps.speed else 1.0,
                                  settings.expressiveness)
            sr = engine.sample_rate  # some engines only know it after loading
            if not caps.speed:
                y = stretch(y, speed)
            y = shift_pitch(y, sr, mood.pitch + settings.pitch)
            y = _fade(y * (mood.energy * settings.energy), sr)
            if prev_was_sentence:
                gap = SENTENCE_GAP * mood.pause * settings.pause_scale
                pieces.append(np.zeros(int(sr * gap), dtype=np.float32))
            pieces.append(y.astype(np.float32))
            prev_was_sentence = True
            done += 1
            if progress:
                progress(done, total)
        out = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        peak = float(np.max(np.abs(out))) if len(out) else 0.0
        if peak > 0.98:
            out = out * (0.98 / peak)
        return Audio(out.astype(np.float32), sr)


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass
