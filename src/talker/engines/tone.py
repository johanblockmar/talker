"""A dependency-free stand-in engine that beeps once per word.

It exists so the pipeline, CLI and GUI can be tested without downloading a
model. It is not a voice.
"""

from __future__ import annotations

import numpy as np

from talker.engines.base import Capabilities, Engine
from talker.markup import Sentence
from talker.moods import Mood


class ToneEngine(Engine):
    name = "tone"
    label = "Test tones (no model)"
    sample_rate = 16000
    capabilities = Capabilities(emphasis=True, expressiveness=True)

    def voices(self) -> list[str]:
        return ["low", "mid", "high"]

    def default_voice(self) -> str:
        return "mid"

    def synthesize(self, sentence: Sentence, voice: str, mood: Mood, speed: float,
                   expressiveness: float) -> np.ndarray:
        base = {"low": 160.0, "mid": 220.0, "high": 300.0}.get(voice, 220.0)
        word_len = int(self.sample_rate * 0.18 / max(speed, 0.1))
        gap = np.zeros(int(word_len * 0.4), dtype=np.float32)
        t = np.arange(word_len) / self.sample_rate
        env = np.hanning(word_len)
        parts = []
        for i, run in enumerate(sentence.runs):
            for j, _ in enumerate(run.text.split()):
                wobble = 1 + 0.1 * expressiveness * np.sin(i + j)
                amp = 0.5 if run.emphasis else 0.3
                f = base * wobble * (1.25 if run.emphasis else 1.0)
                parts += [(amp * env * np.sin(2 * np.pi * f * t)).astype(np.float32), gap]
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
