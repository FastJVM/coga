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

`notify` is the **outcome digest** path, not a generic lifecycle broadcaster.
Only ticket outcomes (`done`) and recurring scan errors enter the daily digest.
Routine lifecycle churn (draft, active, bump, paused, retire, recurring
scaffold) is intentionally silent: the task `log.md` remains the audit trail,
while Slack carries outcomes and urgent exceptions. When the daily-digest
recurring ticket is installed (`recurring/digest/` exists), `notify` spools a
structured record to that ticket's blackboard; when it is absent, those same
outcome/error events fall back to a live `post`.
"""

from __future__ import annotations

import re
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
        raise ValueError(f"slack.notify only accepts digest outcome kinds: {allowed}")

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
    for rec in records:
        by_owner[rec.get("owner")].append(rec)
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
]
