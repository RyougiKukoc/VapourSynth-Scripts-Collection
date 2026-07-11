from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "scripts" / "registry.json"


def _load_registry() -> list[dict[str, str]]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("scripts/registry.json must contain a list")
    return data


class CustomHook(BuildHookInterface[Any]):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version

        force_include = build_data["force_include"]
        force_include[str(REGISTRY_PATH)] = "vs_collection_rk/_registry.json"

        for entry in _load_registry():
            runtime_kind = entry["runtime_kind"]
            install_path = entry["install_path"]
            runtime_source = ROOT / entry["runtime_source"]
            source_root = ROOT / entry["source_root"]

            if runtime_kind not in {"module", "package"}:
                raise RuntimeError(f"Unsupported runtime kind {runtime_kind!r} for {entry['slug']}")

            force_include[str(runtime_source)] = install_path
            force_include[str(source_root)] = f"vs_collection_rk/_sources/{entry['slug']}"

        build_data.setdefault("force_include_editable", {})
        build_data["force_include_editable"] = force_include.copy()
