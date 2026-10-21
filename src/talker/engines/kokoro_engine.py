"""Kokoro-82M: small, fast, natural-sounding. Runs well on CPU.

Kokoro has no emotion model, so moods come through speed, pitch, energy and
pauses. Emphasis maps to Kokoro's stress markup, ``[word](+2)``.
"""

from __future__ import annotations

import importlib.util

import numpy as np

from talker.engines.base import Capabilities, Engine
from talker.markup import Sentence
from talker.moods import Mood

# First letter of a voice id is its language: a = US English, b = UK English.
VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_nova",
    "am_michael", "am_fenrir", "am_puck", "am_adam",
    "bf_emma", "bf_isabella", "bm_george", "bm_fable", "bm_lewis",
]


class KokoroEngine(Engine):
    name = "kokoro"
    label = "Kokoro (fast, CPU-friendly)"
    sample_rate = 24000
    capabilities = Capabilities(emphasis=True)

    def __init__(self, device: str | None = None):
        self.device = device
        self._pipelines: dict[str, object] = {}

    @classmethod
    def available(cls) -> tuple[bool, str]:
        if importlib.util.find_spec("kokoro") is None:
            return False, 'not installed: pip install "talker[kokoro]"'
        return True, ""

    def prefetch(self) -> None:
        from huggingface_hub import snapshot_download

        snapshot_download("hexgrad/Kokoro-82M")
        for lang in sorted({v[0] for v in VOICES}):
            self._pipeline(lang)  # also fetches the English G2P language model

    def voices(self) -> list[str]:
        return list(VOICES)

    def default_voice(self) -> str:
        return "af_heart"

    def _pipeline(self, lang: str):
        if lang not in self._pipelines:
            from kokoro import KPipeline

            self._pipelines[lang] = KPipeline(lang_code=lang, device=self.device)
        return self._pipelines[lang]

    @staticmethod
    def to_kokoro_text(sentence: Sentence) -> str:
        out = []
        for run in sentence.runs:
            if run.emphasis:
                out.append(" ".join(f"[{w}](+2)" for w in run.text.split()))
            else:
                out.append(run.text)
        return "".join(out)

    def synthesize(self, sentence: Sentence, voice: str, mood: Mood, speed: float,
                   expressiveness: float) -> np.ndarray:
        pipeline = self._pipeline(voice[0])
        chunks = [
            np.asarray(r.audio, dtype=np.float32)
            for r in pipeline(self.to_kokoro_text(sentence), voice=voice, speed=speed, split_pattern=None)
            if r.audio is not None
        ]
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
