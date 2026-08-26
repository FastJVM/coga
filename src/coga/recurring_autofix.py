"""Post-sweep autofix loop: analyze one recurring run, ticket what broke.

`coga recurring` prints what it did and exits. That console output is the only
place a failing `ticket.py`, a wedged agent REPL, or a refused forced launch is
ever described, and under cron nobody reads it. This module keeps that output
exactly as it is and closes the loop around it: the sweep records what actually
happened, one agent call reads that record, and a real problem becomes an
`active` ticket under `coga/tasks/autofix/` that the next `coga megalaunch`
picks up.

Three properties keep this inside Coga's grain:

- **The analysis call is text-only.** It is the one place Coga spawns an agent
  without a PTY, so by construction it cannot answer a permission prompt or
  drive a REPL. It receives a run record and returns a verdict plus a ticket
  body; every mutation — ticket creation, git sync, notification — stays on the
  ordinary deterministic paths in this file. That is why it is a *recipe*
  (`coga run autofix-analyze`) and not a second launch seam: unattended work
  belongs behind the registered recipe surface.
- **The record is built, not scraped.** The sweep hands us structured outcomes
  as it goes. We cannot tee fd 1 to capture the console verbatim — redirecting
  it would make `isatty` false and every interactive agent launch would refuse
  itself. So each task contributes its *outcome* (how the launch ended, the
  ticket's status afterwards) plus the period task's **blackboard**, which is
  where a `ticket.py` phase and an agent session both already write what they
  found. That is the durable report channel Coga already has; the console is
  not.
- **The loop is repetition-aware.** It runs after every sweep, so a template
  that fails every night would mint a ticket every night. The open `autofix/`
  tickets go into the prompt and the analyst answers `duplicate` instead.

One thing the record inherits: a period task's blackboard travels verbatim into
the analysis prompt and, when a ticket is created, into a committed
`run-log.md`. Coga never logs a resolved secret value itself, and a `ticket.py`
phase must not write one to its blackboard either — that rule now has a second
consequence.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import typer

from coga import git
from coga.config import AgentType, Config, ConfigError
from coga.create import create_task
from coga.lifecycle import TERMINAL_STATUSES
from coga.notification import post
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import TicketError

# The sub-directory under `tasks/` every autofix ticket lands in. A plain
# directory — `mkdir`/`mv`/`rm` manage it like any other (principle 3).
AUTOFIX_DIRECTORY = "autofix"

# Autofix tickets are created `active`, so they need a frozen workflow (the
# activation gate refuses a workflow-less non-draft ticket). `with-self-review`
# ends at an owner PR review, which is where the human judgment belongs, and it
# carries the `already-satisfied` path — an autofix ticket whose problem turns
# out to be transient closes itself with evidence instead of inventing a change.
AUTOFIX_WORKFLOW = "code/with-self-review"

RUN_LOG_FILENAME = "run-log.md"

# Built-in one-shot argv for the CLIs Coga knows, mirroring
# `DEFAULT_DISCUSSION_TEMPLATES` in `commands/launch.py`. Overridable per agent
# with `[agents.<name>].analyze`; an unknown CLI with no override skips the
# analysis loudly rather than guessing.
DEFAULT_ANALYZE_TEMPLATES = {
    "claude": "-p {prompt}",
    "codex": "exec {prompt}",
}

# The analyst is a single call on a bounded record — generous, but it must not
# become the new way a cron sweep hangs forever. `COGA_AUTOFIX_TIMEOUT`
# (seconds) overrides; `COGA_AUTOFIX=0` disables the loop entirely.
#
# The bound is on the *analysis*, not on each subprocess inside it: the first
# attempt, the `claude auth status` probe, and the subscription retry all draw
# on one deadline. Giving the retry a fresh full timeout would let a configured
# 300s turn into 610s of wall clock and make the documented liveness bound a
# lie (principle 6). The auth probe additionally caps itself at
# `_CLAUDE_AUTH_STATUS_TIMEOUT_SECONDS` so a hung status call cannot eat the
# whole budget the retry still needs.
_ANALYZE_TIMEOUT_SECONDS = 300.0
_CLAUDE_AUTH_STATUS_TIMEOUT_SECONDS = 10.0

_CLAUDE_API_KEY_ENV = "ANTHROPIC_API_KEY"
_CLAUDE_AUTH_ROUTING_ENV = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_CUSTOM_HEADERS",
)
_CLAUDE_SUBSCRIPTION_TYPES = frozenset({"enterprise", "max", "pro", "team"})
_CLAUDE_AUTH_FAILURE_MARKERS = (
    "authentication_error",
    "authentication failed",
    "billing_error",
    "credit balance",
    "invalid api key",
    "payment required",
    "unauthorized",
)

# Linux caps one argv element at 128 KiB and the prompt rides argv, so the
# record is budgeted well under that. Each blackboard keeps its *tail* — a run
# appends its findings, so the newest writing is the relevant writing.
_MAX_BLACKBOARD_CHARS_PER_TASK = 4000
_MAX_RECORD_CHARS = 48000

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


class AutofixUnavailable(Exception):
    """The analysis could not run. Loud, but never fatal to the sweep."""


# --- the run record -----------------------------------------------------------


@dataclass
class TaskOutcome:
    """What one period task did in this sweep.

    Since every template dispatches through a single `coga launch` call, there
    is no per-kind branch to mirror here: `result` says how the launch ended,
    `final_status` says where it left the ticket, and `blackboard` carries what
    the run itself reported.
    """

    template: str
    slug: str
    result: str  # "completed" | "failed" | "timed-out" | "unfinished" | "refused"
    exit_code: int | None = None
    final_status: str | None = None
    detail: str = ""
    blackboard: str = ""

    @property
    def is_problem(self) -> bool:
        return self.result != "completed"


@dataclass
class RunRecord:
    """One recurring sweep, as the analyst sees it.

    Accumulated by `run_recurring_scan` while it works, so the record reflects
    what happened rather than what the console happened to print.
    """

    started: datetime
    repo: str = ""
    # Set to the template name for an on-demand `coga recurring launch <name>`
    # (the `coga dream` / `coga autoclose` / `coga skill-update` aliases), so
    # the analyst is not told a one-template run was a scheduled sweep that
    # somehow scanned nothing.
    on_demand: str = ""
    force: bool = False
    interactive: bool = False
    agent_override: str | None = None
    scan_lines: list[str] = field(default_factory=list)
    scan_errors: list[tuple[str, str]] = field(default_factory=list)
    outcomes: list[TaskOutcome] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def note(self, text: str) -> None:
        """Record a sweep-level line (a refusal, a summary, an early exit)."""
        self.notes.append(text.strip())

    def add(self, outcome: TaskOutcome) -> None:
        self.outcomes.append(outcome)

    @property
    def problems(self) -> list[TaskOutcome]:
        return [o for o in self.outcomes if o.is_problem]

    def render(self) -> str:
        """The run record as the markdown the analyst reads."""
        mode = []
        if self.force:
            mode.append("--force")
        if self.interactive:
            mode.append("--interactive")
        if self.agent_override:
            mode.append(f"--agent {self.agent_override}")

        if self.on_demand:
            title = f"Recurring launch: {self.on_demand}"
            default_mode = f"on-demand `coga recurring launch {self.on_demand}`"
        else:
            title = "Recurring sweep"
            default_mode = "bare sweep"

        lines = [
            f"# {title} — {self.started:%Y-%m-%d %H:%M:%S}",
            "",
            f"- repo: {self.repo or '(unknown)'}",
            f"- mode: {' '.join(mode) if mode else default_mode}",
        ]
        if not self.on_demand:
            lines.append(f"- templates scanned: {len(self.scan_lines)}")
        lines += [
            f"- tasks run: {len(self.outcomes)}",
            f"- problems: {len(self.problems)}",
            "",
        ]

        if self.scan_lines:
            lines += ["## Scan", "", "```"]
            lines += self.scan_lines
            lines += ["```", ""]

        if self.scan_errors:
            lines += ["## Template errors", ""]
            lines += [f"- `{name}`: {msg}" for name, msg in self.scan_errors]
            lines.append("")

        if self.outcomes:
            lines += ["## Task outcomes", ""]
            for outcome in self.outcomes:
                head = f"### {outcome.slug} — {outcome.result}"
                lines += [head, ""]
                lines.append(f"- template: `{outcome.template}`")
                if outcome.exit_code is not None:
                    lines.append(f"- exit code: {outcome.exit_code}")
                if outcome.final_status:
                    lines.append(
                        f"- ticket status after the run: {outcome.final_status}"
                    )
                if outcome.detail:
                    lines.append(f"- note: {outcome.detail}")
                lines.append("")
                body = _tail(
                    _strip_ansi(outcome.blackboard), _MAX_BLACKBOARD_CHARS_PER_TASK
                )
                if body.strip():
                    lines += [
                        "What the run wrote to its blackboard:",
                        "",
                        "```",
                        body.rstrip(),
                        "```",
                        "",
                    ]

        if self.notes:
            lines += ["## Sweep notes", ""]
            lines += [f"- {note}" for note in self.notes]
            lines.append("")

        return _tail("\n".join(lines), _MAX_RECORD_CHARS)


def _strip_ansi(text: str) -> str:
    """Drop terminal control sequences captured from a child's colored output."""
    return _ANSI_RE.sub("", text)


def _tail(text: str, limit: int) -> str:
    """Keep the last `limit` characters — a failing child explains itself last."""
    if len(text) <= limit:
        return text
    return "[... truncated ...]\n" + text[-limit:]


# --- reading what a run reported ----------------------------------------------


def outcome_for_ref(cfg: Config, ref: TaskRef | None) -> str | None:
    """Ticket status after a run, or None when the task is gone."""
    if ref is None or not ref.ticket_path.exists():
        return None
    try:
        return read_ticket(ref).status
    except TicketError:
        return None


def blackboard_for_ref(ref: TaskRef | None) -> str:
    """What the run wrote about itself, or "" when there is nothing to read.

    The blackboard is the report channel a `ticket.py` phase and an agent
    session both already write to, which is why the record reads it instead of
    trying to capture console bytes. Best-effort by design: a period task that
    was reaped, or a ticket too malformed to parse, still leaves an outcome
    worth analyzing.
    """
    if ref is None or not ref.ticket_path.exists():
        return ""
    try:
        return read_blackboard(ref.ticket_path, blackboard_required=False)
    except (TaskFileError, OSError):
        return ""


# --- the analysis call --------------------------------------------------------


@dataclass
class Analysis:
    """The analyst's answer, parsed."""

    verdict: str  # "ok" | "problem" | "duplicate"
    title: str
    body: str
    duplicate_of: str = ""
    raw: str = ""


def autofix_enabled() -> bool:
    """`COGA_AUTOFIX=0` (or `false`/`off`/`no`) disables the loop."""
    value = os.environ.get("COGA_AUTOFIX", "").strip().lower()
    return value not in {"0", "false", "off", "no"}


def _analyze_timeout() -> float | None:
    raw = os.environ.get("COGA_AUTOFIX_TIMEOUT", "").strip()
    if not raw:
        return _ANALYZE_TIMEOUT_SECONDS
    try:
        seconds = float(raw)
    except ValueError:
        return _ANALYZE_TIMEOUT_SECONDS
    return seconds if seconds > 0 else None


def _analyze_deadline(budget: float | None) -> float | None:
    """The monotonic instant the whole analysis must be finished by."""
    return None if budget is None else time.monotonic() + budget


def _remaining(deadline: float | None, cap: float | None = None) -> float | None:
    """Seconds left on the shared analysis budget, further capped by `cap`.

    Returns `None` only when nothing bounds the call at all. A non-positive
    result means the budget is spent — callers must not start another
    subprocess with it.
    """
    if deadline is None:
        return cap
    left = deadline - time.monotonic()
    return left if cap is None else min(left, cap)


def _analyze_agent(cfg: Config, agent_override: str | None) -> AgentType:
    if agent_override:
        return cfg.agent_type(agent_override)
    agent = cfg.default_agent()
    if agent is None:
        raise AutofixUnavailable(
            "no `[agents.*]` table is configured, so there is no CLI to run "
            "the analysis with"
        )
    return agent


def build_analyze_command(agent: AgentType, prompt: str) -> list[str]:
    """Argv for the one-shot analysis call.

    Mirrors `build_agent_command`'s discussion path: the configured
    `[agents.<name>].analyze` template wins, then the built-in template for a
    known CLI. There is deliberately no positional fallback — spawning an
    unknown CLI with a bare prompt would open an interactive REPL nobody can
    drive, which is exactly the hang this loop exists to report.
    """
    template = agent.analyze or DEFAULT_ANALYZE_TEMPLATES.get(Path(agent.cli).name, "")
    if not template:
        raise AutofixUnavailable(
            f"agent type {agent.name!r} (cli {agent.cli!r}) has no one-shot "
            "analysis argv. Set `[agents."
            f"{agent.name}].analyze` in coga.toml to the CLI's "
            'non-interactive form, e.g. analyze = "-p {prompt}".'
        )
    tokens = [tok.replace("{prompt}", prompt) for tok in shlex.split(template)]
    return [agent.cli, *tokens]


def _claude_subscription_fallback_env(
    agent: AgentType,
    failed: subprocess.CompletedProcess[str],
    env: dict[str, str],
    *,
    cwd: Path,
    deadline: float | None = None,
) -> dict[str, str] | None:
    """A verified Claude subscription env after an API-key auth failure.

    Claude Code gives an ambient ``ANTHROPIC_API_KEY`` precedence over its
    signed-in claude.ai account. That is normally the caller's intended auth
    choice, so a working key is never replaced. When the key fails for an auth
    or billing reason, however, the recurring analyst can recover through the
    already-authenticated CLI account instead of losing the whole autofix
    pass. The fallback stays deliberately narrow: only the built-in Claude
    argv with standard auth routing can be checked by the separate status
    command, and that command must report an entitled first-party subscription
    allowed by local login policy. API-key-only installations keep the original
    failure.

    The probe spends the caller's remaining analysis budget rather than its own
    extra time: an exhausted budget declines the fallback, exactly as an
    unreachable or unentitled status call already does.
    """
    if (
        failed.returncode == 0
        or Path(agent.cli).name != "claude"
        or agent.analyze
        or not env.get(_CLAUDE_API_KEY_ENV)
        or any(env.get(name) for name in _CLAUDE_AUTH_ROUTING_ENV)
    ):
        return None
    detail = "\n".join((failed.stdout or "", failed.stderr or "")).lower()
    if not any(marker in detail for marker in _CLAUDE_AUTH_FAILURE_MARKERS):
        return None

    probe_timeout = _remaining(deadline, _CLAUDE_AUTH_STATUS_TIMEOUT_SECONDS)
    if probe_timeout is not None and probe_timeout <= 0:
        return None

    fallback_env = dict(env)
    fallback_env.pop(_CLAUDE_API_KEY_ENV, None)
    try:
        status = subprocess.run(
            [agent.cli, "auth", "status"],
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
            env=fallback_env,
            timeout=probe_timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if status.returncode != 0:
        return None
    try:
        payload = json.loads(status.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    subscription_type = payload.get("subscriptionType")
    if (
        payload.get("loggedIn") is not True
        or payload.get("authMethod") != "claude.ai"
        or payload.get("apiKeySource")
        or payload.get("apiProvider") not in (None, "firstParty")
        or payload.get("forcedLoginMethod") not in (None, "claudeai")
        or not isinstance(subscription_type, str)
        or subscription_type.casefold() not in _CLAUDE_SUBSCRIPTION_TYPES
    ):
        return None
    return fallback_env


def open_autofix_tickets(cfg: Config) -> list[tuple[str, str, str]]:
    """Live `autofix/` tickets as `(slug, title, status)` — the dedupe input."""
    out: list[tuple[str, str, str]] = []
    for ref in list_tasks(cfg):
        if ref.directory != AUTOFIX_DIRECTORY:
            continue
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status in TERMINAL_STATUSES:
            continue
        out.append((ref.id_slug, ticket.title or "", ticket.status or "?"))
    return out


def build_prompt(record_text: str, existing: list[tuple[str, str, str]]) -> str:
    """The analysis prompt: what the run did, what is already ticketed."""
    if existing:
        listed = "\n".join(
            f"- {slug} — \"{title}\" ({status})" for slug, title, status in existing
        )
    else:
        listed = "(none)"

    return f"""You are Coga's recurring-sweep analyst. Coga is a markdown-first,
git-backed company OS. `coga recurring` scans the templates under
`coga/recurring/`, materializes each due period's task, and runs it — either as
a deterministic registered recipe or as an agent session. Below is the record
of one such sweep, followed by the autofix tickets that are already open.

Your job is to decide whether this run shows a problem worth fixing in the
repo, and if so to write the ticket that fixes it.

What counts as a problem: a recipe that exited non-zero, an agent run that
timed out or ended unfinished, a template that failed to load, a task left in a
stuck state, or output that shows a real error, crash, or misconfiguration —
including one hiding behind a zero exit code (a job that silently did nothing
it was supposed to do, a report full of errors it did not fail on).

What is NOT a problem: a clean run, a template that was simply not due, work
that was skipped for a normal documented reason, or an already-known issue that
matches one of the open autofix tickets below.

--- RUN RECORD ---
{record_text}
--- END RUN RECORD ---

Open autofix tickets:
{listed}

You may read files in this repository to understand a failure before deciding.
Do not modify anything and do not run any coga command — Coga creates the
ticket itself from your reply.

Reply with EXACTLY this shape and nothing else:

VERDICT: ok
  — when the run is healthy or everything of note is already ticketed above.

VERDICT: duplicate
DUPLICATE: <slug of the open autofix ticket that already covers it>
  — when the problem is real but already ticketed.

VERDICT: problem
TITLE: <one imperative line, at most 70 characters, naming the fix>
---
<markdown body: what broke, the evidence from the record above, where in the
repo it most likely lives, and what a fix would have to do. Write it as the
Description of a ticket an engineer will pick up cold — no greeting, no
sign-off.>
"""


def parse_analysis(raw: str) -> Analysis:
    """Parse the analyst's reply.

    Fail *toward* surfacing: an unparseable reply is treated as a problem
    carrying the raw text, because the alternative is a broken analyst quietly
    swallowing every failure it was hired to report (principle 6).
    """
    text = raw.strip()
    verdict_match = re.search(
        r"(?mi)^\s*VERDICT:\s*(ok|problem|duplicate)\b", text
    )
    verdict = verdict_match.group(1).lower() if verdict_match else "problem"

    if verdict == "ok":
        return Analysis(verdict="ok", title="", body="", raw=text)

    if verdict == "duplicate":
        dup = re.search(r"(?mi)^\s*DUPLICATE:\s*(\S+)", text)
        return Analysis(
            verdict="duplicate",
            title="",
            body="",
            duplicate_of=dup.group(1) if dup else "",
            raw=text,
        )

    title_match = re.search(r"(?mi)^\s*TITLE:\s*(.+)$", text)
    if title_match:
        title = title_match.group(1).strip()
        after_title = text[title_match.end():]
    else:
        # No TITLE line at all: the reply is off-contract, so keep the whole
        # thing as the body and take the first real line as the title rather
        # than dropping a finding on the floor.
        title = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        after_title = text

    body = re.sub(r"^\s*-{3,}\s*\n", "", after_title.lstrip("\n"), count=1)
    body = body.strip()
    if not title:
        title = "Recurring sweep reported a problem"
    return Analysis(
        verdict="problem",
        title=_clip_title(title),
        body=body or text,
        raw=text,
    )


def _clip_title(title: str) -> str:
    """Ticket titles are one line; a slug is derived from this."""
    single = " ".join(title.replace("`", "").split())
    if len(single) <= 70:
        return single
    return single[:67].rstrip() + "..."


def analyze_record(
    cfg: Config, record_text: str, *, agent_override: str | None = None
) -> Analysis:
    """Run the one-shot analysis call and parse its reply."""
    agent = _analyze_agent(cfg, agent_override)
    if shutil.which(agent.cli) is None:
        raise AutofixUnavailable(
            f"agent CLI {agent.cli!r} is not on PATH, so the run cannot be "
            "analyzed"
        )
    prompt = build_prompt(record_text, open_autofix_tickets(cfg))
    cmd = build_analyze_command(agent, prompt)
    cwd = cfg.repo_root.parent if cfg.repo_root.name == "coga" else cfg.repo_root
    env = os.environ.copy()
    used_subscription_fallback = False
    # One budget for the whole analysis — first attempt, auth probe, and retry
    # all draw down the same deadline, so `COGA_AUTOFIX_TIMEOUT` still bounds
    # what the sweep waits for when the fallback fires.
    budget = _analyze_timeout()
    deadline = _analyze_deadline(budget)
    try:
        while True:
            attempt_timeout = _remaining(deadline)
            if attempt_timeout is not None and attempt_timeout <= 0:
                raise subprocess.TimeoutExpired(cmd, budget or 0.0)
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                errors="replace",
                env=env,
                timeout=attempt_timeout,
                check=False,
            )
            if used_subscription_fallback:
                break
            fallback_env = _claude_subscription_fallback_env(
                agent, result, env, cwd=cwd, deadline=deadline
            )
            if fallback_env is None:
                break
            typer.secho(
                "Autofix: Claude API-key authentication failed; retrying with "
                "the signed-in claude.ai subscription.",
                fg=typer.colors.YELLOW,
                err=True,
            )
            used_subscription_fallback = True
            env = fallback_env
    except FileNotFoundError as exc:
        raise AutofixUnavailable(f"could not run {agent.cli!r}: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        # Report the configured bound, not whatever slice of it this attempt
        # got: the operator set `COGA_AUTOFIX_TIMEOUT`, and a retry that
        # inherited 40s of a 300s budget did not "fail within 40s".
        bound = budget if budget is not None else exc.timeout
        raise AutofixUnavailable(
            f"{agent.cli} did not answer within {bound:.0f}s"
        ) from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise AutofixUnavailable(
            f"{agent.cli}"
            + (" subscription retry" if used_subscription_fallback else "")
            + f" exited {result.returncode}"
            + (f": {_tail(detail, 500)}" if detail else "")
        )
    if not (result.stdout or "").strip():
        raise AutofixUnavailable(f"{agent.cli} returned an empty analysis")
    return parse_analysis(result.stdout)


# --- ticketing the finding ----------------------------------------------------


def create_autofix_ticket(
    cfg: Config, analysis: Analysis, *, run_log: str
) -> tuple[str, Path]:
    """Create the `active` autofix ticket and drop the run log beside it."""
    result = create_task(
        cfg=cfg,
        title=analysis.title,
        workflow_name=AUTOFIX_WORKFLOW,
        contexts=[],
        owner=cfg.current_user,
        assignee=None,
        watchers=[],
        status="active",
        directory=AUTOFIX_DIRECTORY,
        description=_ticket_description(analysis),
        force_directory=True,
        created_by="system",
    )
    task_dir = Path(result["path"])
    (task_dir / RUN_LOG_FILENAME).write_text(run_log)
    return result["slug"], task_dir


def _ticket_description(analysis: Analysis) -> str:
    """The ticket body: the finding, then what the reader should distrust."""
    trailer = "\n".join(
        (
            "Written by the `coga recurring` autofix loop from the sweep this",
            f"ticket's `{RUN_LOG_FILENAME}` records. The finding is an agent's",
            "reading of that run, not a verified diagnosis: confirm it against",
            f"`{RUN_LOG_FILENAME}` before changing anything, and close the ticket",
            "through the workflow's already-satisfied path if the problem was",
            "transient or already fixed.",
        )
    )
    return f"{analysis.body}\n\n---\n\n{trailer}"


def write_run_log(cfg: Config, record: RunRecord, *, rendered: str = "") -> Path:
    """Persist the run record machine-locally, whether or not it gets ticketed.

    `.coga/` is gitignored: one operator's sweep transcript is machine state,
    not team state. A ticketed finding gets its own committed copy inside the
    task directory.
    """
    path = (
        cfg.repo_root
        / ".coga"
        / "recurring-runs"
        / f"{record.started:%Y%m%dT%H%M%S}.md"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered or record.render())
    return path


# --- the loop -----------------------------------------------------------------


def run_autofix(
    cfg: Config, record: RunRecord, *, agent_override: str | None = None
) -> None:
    """Analyze one finished sweep and ticket what it found.

    Never raises: the sweep's own exit code is its report on the work it ran,
    and a broken analyst must not rewrite it. Every failure here is loud on
    stderr instead.
    """
    if not autofix_enabled():
        return
    if not record.outcomes and not record.scan_errors and not record.notes:
        # Nothing was scanned — an early refusal, not a run. There is no record
        # to analyze and inventing one would only burn a call.
        return

    run_log = record.render()
    try:
        log_path = write_run_log(cfg, record, rendered=run_log)
    except OSError as exc:
        typer.secho(
            f"Autofix: could not write the run log: {exc}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return

    typer.echo(f"\nAutofix: analyzing this run ({log_path})...")
    try:
        analysis = analyze_record(cfg, run_log, agent_override=agent_override)
    except Exception as exc:  # noqa: BLE001 — never fail the sweep on the analyst
        typer.secho(
            f"Autofix: analysis skipped — {exc}", fg=typer.colors.YELLOW, err=True
        )
        return

    if analysis.verdict == "ok":
        typer.secho("Autofix: no problem found in this run.", fg=typer.colors.GREEN)
        return
    if analysis.verdict == "duplicate":
        known = analysis.duplicate_of or "an open autofix ticket"
        typer.secho(
            f"Autofix: problem already tracked by {known}; no new ticket.",
            fg=typer.colors.YELLOW,
        )
        return

    try:
        slug, task_dir = create_autofix_ticket(cfg, analysis, run_log=run_log)
    except Exception as exc:  # noqa: BLE001 — report it even if unfilable
        typer.secho(
            f"Autofix: could not create the ticket — {exc}\n"
            f"The analysis is preserved at {log_path}:\n{analysis.raw}",
            fg=typer.colors.RED,
            err=True,
        )
        return

    typer.secho(
        f"Autofix: created {slug} — {analysis.title}", fg=typer.colors.CYAN, bold=True
    )
    git.sync_task_state(cfg, task_dir, message=f"Autofix: {slug} — created")
    post(
        cfg,
        f"🩹 autofix created *{slug}* \"{analysis.title}\" "
        "from the recurring sweep",
        task_path=task_dir,
        owner=cfg.current_user,
        watchers=[],
    )


# --- recipe surface -----------------------------------------------------------


def run_autofix_analyze_recipe(cfg: Config, argv: list[str]) -> int:
    """`coga run autofix-analyze <run-log.md>` — analyze a recorded run.

    The sweep calls the loop in-process; this is the same analysis over a run
    log already on disk, so an operator can re-run a finding by hand (or from
    another scheduler) without re-running the sweep that produced it.
    """
    parser = argparse.ArgumentParser(
        prog="coga run autofix-analyze",
        description="Analyze a recorded recurring run and ticket any problem.",
    )
    parser.add_argument(
        "run_log",
        nargs="?",
        help="Path to a run log written by a sweep. Defaults to the most "
        "recent one under .coga/recurring-runs/.",
    )
    parser.add_argument("--agent")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the analysis without creating a ticket.",
    )
    args = parser.parse_args(argv)

    path = _resolve_run_log(cfg, args.run_log)
    if path is None:
        typer.secho(
            "No run log to analyze — pass a path, or run `coga recurring` "
            "first to produce one under .coga/recurring-runs/.",
            fg=typer.colors.RED,
            err=True,
        )
        return 2

    record_text = path.read_text()
    try:
        analysis = analyze_record(cfg, record_text, agent_override=args.agent)
    except (AutofixUnavailable, ConfigError) as exc:
        typer.secho(
            f"Autofix: analysis skipped — {exc}", fg=typer.colors.RED, err=True
        )
        return 1

    if analysis.verdict == "ok":
        typer.echo(f"{path.name}: no problem found.")
        return 0
    if analysis.verdict == "duplicate":
        typer.echo(
            f"{path.name}: already tracked by "
            f"{analysis.duplicate_of or 'an open autofix ticket'}."
        )
        return 0

    if args.dry_run:
        typer.echo(f"{path.name}: problem — {analysis.title}\n\n{analysis.body}")
        return 0

    slug, task_dir = create_autofix_ticket(cfg, analysis, run_log=record_text)
    typer.echo(f"{path.name}: created {slug} — {analysis.title}")
    git.sync_task_state(cfg, task_dir, message=f"Autofix: {slug} — created")
    post(
        cfg,
        f"🩹 autofix created *{slug}* \"{analysis.title}\" from {path.name}",
        task_path=task_dir,
        owner=cfg.current_user,
        watchers=[],
    )
    return 0


def _resolve_run_log(cfg: Config, given: str | None) -> Path | None:
    if given:
        path = Path(given).expanduser()
        return path if path.is_file() else None
    runs = cfg.repo_root / ".coga" / "recurring-runs"
    if not runs.is_dir():
        return None
    logs = sorted(runs.glob("*.md"))
    return logs[-1] if logs else None


def scan_lines_for_record(scan, *, force: bool = False) -> list[str]:
    """Plain-text mirror of the console scan table, for the run record.

    Deliberately a separate rendering from `_print_table`: the console gets
    color and the record gets stable, greppable text. The record is read by an
    agent, so ANSI in it is noise at best.
    """
    from coga.recurring_runner import _firing_label

    now = datetime.now()
    lines: list[str] = []
    for task in scan.tasks:
        when = _firing_label(task.last_fire, now)
        if task.ref is None:
            action = "skip (ran this period)"
        elif task.resuming:
            action = "resume"
        elif task.launchable or force:
            action = "launch"
        else:
            action = f"skip ({task.status})"
        lines.append(f"{task.template:<20} {when:<26} {action}")
    return lines
