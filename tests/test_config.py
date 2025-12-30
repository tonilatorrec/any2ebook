from importlib.resources import files
from pathlib import Path

import pytest

from any2ebook.config import Config, ConfigNotFoundError, ensure_config_path, user_config_dir

APP_NAME = "any2ebook"


def test_valid_config_path():
    Config.load(files(APP_NAME).joinpath('config_sample.yaml'))

def test_invalid_config_path(tmp_path):
    invalid_path = tmp_path / "config.yaml"
    assert not invalid_path.exists()

    with pytest.raises(ConfigNotFoundError):
        Config.load(invalid_path)

def test_config_file_with_missing_key():
    config = Config.load(Path('tests/config_sample_test.yaml'))
    assert config.input_path is None

def test_user_config_dir():
    assert isinstance(user_config_dir(), Path)

def test_ensure_config_path():
    assert isinstance(ensure_config_path(), Path)