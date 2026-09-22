"""Auto-close started tickets whose linked PR has merged.

Scope: tickets whose `## Dev` blackboard section names a PR, where the PR
is merged on GitHub, and where the ticket is on its final workflow step
(or has no workflow). One bump = `done`. Mid-workflow merges stay alone
— a merge there is suspicious and the human should bump explicitly.

The PR link convention lives in the `dev/code` context: a `pr:` line
under `## Dev` on the blackboard. We parse it directly; coga-the-CLI
treats the blackboard as plain text on purpose.

The `autoclose-merged` recurring ticket's `ticket.py` is the scheduled caller:
it runs `sweep_merged` to finish tickets whose PR merged out of band. The same
implementation remains available explicitly as the registered `coga run
autoclose` command; there is intentionally no dedicated top-level command and
no launch-time or status-time side effect. Accepted tradeoff: absent an
explicit run, a ticket merged today won't auto-close until the next sweep
(≤24h lag).

`coga status` deliberately does NOT call this — it is a read-only view
(principle 6, fail loud, forbids `status`/`show`/`validate` from mutating
state or hitting the network as a side effect of rendering).

Closing a ticket also disposes of its feature checkout, under exactly the
proofs `coga retire` runs — the shared `coga.checkout_disposal` orchestration
over `branchcleanup`'s linked-worktree / pristine / open-PR / landed-or-merged
gates, plus the live-claim scan. The earlier design only *named* a `coga
retire` follow-up here, on the principle that destructive behavior is never
implicit; that produced a ten-entry backlog nobody typed, so the sweep now
runs the deterministic, narrow, named proofs itself (`_dispose_checkouts`)
and names only what a proof refused, with the reason — see
`_report_retire_followups`. It only ever touches worktrees a ticket or a
worklist entry recorded, and only from a checkout on the control branch.

Under a recurring period task the refusals have to outlive the run: the period
task is deleted at the next period boundary, so the sweep records each
preserved checkout in the template's durable `retires.md`
(`coga.retire_worklist`), and on every run — hand-run or recurring — walks the
open entries of every worklist, re-runs the proofs on each (its ticket may be
gone by then), and drops the ones discharged. The worklist stays a worklist.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from coga import git
from coga.blackboard import append_blackboard_report
from coga.mark import mark_done
from coga.config import Config
from coga.notification import post, preflight_post
from coga.retire_worklist import (
    RetireFollowUp,
    RetireWorklistError,
    WorklistChange,
    all_worklists,
    parse_worklist,
    reconcile_worklist,
    worklist_for_period_task,
)
from coga.task_env import blackboard_from_env
from coga.taskfile import (
    TaskFileError,
    read_blackboard,
)
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import Ticket, TicketError
from coga.validate import TaskValidationError

if TYPE_CHECKING:
    from coga.checkout_disposal import CheckoutDisposal


class GhError(Exception):
    """Raised when `gh` is missing, unauthed, or returns a non-zero exit."""


RETIRE_REPORT_HEADING = "## Autoclose Sweep: retire follow-ups"


@dataclass(frozen=True)
class ClosedTicket:
    """One ticket a sweep finished, plus the checkout state it left behind.

    `branch` / `worktree` are the `## Dev` lines as they read at close time.
    They are captured *during* the sweep on purpose: they are the only trace of
    which checkout belongs to this ticket, and a later reader may find them
    gone — retire clears them, and a deleted task takes them with it.
    """

    slug: str
    title: str
    branch: str | None
    worktree: str | None
    # The `pr:` link the close was decided on; the disposal proofs read the
    # merged head from it.
    pr: str | None = None

    @property
    def retire_command(self) -> str:
        return f"coga retire {self.slug}"

    @property
    def checkout_state(self) -> str:
        """What is still on disk, rendered for the report line."""
        return _checkout_state(self.branch, self.worktree)


def _checkout_state(branch: str | None, worktree: str | None) -> str:
    parts = []
    if worktree:
        parts.append(f"worktree `{worktree}`")
    if branch:
        parts.append(f"branch `{branch}`")
    return ", ".join(parts)


@dataclass
class CheckoutOutcome:
    """One recorded checkout the disposal phase judged, and what became of it.

    Candidates are the tickets this sweep closed (`title` set) and the open
    `retires.md` entries carried over from earlier runs (`title` None). A
    backlog entry's ticket may already be gone — retire preserved the checkout
    and then deleted the ticket — so `ticket_exists` says whether the manual
    `coga retire <slug>` still resolves.
    """

    slug: str
    title: str | None
    branch: str | None
    worktree: str | None
    ticket_exists: bool
    disposal: CheckoutDisposal

    @property
    def disposed(self) -> bool:
        return self.disposal.disposed

    @property
    def checkout_state(self) -> str:
        return _checkout_state(self.branch, self.worktree)

    @property
    def manual_command(self) -> str:
        """What a human types for a preserved checkout."""
        if self.ticket_exists:
            return f"`coga retire {self.slug}`"
        return "dispose of the recorded worktree and branch by hand"


OPEN_STATUSES = frozenset({"active", "in_progress"})


@dataclass
class AutocloseResult:
    """What one `sweep_merged` run closed, for reporting and tests."""

    closed: list[ClosedTicket] = field(default_factory=list)
    scanned: int = 0
    """Open (`active`/`in_progress`) tickets this sweep examined.

    The denominator `closed` is measured against. Counted during the walk the
    sweep already makes, so a caller reporting "N open ticket(s) scanned" does
    not have to enumerate every ticket a second time. A sweep cut short by a
    `gh` failure leaves a partial count, matching what it actually looked at.
    """

    checkouts: list[CheckoutOutcome] = field(default_factory=list)
    """Every checkout the disposal phase judged this run, closures then backlog."""
    disposal_skipped: str | None = None
    """Why the disposal phase never ran — every recorded checkout was preserved."""

    @property
    def retire_pending(self) -> list[ClosedTicket]:
        """Closed tickets whose feature checkout or branch outlived them.

        Read after `_dispose_checkouts`: a closure whose checkout the proofs
        disposed of is not pending and never enters the worklist.
        """
        disposed = {item.slug for item in self.checkouts if item.disposed}
        return [
            item
            for item in self.closed
            if (item.branch or item.worktree) and item.slug not in disposed
        ]

    @property
    def disposed(self) -> list[CheckoutOutcome]:
        return [item for item in self.checkouts if item.disposed]

    @property
    def preserved(self) -> list[CheckoutOutcome]:
        return [item for item in self.checkouts if not item.disposed]


_DEV_SECTION_RE = re.compile(
    r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Tolerate an optional `- ` list prefix, exactly like `_BRANCH_LINE_RE` below:
# `## Dev` lines are written both bare (`pr: <url>`) and bulleted
# (`- pr: <url>`), and the bulleted shape is perfectly natural. Without the
# prefix group a bulleted `pr:` line is invisible to the sweep, so a merged
# final-step ticket is silently skipped and left stranded `in_progress`. The
# same sentence applied to a trailing annotation (`pr: <url> (no CI here)`),
# which an anchored `(\S+)$` capture rejected while the `branch:` / `worktree:`
# siblings tolerated it. Capture the rest of the line like they do and
# normalize in `parse_pr_url`. Spell the surrounding runs `[ \t]` rather than
# `\s`: `\s` matches newlines, so a non-greedy `(.+?)` on an empty `pr:` line
# would reach past it and capture the next non-blank line, which is not a
# `pr:` line at all.
_PR_LINE_RE = re.compile(r"^[ \t]*(?:-[ \t]*)?pr:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
_PR_NUMBER_RE = re.compile(r"/pull/(\d+)")
# The `branch:` line is written inconsistently across existing tickets:
# `branch: my-branch`, `- branch: \`my-branch\``, ``branch: `my-branch` ``.
# Tolerate an optional `- ` list prefix and capture the rest of the line; the
# surrounding backticks/whitespace are normalized in `parse_branch_name`. A
# leading backtick delimits the value through its matching closing backtick;
# bare values still consume the whole remainder of the line.
_BRANCH_LINE_RE = re.compile(r"^\s*(?:-\s*)?branch:\s*(.+?)\s*$", re.MULTILINE)
# The `worktree:` line follows the same accreted shapes as `branch:` (bare,
# list-item, backtick-wrapped), so parse it the same way. The open-pr command
# needs it to locate the feature checkout it pushes from.
_WORKTREE_LINE_RE = re.compile(r"^\s*(?:-\s*)?worktree:\s*(.+?)\s*$", re.MULTILINE)


def _delimited_value(raw: str) -> str:
    """Normalize one captured `## Dev` line value.

    A leading backtick delimits the value through its matching closing
    backtick, which is what lets a caller append a trailing annotation
    (``branch: `name` (Magicator repo)``). An unmatched backtick falls back to
    whole-line stripping, so a half-written line still yields something usable.
    Shared by the `pr:` / `branch:` / `worktree:` parsers so the three fields
    cannot drift apart on the next edit.
    """
    value = raw.strip()
    closing_tick = value.find("`", 1) if value.startswith("`") else -1
    if closing_tick >= 0:
        return value[1:closing_tick].strip()
    return value.strip("`").strip()


def parse_pr_url(blackboard_text: str) -> str | None:
    """Return the `pr:` URL under `## Dev`, or None if absent.

    Normalizes like `parse_branch_name` via `_delimited_value`, then keeps only
    the first whitespace-delimited token, since a URL never contains
    whitespace — so a trailing annotation (`pr: <url> (no CI configured)`)
    still yields the bare URL. Returns None for a missing, empty, or
    placeholder value.

    Scans *every* `pr:` line rather than only the first. The old anchored regex
    simply failed to match a placeholder line and kept searching; rejecting it
    in the guard instead would strand a ticket that records `pr: (not opened
    yet)` and later appends the real link below it — the same silent skip this
    parser exists to prevent.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    for match in _PR_LINE_RE.finditer(section.group(1)):
        tokens = _delimited_value(match.group(1)).split()
        if tokens and _looks_like_pr_url(tokens[0]):
            return tokens[0]
    return None


def _looks_like_pr_url(value: str) -> bool:
    """Whether a `pr:` capture is a link rather than a placeholder.

    `parse_worktree_path` rejects placeholders the same way, but here the stakes
    are higher: the old `$`-anchored regex rejected `pr: (not opened yet)` and
    `pr: none - blocked on CI` by accident, and without a guard those captures
    reach `gh pr view`, whose `GhError` aborts the *whole* autoclose sweep with
    exit 2 instead of skipping one ticket. Require the documented full PR URL
    shape: downstream consumers also need its `/pull/<n>` component.
    """
    if not value or value.startswith("("):
        return False
    return parse_pr_number(value) is not None


def parse_branch_name(blackboard_text: str) -> str | None:
    """Return the normalized `branch:` name under `## Dev`, or None if absent.

    Normalizes the inconsistent shapes the convention has accreted: tolerates a
    leading "- " list prefix. A leading backtick delimits the value through the
    next backtick, allowing trailing annotations; an unmatched backtick falls
    back to whole-line normalization. Bare values still consume the entire line.
    Returns None for a missing or empty branch line.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    match = _BRANCH_LINE_RE.search(section.group(1))
    if not match:
        return None
    return _delimited_value(match.group(1)) or None


def parse_worktree_path(blackboard_text: str) -> str | None:
    """Return the normalized `worktree:` path under `## Dev`, or None if absent.

    Mirrors `parse_branch_name`'s normalization: a leading backtick delimits the
    value through the next backtick, while bare values and unmatched backticks
    retain whole-line handling so paths with spaces remain valid. Returns None
    for a missing or empty worktree line, or a placeholder like
    `(not yet created)`.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if not section:
        return None
    match = _WORKTREE_LINE_RE.search(section.group(1))
    if not match:
        return None
    path = _delimited_value(match.group(1))
    if not path or path.startswith("("):
        return None
    return path


def parse_pr_number(url: str) -> int | None:
    m = _PR_NUMBER_RE.search(url)
    return int(m.group(1)) if m else None


def pr_state(url: str) -> str:
    """Query `gh` for the PR's state. Raises GhError on any failure.

    Returns the raw state string ("MERGED", "CLOSED", "OPEN").
    """
    data = pr_view(url, "state")
    return str(data.get("state", ""))


def pr_head(url: str) -> tuple[str, str]:
    """Return the PR's ``(head branch, head commit)`` from GitHub.

    Cleanup callers use the exact head commit to prove a branch has not been
    reused or advanced since the recorded PR merged. Missing fields are an
    error: treating an incomplete response as authorization would make a stale
    ``pr:`` line destructive.
    """
    data = pr_view(url, "headRefName,headRefOid")
    branch = str(data.get("headRefName", "")).strip()
    oid = str(data.get("headRefOid", "")).strip()
    if not branch or not oid:
        raise GhError(
            f"`gh pr view {url}` returned no complete headRefName/headRefOid"
        )
    return branch, oid


def prs_for_head(branch: str, state: str) -> list[dict[str, object]]:
    """Return GitHub PRs for one head branch and state.

    Branch retirement and the repository-wide branch sweep share this lookup:
    neither may dispose of a branch while another PR still has that head.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                state,
                "--json",
                "number,headRefOid",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhError("`gh` not found on PATH") from exc
    if result.returncode != 0:
        raise GhError(
            f"`gh pr list --head {branch} --state {state}` failed "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(f"`gh pr list --head {branch}` returned non-JSON: {exc}") from exc
    if not isinstance(data, list):
        raise GhError(f"`gh pr list --head {branch}` returned unexpected JSON")
    return [item for item in data if isinstance(item, dict)]


def pr_view(url: str, fields: str) -> dict[str, object]:
    """Query selected JSON fields for one PR, normalizing CLI failures."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", url, "--json", fields],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhError("`gh` not found on PATH") from exc
    if result.returncode != 0:
        raise GhError(
            f"`gh pr view {url}` failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(f"`gh pr view {url}` returned non-JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GhError(f"`gh pr view {url}` returned unexpected JSON")
    return data


def _on_final_step(ticket: Ticket) -> bool:
    wf = ticket.workflow
    if not isinstance(wf, dict) or not wf.get("steps"):
        # Autoclose can finish a workflow-less linked-PR ticket even though the
        # manual `coga bump` command deliberately refuses tickets with no steps.
        return True
    steps = wf["steps"]
    idx = ticket.step_index()
    return idx is not None and idx >= len(steps)


def _candidate(ticket: Ticket) -> bool:
    return ticket.status in OPEN_STATUSES and _on_final_step(ticket)


def _try_bump_one(
    cfg: Config,
    ref: TaskRef,
    *,
    quiet: bool,
    on_closed: Callable[[ClosedTicket], None],
    before_close: Callable[[ClosedTicket], None] | None = None,
    on_open: Callable[[], None] | None = None,
) -> ClosedTicket | None:
    """Check `ref`; bump to done iff its linked PR has merged.

    Returns the closed ticket (with its recorded checkout state) iff the ticket
    was bumped, else None. Always raises `GhError` on `gh` failure — callers
    decide whether to swallow or surface. `on_open` fires for every readable
    open ticket, before the final-step filter, so a caller can count what was
    considered and not only what was closed.
    """
    try:
        ticket = read_ticket(ref)
    except TicketError:
        return None
    if ticket.status in OPEN_STATUSES and on_open is not None:
        on_open()
    if not _candidate(ticket):
        return None

    # One read serves all three `## Dev` lines: `pr:` decides whether to close,
    # `branch:`/`worktree:` become the retire follow-up reported afterwards.
    blackboard = _read_dev_blackboard(ref.ticket_path)
    url = parse_pr_url(blackboard) if blackboard is not None else None
    if not url:
        return None

    state = pr_state(url)
    if state != "MERGED":
        return None

    # Re-read in case a concurrent caller (other hook, status, manual
    # bump) already handled this ticket. Mark_done is the gate.
    try:
        ticket = read_ticket(ref)
    except TicketError:
        return None
    if not _candidate(ticket):
        return None

    number = parse_pr_number(url)
    pr_label = f"PR #{number}" if number is not None else "the linked PR"
    pr_link = f"<{url}|{pr_label}>"
    actor = f"human:{cfg.current_user}"
    # A workflow-less ticket has no current step, so collapse the transition.
    prev = ticket.current_step()
    transition = f": {prev['name']} → done" if prev else " finished"
    slack_text = (
        f"🎉 *{ref.id_slug}* \"{ticket.title}\"{transition} — {pr_link} merged"
    )
    log_message = f"auto-bumped on merge of {pr_label} → done"
    echo = None if quiet else f"{ref.id_slug}: done (auto, {pr_label})"

    closed = ClosedTicket(
        slug=ref.id_slug,
        title=ticket.title,
        branch=parse_branch_name(blackboard),
        worktree=parse_worktree_path(blackboard),
        pr=url,
    )
    if before_close is not None:
        before_close(closed)

    try:
        mark_done(
            cfg,
            ref,
            ticket,
            actor=actor,
            log_message=log_message,
            slack_text=slack_text,
            image_url=cfg.gif_for("done"),
            echo=echo,
        )
    except BaseException:
        # `mark_done` writes the terminal state before validation, notification,
        # and git publication. If one of those later operations fails, retain
        # the successful local closure so the recipe can still name its retire
        # follow-up before surfacing the original failure. Checking both the
        # mutated in-memory ticket and disk avoids attributing a concurrent
        # completion to this sweep when a pre-write gate failed.
        if ticket.status == "done":
            try:
                persisted = read_ticket(ref)
            except TicketError:
                persisted = None
            if persisted is not None and persisted.status == "done":
                on_closed(closed)
        raise

    on_closed(closed)
    return closed


def _sweep_merged_into(
    cfg: Config,
    result: AutocloseResult,
    *,
    quiet: bool,
    before_close: Callable[[ClosedTicket], None] | None = None,
) -> None:
    """Populate ``result`` while walking candidates.

    The recipe owns ``result`` outside this call so closures already committed
    to disk remain reportable if a later ticket fails. Public callers use
    ``sweep_merged`` below, which preserves the ordinary return-value API.
    """

    def _note_open() -> None:
        result.scanned += 1

    for ref in list_tasks(cfg):
        try:
            _try_bump_one(
                cfg,
                ref,
                quiet=quiet,
                on_closed=result.closed.append,
                before_close=before_close,
                on_open=_note_open,
            )
        except GhError:
            if quiet:
                # Quiet callers use this as a best-effort check; the recurring
                # sweep runs loud so gh failures surface.
                return
            raise


def sweep_merged(
    cfg: Config,
    *,
    quiet: bool = False,
    result: AutocloseResult | None = None,
    before_close: Callable[[ClosedTicket], None] | None = None,
) -> AutocloseResult:
    """Walk active/in-progress tickets; finish those whose linked PR has merged.

    Returns what the run closed, including each ticket's recorded checkout
    state — the recipe turns that into the `coga retire` follow-up report.

    `quiet=True` suppresses stdout echoes and swallows `GhError` (gh missing or
    unauthed). The recurring sweep skill sets `quiet=False` so a missing `gh`
    surfaces as a real failure. Its recipe also supplies the accumulator and
    pre-close hook: retaining the accumulator outside this call lets it report
    closures committed before a later exception.
    """
    if result is None:
        result = AutocloseResult()
    _sweep_merged_into(
        cfg,
        result,
        quiet=quiet,
        before_close=before_close,
    )
    return result


def _append_blackboard_report(
    cfg: Config,
    blackboard: Path,
    report: str,
) -> None:
    """Atomically append one report within a task's blackboard region.

    Read/replace uses the ticket primitive's byte compare-and-swap so a
    concurrent frontmatter or blackboard writer wins loudly instead of being
    overwritten. The ticket's existing newline convention is retained.
    """
    append_blackboard_report(cfg, blackboard, report)


def _preflight_recipe_notifications(cfg: Config, closed: ClosedTicket) -> None:
    """Fail before closing: every close posts a live per-ticket Done line.

    Checkout debt additionally produces the live sweep summary. Both use the
    default notification destination.
    """
    del closed
    preflight_post(cfg)


def _dispose_checkouts(cfg: Config, result: AutocloseResult) -> None:
    """Dispose of every checkout this run closed and every open worklist entry.

    Runs after the sweep, from the control branch only: a hand-run `coga run
    autoclose` on a feature checkout preserves everything and says so, because
    the claim scan reads that checkout's tickets and the branch proofs its refs.
    Under `coga recurring` the runner services deterministic phases from a
    checkout on the control branch (`recurring_runner`), so the guard is met.

    Candidates in order: the tickets closed this run, then the open entries of
    every `retires.md` — the backlog earlier runs named and nobody retired,
    including entries whose ticket retire already deleted. Each goes through
    `checkout_disposal.dispose_checkout`, the same claim → worktree → local →
    remote proofs `coga retire` runs; whatever a proof refuses stays with its
    reason. The sweep only ever touches worktrees a ticket or an entry
    recorded, and `branchcleanup._is_linked_worktree_of` preserves anything
    that is not a linked worktree of the checkout the sweep runs from.
    """
    # Imported lazily: `branchcleanup` imports the `## Dev` parsers and `gh`
    # lookups from this module at load time, so a top-level import of the
    # disposal module here would form an
    # `autoclose -> checkout_disposal -> branchcleanup -> autoclose` cycle.
    from coga.checkout_disposal import dispose_checkout

    stranded = [item for item in result.closed if item.branch or item.worktree]
    worklists = all_worklists(cfg)
    if not stranded and not worklists:
        # A quiet day with no backlog: nothing to judge, so no git probes.
        return
    if not cfg.git_enabled:
        result.disposal_skipped = "[git].enabled = false"
        return
    root = _worklist_root(cfg)
    if root is None:
        result.disposal_skipped = f"{cfg.repo_root} is not inside a git checkout"
        return
    try:
        current = git.current_branch(root)
    except git.GitError as exc:
        result.disposal_skipped = f"could not read the checked-out branch ({exc})"
        return
    if current != cfg.git_control_branch:
        result.disposal_skipped = (
            f"checkout is on {current!r}, not the control branch "
            f"{cfg.git_control_branch!r}"
        )
        return

    def _echo(slug: str) -> Callable[[str], None]:
        return lambda message: sys.stdout.write(f"[autoclose] {slug}: {message}\n")

    seen: set[str] = set()
    for closed in stranded:
        seen.add(closed.slug)
        result.checkouts.append(
            CheckoutOutcome(
                slug=closed.slug,
                title=closed.title,
                branch=closed.branch,
                worktree=closed.worktree,
                ticket_exists=True,
                disposal=dispose_checkout(
                    cfg,
                    root,
                    branch=closed.branch,
                    worktree=closed.worktree,
                    pr_url=closed.pr,
                    echo=_echo(closed.slug),
                ),
            )
        )

    for path in worklists:
        try:
            _, entries = parse_worklist(path.read_text(encoding="utf-8"))
        except (RetireWorklistError, OSError, UnicodeError) as exc:
            # The reconcile below fails the run loudly over the same file;
            # here it only means its backlog is not walked this time.
            sys.stderr.write(f"[autoclose] backlog in {path} not walked: {exc}\n")
            continue
        for entry in entries:
            if entry.slug in seen:
                continue
            seen.add(entry.slug)
            ticket_exists, pr_url = _entry_ticket(cfg, entry.slug)
            result.checkouts.append(
                CheckoutOutcome(
                    slug=entry.slug,
                    title=None,
                    branch=entry.branch or None,
                    worktree=entry.worktree or None,
                    ticket_exists=ticket_exists,
                    disposal=dispose_checkout(
                        cfg,
                        root,
                        branch=entry.branch or None,
                        worktree=entry.worktree or None,
                        pr_url=pr_url,
                        echo=_echo(entry.slug),
                    ),
                )
            )


def _entry_ticket(cfg: Config, slug: str) -> tuple[bool, str | None]:
    """Whether a worklist entry's ticket still exists, and its `pr:` link if so.

    Exact `id_slug` match only: the CLI's unique-prefix resolution would let a
    deleted `foo` resolve to a newer `foo-followup` and borrow its `pr:`.
    """
    ref = next((t for t in list_tasks(cfg) if t.id_slug == slug), None)
    if ref is None:
        return False, None
    blackboard = _read_dev_blackboard(ref.ticket_path)
    return True, parse_pr_url(blackboard) if blackboard is not None else None


def render_retire_report(
    *,
    generated_at: str,
    task_slug: str | None,
    checkouts: list[CheckoutOutcome],
    pending: list[ClosedTicket] = (),
    skipped: str | None = None,
    worklist: Path | None = None,
) -> str:
    """Render the report of what the disposal phase did to each recorded checkout.

    Only called when there is something to say: a checkout disposed of or
    preserved this run, or — when the phase never ran (`skipped`) — a closed
    ticket in `pending` whose checkout is therefore still on disk. This is the
    *per-run* surface — a task blackboard or stdout — so a quiet day writes
    nothing. Under a recurring period task it names the durable `worklist` the
    preserved entries were recorded in, because the period task itself is
    deleted at the next period boundary.
    """
    lines = [RETIRE_REPORT_HEADING, "", f"Generated: {generated_at}"]
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.append("")
    if skipped is not None:
        lines.append(
            f"Checkout disposal skipped ({skipped}) — every recorded checkout "
            "was preserved."
        )
        for item in pending:
            lines.append(
                f'- `{item.slug}` "{item.title}": {item.checkout_state} — '
                f"`{item.retire_command}`"
            )
    disposed = [item for item in checkouts if item.disposed]
    preserved = [item for item in checkouts if not item.disposed]
    if disposed:
        lines.append(
            f"{len(disposed)} checkout(s) disposed of under the shared retire "
            "proofs (worktree removed, local and remote branch deleted where "
            "each proof admitted it):"
        )
        lines.append("")
        lines.extend(f"- {_report_label(item)}: {item.checkout_state}" for item in disposed)
        lines.append("")
    if preserved:
        lines.append(
            f"{len(preserved)} checkout(s) preserved — a proof refused; each "
            "stays on the worklist until a human acts:"
        )
        lines.append("")
        for item in preserved:
            lines.append(
                f"- {_report_label(item)}: {item.checkout_state} — "
                f"{item.disposal.reason} ({item.manual_command})"
            )
            lines.extend(f"  - {note}" for note in item.disposal.notes)
        lines.append("")
    if worklist is not None:
        lines.append(
            f"Recorded in the durable worklist `{worklist}`; this period "
            "task is deleted at the next period boundary."
        )
    return "\n".join(lines).rstrip("\n") + "\n"


def _report_label(item: CheckoutOutcome) -> str:
    if item.title is not None:
        return f'`{item.slug}` "{item.title}"'
    suffix = "" if item.ticket_exists else ", ticket already deleted"
    return f"`{item.slug}` (worklist backlog{suffix})"


def _worklist_line(change: WorklistChange) -> str:
    """One stdout line describing what the reconcile did to the worklist."""
    parts = [f"{len(change.open)} open"]
    if change.added:
        parts.append(f"{len(change.added)} recorded")
    if change.refreshed:
        parts.append(f"{len(change.refreshed)} refreshed")
    if change.dropped:
        dropped = ", ".join(f"`{entry.slug}`" for entry in change.dropped)
        parts.append(f"{len(change.dropped)} discharged ({dropped})")
    return f"[autoclose] retire worklist {change.path}: {', '.join(parts)}\n"


def render_disposed_summary(disposed: list[CheckoutOutcome]) -> str:
    """The trailing coga-flow line for a sweep that disposed of checkouts."""
    subject = "1 feature checkout" if len(disposed) == 1 else f"{len(disposed)} feature checkouts"
    names = ", ".join(f"`{item.slug}`" for item in disposed)
    return f"🧹 Autoclose disposed of {subject} (worktree and branch): {names}"


def render_preserved_summary(preserved: list[CheckoutOutcome]) -> str:
    """The coga-important line naming each preserved checkout and why.

    Every preserved checkout is work a human must do — the proofs will refuse
    it again tomorrow — which is the `coga/important` bar; a preserved entry
    is re-posted on every run until it is gone.
    """
    subject = (
        "1 feature checkout needs"
        if len(preserved) == 1
        else f"{len(preserved)} feature checkouts need"
    )
    details = "; ".join(
        f"`{item.slug}` ({item.checkout_state}): {item.disposal.reason}"
        for item in preserved
    )
    return f"⚠️ {subject} a human — autoclose could not dispose of it: {details}"


def render_retire_summary(pending: list[ClosedTicket]) -> str:
    """The trailing Slack line when the disposal phase never ran."""
    subject = (
        "1 auto-closed ticket still has"
        if len(pending) == 1
        else f"{len(pending)} auto-closed tickets still have"
    )
    commands = ", ".join(f"`{item.retire_command}`" for item in pending)
    return f"🧹 {subject} a feature checkout: {commands}"


def _worklist_root(cfg: Config) -> Path | None:
    """The git root a worklist entry's relative `worktree:` resolves against.

    `None` when the checkout is not a git repository; the discharge rule then
    keeps every entry it cannot judge without one — a relative worktree, or any
    recorded branch — the fail-closed reading of debt the worklist exists for.
    """
    try:
        return git.toplevel(cfg.repo_root)
    except git.GitError:
        return None


def _report_retire_followups(cfg: Config, result: AutocloseResult) -> bool:
    """Report what the disposal phase did and record what it could not.

    Two per-run surfaces, both silent when the run touched no checkout: the
    run report (the task blackboard when run under a task, stdout otherwise),
    and the Slack lines for the whole sweep — one on coga-flow for what was
    disposed of, one on coga-important for what a proof refused, since a
    preserved checkout is work a human must do. Under a recurring period task
    there is a third, durable surface: the template's `retires.md` worklist,
    where this run's preserved closures are recorded because the period task's
    own blackboard is deleted at the next period boundary. Every existing
    worklist is reconciled on every run, hand-run or recurring, so entries the
    disposal phase just cleared are dropped (see `coga.retire_worklist`).

    The per-ticket `🎉 ... merged` line is deliberately left alone. It
    announces a lifecycle event, while a disposal summary is operational. Both
    summaries are plain live `post`s rather than `notify` outcomes: the
    `notify` kinds are per-ticket outcomes, which a sweep-level summary is not.

    Returns False when a durable worklist or the task report cannot be written.
    Expected I/O and encoding failures are reported on stderr; a failed task
    report falls back to stdout before the live summaries are attempted. The
    tickets are already `done` on disk, so these reporting failures must not
    erase their follow-ups or mask an earlier sweep error.
    """
    pending = result.retire_pending
    # Scoped to the root this sweep actually walked, so an inherited blackboard
    # from another checkout falls back to stdout — and, below, never selects
    # another checkout's recurring template as the durable home.
    blackboard = blackboard_from_env(cfg.repo_root)
    activity = bool(pending or result.checkouts)
    if not activity and blackboard is None and not all_worklists(cfg):
        # Nothing touched, no task this run could own a worklist for, and no
        # backlog file to reconcile.
        return True
    now = datetime.now(timezone.utc)
    worklist = worklist_for_period_task(cfg, blackboard)
    failure: RetireWorklistError | OSError | UnicodeError | None = None
    root = _worklist_root(cfg)
    # The durable half: record this run's preserved closures keyed by slug
    # under the period task's own template, and drop the entries the disposal
    # phase (or `coga retire`, or the branch sweep) has since discharged from
    # every worklist. Runs on every sweep, so a quiet day still prunes.
    for path in sorted({*all_worklists(cfg), *([worklist] if worklist else [])}):
        try:
            change = reconcile_worklist(
                cfg,
                path,
                root=root,
                pending=[
                    RetireFollowUp(
                        slug=item.slug,
                        branch=item.branch or "",
                        worktree=item.worktree or "",
                        recorded=now.date().isoformat(),
                    )
                    for item in pending
                ]
                if path == worklist
                else (),
            )
        except (RetireWorklistError, OSError, UnicodeError) as exc:
            # The closures are already on disk; a worklist this run cannot
            # safely rewrite is a loud failure of the run, not a swallowed
            # warning — but the per-run surfaces below still get written.
            failure = exc
            sys.stderr.write(f"[autoclose] {exc}\n")
        else:
            if change.written or change.open:
                sys.stdout.write(_worklist_line(change))
    if not activity:
        return failure is None

    report = render_retire_report(
        generated_at=now.isoformat(timespec="seconds"),
        task_slug=os.environ.get("COGA_TASK_SLUG"),
        checkouts=result.checkouts,
        pending=pending,
        skipped=result.disposal_skipped,
        # A report must not claim a durable record the reconcile refused.
        worklist=None if failure is not None or not pending else worklist,
    )
    if blackboard:
        try:
            _append_blackboard_report(cfg, blackboard, report)
        except (OSError, UnicodeError) as exc:
            # Disk exhaustion can affect both durable files. Keep the commands
            # visible on stdout and still attempt the live summary.
            failure = exc
            sys.stderr.write(
                f"[autoclose] could not write retire report to {blackboard}: {exc}\n"
            )
            sys.stdout.write(report)
    else:
        sys.stdout.write(report)

    task_path = (
        blackboard.parent
        if blackboard is not None and blackboard.name == "ticket.md"
        else blackboard
    )
    summaries: list[tuple[str, bool]] = []
    if result.disposal_skipped is not None and pending:
        summaries.append((render_retire_summary(pending), False))
    if result.disposed:
        summaries.append((render_disposed_summary(result.disposed), False))
    if result.preserved:
        summaries.append((render_preserved_summary(result.preserved), True))
    for text, important in summaries:
        post(
            cfg,
            text,
            task_path=task_path,
            important=important,
            # The tickets are already `done` on disk and the report is already
            # emitted; an undeliverable hint must not fail the recurring run. A
            # task-scoped run supplies its validated task path above, so the
            # miss is also durable in the repo-global audit log.
            fatal=False,
        )
    return failure is None


def run_autoclose_recipe(
    cfg: Config, argv: list[str], *, result: AutocloseResult | None = None
) -> int:
    """Run the recurring autoclose job through the fixed recipe surface.

    `result` is the optional out-parameter described on `run_recipe`: the
    accumulator this wrapper already keeps outside `sweep_merged` becomes the
    caller's when one is supplied, so a caller that wants to name what the
    sweep closed reads `.closed` / `.retire_pending` / `.checkouts` instead of
    diffing ticket status globally — which cannot tell this sweep's closures
    from a concurrent `coga mark done`. `.scanned` is the matching denominator,
    counted in the walk the sweep already makes.
    """
    if argv:
        sys.stderr.write(
            f"autoclose: unexpected arguments: {' '.join(repr(arg) for arg in argv)}\n"
        )
        return 2
    # Defaulted here, not left to `sweep_merged`: the exception handlers below
    # read `result`, so this frame needs the accumulator the sweep is filling
    # in. `sweep_merged` returns that same object, so its return value is
    # deliberately not rebound onto `result` — a caller's `result=` stays the
    # object being reported on even if the sweep ever returns a different one.
    if result is None:
        result = AutocloseResult()
    try:
        sweep_merged(
            cfg,
            quiet=False,
            result=result,
            before_close=lambda closed: _preflight_recipe_notifications(
                cfg, closed
            ),
        )
    except (GhError, TaskValidationError) as exc:
        result.disposal_skipped = "the sweep failed before checkout disposal ran"
        _report_retire_followups(cfg, result)
        sys.stderr.write(f"[autoclose] {exc}\n")
        return 2
    except BaseException:
        result.disposal_skipped = "the sweep failed before checkout disposal ran"
        _report_retire_followups(cfg, result)
        raise
    if not result.closed:
        sys.stdout.write("[autoclose] no tickets bumped.\n")
    _dispose_checkouts(cfg, result)
    if result.disposal_skipped is not None:
        sys.stdout.write(
            f"[autoclose] checkout disposal skipped ({result.disposal_skipped}) "
            "— every recorded checkout preserved.\n"
        )
    return 0 if _report_retire_followups(cfg, result) else 2


def _read_dev_blackboard(ticket: Path) -> str | None:
    """The blackboard region holding `## Dev`, or None when unreadable."""
    if not ticket.is_file():
        return None
    try:
        # The `## Dev` section lives in the blackboard region below the fence.
        return read_blackboard(ticket, blackboard_required=False)
    except (OSError, TaskFileError) as exc:
        # A read error on a single ticket shouldn't sink the scanner.
        sys.stderr.write(f"[autoclose] could not read {ticket}: {exc}\n")
        return None


__all__ = [
    "AutocloseResult",
    "CheckoutOutcome",
    "ClosedTicket",
    "GhError",
    "RETIRE_REPORT_HEADING",
    "render_retire_report",
    "render_retire_summary",
    "render_disposed_summary",
    "render_preserved_summary",
    "run_autoclose_recipe",
    "sweep_merged",
    "parse_pr_number",
    "parse_pr_url",
    "parse_branch_name",
    "parse_worktree_path",
    "pr_head",
    "pr_view",
    "pr_state",
    "prs_for_head",
]
