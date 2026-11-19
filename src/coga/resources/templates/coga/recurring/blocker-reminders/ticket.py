#!/usr/bin/env python3
"""Run the installed blocker-reminders implementation; a local fork requires review."""
from __future__ import annotations

from coga_edge.blocker_reminders import main

if __name__ == "__main__":
    raise SystemExit(main([], scheduled=True))
