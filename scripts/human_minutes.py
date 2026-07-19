#!/usr/bin/env python3
"""Recompute human-attention and machine-token ledgers from public records.

The default invocation reads ``coga/log.md``, discovers tickets under
``coga/tasks/``, and uses ``gh`` for the PRs recorded under each ticket's
``## Dev`` blackboard section::

    python scripts/human_minutes.py \
        --since 2026-08-03 --until 2026-08-16 \
        --timezone America/Los_Angeles

Use ``--json`` for the machine-readable form. ``--no-github`` is an explicit
offline/log-only escape hatch; the default fails loud when a recorded PR cannot
be read, because silently dropping server-held events would undercount the
published claim.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "America/Los_Angeles"
DEFAULT_GAP_MINUTES = 10.0
DEFAULT_FLOOR_MINUTES = 2.0
SENSITIVITY_FLOOR_MINUTES = 5.0
AUTO_COMMIT_PREFIXES = ("Sync coga state", "Log:", "Ticket:")

_LOG_RE = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) "
    r"\[(?P<task>[^\]]+)\] \[(?P<actor>[^\]]+)\] (?P<message>.*)$"
)
_DEV_SECTION_RE = re.compile(
    r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL
)
_PR_LINE_RE = re.compile(r"^\s*(?:-\s*)?pr:\s*(\S+)\s*$", re.MULTILINE)
_BRANCH_LINE_RE = re.compile(
    r"^\s*(?:-\s*)?branch:\s*(.+?)\s*$", re.MULTILINE
)
_ARTIFACT_LINE_RE = re.compile(
    r"^\s*(?:-\s*)?artifact:\s*(\S+)\s*$", re.MULTILINE
)
_PR_URL_RE = re.compile(
    r"https://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/pull/(?P<number>\d+)"
)
_PROGRESS_RE = re.compile(
    r"\b(?:advanced to step|bumped to step|task done|activated\b|started\b|unblocked\b)",
    re.IGNORECASE,
)
_BLOCKER_ANSWER_RE = re.compile(r"\bunblocked\b.*?:\s*(.+)$", re.IGNORECASE)


class MetricsError(RuntimeError):
    """An input or external-source failure that would make the ledger partial."""


@dataclass(frozen=True)
class Event:
    timestamp: datetime
    task: str
    source: str
    action: str
    link: str | None = None
    event_id: str | None = None


@dataclass(frozen=True)
class Episode:
    start: datetime
    end: datetime
    events: tuple[Event, ...]

    def minutes(self, floor_minutes: float) -> float:
        observed = max(0.0, (self.end - self.start).total_seconds() / 60.0)
        if len(self.events) == 1:
            return floor_minutes
        return observed


@dataclass(frozen=True)
class BlockerAnswer:
    timestamp: datetime
    task: str
    answer: str
    link: str | None


@dataclass(frozen=True)
class ProgressEvent:
    timestamp: datetime
    task: str


@dataclass(frozen=True)
class AttemptEvent:
    timestamp: datetime
    task: str


@dataclass
class LogData:
    events: list[Event]
    blockers: list[BlockerAnswer]
    progress: list[ProgressEvent]
    attempts: list[AttemptEvent]
    usage_records: list[dict[str, Any]]
    human_identities: set[str]
    pr_urls: dict[str, str]


@dataclass(frozen=True)
class TaskInfo:
    slug: str
    path: Path | None
    pr_url: str | None = None
    branch: str | None = None
    artifact: str | None = None
    humans: tuple[str, ...] = ()


class IdentityMatcher:
    """Match git/GitHub identities to the humans named in public Coga state."""

    def __init__(self, identities: Iterable[str]) -> None:
        tokens: set[str] = set()
        for identity in identities:
            tokens.update(_identity_tokens(identity))
        self.tokens = tokens

    def matches_values(self, *values: object) -> bool:
        candidates: set[str] = set()
        for value in values:
            if isinstance(value, str):
                candidates.update(_identity_tokens(value))
        return bool(self.tokens & candidates)

    def matches_actor(self, actor: object) -> bool:
        if not isinstance(actor, dict) or _is_bot(actor):
            return False
        return self.matches_values(
            actor.get("login"), actor.get("name"), actor.get("email")
        )


def _identity_tokens(value: str) -> set[str]:
    normalized = value.strip().strip("@\"'").casefold()
    if not normalized or normalized in {"null", "none"}:
        return set()
    tokens = {normalized}
    if "@" in normalized:
        tokens.add(normalized.split("@", 1)[0])
    return tokens


def _is_bot(actor: dict[str, Any]) -> bool:
    if actor.get("is_bot") is True or actor.get("isBot") is True:
        return True
    if str(actor.get("type", "")).casefold() == "bot":
        return True
    login = str(actor.get("login", "")).casefold()
    return login.endswith("[bot]")


def parse_iso_timestamp(value: str, tz: ZoneInfo) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise MetricsError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def parse_window_bound(
    value: str | None, *, is_until: bool, tz: ZoneInfo
) -> datetime | None:
    if value is None:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            day = date.fromisoformat(value)
        except ValueError as exc:
            raise MetricsError(f"invalid date: {value!r}") from exc
        boundary = time.max if is_until else time.min
        return datetime.combine(day, boundary, tzinfo=tz)
    return parse_iso_timestamp(value, tz)


def in_window(
    timestamp: datetime, since: datetime | None, until: datetime | None
) -> bool:
    return (since is None or timestamp >= since) and (
        until is None or timestamp <= until
    )


def parse_log(path: Path, *, tz: ZoneInfo, log_web_url: str | None) -> LogData:
    if not path.is_file():
        raise MetricsError(f"log file not found: {path}")
    data = LogData([], [], [], [], [], set(), {})
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        raise MetricsError(f"cannot read log file {path}: {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        match = _LOG_RE.match(line)
        if not match:
            continue
        timestamp = datetime.strptime(
            match.group("stamp"), "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz)
        task = match.group("task")
        actor = match.group("actor")
        message = match.group("message")
        link = f"{log_web_url}#L{line_number}" if log_web_url else None

        if actor.startswith("human:"):
            human = actor.split(":", 1)[1]
            if human:
                data.human_identities.add(human)
            data.events.append(
                Event(
                    timestamp=timestamp,
                    task=task,
                    source="log",
                    action=message,
                    link=link,
                    event_id=f"log:{line_number}",
                )
            )
            answer_match = _BLOCKER_ANSWER_RE.search(message)
            if answer_match:
                data.blockers.append(
                    BlockerAnswer(
                        timestamp=timestamp,
                        task=task,
                        answer=answer_match.group(1).strip(),
                        link=link,
                    )
                )

        if _PROGRESS_RE.search(message):
            data.progress.append(ProgressEvent(timestamp=timestamp, task=task))
        if actor == "megalaunch" and re.search(
            r"\b(?:started|launched)\b", message, re.IGNORECASE
        ):
            data.attempts.append(AttemptEvent(timestamp=timestamp, task=task))

        pr_match = _PR_URL_RE.search(message)
        if pr_match:
            data.pr_urls[task] = pr_match.group(0)

        if actor == "system" and message.startswith("{"):
            try:
                record = json.loads(message)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(record, dict)
                and record.get("schema") in {1, 2}
                and isinstance(record.get("slug"), str)
                and "usage_status" in record
            ):
                data.usage_records.append(record)
    return data


def discover_tasks(tasks_dir: Path) -> dict[str, TaskInfo]:
    if not tasks_dir.is_dir():
        raise MetricsError(f"tasks directory not found: {tasks_dir}")
    discovered: dict[str, TaskInfo] = {}
    for path in _iter_ticket_paths(tasks_dir):
        info = parse_task(path, tasks_dir=tasks_dir)
        if info.slug in discovered:
            raise MetricsError(
                f"duplicate task ref {info.slug!r}: "
                f"{discovered[info.slug].path} and {path}"
            )
        discovered[info.slug] = info
    return discovered


def _iter_ticket_paths(directory: Path) -> Iterable[Path]:
    ticket = directory / "ticket.md"
    if ticket.is_file():
        yield ticket
        return
    for child in sorted(directory.iterdir()):
        if child.is_file() and child.suffix == ".md":
            yield child
    for child in sorted(directory.iterdir()):
        if child.is_dir():
            yield from _iter_ticket_paths(child)


def parse_task(path: Path, *, tasks_dir: Path) -> TaskInfo:
    try:
        text = path.read_text()
    except OSError as exc:
        raise MetricsError(f"cannot read task {path}: {exc}") from exc
    frontmatter = _frontmatter_scalars(text)
    relative = path.relative_to(tasks_dir)
    fallback_slug = (
        relative.parent.as_posix()
        if path.name == "ticket.md"
        else relative.with_suffix("").as_posix()
    )
    slug = frontmatter.get("slug") or fallback_slug
    dev_match = _DEV_SECTION_RE.search(text)
    dev = dev_match.group(1) if dev_match else ""
    pr_url = _parse_dev_url(_PR_LINE_RE, dev)
    artifact = _parse_dev_url(_ARTIFACT_LINE_RE, dev) or pr_url
    branch = _parse_branch(dev)
    humans = tuple(
        value
        for key in ("human", "owner")
        if (value := frontmatter.get(key))
    )
    return TaskInfo(
        slug=slug,
        path=path,
        pr_url=pr_url,
        branch=branch,
        artifact=artifact,
        humans=humans,
    )


def _frontmatter_scalars(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^(slug|human|owner):\s*(.*?)\s*$", line)
        if not match:
            continue
        value = match.group(2).strip().strip("\"'")
        if value and value not in {"null", "~"}:
            values[match.group(1)] = value
    return values


def _parse_dev_url(pattern: re.Pattern[str], section: str) -> str | None:
    match = pattern.search(section)
    if not match:
        return None
    value = match.group(1).strip().strip("`")
    return value or None


def _parse_branch(section: str) -> str | None:
    match = _BRANCH_LINE_RE.search(section)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw.startswith("`") and "`" in raw[1:]:
        raw = raw[1 : raw.find("`", 1)]
    else:
        raw = raw.split()[0] if raw else ""
    raw = raw.strip("`")
    if not raw or raw.startswith("("):
        return None
    return raw


class GithubClient:
    def __init__(
        self,
        *,
        fixture: dict[str, Any] | None = None,
        cwd: Path,
    ) -> None:
        self.fixture = fixture
        self.cwd = cwd

    @classmethod
    def from_path(cls, path: Path | None, *, cwd: Path) -> "GithubClient":
        if path is None:
            return cls(cwd=cwd)
        try:
            raw = json.loads(path.read_text())
        except OSError as exc:
            raise MetricsError(f"cannot read GitHub fixture {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise MetricsError(f"invalid GitHub fixture {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise MetricsError("GitHub fixture must be a JSON object keyed by PR URL")
        fixture = raw.get("pull_requests", raw)
        if not isinstance(fixture, dict):
            raise MetricsError("GitHub fixture pull_requests must be an object")
        return cls(fixture=fixture, cwd=cwd)

    def read_pr(self, url: str) -> dict[str, Any]:
        if self.fixture is not None:
            value = self.fixture.get(url)
            if not isinstance(value, dict):
                raise MetricsError(f"GitHub fixture has no object for recorded PR {url}")
            return value

        fields = ",".join(
            [
                "url",
                "number",
                "headRefName",
                "commits",
                "reviews",
                "comments",
                "mergedAt",
                "mergedBy",
                "author",
            ]
        )
        data = self._run_json(["gh", "pr", "view", url, "--json", fields])
        if not isinstance(data, dict):
            raise MetricsError(f"gh pr view {url} returned a non-object")
        match = _PR_URL_RE.fullmatch(url.rstrip("/"))
        review_comments: list[dict[str, Any]] = []
        if match:
            endpoint = (
                f"repos/{match.group('owner')}/{match.group('repo')}/pulls/"
                f"{match.group('number')}/comments"
            )
            raw_comments = self._run_json(
                ["gh", "api", "--paginate", "--slurp", endpoint]
            )
            review_comments = _flatten_gh_pages(raw_comments)
        data["reviewComments"] = review_comments
        return data

    def _run_json(self, argv: list[str]) -> Any:
        try:
            result = subprocess.run(
                argv,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise MetricsError(
                "`gh` not found on PATH; install/authenticate it or pass "
                "--no-github for an explicitly partial offline report"
            ) from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise MetricsError(
                f"{' '.join(argv[:4])} failed (exit {result.returncode}): {detail}"
            )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise MetricsError(
                f"{' '.join(argv[:4])} returned invalid JSON: {exc}"
            ) from exc


def _flatten_gh_pages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    flattened: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            flattened.append(item)
        elif isinstance(item, list):
            flattened.extend(entry for entry in item if isinstance(entry, dict))
    return flattened


def collect_external_events(
    task_infos: dict[str, TaskInfo],
    *,
    matcher: IdentityMatcher,
    tz: ZoneInfo,
    repo_root: Path,
    github: GithubClient | None,
    include_git: bool,
    include_github: bool,
    git_base: str,
    commit_web_root: str | None,
) -> tuple[list[Event], int]:
    events: list[Event] = []
    # A grouped branch/PR can legitimately cover more than one task. Keep one
    # commit event per associated task, then let per-day clustering deduplicate
    # the shared event id so human time is not double-counted.
    seen_commits: set[tuple[str, str]] = set()
    prs_read = 0

    for slug in sorted(task_infos):
        info = task_infos[slug]
        pr_data: dict[str, Any] | None = None
        if info.pr_url and github is not None:
            pr_data = github.read_pr(info.pr_url)
            prs_read += 1
            if include_git:
                events.extend(
                    _git_events_from_pr(
                        slug,
                        info.pr_url,
                        pr_data,
                        matcher=matcher,
                        tz=tz,
                        seen_commits=seen_commits,
                    )
                )
            if include_github:
                events.extend(
                    _github_events_from_pr(
                        slug,
                        info.pr_url,
                        pr_data,
                        matcher=matcher,
                        tz=tz,
                    )
                )

        if include_git and info.branch:
            events.extend(
                _local_branch_events(
                    slug,
                    info.branch,
                    matcher=matcher,
                    tz=tz,
                    repo_root=repo_root,
                    git_base=git_base,
                    commit_web_root=commit_web_root,
                    seen_commits=seen_commits,
                )
            )
    return events, prs_read


def _git_events_from_pr(
    slug: str,
    pr_url: str,
    data: dict[str, Any],
    *,
    matcher: IdentityMatcher,
    tz: ZoneInfo,
    seen_commits: set[tuple[str, str]],
) -> list[Event]:
    events: list[Event] = []
    commits = data.get("commits")
    if not isinstance(commits, list):
        return events
    repo_url = pr_url.split("/pull/", 1)[0]
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        oid = str(commit.get("oid") or "")
        commit_key = (slug, oid)
        if oid and commit_key in seen_commits:
            continue
        subject = str(commit.get("messageHeadline") or "")
        if subject.startswith(AUTO_COMMIT_PREFIXES):
            continue
        authors = commit.get("authors")
        if not isinstance(authors, list) or not any(
            matcher.matches_actor(author) for author in authors
        ):
            continue
        stamp = commit.get("committedDate") or commit.get("authoredDate")
        if not isinstance(stamp, str):
            continue
        if oid:
            seen_commits.add(commit_key)
        events.append(
            Event(
                timestamp=parse_iso_timestamp(stamp, tz),
                task=slug,
                source="git",
                action=subject or "git commit",
                link=f"{repo_url}/commit/{oid}" if oid else pr_url,
                event_id=f"git:{oid}" if oid else None,
            )
        )
    return events


def _github_events_from_pr(
    slug: str,
    pr_url: str,
    data: dict[str, Any],
    *,
    matcher: IdentityMatcher,
    tz: ZoneInfo,
) -> list[Event]:
    events: list[Event] = []
    for review in _dict_items(data.get("reviews")):
        actor = review.get("author") or review.get("user")
        stamp = review.get("submittedAt") or review.get("submitted_at")
        if not isinstance(stamp, str) or not matcher.matches_actor(actor):
            continue
        state = str(review.get("state") or "review").casefold()
        events.append(
            Event(
                parse_iso_timestamp(stamp, tz),
                slug,
                "github",
                f"PR review ({state})",
                _event_url(review, pr_url),
                _event_id("review", review),
            )
        )
    for comment in _dict_items(data.get("comments")):
        actor = comment.get("author") or comment.get("user")
        stamp = comment.get("createdAt") or comment.get("created_at")
        if not isinstance(stamp, str) or not matcher.matches_actor(actor):
            continue
        events.append(
            Event(
                parse_iso_timestamp(stamp, tz),
                slug,
                "github",
                "PR comment",
                _event_url(comment, pr_url),
                _event_id("comment", comment),
            )
        )
    for comment in _dict_items(data.get("reviewComments")):
        actor = comment.get("author") or comment.get("user")
        stamp = comment.get("createdAt") or comment.get("created_at")
        if not isinstance(stamp, str) or not matcher.matches_actor(actor):
            continue
        events.append(
            Event(
                parse_iso_timestamp(stamp, tz),
                slug,
                "github",
                "PR review comment",
                _event_url(comment, pr_url),
                _event_id("review-comment", comment),
            )
        )
    merged_at = data.get("mergedAt") or data.get("merged_at")
    merged_by = data.get("mergedBy") or data.get("merged_by")
    if isinstance(merged_at, str) and matcher.matches_actor(merged_by):
        events.append(
            Event(
                parse_iso_timestamp(merged_at, tz),
                slug,
                "github",
                "PR merged",
                pr_url,
                f"merge:{pr_url}",
            )
        )
    return events


def _dict_items(value: object) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        return (item for item in value if isinstance(item, dict))
    return ()


def _event_url(event: dict[str, Any], fallback: str) -> str:
    for key in ("url", "html_url"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    return fallback


def _event_id(prefix: str, event: dict[str, Any]) -> str | None:
    value = event.get("id") or event.get("databaseId")
    return f"{prefix}:{value}" if value is not None else None


def _local_branch_events(
    slug: str,
    branch: str,
    *,
    matcher: IdentityMatcher,
    tz: ZoneInfo,
    repo_root: Path,
    git_base: str,
    commit_web_root: str | None,
    seen_commits: set[tuple[str, str]],
) -> list[Event]:
    if not _git_ref_exists(repo_root, branch):
        return []
    argv = [
        "git",
        "log",
        branch,
        "--format=%H%x00%cI%x00%an%x00%ae%x00%s%x00%b%x1e",
    ]
    if _git_ref_exists(repo_root, git_base):
        argv.extend(["--not", git_base])
    result = _run_git(argv, repo_root, check=True)
    events: list[Event] = []
    for record in result.stdout.split("\x1e"):
        fields = record.strip("\n").split("\x00", 5)
        if len(fields) != 6:
            continue
        oid, stamp, author_name, author_email, subject, _body = fields
        commit_key = (slug, oid)
        if commit_key in seen_commits or subject.startswith(AUTO_COMMIT_PREFIXES):
            continue
        if not matcher.matches_values(author_name, author_email):
            continue
        seen_commits.add(commit_key)
        link = f"{commit_web_root}/commit/{oid}" if commit_web_root else None
        events.append(
            Event(
                parse_iso_timestamp(stamp, tz),
                slug,
                "git",
                subject or "git commit",
                link,
                f"git:{oid}",
            )
        )
    return events


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    result = _run_git(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        repo_root,
        check=False,
    )
    return result.returncode == 0


def _run_git(
    argv: list[str], repo_root: Path, *, check: bool
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise MetricsError("`git` not found on PATH") from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise MetricsError(
            f"{' '.join(argv[:3])} failed (exit {result.returncode}): {detail}"
        )
    return result


def cluster_events(events: Iterable[Event], *, gap_minutes: float) -> list[Episode]:
    ordered = sorted(_deduplicate_events(events), key=lambda event: event.timestamp)
    if not ordered:
        return []
    gap = timedelta(minutes=gap_minutes)
    groups: list[list[Event]] = [[ordered[0]]]
    for event in ordered[1:]:
        if event.timestamp - groups[-1][-1].timestamp > gap:
            groups.append([event])
        else:
            groups[-1].append(event)
    return [
        Episode(group[0].timestamp, group[-1].timestamp, tuple(group))
        for group in groups
    ]


def _deduplicate_events(events: Iterable[Event]) -> list[Event]:
    unique: list[Event] = []
    seen_ids: set[str] = set()
    for event in events:
        if event.event_id is not None:
            if event.event_id in seen_ids:
                continue
            seen_ids.add(event.event_id)
        unique.append(event)
    return unique


def episode_total(episodes: Iterable[Episode], *, floor_minutes: float) -> float:
    return sum(episode.minutes(floor_minutes) for episode in episodes)


def build_report(
    *,
    log_data: LogData,
    task_infos: dict[str, TaskInfo],
    external_events: list[Event],
    since: datetime | None,
    until: datetime | None,
    timezone_name: str,
    gap_minutes: float,
    floor_minutes: float,
    prs_read: int,
    identities: set[str],
    git_enabled: bool,
    github_enabled: bool,
) -> dict[str, Any]:
    events = [
        event
        for event in [*log_data.events, *external_events]
        if in_window(event.timestamp, since, until)
    ]
    blockers = [
        blocker
        for blocker in log_data.blockers
        if in_window(blocker.timestamp, since, until)
    ]
    progress = [
        item
        for item in log_data.progress
        if in_window(item.timestamp, since, until)
    ]
    attempts = [
        item
        for item in log_data.attempts
        if in_window(item.timestamp, since, until)
    ]

    by_task: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        by_task[event.task].append(event)
    included_tasks = set(by_task) | {attempt.task for attempt in attempts}
    task_rows: list[dict[str, Any]] = []
    sensitivity_tasks: list[dict[str, Any]] = []
    for task in sorted(included_tasks):
        episodes = cluster_events(by_task.get(task, []), gap_minutes=gap_minutes)
        info = task_infos.get(task)
        artifact = info.artifact if info else log_data.pr_urls.get(task)
        task_rows.append(
            {
                "task": task,
                "minutes": _rounded(
                    episode_total(episodes, floor_minutes=floor_minutes)
                ),
                "episodes": len(episodes),
                "events": len(by_task.get(task, [])),
                "artifact": artifact,
            }
        )
        sensitivity_tasks.append(
            {
                "task": task,
                "minutes": _rounded(
                    episode_total(
                        episodes, floor_minutes=SENSITIVITY_FLOOR_MINUTES
                    )
                ),
            }
        )

    events_by_day: dict[date, list[Event]] = defaultdict(list)
    blockers_by_day: dict[date, list[BlockerAnswer]] = defaultdict(list)
    progress_by_day: dict[date, set[str]] = defaultdict(set)
    for event in events:
        events_by_day[event.timestamp.date()].append(event)
    for blocker in blockers:
        blockers_by_day[blocker.timestamp.date()].append(blocker)
    for item in progress:
        progress_by_day[item.timestamp.date()].add(item.task)

    days = _report_days(
        since=since,
        until=until,
        observed=set(events_by_day) | set(blockers_by_day) | set(progress_by_day),
    )
    day_rows: list[dict[str, Any]] = []
    sensitivity_days: list[dict[str, Any]] = []
    for day in days:
        episodes = cluster_events(events_by_day.get(day, []), gap_minutes=gap_minutes)
        day_rows.append(
            {
                "date": day.isoformat(),
                "minutes": _rounded(
                    episode_total(episodes, floor_minutes=floor_minutes)
                ),
                "episodes": len(episodes),
                "blockers_answered": [
                    {
                        "task": blocker.task,
                        "answer": blocker.answer,
                        "link": blocker.link,
                    }
                    for blocker in sorted(
                        blockers_by_day.get(day, []), key=lambda item: item.timestamp
                    )
                ],
                "tasks_advanced": sorted(progress_by_day.get(day, set())),
            }
        )
        sensitivity_days.append(
            {
                "date": day.isoformat(),
                "minutes": _rounded(
                    episode_total(
                        episodes, floor_minutes=SENSITIVITY_FLOOR_MINUTES
                    )
                ),
            }
        )

    source_counts = Counter(event.source for event in _deduplicate_events(events))
    token_records = [
        record
        for record in log_data.usage_records
        if _usage_record_in_window(record, since=since, until=until, tz_name=timezone_name)
    ]
    sensitivity_total = _rounded(
        sum(float(row["minutes"]) for row in sensitivity_days)
    )
    return {
        "schema": 1,
        "window": {
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "timezone": timezone_name,
        },
        "parameters": {
            "gap_minutes": gap_minutes,
            "floor_minutes": floor_minutes,
            "sensitivity_floor_minutes": SENSITIVITY_FLOOR_MINUTES,
        },
        "human_identities": sorted(identities),
        "sources": {
            "log_enabled": True,
            "git_enabled": git_enabled,
            "github_enabled": github_enabled,
            "log_events": source_counts["log"],
            "git_commit_events": source_counts["git"],
            "github_events": source_counts["github"],
            "github_prs_read": prs_read,
            "usage_sessions": len(token_records),
        },
        "tasks": task_rows,
        "days": day_rows,
        "sensitivity": {
            "floor_minutes": SENSITIVITY_FLOOR_MINUTES,
            "total_minutes": sensitivity_total,
            "average_minutes_per_day": _rounded(
                sensitivity_total / len(sensitivity_days)
                if sensitivity_days
                else 0.0
            ),
            "tasks": sensitivity_tasks,
            "days": sensitivity_days,
        },
        "tokens": token_report(token_records),
    }


def _report_days(
    *,
    since: datetime | None,
    until: datetime | None,
    observed: set[date],
) -> list[date]:
    if since is not None and until is not None:
        current = since.date()
        final = until.date()
        days: list[date] = []
        while current <= final:
            days.append(current)
            current += timedelta(days=1)
        return days
    return sorted(observed)


def _usage_record_in_window(
    record: dict[str, Any],
    *,
    since: datetime | None,
    until: datetime | None,
    tz_name: str,
) -> bool:
    stamp = record.get("ended_at") or record.get("ts")
    if not isinstance(stamp, str):
        return False
    try:
        tz = ZoneInfo(tz_name)
        timestamp = parse_iso_timestamp(stamp, tz)
    except (MetricsError, ZoneInfoNotFoundError):
        return False
    return in_window(timestamp, since, until)


TOKEN_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


def token_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    modes: dict[str, list[dict[str, Any]]] = {
        "autonomous": [],
        "interactive": [],
        "unknown": [],
    }
    models: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        human_turns = record.get("human_turns")
        if isinstance(human_turns, int) and not isinstance(human_turns, bool):
            mode = "autonomous" if human_turns == 0 else "interactive"
        else:
            mode = "unknown"
        modes[mode].append(record)
        provider = str(record.get("provider") or "unknown")
        model = str(record.get("model") or "unknown")
        models[(provider, model)].append(record)
    return {
        "classification": (
            "human_turns == 0 is autonomous; human_turns > 0 is interactive; "
            "missing human_turns is unknown"
        ),
        "window_basis": "session ended_at (fallback ts) is inside the window",
        "overall": _token_bucket(records),
        "by_mode": {mode: _token_bucket(rows) for mode, rows in modes.items()},
        "by_model": [
            {
                "provider": provider,
                "model": model,
                **_token_bucket(models[(provider, model)]),
            }
            for provider, model in sorted(models)
        ],
    }


def _token_bucket(records: list[dict[str, Any]]) -> dict[str, int]:
    totals = {field: 0 for field in TOKEN_FIELDS}
    unknown = 0
    for record in records:
        if record.get("usage_status") != "ok":
            unknown += 1
        for field in TOKEN_FIELDS:
            value = record.get(field)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[field] += value
    return {
        "sessions": len(records),
        "unknown_sessions": unknown,
        **totals,
        "total_tokens": sum(totals.values()),
    }


def _rounded(value: float) -> float:
    return round(value + 1e-12, 3)


def format_markdown(report: dict[str, Any]) -> str:
    window = report["window"]
    parameters = report["parameters"]
    sources = report["sources"]
    git_source = sources["git_commit_events"] if sources["git_enabled"] else "omitted"
    github_source = sources["github_events"] if sources["github_enabled"] else "omitted"
    lines = [
        "# Human attention ledger",
        "",
        (
            f"Window: {window['since'] or 'unbounded'} → "
            f"{window['until'] or 'unbounded'} ({window['timezone']})"
        ),
        (
            f"Parameters: gap > {_number(parameters['gap_minutes'])} min starts "
            f"a new episode; isolated-event floor = "
            f"{_number(parameters['floor_minutes'])} min."
        ),
        (
            "Sources: "
            f"log={sources['log_events']}, "
            f"git={git_source}, "
            f"GitHub={github_source} "
            f"({sources['github_prs_read']} PRs), "
            f"usage sessions={sources['usage_sessions']}."
        ),
        "",
        "## Per task",
        "",
        "| task | minutes | episodes | artifact |",
        "| --- | ---: | ---: | --- |",
    ]
    if report["tasks"]:
        for row in report["tasks"]:
            lines.append(
                f"| `{_escape(row['task'])}` | {_minutes(row['minutes'])} | "
                f"{row['episodes']} | {_artifact(row['artifact'])} |"
            )
    else:
        lines.append("| *(no attributed tasks)* | 0.0 | 0 | — |")

    lines.extend(
        [
            "",
            "## Per day",
            "",
            "| date | minutes | blockers answered | tasks advanced |",
            "| --- | ---: | --- | --- |",
        ]
    )
    if report["days"]:
        for row in report["days"]:
            blockers = "; ".join(
                _format_blocker(item) for item in row["blockers_answered"]
            ) or "—"
            advanced = ", ".join(f"`{_escape(task)}`" for task in row["tasks_advanced"])
            lines.append(
                f"| {row['date']} | {_minutes(row['minutes'])} | {blockers} | "
                f"{advanced or '—'} |"
            )
    else:
        lines.append("| *(no observed days)* | 0.0 | — | — |")

    sensitivity = report["sensitivity"]
    lines.extend(
        [
            "",
            (
                "Sensitivity (isolated-event floor = "
                f"{_number(sensitivity['floor_minutes'])} min): "
                f"{_minutes(sensitivity['total_minutes'])} total human minutes; "
                f"{_minutes(sensitivity['average_minutes_per_day'])} min/day."
            ),
            "",
            "## Machine token accounting",
            "",
            "Classification: " + report["tokens"]["classification"] + ".",
            "Window basis: " + report["tokens"]["window_basis"] + ".",
            "",
            "| mode | sessions | unknown | total | input | cache create | cache read | output |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for mode in ("autonomous", "interactive", "unknown"):
        bucket = report["tokens"]["by_mode"][mode]
        lines.append(
            f"| {mode} | {bucket['sessions']} | {bucket['unknown_sessions']} | "
            f"{bucket['total_tokens']} | {bucket['input_tokens']} | "
            f"{bucket['cache_creation_input_tokens']} | "
            f"{bucket['cache_read_input_tokens']} | {bucket['output_tokens']} |"
        )
    return "\n".join(lines)


def _format_blocker(item: dict[str, Any]) -> str:
    task = _escape(str(item["task"]))
    label = f"`{task}`"
    if item.get("link"):
        label = f"[{task}]({item['link']})"
    answer = _escape(_compact(str(item["answer"]), limit=80))
    return f"{label}: {answer}"


def _compact(value: str, *, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _artifact(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "—"
    match = _PR_URL_RE.fullmatch(value.rstrip("/"))
    label = f"PR #{match.group('number')}" if match else "artifact"
    return f"[{label}]({value})"


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _minutes(value: object) -> str:
    return f"{float(value):.1f}"


def _number(value: object) -> str:
    return f"{float(value):g}"


def infer_repo_url(repo_root: Path) -> str | None:
    result = _run_git(["git", "remote", "get-url", "origin"], repo_root, check=False)
    if result.returncode != 0:
        return None
    remote = result.stdout.strip()
    https_match = re.match(r"https?://github\.com/(.+?)(?:\.git)?$", remote)
    ssh_match = re.match(r"(?:git@|ssh://git@)github\.com[:/](.+?)(?:\.git)?$", remote)
    match = https_match or ssh_match
    return f"https://github.com/{match.group(1)}" if match else None


def infer_revision(repo_root: Path) -> str | None:
    result = _run_git(["git", "rev-parse", "HEAD"], repo_root, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compute human-attention episodes and machine-token totals from "
            "Coga, git, and GitHub records."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/human_minutes.py --since 2026-08-03 "
            "--until 2026-08-16\n"
            "  python scripts/human_minutes.py --since 2026-08-03 "
            "--until 2026-08-16 --json\n"
            "  python scripts/human_minutes.py --no-github --no-git"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--log", type=Path, help="Default: <repo>/coga/log.md")
    parser.add_argument(
        "--tasks-dir", type=Path, help="Default: <repo>/coga/tasks"
    )
    parser.add_argument("--since", help="Inclusive ISO timestamp or YYYY-MM-DD")
    parser.add_argument("--until", help="Inclusive ISO timestamp or YYYY-MM-DD")
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help=f"Timezone for log stamps and diary days (default: {DEFAULT_TIMEZONE}).",
    )
    parser.add_argument(
        "--gap-minutes",
        type=float,
        default=DEFAULT_GAP_MINUTES,
        help="A strictly greater gap starts a new episode (default: 10).",
    )
    parser.add_argument(
        "--floor-minutes",
        type=float,
        default=DEFAULT_FLOOR_MINUTES,
        help="Minutes assigned to an isolated one-event episode (default: 2).",
    )
    parser.add_argument(
        "--human",
        action="append",
        default=[],
        help="Additional human login, name, or email alias (repeatable).",
    )
    parser.add_argument(
        "--github-data",
        type=Path,
        help="Read deterministic gh-shaped PR JSON from this file instead of gh.",
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="Explicitly omit GitHub reviews/comments/merges and PR commit metadata.",
    )
    parser.add_argument(
        "--no-git", action="store_true", help="Explicitly omit git commit events."
    )
    parser.add_argument(
        "--git-base",
        default="origin/main",
        help="Exclude this base when reading recorded local feature branches.",
    )
    parser.add_argument(
        "--repo-url", help="Public web URL used for log and commit permalinks."
    )
    parser.add_argument(
        "--revision", help="Revision used in the coga/log.md permalink (default HEAD)."
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.gap_minutes < 0:
            raise MetricsError("--gap-minutes must be >= 0")
        if args.floor_minutes < 0:
            raise MetricsError("--floor-minutes must be >= 0")
        if args.no_github and args.github_data:
            raise MetricsError("--github-data cannot be combined with --no-github")
        try:
            tz = ZoneInfo(args.timezone)
        except ZoneInfoNotFoundError as exc:
            raise MetricsError(f"unknown timezone: {args.timezone}") from exc

        repo_root = args.repo_root.resolve()
        log_path = (args.log or repo_root / "coga" / "log.md").resolve()
        tasks_dir = (args.tasks_dir or repo_root / "coga" / "tasks").resolve()
        since = parse_window_bound(args.since, is_until=False, tz=tz)
        until = parse_window_bound(args.until, is_until=True, tz=tz)
        if since is not None and until is not None and since > until:
            raise MetricsError("--since must not be after --until")

        repo_url = (args.repo_url or infer_repo_url(repo_root) or "").rstrip("/")
        revision = args.revision or infer_revision(repo_root)
        log_web_url: str | None = None
        if repo_url and revision:
            try:
                relative_log = log_path.relative_to(repo_root).as_posix()
            except ValueError:
                relative_log = ""
            if relative_log:
                log_web_url = f"{repo_url}/blob/{revision}/{relative_log}"

        task_infos = discover_tasks(tasks_dir)
        log_data = parse_log(log_path, tz=tz, log_web_url=log_web_url)
        for slug, pr_url in log_data.pr_urls.items():
            existing = task_infos.get(slug)
            if existing is None:
                task_infos[slug] = TaskInfo(
                    slug=slug, path=None, pr_url=pr_url, artifact=pr_url
                )
            elif existing.pr_url is None:
                task_infos[slug] = replace(
                    existing, pr_url=pr_url, artifact=existing.artifact or pr_url
                )

        identities = set(log_data.human_identities)
        identities.update(args.human)
        for info in task_infos.values():
            identities.update(info.humans)
        matcher = IdentityMatcher(identities)
        if (not args.no_git or not args.no_github) and not matcher.tokens:
            raise MetricsError(
                "no human identities found in log/tickets; pass --human to attribute "
                "git and GitHub events"
            )

        github: GithubClient | None = None
        if not args.no_github:
            github = GithubClient.from_path(args.github_data, cwd=repo_root)
        external_events, prs_read = collect_external_events(
            task_infos,
            matcher=matcher,
            tz=tz,
            repo_root=repo_root,
            github=github,
            include_git=not args.no_git,
            include_github=not args.no_github,
            git_base=args.git_base,
            commit_web_root=repo_url or None,
        )
        report = build_report(
            log_data=log_data,
            task_infos=task_infos,
            external_events=external_events,
            since=since,
            until=until,
            timezone_name=args.timezone,
            gap_minutes=args.gap_minutes,
            floor_minutes=args.floor_minutes,
            prs_read=prs_read,
            identities=identities,
            git_enabled=not args.no_git,
            github_enabled=not args.no_github,
        )
        if args.json_output:
            print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        else:
            print(format_markdown(report))
        return 0
    except MetricsError as exc:
        print(f"human_minutes: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
