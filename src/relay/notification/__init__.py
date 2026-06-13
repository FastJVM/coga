"""Notification dispatch and digest helpers.

Relay notifications are the sync point between asynchronous agents and the
humans approving, unblocking, or watching their work. Slack is the first
backend behind this channel-agnostic surface.

`post` is the **live** path for urgent events (`relay panic`, script-step
failures, the manual `relay slack` FYI). It selects the configured
notification channel(s) and dispatches through their backend implementation.
Slack preserves the previous crash-loud/no-retry semantics.

`notify` is the **outcome digest** path, not a generic lifecycle broadcaster.
Only ticket outcomes (`done`) and recurring scan errors enter the daily digest.
Routine lifecycle churn (draft, active, bump, paused, retire, recurring
scaffold) is intentionally silent: the task `log.md` remains the audit trail,
while notifications carry outcomes and urgent exceptions. When the daily-digest
recurring ticket is installed (`recurring/digest/` exists), `notify` spools a
structured record to that ticket's blackboard; when it is absent, those same
outcome/error events fall back to a live `post`.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

from relay import spool
from relay.config import Config
from relay.notification.slack import SlackChannel, mention as _mention
from relay.paths import recurring_dir


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


def digest_spool_path(cfg: Config) -> Path | None:
    """The digest ticket's spool blackboard, or None when it isn't installed.

    The spool lives on the `recurring/digest/` ticket's own persistent
    `blackboard.md` — a real, git-tracked, human-readable file (never a hidden
    dotfile). Its presence is what routes outcome/error `notify` records into
    the daily digest instead of posting them live.
    """
    path = recurring_dir(cfg) / DIGEST_RECURRING_NAME / "blackboard.md"
    return path if path.is_file() else None


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
    its spool (rendered and posted later by `relay digest`). Otherwise fall back
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

    # A `relay recurring --all` debug run (and any child it spawns) is
    # disposable scratch that must never reach notifications or the digest
    # spool —
    # `--all` is documented not to broadcast. The state change is still in the
    # task's own `log.md` (every command appends there before calling notify),
    # so dropping it here loses no audit trail, only the noise. Deferred import
    # keeps notification ↔ config ↔ recurring free of an import cycle.
    if ticket is not None:
        from relay.recurring import is_debug_slug

        if is_debug_slug(ticket):
            return

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

    The returned text has no `[<project>]` prefix — `relay digest` hands it to
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
    "digest_spool_path",
    "DIGEST_RECURRING_NAME",
    "DIGEST_EVENT_KINDS",
    "SlackChannel",
]
