"""Entry point: see finhak.parsing.cli for options (`python scripts/parse_sources.py --help`)."""

import sys

from finhak.parsing.cli import main

if __name__ == "__main__":
    sys.exit(main())
