from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vs_collection_rk import bundled_scripts


def main() -> int:
    for module_name in bundled_scripts():
        importlib.import_module(module_name)
        print(f"OK {module_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
