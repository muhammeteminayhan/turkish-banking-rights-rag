"""Entry point: see finhak.evaluation.judge_cli (`python eval/judge.py --help`)."""

import sys

from finhak.evaluation.judge_cli import main

if __name__ == "__main__":
    sys.exit(main())
