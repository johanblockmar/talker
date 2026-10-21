"""Engine registry. Engines are created lazily so their heavy imports only
happen when they are first used."""

from __future__ import annotations

from talker.engines.base import Capabilities, Engine
from talker.engines.chatterbox_engine import ChatterboxEngine
from talker.engines.kokoro_engine import KokoroEngine
from talker.engines.tone import ToneEngine

ENGINES: dict[str, type[Engine]] = {
    e.name: e for e in (ChatterboxEngine, KokoroEngine, ToneEngine)
}

__all__ = ["ENGINES", "Capabilities", "Engine"]
