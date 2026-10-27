"""Entry point: see finhak.index.cli for options (`python scripts/build_index.py --help`)."""

import sys

from finhak.index.cli import main

if __name__ == "__main__":
    sys.exit(main())
