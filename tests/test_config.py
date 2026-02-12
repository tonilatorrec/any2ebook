from importlib.resources import files
from pathlib import Path

import pytest

from any2ebook.config import Config, ConfigNotFoundError

APP_NAME = "any2ebook"


def test_valid_config_path():
    Config.load(files(APP_NAME).joinpath('config_sample.yaml'))

def test_invalid_config_path(tmp_path):
    invalid_path = tmp_path / "config.yaml"
    assert not invalid_path.exists()

    with pytest.raises(ConfigNotFoundError):
        Config.load(invalid_path)

def test_config_file_with_missing_key():
    fixture_path = Path(__file__).with_name("config_sample_test.yaml")
    config = Config.load(fixture_path)
    assert config.input_path is None
