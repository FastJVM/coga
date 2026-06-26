"""`relay digest` — post one outcome-focused daily Slack digest.

This is the **consumer** half of the daily-digest pipeline. Done events and
recurring scan errors spool structured JSONL records onto the
`recurring/digest/` ticket's blackboard as they happen (see
`relay.notification.notify`). Once a day the digest recurring ticket fires as a
`mode: script` task, and its script step runs this command:

  read the spool → fetch origin/main → render Done + Also merged → post via
  the webhook → empty the spool → record the new git high-water mark.

Idempotent: when there are no Done/error records and no new post-filter
commits, the command stays silent. The spool is emptied only after a successful
post, or after deciding the pending records contain only now-silent legacy
lifecycle chatter. A failed post leaves the records and git state intact for
the next run.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer

from relay import spool
from relay.atomicio import atomic_write_text
from relay.config import ConfigError, load_config
from relay.notification import digest_spool_path, done_pr_numbers, post, render_digest


_STATE_HEADING = "Digest State"
_STATE_RE = re.compile(
    rf"^###\s+{re.escape(_STATE_HEADING)}\s*$\n?(.*?)(?=^##\s|^###\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_PR_FROM_SUBJECT_RE = re.compile(r"(?:\(#(\d+)\)|pull request #(\d+)|PR #(\d+))", re.I)


class DigestGitError(RuntimeError):
    """Raised when the digest's control-branch scan fails."""


def digest(
    quiet_empty: bool = typer.Option(
        True,
        "--quiet-empty/--announce-empty",
        help="On an empty spool, stay silent (default) or print a one-line note.",
    ),
) -> None:
    """Post Done tickets and other merged commits, then update digest state."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    run_digest(cfg, quiet_empty=quiet_empty)


def run_digest(cfg, *, quiet_empty: bool = True) -> bool:
    """Render and post the daily digest; return whether anything sent.

    Returns False when the digest ticket isn't installed or there is no
    outcome to post. Empty spool is not enough to skip: the command still scans
    the control branch for commits merged since the last recorded high-water
    mark.
    """
    spool_path = digest_spool_path(cfg)
    if spool_path is None:
        if not quiet_empty:
            typer.secho(
                "digest: no recurring/digest/ ticket installed — nothing to flush.",
                fg=typer.colors.YELLOW,
                err=True,
            )
        return False

    records = spool.read_records(spool_path)
    try:
        merged, state = _scan_control_branch(cfg, spool_path, done_pr_numbers(records))
    except DigestGitError as exc:
        typer.secho(f"digest: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    renderable_records = [
        rec for rec in records if rec.get("kind") in {"done", "recurring-error"}
    ]
    should_post = bool(renderable_records or merged)
    date_label = datetime.now().strftime("%Y-%m-%d")

    if not should_post:
        if records:
            spool.drain(spool_path)
        if state is not None:
            _write_digest_state(
                spool_path,
                last_commit=state["head"],
                range_label=state["range"],
                posted="skipped — no done tickets or new commits",
            )
        if not quiet_empty:
            typer.echo("digest: no done tickets or new commits — nothing to post.")
        return False

    message = render_digest(
        cfg,
        renderable_records,
        date_label=date_label,
        also_merged=merged,
    )
    item_count = len(renderable_records) + len(merged)
    typer.echo(f"digest: posting {item_count} item(s) for {date_label}")
    post(cfg, message, task_path=spool_path.parent)
    spool.drain(spool_path)
    if state is not None:
        _write_digest_state(
            spool_path,
            last_commit=state["head"],
            range_label=state["range"],
            posted="yes",
        )
    return True


def _scan_control_branch(
    cfg,
    state_path: Path,
    done_prs: set[int],
) -> tuple[list[dict], dict[str, str] | None]:
    """Fetch and scan the configured control branch for unclaimed commits.

    A non-git repo, or one with git sync explicitly disabled, behaves like
    "no commits" so tests and solo scratch repos can still flush Done records.
    A real fetch/log failure is crash-loud because a stale commit digest is
    worse than no digest.
    """
    if not cfg.git_enabled:
        return [], None

    root = _git_toplevel(cfg.repo_root)
    if root is None:
        return [], None

    _run_git(root, "fetch", cfg.git_remote, cfg.git_control_branch)
    head = _run_git(root, "rev-parse", "FETCH_HEAD").strip()
    last = _read_last_commit(state_path)
    if last and _commit_exists(root, last):
        raw = _run_git(root, "log", "--reverse", "--format=%H%x00%s", f"{last}..{head}")
        range_label = f"{last[:7]}..{head[:7]}"
    else:
        raw = _run_git(
            root,
            "log",
            "--reverse",
            "--since=24 hours ago",
            "--format=%H%x00%s",
            head,
        )
        range_label = f"last 24h..{head[:7]}"

    commits = [_parse_commit_line(line) for line in raw.splitlines() if line.strip()]
    filtered = [
        commit
        for commit in commits
        if not _is_relay_state_sync_commit(commit["subject"])
        and commit.get("pr_number") not in done_prs
    ]
    state = {
        "head": head,
        "range": f"{range_label} ({len(commits)} commit(s), {len(filtered)} reported)",
    }
    return filtered, state


def _parse_commit_line(line: str) -> dict:
    sha, _, subject = line.partition("\x00")
    pr_number = _subject_pr_number(subject)
    record: dict[str, object] = {"sha": sha, "subject": subject}
    if pr_number is not None:
        record["pr_number"] = pr_number
    return record


def _subject_pr_number(subject: str) -> int | None:
    match = _PR_FROM_SUBJECT_RE.search(subject)
    if not match:
        return None
    for group in match.groups():
        if group is not None:
            return int(group)
    return None


def _is_relay_state_sync_commit(subject: str) -> bool:
    return subject.startswith("Sync task state:") or (
        subject.startswith("Ticket: ") and " \u2014 " in subject
    )


def _read_last_commit(path: Path) -> str | None:
    if not path.is_file():
        return None
    match = _STATE_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    for raw in match.group(1).splitlines():
        key, _, value = raw.partition(":")
        if key.strip() == "last_commit":
            value = value.strip()
            return value or None
    return None


def _write_digest_state(
    path: Path,
    *,
    last_commit: str,
    range_label: str,
    posted: str,
) -> None:
    text = path.read_text(encoding="utf-8")
    state = (
        f"### {_STATE_HEADING}\n\n"
        f"last_commit: {last_commit}\n"
        f"range: {range_label}\n"
        f"posted: {posted}\n"
    )
    match = _STATE_RE.search(text)
    if match:
        new_text = text[: match.start()] + state + text[match.end() :]
    else:
        spool_heading = re.search(
            rf"^##\s+{re.escape(spool.SPOOL_HEADING)}\s*$",
            text,
            re.MULTILINE,
        )
        if spool_heading:
            prefix = text[: spool_heading.start()].rstrip() + "\n\n"
            new_text = prefix + state + "\n" + text[spool_heading.start() :]
        else:
            new_text = text.rstrip() + "\n\n" + state
    atomic_write_text(path, new_text)


def _git_toplevel(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DigestGitError("`git` not found on PATH") from exc
    if result.returncode != 0:
        msg = (result.stderr + result.stdout).strip()
        if "not a git repository" in msg.lower():
            return None
        raise DigestGitError(f"`git rev-parse --show-toplevel` failed: {msg}")
    top = result.stdout.strip()
    return Path(top) if top else None


def _commit_exists(root: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DigestGitError("`git` not found on PATH") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise DigestGitError(f"`git {' '.join(args)}` failed: {detail}")
    return result.stdout
