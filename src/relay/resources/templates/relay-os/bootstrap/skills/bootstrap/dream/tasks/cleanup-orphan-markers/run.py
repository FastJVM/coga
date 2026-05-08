#!/usr/bin/env python3
"""Run the cleanup-orphan-markers Dream worker."""

from __future__ import annotations

import sys

from relay.dream_cleanup_orphan_markers import main


if __name__ == "__main__":
    sys.exit(main())
