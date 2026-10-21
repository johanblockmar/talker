"""Engine interface. Each engine turns one sentence into a mono float32 array."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from talker.markup import Sentence
from talker.moods import Mood


@dataclass(frozen=True)
class Capabilities:
    emotion: bool = False  # has a real emotion model, not just prosody
    expressiveness: bool = False  # honours the expressiveness (inflection) setting
    emphasis: bool = False  # honours *word* emphasis
    voice_cloning: bool = False  # accepts a reference .wav as a voice
    speed: bool = True  # handles speed itself; otherwise the synthesizer time-stretches


class Engine(ABC):
    name: str = ""
    label: str = ""
    sample_rate: int = 24000
    capabilities = Capabilities()

    def __init__(self, device: str | None = None):
        self.device = device

    @classmethod
    def available(cls) -> tuple[bool, str]:
        """Whether the engine's packages are installed, and why not if they aren't."""
        return True, ""

    def prefetch(self) -> None:
        """Download everything the engine needs so later runs work offline."""

    @abstractmethod
    def voices(self) -> list[str]: ...

    @abstractmethod
    def default_voice(self) -> str: ...

    @abstractmethod
    def synthesize(
        self,
        sentence: Sentence,
        voice: str,
        mood: Mood,
        speed: float,
        expressiveness: float,
    ) -> np.ndarray:
        """Return mono float32 audio at ``self.sample_rate``.

        ``speed`` already includes the mood's speed. Pitch, energy and pauses
        are applied afterwards by the synthesizer, so engines can ignore them.
        """
