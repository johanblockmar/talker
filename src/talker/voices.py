"""Where reference voices for voice-cloning engines live.

A voice is either a single ``.wav`` file, or a folder of clips named after
moods (``neutral.wav``, ``happy.wav``, ``sad.wav`` ...). With a folder, the
clip matching the current mood is used, which gives the strongest emotion;
``neutral.wav`` (or the first clip) is the fallback.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg"}


def voice_dirs() -> list[Path]:
    dirs = []
    if env := os.environ.get("TALKER_VOICES"):
        dirs += [Path(p) for p in env.split(os.pathsep) if p]
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        dirs.append(base / "Talker" / "voices")
    else:
        dirs.append(Path.home() / ".local" / "share" / "talker" / "voices")
    dirs.append(Path.cwd() / "voices")
    return dirs


def list_voices() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for d in voice_dirs():
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
                found.setdefault(p.stem, p)
            elif p.is_dir() and any(c.suffix.lower() in AUDIO_EXTS for c in p.iterdir()):
                found.setdefault(p.name, p)
    return found


def resolve_clip(voice: str, mood: str) -> Path | None:
    """Return the reference clip for ``voice`` in ``mood``, or None if not a known voice."""
    path = Path(voice)
    if not path.exists():
        path = list_voices().get(voice)
        if path is None:
            return None
    if path.is_file():
        return path
    clips = sorted(c for c in path.iterdir() if c.suffix.lower() in AUDIO_EXTS)
    by_mood = {c.stem.lower(): c for c in clips}
    return by_mood.get(mood) or by_mood.get("neutral") or (clips[0] if clips else None)
