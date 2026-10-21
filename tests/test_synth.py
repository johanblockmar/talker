import threading

import numpy as np
import pytest

from talker import Synthesizer, VoiceSettings
from talker.engines.chatterbox_engine import ChatterboxEngine
from talker.engines.kokoro_engine import KokoroEngine
from talker.markup import parse
from talker.moods import MOODS, NEUTRAL, get_mood
from talker.synth import Cancelled


def tone(**kw):
    return VoiceSettings(engine="tone", **kw)


def test_synthesize_produces_audio():
    audio = Synthesizer().synthesize("One two. Three.", tone())
    assert audio.sample_rate == 16000
    assert audio.samples.dtype == np.float32
    assert 0.5 < audio.duration < 3
    assert np.max(np.abs(audio.samples)) <= 0.98


def test_speed_and_pauses_change_length():
    s = Synthesizer()
    base = s.synthesize("One two three. Four five.", tone()).duration
    assert s.synthesize("One two three. Four five.", tone(speed=2.0)).duration < base
    assert s.synthesize("One two three. Four five.", tone(pause_scale=3.0)).duration > base
    assert s.synthesize("One. [pause 1s] Two.", tone()).duration > 1.0


def test_energy_scales_loudness():
    s = Synthesizer()
    quiet = s.synthesize("Hello world.", tone(energy=0.5)).samples
    loud = s.synthesize("Hello world.", tone(energy=1.0)).samples
    assert np.max(np.abs(quiet)) < np.max(np.abs(loud))


def test_pitch_shift_runs():
    pytest.importorskip("librosa")
    audio = Synthesizer().synthesize("Hello world.", tone(pitch=3))
    assert audio.duration > 0


def test_mood_intensity_scaling():
    sad = get_mood("sad")
    assert sad.scaled(0).speed == NEUTRAL.speed
    assert sad.scaled(0.5).speed == pytest.approx(sad.speed)
    assert sad.scaled(1).speed < sad.speed < NEUTRAL.speed


def test_every_mood_synthesizes():
    s = Synthesizer()
    for name in MOODS:
        assert s.synthesize("Hi there.", tone(mood=name)).duration > 0


def test_cancel():
    ev = threading.Event()
    ev.set()
    with pytest.raises(Cancelled):
        Synthesizer().synthesize("Hello.", tone(), cancel=ev)


def test_errors():
    s = Synthesizer()
    with pytest.raises(ValueError):
        s.synthesize("   ", tone())
    with pytest.raises(ValueError):
        s.synthesize("Hi.", tone(mood="grumpy"))
    with pytest.raises(ValueError):
        s.synthesize("Hi.", VoiceSettings(engine="nope"))


def test_save_roundtrip(tmp_path):
    import soundfile as sf

    audio = Synthesizer().synthesize("Hello.", tone())
    path = audio.save(tmp_path / "x.wav")
    data, sr = sf.read(path)
    assert sr == 16000 and len(data) == len(audio.samples)


def test_kokoro_emphasis_markup():
    (sent,) = parse("I *really do* mean it.").sentences
    assert KokoroEngine.to_kokoro_text(sent) == "I [really](+2) [do](+2) mean it."


def test_chatterbox_params_follow_mood_and_expressiveness():
    calm = ChatterboxEngine.params(get_mood("calm"), 0.5)
    excited = ChatterboxEngine.params(get_mood("excited"), 0.5)
    assert excited["exaggeration"] > calm["exaggeration"]
    flat = ChatterboxEngine.params(NEUTRAL, 0.0)
    lively = ChatterboxEngine.params(NEUTRAL, 1.0)
    assert lively["exaggeration"] > flat["exaggeration"]
    assert lively["cfg_weight"] < flat["cfg_weight"]
