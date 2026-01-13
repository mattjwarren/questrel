"""Questrel CLI demo runner.

This script exists so you can run the CLI without installing the package.
It prepends `src/` onto sys.path and then dispatches to `questrel.cli`.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from questrel.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
