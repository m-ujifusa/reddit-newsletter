#!/usr/bin/env python3
"""Manual pipeline trigger script."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from newsletter.main import app

if __name__ == "__main__":
    app(["pipeline"])
