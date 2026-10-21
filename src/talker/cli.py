"""Command line interface. Runs the same pipeline as the desktop app.

Examples:
    talker say "Hello there!" --mood happy -o hello.wav
    talker say -f chapter.txt --engine chatterbox --voice me --mood calm --play
    echo "Read from stdin" | talker say -
    talker moods | talker voices | talker engines
    talker download kokoro chatterbox   (once, then fully offline)
    talker gui
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from talker.engines import ENGINES
from talker.moods import MOODS
from talker.settings import VoiceSettings
from talker.synth import Synthesizer


def _read_text(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text in (None, "-"):
        if sys.stdin.isatty() and args.text is None:
            raise SystemExit("Give some text, -f FILE, or pipe text in with '-'.")
        return sys.stdin.read()
    return args.text


def _settings(args: argparse.Namespace) -> VoiceSettings:
    s = VoiceSettings()
    if args.preset:
        s = VoiceSettings.from_dict(json.loads(Path(args.preset).read_text(encoding="utf-8")))
    for name in ("engine", "voice", "mood", "intensity", "expressiveness", "speed", "pitch",
                 "energy", "pause_scale", "seed"):
        value = getattr(args, name)
        if value is not None:
            setattr(s, name, value)
    return s


def cmd_say(args: argparse.Namespace) -> int:
    text = _read_text(args)
    settings = _settings(args)
    if args.save_preset:
        Path(args.save_preset).write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
    synth = Synthesizer(device=args.device)

    def progress(done: int, total: int) -> None:
        if not args.quiet:
            print(f"\r  sentence {done}/{total}", end="", file=sys.stderr, flush=True)

    audio = synth.synthesize(text, settings, progress=progress)
    if not args.quiet:
        print(file=sys.stderr)
    if args.output:
        path = audio.save(args.output)
        if not args.quiet:
            print(f"Saved {path} ({audio.duration:.1f} s)", file=sys.stderr)
    if args.play or not args.output:
        audio.play()
    return 0


def cmd_moods(args: argparse.Namespace) -> int:
    for m in MOODS.values():
        print(f"{m.name:10} {m.description}")
    return 0


def cmd_engines(args: argparse.Namespace) -> int:
    for name, cls in ENGINES.items():
        ok, why = cls.available()
        print(f"{name:11} {cls.label}" + ("" if ok else f"  [{why}]"))
    return 0


def cmd_voices(args: argparse.Namespace) -> int:
    cls = ENGINES[args.engine]
    for v in cls().voices():
        print(v)
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    names = args.engines or [n for n, c in ENGINES.items() if n != "tone" and c.available()[0]]
    if not names:
        raise RuntimeError('No engines installed. Try: pip install "talker[kokoro]"')
    synth = Synthesizer(device=args.device)
    for name in names:
        print(f"Downloading {name} ...", file=sys.stderr)
        synth.engine(name).prefetch()
    print("Done. Set HF_HUB_OFFLINE=1 to make sure nothing goes online again.", file=sys.stderr)
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    from talker.gui.app import main as gui_main

    return gui_main()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="talker", description="Offline text-to-speech.")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    say = sub.add_parser("say", help="speak or save text")
    say.add_argument("text", nargs="?", help="text to speak, or '-' for stdin")
    say.add_argument("-f", "--file", help="read text from a UTF-8 file")
    say.add_argument("-o", "--output", help="write audio here (.wav, .flac, .ogg)")
    say.add_argument("--play", action="store_true", help="also play when saving")
    say.add_argument("-e", "--engine", choices=list(ENGINES))
    say.add_argument("--voice")
    say.add_argument("-m", "--mood", choices=list(MOODS))
    say.add_argument("-i", "--intensity", type=float, help="mood strength 0..1 (default 0.5)")
    say.add_argument("-x", "--expressiveness", type=float, help="inflection range 0..1")
    say.add_argument("-s", "--speed", type=float, help="speed multiplier, e.g. 1.1")
    say.add_argument("-p", "--pitch", type=float, help="pitch shift in semitones, e.g. -2")
    say.add_argument("--energy", type=float, help="loudness multiplier, e.g. 0.8")
    say.add_argument("--pause-scale", dest="pause_scale", type=float, help="sentence gap multiplier")
    say.add_argument("--seed", type=int, help="fix randomness for repeatable output")
    say.add_argument("--preset", help="load settings from a JSON file (flags override it)")
    say.add_argument("--save-preset", help="write the final settings to a JSON file")
    say.add_argument("--device", help="cpu or cuda (default: auto)")
    say.add_argument("-q", "--quiet", action="store_true")
    say.set_defaults(func=cmd_say)

    sub.add_parser("moods", help="list moods").set_defaults(func=cmd_moods)
    sub.add_parser("engines", help="list engines").set_defaults(func=cmd_engines)
    voices = sub.add_parser("voices", help="list voices for an engine")
    voices.add_argument("-e", "--engine", choices=list(ENGINES), default="kokoro")
    voices.set_defaults(func=cmd_voices)
    dl = sub.add_parser("download", help="fetch models once so Talker runs offline")
    dl.add_argument("engines", nargs="*", help="kokoro and/or chatterbox (default: all installed)")
    dl.add_argument("--device", help="cpu or cuda (default: auto)")
    dl.set_defaults(func=cmd_download)
    sub.add_parser("gui", help="open the desktop app").set_defaults(func=cmd_gui)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    try:
        return args.func(args)
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print(f"talker: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
