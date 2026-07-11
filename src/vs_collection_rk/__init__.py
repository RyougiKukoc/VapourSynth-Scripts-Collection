from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any


__all__ = ["__version__", "bundled_scripts", "find_script", "load_registry"]
__version__ = "0.1.0"


def load_registry() -> list[dict[str, Any]]:
    registry_path = files(__package__).joinpath("_registry.json")
    try:
        return json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        source_registry = Path(__file__).resolve().parents[2] / "scripts" / "registry.json"
        return json.loads(source_registry.read_text(encoding="utf-8"))


def bundled_scripts() -> list[str]:
    return [entry["import_name"] for entry in load_registry()]


def find_script(name: str) -> dict[str, Any]:
    for entry in load_registry():
        if entry["slug"] == name or entry["import_name"] == name:
            return entry
    raise KeyError(name)
