"""Desktop app entry point (talker-gui.exe and `talker gui`).

The engines' libraries are imported here, before PySide6. PySide6 installs an
import hook that inspects every module imported after it, and that hook
crashes on the `six.moves` modules pulled in by transformers (via sklearn,
pandas and dateutil). Loading them first keeps them out of the hook's way.
"""

from __future__ import annotations

import importlib
import sys
import traceback

from talker import runtime
from talker.engines import ENGINES

# What each engine imports when it first runs.
PRELOAD = {
    "kokoro": ["kokoro"],
    "chatterbox": ["chatterbox.tts"],
}


def preload_engines() -> None:
    for name, modules in PRELOAD.items():
        if not ENGINES[name].available()[0]:
            continue
        for module in modules:
            try:
                importlib.import_module(module)
            except Exception:  # the engine reports its own error when used
                traceback.print_exc()


def main() -> int:
    runtime.prepare()
    preload_engines()
    from talker.gui.window import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
