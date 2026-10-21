"""User-facing voice settings, shared by the CLI and the GUI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields


@dataclass
class VoiceSettings:
    engine: str = "kokoro"
    voice: str | None = None  # None means the engine's default voice
    mood: str = "neutral"
    intensity: float = 0.5  # 0 = flat, 0.5 = the mood as designed, 1 = exaggerated
    expressiveness: float = 0.5  # inflection range; only engines that support it use it
    speed: float = 1.0  # multiplier on top of the mood's own speed
    pitch: float = 0.0  # semitones on top of the mood's own pitch
    energy: float = 1.0  # loudness multiplier on top of the mood's own energy
    pause_scale: float = 1.0  # multiplier on the gaps between sentences
    seed: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceSettings":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
