import pytest

from talker import markup


def test_plain_text_splits_into_sentences():
    s = markup.parse("Hello there. How are you?  Fine!")
    assert [x.plain for x in s.sentences] == ["Hello there.", "How are you?", "Fine!"]


def test_emphasis_runs():
    (sent,) = markup.parse("I *really* mean it.").sentences
    assert [(r.text, r.emphasis) for r in sent.runs] == [
        ("I ", False), ("really", True), (" mean it.", False)]


def test_pause_and_mood_tags():
    s = markup.parse("Hi. [pause 300ms] [mood sad] Oh no. [mood] Okay.")
    kinds = [(type(i).__name__, getattr(i, "seconds", None), getattr(i, "mood", None))
             for i in s.items]
    assert kinds == [
        ("Sentence", None, None),
        ("Pause", 0.3, None),
        ("Sentence", None, "sad"),
        ("Sentence", None, None),
    ]


@pytest.mark.parametrize("arg,expected", [(None, 0.5), ("2s", 2.0), ("1.5", 1.5), ("250 ms", 0.25),
                                          ("99s", markup.MAX_PAUSE)])
def test_pause_lengths(arg, expected):
    assert markup.parse_pause(arg) == expected


def test_bad_pause():
    with pytest.raises(ValueError):
        markup.parse("[pause soon]")


def test_punctuation_only_is_dropped():
    assert markup.parse("... --- !!!").sentences == []
