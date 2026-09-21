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

Closing a ticket does not dispose of its feature checkout: that is `coga
retire`, which owns the linked-worktree / open-PR / landed-branch safety
proofs. Autoclose stays non-destructive and instead *names* the follow-up —
see `_report_retire_followups`. Duplicating retire's proofs here would either
copy that machinery or ship a weaker version of it, and implicit destruction
cuts against the principle that destructive behavior is never implicit.

Naming the follow-up does mean naming one that can run: a recorded `worktree:`
may belong to another repository, which `coga retire` cannot dispose of from
either side, so `locate_checkout` judges each checkout with retire's own
ownership proof before the line is rendered (see `CheckoutHome`).

Under a recurring period task the name has to outlive the run: the period task
is deleted at the next period boundary, so the sweep also records each
follow-up in the template's durable `retires.md` (`coga.retire_worklist`) and
drops the entries already discharged. That reconcile runs on every recurring
sweep, closed tickets or not, so the worklist stays a worklist.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from coga import git
from coga.blackboard import append_blackboard_report
from coga.mark import mark_done
from coga.config import Config
from coga.notification import post, preflight_post
from coga.retire_worklist import (
    RetireFollowUp,
    RetireWorklistError,
    WorklistChange,
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


class GhError(Exception):
    """Raised when `gh` is missing, unauthed, or returns a non-zero exit."""


RETIRE_REPORT_HEADING = "## Autoclose Sweep: retire follow-ups"


CheckoutKind = Literal["same", "other", "gone", "preserved", "unknown"]


@dataclass(frozen=True)
class CheckoutHome:
    """What `coga retire <slug>` would do with a closed ticket's `worktree:`.

    The sweep names a follow-up command, so it has to name one that runs.
    `coga retire` resolves the task in the *current* repo and its worktree
    proof (`branchcleanup.remove_ticket_worktree`) requires a linked worktree
    of that same repository — a Coga workspace can track work whose code lives
    elsewhere, and for such a checkout no `coga retire` invocation from either
    side disposes of it. `locate_checkout` judges the recorded path with the
    same proof (`git.worktree_relation`) and only the static, read-only part of
    it: retire's dirt, lock, and PR gates can change between sweep and retire
    and are left to retire.

    - `same` — a linked worktree of the ticket repo with a `branch:` recorded:
      the one case the plain command disposes of it;
    - `other` — a linked worktree of a different repository, whose main
      checkout is `owner`;
    - `gone` — the recorded path is no longer a directory;
    - `preserved` — retire will leave it in place for `reason` (not a git
      worktree, this repository's own checkout, an independent clone, a
      symlink, no `branch:` recorded);
    - `unknown` — nothing was judged: no `worktree:` recorded, or the ticket
      repo is not a git repository, so the rendered line is the plain one.

    `path` is the resolved directory judged, the one any by-hand command names.
    """

    kind: CheckoutKind
    path: Path | None = None
    owner: Path | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ClosedTicket:
    """One ticket a sweep finished, plus the checkout state it left behind.

    `branch` / `worktree` are the `## Dev` lines as they read at close time.
    They are captured *during* the sweep on purpose: they are the only trace of
    which checkout belongs to this ticket, and a later reader may find them
    gone — retire clears them, and a deleted task takes them with it. `home`
    is `locate_checkout`'s verdict on that worktree, attached before the
    report is rendered.
    """

    slug: str
    title: str
    branch: str | None
    worktree: str | None
    home: CheckoutHome = CheckoutHome("unknown")

    @property
    def retire_command(self) -> str:
        return f"coga retire {self.slug}"

    @property
    def checkout_state(self) -> str:
        """What is still on disk, rendered for the report line."""
        parts = []
        if self.worktree:
            parts.append(f"worktree `{self.worktree}`")
        if self.branch:
            parts.append(f"branch `{self.branch}`")
        return ", ".join(parts)


def locate_checkout(root: Path | None, item: ClosedTicket) -> CheckoutHome:
    """Judge `item`'s recorded `worktree:` the way `coga retire` will.

    `root` is the ticket repository's git working-tree root (`None` when there
    is none). A relative path resolves against `root`, as retire and the
    worklist discharge rule do. Read-only: a few `git rev-parse` calls, no
    network.
    """
    if not item.worktree or root is None:
        return CheckoutHome("unknown")
    path = Path(item.worktree).expanduser()
    if not path.is_absolute():
        path = root / path
    home = git.worktree_relation(root, path)
    if home is None:
        return CheckoutHome("unknown")
    relation = git.WorktreeRelation
    if home.relation is relation.MISSING:
        return CheckoutHome("gone", path=home.path)
    if not item.branch:
        reason = (
            "no `branch:` is recorded, so retire cannot prove which checkout "
            "it belongs to"
        )
    elif path.is_symlink():
        reason = "the recorded path is a symlink"
    elif home.path == root.resolve():
        reason = "it is the checkout retire runs from"
    elif home.relation is relation.LINKED_OTHER_REPO:
        return CheckoutHome("other", path=home.path, owner=home.owner)
    elif home.relation is relation.LINKED_SAME_REPO:
        return CheckoutHome("same", path=home.path)
    elif home.relation is relation.NOT_A_REPO:
        reason = "it is not a git worktree"
    elif home.relation is relation.PRIMARY_SAME_REPO:
        reason = "it is this repository's own checkout, not a linked worktree"
    else:
        reason = (
            f"it is an independent checkout owned by `{home.owner}`, not a "
            "linked worktree of this repository"
        )
    return CheckoutHome("preserved", path=home.path, owner=home.owner, reason=reason)


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

    @property
    def retire_pending(self) -> list[ClosedTicket]:
        """Closed tickets whose feature checkout or branch outlived them."""
        return [item for item in self.closed if item.branch or item.worktree]


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


def render_retire_report(
    *,
    generated_at: str,
    task_slug: str | None,
    pending: list[ClosedTicket],
    worklist: Path | None = None,
) -> str:
    """Render the report naming each closed ticket's `coga retire` command.

    Only called with a non-empty `pending`: a sweep that stranded nothing has
    nothing to report. This is the *per-run* surface — a task blackboard or
    stdout — so a daily no-op line would only grow it without bound. Under a
    recurring period task it names the durable `worklist` the same entries
    were recorded in, because the period task itself is deleted at the next
    period boundary. Each line's follow-up is rendered from the ticket's
    `home` — see `_followup_line`.
    """
    lines = [RETIRE_REPORT_HEADING, "", f"Generated: {generated_at}"]
    if task_slug:
        lines.append(f"Task: `{task_slug}`")
    lines.extend(
        [
            "",
            f"{len(pending)} auto-closed ticket(s) still have a recorded "
            "feature checkout. Autoclose never removes one — `coga retire` "
            "owns the worktree and branch safety proofs:",
            "",
        ]
    )
    for item in pending:
        lines.append(
            f'- `{item.slug}` "{item.title}": {item.checkout_state} — '
            f"{_followup_line(item)}"
        )
    if worklist is not None:
        lines.extend(
            [
                "",
                f"Recorded in the durable worklist `{worklist}`; this period "
                "task is deleted at the next period boundary.",
            ]
        )
    return "\n".join(lines) + "\n"


def _followup_line(item: ClosedTicket) -> str:
    """The follow-up text after the em dash of one report line.

    Only the same-repo case (and the unjudged one) gets the bare command.
    Every other kind says what retire will do instead and names the cleanup
    that does resolve it, so a run nobody reads closely never leaves a
    command that silently fails.
    """
    home = item.home
    match home.kind:
        case "other":
            owner = home.owner
            steps = [f"`git -C {owner} worktree remove {home.path}`"]
            if item.branch:
                steps.append(f"`git -C {owner} branch -d {item.branch}`")
            return (
                f"the worktree belongs to `{owner}`, not this repository: "
                f"`{item.retire_command}` from here fails its same-repo "
                "worktree proof and leaves it in place, and the task does not "
                f"exist there. Dispose of it by hand from `{owner}`: "
                f"{', then '.join(steps)}."
            )
        case "gone":
            if not item.branch:
                return (
                    "the worktree is no longer on disk and no branch is "
                    f"recorded; `{item.retire_command}` has only the stale "
                    "`## Dev` record to clear."
                )
            return (
                f"the worktree is no longer on disk; `{item.retire_command}` "
                f"reports it already gone and disposes of branch "
                f"`{item.branch}` only, if this repository holds it (if "
                "`git worktree list` still names the path as prunable, "
                "`git worktree prune` first)."
            )
        case "preserved":
            branch = (
                f" and disposes of branch `{item.branch}` only"
                if item.branch
                else ""
            )
            return (
                f"`{item.retire_command}` leaves `{home.path}` in place "
                f"({home.reason}){branch}. Inspect and remove the directory "
                "by hand."
            )
        case _:
            return f"`{item.retire_command}`"


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


def render_retire_summary(pending: list[ClosedTicket]) -> str:
    """Render the single trailing Slack line for a whole sweep.

    A cross-repo checkout is the one kind whose command cannot run from any
    checkout, so the summary names its owner instead; every other kind keeps
    the command and the report carries the detail.
    """
    subject = (
        "1 auto-closed ticket still has"
        if len(pending) == 1
        else f"{len(pending)} auto-closed tickets still have"
    )
    parts = []
    for item in pending:
        if item.home.kind == "other":
            parts.append(
                f"`{item.slug}` (worktree owned by `{item.home.owner}` — clean "
                "up by hand there)"
            )
        else:
            parts.append(f"`{item.retire_command}`")
    return f"🧹 {subject} a feature checkout: {', '.join(parts)}"


def _worklist_root(cfg: Config) -> Path | None:
    """The git root a worklist entry's relative `worktree:` resolves against.

    `None` when the checkout is not a git repository; the discharge rule then
    keeps every entry it cannot judge without one — a relative worktree, or any
    recorded branch — the fail-closed reading of debt the worklist exists for.
    """
    try:
        return git._toplevel(cfg.repo_root)
    except git.GitError:
        return None


def _report_retire_followups(cfg: Config, result: AutocloseResult) -> bool:
    """Name the `coga retire` follow-up for the tickets this sweep stranded.

    Two per-run surfaces, both silent when the sweep left nothing behind: the
    run report (the task blackboard when run under a task, stdout otherwise),
    and one trailing Slack line for the whole sweep. Under a recurring period
    task there is a third, durable one: the template's `retires.md` worklist,
    reconciled on every run because the period task's own blackboard is
    deleted at the next period boundary (see `coga.retire_worklist`).

    The per-ticket `🎉 ... merged` line is deliberately left alone. It
    announces a lifecycle event, while a retire hint is an operational to-do
    with a different audience — repeating it on every Done line turns the
    outcome feed into a command list and buries the action item. This summary
    is a plain live `post` rather than a `notify` outcome: the `notify` kinds
    are per-ticket outcomes, which a sweep-level summary is not.

    Returns False when the durable worklist or task report cannot be written.
    Expected I/O and encoding failures are reported on stderr; a failed task
    report falls back to stdout before the live summary is attempted. The
    tickets are already `done` on disk, so these reporting failures must not
    erase their follow-ups or mask an earlier sweep error.
    """
    pending = result.retire_pending
    # Scoped to the root this sweep actually walked, so an inherited blackboard
    # from another checkout falls back to stdout — and, below, never selects
    # another checkout's recurring template as the durable home.
    blackboard = blackboard_from_env(cfg.repo_root)
    if not pending and blackboard is None:
        # Nothing stranded and no task this run could own a worklist for.
        return True
    now = datetime.now(timezone.utc)
    worklist = worklist_for_period_task(cfg, blackboard)
    root = _worklist_root(cfg)
    failure: RetireWorklistError | OSError | UnicodeError | None = None
    if worklist is not None:
        # The durable half: record this run's follow-ups keyed by slug and drop
        # the ones `coga retire` (or the branch sweep) has since discharged.
        # Runs on every recurring sweep, so a quiet day still prunes.
        try:
            change = reconcile_worklist(
                cfg,
                worklist,
                root=root,
                pending=[
                    RetireFollowUp(
                        slug=item.slug,
                        branch=item.branch or "",
                        worktree=item.worktree or "",
                        recorded=now.date().isoformat(),
                    )
                    for item in pending
                ],
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
    if not pending:
        return failure is None

    pending = [replace(item, home=locate_checkout(root, item)) for item in pending]
    report = render_retire_report(
        generated_at=now.isoformat(timespec="seconds"),
        task_slug=os.environ.get("COGA_TASK_SLUG"),
        pending=pending,
        # A report must not claim a durable record the reconcile refused.
        worklist=None if failure is not None else worklist,
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

    post(
        cfg,
        render_retire_summary(pending),
        task_path=(
            blackboard.parent
            if blackboard is not None and blackboard.name == "ticket.md"
            else blackboard
        ),
        # The tickets are already `done` on disk and the report is already
        # emitted; an undeliverable hint must not fail the recurring run. A
        # task-scoped run supplies its validated task path above, so the miss
        # is also durable in the repo-global audit log.
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
    sweep closed reads `.closed` / `.retire_pending` instead of diffing ticket
    status globally — which cannot tell this sweep's closures from a concurrent
    `coga mark done`. `.scanned` is the matching denominator, counted in the
    walk the sweep already makes.
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
        _report_retire_followups(cfg, result)
        sys.stderr.write(f"[autoclose] {exc}\n")
        return 2
    except BaseException:
        _report_retire_followups(cfg, result)
        raise
    if not result.closed:
        sys.stdout.write("[autoclose] no tickets bumped.\n")
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
    "CheckoutHome",
    "ClosedTicket",
    "GhError",
    "RETIRE_REPORT_HEADING",
    "locate_checkout",
    "render_retire_report",
    "render_retire_summary",
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
