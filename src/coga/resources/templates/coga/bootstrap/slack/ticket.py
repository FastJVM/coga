"""Post the stock FYI; replace this file with a full local fork."""
from __future__ import annotations

import sys
from coga_edge.slack import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
