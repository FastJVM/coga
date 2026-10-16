"""Clone-scoped recurring templates: per-clone work with no shared period task.

A recurring template is `scope: repo` by default: one shared period task per
firing, serviced by whichever clone sweeps first and recorded in `coga/log.md`.
That is wrong for work on clone- or machine-local state — local branch refs,
linked worktrees, machine-local `[upstream]` paths — because every other clone
of the repository never runs it. A `scope: clone` template is instead serviced
once per period *in every clone*: the sweep runs its reserved `ticket.py`
directly, with no period task or log line, and records the serviced period in
a clone-local ledger under the primary checkout's `.coga/`. The runner makes
no commit; a template may publish its own state under the scheduling contract.

The ledger lives in the primary checkout (resolved through git's common dir),
not in whichever working tree the sweep ran from, so a run serviced from a
temporary control worktree still counts for the clone that owns it.

The `coga/recurring/scheduling` context owns this contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from coga import git
from coga.atomicio import atomic_write_text
from coga.config import Config, build_launch_env
from coga.task_env import TASK_ENV_KEYS, host_repo_root

SCOPE_REPO = "repo"
SCOPE_CLONE = "clone"
SCOPES = (SCOPE_REPO, SCOPE_CLONE)

# What a clone-scoped `ticket.py` can read to tell it is not inside a period
# task (no `COGA_TASK_SLUG`, nothing to bump) and which period it services.
SCOPE_ENV = "COGA_RECURRING_SCOPE"
TEMPLATE_ENV = "COGA_RECURRING_TEMPLATE"
PERIOD_ENV = "COGA_RECURRING_PERIOD"

_STATE_DIR = Path(".coga") / "recurring-clone"
# Bounded so a chatty run cannot grow the run record without limit.
_OUTPUT_TAIL_CHARS = 4000


@dataclass(frozen=True)
class CloneLedgerEntry:
    period: str
    serviced_at: str


@dataclass(frozen=True)
class CloneRunResult:
    template: str
    period: str
    exit_code: int
    output: str
    log_path: Path


def clone_state_dir(cfg: Config) -> Path:
    """The clone-local state directory, anchored at the primary checkout.

    A linked worktree (the temporary control worktree `--all` services an
    off-control clone from) shares refs with its primary, so it records against
    the primary's Coga workspace at the same relative path. Outside git, or when
    git cannot say, the invoking workspace is the clone.
    """
    root = cfg.repo_root
    if cfg.git_enabled:
        try:
            top = git.toplevel(root)
        except git.GitError:
            top = None
        if top is not None:
            try:
                common = Path(
                    git.run_git(
                        top, "rev-parse", "--path-format=absolute", "--git-common-dir"
                    ).strip()
                )
            except git.GitError:
                common = None
            if common is not None and common.name == ".git":
                primary = common.parent
                try:
                    rel = cfg.repo_root.resolve().relative_to(top.resolve())
                except ValueError:
                    rel = Path()
                root = primary / rel
    return root / _STATE_DIR


def _ledger_path(cfg: Config, name: str) -> Path:
    return clone_state_dir(cfg) / f"{name}.json"


def _log_path(cfg: Config, name: str) -> Path:
    return clone_state_dir(cfg) / f"{name}.log"


def read_clone_ledger(cfg: Config, name: str) -> CloneLedgerEntry | None:
    """The last period this clone serviced for `name`, or `None`.

    An unreadable or malformed ledger file reads as never serviced: the cost is
    one extra run of an idempotent per-clone job, never a skipped one.
    """
    path = _ledger_path(cfg, name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("period"), str):
        return None
    return CloneLedgerEntry(
        period=data["period"], serviced_at=str(data.get("serviced_at", ""))
    )


def record_clone_period(cfg: Config, name: str, period: str, now: datetime) -> None:
    path = _ledger_path(cfg, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        json.dumps(
            {"period": period, "serviced_at": now.isoformat(timespec="seconds")},
            indent=2,
        )
        + "\n",
    )


def run_clone_template(
    cfg: Config,
    name: str,
    script: Path,
    period: str,
    *,
    secrets: object = None,
    now: datetime | None = None,
) -> CloneRunResult:
    """Run one clone-scoped template's `ticket.py` and record a clean exit.

    The script runs from the host repository with the template's declared
    secrets and none of the period-task variables, so a shim that would bump a
    task cannot find one. Output is echoed, kept in a per-template log beside
    the ledger, and returned for the sweep's run record. Only exit 0 advances
    the ledger; a failure is retried by the next sweep.
    """
    now = now or datetime.now()
    env = build_launch_env(cfg, secrets)
    for key in TASK_ENV_KEYS:
        env.pop(key, None)
    env["COGA_COGA_OS_ROOT"] = str(cfg.repo_root.resolve())
    env["COGA_REPO_ROOT"] = str(host_repo_root(cfg).resolve())
    env[SCOPE_ENV] = SCOPE_CLONE
    env[TEMPLATE_ENV] = name
    env[PERIOD_ENV] = period
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=host_repo_root(cfg),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = completed.stdout or ""
    sys.stdout.write(output)
    log_path = _log_path(cfg, name)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            log_path,
            f"# {name} — period {period} — {now.isoformat(timespec='seconds')} "
            f"— exit {completed.returncode}\n\n{output}",
        )
    except OSError as exc:
        sys.stderr.write(f"Warning: could not write {log_path}: {exc}\n")
    if completed.returncode == 0:
        record_clone_period(cfg, name, period, now)
    return CloneRunResult(
        template=name,
        period=period,
        exit_code=completed.returncode,
        output=output[-_OUTPUT_TAIL_CHARS:],
        log_path=log_path,
    )

