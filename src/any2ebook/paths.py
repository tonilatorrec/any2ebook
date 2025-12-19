import os
import shutil
from importlib.resources import files
from pathlib import Path

APP_NAME = "any2ebook"

def _override_root() -> Path | None:
    v = os.environ.get("ANY2EBOOK_HOME")
    return Path(v).expanduser().resolve() if v else None

def user_config_dir() -> Path:
    """Get conventional config dir based on OS"""
    root = _override_root()
    if root:
        return root / "config"
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            # very rare, but keep a last-resort fallback
            base = str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME

    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / APP_NAME

def ensure_config() -> Path:
    """Ensures the user config file exists, otherwise copies from config_sample.yaml
    Returns the path to the user config file"""
    cfg_dir = user_config_dir()
    cfg = cfg_dir / "config.yaml"
    if not cfg.exists():
        print(f"Creating {APP_NAME} config file")
        default_cfg = files("any2ebook").joinpath("config_sample.yaml")
        shutil.copy(default_cfg, cfg)
    return cfg
