"""Chatterbox (Resemble AI, MIT): expressive neural TTS with an emotion knob.

Mood maps to Chatterbox's ``exaggeration`` (emotion intensity), ``cfg_weight``
(pacing/adherence) and ``temperature``. Any short clean recording (5 to 15 s)
can be used as the voice; a folder of per-mood clips gives the strongest
emotion. See ``talker.voices``. Best on an NVIDIA GPU; works on CPU, slowly.
"""

from __future__ import annotations

import importlib.util

import numpy as np

from talker.engines.base import Capabilities, Engine
from talker.markup import Sentence
from talker.moods import Mood
from talker.voices import list_voices, resolve_clip

DEFAULT = "default"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class ChatterboxEngine(Engine):
    name = "chatterbox"
    label = "Chatterbox (expressive, emotion control)"
    capabilities = Capabilities(emotion=True, expressiveness=True, voice_cloning=True, speed=False)

    def __init__(self, device: str | None = None):
        self.device = device
        self._model = None
        self._builtin_conds = None
        self._loaded_clip: str | None = None

    @classmethod
    def available(cls) -> tuple[bool, str]:
        if importlib.util.find_spec("chatterbox") is None:
            return False, 'not installed: pip install "talker[chatterbox]"'
        return True, ""

    def _load(self):
        if self._model is None:
            import torch
            from chatterbox.tts import ChatterboxTTS

            device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            self._model = ChatterboxTTS.from_pretrained(device=device)
            self._builtin_conds = self._model.conds
            self.sample_rate = self._model.sr
        return self._model

    def prefetch(self) -> None:
        self._load()

    def voices(self) -> list[str]:
        return [DEFAULT, *list_voices()]

    def default_voice(self) -> str:
        return DEFAULT

    @staticmethod
    def params(mood: Mood, expressiveness: float) -> dict:
        e = expressiveness - 0.5
        return {
            "exaggeration": _clamp(mood.exaggeration + 0.6 * e, 0.25, 2.0),
            "cfg_weight": _clamp(mood.cfg_weight - 0.3 * e, 0.0, 1.0),
            "temperature": _clamp(mood.temperature + 0.2 * e, 0.05, 1.5),
        }

    def synthesize(self, sentence: Sentence, voice: str, mood: Mood, speed: float,
                   expressiveness: float) -> np.ndarray:
        model = self._load()
        clip = None if voice == DEFAULT else resolve_clip(voice, mood.name)
        if voice != DEFAULT and clip is None:
            raise ValueError(f"Voice {voice!r} not found. Put a .wav in one of the voice folders.")
        clip_key = str(clip) if clip else None
        kwargs = self.params(mood, expressiveness)
        if clip_key != self._loaded_clip:
            if clip_key is None:
                model.conds = self._builtin_conds
            else:
                kwargs["audio_prompt_path"] = clip_key
            self._loaded_clip = clip_key
        wav = model.generate(sentence.plain, **kwargs)
        return wav.squeeze(0).cpu().numpy().astype(np.float32)
