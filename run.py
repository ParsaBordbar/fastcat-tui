#!/usr/bin/env python3
"""Launcher: `python3 run.py` opens the TUI, `python3 run.py <command> ...` runs the CLI."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastcat_tui.cli import main

if __name__ == "__main__":
    main()
