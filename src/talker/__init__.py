"""Talker: offline text-to-speech with mood and inflection controls."""

from talker.settings import VoiceSettings
from talker.synth import Audio, Synthesizer

__all__ = ["Audio", "Synthesizer", "VoiceSettings"]
__version__ = "0.1.0"
