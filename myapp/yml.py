from pathlib import Path
from typing import Optional
import yaml

_cfg: Optional[dict] = None

PATHS = [
    "/run/secrets/config_file",
    "config.yml",
]


def get_cfg(app=None, paths=None, cache=True):
    global _cfg

    if cache and isinstance(_cfg, dict):
        if app:
            return _cfg.get(app)
        return _cfg

    if paths is None:
        paths = PATHS

    for path in paths:
        if not Path(path).exists():
            continue

        with open(path, encoding='utf8') as file:
            result = yaml.safe_load(file)
            if app:
                return result.get(app)
            if cache:
                _cfg = result
            return result


def get_spec(path):
    return get_cfg(paths=[path], cache=False)
