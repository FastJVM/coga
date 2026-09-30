"""The durable worklist of feature checkouts the autoclose sweep could not dispose of.

The autoclose sweep disposes of the feature checkout of every ticket it closes
under the shared retire proofs (`coga.checkout_disposal`), and records a
follow-up for every checkout a proof refused. When that sweep runs as a
recurring period task, the period task's blackboard is the wrong place to keep
the record: `coga recurring` deletes the period task at the start of the next
period, and the sweep only rediscovers tickets it closes in the *current* run,
so a follow-up nobody acted on in time disappeared from every surface while
the checkout was still on disk.

This module owns the file that survives that boundary: `retires.md` beside the
recurring template's `ticket.md` under `coga/recurring/<name>/`. Two callers
share it, which is what earns it a home in core:

- the autoclose recipe walks every open entry on every run — hand-run or
  recurring — re-runs the proofs on each (its ticket may be gone by then),
  records the run's preserved closures, and drops the ones discharged;
- `coga retire` drops its own slug once the retire has actually disposed of
  the checkout.

Entries are keyed by task slug, so re-recording one refreshes the checkout it
names and keeps the first sighting's date. When an entry is **discharged** is
`is_discharged`'s rule; the `coga/autoclose/sweep` skill owns the prose. The
one design constant: the file is a record of debt, so every unknown (a branch
list or git root that cannot be read, a checkout git cannot answer for) keeps
the entry — the failure mode is "listed one time too many", never "silently
forgotten".

Primary checkouts are never directory debt, including those of another clone:
Git topology proves a primary checkout, not that its repository is disposable.
`is_primary_checkout` applies `git.classify_checkout` at closure and discharge.
Independent sandbox clones get the same protection. Linked worktrees and
unreadable directories stay listed until removed.

A foreign checkout's branch belongs to its owning repository. Entries record
that primary checkout as `owner` while it can still be classified; legacy
ownerless entries infer ownership before judging discharge, then backfill it
when retained. An unreadable owner or branch list keeps the entry. Once the
recorded branch is gone there, a primary checkout entry clears without removing
the directory. A legacy foreign linked worktree already gone cannot be
classified; its owner can be backfilled by hand.

The file is plain markdown so a human can read, hand-edit, or backfill it.
The one line shape is::

    - `<slug>` — branch `<branch>`, worktree `<path>`, recorded `<YYYY-MM-DD>`

with an optional trailing ``, owner `<path>` `` for a checkout owned by
another repository.
Field encoding for hand-edited entries is documented in `coga/autoclose/sweep`.
A line that does not parse, or a file without the `## Follow-ups (open)`
heading, fails loud rather than growing a second section no reader would find.
The file is `merge=union` like `log.md`, so a slug recorded on two branches can
arrive as two lines and a line one side dropped can be resurrected; both heal
on the next reconcile, which collapses duplicates on read and re-applies the
same discharge rule.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import quote, unquote

from coga import git
from coga.atomicio import atomic_write_text
from coga.config import Config
from coga.paths import recurring_dir, tasks_dir

RETIRE_WORKLIST_FILENAME = "retires.md"
RETIRE_WORKLIST_HEADING = "## Follow-ups (open)"
RETIRE_WORKLIST_HEADER = f"""# Feature checkouts autoclose could not dispose of

Durable worklist of auto-closed tickets whose feature checkout still exists.
The autoclose sweep records follow-ups here rather than in its period task
under `coga/tasks/recurring/`, which `coga recurring` deletes at the start of
the next period.

Every entry is a checkout a safety proof refused. Autoclose disposes of the
recorded worktree and branch itself, under the same proofs `coga retire` runs
(same-repo linked worktree on the recorded branch, locally pristine, no other
live ticket claiming it, no open PR, landed or at the merged PR's exact head);
it re-runs them on every open entry on every run and posts each refusal, with
its reason, to the coga-important Slack channel. An entry therefore stays here
only while a proof keeps refusing it — a dirty worktree, an independent clone,
a branch another live ticket records — and clears on the next run after the
cause is fixed. Run `coga retire <slug>` to see the proofs at first hand.
Entries are keyed by slug, so a later sweep refreshes one rather than
duplicating it, and an entry is dropped once its local branch is gone and its
worktree directory is gone or is this repository's own primary checkout, which
nobody disposes of. A worktree owned by another repository records that
repository as `owner`, and its branch is judged there: an owner this run
cannot read keeps the entry. An entry whose ticket no longer exists — retire
preserved the checkout and then deleted the ticket — is still walked: the
merge proof then uses the merged PRs for the recorded branch name.

For the line format and field encoding, see the `coga/autoclose/sweep` skill.

{RETIRE_WORKLIST_HEADING}
"""
_ENTRY_RE = re.compile(
    r"^- `(?P<slug>[^`]+)` — branch `(?P<branch>[^`]*)`, "
    r"worktree `(?P<worktree>[^`]*)`, recorded `(?P<recorded>[^`]*)`"
    r"(?:, owner `(?P<owner>[^`]*)`)?$"
)


class RetireWorklistError(RuntimeError):
    """The worklist on disk is not one this module wrote or can safely rewrite."""


@dataclass(frozen=True)
class RetireFollowUp:
    """One stranded checkout: the exact `coga retire <slug>` still to run."""

    slug: str
    branch: str
    worktree: str
    recorded: str
    owner: str = ""
    """The main working tree of the repository that owns `worktree`, when
    that is not this repository; empty otherwise (and on older lines)."""

    def render(self) -> str:
        # Keep the line parseable even when a path contains a backtick or a
        # newline. Escaping percent itself makes decoding unambiguous.
        slug, branch, worktree, recorded, owner = (
            quote(value, safe="/:")
            for value in (
                self.slug,
                self.branch,
                self.worktree,
                self.recorded,
                self.owner,
            )
        )
        line = (
            f"- `{slug}` — branch `{branch}`, "
            f"worktree `{worktree}`, recorded `{recorded}`"
        )
        return f"{line}, owner `{owner}`" if owner else line


@dataclass
class WorklistChange:
    """What one reconcile did, for the run report and tests."""

    path: Path
    added: list[RetireFollowUp] = field(default_factory=list)
    refreshed: list[RetireFollowUp] = field(default_factory=list)
    dropped: list[RetireFollowUp] = field(default_factory=list)
    open: list[RetireFollowUp] = field(default_factory=list)
    written: bool = False


def template_worklist_path(cfg: Config, template: str) -> Path:
    """The worklist beside `coga/recurring/<template>/ticket.md`."""
    return recurring_dir(cfg) / template / RETIRE_WORKLIST_FILENAME


def worklist_for_period_task(cfg: Config, blackboard: Path | None) -> Path | None:
    """The durable worklist for the period task a recipe is running under.

    `blackboard` is the already-scoped result of `blackboard_from_env`, so it
    is known to sit inside this root's `tasks/` tree. A period task always
    materializes at `tasks/recurring/<name>/`, which names its template
    directly; an ordinary task, a stateless bootstrap target, or no task at all
    returns `None` and keeps the caller's ordinary report surfaces. A period
    task whose template has since been removed or parked also returns `None`:
    there is no durable sibling to write beside.
    """
    if blackboard is None:
        return None
    tasks_root = tasks_dir(cfg).resolve()
    try:
        parts = blackboard.resolve().relative_to(tasks_root).parts
    except ValueError:
        return None
    if len(parts) != 3 or parts[0] != "recurring" or parts[2] != "ticket.md":
        return None
    template = parts[1]
    if not (recurring_dir(cfg) / template / "ticket.md").is_file():
        return None
    return template_worklist_path(cfg, template)


def all_worklists(cfg: Config) -> list[Path]:
    """Every recurring template's worklist that exists on disk, sorted."""
    return sorted(
        path
        for path in recurring_dir(cfg).glob(f"*/{RETIRE_WORKLIST_FILENAME}")
        if path.is_file() and not path.parent.name.startswith("_")
    )


def parse_worklist(text: str) -> tuple[str, list[RetireFollowUp]]:
    """Split a worklist into its header (through the heading) and its entries.

    Duplicate slugs collapse on read, keeping the first sighting's `recorded`
    date, the later line's checkout, and a recorded `owner` an ownerless line
    for the same worktree would drop — the same rule a re-record applies — so
    a union-merge artifact cannot outlive the next write. A stripped
    trailing newline is a benign editor artifact and is normalized rather than
    failing the daily sweep; anything else unexpected fails loud.
    """
    if not text.endswith("\n"):
        text += "\n"
    separator = RETIRE_WORKLIST_HEADING + "\n"
    if separator not in text:
        raise RetireWorklistError(
            f"retire worklist has no {RETIRE_WORKLIST_HEADING!r} section"
        )
    header, _, body = text.partition(separator)
    by_slug: dict[str, RetireFollowUp] = {}
    for line in body.splitlines():
        if not line.strip():
            continue
        match = _ENTRY_RE.match(line)
        if match is None:
            raise RetireWorklistError(f"unparsable retire worklist line: {line}")
        entry = RetireFollowUp(
            **{
                key: unquote(value, errors="strict")
                for key, value in match.groupdict().items()
                if value is not None
            }
        )
        existing = by_slug.get(entry.slug)
        if existing is not None:
            entry = _merge_sighting(existing, entry)
        by_slug[entry.slug] = entry
    return header + separator, list(by_slug.values())


def _merge_sighting(existing: RetireFollowUp, later: RetireFollowUp) -> RetireFollowUp:
    """A re-sighting of `existing`'s slug: the later checkout, the first date.

    An ownerless later line naming the same worktree keeps the recorded
    `owner`, so neither a legacy line union merge resurrects nor a re-record
    made after the directory is gone can erase it.
    """
    merged = replace(later, recorded=existing.recorded)
    if not merged.owner and merged.worktree == existing.worktree:
        merged = replace(merged, owner=existing.owner)
    return merged


def render_worklist(header: str, entries: Iterable[RetireFollowUp]) -> str:
    """Render the header plus one sorted line per entry."""
    lines = [entry.render() for entry in sorted(entries, key=lambda e: e.slug)]
    body = "\n".join(lines) + "\n" if lines else ""
    return header + "\n" + body


def local_branches(root: Path) -> frozenset[str] | None:
    """`root`'s local branch names, or `None` when they cannot be listed.

    One `for-each-ref` for the whole worklist rather than a probe per entry.
    `None` is deliberately distinct from an empty set: a failed probe leaves
    every branch unknown, and an unknown branch keeps its entry.

    The full `%(refname)` is stripped by hand rather than asking for
    `%(refname:short)`: git shortens a branch that shares its name with a tag
    to `heads/<name>`, which would read as "branch gone" and discharge an
    entry whose branch still exists — the same shadowing `coga/codebase/gotchas` warns
    about for `rev-parse --abbrev-ref`.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "for-each-ref",
                "--format=%(refname)",
                "refs/heads/",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return frozenset(ref.removeprefix("refs/heads/") for ref in result.stdout.split())


def _recorded_relation(
    root: Path | None, recorded: str | None
) -> git.CheckoutRelation | None:
    """`git.classify_checkout` on a recorded `worktree:`, or `None` when unknown.

    A relative value resolves against `root`; no git root, an empty value, or
    a path that is not a directory has no verdict.
    """
    if root is None or not recorded:
        return None
    path = Path(recorded).expanduser()
    if not path.is_absolute():
        path = root / path
    if not path.is_dir():
        return None
    return git.classify_checkout(root, path)


def is_primary_checkout(root: Path | None, recorded: str | None) -> bool:
    """Whether a recorded `worktree:` is provably a repository's primary checkout.

    A primary checkout is never directory debt: no proof removes it and
    no operator deletes it (see the module docstring). A relative value
    resolves against `root`. Every unknown answers False — no git root, a path
    that is not a directory, a checkout `git.classify_checkout` cannot read —
    so a caller that drops the worktree half on True only ever drops it on
    proof.
    """
    relation = _recorded_relation(root, recorded)
    return relation is not None and relation.kind in {"primary", "foreign-primary"}


def worktree_owner(root: Path | None, recorded: str) -> str:
    """The owning repository's primary checkout for a foreign `worktree:`.

    Both linked worktrees and independent primary checkouts carry ownership.
    This repository's checkouts and unknown paths return an empty string.
    A relative value resolves against `root`.
    """
    relation = _recorded_relation(root, recorded)
    if relation is None or relation.owner is None:
        return ""
    return str(relation.owner)


def _common_dir(path: Path) -> Path | None:
    try:
        common = git.run_git(
            path, "rev-parse", "--path-format=absolute", "--git-common-dir"
        )
    except git.GitError:
        return None
    return Path(common.strip()).resolve()


def branch_owner(root: Path | None, owner: str) -> Path | None:
    """The repository whose local branches decide a recorded `owner`'s `branch:`.

    `root` itself when the owner shares `root`'s repository — the sweep firing
    from the owning clone judges it like any other entry — the owner's path
    when it is another repository (a bare one included: its branch list is
    read the same way), and `None` when that cannot be answered: no git root,
    a path that is no longer a directory, or one git cannot read. `None` keeps
    the entry. Repositories are compared by common dir, never by path.
    """
    if root is None or not owner:
        return None
    path = Path(owner).expanduser()
    if not path.is_dir():
        return None
    theirs = _common_dir(path)
    if theirs is None:
        return None
    return root if theirs == _common_dir(root) else path


def owner_branch_remains(root: Path | None, entry: RetireFollowUp) -> bool | None:
    """Whether an entry's `branch:` is still held by its recorded `owner`.

    Infer ownership for legacy entries before consulting branches. `None`
    when the entry has no provable owner, no branch, or an owner that is
    `root`'s own repository: the branch is judged here like any other. `True`
    also covers an owner or branch list that cannot be read, because an
    unknown keeps the entry.
    """
    entry = _with_owner(entry, root)
    if not entry.branch or not entry.owner:
        return None
    home = branch_owner(root, entry.owner)
    if home is None:
        return True
    if home == root:
        return None
    branches = local_branches(home)
    return branches is None or entry.branch in branches


def is_discharged(
    entry: RetireFollowUp, *, root: Path | None, branches: frozenset[str] | None
) -> bool:
    """Whether `coga retire <slug>` has nothing left to dispose of.

    Discharged means the recorded worktree path is no longer a directory, or is
    a repository's primary checkout (`is_primary_checkout`), *and* the
    recorded branch is no longer a local branch; either half still to dispose
    of keeps the entry. A relative `worktree:` resolves against the git root
    the ticket lives in, never the process working directory. Every unknown
    keeps the entry: a relative worktree with no git root to anchor it (`root
    is None`), or a branch list that could not be read (`branches is None`).

    `branches` is `root`'s branch list. An entry with a recorded `owner` is
    judged against that owner's branches instead (`owner_branch_remains`),
    because its branch was never this repository's to lose; an owner that
    cannot be read keeps the entry.
    """
    if entry.worktree and not is_primary_checkout(root, entry.worktree):
        path = Path(entry.worktree).expanduser()
        if not path.is_absolute():
            if root is None:
                return False
            path = root / path
        if path.is_dir():
            return False
    held = owner_branch_remains(root, entry)
    if held is not None:
        return not held
    if entry.branch and (branches is None or entry.branch in branches):
        return False
    return True


def reconcile_worklist(
    cfg: Config,
    path: Path,
    *,
    root: Path | None,
    pending: Iterable[RetireFollowUp] = (),
    branches: frozenset[str] | None = None,
) -> WorklistChange:
    """Record `pending`, drop discharged entries, and write only what changed.

    The whole read/prune/merge/write happens under the local state-publication
    barrier, and the write refuses if the file's bytes moved between the read
    and the replace, so a concurrent writer wins loudly instead of being
    overwritten. `branches` defaults to `local_branches(root)`, probed only
    when there are entries to judge, so a quiet day with no worklist costs no
    git call. Every kept or recorded entry without an `owner` whose worktree
    belongs to another repository gains one while the directory
    still exists to be classified (`worktree_owner`), so the discharge rule
    can later judge its branch where it lives.
    """
    change = WorklistChange(path=path)
    with git.state_lock(cfg):
        raw = path.read_bytes() if path.exists() else None
        header, entries = (
            parse_worklist(raw.decode("utf-8"))
            if raw is not None
            else (RETIRE_WORKLIST_HEADER, [])
        )
        if branches is None and entries and root is not None:
            branches = local_branches(root)
        kept: dict[str, RetireFollowUp] = {}
        for entry in entries:
            if is_discharged(entry, root=root, branches=branches):
                change.dropped.append(entry)
            else:
                kept[entry.slug] = entry
        by_slug = {slug: _with_owner(entry, root) for slug, entry in kept.items()}
        for item in pending:
            item = _with_owner(item, root)
            existing = by_slug.get(item.slug)
            if existing is None:
                by_slug[item.slug] = item
                change.added.append(item)
                continue
            by_slug[item.slug] = _merge_sighting(existing, item)
        # One refresh per slug, however many of the backfill and the pending
        # merge changed it.
        change.refreshed = [
            entry
            for slug, entry in by_slug.items()
            if slug in kept and entry != kept[slug]
        ]
        change.open = sorted(by_slug.values(), key=lambda e: e.slug)
        rendered = render_worklist(header, change.open)
        if raw is not None and rendered.encode("utf-8") == raw:
            return change
        if raw is None and not change.open:
            # Nothing to record and no file to prune: do not mint an empty
            # worklist on every quiet day.
            return change
        current = path.read_bytes() if path.exists() else None
        if current != raw:
            raise RetireWorklistError(
                f"retire worklist changed underneath this run: {path}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, rendered)
        change.written = True
    return change


def _with_owner(entry: RetireFollowUp, root: Path | None) -> RetireFollowUp:
    if entry.owner:
        return entry
    owner = worktree_owner(root, entry.worktree)
    return replace(entry, owner=owner) if owner else entry


def discharge_slug(cfg: Config, slug: str, *, root: Path) -> list[Path]:
    """Drop `slug` from every worklist where it is now discharged.

    `coga retire`'s hook: after checkout cleanup, the entry goes only if the
    worktree and branch really are gone — a preserved checkout keeps its line.
    Any other discharged entry in the same file is dropped too; the rule is
    the same and the file is being rewritten anyway. Returns the worklists
    that changed.
    """
    changed: list[Path] = []
    for path in all_worklists(cfg):
        _, entries = parse_worklist(path.read_text(encoding="utf-8"))
        if not any(entry.slug == slug for entry in entries):
            continue
        change = reconcile_worklist(cfg, path, root=root)
        if any(entry.slug == slug for entry in change.dropped):
            changed.append(path)
    return changed


__all__ = [
    "RETIRE_WORKLIST_FILENAME",
    "RETIRE_WORKLIST_HEADER",
    "RETIRE_WORKLIST_HEADING",
    "RetireFollowUp",
    "RetireWorklistError",
    "WorklistChange",
    "all_worklists",
    "branch_owner",
    "discharge_slug",
    "is_discharged",
    "is_primary_checkout",
    "local_branches",
    "owner_branch_remains",
    "parse_worklist",
    "reconcile_worklist",
    "render_worklist",
    "template_worklist_path",
    "worklist_for_period_task",
    "worktree_owner",
]
