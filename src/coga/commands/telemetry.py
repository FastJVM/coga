"""`coga telemetry` — inspect and send the anonymous install ping.

Two subcommands:

- `show` — read-only. Prints whether telemetry is on (and, if off, which
  disable path won), the `instance_id`, the endpoint URL, and the **exact**
  payload that would be sent — without sending anything. This is the
  legibility guarantee: a human or agent can read precisely what leaves the
  machine.
- `send` — build and POST one ping. This is what the daily
  `coga/recurring/telemetry/` recurring task runs; it is never invoked from a
  foreground dispatch path. A disabled install is a clean no-op.

Both exit non-zero only on a config error. A *send* failure is reported but
exits 0 — the daily run must not crash on a flaky network or a not-yet-deployed
endpoint (the failure is recorded, never swallowed; see `coga.telemetry.send`).
"""

from __future__ import annotations

import json
import sys

import typer

from coga import telemetry
from coga.config import ConfigError, load_config

app = typer.Typer(
    name="telemetry",
    help="Inspect or send the anonymous install ping (opt-out, no PII).",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("show")
def show() -> None:
    """Print telemetry status, the instance id, the URL, and the exact payload.

    Sends nothing. Reading (or generating, on first run) the `instance_id` is
    the only side effect.
    """
    cfg = _load()

    reason = telemetry.disabled_reason(cfg)
    if reason is None:
        typer.echo("status: enabled (opt-out — sent once daily by the "
                   "recurring task)")
    else:
        typer.echo(f"status: disabled — {reason}")

    typer.echo(f"instance_id: {telemetry.read_or_create_instance_id()}")
    typer.echo(f"endpoint: {telemetry.telemetry_url()}")
    typer.echo("")
    typer.echo("payload that would be sent:")
    typer.echo(json.dumps(telemetry.build_payload(cfg), indent=2))

    typer.echo("")
    typer.echo(
        "Disable any of three ways: `[telemetry] enabled = false` in "
        "coga.toml/coga.local.toml, COGA_TELEMETRY_DISABLE=1, or DO_NOT_TRACK=1."
    )


@app.command("send")
def send() -> None:
    """Send one ping (or skip if disabled). Used by the recurring task.

    Exits 0 even when the send fails — the failure is printed (and, run as a
    `mode: script` step, captured to the recurring task's log/blackboard) but
    never crashes the daily run.
    """
    cfg = _load()
    result = telemetry.send(cfg)
    typer.echo(f"telemetry: {result.detail}")


def _load():
    try:
        return load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
