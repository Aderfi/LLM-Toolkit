from llmtools import config


def test_delete_disabled_by_default():
    assert config.ALLOW_DELETE_FILES is False


def test_model_is_gemma4_e4b():
    assert config.MODEL == "gemma4:e4b"
