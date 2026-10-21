"""Inline markup for inflection and mood changes.

Plain text works as-is. Optional tags:

    *word*            emphasise a word or phrase
    [pause 500ms]     insert silence (also: [pause 1.5s], [pause] = 0.5 s)
    [mood happy]      switch mood for the text that follows
    [mood]            back to the mood chosen in the settings

Text is split into sentences so long input stays within engine limits and so
the gap between sentences can follow the mood.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TAG_RE = re.compile(r"\[(pause|mood)(?:\s+([^\]]*))?\]", re.IGNORECASE)
EMPHASIS_RE = re.compile(r"\*([^*\n]+)\*")
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+|\n\s*\n+")
DEFAULT_PAUSE = 0.5
MAX_PAUSE = 10.0


@dataclass
class Run:
    text: str
    emphasis: bool = False


@dataclass
class Sentence:
    runs: list[Run]
    mood: str | None = None  # None means the settings' mood

    @property
    def plain(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class Pause:
    seconds: float


@dataclass
class Script:
    items: list[Sentence | Pause] = field(default_factory=list)

    @property
    def sentences(self) -> list[Sentence]:
        return [i for i in self.items if isinstance(i, Sentence)]


def parse_pause(arg: str | None) -> float:
    if not arg:
        return DEFAULT_PAUSE
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(ms|s)?\s*", arg, re.IGNORECASE)
    if not m:
        raise ValueError(f"Bad pause length {arg!r}; use e.g. [pause 400ms] or [pause 1.2s]")
    value = float(m.group(1))
    if (m.group(2) or "s").lower() == "ms":
        value /= 1000.0
    return min(value, MAX_PAUSE)


def _runs(text: str) -> list[Run]:
    runs: list[Run] = []
    pos = 0
    for m in EMPHASIS_RE.finditer(text):
        if m.start() > pos:
            runs.append(Run(text[pos:m.start()]))
        runs.append(Run(m.group(1), emphasis=True))
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:]))
    return runs


def _add_text(script: Script, text: str, mood: str | None) -> None:
    for chunk in SENTENCE_RE.split(text):
        chunk = " ".join(chunk.split())
        if chunk and re.search(r"\w", chunk):
            script.items.append(Sentence(_runs(chunk), mood))


def parse(text: str) -> Script:
    script = Script()
    mood: str | None = None
    pos = 0
    for m in TAG_RE.finditer(text):
        _add_text(script, text[pos:m.start()], mood)
        kind, arg = m.group(1).lower(), (m.group(2) or "").strip()
        if kind == "pause":
            script.items.append(Pause(parse_pause(arg)))
        else:
            mood = arg.lower() or None
        pos = m.end()
    _add_text(script, text[pos:], mood)
    return script
