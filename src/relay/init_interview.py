"""Init interview — first-run questions that seed a `relay-setup` ticket.

Runs once, on a fresh `relay init` (never on `--update`; fresh init refuses
to run when `relay-os/` already exists, so once-ness is structural). The
human's answers land verbatim in the Context of an auto-scaffolded
`relay-setup` ticket; launching that ticket has an agent turn the answers
plus a repo scan into durable artifacts — contexts, rules, workflows,
recurring tasks, possibly skills. The generation contract (fact/intent
precedence, stub-and-ask, the open-questions deliverable) lives in the
`init/setup` workflow, not here: this module only collects the human's
words and writes the ticket.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import typer

from relay.config import load_config
from relay.scaffold import scaffold_task


SETUP_WORKFLOW = "init/setup"
SETUP_SLUG = "relay-setup"

# Question text carries the probes the design dry run showed the bare
# questions miss: enumerate instead of summarizing, locate referenced
# documents so the scan can ingest them, anchor cadences a calendar can't
# infer. Asking is the probing.
QUESTIONS: tuple[str, ...] = (
    "What is this repo for? What project or operation does it coordinate, "
    "and what does success look like?",
    "What knowledge does this work depend on that an outsider couldn't get "
    "from reading the repo? The stuff in your head: accounts and tools you "
    "use, vendor quirks, who's who, deadlines, thresholds, things that have "
    "bitten you before. If you mention a document, say where it lives so "
    "the setup agent can read it.",
    "What rules should every agent always follow here? The non-negotiables "
    "— e.g. \"never touch real financial data without asking\", \"never "
    "email anyone external\", \"X is read-only\".",
    "What work comes up repeatedly — and is any of it on a schedule? List "
    "each one rather than summarizing (\"a few year-end processes\" hides "
    "them). Include the cadence, and an anchor date for cadences a calendar "
    "can't infer (bi-weekly: which week?).",
)

SETUP_TICKET_BODY = """\
## Description

Turn the init interview answers below plus a scan of this repo into durable
relay-os artifacts — contexts, rules, workflows, recurring tasks, possibly
skills — so future agents start already knowing the project instead of
starting from zero. Generated files are drafts for the owner's review;
nothing is final without sign-off.

## Context

Interview answers, recorded verbatim at `relay init` on {date}:

{qa}
"""


@dataclass
class InterviewResult:
    """What the interview captured: the user's name and (question, answer) pairs."""

    user: str
    answers: list[tuple[str, str]]


def interview_eligible() -> bool:
    """Only prompt a real human: both ends of the pipe must be a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def run_interview() -> InterviewResult | None:
    """Ask the setup questions. Returns None when the human bails (Ctrl-C/EOF)."""
    typer.echo("")
    typer.secho("Relay setup interview", bold=True)
    typer.echo(
        "Four questions seed a `relay-setup` ticket so future agents start\n"
        "already knowing this repo. Answer in plain prose; finish each answer\n"
        "with an empty line. Ctrl-C skips the interview (relay-os starts empty)."
    )
    try:
        user = typer.prompt("\nYour name (becomes `user` in relay.local.toml)").strip()
        if not user:
            typer.secho("No name given — skipping interview.", fg=typer.colors.YELLOW)
            return None
        answers: list[tuple[str, str]] = []
        for i, question in enumerate(QUESTIONS, 1):
            typer.echo("")
            typer.secho(f"{i}/{len(QUESTIONS)} {question}", bold=True)
            answers.append((question, _read_multiline()))
        return InterviewResult(user=user, answers=answers)
    except (KeyboardInterrupt, EOFError):
        typer.echo("")
        typer.secho(
            "Interview skipped — relay-os starts empty.", fg=typer.colors.YELLOW
        )
        return None


def _read_multiline() -> str:
    """Read lines until an empty one. EOF also ends the answer."""
    lines: list[str] = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def scaffold_setup_ticket(relay_os: Path, interview: InterviewResult) -> dict[str, Any]:
    """Write the `relay-setup` ticket from the interview answers.

    Expects `user` to already be set in relay.local.toml (init writes it from
    the interview before calling) — `load_config` refuses to run otherwise.
    Scaffolded `active` so it is `relay launch`-ready without a manual
    `relay mark active` first. Returns scaffold_task's {slug, path}.
    """
    cfg = load_config(relay_os)
    qa = "\n\n".join(
        f"**Q{i}. {question}**\n\n{answer or '(no answer)'}"
        for i, (question, answer) in enumerate(interview.answers, 1)
    )
    body = SETUP_TICKET_BODY.format(date=date.today().isoformat(), qa=qa)
    return scaffold_task(
        cfg=cfg,
        title=SETUP_SLUG,
        workflow_name=SETUP_WORKFLOW,
        contexts=[],
        mode="interactive",
        owner=interview.user,
        assignee=None,
        watchers=[],
        status="active",
        slug_override=SETUP_SLUG,
        body=body,
    )


__all__ = [
    "QUESTIONS",
    "SETUP_SLUG",
    "SETUP_WORKFLOW",
    "InterviewResult",
    "interview_eligible",
    "run_interview",
    "scaffold_setup_ticket",
]
