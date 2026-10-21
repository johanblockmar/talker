import json

import soundfile as sf

from talker.cli import main


def test_say_to_file(tmp_path, capsys):
    out = tmp_path / "out.wav"
    assert main(["say", "Hello there. [mood happy] Nice day!", "-e", "tone", "-o", str(out), "-q"]) == 0
    data, sr = sf.read(out)
    assert sr == 16000 and len(data) > 0


def test_say_from_file_with_presets(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("Line one.\n\nLine two.", encoding="utf-8")
    preset = tmp_path / "p.json"
    out = tmp_path / "out.flac"
    args = ["say", "-f", str(src), "-e", "tone", "-m", "calm", "-s", "1.2", "-o", str(out), "-q"]
    assert main(args + ["--save-preset", str(preset)]) == 0
    saved = json.loads(preset.read_text())
    assert saved["mood"] == "calm" and saved["speed"] == 1.2
    assert main(["say", "-f", str(src), "--preset", str(preset), "-o", str(out), "-q"]) == 0


def test_listing_commands(capsys):
    assert main(["moods"]) == 0
    assert "whisper" in capsys.readouterr().out
    assert main(["engines"]) == 0
    assert "chatterbox" in capsys.readouterr().out
    assert main(["voices", "-e", "kokoro"]) == 0
    assert "af_heart" in capsys.readouterr().out


def test_bad_input_returns_error(capsys):
    assert main(["say", "...", "-e", "tone", "-o", "x.wav", "-q"]) == 2
    assert "Nothing to say" in capsys.readouterr().err
