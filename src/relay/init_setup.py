"""Init setup ticket — scaffolded on a fresh `relay init`.

`relay init` asks nothing beyond the user's name: interactive interviews
don't belong inside init, so the four setup questions are asked by the
agent at first launch — the `interview` step of the `init/setup` workflow
— and the ticket ships with an empty Context for that step to fill. The
question wording and the generation contract (fact/intent precedence,
stub-and-ask, the open-questions deliverable, the follow-up interview)
live in the workflow file, not here: this module only writes the ticket.

Scaffolds once, on fresh init (never on `--update`; fresh init refuses to
run when `relay-os/` already exists, so once-ness is structural).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer

from relay.config import load_config
from relay.scaffold import scaffold_task


SETUP_WORKFLOW = "init/setup"
SETUP_SLUG = "relay-setup"

SETUP_TICKET_BODY = """\
## Description

Interview the owner, then turn the answers plus a scan of this repo into
durable relay-os artifacts — contexts, rules, workflows, recurring tasks,
possibly skills — so future agents start already knowing the project
instead of starting from zero. The interview is the first workflow step:
launching this ticket starts it. Generated files are drafts for the
owner's review; nothing is final without sign-off.

## Context

Empty until the `interview` step runs at first launch — the agent records
the owner's answers to the four setup questions here verbatim.
"""


def prompt_eligible() -> bool:
    """Only prompt a real human: both ends of the pipe must be a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_user_name() -> str | None:
    """Ask for the user's name. Returns None when the human bails (Ctrl-C/EOF)."""
    try:
        user = typer.prompt(
            "\nYour name (becomes `user` in relay.local.toml)"
        ).strip()
    except (KeyboardInterrupt, EOFError):
        typer.echo("")
        return None
    return user or None


def scaffold_setup_ticket(relay_os: Path, owner: str) -> dict[str, Any]:
    """Write the `relay-setup` ticket, Context left for the launch interview.

    Expects `user` to already be set in relay.local.toml (init writes it from
    the name prompt before calling) — `load_config` refuses to run otherwise.
    Scaffolded `active` so it is `relay launch`-ready without a manual
    `relay mark active` first. Returns scaffold_task's {slug, path}.
    """
    cfg = load_config(relay_os)
    return scaffold_task(
        cfg=cfg,
        title=SETUP_SLUG,
        workflow_name=SETUP_WORKFLOW,
        contexts=[],
        mode="interactive",
        owner=owner,
        assignee=None,
        watchers=[],
        status="active",
        slug_override=SETUP_SLUG,
        body=SETUP_TICKET_BODY,
    )


__all__ = [
    "SETUP_SLUG",
    "SETUP_WORKFLOW",
    "prompt_eligible",
    "prompt_user_name",
    "scaffold_setup_ticket",
]
