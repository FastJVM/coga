"""Notification dispatch and digest helpers.

Coga notifications are the sync point between asynchronous agents and the
humans approving, unblocking, or watching their work. Slack is the first
backend behind this channel-agnostic surface.

`post` is the **live** path for urgent events (`coga panic`, script-step
failures, the manual `coga slack` FYI). It selects the configured
notification channel(s) and dispatches through their backend implementation.
Slack preserves the previous crash-loud/no-retry semantics.

`notify` is the **outcome digest** path, not a generic lifecycle broadcaster.
Only ticket outcomes (`done`) and recurring scan errors enter the daily digest.
Routine lifecycle churn (draft, active, bump, paused, retire, recurring
create) is intentionally silent: the repo-global `coga-os/log.md` remains the audit trail,
while notifications carry outcomes and urgent exceptions. When the daily-digest
recurring ticket is installed (`recurring/digest/spool.md` exists, or an older
`recurring/digest/ticket.md` is present and can be migrated), `notify` spools a
structured record to that dedicated, `merge=union` spool file; when it is
absent, those same outcome/error events fall back to a live `post`.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

from coga import spool
from coga.atomicio import atomic_write_text
from coga.config import Config
from coga.notification.slack import SlackChannel, mention as _mention
from coga.paths import recurring_dir


def _channels(cfg: Config) -> list[SlackChannel]:
    channels: list[SlackChannel] = []
    for name in cfg.notification_channels:
        if name == SlackChannel.name:
            channels.append(SlackChannel(cfg))
    return channels


def post(
    cfg: Config,
    message: str,
    *,
    task_path: Path | None = None,
    owner: str | None = None,
    watchers: list[str] | None = None,
    image_url: str | None = None,
) -> None:
    """Post a live notification through every configured channel."""
    channels = _channels(cfg)
    if not channels:
        sys.stderr.write(f"[notification] no channels configured: {message}\n")
        return
    for channel in channels:
        channel.send(
            message,
            task_path=task_path,
            owner=owner,
            watchers=watchers,
            image_url=image_url,
        )


# --- digest (outcome) path ----------------------------------------------------

DIGEST_RECURRING_NAME = "digest"
DIGEST_EVENT_KINDS = {"done", "recurring-error"}
_DETAIL_PR_RE = re.compile(r"PR #(\d+)")
_SLACK_PR_LINK_RE = re.compile(r"<[^>|]+?\|PR #\d+>")
_DIGEST_SPOOL_SEED = """# Daily digest spool

Producer/consumer queue for `coga digest`. Producers append one JSONL record
at the **bottom** of `## Spool (pending)`; the single consumer (`coga digest`)
advances the `consumed_through:` watermark to the newest record and trims the
consumed prefix, always keeping the newest record in place as an *anchor*.

This file is marked `merge=union` (`.gitattributes`) so two clones appending
concurrently merge without conflict. Together with the top-trim/bottom-append
shape (deletes and appends sit in disjoint hunks separated by the anchor), that
makes the spool mergeable by construction with no lock — see the `coga/sync`
context. The git high-water mark lives separately in the digest ticket's
`### Digest State`, not here.

## Spool (pending)

consumed_through:
"""


def digest_spool_path(cfg: Config) -> Path | None:
    """The dedicated digest spool file, or None when it isn't installed.

    The spool lives in `recurring/digest/spool.md` — a standalone, git-tracked,
    `merge=union` file (never a hidden dotfile), kept *separate* from the
    digest ticket so concurrent producer appends merge by union without ever
    touching the ticket's YAML frontmatter. Its presence is what routes
    outcome/error `notify` records into the daily digest instead of posting them
    live. `coga.spool` operates on this file's `## Spool (pending)` section.

    Existing repos may have the digest ticket but not the newer sibling
    `spool.md` yet. Treat that as an installed digest and create the dedicated
    file from the legacy ticket's old spool section so outcomes keep batching
    instead of silently falling back to live posts until `coga init --update`.
    """
    digest_dir = recurring_dir(cfg) / DIGEST_RECURRING_NAME
    path = digest_dir / "spool.md"
    if path.is_file():
        return path
    legacy_ticket = digest_dir / "ticket.md"
    if not legacy_ticket.is_file():
        return None
    _migrate_legacy_digest_spool(path, legacy_ticket)
    return path if path.is_file() else None


def _migrate_legacy_digest_spool(path: Path, legacy_ticket: Path) -> None:
    """Create `spool.md` for an older digest ticket installation.

    Older repos stored the pending JSONL lines in the digest ticket's blackboard.
    Copy any still-unconsumed records into the new dedicated spool, stamping ids
    as needed. The old ticket section is left untouched; once `spool.md` exists,
    all new producers and the consumer ignore the legacy section.
    """
    if path.exists():
        return
    records = spool.read_unconsumed(legacy_ticket)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, _DIGEST_SPOOL_SEED)
    for record in records:
        spool.append_record(path, record)


def digest_state_path(cfg: Config) -> Path:
    """The digest ticket holding `### Digest State` (the git high-water mark).

    Kept in the ticket (not the union-merged spool file): the high-water mark is
    single-writer consumer state that should not ride union semantics. Returned
    unconditionally — callers guard on `is_file()` — so the path resolves even
    before the recurring ticket is materialized.
    """
    return recurring_dir(cfg) / DIGEST_RECURRING_NAME / "ticket.md"


def dedupe_records(records: list[dict]) -> list[dict]:
    """Drop duplicate spool records, preserving first-seen order.

    Two clones that independently recorded the same event each stamp a distinct
    random `id`, so id alone can't collapse them; the de-dup key is the content
    tuple `(project, kind, ticket, detail)` (deliberately excluding `ts`, which
    the two clones capture seconds apart). That key also subsumes an exact line
    duplicated by a `merge=union` resolution. `id` is kept as a fast exact-dup
    guard for records that carry no distinguishing content.
    """
    seen_ids: set[str] = set()
    seen_keys: set[tuple] = set()
    out: list[dict] = []
    for rec in records:
        rid = rec.get("id")
        key = (
            rec.get("project"),
            rec.get("kind"),
            rec.get("ticket"),
            rec.get("detail"),
        )
        if (rid is not None and rid in seen_ids) or key in seen_keys:
            continue
        if rid is not None:
            seen_ids.add(rid)
        seen_keys.add(key)
        out.append(rec)
    return out


def notify(
    cfg: Config,
    slack_text: str,
    *,
    kind: str,
    detail: str,
    ticket: str | None = None,
    owner: str | None = None,
    watchers: list[str] | None = None,
    task_path: Path | None = None,
    image_url: str | None = None,
) -> None:
    """Route an outcome/error event: spool it, or post live.

    Only `done` and `recurring-error` belong here. Other lifecycle transitions
    are intentionally silent and should not call this helper.

    When the digest ticket is installed, append a structured JSONL record to
    its spool (rendered and posted later by `coga digest`). Otherwise fall back
    to a live `post(slack_text)`, so `image_url` and the `[project] [owner]`
    formatting still apply on that path.

    `kind` is the event tag; `detail` is the human one-liner shown in the
    digest. `ticket`/`owner` drive the Done grouping; a record with no `ticket`
    (for example a recurring-scan error summary) renders in its own section.
    """
    if kind not in DIGEST_EVENT_KINDS:
        allowed = ", ".join(sorted(DIGEST_EVENT_KINDS))
        raise ValueError(
            f"notification.notify only accepts digest outcome kinds: {allowed}"
        )

    spool_path = digest_spool_path(cfg)
    if spool_path is None:
        post(
            cfg,
            slack_text,
            task_path=task_path,
            owner=owner,
            watchers=watchers,
            image_url=image_url,
        )
        return

    record = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "project": cfg.project_name,
        "kind": kind,
        "detail": detail,
    }
    if ticket:
        record["ticket"] = ticket
    if owner:
        record["owner"] = owner
    if watchers:
        record["watchers"] = list(watchers)
    spool.append_record(spool_path, record)


def done_pr_numbers(records: list[dict]) -> set[int]:
    """PR numbers already represented by spooled Done records."""
    numbers: set[int] = set()
    for rec in records:
        if rec.get("kind") != "done":
            continue
        detail = str(rec.get("detail") or "")
        numbers.update(int(match.group(1)) for match in _DETAIL_PR_RE.finditer(detail))
    return numbers


def render_digest(
    cfg: Config,
    records: list[dict],
    *,
    date_label: str,
    also_merged: list[dict] | None = None,
) -> str:
    """Render one outcome-focused daily digest message.

    The digest is no longer a chronological replay. It lists Done tickets,
    grouped by owner, then commits that reached the control branch without
    matching one of those Done PRs. Recurring scan errors stay visible because
    they represent skipped scheduled work.

    The returned text has no `[<project>]` prefix — `coga digest` hands it to
    `post`, which adds the channel-disambiguating prefix exactly as it does for
    a live event.
    """
    done_records = [rec for rec in records if rec.get("kind") == "done"]
    error_records = [rec for rec in records if rec.get("kind") == "recurring-error"]
    merged = also_merged or []

    lines: list[str] = [f"📋 Daily digest · {date_label} · {cfg.project_name}"]
    if done_records:
        lines.append("Done:")
        lines.extend(_render_done_people(cfg, done_records))
    if merged:
        if len(lines) > 1:
            lines.append("")
        lines.append("Also merged (no ticket):")
        for commit in merged:
            sha = str(commit.get("sha") or "")[:7]
            subject = str(commit.get("subject") or "").strip()
            lines.append(f" • {sha} {subject}".rstrip())
    if error_records:
        if len(lines) > 1:
            lines.append("")
        lines.append("Recurring errors:")
        for rec in error_records:
            lines.append(f" • {rec.get('detail', '')}")
    return "\n".join(lines)


def _render_done_people(cfg: Config, records: list[dict]) -> list[str]:
    # Group by owner, preserving first-seen order; ownerless records last.
    owners: list[str | None] = []
    by_owner: dict[str | None, list[dict]] = {}
    for rec in records:
        owner = rec.get("owner")
        if owner not in by_owner:
            by_owner[owner] = []
            owners.append(owner)
        by_owner[owner].append(rec)
    # Stable sort: keep first-seen (chronological) order, just push the
    # ownerless bucket (None) last.
    owners.sort(key=lambda o: o is None)

    out: list[str] = []
    for owner in owners:
        out.append(_mention(cfg, owner) if owner else "(no owner)")
        for rec in by_owner[owner]:
            out.append(_render_done_record(cfg, rec))
    return out


def _render_done_record(cfg: Config, rec: dict) -> str:
    slug = rec.get("ticket") or "(no ticket)"
    cc = _cc_trailer(cfg, [rec])
    detail = str(rec.get("detail") or "").strip()
    pr_label = _done_pr_label(detail)
    if pr_label:
        return f" • {slug}{cc} — {pr_label} merged ✅"
    return f" • {slug}{cc} — {_clean_done_detail(detail)}"


def _done_pr_label(detail: str) -> str | None:
    link = _SLACK_PR_LINK_RE.search(detail)
    if link:
        return link.group(0)
    match = _DETAIL_PR_RE.search(detail)
    if match:
        return f"PR #{match.group(1)}"
    return None


def _clean_done_detail(detail: str) -> str:
    if not detail:
        return "done"
    return detail.removeprefix("→ ").strip()


def _cc_trailer(cfg: Config, records: list[dict]) -> str:
    """`(cc <@…> …)` for the union of mapped watchers across a ticket's events."""
    seen: list[str] = []
    for rec in records:
        for w in rec.get("watchers") or []:
            if w in cfg.slack_users and w not in seen:
                seen.append(w)
    if not seen:
        return ""
    return " (cc " + " ".join(f"<@{cfg.slack_users[w]}>" for w in seen) + ")"


__all__ = [
    "post",
    "notify",
    "render_digest",
    "done_pr_numbers",
    "dedupe_records",
    "digest_spool_path",
    "digest_state_path",
    "DIGEST_RECURRING_NAME",
    "DIGEST_EVENT_KINDS",
    "SlackChannel",
]
