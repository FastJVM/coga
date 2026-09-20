"""The durable worklist of stranded `coga retire` follow-ups.

The autoclose sweep names a `coga retire <slug>` follow-up for every ticket it
closes that still records a feature checkout, and it must never dispose of one
itself — `coga retire` owns the worktree and branch safety proofs. When that
sweep runs as a recurring period task, the period task's blackboard is the
wrong place to keep the name: `coga recurring` deletes the period task at the
start of the next period, and the sweep only rediscovers tickets it closes in
the *current* run, so a follow-up nobody acted on in time disappeared from every
surface while the checkout was still on disk.

This module owns the file that survives that boundary: `retires.md` beside the
recurring template's `ticket.md` under `coga/recurring/<name>/`. Two callers
share it, which is what earns it a home in core:

- the autoclose recipe reconciles it on every recurring run — it records the
  run's new follow-ups and drops the ones already discharged;
- `coga retire` drops its own slug once the retire has actually disposed of
  the checkout.

Entries are keyed by task slug, so re-recording one refreshes the checkout it
names and keeps the first sighting's date. When an entry is **discharged** is
`is_discharged`'s rule; the `coga/autoclose/sweep` skill owns the prose. The
one design constant: the file is a record of debt, so every unknown (a branch
list or git root that cannot be read, a checkout git cannot answer for) keeps
the entry — the failure mode is "listed one time too many", never "silently
forgotten".

The rule's other half is that debt has to be *clearable by somebody*. One
recorded `worktree:` never is: this repository's own primary checkout, which a
ticket worked in the single-checkout layout records as its own, and which no
`coga retire` run removes and no operator deletes — so counting it kept such an
entry listed forever. `autoclose` declines to record that path and
`worktree_outstanding` ignores an already written one, both through the single
`git.classify_checkout` probe, so the recording and discharge sides cannot
disagree. A checkout retire itself preserves but a human can dispose of — an
independent fallback clone, or another repository's linked worktree, which is
what cross-repo upstream work records — stays listed, because this file is its
only durable trace once the ticket is gone.

The file is plain markdown so a human can read, hand-edit, or backfill it.
The one line shape is::

    - `<slug>` — branch `<branch>`, worktree `<path>`, recorded `<YYYY-MM-DD>`

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
RETIRE_WORKLIST_HEADER = f"""# Stranded `coga retire` follow-ups

Durable worklist of auto-closed tickets whose feature checkout still exists.
The autoclose sweep records follow-ups here rather than in its period task
under `coga/tasks/recurring/`, which `coga recurring` deletes at the start of
the next period.

Every entry means the same thing: run `coga retire <slug>` to dispose of the
recorded worktree and branch. Autoclose only ever names the follow-up; retire
owns the safety proofs. Entries are keyed by slug, so a later sweep refreshes
one rather than duplicating it, and an entry is dropped once its local branch
is gone and its recorded worktree is either gone or this repository's own
primary checkout. Nobody ever disposes of the primary checkout, so recording it
never holds an entry open. Every other checkout does: `coga retire` removes a
linked worktree of this repository, and you remove an independent clone or
another repository's worktree by hand. An entry whose ticket no longer exists —
retire preserved the checkout and then deleted the ticket — is still debt:
dispose of the recorded worktree and branch by hand (or let the weekly branch
sweep take the branch) and the entry clears by the same rule.

For the line format and field encoding, see the `coga/autoclose/sweep` skill.

{RETIRE_WORKLIST_HEADING}
"""
_ENTRY_RE = re.compile(
    r"^- `(?P<slug>[^`]+)` — branch `(?P<branch>[^`]*)`, "
    r"worktree `(?P<worktree>[^`]*)`, recorded `(?P<recorded>[^`]*)`$"
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

    def render(self) -> str:
        # Keep the line parseable even when a path contains a backtick or a
        # newline. Escaping percent itself makes decoding unambiguous.
        slug, branch, worktree, recorded = (
            quote(value, safe="/:")
            for value in (self.slug, self.branch, self.worktree, self.recorded)
        )
        return (
            f"- `{slug}` — branch `{branch}`, "
            f"worktree `{worktree}`, recorded `{recorded}`"
        )


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
    date and the later line's checkout — the same rule a re-record applies —
    so a union-merge artifact cannot outlive the next write. A stripped
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
            }
        )
        existing = by_slug.get(entry.slug)
        if existing is not None:
            entry = replace(entry, recorded=existing.recorded)
        by_slug[entry.slug] = entry
    return header + separator, list(by_slug.values())


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
    entry whose branch still exists — the same shadowing `coga/codebase` warns
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


def worktree_outstanding(entry: RetireFollowUp, *, root: Path | None) -> bool:
    """Whether the entry's recorded checkout is still somebody's to dispose of.

    A path that is not a directory is gone, so nothing is outstanding. A path
    that exists is outstanding unless it is **this repository's primary
    checkout** (`git.classify_checkout` → `"primary"`), the one recorded
    `worktree:` no action could ever clear. A `"foreign"` checkout stays
    outstanding even though `coga retire` will not remove it, because a human
    still will; the module docstring above has the why, and `autoclose`
    declines to record the primary checkout through the same probe.

    Unknowns stay outstanding, as everywhere else here: no git root to anchor a
    relative path (`root is None`), or a checkout `git.classify_checkout` could
    not read (`None`).
    """
    if not entry.worktree:
        return False
    path = Path(entry.worktree).expanduser()
    if not path.is_absolute():
        if root is None:
            return True
        path = root / path
    if not path.is_dir():
        return False
    if root is None:
        return True
    return git.classify_checkout(root, path) != "primary"


def is_discharged(
    entry: RetireFollowUp, *, root: Path | None, branches: frozenset[str] | None
) -> bool:
    """Whether `coga retire <slug>` has nothing left to dispose of.

    Discharged means the recorded worktree is no longer outstanding (see
    `worktree_outstanding`) *and* the recorded branch is no longer a local
    branch; either half still to dispose of keeps the entry. Every unknown
    keeps the entry, including a branch list that could not be read
    (`branches is None`).
    """
    if worktree_outstanding(entry, root=root):
        return False
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
    git call.
    """
    change = WorklistChange(path=path)
    with git.state_publication_barrier(cfg):
        raw = path.read_bytes() if path.exists() else None
        header, entries = (
            parse_worklist(raw.decode("utf-8"))
            if raw is not None
            else (RETIRE_WORKLIST_HEADER, [])
        )
        if branches is None and entries and root is not None:
            branches = local_branches(root)
        by_slug: dict[str, RetireFollowUp] = {}
        for entry in entries:
            if is_discharged(entry, root=root, branches=branches):
                change.dropped.append(entry)
            else:
                by_slug[entry.slug] = entry
        for item in pending:
            existing = by_slug.get(item.slug)
            if existing is None:
                by_slug[item.slug] = item
                change.added.append(item)
                continue
            merged = replace(item, recorded=existing.recorded)
            if merged != existing:
                change.refreshed.append(merged)
            by_slug[item.slug] = merged
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


def discharge_slug(cfg: Config, slug: str, *, root: Path) -> list[Path]:
    """Drop `slug` from every worklist where it is now discharged.

    `coga retire`'s hook: after checkout cleanup, the entry goes only if
    `is_discharged` says nothing is left to dispose of — a checkout retire
    preserved and a human still has to remove keeps its line. The one
    exception is this repository's own primary checkout, which the same rule
    never counted as debt. Any other discharged entry in the same file is
    dropped too; the rule is the same and the file is being rewritten anyway.
    Returns the worklists that changed.
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
    "discharge_slug",
    "is_discharged",
    "local_branches",
    "parse_worklist",
    "reconcile_worklist",
    "render_worklist",
    "template_worklist_path",
    "worklist_for_period_task",
    "worktree_outstanding",
]
