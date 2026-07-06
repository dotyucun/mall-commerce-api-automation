from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).with_name("default.yaml")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    return config
