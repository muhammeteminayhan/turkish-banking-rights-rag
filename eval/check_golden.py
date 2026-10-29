"""Entry point: see finhak.evaluation.draft_cli (`python eval/check_golden.py --help`)."""

import sys

from finhak.evaluation.draft_cli import main

if __name__ == "__main__":
    sys.exit(main())
