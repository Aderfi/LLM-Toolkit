from llmtools import utils


def test_calculate():
    assert "7" in utils.calculate("3 + 4")


def test_calculate_rejects_names():
    assert "error" in utils.calculate("__import__('os')").lower()


def test_base64_roundtrip():
    enc = utils.base64_encode("hola")
    assert "hola" == utils.base64_decode(enc.strip())


def test_hash_text():
    assert len(utils.hash_text("x").split(":")[-1].strip()) == 64
