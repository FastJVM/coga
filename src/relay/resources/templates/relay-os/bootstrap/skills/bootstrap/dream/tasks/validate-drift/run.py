#!/usr/bin/env python3
"""Run the validate-drift Dream worker."""

from __future__ import annotations

import sys

from relay.dream_validate_drift import main


if __name__ == "__main__":
    sys.exit(main())
