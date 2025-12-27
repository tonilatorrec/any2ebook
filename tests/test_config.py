from any2ebook.config import Config
import pytest
from importlib.resources import files
from pathlib import Path
import os

APP_NAME = "any2ebook"

def test_valid_config_path():
    Config.load(files(APP_NAME).joinpath('config_sample.yaml'))

def test_config_file_with_missing_key():
    config = Config.load(Path('tests/config_sample_test.yaml'))
    assert config.input_path is None