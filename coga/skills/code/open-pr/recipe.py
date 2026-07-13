"""Push a code ticket's branch and open (or ready) its PR — logic for code/open-pr.

This recipe lives **beside** the skill's `run.py` in the skill directory, so the
skill is self-contained: the logic is in the editable skill, not trapped in the
installed `coga` package. Python runs a `.py` script step with the script's own
directory on `sys.path[0]`, so `run.py` imports this as a plain sibling module
(`from recipe import ...`); the unit test loads it the same way. It still imports
shared infrastructure (`coga.autoclose` parsers, `coga.compose`, `coga.taskfile`,
`coga.ticket`, `coga.config`, `coga.github_preflight`) from the package — those
are shared utilities, not open-pr-specific logic, so they stay in core.

The recipe is deliberately deterministic — that is the whole point of making
open-pr a script step rather than an agent checklist. The launch supervisor runs
it and advances the workflow **only on exit 0**; every fail-loud condition here
raises `OpenPrError`, which the wrapper turns into a non-zero exit, so the step
cannot advance without a real PR. In particular a branch with no commits ahead
of the base (the cross-worktree divergence incident) fails loud instead of
silently marching the workflow forward.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from coga.autoclose import parse_branch_name, parse_pr_url, parse_worktree_path
from coga.compose import _extract_section
from coga.config import Config
from coga.github_preflight import (
    _remote_host,
    check_branch_contains_control,
    check_git_auth,
    check_git_remote,
    check_gh_auth,
)
from coga.taskfile import read_blackboard, replace_blackboard, split_body
from coga.ticket import Ticket


class OpenPrError(Exception):
    """A fail-loud condition in the open-pr recipe (missing state, nothing to
    PR, or a git/gh failure). The wrapper maps it to a non-zero exit so the
    workflow step does not advance."""


def _run(args: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def _git(args: list[str], *, cwd: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", "-C", cwd, *args])


_PR_LINE_RE = re.compile(r"^(?P<prefix>\s*(?:-\s*)?)pr:.*$", re.MULTILINE)
_DEV_HEADER_RE = re.compile(r"^##\s+Dev\s*$", re.MULTILINE)
_DEV_SECTION_RE = re.compile(r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL)


def set_dev_pr(blackboard_text: str, url: str) -> str:
    """Return `blackboard_text` with the `## Dev` `pr:` line set to `url`.

    Updates the line in place when present (preserving any `- ` / indentation),
    inserts one right after the `## Dev` header when the section exists without a
    `pr:` line, and appends a fresh `## Dev` section as a last resort. Mirrors the
    `dev/code` convention: the blackboard records *current* state, so overwrite
    rather than append a second `pr:` line.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if section:
        body = section.group(1)
        if _PR_LINE_RE.search(body):
            new_body = _PR_LINE_RE.sub(
                lambda m: f"{m.group('prefix')}pr: {url}", body, count=1
            )
        else:
            new_body = f"pr: {url}\n{body}" if body else f"pr: {url}\n"
        return blackboard_text[: section.start(1)] + new_body + blackboard_text[section.end(1):]

    header = _DEV_HEADER_RE.search(blackboard_text)
    if header:
        return blackboard_text[: header.end()] + f"\npr: {url}" + blackboard_text[header.end():]

    sep = "" if not blackboard_text or blackboard_text.endswith("\n") else "\n"
    return f"{blackboard_text}{sep}\n## Dev\npr: {url}\n"


def _pr_body(ticket: Ticket, blackboard: str, above: str, slug: str) -> str:
    """Assemble the PR body.

    Source priority (per the settled ticket decision — fall back to
    `## Description`, never block the pipeline for a missing summary):
      1. a `## PR` section the agent authored (blackboard first, then body),
      2. else the ticket's `## Description`,
      3. else the ticket title.
    Always ends with a `Closes ticket:` line so the link is machine-findable.
    """
    body = _extract_section(blackboard, "PR").strip() or _extract_section(above, "PR").strip()
    if not body:
        body = _extract_section(above, "Description").strip()
    if not body:
        body = ticket.title or slug
    return f"{body}\n\nCloses ticket: `{slug}`\n"


def _open_pr_url(branch: str, cwd: str) -> dict | None:
    """Return the OPEN PR for `branch` as a dict, or None.

    `gh pr view <branch>` errors when no PR exists, which we treat as "none"
    (the common first-open path) rather than a hard failure. A non-OPEN PR
    (merged/closed) is also treated as none so we open a fresh one.
    """
    result = _run(
        ["gh", "pr", "view", branch, "--json", "url,state,isDraft,number"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if str(data.get("state", "")).upper() != "OPEN":
        return None
    return data


def open_pr(cfg: Config, *, slug: str, blackboard_path: Path) -> str:
    """Push the feature branch and open (or ready) its PR; return the PR URL.

    Reads `branch:` / `worktree:` (and an optional `## PR` body) from the
    ticket's `## Dev` blackboard section, confirms the worktree is on that
    branch, clean, ahead of the base branch, and has no material stale drift
    from `<remote>/<base>`, pushes, opens the PR (`gh pr create`, or `gh pr ready`
    for an existing draft, or reuses an already-open PR), and writes
    `pr: <url>` back under `## Dev`.

    Raises `OpenPrError` on any fail-loud condition — the caller must not
    advance the workflow step when that happens.
    """
    remote = cfg.git_remote
    base = cfg.git_control_branch

    ticket = Ticket.read(blackboard_path)
    above, blackboard = split_body(ticket.body)
    blackboard = blackboard or ""

    branch = parse_branch_name(blackboard)
    if not branch or branch.startswith("("):
        raise OpenPrError(
            "No usable `branch:` recorded under `## Dev` on the blackboard. The "
            "implement step must create the feature branch and record it before "
            "open-pr can run. Fix the `## Dev` section, or `coga block "
            f'--task {slug} --reason "..."` if the branch was lost.'
        )

    worktree = parse_worktree_path(blackboard)
    if not worktree:
        raise OpenPrError(
            "No usable `worktree:` recorded under `## Dev` on the blackboard. "
            "open-pr pushes from the feature worktree; record its path there "
            f"(see the dev/code context), or `coga block --task {slug}`."
        )
    if not Path(worktree).is_dir():
        raise OpenPrError(
            f"Feature worktree {worktree!r} does not exist. If it was torn down "
            f"before the PR was opened, recreate it "
            f"(`git worktree add {worktree} {branch}`) or `coga block --task {slug}`."
        )

    already = parse_pr_url(blackboard)

    # --- confirm branch, cleanliness, commits ahead of base ------------------
    head = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree)
    if head.returncode != 0:
        raise OpenPrError(
            f"`git rev-parse` failed in {worktree!r}: {head.stderr.strip() or 'no output'}"
        )
    current_branch = head.stdout.strip()
    if current_branch != branch:
        raise OpenPrError(
            f"Feature worktree {worktree!r} is on {current_branch!r}, not the "
            f"recorded branch {branch!r}. Check it out there before open-pr runs."
        )

    dirty = _git(["status", "--porcelain"], cwd=worktree)
    if dirty.returncode != 0:
        raise OpenPrError(
            f"`git status` failed in {worktree!r}: {dirty.stderr.strip() or 'no output'}"
        )
    if dirty.stdout.strip():
        raise OpenPrError(
            f"Feature worktree {worktree!r} has uncommitted changes. The "
            "implement/peer-review steps must commit before open-pr. Commit or "
            "stash them, then relaunch."
        )

    # Commits ahead of the base branch. Resolve the base as the local ref first
    # (shared across worktrees), then the remote-tracking ref. Zero commits ahead
    # is the incident's mis-branch case — fail loud instead of opening an empty PR.
    base_ref = base
    if _git(["rev-parse", "--verify", "--quiet", base], cwd=worktree).returncode != 0:
        remote_base = f"{remote}/{base}"
        if _git(["rev-parse", "--verify", "--quiet", remote_base], cwd=worktree).returncode == 0:
            base_ref = remote_base
        else:
            raise OpenPrError(
                f"Base branch {base!r} not found in {worktree!r} (neither {base!r} "
                f"nor {remote}/{base}). Fetch it, or set [git].control_branch."
            )
    ahead = _git(["rev-list", "--count", f"{base_ref}..HEAD"], cwd=worktree)
    if ahead.returncode != 0:
        raise OpenPrError(
            f"`git rev-list` failed in {worktree!r}: {ahead.stderr.strip() or 'no output'}"
        )
    if ahead.stdout.strip() == "0":
        raise OpenPrError(
            f"Branch {branch!r} has no commits ahead of {base_ref} — there is "
            "nothing to open a PR for. This is exactly the failure open-pr must "
            "not paper over: implement/peer-review produced no committed change. "
            f"Build the change, or `coga block --task {slug}`."
        )

    # --- refuse material stale-branch drift ---------------------------------
    # Task-step and audit-log sync advances the control branch between agent
    # steps. The shared preflight permits only non-overlapping generated state;
    # any source/docs/config or overlapping drift remains a hard failure.
    freshness = check_branch_contains_control(
        remote,
        base,
        cwd=worktree,
        coga_root=cfg.repo_root,
    )
    if not freshness.ok:
        raise OpenPrError(
            f"Branch {branch!r} is not safe to publish. {freshness.detail} "
            f"Reconcile it and relaunch, or `coga block --task {slug}`."
        )
    if freshness.value == "state-only-drift":
        print(f"[open-pr] {freshness.detail}")

    # --- push ----------------------------------------------------------------
    push = _git(["push", "-u", remote, branch], cwd=worktree)
    if push.returncode != 0:
        hint = check_git_auth(remote).detail
        raise OpenPrError(
            f"`git push -u {remote} {branch}` failed: "
            f"{push.stderr.strip() or 'no output'}\n{hint}"
        )

    # --- open or ready the PR ------------------------------------------------
    title = ticket.title or slug
    body = _pr_body(ticket, blackboard, above, slug)

    existing = _open_pr_url(branch, worktree)
    if existing is not None:
        url = existing["url"]
        if existing.get("isDraft"):
            ready = _run(["gh", "pr", "ready", url], cwd=worktree)
            if ready.returncode != 0:
                raise OpenPrError(
                    f"`gh pr ready {url}` failed: {ready.stderr.strip() or 'no output'}"
                )
    else:
        create = _run(
            [
                "gh", "pr", "create",
                "--base", base,
                "--head", branch,
                "--title", title,
                "--body", body,
            ],
            cwd=worktree,
        )
        if create.returncode != 0:
            stderr = create.stderr.strip()
            hint = ""
            # Attach the github_preflight setup hint only when it looks like auth.
            if "auth" in stderr.lower() or "logged" in stderr.lower():
                remote_url = check_git_remote(remote).value
                hint = "\n" + check_gh_auth(_remote_host(remote_url)).detail
            raise OpenPrError(f"`gh pr create` failed: {stderr or 'no output'}{hint}")
        url = create.stdout.strip().splitlines()[-1].strip() if create.stdout.strip() else ""
        if not url:
            raise OpenPrError("`gh pr create` succeeded but returned no PR URL to record.")

    # --- record pr: back under ## Dev ---------------------------------------
    # RE-READ the live blackboard region: the launcher advances the step right
    # after we return by rendering the ticket, so only a byte-spliced blackboard
    # write (replace_blackboard) is safe — it leaves frontmatter + body untouched.
    current_blackboard = read_blackboard(blackboard_path)
    if parse_pr_url(current_blackboard) != url:
        replace_blackboard(blackboard_path, set_dev_pr(current_blackboard, url))

    if already and already != url:
        # Not an error — record it so a stale link replacement is visible in logs.
        print(f"[open-pr] note: replaced a stale pr: line ({already}) with {url}")
    return url
