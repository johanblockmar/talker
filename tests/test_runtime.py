import pytest

from talker import runtime


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    return tmp_path


def fake_cache(cache, repo):
    (cache / f"models--{repo.replace('/', '--')}" / "snapshots" / "abc").mkdir(parents=True)


def only_installed(monkeypatch, names):
    for name in runtime.MODEL_REPOS:
        ok = name in names
        monkeypatch.setattr(runtime.ENGINES[name], "available", classmethod(lambda cls, ok=ok: (ok, "")))


def test_offline_once_installed_models_are_cached(cache, monkeypatch):
    import os

    only_installed(monkeypatch, ["kokoro"])
    assert not runtime.go_offline_if_ready()
    fake_cache(cache, "hexgrad/Kokoro-82M")
    assert runtime.go_offline_if_ready()
    assert os.environ["HF_HUB_OFFLINE"] == "1"


def test_stays_online_while_any_installed_model_is_missing(cache, monkeypatch):
    only_installed(monkeypatch, ["kokoro", "chatterbox"])
    fake_cache(cache, "hexgrad/Kokoro-82M")
    assert not runtime.go_offline_if_ready()


def test_respects_explicit_setting(cache, monkeypatch):
    only_installed(monkeypatch, ["kokoro"])
    fake_cache(cache, "hexgrad/Kokoro-82M")
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    assert not runtime.go_offline_if_ready()
