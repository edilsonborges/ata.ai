from app.services.storage import slugify, is_supported, is_video


def test_slugify_removes_accents_and_limits_words():
    assert slugify("Revisão de Arquitetura da API Nova v2") == "revisao-de-arquitetura-da-api"


def test_slugify_empty_fallback():
    assert slugify("") == "reuniao"


def test_is_supported():
    assert is_supported("foo.mp4")
    assert is_supported("foo.WAV")
    assert not is_supported("foo.txt")


def test_is_video():
    assert is_video("x.mp4")
    assert not is_video("x.wav")
