"""Entry point: see finhak.evaluation.cli for options (`python eval/run_retrieval.py --help`)."""

import sys

from finhak.evaluation.cli import main

if __name__ == "__main__":
    sys.exit(main())
