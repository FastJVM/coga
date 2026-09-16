"""Sweep stale git branches as a scheduled safety net behind retire-time deletion.

`coga retire` deletes a ticket's branch as soon as the ticket finishes (see
`branchcleanup.py`), but that cleanup is best-effort: `git`/`gh` failures are
swallowed there, and a branch also leaks when its ticket is deleted without
going through retire, or a session dies before retire runs. `sweep_branches`
is the net behind that — it walks every local and `origin` branch directly
(no ticket lookup) and deletes the ones GitHub confirms have already landed.

The merge signal differs from retire's: retire trusts a single ticket's
recorded `pr:` link (`autoclose.pr_state`, URL-keyed). A swept branch has no
ticket to point at a PR, so the check here is by **head branch name**
(`gh pr list --head <branch> --json number,headRefOid`), and it requires a
merged PR for that head **and no open PR** for it. A merged PR vouches for a
local ref only when the ref carries nothing beyond what landed: every commit
on the ref that neither the merged head nor the control branch contains must
touch only generated Coga state (`tasks/**`, `log.md`) — see
`merged_pr_verdict`. A branch that once merged a PR and was later reused for
real work therefore survives, while the two shapes Coga itself produces are
released: a ref that walked past the merged head through state-sync commits
(this repo squash-merges, so ancestry into control never says "landed" for
those), and a ref that *lags* the merged head because the last commit was
pushed from another checkout. A remote ref is authorized only at the exact
merged tip; its objects are usually not local.

Live tickets are consulted defensively before any gh lookup: a branch that any
non-terminal ticket names anywhere in its task files is skipped outright, so a
ticket still mid-workflow never loses its branch even if its PR already
merged. The match is deliberately broad — a mere mention pins — because the
alternative (trusting only a `## Dev` `branch:` line) missed a draft that
named its branch three times in prose and attachments but had no `## Dev`
section, and a false positive here only defers a delete by a week. Recurring
period tasks are the one exception: their blackboards are generated reports
that name branches (this sweep's own, autoclose's retire follow-ups), so they
pin only a recorded `## Dev` `branch:`.

Before enumerating branches, the sweep prunes registrations for worktrees whose
directories are gone. A merged branch that remains checked out in a live
worktree is preserved deliberately and reported as worktree-pinned instead of
falling through to a failed `git branch -d`/`-D`.

Reuses `branchcleanup.py`'s `delete_remote_branch` / `delete_local_branch`
for the actual git plumbing (ancestry check, `-d` then logged `-D` fallback,
never force without a merged PR) — only the merge-signal lookup differs, so
those two functions were exported (dropped their leading underscore) rather
than duplicated.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from coga.autoclose import GhError, parse_branch_name, prs_for_head
from coga.blackboard import append_blackboard_report
from coga.branchcleanup import (
    BranchCleanupResult,
    delete_local_branch,
    delete_remote_branch,
    local_branch_landed,
)
from coga.config import Config
from coga import git
from coga.github_preflight import coga_root_prefix, is_coga_state_path
from coga.lifecycle import TERMINAL_STATUSES
from coga.task_env import blackboard_from_env
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import list_tasks, read_ticket
from coga.ticket import TicketError

SWEEP_REPORT_HEADING = "## Branch Sweep"


@dataclass
class BranchSweepResult:
    """What one `sweep_branches` run did, for reporting and tests."""

    local_deleted: list[str] = field(default_factory=list)
    remote_deleted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    worktree_pinned: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    gh_unavailable: str | None = None
    remote_unavailable: str | None = None
    worktree_unavailable: str | None = None
    state_root_unavailable: str | None = None

    @property
    def failure(self) -> str | None:
        """First failure explaining a skipped or partial sweep, if any."""
        return (
            self.remote_unavailable
            or self.worktree_unavailable
            or self.state_root_unavailable
            or self.gh_unavailable
        )


@dataclass(frozen=True)
class MergedPrVerdict:
    """Whether a merged PR authorizes deleting one local ref, and why.

    `reason` is written to the sweep's notes when a merged PR exists but did
    not authorize the delete, so the run record says what kept the branch —
    "PR #779 merged at db19491d31, but the ref carries commits touching
    src/coga/commands/launch.py" is the line a human acts on.
    """

    landed: bool
    reason: str


def sweep_branches(
    cfg: Config,
    root: Path,
    *,
    echo: Callable[[str], None] = print,
    result: BranchSweepResult | None = None,
) -> BranchSweepResult:
    """Delete local/`origin` branches whose PR has merged, skipping live ones.

    `root` is the git working-tree root. Prunes registrations for missing
    worktrees first. Never touches `cfg.git_control_branch`, the currently
    checked-out branch, a branch recorded on a non-terminal ticket, or a merged
    branch still checked out in a live worktree. If worktree state or `gh` is
    unavailable, the rest of the sweep is skipped and reported rather than
    deleting with incomplete safety information.

    `result`, when given, is used as the accumulator and returned — the same
    idiom `sweep_merged` offers, so a caller holding the object can read what
    the sweep did without a second enumeration of local and remote refs.
    """
    if result is None:
        result = BranchSweepResult()
    worktree_branches = _worktree_branches(root, result, echo)
    if result.worktree_unavailable is not None:
        return result
    coga_prefix, prefix_error = coga_root_prefix(cfg.repo_root)
    if coga_prefix is None:
        # Without the prefix nothing can tell generated state from source, so
        # the widened merged-PR gate has no safe answer; fail the sweep loudly
        # like the worktree probe does rather than fall back to a looser rule.
        result.state_root_unavailable = prefix_error
        _note(
            result,
            echo,
            "Branch sweep: could not locate the Coga OS root in git — sweep "
            f"skipped: {prefix_error}",
        )
        return result

    current = _current_branch(root)
    local = _local_branches(root)
    remote = _remote_branches(cfg, root, result, echo)
    names = local.keys() | remote.keys()
    live_branches = _live_ticket_branches(cfg, set(names))
    landed_refs = [
        ref
        for ref in (cfg.git_control_branch, f"{cfg.git_remote}/{cfg.git_control_branch}")
        if _object_present(root, ref)
    ]

    for branch in sorted(names):
        if branch == cfg.git_control_branch:
            continue
        if branch == current:
            _note(result, echo, f"Branch sweep: {branch!r} is the checked-out branch — left in place.")
            continue
        if branch in live_branches:
            _note(result, echo, f"Branch sweep: {branch!r} is recorded on a live ticket — left in place.")
            continue

        if result.gh_unavailable is not None:
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: {branch!r} left in place (gh unavailable).")
            continue

        local_tip = local.get(branch)
        remote_tip = remote.get(branch)

        try:
            merged = _merged_prs(branch)
            # Checked second so a branch with no PR at all costs one gh call.
            open_pr = bool(merged) and bool(prs_for_head(branch, "open"))
        except GhError as exc:
            result.gh_unavailable = str(exc)
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: gh unavailable ({exc}) — no gated deletes this run.")
            continue

        # A remote ref is released only at the exact merged tip; the widened
        # rule is for the local ref, whose extra commits can be inspected.
        remote_merged = (
            not open_pr and any(head == remote_tip for _number, head in merged)
        )
        local_verdict: MergedPrVerdict | None = None
        if local_tip is not None and merged:
            local_verdict = (
                MergedPrVerdict(False, "has an open PR")
                if open_pr
                else merged_pr_verdict(
                    root,
                    local_tip,
                    merged,
                    landed_refs=landed_refs,
                    remote=cfg.git_remote,
                    coga_prefix=coga_prefix,
                )
            )
        local_merged = local_verdict is not None and local_verdict.landed

        local_landed = (
            local_tip is not None
            and local_branch_landed(root, branch, cfg.git_control_branch)
        )
        if branch in worktree_branches and (
            remote_merged
            or local_merged
            or local_landed
        ):
            result.worktree_pinned.append(branch)
            _note(
                result,
                echo,
                f"Branch sweep: {branch!r} has a landed ref but is checked out "
                f"in worktree {worktree_branches[branch]!r} — left in place.",
            )
            continue

        # The cleanup helpers note into the sweep's own record, so each delete
        # and refusal lands in the run report in the order it happened.
        cleanup = BranchCleanupResult(branch=branch, notes=result.notes)
        if branch in local:
            if local_verdict is not None and not local_merged and not local_landed:
                # `delete_local_branch` says "no merged PR vouching for it"
                # below; when a PR exists and still did not authorize, the
                # verdict's reason is the actionable part of the run record.
                _note(result, echo, f"Branch sweep: {branch!r} {local_verdict.reason}.")
            delete_local_branch(
                root,
                branch,
                local_merged,
                echo,
                cleanup,
                landed_ref=cfg.git_control_branch,
                expected_tip=local_tip,
            )

        # During rebase/bisect Git can report a worktree as detached while
        # still reserving its original branch. Let Git's own deletion gate
        # catch that hidden state before touching the remote ref.
        if cleanup.local_worktree_path is not None:
            result.worktree_pinned.append(branch)
            _note(
                result,
                echo,
                f"Branch sweep: {branch!r} has a landed ref but is held by "
                f"worktree {cleanup.local_worktree_path!r} — both refs left in place.",
            )
            continue

        # Do not delete the remote half of a branch whose local half could not
        # be removed. Besides making partial cleanup conservative, this is the
        # fallback safety gate for worktree operation states Git does not expose
        # as a branch in porcelain output.
        if branch in remote and (branch not in local or cleanup.local_deleted):
            delete_remote_branch(
                cfg, root, branch, remote_merged, echo, cleanup, expected_tip=remote_tip
            )

        if cleanup.local_deleted:
            result.local_deleted.append(branch)
        if cleanup.remote_deleted:
            result.remote_deleted.append(branch)
        if not cleanup.local_deleted and not cleanup.remote_deleted:
            result.skipped.append(branch)

    return result


def _merged_prs(branch: str) -> list[tuple[str, str]]:
    """`(number, head SHA)` of every merged PR whose head branch is `branch`.

    Raises `GhError` if `gh` is missing, unauthed, or errors.
    """
    return [
        (str(item.get("number", "")), str(item["headRefOid"]))
        for item in prs_for_head(branch, "merged")
        if item.get("headRefOid")
    ]


def merged_pr_verdict(
    root: Path,
    tip: str,
    merged: list[tuple[str, str]],
    *,
    landed_refs: list[str],
    remote: str,
    coga_prefix: str,
) -> MergedPrVerdict:
    """Decide whether one of the `merged` PRs vouches for the local ref at `tip`.

    A merged PR authorizes the delete when the ref carries nothing the PR did
    not land: every commit in `git rev-list <tip> ^<merged head> ^<landed>...`
    touches only generated Coga state (`is_coga_state_path`). `landed_refs`
    are the control refs that exist locally — the control branch and its
    remote-tracking ref — because a branch that merged the remote-tracking
    control ref after its PR landed carries control's own later source
    commits, which a lagging local control branch would otherwise report as
    the ref's unmerged work. That one rule covers the exact merged tip
    (nothing to list), a local ref that lags the merged head because the last
    commit was pushed from another checkout (nothing to list either), and a
    ref that walked past the merged head through Coga's own state-sync
    commits, including its clean `Merge <control> state into <branch>` merges —
    `git diff-tree --cc` lists a merge commit's paths only where the result
    differs from every parent, so an evil merge that resolved a source file
    still counts as work. Real unmerged source commits fail the rule and keep
    the branch, with the offending paths in the verdict.

    The merged head is only reachable locally when this checkout fetched it;
    otherwise it is fetched from `refs/pull/<number>/head` without writing a
    ref (`--no-write-fetch-head`), so the objects exist for the comparison and
    nothing else changes.
    """
    for number, head in merged:
        if head == tip:
            return MergedPrVerdict(True, f"PR #{number} merged at this exact tip")
    reason = ""
    for number, head in merged:
        refused = f"has merged PR #{number} at {head[:12]}, but"
        if not _object_present(root, head) and not _fetch_pr_head(
            root, remote, number, head
        ):
            reason = f"{refused} that head could not be fetched from {remote} to compare against"
            continue
        beyond = _git(
            root, "rev-list", tip, f"^{head}", *(f"^{ref}" for ref in landed_refs)
        )
        if beyond.returncode != 0:
            reason = (
                f"{refused} its history could not be compared: "
                f"{(beyond.stderr + beyond.stdout).strip()}"
            )
            continue
        commits = [line for line in beyond.stdout.splitlines() if line]
        offending = _non_state_paths(root, commits, coga_prefix=coga_prefix)
        if offending is None:
            reason = f"{refused} the commits beyond it could not be inspected"
            continue
        if not offending:
            beyond_note = (
                f"; the {len(commits)} later commit(s) on this ref touch only "
                "Coga task/log state"
                if commits
                else "; the ref is contained in the merged head"
            )
            return MergedPrVerdict(True, f"PR #{number} merged{beyond_note}")
        shown = ", ".join(sorted(offending)[:3])
        more = f" (+{len(offending) - 3} more)" if len(offending) > 3 else ""
        reason = f"{refused} the ref carries commits touching {shown}{more} — left in place"
    return MergedPrVerdict(False, reason)


def _non_state_paths(
    root: Path, commits: list[str], *, coga_prefix: str
) -> set[str] | None:
    """Paths outside generated Coga state that `commits` touch, or None on error.

    One `git diff-tree --stdin --cc` call over the whole list: non-merge
    commits list their ordinary diff, merge commits only the paths whose result
    differs from every parent. `--root` keeps a root commit from being read as
    an empty diff.
    """
    if not commits:
        return set()
    proc = _git(
        root,
        "diff-tree",
        "--stdin",
        "--cc",
        "-r",
        "--root",
        "--name-only",
        "--no-commit-id",
        input="\n".join(commits) + "\n",
    )
    if proc.returncode != 0:
        return None
    return {
        line
        for line in proc.stdout.splitlines()
        if line and not is_coga_state_path(line, coga_prefix=coga_prefix)
    }


def _fetch_pr_head(root: Path, remote: str, number: str, head: str) -> bool:
    """Fetch a merged PR's head objects without writing any ref.

    GitHub keeps `refs/pull/<n>/head` after the branch is deleted, so the
    comparison can run even when retire already removed the remote branch.
    True iff `head` is a local object afterwards.
    """
    if not number.isdigit():
        return False
    proc = _git(
        root,
        "fetch",
        "--quiet",
        "--no-tags",
        "--no-write-fetch-head",
        remote,
        f"refs/pull/{number}/head",
    )
    return proc.returncode == 0 and _object_present(root, head)


def _object_present(root: Path, oid: str) -> bool:
    return bool(oid) and _git(root, "cat-file", "-e", f"{oid}^{{commit}}").returncode == 0


def run_branch_sweep_recipe(
    cfg: Config, argv: list[str], *, result: BranchSweepResult | None = None
) -> int:
    """Run the recurring branch-sweep job.

    `result` is the optional out-parameter described on `run_recipe`: the
    `BranchSweepResult` this wrapper already computes is handed back through it
    with `.local_deleted` / `.remote_deleted` populated, so a caller that wants
    to name the deleted branches does not have to snapshot `git ls-remote`
    either side of the run.
    """
    if argv:
        sys.stderr.write(
            f"branch-sweep: unexpected arguments: {' '.join(repr(arg) for arg in argv)}\n"
        )
        return 2
    root = git._toplevel(cfg.repo_root)
    if root is None:
        sys.stderr.write(f"[branch-sweep] {cfg.repo_root} is not inside a git repo\n")
        return 2
    if result is None:
        result = BranchSweepResult()
    # Not rebound from the return value: `sweep_branches` hands back this same
    # object, and reading the caller's own reference keeps the out-parameter
    # contract true even if that ever stops being so.
    sweep_branches(cfg, root, echo=print, result=result)
    # The report is the run's only durable record — the period task's
    # blackboard is what the recurring sweep's autofix analyst reads, and a
    # console-only sweep left the 2026-09-08 period with an empty one. Written
    # before the exit code is decided so a failed sweep is recorded too.
    report = render_sweep_report(
        result,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        task_slug=os.environ.get("COGA_TASK_SLUG"),
    )
    blackboard = blackboard_from_env(cfg.repo_root)
    if blackboard:
        append_blackboard_report(cfg, blackboard, report)
    else:
        sys.stdout.write(report)
    if result.failure:
        sys.stderr.write(f"[branch-sweep] {result.failure}\n")
        return 2
    if result.worktree_pinned:
        sys.stdout.write(
            "[branch-sweep] skipped-worktree-pinned: "
            f"{', '.join(result.worktree_pinned)}\n"
        )
    if not result.local_deleted and not result.remote_deleted:
        sys.stdout.write("[branch-sweep] no branches deleted.\n")
    return 0


def render_sweep_report(
    result: BranchSweepResult,
    *,
    generated_at: str,
    task_slug: str | None,
) -> str:
    """Render one run's outcomes and every per-branch decision as a section."""
    lines = [SWEEP_REPORT_HEADING, "", f"Generated: {generated_at}"]
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.append("")
    if result.failure:
        status = (
            "the sweep stopped early"
            if result.worktree_unavailable or result.state_root_unavailable
            else "partial sweep"
        )
        lines.append(f"Result: {status} — {result.failure}")
    count_label = "Counts" if result.failure else "Result"
    lines.append(
        f"{count_label}: {len(result.local_deleted)} local and "
        f"{len(result.remote_deleted)} remote branch(es) deleted, "
        f"{len(result.worktree_pinned)} skipped-worktree-pinned, "
        f"{len(result.skipped)} skipped."
    )
    for label, names in (
        ("deleted local", result.local_deleted),
        ("deleted remote", result.remote_deleted),
        ("skipped-worktree-pinned", result.worktree_pinned),
        ("skipped", result.skipped),
    ):
        if names:
            lines.append(f"- {label}: {', '.join(names)}")
    if result.notes:
        lines.extend(["", "### Decisions", ""])
        lines.extend(f"- {note}" for note in result.notes)
    return "\n".join(lines) + "\n"


# A mention must be the whole branch name: `fix` in prose pins a branch named
# `fix`, while `prefix`, `fixes`, `old-fix`, and the longer name `fix/one` do
# not. A `.` or `/` is a delimiter only when no name character follows it, so
# a sentence-final "on fix." and `origin/fix` still count and `v1.2` does not
# pin `v1`.
_MENTION_START = r"(?<![\w-])(?<!\w\.)"
_MENTION_END = r"(?![\w-])(?![./]\w)"

# Period tasks under `tasks/recurring/` are machine-generated and their
# blackboards accumulate reports that name branches — autoclose's retire
# follow-ups, and this sweep's own record when a failed run leaves its period
# `in_progress`. Scanning those would let one failed sweep pin every branch
# it skipped, so a period task protects only a `## Dev` `branch:` it records.
_PERIOD_TASK_PREFIX = "recurring/"


def _live_ticket_branches(cfg: Config, candidates: set[str]) -> set[str]:
    """The `candidates` any non-terminal ticket names anywhere in its files.

    Every file of an ordinary task is read — the ticket body above and below
    the fence and, for a directory-form task, each attachment — so a draft
    that names its branch in prose or in a handoff manifest but has no
    `## Dev` section still pins it. A ticket whose frontmatter cannot be read
    is treated as live for the same reason: the sweep cannot prove it
    finished. A recurring period task pins only its `## Dev` `branch:`.
    """
    if not candidates:
        return set()
    names = sorted(candidates, key=len, reverse=True)
    pattern = re.compile(
        _MENTION_START
        + "(?:"
        + "|".join(re.escape(name) for name in names)
        + ")"
        + _MENTION_END
    )
    branches: set[str] = set()
    for ref in list_tasks(cfg):
        try:
            if read_ticket(ref).status in TERMINAL_STATUSES:
                continue
        except TicketError:
            pass
        if ref.id_slug.startswith(_PERIOD_TASK_PREFIX):
            try:
                blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
            except (OSError, TaskFileError):
                continue
            name = parse_branch_name(blackboard)
            if name in candidates:
                branches.add(name)
            continue
        for path in _task_files(ref.path):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            branches.update(pattern.findall(text))
            if len(branches) == len(candidates):
                return branches
    return branches


def _task_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return [child for child in path.rglob("*") if child.is_file()]


def _note(result: BranchSweepResult, echo: Callable[[str], None], message: str) -> None:
    result.notes.append(message)
    echo(message)


def _worktree_branches(
    root: Path,
    result: BranchSweepResult,
    echo: Callable[[str], None],
) -> dict[str, str]:
    """Prune missing worktrees and return live local branch-to-path mappings."""
    pruned = _git(root, "worktree", "prune")
    if pruned.returncode != 0:
        detail = (pruned.stderr + pruned.stdout).strip() or "git worktree prune failed"
        result.worktree_unavailable = detail
        _note(
            result,
            echo,
            f"Branch sweep: could not prune stale worktrees — sweep skipped: {detail}",
        )
        return {}

    listed = _git(root, "worktree", "list", "--porcelain")
    if listed.returncode != 0:
        detail = (
            (listed.stderr + listed.stdout).strip()
            or "git worktree list --porcelain failed"
        )
        result.worktree_unavailable = detail
        _note(
            result,
            echo,
            f"Branch sweep: could not list live worktrees — sweep skipped: {detail}",
        )
        return {}

    worktrees: dict[str, str] = {}
    path = ""
    branch_prefix = "branch refs/heads/"
    for line in listed.stdout.splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif path and line.startswith(branch_prefix):
            worktrees[line.removeprefix(branch_prefix)] = path
    return worktrees


def _local_branches(root: Path) -> dict[str, str]:
    proc = _git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    branches: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        tip = _rev_parse(root, line)
        if tip:
            branches[line] = tip
    return branches


def _remote_branches(
    cfg: Config,
    root: Path,
    result: BranchSweepResult,
    echo: Callable[[str], None],
) -> dict[str, str]:
    proc = _git(root, "ls-remote", "--heads", cfg.git_remote)
    if proc.returncode != 0:
        detail = (proc.stderr + proc.stdout).strip()
        result.remote_unavailable = detail or f"could not list {cfg.git_remote}"
        _note(
            result,
            echo,
            f"Branch sweep: could not list {cfg.git_remote} branches — remote sweep skipped: "
            f"{result.remote_unavailable}",
        )
        return {}
    branches: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        try:
            tip, ref = line.split(None, 1)
        except ValueError:
            continue
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            branches[ref[len(prefix):]] = tip
    return branches


def _current_branch(root: Path) -> str:
    proc = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _rev_parse(root: Path, ref: str) -> str:
    proc = _git(root, "rev-parse", ref)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _git(
    root: Path, *args: str, input: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=input,
        capture_output=True,
        text=True,
        check=False,
    )


__all__ = [
    "SWEEP_REPORT_HEADING",
    "BranchSweepResult",
    "MergedPrVerdict",
    "merged_pr_verdict",
    "render_sweep_report",
    "run_branch_sweep_recipe",
    "sweep_branches",
]
