"""Entry point: see finhak.generation.cli for options (`python scripts/ask.py --help`)."""

import sys

from finhak.generation.cli import main

if __name__ == "__main__":
    sys.exit(main())
