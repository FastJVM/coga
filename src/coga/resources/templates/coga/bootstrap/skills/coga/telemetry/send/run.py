#!/usr/bin/env python3
"""Send the anonymous install ping — the `mode: script` body of recurring/telemetry.

Runs as a Coga `mode: script` step (see `coga.commands.launch_script`): the
working directory is the host repo, and `coga` is importable. We call
`telemetry.send` directly rather than shelling out to `coga telemetry send`, so
the send does not depend on `coga` being on `PATH` inside the script
environment.

`telemetry.send` never raises — a disabled install is a clean no-op, and a
failed send is *returned* as a result, not thrown — so this exits 0 on every
ordinary day. The one-line outcome printed here is captured into the recurring
task's run history (`coga/log.md`), so a send failure is recorded rather than
swallowed without crashing the daily run.
"""

from __future__ import annotations

import sys

from coga import telemetry
from coga.config import ConfigError, load_config


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"[telemetry] {exc}\n")
        return 2
    result = telemetry.send(cfg)
    sys.stdout.write(f"[telemetry] {result.detail}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
