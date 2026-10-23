"""Entry point: see finhak.ingest.cli for options (`python scripts/fetch_sources.py --help`)."""

import sys

from finhak.ingest.cli import main

if __name__ == "__main__":
    sys.exit(main())
