from any2ebook.config import Config, InvalidConfigError
import pytest
from importlib.resources import files
from pathlib import Path
import os

APP_NAME = "any2ebook"

def test_invalid_config_path():
    with pytest.raises(InvalidConfigError) as e:
        Config.load(Path('tests/config_sample_test.yaml'))