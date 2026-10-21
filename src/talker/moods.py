"""Mood presets.

A mood is a set of target values. ``intensity`` scales how far from neutral the
mood pushes: 0 gives neutral, 0.5 gives the preset as written, 1 doubles the
distance. Engines with a real emotion model (Chatterbox) get ``exaggeration``,
``cfg_weight`` and ``temperature``; every engine gets the prosody values
(speed, pitch, energy, pauses), which are applied in post-processing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Mood:
    name: str
    description: str
    speed: float = 1.0
    pitch: float = 0.0  # semitones
    energy: float = 1.0
    pause: float = 1.0
    exaggeration: float = 0.5
    cfg_weight: float = 0.5
    temperature: float = 0.8

    def scaled(self, intensity: float) -> "Mood":
        k = max(0.0, min(1.0, intensity)) * 2.0
        n = NEUTRAL

        def lerp(a: float, b: float) -> float:
            return a + (b - a) * k

        return replace(
            self,
            speed=lerp(n.speed, self.speed),
            pitch=lerp(n.pitch, self.pitch),
            energy=lerp(n.energy, self.energy),
            pause=lerp(n.pause, self.pause),
            exaggeration=lerp(n.exaggeration, self.exaggeration),
            cfg_weight=lerp(n.cfg_weight, self.cfg_weight),
            temperature=lerp(n.temperature, self.temperature),
        )


NEUTRAL = Mood("neutral", "Even, informative delivery.")

MOODS: dict[str, Mood] = {
    m.name: m
    for m in [
        NEUTRAL,
        Mood("happy", "Bright and upbeat.", speed=1.06, pitch=1.0, energy=1.1, pause=0.9,
             exaggeration=0.75, cfg_weight=0.4, temperature=0.85),
        Mood("excited", "Fast, energetic, big swings.", speed=1.14, pitch=1.8, energy=1.2, pause=0.75,
             exaggeration=0.95, cfg_weight=0.3, temperature=0.9),
        Mood("calm", "Relaxed and soothing.", speed=0.92, pitch=-0.5, energy=0.85, pause=1.25,
             exaggeration=0.35, cfg_weight=0.55, temperature=0.7),
        Mood("sad", "Slow, low and soft.", speed=0.86, pitch=-1.5, energy=0.75, pause=1.4,
             exaggeration=0.6, cfg_weight=0.55, temperature=0.75),
        Mood("angry", "Hard, loud and clipped.", speed=1.08, pitch=0.5, energy=1.3, pause=0.8,
             exaggeration=0.9, cfg_weight=0.35, temperature=0.85),
        Mood("serious", "Measured and firm.", speed=0.95, pitch=-0.8, energy=1.0, pause=1.15,
             exaggeration=0.4, cfg_weight=0.6, temperature=0.7),
        Mood("whisper", "Quiet and intimate.", speed=0.94, pitch=-0.3, energy=0.55, pause=1.2,
             exaggeration=0.3, cfg_weight=0.5, temperature=0.75),
    ]
}


def get_mood(name: str) -> Mood:
    try:
        return MOODS[name.lower()]
    except KeyError:
        raise ValueError(f"Unknown mood {name!r}. Choose from: {', '.join(MOODS)}") from None
