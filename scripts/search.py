"""Entry point: see finhak.retrieval.cli for options (`python scripts/search.py --help`)."""

import sys

from finhak.retrieval.cli import main

if __name__ == "__main__":
    sys.exit(main())
