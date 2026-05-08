"""Cleanup-orphan-markers Dream worker.

Find done tickets whose blackboard carries the processed Retro marker but
whose task directory was not deleted by the Retro PR. With --open-prs, open
a delete-only PR for each candidate. Without that flag, report candidates only.

The detection rules are deterministic: status frontmatter exact match on `done`,
`## Retro` section containing both `skill: retro/done-ticket` and
`status: processed`, exact slug match (no prefix matching), and no open PR
already touching the task directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from relay.config import Config, ConfigError, find_repo_root, load_config
from relay.slack import post
from relay.tasks import TaskNotFoundError, read_ticket, resolve_task


RETRO_SKILL_LINE = "skill: retro/done-ticket"
RETRO_STATUS_LINE = "status: processed"

ACTION_PR_OPENED = "pr-opened"
ACTION_SKIPPED_OPEN_PR = "skipped-open-pr"
ACTION_CANDIDATE_ONLY = "candidate-only"
ACTION_HUMAN_NEEDED = "human-needed"


@dataclass(frozen=True)
class OrphanCandidate:
    slug: str
    task_dir: Path
    blackboard: Path


@dataclass(frozen=True)
class CleanupAction:
    slug: str
    action: str
    detail: str
    pr_url: str | None = None


def find_orphan_candidates(repo_root: Path) -> list[OrphanCandidate]:
    """Done-ticket task dirs whose blackboard carries the processed Retro marker."""
    tasks_dir = repo_root / "tasks"
    if not tasks_dir.is_dir():
        return []
    candidates: list[OrphanCandidate] = []
    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        ticket = task_dir / "ticket.md"
        blackboard = task_dir / "blackboard.md"
        if not ticket.is_file() or not blackboard.is_file():
            continue
        if not _ticket_is_done(ticket):
            continue
        if not _blackboard_has_processed_marker(blackboard):
            continue
        candidates.append(
            OrphanCandidate(slug=task_dir.name, task_dir=task_dir, blackboard=blackboard)
        )
    return candidates


def _ticket_is_done(ticket: Path) -> bool:
    text = ticket.read_text()
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end < 0:
        return False
    front = text[3:end]
    for raw in front.splitlines():
        line = raw.strip()
        if line.startswith("status:") and line.split(":", 1)[1].strip() == "done":
            return True
    return False


_RETRO_SECTION_RE = re.compile(r"^## Retro\b.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)


def _blackboard_has_processed_marker(blackboard: Path) -> bool:
    text = blackboard.read_text()
    for match in _RETRO_SECTION_RE.finditer(text):
        section = match.group(0)
        if RETRO_SKILL_LINE in section and RETRO_STATUS_LINE in section:
            return True
    return False


def list_open_prs_touching(repo_root: Path, slug: str) -> list[int]:
    """Open PR numbers whose changed files include `relay-os/tasks/<slug>/...`."""
    result = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json", "number,files", "--limit", "200"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"gh pr list failed: {detail}")
    prs = json.loads(result.stdout or "[]")
    target_prefix = f"relay-os/tasks/{slug}/"
    matching: list[int] = []
    for pr in prs:
        files = pr.get("files") or []
        for f in files:
            path = f.get("path") if isinstance(f, dict) else None
            if path and path.startswith(target_prefix):
                matching.append(int(pr["number"]))
                break
    return matching


def open_cleanup_pr(repo_root: Path, slug: str, *, base_branch: str = "main") -> str:
    """Open a delete-only PR for the slug and return the PR URL.

    Operates inside a fresh worktree off origin/<base_branch> so the running
    repo's working tree is never touched. Deletion goes through
    `relay delete --exact`; this worker only adds the PR wrapper. Cleans the
    worktree on success or failure.
    """
    target_rel = f"relay-os/tasks/{slug}/"
    branch = f"dream/cleanup-orphan-{slug}"
    worktree = repo_root / ".dream-worktrees" / f"cleanup-orphan-{slug}"

    _git(repo_root, ["fetch", "origin", base_branch])

    if worktree.exists():
        _git(repo_root, ["worktree", "remove", "--force", str(worktree)], allow_fail=True)

    _git(
        repo_root,
        ["worktree", "add", "-B", branch, str(worktree), f"origin/{base_branch}"],
    )

    try:
        if not (worktree / "relay-os" / "tasks" / slug).is_dir():
            raise RuntimeError(
                f"task dir `{target_rel}` does not exist on origin/{base_branch}; "
                f"nothing to clean up"
            )
        result = subprocess.run(
            [sys.executable, "-m", "relay.cli", "delete", slug, "--exact"],
            cwd=worktree,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "no output"
            raise RuntimeError(f"`relay delete --exact {slug}` failed: {detail}")
        _git(worktree, ["add", "-A", "relay-os/tasks"])
        commit_msg = (
            f"Dream cleanup: delete orphan-marker task {slug}\n\n"
            "Source task carried the processed Retro marker "
            "(skill: retro/done-ticket / status: processed) but the Retro PR did "
            "not delete the task directory. Deletion uses `relay delete --exact`; "
            "git history is the audit trail."
        )
        _git(worktree, ["commit", "-m", commit_msg])
        _git(worktree, ["push", "-u", "origin", branch])
        body = (
            f"Dream cleanup: delete orphan-marker task `{slug}`.\n\n"
            f"The source task's blackboard already carries the processed Retro "
            f"marker (`skill: retro/done-ticket` / `status: processed`), but the "
            f"task directory was not deleted by the Retro PR. This PR completes "
            f"the cleanup by deleting only `{target_rel}` via "
            f"`relay delete --exact {slug}`.\n\n"
            f"Git history for the deleted files is the audit trail."
        )
        result = subprocess.run(
            [
                "gh", "pr", "create",
                "--title", f"Dream cleanup: delete orphan-marker task `{slug}`",
                "--body", body,
                "--base", base_branch,
                "--head", branch,
            ],
            cwd=worktree,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "no output"
            raise RuntimeError(f"gh pr create failed: {detail}")
        return result.stdout.strip().splitlines()[-1]
    finally:
        _git(repo_root, ["worktree", "remove", "--force", str(worktree)], allow_fail=True)


def _git(cwd: Path, args: list[str], *, allow_fail: bool = False) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=False, capture_output=True, text=True
    )
    if result.returncode != 0 and not allow_fail:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"`git {shlex.join(args)}` failed: {detail}")
    return result.stdout


def process_candidates(
    repo_root: Path,
    candidates: list[OrphanCandidate],
    *,
    open_prs: bool,
    base_branch: str = "main",
) -> list[CleanupAction]:
    actions: list[CleanupAction] = []
    for candidate in candidates:
        try:
            open_pr_numbers = list_open_prs_touching(repo_root, candidate.slug)
        except RuntimeError as exc:
            actions.append(
                CleanupAction(
                    slug=candidate.slug,
                    action=ACTION_HUMAN_NEEDED,
                    detail=f"could not check open PRs: {exc}",
                )
            )
            continue
        if open_pr_numbers:
            actions.append(
                CleanupAction(
                    slug=candidate.slug,
                    action=ACTION_SKIPPED_OPEN_PR,
                    detail=f"open PR(s) already touching the dir: #{', #'.join(str(n) for n in open_pr_numbers)}",
                )
            )
            continue
        if not open_prs:
            actions.append(
                CleanupAction(
                    slug=candidate.slug,
                    action=ACTION_CANDIDATE_ONLY,
                    detail="orphan marker present; pass --open-prs to open the deletion PR",
                )
            )
            continue
        try:
            url = open_cleanup_pr(repo_root, candidate.slug, base_branch=base_branch)
        except RuntimeError as exc:
            actions.append(
                CleanupAction(
                    slug=candidate.slug,
                    action=ACTION_HUMAN_NEEDED,
                    detail=f"could not open cleanup PR: {exc}",
                )
            )
            continue
        actions.append(
            CleanupAction(
                slug=candidate.slug,
                action=ACTION_PR_OPENED,
                detail="delete-only PR opened",
                pr_url=url,
            )
        )
    return actions


def render_blackboard_report(
    actions: list[CleanupAction], *, generated_at: str, opened_prs: bool
) -> str:
    lines = [
        "## Dream Worker: cleanup-orphan-markers",
        "",
        f"Generated: {generated_at}",
        f"Mode: {'open-prs' if opened_prs else 'report-only'}",
        "",
    ]
    if not actions:
        lines.append("Result: no orphan-marker done tickets found.")
        return "\n".join(lines) + "\n"

    counts = {
        ACTION_PR_OPENED: 0,
        ACTION_SKIPPED_OPEN_PR: 0,
        ACTION_CANDIDATE_ONLY: 0,
        ACTION_HUMAN_NEEDED: 0,
    }
    for a in actions:
        counts[a.action] = counts.get(a.action, 0) + 1

    lines.append(
        "Result: "
        f"{counts[ACTION_PR_OPENED]} pr-opened, "
        f"{counts[ACTION_SKIPPED_OPEN_PR]} skipped (open PR), "
        f"{counts[ACTION_CANDIDATE_ONLY]} candidate-only, "
        f"{counts[ACTION_HUMAN_NEEDED]} human-needed."
    )
    lines.append("")
    for a in actions:
        suffix = f" — {a.pr_url}" if a.pr_url else ""
        lines.append(f"- `{a.slug}` ({a.action}): {a.detail}{suffix}")
    return "\n".join(lines) + "\n"


def append_report(blackboard: Path, report: str) -> None:
    if not blackboard.parent.is_dir():
        raise RuntimeError(f"Blackboard parent does not exist: {blackboard.parent}")
    existing = blackboard.read_text() if blackboard.is_file() else ""
    if not existing or existing.endswith("\n\n"):
        separator = ""
    elif existing.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    blackboard.write_text(existing + separator + report)


def build_slack_summary(actions: list[CleanupAction], *, opened_prs: bool) -> str:
    if not actions:
        return "Dream cleanup-orphan-markers: no orphan-marker done tickets."
    pr_opened = sum(1 for a in actions if a.action == ACTION_PR_OPENED)
    skipped = sum(1 for a in actions if a.action == ACTION_SKIPPED_OPEN_PR)
    cand = sum(1 for a in actions if a.action == ACTION_CANDIDATE_ONLY)
    human = sum(1 for a in actions if a.action == ACTION_HUMAN_NEEDED)
    parts = []
    if pr_opened:
        parts.append(f"{pr_opened} PR(s) opened")
    if skipped:
        parts.append(f"{skipped} already-in-flight")
    if cand:
        parts.append(f"{cand} candidate(s) (report-only)")
    if human:
        parts.append(f"{human} human-needed")
    return "Dream cleanup-orphan-markers: " + "; ".join(parts) + "."


def post_slack_summary(cfg: Config, task_slug: str, summary: str) -> None:
    try:
        ref = resolve_task(cfg, task_slug)
    except TaskNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc
    ticket = read_ticket(ref)
    post(cfg, f"🧹 {summary}", task_path=ref.path, owner=ticket.owner or cfg.current_user)


def load_worker_config(cwd: Path | None) -> Config:
    if cwd is None:
        return load_config()
    return load_config(find_repo_root(cwd))


def _script_task_argv_from_env() -> list[str] | None:
    blackboard = os.environ.get("RELAY_TASK_BLACKBOARD")
    repo_root = os.environ.get("RELAY_REPO_ROOT")
    if not blackboard and not repo_root:
        return None
    argv = ["--open-prs"]
    if repo_root:
        argv.extend(["--cwd", repo_root])
    if blackboard:
        argv.extend(["--blackboard", blackboard])
    return argv


def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) == 1:
        argv = _script_task_argv_from_env()

    parser = argparse.ArgumentParser(description="Run the cleanup-orphan-markers Dream worker.")
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Repo root to scan. Defaults to the current directory.",
    )
    parser.add_argument(
        "--blackboard",
        type=Path,
        help="Append the worker report to this Dream run blackboard.",
    )
    parser.add_argument(
        "--open-prs",
        action="store_true",
        help="Open delete-only PRs for each candidate. Default is report-only.",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch the cleanup PRs target. Default: main.",
    )
    parser.add_argument(
        "--slack-task",
        help="Post the worker summary to Slack against this task slug.",
    )
    args = parser.parse_args(argv)

    try:
        cfg = load_worker_config(args.cwd)
        candidates = find_orphan_candidates(cfg.repo_root)
        actions = process_candidates(
            cfg.repo_root,
            candidates,
            open_prs=args.open_prs,
            base_branch=args.base_branch,
        )
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        report = render_blackboard_report(
            actions, generated_at=generated_at, opened_prs=args.open_prs
        )
        if args.blackboard:
            append_report(args.blackboard, report)
        else:
            sys.stdout.write(report)
        if args.slack_task:
            summary = build_slack_summary(actions, opened_prs=args.open_prs)
            post_slack_summary(cfg, args.slack_task, summary)
    except (ConfigError, RuntimeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
