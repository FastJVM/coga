"""Push a code ticket's branch and open (or ready) its PR.

The deterministic recipe behind the `bootstrap/open-pr` command ticket:
`coga open-pr <slug>` (a default alias for `coga launch bootstrap/open-pr
<slug>`) runs the sibling `run.py`, which resolves the target task and calls
`open_pr()` here. The ordinary agent-owned open-pr step runs that spelling.
Every operational refusal raises `OpenPrError`, which the seam renders as a
concise non-zero exit. The workflow's `requires: pr` completion gate is
separate: `coga bump` advances only after this recipe records the PR URL
under `## Dev`. Like any command-ticket recipe, it imports shared core infra
(`coga.autoclose` parsers, `coga.github_preflight`, `coga.taskfile`, and
`coga.git`'s sync primitives) freely.
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
from coga.git import (
    is_linked_worktree,
    sync_log,
    sync_paths,
    ticket_state_guard,
)
from coga.lifecycle import TERMINAL_STATUSES
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


def _git_checkout_root(path: str | Path) -> Path | None:
    """Return the resolved worktree root containing `path`, if it is in Git.

    `--show-toplevel` identifies a checkout rather than only its shared Git
    repository, so linked worktrees remain distinct while nested Coga roots and
    symlinked paths still compare equal to their containing checkout.
    """
    result = _run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"]
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def same_git_checkout(left: str | Path, right: str | Path) -> bool:
    """Return whether two paths are inside the same Git checkout."""
    left_root = _git_checkout_root(left)
    right_root = _git_checkout_root(right)
    return left_root is not None and left_root == right_root


def _single_checkout_publishable_paths(
    *,
    base_ref: str,
    checkout_root: Path,
    coga_root: Path,
) -> list[str]:
    """Return branch changes other than generated Coga task/audit state.

    A primary-checkout feature branch accumulates lifecycle commits from
    `launch` / `bump`, so a non-zero commit count does not prove that the
    implementation produced anything to review. Compare the branch side of the
    fork and exclude exactly the generated paths the freshness check treats as
    operational state: `coga/tasks/**` and `coga/log.md` (adjusted for a Coga OS
    rooted at the Git toplevel).
    """
    try:
        coga_prefix = coga_root.resolve().relative_to(checkout_root).as_posix()
    except ValueError as exc:
        raise OpenPrError(
            f"Configured Coga root {str(coga_root)!r} is not inside the recorded "
            f"checkout {str(checkout_root)!r}; refusing to publish."
        ) from exc

    changed = _git(
        ["diff", "--no-renames", "--name-only", "-z", f"{base_ref}...HEAD"],
        cwd=str(checkout_root),
    )
    if changed.returncode != 0:
        raise OpenPrError(
            "Could not inspect the feature branch's committed paths while "
            f"checking for publishable work: {changed.stderr.strip() or 'no output'}"
        )

    prefix = "" if coga_prefix == "." else f"{coga_prefix}/"
    tasks_prefix = f"{prefix}tasks/"
    log_path = f"{prefix}log.md"
    return [
        path
        for path in changed.stdout.split("\0")
        if path and path != log_path and not path.startswith(tasks_prefix)
    ]


def _remote_branch_oid(remote: str, branch: str, *, cwd: str) -> str | None:
    """Return the advertised remote branch OID, or None when it does not exist."""
    result = _git(
        ["ls-remote", "--heads", remote, f"refs/heads/{branch}"], cwd=cwd
    )
    if result.returncode != 0:
        hint = check_git_auth(remote).detail
        raise OpenPrError(
            f"`git ls-remote {remote} {branch}` failed: "
            f"{result.stderr.strip() or 'no output'}\n{hint}"
        )
    line = next((line for line in result.stdout.splitlines() if line.strip()), "")
    return line.split(maxsplit=1)[0] if line else None


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


def _sync_pr_record(
    cfg: Config,
    *,
    worktree: str,
    blackboard_path: Path,
    slug: str,
) -> None:
    """Land a single-checkout ticket's generated `pr:` line on both branches.

    Routes through the same `sync_paths` primitive the `requires: pr` bump uses,
    so the record reaches the control branch as well as the feature branch.
    Publishing only the feature branch leaves `coga/tasks/<slug>/ticket.md`
    divergent between the two tips, and the freshness check accepts an
    overlapping generated path only while both tips carry identical bytes — the
    next `coga open-pr` would then reject its own record as a stale branch.

    Sync failure is reported, not raised. By this point the PR is open and its
    URL is on the live ticket, so a failed push must not fail the command: the
    recorded artifact is the gate, and the following bump's own publishing sync
    lands the same state.

    Guarded like every other publisher of a specific ticket's state. The
    terminal-status check at the top of `open_pr` reads the *local* ticket; this
    reads the committed control copy at each landing attempt, which is the only
    place a concurrent close is visible. Without it the overlay would replace a
    ticket another checkout had already finished — writing a `pr:` line over a
    `done` copy — and the non-fast-forward retry would faithfully rebuild that
    overwrite on the refetched tip.
    """
    checkout_root = _git_checkout_root(worktree)
    if checkout_root is None:
        raise OpenPrError(
            f"Could not resolve the Git checkout containing {worktree!r} while "
            "committing the recorded PR URL."
        )
    try:
        blackboard_path.resolve().relative_to(checkout_root)
    except ValueError as exc:
        raise OpenPrError(
            f"Ticket {str(blackboard_path)!r} is not inside the recorded "
            f"checkout {str(checkout_root)!r}; refusing to commit the PR URL."
        ) from exc

    sync_paths(
        cfg,
        blackboard_path.parent,
        [blackboard_path],
        message=f"Ticket: {slug} — PR opened",
        publish_current_branch=True,
        guard=ticket_state_guard(cfg, blackboard_path),
    )


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


def open_pr(
    cfg: Config,
    *,
    slug: str,
    blackboard_path: Path,
    single_checkout: bool = False,
) -> str:
    """Push the feature branch and open (or ready) its PR; return the PR URL.

    Reads `branch:` / `worktree:` (and an optional `## PR` body) from the
    ticket's `## Dev` blackboard section, confirms the recorded checkout is on
    that branch, clean, ahead of the base branch, and has no material stale
    drift from `<remote>/<base>`, pushes, opens the PR (`gh pr create`, or `gh
    pr ready` for an existing draft, or reuses an already-open PR), and writes
    `pr: <url>` back under `## Dev`. When the recorded checkout also contains
    the live Coga ticket, the generated URL write is synced to the feature
    branch *and* the control branch so the checkout stays clean, the PR
    contains it, and both tips keep identical ticket bytes for the next
    freshness check; that layout must also contain a committed change outside
    generated task/log state. The caller sets `single_checkout` only after the
    CLI proves that live-ticket ownership from its launch metadata.

    Raises `OpenPrError` on any fail-loud condition — the caller must not
    advance the workflow step when that happens.
    """
    remote = cfg.git_remote
    base = cfg.git_control_branch

    ticket = Ticket.read(blackboard_path)
    if ticket.status in TERMINAL_STATUSES:
        raise OpenPrError(
            f"Cannot open a PR for {slug}: ticket status "
            f"{ticket.status!r} is terminal."
        )
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
            "open-pr pushes from the recorded checkout; record its path there "
            f"(see the dev/code context), or `coga block --task {slug}`."
        )
    if not Path(worktree).is_dir():
        raise OpenPrError(
            f"Recorded worktree {worktree!r} does not exist. If the recorded path "
            "has a trailing repository note, delimit the path with backticks "
            "(for example: worktree: `/path` (other repo)), or put the note on "
            "a separate line. If the worktree was torn down before the PR was "
            "opened, recreate it "
            f"(`git worktree add {worktree} {branch}`) or `coga block --task {slug}`."
        )

    already = parse_pr_url(blackboard)
    if single_checkout and (
        not same_git_checkout(cfg.repo_root, worktree)
        or is_linked_worktree(Path(worktree))
    ):
        raise OpenPrError(
            "The caller marked this as a single-checkout open-pr, but the "
            "recorded worktree is a distinct checkout. Refusing to commit the "
            "generated PR URL to the wrong ticket copy."
        )

    # --- confirm branch, cleanliness, commits ahead of base ------------------
    head = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree)
    if head.returncode != 0:
        raise OpenPrError(
            f"`git rev-parse` failed in {worktree!r}: {head.stderr.strip() or 'no output'}"
        )
    current_branch = head.stdout.strip()
    if current_branch != branch:
        raise OpenPrError(
            f"Recorded worktree {worktree!r} is on {current_branch!r}, not the "
            f"recorded branch {branch!r}. If the recorded branch has a trailing "
            "repository note, delimit the name with backticks "
            "(for example: branch: `name` (other repo)), or put the note on a "
            "separate line. Otherwise, check it out there before open-pr runs."
        )

    if single_checkout:
        # A supervised agent launch appends its audit line before the agent runs,
        # while the normal teardown sync happens only after the agent bumps and
        # exits. In the primary-checkout layout that generated write is in this
        # same feature checkout, so commit exactly the union-safe log before the
        # cleanliness gate. Any product or other Coga dirt still fails below.
        sync_log(cfg, message=f"Log: {slug}")

    dirty = _git(["status", "--porcelain"], cwd=worktree)
    if dirty.returncode != 0:
        raise OpenPrError(
            f"`git status` failed in {worktree!r}: {dirty.stderr.strip() or 'no output'}"
        )
    if dirty.stdout.strip():
        raise OpenPrError(
            f"Recorded worktree {worktree!r} has uncommitted changes. The "
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
    if single_checkout:
        checkout_root = _git_checkout_root(worktree)
        if checkout_root is None:
            raise OpenPrError(
                f"Could not resolve the Git checkout containing {worktree!r} "
                "while checking branch freshness."
            )
        try:
            blackboard_path.resolve().relative_to(checkout_root)
        except ValueError as exc:
            raise OpenPrError(
                f"Ticket {str(blackboard_path)!r} is not inside the recorded "
                f"checkout {str(checkout_root)!r}; refusing to publish."
            ) from exc
        if not _single_checkout_publishable_paths(
            base_ref=base_ref,
            checkout_root=checkout_root,
            coga_root=cfg.repo_root,
        ):
            raise OpenPrError(
                f"Branch {branch!r} has no committed changes outside generated "
                "Coga task/log state — there is no implementation to open a PR "
                "for. Build and commit the requested change before relaunching."
            )

    freshness = check_branch_contains_control(
        remote,
        base,
        cwd=worktree,
        coga_root=cfg.repo_root,
        allow_identical_coga_state_overlaps=single_checkout,
    )
    if not freshness.ok:
        raise OpenPrError(
            f"Branch {branch!r} is not safe to publish. {freshness.detail} "
            f"Reconcile it and relaunch, or `coga block --task {slug}`."
        )
    if freshness.value == "state-only-drift":
        print(f"[open-pr] {freshness.detail}")

    # `gh` is optional at init, so the PR step owns the point-of-need check.
    # Run it before pushing: a missing or logged-out CLI should produce the
    # actionable preflight hint without leaving a remote branch behind first.
    remote_url = _git(["remote", "get-url", remote], cwd=worktree)
    host = (
        _remote_host(remote_url.stdout.strip())
        if remote_url.returncode == 0
        else None
    )
    gh_auth = check_gh_auth(host)
    if not gh_auth.ok:
        raise OpenPrError(gh_auth.detail)

    # --- push ----------------------------------------------------------------
    # A previous open-pr attempt may have pushed before `gh` failed. If the
    # operator then rebases as instructed, an ordinary retry is non-fast-forward.
    # Use an explicit lease against the OID observed immediately before push:
    # rewritten local history is publishable, but concurrent remote updates are
    # still rejected instead of overwritten.
    remote_oid = _remote_branch_oid(remote, branch, cwd=worktree)
    push_args = ["push", "-u"]
    if remote_oid:
        push_args.append(
            f"--force-with-lease=refs/heads/{branch}:{remote_oid}"
        )
    push_args.extend([remote, branch])
    push = _git(push_args, cwd=worktree)
    if push.returncode != 0:
        hint = check_git_auth(remote).detail
        rendered = " ".join(push_args)
        raise OpenPrError(
            f"`git {rendered}` failed: "
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
        if single_checkout:
            _sync_pr_record(
                cfg,
                worktree=worktree,
                blackboard_path=blackboard_path,
                slug=slug,
            )

    if already and already != url:
        # Not an error — record it so a stale link replacement is visible in logs.
        print(f"[open-pr] note: replaced a stale pr: line ({already}) with {url}")
    return url
