import argparse
import sys

from .commands import create, launch, status, step, panic, feed


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="relay",
        description="Relay — a blackboard for humans and agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for mod in (create, launch, status, step, panic, feed):
        mod.register(sub)

    args = parser.parse_args(argv)
    try:
        return args.func(args) or 0
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
