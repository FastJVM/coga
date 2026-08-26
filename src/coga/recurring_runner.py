"""Recurring scan and launch orchestration shared by command heads and recipes."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import shutil
import sys
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import typer

from coga import git
from coga.aliases import DEFAULT_ALIASES, validate_aliases
from coga.commands.launch import _interactive_stdio_has_tty
from coga.config import (
    Config,
    ConfigError,
    load_config,
    parse_owner,
)
from coga.lifecycle import TERMINAL_STATUSES
from coga.logfile import append_log, ref_tag_for_path, task_log_lines
from coga.paths import log_path
from coga.taskfile import read_blackboard
from coga.recurring import (
    DueTask,
    DueScan,
    RecurringError,
    Template,
    frozen_task_delegate,
    format_serviced_log,
    parse_serviced_period_entries,
    parse_serviced_period_entries_reverse,
    period_key_at_least,
    read_serviced_ledger,
    recurring_dir,
    resolve_agent_delegate,
    create_named,
    scan_due,
)
from coga.recurring_autofix import (
    RunRecord,
    TaskOutcome,
    blackboard_for_ref,
    outcome_for_ref,
    run_autofix,
    scan_lines_for_record,
)
from coga.period_state import SNAPSHOT_FILE, parse_keys
from coga.mark import (
    BlackboardNeedsSynthesis,
    RequiredExtensionMissing,
    StrandedProductCode,
    WorkflowMissing,
    format_blackboard_synthesis_refusal,
    mark_active,
    mark_done,
    mark_in_progress,
    mark_paused,
    prepare_active,
)
from coga.notification import digest_spool_path, notify
from coga.repl_supervisor import _TIMEOUT_EXIT_CODE
from coga.tasks import TaskRef, read_ticket
from coga.ticket import Ticket, TicketError
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError
from coga.workspace_discovery import discover_coga_repos

# Default idle-timeout backstop (seconds) the sweep arms on the interactive
# REPLs it spawns: one that stalls or crashes before signalling done would
# otherwise block the sequential sweep forever — the hang this command was seen
# to hit. Generous enough that a slow-but-progressing agent (which streams PTY
# output) never trips it; only a genuinely silent REPL does. `--interactive`
# (a human driving by hand) leaves it off; `COGA_REPL_IDLE_TIMEOUT` overrides
# the window or, at `<= 0` / non-finite, disarms it.
_RECURRING_IDLE_TIMEOUT_SECONDS = 900.0


def recurring_owner_refusal(cfg: Config) -> str | None:
    """Why this operator may not launch recurring here, or None if they may.

    Recurring sweeps mutate shared period state (the created period task and
    the repo-global serviced-period ledger) and then launch real
    work, so two *different* operators sweeping the same repo from their own
    clones race each other. The committed `owner` in `coga.toml` picks one of
    them: every clone reads the same name, and only the operator whose
    machine-local `user` matches it may launch.

    A **policy gate, not a lock.** Same-machine overlap is already prevented by
    the sweep being sequential and foreground; the owner running two clones of
    their own can still race, and this does not try to stop them. `--force` is
    gated too — a deliberate takeover is a committed `owner` change, not a
    flag. A repo with no `owner` set behaves exactly as before.
    """
    return _recurring_owner_refusal(cfg, cfg.owner)


def _recurring_owner_refusal(cfg: Config, owner: str) -> str | None:
    """Apply the owner policy using an explicitly resolved committed value."""
    if not owner or cfg.current_user == owner:
        return None
    who = (
        f"this checkout runs as {cfg.current_user!r}"
        if cfg.current_user
        else "this checkout has no `user` set in coga.local.toml"
    )
    return (
        f"Recurring launches in this repo belong to {owner!r} "
        f"(`owner` in coga.toml); {who}. Recurring is gated to one operator so "
        "two clones cannot sweep the same repo at once — ask them to run it, "
        "or change the committed `owner` to take it over."
    )


def _refuse_non_owner(cfg: Config) -> bool:
    """Authorize from the control tip and print any refusal."""
    refusal = _launch_owner_refusal(cfg)
    if refusal is None:
        return False
    typer.secho(refusal, fg=typer.colors.RED, err=True)
    return True


def _refuse_non_control_branch(cfg: Config) -> bool:
    """Require recurring mutations to start on the configured control branch.

    Git-disabled and non-git workspaces have no Coga-managed control checkout,
    so they retain their existing local behavior. This is deliberately only a
    branch gate: reachability and freshness remain best-effort for interactive
    runs and mandatory for ``coga recurring --all``.
    """
    if not cfg.git_enabled:
        return False

    location = cfg.repo_root
    try:
        # Only a confirmed non-git workspace is exempt. The best-effort local
        # helper used by discovery collapses every probe failure to ``None``;
        # this mutation gate must preserve inspection errors and fail closed.
        root = git._toplevel(cfg.repo_root)
        if root is None:
            return False
        location = root
        current = _current_branch(root)
    except git.GitError as exc:
        typer.secho(
            "Recurring launch refused: could not determine the current branch "
            f"in {location}: {exc}. Check out the configured control branch "
            f"{cfg.git_control_branch!r} with `git switch "
            f"{cfg.git_control_branch}` and retry.",
            fg=typer.colors.RED,
            err=True,
        )
        return True

    if current == cfg.git_control_branch:
        return False

    where = "detached HEAD" if current == "HEAD" else f"branch {current!r}"
    typer.secho(
        f"Recurring launch refused: the current checkout is on {where}, not "
        f"the configured control branch {cfg.git_control_branch!r}. Check out "
        f"the control branch with `git switch {cfg.git_control_branch}` and "
        "retry. `--force` does not override "
        "this gate.",
        fg=typer.colors.RED,
        err=True,
    )
    return True


def _launch_owner_refusal(cfg: Config) -> str | None:
    """Resolve recurring authorization from the latest reachable control tip.

    A stale local checkout may predate an owner addition or transfer, and the
    working tree may contain an uncommitted owner edit. Neither is
    authoritative: read the shared config blob from the fetched control commit
    instead.

    Fetch failure retains compatibility for repos whose local committed config
    has never opted into an owner. Once an owner is present locally, however,
    an apparent owner may not launch until the latest value can be confirmed;
    otherwise an offline stale clone could bypass an owner transfer.
    """
    owner, error, control_reached = _control_tip_owner(cfg)
    if owner is not None:
        return _recurring_owner_refusal(cfg, owner)

    local_owner, local_error = _local_committed_owner(cfg)
    if local_owner is None:
        return (
            "Recurring launch refused: could not read the committed local "
            f"`owner` after control-tip lookup failed ({error}): {local_error}."
        )
    local_refusal = _recurring_owner_refusal(cfg, local_owner)
    if local_refusal is not None:
        return local_refusal
    if not local_owner and not control_reached:
        # No local opt-in: preserve the pre-owner best-effort behavior when the
        # configured remote is unavailable.
        return None

    local_note = (
        f" The local commit names {local_owner!r}, but that value may be stale."
        if local_owner
        else ""
    )
    return (
        "Recurring launch refused: could not confirm the latest committed "
        f"`owner` from {cfg.git_remote}/{cfg.git_control_branch}: {error}."
        f"{local_note} Retry when the control branch is reachable; `--force` "
        "does not override the owner gate."
    )


def _control_tip_owner(cfg: Config) -> tuple[str | None, str, bool]:
    """Return (owner, error, control_reached) for committed control config.

    ``owner`` is ``""`` when the fetched config deliberately leaves the gate
    unset and ``None`` only when it could not be resolved. ``control_reached``
    distinguishes an unavailable remote from a fetched but unreadable/invalid
    config, which must fail closed even for a locally owner-less checkout.

    Local `HEAD` is authoritative only for a checkout with **no configured
    remote**. `[git].enabled = false` does not qualify: it is the sync opt-out
    documented for a remote-less repo, and honoring it here would make a
    machine-local, uncommitted setting an override of a committed policy — a
    stale clone would read no owner at all, and a former owner would stay
    authorized after a transfer, while the sweep still created period state and
    launched real work.
    """
    root = _git_toplevel(cfg.repo_root)
    if root is None:
        # A non-git local repo has no distinct control tip; its shared config is
        # the only committed-policy source available.
        return cfg.owner, "", True

    reached = False
    try:
        if not git._remote_configured(root, cfg.git_remote):
            return _owner_at_ref(cfg, root, "HEAD"), "", True
        # Authorize from the destination the sweep will actually mutate.
        # `_push_control_branch` publishes period state with `git push
        # <remote>`, and git distinguishes a remote's push URLs from its fetch
        # URL — reading the owner from the fetch repository would let an
        # operator it authorizes create and launch work in a push repository
        # owned by someone else. A multi-push remote has no single such
        # repository, so it fails closed rather than picking one.
        push_urls = git._remote_push_urls(root, cfg.git_remote)
        if len(push_urls) != 1:
            return (
                None,
                f"remote {cfg.git_remote!r} has {len(push_urls)} effective "
                "push URLs, so recurring state has no single owning "
                "repository to authorize against",
                True,
            )
        # FETCH_HEAD is checkout-wide and another Coga/git process may replace
        # it between fetch and read. The shared git primitive fetches through a
        # UUID-scoped ref and returns the exact command-owned commit instead.
        target = git._fetch_branch_oid(
            root, push_urls[0], cfg.git_control_branch
        )
        reached = True
        return _owner_at_ref(cfg, root, target), "", True
    except (ConfigError, git.GitError, tomllib.TOMLDecodeError) as exc:
        return None, str(exc), reached


def _local_committed_owner(cfg: Config) -> tuple[str | None, str]:
    """Read owner from HEAD, falling back to config only outside git."""
    root = _git_toplevel(cfg.repo_root)
    if root is None:
        return cfg.owner, ""
    try:
        return _owner_at_ref(cfg, root, "HEAD"), ""
    except (ConfigError, git.GitError, tomllib.TOMLDecodeError) as exc:
        return None, str(exc)


def _owner_at_ref(cfg: Config, root: Path, ref: str) -> str:
    """Parse the shared recurring owner from one exact committed config."""
    target = _rev_parse(root, ref)
    config_rel = _relative_to_root(root, cfg.repo_root / "coga.toml")
    shared_text = _show_path(root, target, config_rel)
    if not shared_text:
        raise ConfigError(f"commit {target} has no readable {config_rel}")
    shared = tomllib.loads(shared_text)
    return parse_owner(shared.get("owner"))


def run_recurring_all_repos(
    scan_root: Path,
    *,
    force: bool = False,
    interactive: bool = False,
    agent_override: str | None = None,
) -> int:
    """Run one normal recurring sweep in every Coga repo below ``scan_root``.

    Each repo runs in a fresh CLI process so config discovery, aliases, launch
    supervision, and the end-of-command Coga-state sync have exactly their
    ordinary single-repo behavior. Workspaces rejected by Coga's intentional
    config guards are summarized as unconfigured instead of dispatched.
    Failures from dispatched repos are isolated: the sweep continues through
    later repos and returns non-zero after reporting the aggregate.
    """
    root = scan_root.expanduser().resolve()
    if not root.is_dir():
        typer.secho(f"{root} is not a directory.", fg=typer.colors.RED, err=True)
        return 2

    repos = discover_coga_repos(root)
    if not repos:
        typer.secho(
            f"No Coga repos found under {root} "
            "(looked for coga/ directories with a coga.toml).",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return 1

    typer.echo(f"Found {len(repos)} Coga repo(s) under {root}:")
    for coga_os in repos:
        typer.echo(f"  {_repo_label(coga_os, root)}")

    serviceable: list[Path] = []
    skipped_unconfigured: list[str] = []
    skipped_not_owner: list[str] = []
    for coga_os in repos:
        label = _repo_label(coga_os, root)
        if not _has_serviceable_config(coga_os):
            skipped_unconfigured.append(label)
            continue
        # Per-repo, before duplicate grouping: a repo this operator does not own
        # is not a sweep target at all, so it must not be picked as the keeper
        # for a remote whose other checkout *is* runnable.
        refusal = _repo_owner_refusal(coga_os)
        if refusal is not None:
            skipped_not_owner.append(f"{label} — {refusal}")
            continue
        serviceable.append(coga_os)

    duplicate_of = _duplicate_remote_checkouts(serviceable)
    failed: list[str] = []
    skipped_duplicates: list[str] = []
    for index, coga_os in enumerate(serviceable, 1):
        label = _repo_label(coga_os, root)
        typer.secho(
            f"\n[{index}/{len(serviceable)}] {label}",
            fg=typer.colors.CYAN,
            bold=True,
        )
        original = duplicate_of.get(coga_os)
        if original is not None:
            original_label = _repo_label(original, root)
            skipped_duplicates.append(label)
            typer.secho(
                f"  ⚠ {label} — same git remote as {original_label}; "
                "skipped duplicate checkout",
                fg=typer.colors.YELLOW,
                err=True,
            )
            continue
        process_started = True
        try:
            code = _run_repo_recurring(
                coga_os,
                force=force,
                interactive=interactive,
                agent_override=agent_override,
            )
        except OSError as exc:
            process_started = False
            code = 1
            typer.secho(f"  ✗ {label} — {exc}", fg=typer.colors.RED, err=True)
        if code:
            failed.append(label)
            if process_started:
                if code == git.STALE_CONTROL_EXIT_CODE:
                    # The child already printed the conflict and the exact
                    # resolve command; keep the parent line short but name the
                    # cause instead of a bare exit code.
                    typer.secho(
                        f"  ✗ {label} — control checkout could not integrate "
                        "the latest control tip; resolve the conflict shown "
                        "above in that checkout, then re-run",
                        fg=typer.colors.RED,
                        err=True,
                    )
                else:
                    typer.secho(
                        f"  ✗ {label} — recurring exited {code}",
                        fg=typer.colors.RED,
                        err=True,
                    )

    swept = (
        len(repos)
        - len(failed)
        - len(skipped_duplicates)
        - len(skipped_unconfigured)
        - len(skipped_not_owner)
    )
    typer.echo(f"\nSwept {swept} of {len(repos)} Coga repo(s).")
    if skipped_unconfigured:
        count = len(skipped_unconfigured)
        repo_word = "repo" if count == 1 else "repos"
        typer.secho(
            f"Skipped {count} unconfigured {repo_word}.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    if skipped_not_owner:
        count = len(skipped_not_owner)
        repo_word = "repo" if count == 1 else "repos"
        # Named individually, not just counted: an operator who owns none of
        # the repos they scanned would otherwise see an empty sweep with no
        # clue which name to ask for.
        listed = "\n".join(f"  {entry}" for entry in skipped_not_owner)
        typer.secho(
            f"Skipped {count} {repo_word} owned by someone else:\n{listed}",
            fg=typer.colors.YELLOW,
            err=True,
        )
    if skipped_duplicates:
        typer.secho(
            f"Skipped {len(skipped_duplicates)} duplicate checkout(s) "
            "that share a configured git remote.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    if failed:
        typer.secho(
            f"{len(failed)} repo(s) failed: {', '.join(failed)} — see each "
            "repo's section above for the error and fix.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return 1
    return 0


def _repo_label(coga_os: Path, root: Path) -> str:
    host_repo = coga_os.parent
    try:
        relative = host_repo.relative_to(root)
    except ValueError:
        return str(host_repo)
    return host_repo.name if relative == Path(".") else str(relative)


def _has_serviceable_config(coga_os: Path) -> bool:
    """Whether a discovered workspace is a configured scheduler target."""
    try:
        cfg = load_config(coga_os)
        validate_aliases({**DEFAULT_ALIASES, **cfg.aliases})
    except ConfigError:
        return False
    except Exception:
        # The child process remains authoritative for malformed TOML, I/O
        # failures, and unexpected loader bugs. Only Coga's intentional config
        # guards identify an unconfigured checkout that the parent may skip.
        return True
    return True


def _repo_owner_refusal(coga_os: Path) -> str | None:
    """The owner refusal for a discovered workspace, or None if it may sweep.

    The gate is per-repo under `--all`: each repo names its own `owner`, so an
    operator sweeping a directory of clones runs the ones they own and skips
    the rest rather than failing the whole sweep. Config that fails to load
    here is left to the child process, which is the authoritative loader —
    exactly as `_configured_remote_identity` does.
    """
    try:
        cfg = load_config(coga_os, require_user=False)
        owner, _reason, _control_reached = _control_tip_owner(cfg)
        if owner is None:
            # Never pre-skip on an unconfirmed value. The selected child is the
            # authoritative freshness gate and fails before scanning if the
            # control tip cannot be integrated.
            return None
    except Exception:
        return None
    return _recurring_owner_refusal(cfg, owner)


def _duplicate_remote_checkouts(repos: list[Path]) -> dict[Path, Path]:
    """Map repeated remote workspaces to one usable control checkout."""
    by_remote: dict[tuple[str, str], list[tuple[Path, bool, bool]]] = {}
    duplicates: dict[Path, Path] = {}
    for coga_os in repos:
        resolved = _configured_remote_identity(coga_os)
        if resolved is None:
            continue
        remote_identity, workspace_identity, has_user, on_control_branch = resolved
        by_remote.setdefault((remote_identity, workspace_identity), []).append(
            (coga_os, has_user, on_control_branch)
        )

    for checkouts in by_remote.values():
        keeper = next(
            (
                path
                for path, has_user, on_control in checkouts
                if has_user and on_control
            ),
            None,
        )
        if keeper is None:
            keeper = next(
                (path for path, _has_user, on_control in checkouts if on_control),
                None,
            )
        if keeper is None:
            keeper = next(
                (path for path, has_user, _on_control in checkouts if has_user),
                checkouts[0][0],
            )
        for path, _has_user, _on_control in checkouts:
            if path != keeper:
                duplicates[path] = keeper
    return duplicates


def _configured_remote_identity(
    coga_os: Path,
) -> tuple[str, str, bool, bool] | None:
    """Return remote/workspace identity and checkout eligibility signals."""
    try:
        cfg = load_config(coga_os, require_user=False)
    except Exception:
        # Classification is best-effort. The repo's child process is the
        # authoritative config loader, so every failure still surfaces there
        # without starving later repos in the parent sweep.
        return None
    if not cfg.git_enabled:
        return None

    try:
        root = _git_toplevel(coga_os)
    except OSError:
        return None
    if root is None:
        return None
    try:
        on_control_branch = _current_branch(root) == cfg.git_control_branch
    except git.GitError:
        on_control_branch = False

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", cfg.git_remote],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip().splitlines()
    if not url:
        return None
    try:
        identity = _normalize_remote_identity(root, url[0])
    except OSError:
        return None
    if identity is None:
        return None

    # One git checkout may intentionally contain several independent Coga
    # workspaces. Only equal workspace paths across separate checkouts of the
    # remote are duplicates; siblings inside one monorepo must all run.
    try:
        workspace_identity = (
            coga_os.resolve().relative_to(root.resolve()).as_posix()
        )
    except (OSError, ValueError):
        return None
    return identity, workspace_identity, bool(cfg.current_user), on_control_branch


def _normalize_remote_identity(root: Path, url: str) -> str | None:
    """Canonicalize local remote paths; preserve resolved network URLs."""
    value = url.strip()
    if not value:
        return None

    if value.startswith("file://"):
        parsed = urlsplit(value)
        if parsed.netloc not in {"", "localhost"}:
            return f"url:{value.rstrip('/')}"
        return f"file:{Path(unquote(parsed.path)).resolve()}"

    # A scp-style remote (`git@host:org/repo.git`) has no `://` but is not a
    # filesystem path. Everything else without a URL scheme is the local-path
    # form git resolves relative to the checkout.
    if "://" not in value and not (
        ":" in value and not value.startswith(("/", "./", "../", "~"))
    ):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        return f"file:{path.resolve()}"
    return f"url:{value.rstrip('/')}"


def _run_repo_recurring(
    coga_os: Path,
    *,
    force: bool,
    interactive: bool,
    agent_override: str | None,
) -> int:
    """Dispatch the registered recurring recipe from ``coga_os``'s host."""
    command = [
        sys.executable,
        "-m",
        "coga.cli",
        "run",
        "recurring-scan",
        "--require-fresh-control",
    ]
    if force:
        command.append("--force")
    if interactive:
        command.append("--interactive")
    if agent_override:
        command.extend(("--agent", agent_override))

    result = subprocess.run(
        command,
        cwd=coga_os.parent,
        env=os.environ.copy(),
        check=False,
    )
    return result.returncode


def run_recurring_scan(
    cfg: Config,
    *,
    force: bool = False,
    interactive: bool = False,
    agent_override: str | None = None,
    require_fresh_control: bool = False,
) -> int:
    """Scan every recurring template and launch any due tasks, sequentially.

    Bare `coga recurring` is the default action. For each template under
    `coga/recurring/` it get-or-creates the current period's task, then
    launches every one still `active` or orphaned `in_progress` —
    most-overdue first, one at a time. A period task left `in_progress` by a
    sweep whose supervisor died mid-run (laptop sleep, SSH drop) is **resumed**
    from its current step on the next sweep. If an interactive launch returns
    unfinished, the sweep pauses it before continuing, so a frozen
    `in_progress` can still mean "dead run's orphan". `done`, `canceled`, and
    `paused` tasks are skipped. Current period only: running this once a month for a weekly
    template produces one run, not a backlog. It does not install or manage
    system cron; nothing runs unless you invoke it.

    `--force` forces a real, full run: the only difference from the bare sweep is
    that it ignores the schedule and the status filter, so every template is
    launched — including ones already serviced this period (re-launched) and
    `done`/`paused` ones (the runner reactivates them). Canceled tasks are
    included in discovery but refused rather than reactivated; the sweep
    reports each refusal, continues with later templates, and returns non-zero
    after the remaining work finishes. Everything else — Slack, the digest
    spool, git task-state sync, and the serviced-period ledger advance —
    is identical to a normal run.

    `agent_override` temporarily selects the configured agent for agent-backed
    tasks. It never rewrites the ticket, and a period task carrying `ticket.py`
    keeps its deterministic execution path.

    A git-backed interactive run requires the configured control branch to be
    checked out, but does not require its remote tip to be reachable. A child
    dispatched by `coga recurring --all` sets
    `require_fresh_control`: failure to fetch and integrate the configured
    control tip returns non-zero before `scan_due` can mutate period state.
    Bare single-repo sweeps retain the established best-effort catch-up.

    `coga recurring launch <name>` force-runs one named template now.

    A repo with a committed `owner` refuses this for every other operator —
    including under `--force` — before anything is scanned or created; see
    `recurring_owner_refusal`.
    """
    # `--all` retains its existing stricter combined branch/freshness gate and
    # distinct stale-control exit code. Interactive entry points need only the
    # local branch precondition, so an offline control checkout may proceed.
    if not require_fresh_control and _refuse_non_control_branch(cfg):
        return 2

    fresh, freshness_error = _sync_control_checkout_ahead(
        cfg, announce_failure=not require_fresh_control
    )
    if require_fresh_control and not fresh:
        typer.secho(
            "Recurring scan skipped: could not confirm this checkout includes "
            f"the latest {cfg.git_remote}/{cfg.git_control_branch}: "
            f"{freshness_error}",
            fg=typer.colors.RED,
            err=True,
        )
        # Distinct exit code: the refusal happened before any period state
        # was touched, so the layers wrapping this launch skip their post-run
        # git catch-up instead of re-failing (and re-printing) the same
        # divergence — see `git.STALE_CONTROL_EXIT_CODE`.
        return git.STALE_CONTROL_EXIT_CODE
    if _refuse_non_owner(cfg):
        return 2
    if not _valid_agent_override(cfg, agent_override):
        return 2
    scan = scan_due(
        cfg, allow_interactive=_interactive_stdio_has_tty(), force=force
    )
    _broadcast_scan(
        cfg,
        scan,
        respect_handled_period=not force,
        sync_existing=force,
        control_is_fresh=fresh,
    )
    _print_table(scan, force=force)

    # The autofix loop's view of this sweep. Built as we go rather than scraped
    # from the console: fd 1 must stay a TTY or every interactive launch below
    # would refuse itself. See `coga/recurring_autofix.py`.
    record = RunRecord(
        started=datetime.now(),
        repo=cfg.repo_root.name,
        force=force,
        interactive=interactive,
        agent_override=agent_override,
        scan_lines=scan_lines_for_record(scan, force=force),
        scan_errors=list(scan.errors),
    )

    # `force` launches every materialized task regardless of status;
    # the bare sweep launches only the launchable (active/in_progress) ones.
    due = scan.forced if force else scan.due
    if not due:
        message = (
            "No recurring templates to launch." if force else "No recurring tasks due."
        )
        typer.echo(message)
        record.note(message)
        run_autofix(cfg, record, agent_override=agent_override)
        return 0

    label = "task(s)" if force else "due task(s)"
    typer.echo(f"\nLaunching {len(due)} {label} sequentially...\n")
    record.note(f"launching {len(due)} {label} sequentially")

    # `finally`, not a trailing call: a sweep that dies partway through — a
    # `ticket.py` exiting non-zero, `_stop_if_unfinished_after_launch` exiting
    # on an invalid ticket — is exactly the run most worth analyzing.
    try:
        return _launch_due_tasks(
            cfg,
            due,
            record,
            force=force,
            interactive=interactive,
            agent_override=agent_override,
        )
    finally:
        run_autofix(cfg, record, agent_override=agent_override)


def _launch_due_tasks(
    cfg: Config,
    due: list[DueTask],
    record: RunRecord,
    *,
    force: bool,
    interactive: bool,
    agent_override: str | None,
) -> int:
    """Run each due period task in order, recording what each one did.

    Split out of `run_recurring_scan` so the sweep has one place to hand the
    finished `RunRecord` to the autofix loop, however the loop ends — including
    the early return on a failed `ticket.py`.
    """
    # `--interactive` is a human stepping through by hand, so leave the spawned
    # REPL unbounded; an automatic sweep arms the liveness backstops so one stuck
    # agent can't block the tasks behind it.
    idle_timeout = None if interactive else _recurring_idle_timeout(cfg)
    max_session = None if interactive else _recurring_max_session(cfg)
    from coga.commands.launch import launch_recurring_period as launch_cmd

    forced_refusals = 0
    for i, task in enumerate(due, 1):
        typer.secho(
            f"[{i}/{len(due)}] {task.ref.id_slug}", fg=typer.colors.CYAN, bold=True
        )
        if force:
            try:
                _prepare_forced_launch(cfg, task)
            except RecurringError as exc:
                forced_refusals += 1
                typer.secho(str(exc), fg=typer.colors.RED, err=True)
                record.add(
                    TaskOutcome(
                        template=task.template,
                        slug=task.ref.id_slug if task.ref else task.template,
                        result="refused",
                        detail=str(exc),
                    )
                )
                continue
        # Reconciliation can refresh or replace the materialized period after
        # `scan_due` cached its dispatch field. Route only from the durable
        # ticket that now owns this launch; otherwise a restored delegate could
        # run as an ordinary wrapper, or a removed delegate could still spawn
        # obsolete bootstrap work.
        try:
            current_ticket = read_ticket(task.ref)
            task.status = current_ticket.status
            task.delegate = frozen_task_delegate(task.ref, current_ticket)
        except (RecurringError, TicketError) as exc:
            detail = (
                f"cannot classify recurring period {task.ref.id_slug} after "
                f"reconciliation: {exc}"
            )
            typer.secho(detail, fg=typer.colors.RED, err=True)
            record.add(
                TaskOutcome(
                    template=task.template,
                    slug=task.ref.id_slug,
                    result="refused",
                    detail=detail,
                )
            )
            return 2
        # One dispatch for every template: `coga launch` classifies the period
        # task from its own directory, so a `ticket.py` template runs
        # deterministically and an agent template composes a prompt, without
        # this sweep holding a second copy of that rule.
        #
        if task.delegate:
            # A delegating template's period task never runs its own agent
            # session: the sweep launches the declared bootstrap target
            # directly — in this operator's terminal, under the same liveness
            # bounds and queue posture as any sweep launch — and does the
            # period task's lifecycle bookkeeping itself.
            delegated = _run_delegated_task(
                cfg,
                task.ref,
                agent_override=agent_override,
                idle_timeout=idle_timeout,
                max_session=max_session,
                queue_guidance=not interactive,
                continue_after_timeout=True,
            )
            # Main's sweep records every run it performed; `run_autofix` fires
            # only when `record.outcomes` is non-empty, so a delegated run that
            # returned without recording would be invisible to the analyst.
            record.add(
                _task_outcome(
                    cfg,
                    task.template,
                    task.ref,
                    kind=delegated.kind,
                    result=(
                        "failed"
                        if delegated.exit_code and delegated.kind != "timeout"
                        else ""
                    ),
                    exit_code=delegated.exit_code or None,
                )
            )
            if delegated.exit_code:
                return delegated.exit_code
            continue
        # Sequential by design: each launch blocks until the session exits
        # before the next begins. `scan_due` filters out templates that cannot
        # run in the current stdio context (an agent run with no TTY), and the
        # liveness backstops release any that launch but then stall. `launch`
        # returns "timeout" when a backstop fired so we record the wedge
        # honestly below instead of pausing it as a human would.
        try:
            kind = launch_cmd(
                task.ref.id_slug,
                agent_override=agent_override,
                prompt_report=False,
                idle_timeout=idle_timeout,
                max_session=max_session,
                return_timeout=True,
                script_failure_important=True,
                # An automatic sweep's agent must announce-and-continue and end
                # owner decisions in `coga block` — a conversational ask hangs
                # the queue until a liveness timeout fails the task.
                # `--interactive` is a human stepping through by hand, so it
                # keeps plain launches.
                queue_guidance=not interactive,
            )
        except SystemExit as exc:
            # A failed `ticket.py` exits the launch. Return that code instead
            # of unwinding the process, so the sweep stops where the old recipe
            # dispatch stopped *and* the command still reaches its exit-boundary
            # git sync. The task is deliberately left unfinished, not paused.
            code = _exit_status(exc)
            if code:
                record.add(
                    _task_outcome(
                        cfg, task.template, task.ref, result="failed", exit_code=code
                    )
                )
                return code
            kind = None
        if kind == "skipped":
            record.note(
                f"{task.ref.id_slug} changed on control before launch; skipped"
            )
            continue
        _stop_if_unfinished_after_launch(
            cfg,
            task.ref,
            timed_out=(kind == "timeout"),
            script_stopped=(kind == "script"),
        )
        record.add(_task_outcome(cfg, task.template, task.ref, kind=kind))
    return 2 if forced_refusals else 0


def _task_outcome(
    cfg: Config,
    template: str,
    ref: TaskRef | None,
    *,
    kind: str | None = None,
    result: str = "",
    exit_code: int | None = None,
) -> TaskOutcome:
    """Classify one period task's run for the record.

    A launched task has no exit code worth reading in the ordinary case — the
    supervisor tears the session down on a lifecycle transition — so the
    ticket's status after the run *is* the outcome, and its blackboard is what
    the run had to say. `_stop_if_unfinished_after_launch` has already parked an
    unfinished run, which is what makes `paused` legible here.
    """
    status = outcome_for_ref(cfg, ref)
    detail = ""
    if not result:
        # Status first, `kind` only to explain it. `kind == "script"` says the
        # deterministic phase ended the launch — including the ordinary success
        # where it closed the step itself — so reading it as a failure would
        # report every healthy `ticket.py` template as unfinished.
        if kind == "timeout":
            result = "timed-out"
            detail = (
                "liveness watchdog tore the session down before it signalled done"
            )
        elif status is None:
            result = "completed"
            detail = "task directory was removed during the run"
        elif status in TERMINAL_STATUSES:
            result = "completed"
        elif status == "blocked":
            result = "unfinished"
            detail = (
                "the deterministic `ticket.py` phase recorded a blocker"
                if kind == "script"
                else "the agent blocked on a human answer"
            )
        elif kind == "script":
            result = "unfinished"
            detail = (
                "the deterministic `ticket.py` phase stopped before the step closed"
            )
        else:
            result = "unfinished"
            detail = (
                "the run exited without a terminal transition; the sweep parked it"
            )
    return TaskOutcome(
        template=template,
        slug=ref.id_slug if ref else template,
        result=result,
        exit_code=exit_code,
        final_status=status,
        detail=detail,
        blackboard=blackboard_for_ref(ref),
    )


def run_recurring_scan_recipe(cfg: Config, argv: list[str]) -> int:
    """Parse the recurring scanner's ordinary argv recipe contract."""
    parser = argparse.ArgumentParser(
        prog="coga run recurring-scan",
        description="Scan recurring templates and launch due period tasks.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--agent")
    parser.add_argument("--require-fresh-control", action="store_true")
    args = parser.parse_args(argv)
    return run_recurring_scan(
        cfg,
        force=args.force,
        interactive=args.interactive,
        agent_override=args.agent,
        require_fresh_control=args.require_fresh_control,
    )


@dataclass(frozen=True)
class DelegatedRunResult:
    """Exit status plus the delegated supervisor's termination class."""

    exit_code: int
    kind: str | None


@dataclass(frozen=True)
class _PeriodLease:
    """Exact stable-path generation owned by one delegated child.

    Ticket bytes alone are insufficient: a later recurring generation may be
    materialized at the same path with byte-identical frozen dispatch and
    lifecycle state. Every canonical create/reuse/reactivation writes a
    task-tagged audit line, so the sorted multiset of those lines is the
    durable generation discriminator. Sorting makes the lease insensitive to
    merge=union's legal line reordering while retaining duplicate counts.
    """

    ticket_bytes: bytes | None
    audit_lines: tuple[bytes, ...]


_LOG_REF_RE = re.compile(
    rb"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} \[([^\]]*)\] \[[^\]]*\] .*$"
)


def _task_audit_fingerprint(data: bytes | None, task_ref: str) -> tuple[bytes, ...]:
    if not data:
        return ()
    expected = task_ref.encode("utf-8")
    matching: list[bytes] = []
    for line in data.splitlines():
        match = _LOG_REF_RE.match(line)
        if match is not None and match.group(1) == expected:
            matching.append(line)
    return tuple(sorted(matching))


def _local_period_lease(cfg: Config, ref: TaskRef) -> _PeriodLease:
    ticket_bytes = ref.ticket_path.read_bytes() if ref.ticket_path.is_file() else None
    audit_path = log_path(cfg)
    audit_bytes = audit_path.read_bytes() if audit_path.is_file() else None
    return _PeriodLease(
        ticket_bytes=ticket_bytes,
        audit_lines=_task_audit_fingerprint(audit_bytes, ref.id_slug),
    )


def _revision_period_lease(
    cfg: Config, ref: TaskRef, revision: str
) -> _PeriodLease:
    root = git._toplevel(cfg.repo_root)
    if root is None:
        return _local_period_lease(cfg, ref)
    ticket_rel = _relative_to_root(root, ref.ticket_path)
    log_rel = _relative_to_root(root, log_path(cfg))
    return _PeriodLease(
        ticket_bytes=git._tree_bytes(root, revision, ticket_rel),
        audit_lines=_task_audit_fingerprint(
            git._tree_bytes(root, revision, log_rel), ref.id_slug
        ),
    )


def _period_lease_guard(
    cfg: Config, ref: TaskRef, expected: _PeriodLease
) -> Callable[[str], None]:
    """Bind an exact ticket-plus-generation CAS to every control attempt."""
    lifecycle_guard = git.ticket_state_guard(cfg, ref.ticket_path)

    def guard(base: str) -> None:
        actual = _revision_period_lease(cfg, ref, base)
        if actual != expected:
            changed: list[str] = []
            if actual.ticket_bytes != expected.ticket_bytes:
                changed.append("ticket bytes")
            if actual.audit_lines != expected.audit_lines:
                changed.append("task audit generation")
            raise git.StateRegressionError(
                f"{ref.id_slug}: delegated period lease changed on control "
                f"({', '.join(changed) or 'unknown state'}); refusing stale "
                "lifecycle publication"
            )
        lifecycle_guard(base)

    return guard


def _period_mutation_snapshot(
    cfg: Config, ref: TaskRef, *, include_digest_spool: bool = False
) -> git.FileMutationRollback:
    audit_path = log_path(cfg)
    paths = [ref.ticket_path, audit_path]
    union_paths = [audit_path]
    if include_digest_spool:
        spool_path = digest_spool_path(cfg)
        if spool_path is not None:
            paths.append(spool_path)
            union_paths.append(spool_path)
    return git.FileMutationRollback.capture(paths, union_paths=union_paths)


def _restore_refused_period_mutation(
    rollback: git.FileMutationRollback, *, action: str
) -> None:
    refused = rollback.restore()
    if refused:
        names = ", ".join(str(path) for path in refused)
        raise RecurringError(
            f"could not restore delegated period after refused {action}; "
            f"concurrent writes remain at {names}"
        )


def _run_delegated_task(
    cfg: Config,
    ref: TaskRef,
    *,
    agent_override: str | None = None,
    idle_timeout: float | None = None,
    max_session: float | None = None,
    queue_guidance: bool = True,
    continue_after_timeout: bool,
    activate_if_needed: bool = False,
) -> DelegatedRunResult:
    """Run one delegating period task by launching its bootstrap target.

    A `delegate:` template owns only the schedule; the real work is a
    stateless `bootstrap/<name>` command ticket. The sweep is a foreground
    command in the operator's own terminal, so it performs that agent launch
    in-process — TTY admission was already decided before the period task was
    created (`scan_due` refuses agent-backed templates, delegating ones
    included, without a TTY) — and owns the period task's lifecycle
    bookkeeping exactly as `_run_recipe_task` does around a recipe
    subprocess. No agent session ever runs on the period task itself, so no
    wrapper has to shell out to a nested `coga launch` or manufacture a pty.

    Only the bootstrap target's done sentinel marks the period task done; a
    natural or crashed REPL exit leaves it `in_progress` and fails loud. A
    liveness timeout pauses and continues only for a multi-task sweep. A named
    launch instead returns the timeout code and leaves the task retryable as
    `in_progress`. Start, final spawn, completion, and timeout each lease both
    the exact ticket and its task-tagged audit generation. The control guard
    observes that lease as a compare-and-set, so a stable-path replacement can
    neither start obsolete work nor receive the prior child's result.

    ``activate_if_needed`` belongs only to direct ``coga launch``: the typed
    command is the documented readiness signal for a paused/draft task. Sweeps
    and named recurring runs retain their stricter active/orphan admission.
    """
    ticket = read_ticket(ref)
    try:
        delegate = frozen_task_delegate(ref, ticket)
        if delegate is None:
            raise RecurringError(
                f"delegating recurring task {ref.id_slug} is missing its "
                "frozen target"
            )
        allowed_statuses = {"active", "in_progress"}
        if activate_if_needed:
            allowed_statuses.update({"draft", "paused"})
        if ticket.status not in allowed_statuses:
            expected = "'active' or 'in_progress'"
            if activate_if_needed:
                expected += " (or 'draft'/'paused' for direct launch)"
            raise RecurringError(
                f"cannot launch delegated period {ref.id_slug}: task is "
                f"{ticket.status!r}, expected {expected}"
            )
        # Re-check the frozen target immediately before every run. Validation
        # catches drift repo-wide; this runtime gate keeps a later bootstrap
        # edit from turning an agent delegation into repeated script work.
        resolve_agent_delegate(cfg, delegate)
    except (RecurringError, TicketError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return DelegatedRunResult(2, "refused")

    initial_period_lease = _local_period_lease(cfg, ref)
    expected_period_lease: _PeriodLease | None = None

    # Bootstrap tickets are deliberately stateless and self-skip push auth.
    # Delegation still owns a materialized period task, so preflight that real
    # publication target before any bootstrap work can begin.
    from coga.commands.launch import _preflight_push_auth

    require_period_publication = bool(
        _preflight_push_auth(cfg, ref, is_bootstrap=False)
    )

    def ticket_for_lease(
        lease: _PeriodLease, *, boundary: str, expected_status: str
    ) -> Ticket:
        try:
            if lease.ticket_bytes is None:
                raise TicketError("period ticket disappeared")
            current = Ticket.parse(lease.ticket_bytes.decode())
            current_delegate = frozen_task_delegate(ref, current)
        except (OSError, UnicodeError, TicketError, RecurringError) as exc:
            raise RecurringError(
                f"cannot lease delegated period {ref.id_slug} at {boundary}: "
                f"{exc}"
            ) from exc
        if current.status != expected_status:
            raise RecurringError(
                f"cannot launch delegated target {delegate}: period task "
                f"{ref.id_slug} changed to {current.status!r} at {boundary}"
            )
        if current_delegate != delegate:
            raise RecurringError(
                f"cannot launch delegated period {ref.id_slug}: frozen target "
                f"changed from {delegate!r} to {current_delegate!r} at "
                f"{boundary}"
            )
        return current

    def confirm_control_lease(
        lease_cfg: Config, lease: _PeriodLease, *, boundary: str
    ) -> None:
        try:
            git.sync_task_state(
                lease_cfg,
                ref.path,
                message=f"Lease: {ref.id_slug} — {boundary}",
                guard=_period_lease_guard(lease_cfg, ref, lease),
                raise_state_regression=True,
                **(
                    {"raise_git_error": True}
                    if require_period_publication
                    else {}
                ),
            )
        except git.GitError as exc:
            raise RecurringError(
                f"cannot lease delegated period {ref.id_slug} at {boundary}: {exc}"
            ) from exc

    def start_period() -> None:
        """Publish lifecycle after preflight; launch will then re-compose."""
        nonlocal expected_period_lease
        # The bootstrap launch audit is made durable immediately before this
        # callback and may integrate a newer control tip. Use that tip's config
        # for the period transition; the following launch pass will independently
        # reload it again before composing the child.
        start_cfg = load_config(cfg.repo_root)
        current_lease = _local_period_lease(start_cfg, ref)
        if current_lease != initial_period_lease:
            raise RecurringError(
                f"cannot start delegated period {ref.id_slug}: its ticket or "
                "task audit generation changed during preflight"
            )
        if current_lease.ticket_bytes is None:
            raise RecurringError(
                f"cannot start delegated period {ref.id_slug}: ticket disappeared"
            )
        try:
            current = Ticket.parse(current_lease.ticket_bytes.decode())
            current_delegate = frozen_task_delegate(ref, current)
        except (UnicodeError, TicketError, RecurringError) as exc:
            raise RecurringError(
                f"cannot start delegated period {ref.id_slug}: {exc}"
            ) from exc
        if current_delegate != delegate:
            raise RecurringError(
                f"cannot start delegated period {ref.id_slug}: frozen target "
                f"changed from {delegate!r} to {current_delegate!r}"
            )

        prior_status = current.status
        if activate_if_needed and prior_status in {"draft", "paused"}:
            try:
                prepare_active(start_cfg, ref, current)
            except WorkflowMissing as exc:
                raise RecurringError(
                    f"cannot activate delegated period {ref.id_slug}: it has "
                    "no workflow to advance"
                ) from exc
            except WorkflowError as exc:
                raise RecurringError(
                    f"cannot activate delegated period {ref.id_slug}: its "
                    f"workflow could not be frozen — {exc}"
                ) from exc
            except RequiredExtensionMissing as exc:
                fields = ", ".join(repr(name) for name in exc.fields)
                raise RecurringError(
                    f"cannot activate delegated period {ref.id_slug}: required "
                    f"extension field(s) empty: {fields}"
                ) from exc
            except BlackboardNeedsSynthesis as exc:
                raise RecurringError(
                    format_blackboard_synthesis_refusal(
                        ref.id_slug, action="launch", reason=exc.reason
                    )
                ) from exc

        if current.status == "active":
            cur = current.current_step()
            step_note = (
                f" (step {current.step_index()}: {cur['name']})" if cur else ""
            )
            transition = (
                "active → in_progress"
                if prior_status == "active"
                else f"{prior_status} → active → in_progress"
            )
            rollback = _period_mutation_snapshot(start_cfg, ref)
            publication_succeeded = False

            def record_publication() -> None:
                nonlocal publication_succeeded
                publication_succeeded = True

            try:
                mark_in_progress(
                    start_cfg,
                    ref,
                    current,
                    actor="system",
                    log_message=(
                        f"started ({transition}) via recurring delegation "
                        f"to {delegate}"
                    ),
                    slack_text=(
                        f"▶️ delegated run started *{ref.id_slug}* "
                        f"\"{current.title}\"{step_note}"
                    ),
                    echo=f"{ref.id_slug}: in_progress",
                    mutation_snapshot=rollback,
                    after_sync=record_publication,
                    state_guard=_period_lease_guard(
                        start_cfg, ref, initial_period_lease
                    ),
                    strict_state_guard=True,
                    strict_state_sync=require_period_publication,
                )
            except git.GitError as exc:
                if not publication_succeeded:
                    _restore_refused_period_mutation(
                        rollback, action="delegated start"
                    )
                raise RecurringError(
                    f"cannot start delegated period {ref.id_slug}: {exc}"
                ) from exc
            except BaseException:
                if not publication_succeeded:
                    _restore_refused_period_mutation(
                        rollback, action="delegated start"
                    )
                raise
        elif current.status != "in_progress":
            raise RecurringError(
                f"cannot launch delegated target {delegate}: period task "
                f"{ref.id_slug} changed to {current.status!r} during preflight"
            )
        else:
            confirm_control_lease(
                start_cfg, initial_period_lease, boundary="orphan resume"
            )

        started_lease = _local_period_lease(start_cfg, ref)
        ticket_for_lease(
            started_lease,
            boundary="start publication",
            expected_status="in_progress",
        )
        launch_audit = append_log(
            start_cfg,
            ref.id_slug,
            "system",
            f"launched delegated target {delegate}",
        )
        git.sync_log(start_cfg, message=f"Log: {ref.id_slug}")
        expected_audit = tuple(
            sorted([*started_lease.audit_lines, launch_audit.rstrip(b"\n")])
        )
        expected_period_lease = _local_period_lease(start_cfg, ref)
        if expected_period_lease != _PeriodLease(
            ticket_bytes=started_lease.ticket_bytes,
            audit_lines=expected_audit,
        ):
            raise RecurringError(
                f"cannot launch delegated period {ref.id_slug}: its ticket or "
                "task audit generation changed while publishing the launch audit"
            )
        ticket_for_lease(
            expected_period_lease,
            boundary="launch audit publication",
            expected_status="in_progress",
        )

    def revalidate_period_before_spawn() -> None:
        """Refuse if publication/recomposition moved the period's lease."""
        if expected_period_lease is None:
            raise RecurringError(
                f"cannot launch delegated period {ref.id_slug}: its start "
                "publication did not establish a spawn lease"
            )
        current_lease = _local_period_lease(cfg, ref)
        if current_lease != expected_period_lease:
            raise RecurringError(
                f"cannot launch delegated period {ref.id_slug}: its ticket or "
                "task audit generation changed after start publication; "
                "retry from fresh state"
            )
        ticket_for_lease(
            current_lease,
            boundary="final spawn",
            expected_status="in_progress",
        )
        confirm_control_lease(cfg, expected_period_lease, boundary="final spawn")

    from coga.commands.launch import launch_with_before_spawn as launch_cmd

    try:
        kind = launch_cmd(
            delegate,
            agent_override=agent_override,
            idle_timeout=idle_timeout,
            max_session=max_session,
            return_timeout=True,
            queue_guidance=queue_guidance,
            before_spawn=start_period,
            revalidate_before_spawn=revalidate_period_before_spawn,
        )
    except (ConfigError, RecurringError, TaskValidationError, TicketError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return DelegatedRunResult(2, "refused")

    # The bootstrap launch may have changed coga.toml itself, and its teardown
    # may have refreshed a concurrent control-plane edit into this checkout.
    # Re-read configuration before any post-child lifecycle write so validation,
    # git publication, and notifications use the state that now owns the task.
    try:
        cfg = load_config(cfg.repo_root)
    except ConfigError as exc:
        typer.secho(
            f"cannot finalize delegated period {ref.id_slug}: configuration "
            f"is invalid after the bootstrap session: {exc}",
            fg=typer.colors.RED,
            err=True,
        )
        return DelegatedRunResult(2, kind or "refused")

    if kind not in {"done", "timeout"}:
        typer.secho(
            f"{ref.id_slug}: delegated target {delegate} ended without "
            f"its done signal (termination={kind or 'unknown'}); task left "
            "in_progress.",
            fg=typer.colors.RED,
            err=True,
        )
        return DelegatedRunResult(2, kind or "unknown")

    if expected_period_lease is None:
        typer.secho(
            f"cannot finalize delegated period {ref.id_slug}: no child lease "
            "was established",
            fg=typer.colors.RED,
            err=True,
        )
        return DelegatedRunResult(2, "refused")

    current_lease = _local_period_lease(cfg, ref)
    if current_lease != expected_period_lease:
        current_ticket: Ticket | None = None
        if current_lease.ticket_bytes is not None:
            try:
                current_ticket = Ticket.parse(current_lease.ticket_bytes.decode())
            except (UnicodeError, TicketError):
                current_ticket = None
        if kind == "done" and (
            current_ticket is None or current_ticket.status in TERMINAL_STATUSES
        ):
            return DelegatedRunResult(0, "done")
        typer.secho(
            f"{ref.id_slug}: delegated target {delegate} returned {kind}, but "
            "the stable task path now belongs to a different ticket/audit "
            "generation; its lifecycle was left unchanged.",
            fg=typer.colors.RED,
            err=True,
        )
        if kind == "timeout":
            return DelegatedRunResult(
                0 if continue_after_timeout else _TIMEOUT_EXIT_CODE,
                "timeout",
            )
        return DelegatedRunResult(2, "refused")

    if kind == "timeout":
        if continue_after_timeout:
            try:
                _stop_if_unfinished_after_launch(
                    cfg,
                    ref,
                    timed_out=True,
                    expected_period_lease=expected_period_lease,
                    require_period_publication=require_period_publication,
                )
            except RecurringError as exc:
                typer.secho(str(exc), fg=typer.colors.RED, err=True)
            return DelegatedRunResult(0, "timeout")
        typer.secho(
            f"{ref.id_slug}: delegated target {delegate} timed out; "
            "task left in_progress for an explicit retry.",
            fg=typer.colors.RED,
            err=True,
        )
        return DelegatedRunResult(_TIMEOUT_EXIT_CODE, "timeout")

    after_delegate = ticket_for_lease(
        current_lease,
        boundary="completion",
        expected_status="in_progress",
    )
    rollback = _period_mutation_snapshot(cfg, ref, include_digest_spool=True)
    publication_succeeded = False

    def record_completion_publication() -> None:
        nonlocal publication_succeeded
        publication_succeeded = True

    try:
        mark_done(
            cfg,
            ref,
            after_delegate,
            actor="system",
            log_message=(
                f"completed (delegated {delegate} run finished) "
                "via coga recurring"
            ),
            slack_text=(
                f"✅ delegated run completed *{ref.id_slug}* "
                f"\"{after_delegate.title}\""
            ),
            digest_detail=f"→ done (delegate: {delegate})",
            echo=f"{ref.id_slug}: done",
            mutation_snapshot=rollback,
            after_sync=record_completion_publication,
            state_guard=_period_lease_guard(cfg, ref, expected_period_lease),
            strict_state_guard=True,
            strict_state_sync=require_period_publication,
        )
    except git.GitError as exc:
        if not publication_succeeded:
            _restore_refused_period_mutation(rollback, action="delegated completion")
        typer.secho(
            f"cannot complete delegated period {ref.id_slug}: {exc}",
            fg=typer.colors.RED,
            err=True,
        )
        return DelegatedRunResult(2, "refused")
    except StrandedProductCode as exc:
        listed = "\n".join(f"    {path}" for path in exc.paths)
        typer.secho(
            f"Cannot finish {ref.id_slug}: its {exc.workflow_name} workflow "
            "has no push/PR step, but this checkout committed tracked product "
            f"code not on the control branch:\n{listed}",
            fg=typer.colors.RED,
            err=True,
        )
        return DelegatedRunResult(2, "done")
    except TaskValidationError as exc:
        if not publication_succeeded:
            _restore_refused_period_mutation(rollback, action="delegated completion")
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return DelegatedRunResult(2, "done")
    return DelegatedRunResult(0, "done")


def run_recurring_named(
    cfg: Config,
    name: str,
    *,
    interactive: bool = False,
    agent_override: str | None = None,
) -> int:
    """Create a named recurring template now and launch it.

    Ignores the template's schedule — the on-demand entry point behind
    aliases like `coga dream`. The task slug is the stable qualified
    `recurring/<name>`, so this and a bare `coga recurring` converge on one
    instantiated task directory.

    `agent_override` has the same ephemeral, agent-only semantics as the full
    recurring sweep. A git-backed run requires the configured control branch
    to be checked out, and the same committed-`owner` gate applies — this is a
    launch, so either refusal happens before the template is created.
    """
    if _refuse_non_control_branch(cfg):
        return 2
    fresh, _reason = _sync_control_checkout_ahead(cfg)
    if _refuse_non_owner(cfg):
        return 2
    if not _valid_agent_override(cfg, agent_override):
        return 2
    try:
        outcome = create_named(cfg, name)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return 2

    ref = outcome.ref
    control_ledger: dict[str, str] | None = None
    if fresh:
        # `create_named` captured this target-aware answer before it could
        # append its own record. The successful catch-up makes that local view
        # the pinned control snapshot, so no whole-blob `git show` is needed.
        template_ref = _recurring_ref(name)
        control_ledger = {
            _LEDGER_LOADED: "yes",
            _control_ledger_target_key(template_ref): outcome.period_key,
        }
        if outcome.prior_serviced_period is not None:
            control_ledger[template_ref] = outcome.prior_serviced_period
    try:
        if outcome.created:
            created_on_control = _sync_recurring_create(
                cfg,
                name,
                ref,
                respect_handled_period=False,
                expected_period_key=outcome.period_key,
                control_ledger=control_ledger,
            )
        else:
            _validate_control_serviced_period(
                cfg,
                name,
                control_ledger,
                expected_period_key=outcome.period_key,
            )
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return 2

    if outcome.created:
        if not (ref.ticket_path).is_file():
            typer.secho(
                f"{ref.id_slug} was already handled on the control branch; "
                "not launching.",
                fg=typer.colors.BRIGHT_BLACK,
            )
            return 0
        if created_on_control:
            typer.echo(f"Created {ref.id_slug}")
    else:
        typer.echo(f"{ref.id_slug} already created for this period")

    # An on-demand `coga recurring launch <name>` (the `coga dream`,
    # `coga autoclose`, and `coga skill-update` aliases) is a real run of a real
    # template, so it closes the same loop the scheduled sweep does.
    record = RunRecord(
        started=datetime.now(),
        repo=cfg.repo_root.name,
        on_demand=name,
        interactive=interactive,
        agent_override=agent_override,
    )
    try:
        return _launch_created(
            cfg,
            ref,
            interactive=interactive,
            agent_override=agent_override,
            record=record,
            template=name,
        )
    finally:
        # Only when something actually ran: `_launch_created` records the run
        # it performed, so an empty record means a gate refused to launch —
        # a closed or human-parked template, or one already handled on control.
        if record.outcomes:
            run_autofix(cfg, record, agent_override=agent_override)


def _sync_control_checkout_ahead(
    cfg: Config, *, announce_failure: bool = True
) -> tuple[bool, str]:
    """Catch the checked-out control branch up to origin before scanning.

    The scan decides what is due from working-tree templates and period tasks;
    starting from origin's tip means those reads see runs another machine
    already serviced, instead of relying solely on the per-create FETCH_HEAD
    checks. Runs while the tree is still clean of scan writes, so the rebase
    is normally a plain fast-forward. Only applies when this checkout holds
    the control branch. Returns a confirmation flag and an actionable reason.
    Bare and named sweeps keep misses best-effort because each create still
    reconciles against FETCH_HEAD; the `--all` child treats a false result as
    an entry-gate failure before scanning.

    A git failure (offline, conflicting local commits) writes one stderr note —
    unless the caller passes `announce_failure=False` because it is about to
    fail loud with the returned reason itself, in which case a note here would
    print the same conflict twice.
    """
    if not cfg.git_enabled:
        return False, "[git].enabled = false"
    root = _git_toplevel(cfg.repo_root)
    if root is None:
        return False, "workspace is not inside a git checkout"
    fetched = False
    try:
        current = _current_branch(root)
        if current != cfg.git_control_branch:
            where = "detached HEAD" if current == "HEAD" else f"branch {current!r}"
            return False, (
                f"configured control branch {cfg.git_control_branch!r} is not "
                f"checked out ({where})"
            )
        _fetch_control_branch(cfg, root)
        fetched = True
        target = _rev_parse(root, "FETCH_HEAD")
        _rebase_checked_out_branch_onto(root, target)
        _confirm_control_tip_integrated(root, target)
    except git.GitError as exc:
        reason = str(exc)
        if fetched:
            # The fetch worked, so this is a local-integration failure
            # (usually diverged local commits). Name the manual fix; a fetch
            # failure (offline, dead remote) gets no rebase advice.
            reason += (
                f"\nResolve in that checkout — e.g. `git -C {root} rebase "
                f"{cfg.git_remote}/{cfg.git_control_branch}` — then re-run."
            )
        if announce_failure:
            sys.stderr.write(f"[git] note: pre-scan catch-up skipped: {exc}\n")
        return False, reason
    return True, ""


def _launch_created(
    cfg: Config,
    ref: TaskRef,
    *,
    interactive: bool = False,
    agent_override: str | None = None,
    record: RunRecord | None = None,
    template: str = "",
) -> int:
    """Launch (or resume) a created recurring task.

    Recurring tasks create straight to `active` — machine-authored ready
    jobs, no separate activation step. An `in_progress` task is a *resume*: a
    past sweep died mid-run and left it frozen (`coga recurring` is a
    foreground command with no concurrent sweep, so it can only be an orphan),
    and `coga launch` re-composes it from its current `step:`.
    `done`/`canceled`/`paused` are left alone — re-launching closed or
    human-parked work would be wrong, and saying so beats silently doing nothing.

    `record`, when given, collects this run's outcome for the autofix loop. It
    is filled in here rather than by the caller because this is where the two
    "nothing actually ran" gates live: a task already handled on the control
    branch, and a closed or human-parked one. Neither is a run, and analyzing a
    sweep that never happened would only burn a call.
    """
    if not (ref.ticket_path).is_file():
        typer.secho(
            f"{ref.id_slug} was already handled on the control branch; not launching.",
            fg=typer.colors.BRIGHT_BLACK,
        )
        return 0

    ticket = read_ticket(ref)
    if ticket.status not in {"active", "in_progress"}:
        typer.secho(
            f"{ref.id_slug} is {ticket.status}; not launching.",
            fg=typer.colors.YELLOW,
        )
        return 0

    verb = "Resuming" if ticket.status == "in_progress" else "Launching"
    typer.echo(f"{verb} {ref.id_slug}")
    idle_timeout = None if interactive else _recurring_idle_timeout(cfg)
    max_session = None if interactive else _recurring_max_session(cfg)
    if "delegate" in ticket.frontmatter:
        # An on-demand named launch delegates exactly as the sweep does: the
        # runner launches the bootstrap target in this operator's terminal
        # and keeps the period task's bookkeeping to itself.
        delegated = _run_delegated_task(
            cfg,
            ref,
            agent_override=agent_override,
            idle_timeout=idle_timeout,
            max_session=max_session,
            queue_guidance=not interactive,
            continue_after_timeout=False,
        )
        if record is not None:
            record.add(
                _task_outcome(
                    cfg,
                    template or ref.slug,
                    ref,
                    kind=delegated.kind,
                    result=(
                        "failed"
                        if delegated.exit_code and delegated.kind != "timeout"
                        else ""
                    ),
                    exit_code=delegated.exit_code or None,
                )
            )
        return delegated.exit_code

    from coga.commands.launch import launch_recurring_period as launch_cmd

    try:
        kind = launch_cmd(
            ref.id_slug,
            agent_override=agent_override,
            prompt_report=False,
            idle_timeout=idle_timeout,
            max_session=max_session,
            return_timeout=False,
            script_failure_important=True,
            # Same queue posture as the full sweep: automatic launches get the
            # announce-and-continue / block-don't-ask guidance; `--interactive`
            # human-stepped runs keep plain launches.
            queue_guidance=not interactive,
        )
    except SystemExit as exc:
        # A failed `ticket.py` is this command's result, not a process abort:
        # returning the code keeps the caller's exit-boundary git sync.
        code = _exit_status(exc)
        if record is not None:
            record.add(
                _task_outcome(
                    cfg,
                    template or ref.slug,
                    ref,
                    result="failed" if code else "",
                    exit_code=code or None,
                )
            )
        return code
    if kind == "skipped":
        return 0
    if record is not None:
        record.add(_task_outcome(cfg, template or ref.slug, ref))
    return 0


def _exit_status(exc: SystemExit) -> int:
    """The integer result of a launch that exited instead of returning.

    `SystemExit.code` is `None` for a clean exit and may be a message string;
    a non-integer code is a failure by CPython's own convention.
    """
    if exc.code is None:
        return 0
    return exc.code if isinstance(exc.code, int) else 2


def _valid_agent_override(cfg: Config, agent_override: str | None) -> bool:
    """Fail loud on an unknown recurring agent, even when no task is due."""
    if agent_override is None:
        return True
    try:
        cfg.agent_type(agent_override)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return False
    return True


def _sync_recurring_create(
    cfg: Config,
    template_name: str,
    ref: TaskRef,
    *,
    respect_handled_period: bool = True,
    respect_existing_task: bool = True,
    restore_existing_control_task: bool = False,
    overwrite_dirty_control_task: bool = False,
    force_period_key: str | None = None,
    force_snapshot_is_fresh: bool = False,
    force_record_period: bool = False,
    expected_period_key: str | None = None,
    control_ledger: dict[str, str] | None = None,
) -> bool:
    """Sync the period task and ledger record that make deletion idempotent.

    `expected_period_key` bounds both the local reverse ledger read and any
    fallback control-snapshot read after they find a record sufficient for
    this sync's at-least comparison. Callers that cannot prove the period leave
    it unset and get the exact whole-ledger read.
    `control_ledger` is the caller's per-run snapshot of control's serviced
    periods; see `_control_serviced_period_cached` for why a sweep must share
    one.
    """
    template_dir = recurring_dir(cfg) / template_name
    message = f"Ticket: {ref.id_slug} — recurring create"
    if not template_dir.is_dir():
        git.sync_paths(
            cfg,
            ref.path,
            [ref.path],
            message=message,
        )
        return True
    # The serviced-period ledger is the repo-global, union-merged `coga/log.md`
    # (appended by `_record_run`), which never rides the cross-branch overlay —
    # so this sync reconciles no scheduler state at all. The template ticket
    # stays in the overlay only for the *run* cursors it carries
    # (`state_keys` values, the digest's `### Digest State`).
    template_ticket = template_dir / "ticket.md"
    original_ticket = template_ticket.read_text() if template_ticket.is_file() else ""
    local_ticket = original_ticket
    template_ref = _recurring_ref(template_name)
    if control_ledger is not None and expected_period_key is not None:
        # `_broadcast_scan` seeds every template before the first sync so the
        # shared snapshot resolves them in one reverse pass. Direct callers
        # still contribute their own target here.
        control_ledger.setdefault(
            _control_ledger_target_key(template_ref), expected_period_key
        )
    resolve_at = (
        {template_ref: expected_period_key}
        if expected_period_key is not None
        else None
    )
    ledger = read_serviced_ledger(cfg, resolve_at)
    ledger_error = ledger.errors.get(template_ref)
    if ledger_error is not None:
        raise RecurringError(ledger_error)
    period_key = ledger.periods.get(template_ref)
    state_keys: list[str] = []
    if force_period_key is not None:
        try:
            template = Template.load(template_dir)
        except RecurringError:
            template = None
        if template is not None:
            state_keys = list(template.frontmatter.get("state_keys") or [])
    restore_ticket = original_ticket
    created_on_control = True
    try:
        (
            restore_ticket,
            created_on_control,
        ) = _sync_recurring_create_paths(
            cfg,
            anchor_path=ref.path,
            paths=[ref.path, template_ticket],
            template_ticket=template_ticket,
            original_ticket=original_ticket,
            local_ticket=local_ticket,
            period_key=period_key,
            message=message,
            respect_handled_period=respect_handled_period,
            respect_existing_task=respect_existing_task,
            restore_existing_control_task=restore_existing_control_task,
            overwrite_dirty_control_task=overwrite_dirty_control_task,
            force_period_key=force_period_key,
            force_snapshot_is_fresh=force_snapshot_is_fresh,
            force_record_period=force_record_period,
            state_keys=state_keys,
            control_ledger=control_ledger,
        )
    except RecurringError:
        raise
    except Exception as exc:
        # `_sync_recurring_create_paths` already degrades on GitError. This
        # backstop keeps any *other* failure (subprocess, OS, racing control
        # pushes) from aborting the caller between task creation and launch —
        # the created task on disk is the source of truth, so a sync miss is
        # non-fatal: report + log, keep the task launchable.
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        _append_sync_failure(cfg, ref.path, exc)
    finally:
        if restore_ticket:
            template_ticket.write_text(restore_ticket)
    return created_on_control


def _sync_recurring_create_paths(
    cfg: Config,
    *,
    anchor_path: Path,
    paths: list[Path],
    template_ticket: Path,
    original_ticket: str,
    local_ticket: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
    respect_existing_task: bool,
    restore_existing_control_task: bool,
    overwrite_dirty_control_task: bool,
    force_period_key: str | None,
    force_snapshot_is_fresh: bool,
    force_record_period: bool,
    state_keys: list[str],
    control_ledger: dict[str, str] | None = None,
) -> tuple[str, bool]:
    """Sync create paths, carrying the period task and template cursors.

    The cross-branch overlay carries the period task dir and the template
    `ticket.md` (`rels`). The repo-global `coga/log.md` is union-merged and
    rides only the *local* commit (`_local_commit_rels`), never the overlay —
    mirroring `coga.git.sync_paths`.
    """
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return original_ticket, True

    root = _git_toplevel(anchor_path)
    if root is None:
        sys.stderr.write(f"[git] not a git repo (sync skipped): {message}\n")
        return original_ticket, True

    try:
        rels = [_relative_to_root(root, path) for path in paths]
        ticket_rel = _relative_to_root(root, template_ticket)
        local_rels = _local_commit_rels(cfg, root, rels)
        branch = _current_branch(root)

        try:
            _fetch_control_branch(cfg, root)
        except git.GitError:
            if local_ticket:
                template_ticket.write_text(local_ticket)
            git.sync_paths(cfg, anchor_path, paths, message=message)
            return original_ticket, True
        base = _rev_parse(root, "FETCH_HEAD")
        task_rel = _relative_to_root(root, anchor_path)
        restored_control_task = False
        restored_snapshot: str | None = None
        if restore_existing_control_task:
            restored_control_task, restored_snapshot = _restore_control_task_if_present(
                root,
                base,
                task_rel,
                preserve_local_changes=not overwrite_dirty_control_task,
            )
            if restored_control_task and force_period_key is not None:
                local_ticket = _reconcile_forced_period_after_control_restore(
                    cfg,
                    root,
                    base,
                    task_rel=task_rel,
                    template_ref=_template_ref_from_ticket_rel(ticket_rel),
                    template_ticket=template_ticket,
                    ticket_rel=ticket_rel,
                    task_id_slug=_task_id_slug_from_rel(task_rel),
                    force_period_key=force_period_key,
                    snapshot_text_is_fresh=force_snapshot_is_fresh,
                    snapshot_text=restored_snapshot,
                    snapshot_ticket_text=local_ticket,
                    record_period=force_record_period,
                    state_keys=state_keys,
                )
                if force_record_period:
                    period_key = force_period_key
                original_ticket = local_ticket
                if not force_record_period:
                    return local_ticket, False
        if _control_already_has_period(
            root,
            base,
            task_rel,
            log_rel=_relative_to_root(root, log_path(cfg)),
            template_ref=_template_ref_from_ticket_rel(ticket_rel),
            period_key=period_key,
            control_ledger=control_ledger,
            include_ledger=respect_handled_period,
            include_task=respect_existing_task,
        ):
            if branch == cfg.git_control_branch:
                _restore_selected_paths_from_ref(root, "HEAD", rels)
                _rebase_checked_out_branch_onto(root, base)
                # The create appended to the global log before the sync detected
                # the period was already handled on control; commit that line so
                # the control checkout is left clean (the overlay never carries
                # the log).
                _commit_global_log(cfg, root, message)
                return (
                    _control_template_or_local(
                        root, "HEAD", ticket_rel, original_ticket
                    ),
                    False,
                )
            _restore_selected_paths_from_ref(root, base, rels)
            if branch != "HEAD":
                git._commit_paths(root, local_rels, message)
                return (
                    _control_template_or_local(
                        root, "HEAD", ticket_rel, original_ticket
                    ),
                    False,
                )
            return (
                _control_template_or_local(
                    root, base, ticket_rel, original_ticket
                ),
                False,
            )
        _adopt_control_template(
            root, template_ticket, ticket_rel, base, local_ticket
        )

        if branch == cfg.git_control_branch:
            return _sync_recurring_create_on_checked_out_control_branch(
                cfg,
                root,
                rels,
                template_ticket=template_ticket,
                ticket_rel=ticket_rel,
                original_ticket=original_ticket,
                local_ticket=local_ticket,
                period_key=period_key,
                message=message,
                respect_handled_period=respect_handled_period,
                respect_existing_task=respect_existing_task,
                restore_existing_control_task=restore_existing_control_task,
                overwrite_dirty_control_task=overwrite_dirty_control_task,
                force_period_key=force_period_key,
                force_snapshot_is_fresh=force_snapshot_is_fresh,
                force_record_period=force_record_period,
                state_keys=state_keys,
                control_ledger=control_ledger,
            )

        committed_ticket = template_ticket.read_text()
        # Detached HEAD skips the local commit (it would be orphaned); the
        # landing push below fast-forwards the local control ref best-effort
        # via `git._try_update_local_ref`, which reports any miss to stderr.
        if branch != "HEAD":
            git._commit_paths(root, local_rels, message)
            committed_ticket = _show_path(root, "HEAD", ticket_rel)
        landed, already_handled = _land_recurring_create_on_control_branch(
            cfg,
            root,
            rels,
            template_ticket=template_ticket,
            ticket_rel=ticket_rel,
            task_rel=task_rel,
            local_ticket=local_ticket,
            period_key=period_key,
            message=message,
            respect_handled_period=respect_handled_period,
            respect_existing_task=respect_existing_task,
            restore_existing_control_task=restore_existing_control_task,
            overwrite_dirty_control_task=overwrite_dirty_control_task,
            force_period_key=force_period_key,
            force_snapshot_is_fresh=force_snapshot_is_fresh,
            force_record_period=force_record_period,
            state_keys=state_keys,
            control_ledger=control_ledger,
        )
        if already_handled:
            _restore_selected_paths_from_ref(root, landed, rels)
            if branch != "HEAD":
                git._commit_paths(root, local_rels, message)
                return (
                    _control_template_or_local(
                        root, "HEAD", ticket_rel, original_ticket
                    ),
                    False,
                )
            return (
                _control_template_or_local(
                    root, landed, ticket_rel, original_ticket
                ),
                False,
            )
        return (
            committed_ticket or original_ticket,
            True,
        )
    except git.GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        _append_sync_failure(cfg, anchor_path, exc)
        return original_ticket, True


def _local_commit_rels(cfg: Config, root: Path, rels: list[str]) -> list[str]:
    """The overlay `rels` plus the repo-global log for the *local* commit only.

    The global `coga/log.md` is `merge=union`, so it must never ride the
    cross-branch overlay (which replaces files wholesale). It is committed
    locally and reaches control via the same-branch push / PR merge.
    """
    log_file = log_path(cfg)
    if not log_file.exists():
        return rels
    log_rel = _relative_to_root(root, log_file)
    return rels if log_rel in rels else [*rels, log_rel]


def _commit_global_log(cfg: Config, root: Path, message: str) -> None:
    """Commit only the repo-global `coga/log.md`, if it has changes.

    The union-merge global log rides the *local* commit and never the
    cross-branch overlay, so every control-branch return path that may have left
    an appended log line in the working tree (a recurring create that the sync
    then detected was already handled on control, and unwound the task/ticket
    for) must commit it — otherwise the tree is left dirty. A no-op when the log
    is unchanged or the period task path was removed (only the log rel is
    passed, so a removed-task pathspec can't abort the commit)."""
    log_file = log_path(cfg)
    if log_file.exists():
        git._commit_paths(root, [_relative_to_root(root, log_file)], message)


def _control_template_or_local(
    root: Path, ref: str, ticket_rel: str, local_ticket: str
) -> str:
    """Control's template `ticket.md`, falling back to the local copy.

    The template no longer carries scheduler state — the serviced-period ledger
    is the repo-global log — but it still carries *run* cursors
    (`state_keys` values, the digest's `### Digest State`). Control wins because
    its copy holds whichever cursor advanced most recently, so a stale checkout
    adopts it instead of re-running from a stale cursor.
    """
    return _show_path(root, ref, ticket_rel) or local_ticket


def _append_sync_failure(cfg: Config, anchor_path: Path, exc: Exception) -> None:
    """Best-effort global-log note for non-fatal git sync failures."""
    if not anchor_path.is_dir():
        return
    try:
        append_log(cfg, ref_tag_for_path(cfg, anchor_path), "git", f"sync failed: {exc}")
    except OSError:
        return


def _land_recurring_create_on_control_branch(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    template_ticket: Path,
    ticket_rel: str,
    task_rel: str,
    local_ticket: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
    respect_existing_task: bool,
    restore_existing_control_task: bool,
    overwrite_dirty_control_task: bool,
    force_period_key: str | None,
    force_snapshot_is_fresh: bool,
    force_record_period: bool,
    state_keys: list[str],
    control_ledger: dict[str, str] | None = None,
    update_local_ref: bool = True,
) -> tuple[str, bool]:
    remote = cfg.git_remote
    branch = cfg.git_control_branch

    for _ in range(git._MAX_SYNC_ATTEMPTS):
        _fetch_control_branch(cfg, root)
        base = _rev_parse(root, "FETCH_HEAD")
        restored_control_task = False
        restored_snapshot: str | None = None
        if restore_existing_control_task:
            restored_control_task, restored_snapshot = _restore_control_task_if_present(
                root,
                base,
                task_rel,
                preserve_local_changes=not overwrite_dirty_control_task,
            )
            if restored_control_task and force_period_key is not None:
                local_ticket = _reconcile_forced_period_after_control_restore(
                    cfg,
                    root,
                    base,
                    task_rel=task_rel,
                    template_ref=_template_ref_from_ticket_rel(ticket_rel),
                    template_ticket=template_ticket,
                    ticket_rel=ticket_rel,
                    task_id_slug=_task_id_slug_from_rel(task_rel),
                    force_period_key=force_period_key,
                    snapshot_text_is_fresh=force_snapshot_is_fresh,
                    snapshot_text=restored_snapshot,
                    snapshot_ticket_text=local_ticket,
                    record_period=force_record_period,
                    state_keys=state_keys,
                )
                if force_record_period:
                    period_key = force_period_key
        if _control_already_has_period(
            root,
            base,
            task_rel,
            log_rel=_relative_to_root(root, log_path(cfg)),
            template_ref=_template_ref_from_ticket_rel(ticket_rel),
            period_key=period_key,
            control_ledger=control_ledger,
            include_ledger=respect_handled_period,
            include_task=respect_existing_task,
        ):
            return base, True
        _adopt_control_template(
            root, template_ticket, ticket_rel, base, local_ticket
        )
        control_rels = _control_create_rels(root, base, rels, ticket_rel)

        # The serviced-period record must reach control with the task it
        # describes. It lives in the repo-global `coga/log.md`, which is
        # `merge=union` and so must never ride the overlay (that replaces
        # files wholesale and would drop a peer's concurrent appends) — it
        # is three-way unioned into the control tree instead.
        #
        # Waiting for this branch's PR to merge is not good enough: the task
        # lands on control now, and if Dream reaps it before the merge — or
        # the branch never merges — control would hold neither the task nor
        # its record, and the period would fire again.
        tree = git._build_overlay_tree(
            root,
            base,
            control_rels,
            union_rels=_control_ledger_rels(cfg, root),
        )
        if tree == _rev_parse(root, f"{base}^{{tree}}"):
            return base, False

        new = git._run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
        result = git._push_ref(root, remote, f"{new}:refs/heads/{branch}")
        if result is None:
            if update_local_ref:
                git._try_update_local_ref(root, branch, new)
            return new, False
        if not git._is_non_fast_forward(result):
            raise git.GitError(
                f"`git push {remote} {new}:refs/heads/{branch}` failed: {result}"
            )

    raise git.GitError(
        f"could not land on {branch!r} after {git._MAX_SYNC_ATTEMPTS} attempts — "
        f"contention on refs/heads/{branch}"
    )


def _sync_recurring_create_on_checked_out_control_branch(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    template_ticket: Path,
    ticket_rel: str,
    original_ticket: str,
    local_ticket: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
    respect_existing_task: bool,
    restore_existing_control_task: bool,
    overwrite_dirty_control_task: bool,
    force_period_key: str | None,
    force_snapshot_is_fresh: bool,
    force_record_period: bool,
    state_keys: list[str],
    control_ledger: dict[str, str] | None = None,
) -> tuple[str, bool]:
    landed, already_handled = _land_recurring_create_on_control_branch(
        cfg,
        root,
        rels,
        template_ticket=template_ticket,
        ticket_rel=ticket_rel,
        task_rel=rels[0],
        local_ticket=local_ticket,
        period_key=period_key,
        message=message,
        respect_handled_period=respect_handled_period,
        respect_existing_task=respect_existing_task,
        restore_existing_control_task=restore_existing_control_task,
        overwrite_dirty_control_task=overwrite_dirty_control_task,
        force_period_key=force_period_key,
        force_snapshot_is_fresh=force_snapshot_is_fresh,
        force_record_period=force_record_period,
        state_keys=state_keys,
        control_ledger=control_ledger,
        # The checked-out control branch is reconciled right below via
        # restore + rebase; the landing's best-effort ff-merge would always
        # fail against this checkout's still-dirty create paths and print a
        # spurious "not fast-forwarded" note.
        update_local_ref=False,
    )
    _restore_selected_paths_from_ref(root, "HEAD", rels)
    _rebase_checked_out_branch_onto(root, landed)
    # The overlay already landed (and the rebase pulled in) the task dir +
    # template ticket; the only thing still uncommitted is the repo-global
    # `coga/log.md` (union-merge, excluded from the overlay, appended by
    # `_record_run`). Commit just that file so origin and the local control
    # branch reflect the history line and the tree is left clean.
    _commit_global_log(cfg, root, message)
    git._push_control_branch(cfg, root)
    if already_handled:
        return (
            _control_template_or_local(
                root, "HEAD", ticket_rel, original_ticket
            ),
            False,
        )
    return (
        _control_template_or_local(root, "HEAD", ticket_rel, original_ticket),
        True,
    )


def _control_ledger_rels(cfg: Config, root: Path) -> list[str]:
    """The repo-global log, as a union-merged path for a control-tree build."""
    log_file = log_path(cfg)
    if not log_file.exists():
        return []
    return [_relative_to_root(root, log_file)]


def _control_create_rels(
    root: Path, ref: str, rels: list[str], ticket_rel: str
) -> list[str]:
    if _ref_has_path(root, ref, ticket_rel):
        return rels
    return rels[:1]


def _control_already_has_period(
    root: Path,
    ref: str,
    task_rel: str,
    *,
    log_rel: str,
    template_ref: str,
    period_key: str | None,
    control_ledger: dict[str, str] | None = None,
    include_ledger: bool = True,
    include_task: bool = True,
) -> bool:
    # An override disables the *dedup decision*, not ledger validation. Always
    # parse control's record so `--force` / named launches cannot run through a
    # malformed high-water mark merely because its value will not be compared.
    serviced = _control_serviced_period_cached(
        root,
        ref,
        log_rel,
        template_ref,
        control_ledger,
        resolve_at=(
            {template_ref: period_key} if period_key is not None else None
        ),
    )
    if include_ledger and period_key is not None and serviced is not None:
        try:
            if period_key_at_least(serviced, period_key):
                return True
        except ValueError as exc:
            raise RecurringError(
                f"invalid serviced-period comparison for {template_ref}: {exc}"
            ) from exc
    return include_task and _ref_has_path(root, ref, task_rel)


def _control_serviced_period_cached(
    root: Path,
    ref: str,
    log_rel: str,
    template_ref: str,
    control_ledger: dict[str, str] | None,
    *,
    resolve_at: Mapping[str, str] | None = None,
) -> str | None:
    """Control's serviced period for `template_ref`, read at most once per run.

    `control_ledger` is a per-run cache owned by the caller, resolved for every
    target in one pass on first use (or preloaded from a successful pre-scan
    control catch-up). The repo-global log holds all templates' records in one
    file, so the first sync of a sweep pushes the whole file — including the
    lines this same sweep just wrote for templates it has not synced yet.
    Reading control per template, even cached per template, would let a later
    template mistake its own pending record for another checkout's and delete
    the task it just created. Capturing every entry at once, before the sweep
    publishes anything, keeps the check answering the question it is for.

    The trade-off is deliberate: a competing push landing *mid-sweep* is not
    seen by this half of the guard. The task-presence half still catches it,
    and reading fresh reintroduces the self-collision above.
    """
    if control_ledger is None:
        ledger = _read_control_ledger(root, ref, log_rel, resolve_at)
        error = ledger.get(_control_ledger_error_key(template_ref))
        if error is not None:
            raise RecurringError(error)
        return ledger.get(template_ref)
    if not control_ledger.get(_LEDGER_LOADED):
        targets = _control_ledger_targets(control_ledger)
        control_ledger.update(
            _read_control_ledger(root, ref, log_rel, targets or resolve_at)
        )
        control_ledger[_LEDGER_LOADED] = "yes"
    error = control_ledger.get(_control_ledger_error_key(template_ref))
    if error is not None:
        raise RecurringError(error)
    return control_ledger.get(template_ref)


def _validate_control_serviced_period(
    cfg: Config,
    template_name: str,
    control_ledger: dict[str, str] | None = None,
    *,
    expected_period_key: str | None = None,
) -> None:
    """Fail on malformed control-ledger state without changing task state.

    A prior sweep can leave a locally created task behind after its control
    sync discovers a malformed record. Reused tasks skip create-sync, so they
    pass through this read-only gate on every later sweep instead of launching
    after the first warning. A shared cache pins the same pre-publication
    control snapshot for every template in one sweep.

    Control freshness remains best-effort for bare/named single-repo launches,
    matching their existing sync contract. A reachable malformed record is a
    hard template error; an unreachable remote keeps the existing loud Git
    warning and local behavior.
    """
    if not cfg.git_enabled:
        return
    root = _git_toplevel(cfg.repo_root)
    if root is None:
        return

    if control_ledger is not None and control_ledger.get(_LEDGER_LOADED):
        ref = "HEAD"  # ignored once the shared ledger snapshot is populated
    else:
        try:
            _fetch_control_branch(cfg, root)
            ref = _rev_parse(root, "FETCH_HEAD")
        except git.GitError as exc:
            sys.stderr.write(
                f"[git] control serviced-ledger validation skipped: {exc}\n"
            )
            return

    _control_serviced_period_cached(
        root,
        ref,
        _relative_to_root(root, log_path(cfg)),
        _recurring_ref(template_name),
        control_ledger,
        resolve_at=(
            {_recurring_ref(template_name): expected_period_key}
            if expected_period_key is not None
            else None
        ),
    )


def _restore_selected_paths_from_ref(root: Path, ref: str, rels: list[str]) -> None:
    for rel in rels:
        if _ref_has_path(root, ref, rel):
            git._run_git(
                root, "restore", "--source", ref, "--staged", "--worktree", "--", rel
            )
            continue
        git._run_git(root, "rm", "-rf", "--cached", "--ignore-unmatch", "--", rel)
        path = Path(rel) if Path(rel).is_absolute() else root / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def _restore_control_task_if_present(
    root: Path, ref: str, task_rel: str, *, preserve_local_changes: bool
) -> tuple[bool, str | None]:
    if not _ref_has_path(root, ref, task_rel):
        return False, None
    if preserve_local_changes and _path_has_local_changes(root, task_rel):
        return False, None
    snapshot = root / task_rel / ".state-snapshot.json"
    snapshot_text = snapshot.read_text() if snapshot.is_file() else None
    _restore_selected_paths_from_ref(root, ref, [task_rel])
    return True, snapshot_text


def _path_has_local_changes(root: Path, rel: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", rel],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return any(not _is_generated_snapshot_status(line, rel) for line in lines)


def _is_generated_snapshot_status(line: str, rel: str) -> bool:
    snapshot_rel = f"{Path(rel).as_posix().rstrip('/')}/.state-snapshot.json"
    path = line[3:].strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    return path == snapshot_rel


def _reconcile_forced_period_after_control_restore(
    cfg: Config,
    root: Path,
    ref: str,
    *,
    task_rel: str,
    ticket_rel: str,
    template_ref: str,
    template_ticket: Path,
    task_id_slug: str,
    force_period_key: str,
    snapshot_text_is_fresh: bool,
    snapshot_text: str | None,
    snapshot_ticket_text: str,
    record_period: bool,
    state_keys: list[str],
) -> str:
    """Recompute forced-run bookkeeping after local task state is current.

    Returns the template text to keep locally. The serviced-period ledger is
    the repo-global log, so nothing scheduler-owned is merged here; the
    template is touched only for the *run* cursors it carries.
    """
    control_ticket = _show_path(root, ref, ticket_rel)
    if not record_period:
        # Discovery only. The local template already holds its own cursors and
        # there is no mark to adopt from control, so leave it as it stands.
        return snapshot_ticket_text

    template_ticket.write_text(control_ticket or snapshot_ticket_text)
    _append_forced_reused_log(cfg, template_ref, task_id_slug, force_period_key)

    snapshot = root / task_rel / SNAPSHOT_FILE
    if snapshot_text is not None and snapshot_text_is_fresh:
        snapshot.write_text(snapshot_text)
    elif state_keys:
        _write_snapshot_from_text(
            root / task_rel,
            Path(task_id_slug).name,
            snapshot_ticket_text,
            state_keys,
        )

    return template_ticket.read_text() if template_ticket.is_file() else ""


def _append_forced_reused_log(
    cfg: Config, template_ref: str, task_id_slug: str, period_key: str
) -> None:
    """Record a forced reuse in the repo-global ledger, idempotently.

    Skipped when the same line is already present, so repeated `--force` runs
    inside one period leave one record rather than one per invocation.
    """
    needle = format_serviced_log("reused", task_id_slug, period_key)
    if any(needle in line for line in task_log_lines(cfg, template_ref)):
        return
    append_log(cfg, template_ref, "system", needle)


def _write_snapshot_from_text(
    task_dir: Path, parent: str, blackboard_text: str, state_keys: list[str]
) -> None:
    keys = parse_keys(blackboard_text, list(state_keys))
    payload = {"parent": parent, "keys": keys}
    (task_dir / SNAPSHOT_FILE).write_text(json.dumps(payload, indent=2) + "\n")


def _task_id_slug_from_rel(rel: str) -> str:
    parts = Path(rel).parts
    if "tasks" not in parts:
        return Path(rel).name
    i = len(parts) - 1 - list(reversed(parts)).index("tasks")
    return "/".join(parts[i + 1 :])


def _ref_has_path(root: Path, ref: str, rel: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{ref}:{rel}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _rebase_checked_out_branch_onto(root: Path, target: str) -> None:
    if _rev_parse(root, "HEAD") == target:
        return

    proc = subprocess.run(
        ["git", "-C", str(root), "-c", "rebase.autoStash=true", "rebase", target],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return

    subprocess.run(
        ["git", "-C", str(root), "rebase", "--abort"],
        capture_output=True,
        text=True,
        check=False,
    )
    raise git.GitError(
        f"could not rebase checked-out control branch onto {target}: "
        f"{git.summarize_git_failure(proc.stderr + proc.stdout)}"
    )


def _confirm_control_tip_integrated(root: Path, target: str) -> None:
    """Fail unless `target` is in HEAD and the working tree has no conflicts."""
    ancestor = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", target, "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise git.GitError(
            f"fetched control tip {target} is not integrated into HEAD"
        )

    unmerged = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=U"],
        capture_output=True,
        text=True,
        check=False,
    )
    if unmerged.returncode != 0:
        raise git.GitError(
            "could not verify the checkout has no unresolved merge conflicts"
        )
    conflicts = [line for line in unmerged.stdout.splitlines() if line]
    if conflicts:
        raise git.GitError(
            "checkout still has unresolved merge conflicts: "
            + ", ".join(conflicts)
        )


def _adopt_control_template(
    root: Path,
    template_ticket: Path,
    ticket_rel: str,
    ref: str,
    local_ticket: str,
) -> None:
    """Point the local template at control's copy of its run cursors."""
    template_ticket.write_text(
        _control_template_or_local(root, ref, ticket_rel, local_ticket)
    )


# Sentinel key marking a per-run control-ledger cache as populated.
_LEDGER_LOADED = "\0loaded"
_LEDGER_ERROR_PREFIX = "\0error:"
_LEDGER_TARGET_PREFIX = "\0target:"

_CONTROL_LOG_ENTRY_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} \[(?P<ref>[^\]]*)\] \[[^\]]*\] "
    r"(?P<message>.*)$"
)


def _recurring_ref(template_name: str) -> str:
    """The log tag for a template — `recurring/<name>`."""
    return f"recurring/{template_name}"


def _template_ref_from_ticket_rel(ticket_rel: str) -> str:
    """`.../recurring/<name>/ticket.md` → the `recurring/<name>` log tag."""
    return _recurring_ref(PurePosixPath(ticket_rel).parent.name)


def _control_ledger_error_key(template_ref: str) -> str:
    return f"{_LEDGER_ERROR_PREFIX}{template_ref}"


def _control_ledger_target_key(template_ref: str) -> str:
    return f"{_LEDGER_TARGET_PREFIX}{template_ref}"


def _control_ledger_targets(control_ledger: Mapping[str, str]) -> dict[str, str]:
    return {
        key.removeprefix(_LEDGER_TARGET_PREFIX): value
        for key, value in control_ledger.items()
        if key.startswith(_LEDGER_TARGET_PREFIX)
    }


def _read_control_ledger(
    root: Path,
    ref: str,
    log_rel: str,
    resolve_at: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Read serviced periods from the pinned control log at `ref`.

    `resolve_at` applies the same per-template target proof as the working-tree
    reader. A sweep supplies all of its targets together, so even this fallback
    captures one shared pre-publication snapshot rather than reading lazily per
    template. Without targets the exact whole-ledger parse remains available
    to callers that cannot state an at-least question.
    """
    text = _show_path(root, ref, log_rel)
    if not text:
        return {}

    lines = text.splitlines()

    def entries(source: Iterable[str]) -> Iterable[tuple[str, str]]:
        for line in source:
            match = _CONTROL_LOG_ENTRY_RE.match(line)
            if match is not None:
                yield match.group("ref"), match.group("message")

    ledger = (
        parse_serviced_period_entries(entries(iter(lines)))
        if resolve_at is None
        else parse_serviced_period_entries_reverse(
            entries(reversed(lines)), resolve_at
        )
    )
    out = dict(ledger.periods)
    for template_ref, error in ledger.errors.items():
        out[_control_ledger_error_key(template_ref)] = error
    return out


def _show_path(root: Path, ref: str, rel: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"{ref}:{rel}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def _fetch_control_branch(cfg: Config, root: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "fetch", cfg.git_remote, cfg.git_control_branch],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise git.GitError("`git` not found on PATH") from exc
    if result.returncode != 0:
        raise git.GitError(
            f"`git fetch {cfg.git_remote} {cfg.git_control_branch}` failed "
            f"(exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def _rev_parse(root: Path, ref: str) -> str:
    return git._run_git(root, "rev-parse", ref).strip()


def _current_branch(root: Path) -> str:
    # `rev-parse --abbrev-ref HEAD` returns `heads/<name>` when a tag shadows
    # the branch. `branch --show-current` is unambiguous and empty when detached.
    current = git._run_git(root, "branch", "--show-current").strip()
    return current or "HEAD"


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _git_toplevel(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    top = result.stdout.strip()
    return Path(top) if top else None


def _stop_if_unfinished_after_launch(
    cfg: Config,
    ref: TaskRef,
    *,
    timed_out: bool = False,
    script_stopped: bool = False,
    expected_period_lease: _PeriodLease | None = None,
    require_period_publication: bool = False,
) -> None:
    """Pause a recurring task when its agent launch returns unfinished.

    Exiting an agent without a terminal transition parks that run. Make it
    durable by pausing the task, then continue; otherwise the next scan would
    treat the leftover `in_progress` state as a dead supervisor's orphan and
    relaunch it.

    `timed_out` is set when `launch` reported a liveness teardown (idle /
    max-session) — the agent wedged and never signalled done. That must NOT be
    recorded as an ordinary pause: it isn't a deliberate park, it's a stuck
    run. We pause it (so the next scan doesn't relaunch the orphan) but log and
    broadcast it as a watchdog *timeout*, with a system actor, then continue the
    sweep so one wedge can't starve the tasks behind it.

    A script that deliberately records `blocked` has also completed its
    deterministic phase: preserve that supported lifecycle signal. An agent
    session that blocks is still paused by the scheduled-run contract, so this
    exception is gated on the launcher's script-only stop kind.
    """
    if not (ref.ticket_path).exists():
        return

    if (
        expected_period_lease is not None
        and _local_period_lease(cfg, ref) != expected_period_lease
    ):
        raise RecurringError(
            f"cannot pause delegated period {ref.id_slug}: its ticket or task "
            "audit generation changed after the child exited"
        )

    ticket = read_ticket(ref)
    if ticket.status in TERMINAL_STATUSES or ticket.status == "paused":
        return
    if script_stopped and ticket.status == "blocked":
        return

    if timed_out:
        suffix = "liveness watchdog: REPL timed out before signalling done"
        rollback = (
            _period_mutation_snapshot(cfg, ref)
            if expected_period_lease is not None
            else None
        )
        publication_succeeded = False

        def record_publication() -> None:
            nonlocal publication_succeeded
            publication_succeeded = True

        try:
            mark_paused(
                cfg,
                ref,
                ticket,
                actor="system:watchdog",
                log_message=f"paused ({ticket.status} → paused) — {suffix}",
                slack_text=(
                    f"⏱️ *{ref.id_slug}* \"{ticket.title}\" timed out — {suffix}"
                ),
                digest_detail=f"→ paused (timeout) — {suffix}",
                echo=None,
                mutation_snapshot=rollback,
                after_sync=(
                    record_publication
                    if expected_period_lease is not None
                    else None
                ),
                state_guard=(
                    _period_lease_guard(cfg, ref, expected_period_lease)
                    if expected_period_lease is not None
                    else None
                ),
                strict_state_guard=expected_period_lease is not None,
                strict_state_sync=require_period_publication,
            )
        except git.GitError as exc:
            if rollback is not None and not publication_succeeded:
                _restore_refused_period_mutation(
                    rollback, action="delegated timeout"
                )
            raise RecurringError(
                f"cannot pause delegated period {ref.id_slug}: {exc}"
            ) from exc
        except TaskValidationError as exc:
            if rollback is not None and not publication_succeeded:
                _restore_refused_period_mutation(
                    rollback, action="delegated timeout"
                )
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)
        typer.secho(
            f"{ref.id_slug}: timed out (status={ticket.status!r}); paused as a "
            "watchdog timeout and continuing to next due task.",
            fg=typer.colors.YELLOW,
        )
        return

    suffix = "Agent recurring launch exited unfinished"
    try:
        mark_paused(
            cfg,
            ref,
            ticket,
            actor=f"human:{cfg.current_user}",
            log_message=f"paused ({ticket.status} → paused) — {suffix}",
            echo=None,
        )
    except TaskValidationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    typer.secho(
        f"{ref.id_slug}: ended with status={ticket.status!r}; "
        "paused and continuing to next due task.",
        fg=typer.colors.YELLOW,
    )


# --- scan reporting -----------------------------------------------------------


def _env_seconds(name: str) -> tuple[bool, float | None]:
    """Read a seconds value from env var `name`.

    Returns `(present, value)`: `present` is False when the var is unset (so
    the caller falls back to config/default); when set, `value` is the parsed
    seconds or None for a `<= 0`, non-finite, or unparseable value (an explicit
    "disarm this backstop"). The env override always wins over config when set —
    even to disarm — so a machine can turn a committed default off locally.
    """
    raw = os.environ.get(name)
    if raw is None:
        return False, None
    try:
        seconds = float(raw)
    except ValueError:
        return True, None
    if not math.isfinite(seconds) or seconds <= 0:
        return True, None
    return True, seconds


def _recurring_idle_timeout(cfg) -> float | None:
    """Idle-timeout (seconds) for interactive REPLs the sweep spawns.

    Precedence: `COGA_REPL_IDLE_TIMEOUT` env override > `[launch].idle_timeout`
    in `coga.toml` (`cfg.launch_idle_timeout`) > the `_RECURRING_IDLE_TIMEOUT_
    SECONDS` default. A `<= 0`, non-finite (`inf`/`nan`), or unparseable env
    value disarms the backstop (returns None). Read-only — the value is passed
    explicitly to `coga launch`, never written back to the environment, so it
    cannot leak into the process or a spawned child.
    """
    present, value = _env_seconds("COGA_REPL_IDLE_TIMEOUT")
    if present:
        return value
    if cfg.launch_idle_timeout_present:
        return cfg.launch_idle_timeout
    return _RECURRING_IDLE_TIMEOUT_SECONDS


def _recurring_max_session(cfg) -> float | None:
    """Max-session wall-clock cap (seconds) for the REPLs the sweep spawns.

    Precedence: `COGA_REPL_MAX_SESSION` env override > `[launch].max_session`
    (`cfg.launch_max_session`) > None (no cap). Unlike idle-timeout there is no
    built-in default — a wall-clock cap is opt-in, since a legitimately long
    interactive step shouldn't be killed unless the team asked for it. A `<= 0`,
    non-finite, or unparseable env value disarms it.
    """
    present, value = _env_seconds("COGA_REPL_MAX_SESSION")
    if present:
        return value
    return cfg.launch_max_session


def _prepare_forced_launch(cfg: Config, task: DueTask) -> None:
    """Record a forced rerun only once the sweep reaches this task.

    `coga recurring --force` includes existing `done`/`canceled`/`paused`
    period tasks. Those tasks must not advance the parent high-water during
    scan: a prior task might stop the sequential sweep first. Once we reach the
    task, refuse it if canceled; otherwise flip it back to `active`, then record
    the forced period and sync the real task.
    If the later launch preflight fails, the task is at least live for a future
    normal sweep instead of being silently skipped as already serviced.
    """
    if task.ref is None:
        return

    if not (task.ref.ticket_path).is_file():
        outcome = create_named(cfg, task.template)
        task.ref = outcome.ref
        task.created = outcome.created

    if not task.created:
        _sync_recurring_create(
            cfg,
            task.template,
            task.ref,
            respect_handled_period=False,
            respect_existing_task=False,
            restore_existing_control_task=True,
            overwrite_dirty_control_task=False,
            force_period_key=task.period_key,
            force_snapshot_is_fresh=False,
            force_record_period=False,
            expected_period_key=task.period_key,
        )

    ticket = read_ticket(task.ref)
    task.status = ticket.status
    if ticket.status == "canceled":
        raise RecurringError(
            f"cannot force-run {task.ref.id_slug}: its task is canceled and "
            "cannot be reactivated; delete it before starting a fresh run"
        )
    if not task.created and ticket.status in {"active", "in_progress"}:
        return

    if ticket.status not in {"active", "in_progress"}:
        prior = ticket.status
        mark_active(
            cfg,
            task.ref,
            ticket,
            actor=f"human:{cfg.current_user}",
            log_message=f"activated ({prior} → active) for forced recurring run",
            echo=f"{task.ref.id_slug}: active (forced recurring run)",
        )
        task.status = "active"
    _record_forced_period_locally(cfg, task)
    _sync_recurring_create(
        cfg,
        task.template,
        task.ref,
        respect_handled_period=False,
        respect_existing_task=False,
        restore_existing_control_task=False,
        overwrite_dirty_control_task=False,
        expected_period_key=task.period_key,
    )


def _record_forced_period_locally(cfg: Config, task: DueTask) -> None:
    if task.ref is None or not task.period_key:
        return

    template_dir = recurring_dir(cfg) / task.template
    template = Template.load(template_dir)
    blackboard_text = (
        read_blackboard(template.ticket_path, blackboard_required=False)
        if template.ticket_path.is_file()
        else ""
    )
    state_keys = list(template.frontmatter.get("state_keys") or [])
    if state_keys:
        _write_snapshot_from_text(
            task.ref.path,
            template.name,
            blackboard_text,
            state_keys,
        )

    _append_forced_reused_log(
        cfg, _recurring_ref(template.name), task.ref.id_slug, task.period_key
    )


def _broadcast_scan(
    cfg,
    scan: DueScan,
    *,
    respect_handled_period: bool = True,
    sync_existing: bool = False,
    control_is_fresh: bool = False,
) -> None:
    """Post Slack lines for newly created tasks and skipped templates.

    In `--all` mode, also refresh existing task status from the control branch
    before the launch list is sorted. A stale local `done` copy may be an
    `in_progress` orphan on control, and resume-first ordering depends on the
    current status. The actual restore/sync still happens when the launch loop
    reaches that task, so an unreached task is not mutated during the scan.
    """
    # One control-ledger snapshot for the whole sweep: the first sync publishes
    # the shared log, so a per-task read would see this sweep's own pending
    # records as another checkout's.
    targets = scan.period_targets or {
        _recurring_ref(task.template): task.period_key
        for task in scan.tasks
        if task.period_key
    }
    control_ledger: dict[str, str] = {
        _control_ledger_target_key(ref): period
        for ref, period in targets.items()
    }
    if control_is_fresh:
        # `scan_due` took this target-bounded snapshot immediately after the
        # successful pre-scan catch-up and before any create appended to the
        # shared log. Reusing it is both the self-collision guard and the only
        # way a normal git-backed sweep can retain the local reverse reader's
        # bounded I/O; reading the Git blob would materialize the whole log.
        control_ledger.update(scan.ledger_periods)
        control_ledger.update(
            {
                _control_ledger_error_key(ref): error
                for ref, error in scan.ledger_errors.items()
            }
        )
        control_ledger[_LEDGER_LOADED] = "yes"
    for task in list(scan.tasks):
        try:
            if not task.created and not task.replaced_done:
                _validate_control_serviced_period(
                    cfg,
                    task.template,
                    control_ledger,
                    expected_period_key=task.period_key,
                )
                if sync_existing:
                    _refresh_forced_status_from_control(cfg, task)
                continue
            if task.ref is None:
                continue
            created_on_control = _sync_recurring_create(
                cfg,
                task.template,
                task.ref,
                respect_handled_period=respect_handled_period,
                # A normal replacement deliberately replaces the prior-period
                # `done` task at the stable path. The period ledger still guards
                # against racing another machine that handled this firing first.
                respect_existing_task=not (sync_existing or task.replaced_done),
                restore_existing_control_task=sync_existing,
                overwrite_dirty_control_task=sync_existing and task.created,
                force_period_key=task.period_key if sync_existing else None,
                force_snapshot_is_fresh=False,
                force_record_period=False,
                expected_period_key=task.period_key,
                control_ledger=control_ledger,
            )
        except RecurringError as exc:
            scan.tasks.remove(task)
            sys.stderr.write(f"[recurring] skipping {task.template}: {exc}\n")
            scan.errors.append((task.template, str(exc)))
            continue
        if not (task.ref.ticket_path).is_file():
            scan.tasks.remove(task)
            typer.secho(
                f"{task.ref.id_slug} was already handled on the control branch; "
                "not launching.",
                fg=typer.colors.BRIGHT_BLACK,
            )
            continue
        ticket = read_ticket(task.ref)
        task.status = ticket.status
        if sync_existing and not created_on_control:
            task.created = False
        if task.replaced_done and created_on_control:
            typer.echo(f"Replaced completed {task.ref.id_slug}")
        elif task.created and created_on_control:
            typer.echo(f"Created {task.ref.id_slug}")

    if scan.errors:
        n = len(scan.errors)
        plural = "" if n == 1 else "s"
        bullets = "\n".join(f"• {name}: {msg}" for name, msg in scan.errors)
        inline = "; ".join(f"{name} ({msg})" for name, msg in scan.errors)
        notify(
            cfg,
            f"⚠️ recurring scan skipped {n} template{plural}\n{bullets}",
            kind="recurring-error",
            detail=f"⚠️ recurring scan skipped {n} template{plural}: {inline}",
            important=True,
        )


def _refresh_forced_status_from_control(cfg: Config, task: DueTask) -> None:
    """Best-effort read-only status refresh for `--all` launch ordering."""
    if task.ref is None or not cfg.git_enabled:
        return
    root = _git_toplevel(task.ref.path)
    if root is None:
        return
    task_rel = _relative_to_root(root, task.ref.path)
    if _path_has_local_changes(root, task_rel):
        return
    try:
        _fetch_control_branch(cfg, root)
        base = _rev_parse(root, "FETCH_HEAD")
    except git.GitError as exc:
        sys.stderr.write(f"[git] forced status refresh skipped: {exc}\n")
        return
    text = _show_path(root, base, f"{task_rel}/ticket.md")
    if not text:
        return
    try:
        ticket = Ticket.parse(text)
    except TicketError:
        return
    task.status = ticket.status


def _print_table(scan: DueScan, *, force: bool = False) -> None:
    """Print a one-line-per-template scan summary."""
    if not scan.tasks and not scan.errors:
        return

    now = datetime.now()
    typer.echo(f"Recurring scan — {now:%Y-%m-%d %H:%M}\n")
    for task in scan.tasks:
        when = _firing_label(task.last_fire, now)
        if task.ref is None:
            # The period was created earlier this cycle and the task
            # was removed afterwards (a later Dream retro pass or `coga delete`).
            action = typer.style(
                "skip (ran this period)", fg=typer.colors.BRIGHT_BLACK
            )
        elif task.resuming:
            # An orphaned `in_progress` period task from a dead sweep — relaunch
            # resumes its current step rather than starting a fresh run.
            action = typer.style("→ resume", fg=typer.colors.YELLOW)
        elif task.launchable or force:
            action = typer.style("→ launch", fg=typer.colors.GREEN)
        else:
            action = typer.style(
                f"skip ({task.status})", fg=typer.colors.BRIGHT_BLACK
            )
        typer.echo(f"  {task.template:<20} {when:<26} {action}")

    for name, msg in scan.errors:
        bad = typer.style(f"skip (error: {msg})", fg=typer.colors.RED)
        typer.echo(f"  {name:<20} {'':<26} {bad}")


def _firing_label(last_fire: datetime, now: datetime) -> str:
    """Human label for a scheduled firing — 'ready' or 'overdue Nd'."""
    delta = now - last_fire
    stamp = last_fire.strftime("%a %H:%M")
    if delta.total_seconds() < 86400:
        return f"ready ({stamp})"
    return f"overdue {delta.days}d ({stamp})"
