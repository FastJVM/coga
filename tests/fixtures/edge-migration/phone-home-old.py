"""Synthetic full-script baseline used by the installed-wheel migration test."""

from pathlib import Path


def main() -> None:
    # The migration compares this file as bytes. A full local copy may contain
    # its own worker implementation instead of importing the installed shim.
    Path("legacy-worker-ran").touch()


if __name__ == "__main__":
    main()
