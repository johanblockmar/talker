"""Process setup shared by the CLI and the GUI: offline mode and quieter logs.

Both must run before any engine imports huggingface_hub or torch, because
huggingface_hub reads HF_HUB_OFFLINE when it is first imported.
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

from talker.engines import ENGINES

MODEL_REPOS = {
    "kokoro": "hexgrad/Kokoro-82M",
    "chatterbox": "ResembleAI/chatterbox",
}


def hf_cache_dir() -> Path:
    if cache := os.environ.get("HF_HUB_CACHE"):
        return Path(cache)
    home = os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface"
    return Path(home) / "hub"


def is_cached(repo: str) -> bool:
    snapshots = hf_cache_dir() / f"models--{repo.replace('/', '--')}" / "snapshots"
    return snapshots.is_dir() and any(snapshots.iterdir())


def go_offline_if_ready() -> bool:
    """Stop all network access once every installed engine's model is downloaded."""
    if "HF_HUB_OFFLINE" in os.environ:
        return os.environ["HF_HUB_OFFLINE"] not in ("", "0")
    installed = [n for n in MODEL_REPOS if ENGINES[n].available()[0]]
    if installed and all(is_cached(MODEL_REPOS[n]) for n in installed):
        os.environ["HF_HUB_OFFLINE"] = "1"
        return True
    return False


def quiet_libraries() -> None:
    """Hide third-party deprecation and setup chatter that isn't actionable."""
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning, module=r"torch\..*")
    warnings.filterwarnings("ignore", message=".*unauthenticated requests to the HF Hub.*")
    for name in ("huggingface_hub", "transformers", "diffusers"):
        logging.getLogger(name).setLevel(logging.ERROR)


def log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "Talker"
    return Path.home() / ".local" / "state" / "talker"


def ensure_std_streams() -> Path | None:
    """Give a windowed app somewhere to print.

    talker-gui.exe runs without a console, so sys.stdout and sys.stderr are
    None and libraries that print or log (Kokoro's loguru, tqdm) crash.
    Send their output to a log file instead. Returns the log path if used.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return None
    path = log_dir() / "talker.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = open(path, "a", encoding="utf-8", buffering=1)
    except OSError:
        path, stream = None, open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    return path


def prepare(online: bool = False, verbose: bool = False) -> None:
    ensure_std_streams()
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    if not verbose:
        quiet_libraries()
    if not online:
        go_offline_if_ready()
