"""Questrel text adventure demo runner.

This keeps the interactive demo runnable without installing the package.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from questrel.demos.text_adventure import main as demo_main

    return demo_main()


if __name__ == "__main__":
    raise SystemExit(main())
