"""Archive and clean eligible feature branches with explicit ticket ownership.

Shared by terminal-ticket disposal and the daily/weekly branch sweep. Merged
PRs retain the landed-history proof; closed-unmerged PRs additionally need a
surviving done/canceled owner. Open PRs and live Dev claims protect both refs.
The owning contract is docs/contexts/dev/checkout-cleanup/SKILL.md.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from coga.autoclose import GhError, prs_for_head
from coga.blackboard import append_blackboard_report
from coga.branchcleanup import (
    BranchCleanupResult,
    WorktreeCleanupResult,
    delete_local_branch,
    delete_remote_branch,
    inspect_worktree_for_removal,
    local_branch_landed,
    remove_inspected_worktree,
)
from coga.checkout_disposal import checkout_records, live_checkout_claim
from coga.config import Config, local_config_path
from coga import git
from coga.github_preflight import coga_root_prefix, is_coga_state_path
from coga.lifecycle import TERMINAL_STATUSES
from coga.skill_manager import SKILL_UPDATE_BRANCH
from coga.task_env import blackboard_from_env

if TYPE_CHECKING:
    from coga.branchcleanup import _WorktreeLocalState

SWEEP_REPORT_HEADING = "## Branch Sweep"


@dataclass
class BranchSweepResult:
    """What one `sweep_branches` run did, for reporting and tests."""

    local_deleted: list[str] = field(default_factory=list)
    remote_deleted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    worktree_pinned: list[str] = field(default_factory=list)
    worktree_removed: list[str] = field(default_factory=list)
    """Linked worktrees the sweep removed under `[git].worktrees_ticket_owned`."""
    notes: list[str] = field(default_factory=list)
    gh_unavailable: str | None = None
    remote_unavailable: str | None = None
    worktree_unavailable: str | None = None
    state_root_unavailable: str | None = None
    retirement_failures: list[str] = field(default_factory=list)

    @property
    def failure(self) -> str | None:
        """First failure explaining a skipped or partial sweep, if any."""
        return (
            self.remote_unavailable
            or self.worktree_unavailable
            or self.state_root_unavailable
            or self.gh_unavailable
            or next(iter(self.retirement_failures), None)
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
    branches: set[str] | None = None,
    recorded_worktrees: dict[str, str] | None = None,
    remove_worktrees: bool = True,
    dry_run: bool = False,
) -> BranchSweepResult:
    """Delete local/`origin` branches whose PR has merged, skipping live ones.

    `root` is the git working-tree root. Prunes registrations for missing
    worktrees first. Never touches `cfg.git_control_branch`, the currently
    checked-out branch, the shared skill-update branch, or a branch recorded
    on a non-terminal ticket. Publish the retirement tag before deletion. A merged
    branch still checked out in a live worktree is left alone unless
    `cfg.git_worktrees_ticket_owned` admits removing that worktree first (see
    the module docstring). If worktree state or `gh` is unavailable, the rest
    of the sweep is skipped and reported rather than deleting with incomplete
    safety information.

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
    if result.remote_unavailable:
        return result
    names = local.keys() | remote.keys()
    if branches is not None:
        names &= branches
    try:
        records = checkout_records(cfg, root)
    except Exception as exc:
        result.state_root_unavailable = f"could not verify ticket ownership: {exc}"
        _note(result, echo, f"Branch sweep: {result.state_root_unavailable} — no deletes.")
        return result
    live_branches = {b for _, status, owned, _ in records if status not in TERMINAL_STATUSES for b in owned}
    terminal_branches = {b for _, status, owned, _ in records if status in TERMINAL_STATUSES for b in owned}
    recorded_worktrees = dict(recorded_worktrees or {})
    for _, status, owned, worktree in records:
        if owned and worktree and status in TERMINAL_STATUSES:
            recorded_worktrees.setdefault(owned[0], worktree)
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
        if branch == SKILL_UPDATE_BRANCH:
            _note(
                result, echo,
                f"Branch sweep: {branch!r} is the shared skill-update branch — left in place.",
            )
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

        recorded = recorded_worktrees.get(branch)
        if recorded:
            path = Path(recorded)
            if not path.is_absolute():
                path = root / path
            relation = git.classify_checkout(root, path)
            if relation is None or relation.kind.startswith("foreign"):
                result.skipped.append(branch)
                _note(result, echo, f"Branch sweep: {branch!r} recorded checkout {recorded!r} is missing, unreadable, or owned by another clone — inspect in its owning repository.")
                continue
            if relation.kind == "linked" and str(path.resolve()) != str(Path(worktree_branches.get(branch, "")).resolve()):
                result.skipped.append(branch)
                _note(result, echo, f"Branch sweep: {branch!r} recorded checkout now holds another branch — left in place.")
                continue

        try:
            merged = _merged_prs(branch)
            closed = [
                (str(item["number"]), str(item["headRefOid"]))
                for item in prs_for_head(branch, "closed")
                if item.get("number") and item.get("headRefOid")
            ] if branch in terminal_branches else []
            # GitHub's "closed" listing also includes merged PRs.
            closed = [item for item in closed if item not in merged]
            open_pr = bool(prs_for_head(branch, "open"))
        except GhError as exc:
            result.gh_unavailable = str(exc)
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: gh unavailable ({exc}) — no gated deletes this run.")
            continue

        if open_pr:
            if branch in worktree_branches:
                result.worktree_pinned.append(branch)
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: {branch!r} has an open PR — both refs left in place.")
            continue
        authorized_prs = list(dict.fromkeys(merged + closed))
        if closed:
            _note(result, echo, f"Branch sweep: {branch!r} has a terminal owning ticket; closed PR heads may authorize cleanup.")

        # A remote ref is released only at the exact merged tip; the widened
        # rule is for the local ref, whose extra commits can be inspected.
        remote_merged = (
            not open_pr and any(head == remote_tip for _number, head in authorized_prs)
        )
        local_verdict: MergedPrVerdict | None = None
        if local_tip is not None and authorized_prs:
            local_verdict = (
                MergedPrVerdict(False, "has an open PR")
                if open_pr
                else merged_pr_verdict(
                    root,
                    local_tip,
                    authorized_prs,
                    landed_refs=landed_refs if merged else [],
                    remote=cfg.git_remote,
                    coga_prefix=coga_prefix,
                )
            )
        if local_verdict is not None and closed and not merged:
            local_verdict = MergedPrVerdict(local_verdict.landed, local_verdict.reason.replace("merged", "closed"))
        local_merged = local_verdict is not None and local_verdict.landed
        if remote_tip and authorized_prs and not remote_merged:
            _note(result, echo, f"Branch sweep: {branch!r} remote tip {remote_tip[:12]} differs from the closed/merged PR head — remote preserved.")

        local_landed = (
            local_tip is not None
            and local_branch_landed(root, branch, cfg.git_control_branch)
        )
        remove_worktree = False
        if branch in worktree_branches and (
            remote_merged
            or local_merged
            or local_landed
        ):
            recorded = recorded_worktrees.get(branch)
            explicitly_recorded = recorded is not None and Path(recorded).resolve() == Path(worktree_branches[branch]).resolve()
            if not remove_worktrees or not (cfg.git_worktrees_ticket_owned or explicitly_recorded):
                result.worktree_pinned.append(branch)
                _note(
                    result,
                    echo,
                    f"Branch sweep: {branch!r} has a landed ref but is checked out "
                    f"in worktree {worktree_branches[branch]!r} — left in place.",
                )
                continue
            # A merged remote ref does not vouch for newer local work.
            # Authorize the checkout itself before removing its directory.
            if open_pr or not (local_merged or local_landed):
                result.worktree_pinned.append(branch)
                reason = "has an open PR" if open_pr else "local tip has not landed"
                _note(
                    result, echo,
                    f"Branch sweep: {branch!r} {reason} — worktree "
                    f"{worktree_branches[branch]!r} and both refs left in place.",
                )
                continue
            remove_worktree = True

        if remove_worktree:
            cleanup, local_state = _inspect_pinning_worktree(
                cfg, root, branch, worktree_branches[branch], result, echo
            )
            if local_state is None and not cleanup.already_gone:
                result.worktree_pinned.append(branch)
                continue

        if dry_run:
            eligibility = []
            if local_tip and (local_merged or local_landed):
                eligibility.append(f"local {local_tip}")
            if remote_tip and remote_merged and (local_tip is None or eligibility):
                eligibility.append(f"remote {remote_tip}")
            if eligibility:
                _note(result, echo, f"Branch sweep: {branch!r} eligible after archive publication: {', '.join(eligibility)}.")
            else:
                reason = local_verdict.reason if local_verdict else "no eligible PR head or landed local tip"
                _note(result, echo, f"Branch sweep: {branch!r} preserved: {reason}.")
            result.skipped.append(branch)
            continue

        # Archive every tip this pass could delete before touching a checkout
        # or ref. A single tag must preserve both halves of a split branch.
        retirement_tips: list[str] = []
        if local_tip is not None and (local_merged or local_landed):
            retirement_tips.append(local_tip)
        if remote_tip is not None and remote_merged and (
            local_tip is None or retirement_tips
        ):
            retirement_tips.append(remote_tip)
        if retirement_tips and not _publish_retirement_tag(
            cfg, root, branch, retirement_tips, result, echo,
            pr_heads={head: number for number, head in authorized_prs},
        ):
            result.skipped.append(branch)
            continue

        try:
            claim = live_checkout_claim(cfg, root, branch=branch, worktree=recorded_worktrees.get(branch))
        except Exception as exc:
            claim = f"could not recheck ownership: {exc}"
        if claim:
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: {branch!r}: {claim} — left in place.")
            continue

        try:
            reopened = bool(retirement_tips) and bool(prs_for_head(branch, "open"))
        except GhError as exc:
            result.gh_unavailable = str(exc)
            reopened = True
        if reopened:
            result.skipped.append(branch)
            _note(result, echo, f"Branch sweep: {branch!r} open-PR check changed or failed after archival — left in place.")
            continue

        if remove_worktree:
            # Publication crosses a network boundary. Repeat the claim and
            # local-state proofs before removing the previously clean checkout.
            cleanup = _remove_pinning_worktree(
                cfg, root, branch, worktree_branches[branch], result, echo,
                expected_tip=local_tip,
            )
            if not (cleanup.removed or cleanup.already_gone):
                result.worktree_pinned.append(branch)
                continue
            if cleanup.removed:
                result.worktree_removed.append(worktree_branches[branch])

        # The cleanup helpers note into the sweep's own record, so each delete
        # and refusal lands in the run report in the order it happened.
        cleanup = BranchCleanupResult(branch=branch, notes=result.notes)
        if branch in local:
            if local_verdict is not None and not local_merged and not local_landed:
                # `delete_local_branch` says "no merged PR vouching for it"
                # below; when a PR exists and still did not authorize, the
                # verdict's reason is the actionable part of the run record.
                _note(result, echo, f"Branch sweep: {branch!r} {local_verdict.reason}.")
            if local_merged or local_landed:
                delete_local_branch(
                    root,
                    branch,
                    local_merged,
                    echo,
                    cleanup,
                    landed_ref=cfg.git_control_branch,
                    expected_tip=local_tip,
                )
            else:
                # Control could advance after this pass's landing check.
                # Never let the helper authorize an unarchived tip anew.
                _note(
                    result, echo,
                    f"Branch cleanup: local {branch!r} has unmerged work and no merged "
                    "PR vouching for it — left in place.",
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


def _publish_retirement_tag(
    cfg: Config,
    root: Path,
    branch: str,
    tips: list[str],
    result: BranchSweepResult,
    echo: Callable[[str], None],
    *,
    pr_heads: dict[str, str] | None = None,
) -> bool:
    """Push an immutable archive covering every tip authorized for deletion.

    `pr_heads` maps merged PR head SHAs to their PR numbers. GitHub keeps each
    at `refs/pull/<n>/head`, so when the tips diverge — a local ref whose
    commits another checkout rebased and merged from that copy — a tip that
    is a merged head is left to that ref and the tag archives the rest.
    """
    tag = f"retired/{branch}"

    def refuse(reason: str) -> bool:
        message = f"Branch sweep: {branch!r} could not publish {tag!r}: {reason} — left in place."
        result.retirement_failures.append(message)
        _note(result, echo, message)
        return False

    for tip in dict.fromkeys(tips):
        if _object_present(root, tip):
            continue
        fetched = _git(
            root, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head",
            cfg.git_remote, tip,
        )
        if fetched.returncode != 0 or not _object_present(root, tip):
            return refuse(
                f"cannot fetch tip {tip}: {(fetched.stderr + fetched.stdout).strip()}"
            )

    # Local refs may lag a merged remote head or carry later bookkeeping.
    # Choose the actual tip that contains all the others; never synthesize a
    # merge. Divergent history drops only a side GitHub already preserves.
    target = _containing_tip(root, tips)
    pr_heads = pr_heads or {}
    pr_kept = [tip for tip in tips if tip in pr_heads]
    if target is None and pr_kept and len(pr_kept) < len(tips):
        target = _containing_tip(root, [tip for tip in tips if tip not in pr_kept])
        if target is not None:
            kept = ", ".join(
                f"{tip[:12]} at refs/pull/{pr_heads[tip]}/head" for tip in pr_kept
            )
            _note(
                result, echo,
                f"Branch sweep: {branch!r} tips diverge; {kept} stays on "
                f"{cfg.git_remote} as the PR head.",
            )
    if target is None:
        return refuse("divergent tips cannot be preserved by one retirement tag")

    # The remote tag is the archive; a local tag is only a convenience copy.
    # An earlier sweep (perhaps from another clone) may already hold the name
    # at a descendant, which preserves this tip, or at unrelated history,
    # which must never be moved. The second, tip-qualified name is
    # deterministic, so a retry finds its own earlier publication. It cannot
    # be `retired/<branch>/<sha>`: a ref cannot nest under an existing tag ref.
    names = [tag, f"{tag}@{target[:12]}"]
    listed = _git(
        root, "ls-remote", "--tags", cfg.git_remote,
        *(f"refs/tags/{name}" for name in names),
    )
    if listed.returncode != 0:
        return refuse(
            f"cannot read remote tags: {(listed.stderr + listed.stdout).strip()}"
        )
    remote_tags = {
        ref: oid
        for oid, _, ref in (
            line.partition("\t") for line in listed.stdout.splitlines()
        )
    }

    for name in names:
        name_ref = f"refs/tags/{name}"
        # A blob/tree tag occupies the name even though it cannot archive a
        # commit. Keep its OID so it is neither published over nor mirrored.
        local_oid = _rev_parse(root, name_ref) or None
        local_tag = _rev_parse(root, f"{name_ref}^{{commit}}") or local_oid
        remote_oid = remote_tags.get(name_ref)
        if remote_oid is not None:
            remote_commit = _archived_object(cfg, root, remote_oid)
            if remote_commit is None:
                return refuse(f"cannot fetch remote {name!r} at {remote_oid}")
            if not _object_present(root, remote_commit):
                continue
            if not (
                remote_commit == target
                or _git(root, "merge-base", "--is-ancestor", target, remote_commit).returncode == 0
            ):
                continue
            _mirror_local_tag(root, name, local_tag, remote_commit)
            _note(
                result, echo,
                f"Branch sweep: {branch!r} at {target} is already archived by "
                f"{name!r} on {cfg.git_remote}.",
            )
            return True
        # An unpublished local tag elsewhere may be someone's only archive.
        if local_tag is not None and local_tag != target:
            continue
        # Suppress push.followTags as well as naming the one ref: otherwise
        # Git may also publish unrelated annotated tags reachable from this
        # commit. No force: a tag published since the listing is rejected.
        pushed = _git(
            root, "push", "--no-follow-tags", cfg.git_remote, f"{target}:{name_ref}"
        )
        if pushed.returncode != 0:
            return refuse((pushed.stderr + pushed.stdout).strip())
        _mirror_local_tag(root, name, local_tag, target)
        _note(
            result, echo,
            f"Branch sweep: archived {branch!r} at {target} as {name!r} on {cfg.git_remote}.",
        )
        return True

    return refuse(
        f"{' and '.join(repr(name) for name in names)} already archive other "
        "objects; never overwrite them"
    )


def _archived_object(cfg: Config, root: Path, oid: str) -> str | None:
    """Return the peeled object, including blobs/trees, or None if unavailable."""
    if _git(root, "cat-file", "-e", oid).returncode != 0:
        _git(
            root, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head",
            cfg.git_remote, oid,
        )
    return _rev_parse(root, f"{oid}^{{}}") or None


def _mirror_local_tag(root: Path, name: str, local: str | None, archived: str) -> None:
    """Keep the local tag from disagreeing with the published archive.

    Create it when missing; advance it only when the archive already contains
    its commit, so no local-only history is dropped.
    """
    if local is None:
        _git(root, "tag", "--", name, archived)
    elif local != archived and (
        _git(root, "merge-base", "--is-ancestor", local, archived).returncode == 0
    ):
        _git(root, "tag", "--force", "--", name, archived)


def _containing_tip(root: Path, tips: list[str]) -> str | None:
    """The tip in `tips` that every other tip is an ancestor of, if any."""
    return next(
        (
            candidate for candidate in tips
            if all(
                tip == candidate
                or _git(root, "merge-base", "--is-ancestor", tip, candidate).returncode == 0
                for tip in tips
            )
        ),
        None,
    )


def _remove_pinning_worktree(
    cfg: Config,
    root: Path,
    branch: str,
    worktree: str,
    result: BranchSweepResult,
    echo: Callable[[str], None],
    *,
    expected_tip: str | None,
) -> WorktreeCleanupResult:
    """Recheck and remove the live worktree holding archived, landed `branch`.

    `expected_tip` is the local tip the sweep archived and authorized. A clean
    commit made in the checkout during publication moves HEAD without
    dirtying it, so the removal also requires HEAD to still be that tip.
    """
    cleanup, local_state = _inspect_pinning_worktree(
        cfg, root, branch, worktree, result, echo
    )
    if local_state is None:
        return cleanup
    head = _git(Path(worktree), "rev-parse", "--verify", "HEAD")
    current = head.stdout.strip() if head.returncode == 0 else None
    if expected_tip is None or current != expected_tip:
        moved = current[:12] if current else "an unreadable HEAD"
        archived = expected_tip[:12] if expected_tip else "no archived tip"
        _note(
            result, echo,
            f"Branch sweep: {branch!r} worktree {worktree!r} moved from "
            f"{archived} to {moved} since it was authorized — both refs left in place.",
        )
        return cleanup
    return remove_inspected_worktree(
        root, Path(worktree), local_state, result=cleanup, echo=echo
    )


def _inspect_pinning_worktree(
    cfg: Config,
    root: Path,
    branch: str,
    worktree: str,
    result: BranchSweepResult,
    echo: Callable[[str], None],
) -> tuple[WorktreeCleanupResult, _WorktreeLocalState | None]:
    """Prove a landed worktree is disposable without archiving or removing it.

    Only reached under `[git].worktrees_ticket_owned`, after the sweep has
    already established that the branch landed and no live ticket names it.
    The worktree proofs are retire's (`inspect_worktree_for_removal`: same-repo
    linked worktree, checked out on `branch`, nothing but regenerable caches
    locally) plus the claim scan on the *path*, which the branch-name guard
    above cannot see. Every refusal is noted and keeps the branch
    worktree-pinned, as before the key existed.
    """
    path = Path(worktree)
    cleanup = WorktreeCleanupResult(worktree=worktree, notes=result.notes)
    try:
        claim = live_checkout_claim(cfg, root, branch=branch, worktree=worktree)
    except Exception as exc:  # noqa: BLE001 — incomplete proof preserves checkout
        _note(
            result,
            echo,
            f"Branch sweep: {branch!r} has a landed ref but its worktree "
            f"{worktree!r} could not be proven unclaimed ({exc}) — left in place.",
        )
        return cleanup, None
    if claim is not None:
        _note(
            result,
            echo,
            f"Branch sweep: {branch!r} has a landed ref but {claim} — worktree "
            f"{worktree!r} left in place.",
        )
        return cleanup, None
    local_state = inspect_worktree_for_removal(
        root,
        path,
        branch,
        result=cleanup,
        echo=echo,
        local_config=local_config_path(cfg.repo_root),
    )
    if local_state is None:
        # `already_gone` (pruned between the listing and now) no longer pins
        # the branch; every other refusal keeps both refs.
        if not cleanup.already_gone:
            _note(
                result,
                echo,
                f"Branch sweep: {branch!r} has a landed ref but its worktree "
                f"{worktree!r} was preserved — both refs left in place.",
            )
    return cleanup, local_state


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
    not land: commits beyond the merged head and control must either have a
    whitespace-sensitive patch match on the merged head or touch only
    generated Coga state (`is_coga_state_path`). `git patch-id --verbatim`
    preserves meaningful whitespace, including Python indentation. Compare
    against the merged head's history without excluding control: a normal
    merge puts the matching commits on control too. A rebase that changed a
    patch keeps its commit in the list and the branch, and merge commits are
    never excluded by patch matching.
    `landed_refs` are the control refs that exist locally — the control
    branch and its remote-tracking ref — because a branch that merged the
    remote-tracking control ref after its PR landed carries control's own
    later source commits, which a lagging local control branch would
    otherwise report as the ref's unmerged work. That one rule covers the exact merged tip
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
        if commits:
            merged_patches = _verbatim_patch_ids(root, [head, f"^{tip}"])
            local_patches = _verbatim_patch_ids(root, commits, no_walk=True)
            if merged_patches is None or local_patches is None:
                reason = f"{refused} its patches could not be compared"
                continue
            matching = Counter(merged_patches.values())
            unmatched = []
            for commit in commits:
                patch_id = local_patches.get(commit)
                if patch_id is not None and matching[patch_id]:
                    matching[patch_id] -= 1
                else:
                    unmatched.append(commit)
            commits = unmatched
        offending = _non_state_paths(root, commits, coga_prefix=coga_prefix)
        if offending is None:
            reason = f"{refused} the commits beyond it could not be inspected"
            continue
        if not offending:
            beyond_note = (
                f"; the {len(commits)} later commit(s) on this ref touch only "
                "Coga task/log state"
                if commits
                else "; the ref is contained in or patch-equivalent to landed history"
            )
            return MergedPrVerdict(True, f"PR #{number} merged{beyond_note}")
        shown = ", ".join(sorted(offending)[:3])
        more = f" (+{len(offending) - 3} more)" if len(offending) > 3 else ""
        reason = f"{refused} the ref carries commits touching {shown}{more} — left in place"
    return MergedPrVerdict(False, reason)


def _verbatim_patch_ids(
    root: Path, revisions: list[str], *, no_walk: bool = False
) -> dict[str, str] | None:
    """Map non-merge commits to whitespace-sensitive patch IDs; fail closed.

    Keep control exclusions out of the merged-side revisions so normal
    merges retain the same comparison evidence as squash merges. A differing
    context can conservatively prevent a match. Disable external diff and
    text conversion so the proof describes the stored source bytes.
    """
    # Use bytes: text-mode subprocess IO would normalize CRLF in a patch.
    git = ["git", "-C", str(root)]
    patches = subprocess.run(
        [
            *git, "log", "--stdin", *(["--no-walk=unsorted"] if no_walk else []),
            "--no-merges", "--root", "--format=commit %H", "--patch", "--binary",
            "--full-index", "--no-color", "--no-ext-diff", "--no-textconv",
            "--no-renames", "--no-notes", "--no-relative", "--ignore-submodules=none",
            "--submodule=short", "--src-prefix=a/", "--dst-prefix=b/", "--",
        ],
        input=("\n".join(revisions) + "\n").encode("ascii"),
        capture_output=True,
        check=False,
    )
    if patches.returncode != 0:
        return None
    ids = subprocess.run(
        [*git, "patch-id", "--verbatim"], input=patches.stdout,
        capture_output=True, check=False,
    )
    if ids.returncode != 0:
        return None
    result: dict[str, str] = {}
    for line in ids.stdout.decode("ascii").splitlines():
        fields = line.split()
        if len(fields) != 2:
            return None
        patch_id, commit = fields
        result[commit] = patch_id
    return result


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
    root = git.toplevel(cfg.repo_root)
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
    if result.worktree_removed:
        sys.stdout.write(
            "[branch-sweep] removed-worktree: "
            f"{', '.join(result.worktree_removed)}\n"
        )
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
        f"{len(result.worktree_removed)} worktree(s) removed, "
        f"{len(result.worktree_pinned)} skipped-worktree-pinned, "
        f"{len(result.skipped)} skipped."
    )
    for label, names in (
        ("deleted local", result.local_deleted),
        ("deleted remote", result.remote_deleted),
        ("removed worktree", result.worktree_removed),
        ("skipped-worktree-pinned", result.worktree_pinned),
        ("skipped", result.skipped),
    ):
        if names:
            lines.append(f"- {label}: {', '.join(names)}")
    if result.notes:
        lines.extend(["", "### Decisions", ""])
        lines.extend(f"- {note}" for note in result.notes)
    return "\n".join(lines) + "\n"


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
    # `:short` adds a `heads/` prefix when an archive tag shares the name.
    proc = _git(root, "for-each-ref", "--format=%(refname:strip=2)", "refs/heads/")
    branches: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        tip = _rev_parse(root, f"refs/heads/{line}")
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
