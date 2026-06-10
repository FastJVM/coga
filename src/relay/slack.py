"""Slack webhook poster — relay's sync point with humans.

Slack is required by default for multi-user coordination: agents and CLI
commands post here so teammates see state changes as they happen. A silent
FYI becomes a stale mental model on the human side, so failures crash
loudly rather than degrade.

`post` is the **live** path for urgent events (`relay panic`, script-step
failures, the manual `relay slack` FYI). It has three branches:
  - `slack_enabled = False` (opt-out via `[slack].enabled = false` in
    `relay.local.toml`) — every call writes to stderr, never crashes. The
    cost is being out of the sync loop.
  - `enabled` + no webhook — crash with a message pointing the user at
    `[slack].webhook` and the opt-out.
  - `enabled` + webhook — POST. On any RequestException, append to the
    task's `log.md` (when `task_path` is given) and crash so the caller
    sees the failure.

`notify` is the **batchable** path for routine state-change chatter (create,
bump, mark active/paused/done, retire, automerge done, recurring scaffolds).
When the daily-digest recurring ticket is installed (`recurring/digest/`
exists), `notify` spools a structured record to that ticket's blackboard
instead of posting; the spool is rendered and posted once a day by
`relay digest` (see `render_digest`). When the digest ticket is *not*
installed, `notify` degrades to a live `post`, so a repo without the digest
keeps today's real-time behavior — the two-tier model is opt-in by installing
the ticket.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import requests
import typer

from relay import spool
from relay.config import Config
from relay.logfile import append_log
from relay.paths import recurring_dir


def _mention(cfg: Config, name: str) -> str:
    """Render `name` as a Slack ping when its member ID is mapped.

    `[slack.users]` in `relay.toml` maps a relay name to a Slack member ID.
    Slack only fires a notification for the `<@U…>` mention form, so a
    mapped name becomes `<@U…>`; an unmapped one stays plain text (named,
    but not pinged). An incoming webhook can't resolve an ID itself — that's
    why the table has to be supplied.
    """
    user_id = cfg.slack_users.get(name)
    return f"<@{user_id}>" if user_id else name


def post(
    cfg: Config,
    message: str,
    *,
    task_path: Path | None = None,
    owner: str | None = None,
    watchers: list[str] | None = None,
    image_url: str | None = None,
) -> None:
    """Post a message to Slack, or crash trying.

    Every message is prefixed with `[<project>]` so a Slack channel shared
    across multiple relay repos stays disambiguated. When `owner` is given,
    `[<owner>]` follows — that's the human accountable for the ticket, so
    teammates can tell whose agent (e.g. `claude`) just acted when several
    teammates share an agent nickname. Owner and watchers render as real
    `<@ID>` pings for any name mapped in `[slack.users]` (see `_mention`).

    `watchers`, if given, are cc'd in a trailer — but only those with a
    mapped member ID, since cc'ing a plain name notifies no one and is just
    noise.

    `image_url`, if given, attaches a single image (GIF or PNG) below the
    text via Slack's `attachments` field — used for milestone events
    (done, panic) so they pop visually in a high-volume feed.

    See module docstring for the three branches and why we crash.
    """
    prefix = f"[{cfg.project_name}]"
    if owner:
        prefix += f" [{_mention(cfg, owner)}]"
    full_message = f"{prefix} {message}"
    if watchers:
        cc = [f"<@{cfg.slack_users[w]}>" for w in watchers if w in cfg.slack_users]
        if cc:
            full_message += f" (cc {' '.join(cc)})"

    if not cfg.slack_enabled:
        sys.stderr.write(f"[slack] disabled (post suppressed): {full_message}\n")
        return

    if not cfg.slack_webhook:
        sys.stderr.write(
            "[slack] no webhook configured. Set [slack].webhook in relay.toml "
            '(e.g. webhook = "env:SLACK_WEBHOOK_URL", then export SLACK_WEBHOOK_URL), '
            "or opt out with [slack].enabled = false in relay.local.toml.\n"
        )
        raise typer.Exit(1)

    payload: dict[str, object] = {"text": full_message}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "fallback": full_message}]

    try:
        requests.post(
            cfg.slack_webhook,
            json=payload,
            timeout=5,
        )
    except requests.RequestException as exc:
        sys.stderr.write(f"[slack] post failed: {exc}. Message was: {full_message}\n")
        if task_path is not None:
            append_log(task_path, "slack", f"post failed: {type(exc).__name__}: {exc}")
        raise typer.Exit(1)


# --- digest (batchable) path --------------------------------------------------

DIGEST_RECURRING_NAME = "digest"


def digest_spool_path(cfg: Config) -> Path | None:
    """The digest ticket's spool blackboard, or None when it isn't installed.

    The spool lives on the `recurring/digest/` ticket's own persistent
    `blackboard.md` — a real, git-tracked, human-readable file (never a hidden
    dotfile). Its presence is what switches `notify` from live posting to
    batching, so a repo opts into the daily digest simply by installing the
    ticket.
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
    """Route a batchable state-change event: spool it, or post live.

    When the digest ticket is installed, append a structured JSONL record to
    its spool (grouped and posted later by `relay digest`). Otherwise fall back
    to a live `post(slack_text)` — identical to pre-digest behavior, so
    `image_url` and the `[project] [owner]` formatting still apply on that path.

    `kind` is a short event tag (e.g. `bump`, `done`, `recurring`); `detail` is
    the human one-liner shown under the ticket in the digest. `ticket`/`owner`
    drive the digest's project → person → ticket grouping; a record with no
    `owner` (e.g. a recurring-scan error summary) renders in an ownerless
    bucket.
    """
    # A `relay recurring --all` debug run (and any child it spawns) is
    # disposable scratch that must never reach Slack or the digest spool —
    # `--all` is documented not to broadcast. The state change is still in the
    # task's own `log.md` (every command appends there before calling notify),
    # so dropping it here loses no audit trail, only the noise. Deferred import
    # keeps slack ↔ config ↔ recurring free of an import cycle.
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


def render_digest(cfg: Config, records: list[dict], *, date_label: str) -> str:
    """Render spooled records into one channel message, project → person → ticket.

    Owner names render through `_mention` (a `<@ID>` ping when mapped, plain
    text otherwise); per-ticket watcher cc's follow the same `[slack.users]`
    rule `post` uses. Events under each ticket appear in spool (chronological)
    order, so the digest is a once-a-day replay rather than only a final
    snapshot. Records with no `ticket` (e.g. a recurring-scan error) list as
    standalone lines under their owner, or under an ownerless bucket.

    The returned text has no `[<project>]` prefix — `relay digest` hands it to
    `post`, which adds the channel-disambiguating prefix exactly as it does for
    a live event.
    """
    by_project: dict[str, list[dict]] = {}
    for rec in records:
        by_project.setdefault(rec.get("project") or cfg.project_name, []).append(rec)

    lines: list[str] = [f"📋 Daily digest · {date_label}"]
    for project in sorted(by_project):
        if len(by_project) > 1:
            lines.append("")
            lines.append(f"=== {project} ===")
        lines.extend(_render_people(cfg, by_project[project]))
    return "\n".join(lines)


def _render_people(cfg: Config, records: list[dict]) -> list[str]:
    # Group by owner, preserving first-seen order; ownerless records last.
    owners: list[str | None] = []
    by_owner: dict[str | None, list[dict]] = {}
    for rec in records:
        owner = rec.get("owner")
        if owner not in by_owner:
            by_owner[owner] = []
            owners.append(owner)
    for rec in records:
        by_owner[rec.get("owner")].append(rec)
    # Stable sort: keep first-seen (chronological) order, just push the
    # ownerless bucket (None) last.
    owners.sort(key=lambda o: o is None)

    out: list[str] = []
    for owner in owners:
        out.append("")
        out.append(_mention(cfg, owner) if owner else "(no owner)")
        out.extend(_render_tickets(cfg, by_owner[owner]))
    return out


def _render_tickets(cfg: Config, records: list[dict]) -> list[str]:
    tickets: list[str | None] = []
    by_ticket: dict[str | None, list[dict]] = {}
    for rec in records:
        slug = rec.get("ticket")
        if slug not in by_ticket:
            by_ticket[slug] = []
            tickets.append(slug)
        by_ticket[slug].append(rec)

    out: list[str] = []
    for slug in tickets:
        group = by_ticket[slug]
        cc = _cc_trailer(cfg, group)
        if slug is None:
            # Ownerless / ticketless lines (e.g. recurring-scan errors).
            for rec in group:
                out.append(f" • {rec.get('detail', '')}")
            continue
        out.append(f" • {slug}{cc}")
        for rec in group:
            out.append(f"     {rec.get('detail', '')}")
    return out


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
    "digest_spool_path",
    "DIGEST_RECURRING_NAME",
]
