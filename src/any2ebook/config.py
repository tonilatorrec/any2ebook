import os
import shutil
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path

import yaml

APP_NAME = "any2ebook"

class ConfigNotFoundError(FileNotFoundError):
    pass

@dataclass(slots=True)
class Config:
    # stable fields (known at dev time)
    config_path: Path
    clippings_path: Path | None = None
    input_path: Path | None = None
    output_path: Path | None = None

    @classmethod
    def load(cls, path: os.PathLike | None) -> "Config":
        """Load config from disk."""
        if not path.exists():
            raise ConfigNotFoundError(path)
        with open(path, 'r') as f:
            raw = yaml.safe_load(f) or {}
            # TODO: avoid Path('.') when the raw is ''
            return cls(
                config_path=Path(path),
                clippings_path=Path(raw['clippings_path']) if raw.get('clippings_path') is not None else None,
                input_path=Path(raw['input_path']) if raw.get('input_path') is not None else None,
                output_path=Path(raw['output_path']) if raw.get('output_path') is not None else None
            )

    def save(self, config_path: Path | None = None) -> None:
        """Save to disk."""
        raw = asdict(self)
        out = dict()
        # TODO: create constant for all keys to be saved in config file
        for k in ('clippings_path', 'input_path', 'output_path'): 
            out[k] = str(raw[k]) if raw[k] is not None else None
        if config_path is None:
            with open(self.config_path, 'w') as f:
                yaml.dump(out, f)
        else:
            with open(config_path, 'w') as f:
                yaml.dump(out, f)         
                self.config_path = config_path 

    def validate(self) -> None:
        # TODO: implement?
        pass

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


def ensure_config_path() -> Path:
    """Ensures the user config file exists, otherwise copies from config_sample.yaml
    Returns the path to the user config file"""
    cfg_dir = user_config_dir()
    if not cfg_dir.exists():
        os.makedirs(cfg_dir)
    cfg = cfg_dir / "config.yaml"
    if not cfg.exists():
        print(f"Creating {APP_NAME} config file")
        default_cfg = files("any2ebook").joinpath("config_sample.yaml")
        shutil.copy(default_cfg, cfg)
    return cfg


