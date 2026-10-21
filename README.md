# Talker

Offline text-to-speech for Windows, written in Python. One synthesis core, two front ends: a desktop app and a command line tool. After a one-time model download, nothing leaves your PC.

## Engines

| Engine | Sound | Mood control | Speed | Licence |
|---|---|---|---|---|
| **Chatterbox** (Resemble AI) | Very natural, can clone a voice from a short clip | Real emotion model: an "exaggeration" knob plus per-mood reference clips | Fast on an NVIDIA GPU, slow on CPU | MIT |
| **Kokoro-82M** | Natural, 15 built-in English voices | Prosody only: speed, pitch, energy, pauses, word emphasis | Faster than real time on CPU | Apache 2.0 |
| Test tones | Beeps | n/a | instant | (for testing without a model) |

Chatterbox is the expressive engine; Kokoro is the quick, lightweight one. Both run under the same settings.

Engines considered and not used: Piper (fast but no emotion control), Coqui XTTS-v2 (non-commercial licence, project abandoned), Parler-TTS and Bark (slower, less consistent), Orpheus (3B parameters, heavy for a desktop app).

## Install on Windows

Needs Python 3.10, 3.11 or 3.12 (3.11 recommended; Chatterbox's PyTorch 2.6 has no 3.13 wheels).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

The script makes `.venv`, installs CUDA PyTorch if it finds an NVIDIA GPU (CPU PyTorch otherwise), installs Talker with both engines and the GUI, and downloads the models (about 3 GB for Chatterbox, 350 MB for Kokoro). To keep it strictly offline afterwards, set `HF_HUB_OFFLINE=1`.

Manual install, if you prefer:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124   # or /whl/cpu
pip install -e .[all]          # or .[kokoro,gui] for the light setup
talker download
```

## Desktop app

```powershell
talker-gui        # or: talker gui
```

Type text, pick an engine, voice and mood, adjust the sliders, press **Speak** or **Save audio**. Settings and text are remembered between sessions.

## Command line

```powershell
talker say "Hello there!" --mood happy                       # speak it
talker say "Hello there!" -m excited -i 0.8 -o hello.wav     # save it
talker say -f chapter.txt -e chatterbox --voice me -m calm -o chapter.flac
type notes.txt | talker say - -e kokoro --voice bm_george
talker say "..." --save-preset narrator.json                 # save settings
talker say -f script.txt --preset narrator.json -o out.wav   # reuse them
talker moods      talker engines      talker voices -e kokoro
```

## Controls

| Setting | CLI flag | What it does |
|---|---|---|
| Mood | `-m` | neutral, happy, excited, calm, sad, angry, serious, whisper |
| Intensity | `-i` | 0 = flat, 0.5 = the mood as designed, 1 = exaggerated |
| Expressiveness | `-x` | Inflection range: how much the voice moves (Chatterbox) |
| Speed | `-s` | Multiplier on top of the mood's speed |
| Pitch | `-p` | Semitones on top of the mood's pitch |
| Energy | `--energy` | Loudness multiplier |
| Pauses | `--pause-scale` | Length of the gap between sentences |
| Seed | `--seed` | Repeatable output from Chatterbox |

### Inline markup

```
I *really* didn't expect that. [pause 600ms]
[mood excited] We won! [mood] Anyway, back to the plan.
```

* `*word*` emphasises a word (Kokoro stress markup; Chatterbox ignores it).
* `[pause 500ms]` or `[pause 1.5s]` inserts silence.
* `[mood happy]` switches mood until the next `[mood ...]`; `[mood]` goes back to the chosen mood.

### Your own voice (Chatterbox)

Put a 5 to 15 second clean recording in `voices\` or `%APPDATA%\Talker\voices\`, or a folder with one clip per mood (`neutral.wav`, `happy.wav`, ...). See [voices/README.md](voices/README.md).

## Layout

```
src/talker/
  synth.py        pipeline: parse -> engine per sentence -> prosody -> join
  markup.py       *emphasis*, [pause], [mood] tags and sentence splitting
  moods.py        mood presets and intensity scaling
  settings.py     VoiceSettings, shared by GUI, CLI and JSON presets
  voices.py       reference-voice folders for cloning
  engines/        chatterbox, kokoro, tone (test) behind one interface
  cli.py          command line
  gui/app.py      PySide6 desktop app
```

Adding an engine means one subclass of `engines.base.Engine` and one line in `engines/__init__.py`.

## Tests

```powershell
pip install -e .[dev]
pytest
```

The tests use the test-tone engine, so they need no model download.
