"""Weekly snapshot recipe; behavioral contract: coga/telemetry."""

from __future__ import annotations

import contextlib
import hashlib
import http.client
import io
import json
import os
import platform
import re
import subprocess
import sys
import tomllib
import time
from collections.abc import Callable
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from uuid import UUID, uuid4

from coga import git, notification
from coga.blackboard import append_blackboard_report
from coga.config import Config, load_config
from coga.lifecycle import VALID_STATUSES
from coga.logfile import append_log
from coga.paths import log_path, recurring_dir
from coga.task_env import blackboard_from_env
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import DuplicateTaskSlugError, list_tasks, read_ticket
from coga.ticket import TicketError

# Public write-only project 606347 key; rotation requires a release.
POSTHOG_CAPTURE_KEY = 'phc_v9CUMRgcBDkGkC64C2WzvZ4Xy43ZTKEqijRsiGMG9DaE'
_EVENT = "coga_weekly_snapshot"
_DEADLINE = 3.0
_OUTCOMES = frozenset({"accepted", "rejected", "network-error", "timed-out", "suppressed"})
_VERSION = re.compile(
    r"(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?"
    r"(?:\.post[0-9]+)?(?:\.dev[0-9]+)?(?:\+[a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*)?",
    re.ASCII,
)
_NUMERIC = re.compile(r"[0-9]+(?:\.[0-9]+)*", re.ASCII)
_STATE_LINE = re.compile(r"^period_state: ([^\r\n]+)(?=\r?$)", re.MULTILINE)
_ENTRY = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}) \[([^\[\]\s]+)\] \[([^\[\]\s]+)\] (.+)")
_MOVEMENT = re.compile(
    r"(?:advanced to step [1-9][0-9]* \([^()\r\n]+\)(?: → [^\s]+)?(?: — .+)?"
    r"|task done(?: — .+)?"
    r"|auto-bumped on merge of (?:PR #[0-9]+|the linked PR) → done)"
)
_COUNT_KEYS = {f"tickets_{s}" for s in VALID_STATUSES} | {"movement_count"}
_PROPERTY_KEYS = _COUNT_KEYS | {"coga_version", "os_name", "os_version", "python_version"}


class TelemetryError(ValueError):
    """Invalid local input; never includes private input in its message."""


def _uuid(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value and UUID(value).version == 4
    except ValueError:
        return False


def _state(region: str) -> tuple[dict, re.Match[str]]:
    matches = list(_STATE_LINE.finditer(region))
    if len(matches) != 1:
        raise TelemetryError("phone-home requires one period_state line")
    try:
        state = json.loads(matches[0][1])
        if not isinstance(state, dict) or set(state) != {"schema", "run", "repo_id", "offset", "digest"}:
            raise ValueError
        if type(state["schema"]) is not int or state["schema"] != 1:
            raise ValueError
        if any(type(state[k]) is not int or state[k] < 0 for k in ("run", "offset")):
            raise ValueError
        if state["repo_id"] is not None and not _uuid(state["repo_id"]):
            raise ValueError
        if not isinstance(state["digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", state["digest"]):
            raise ValueError
    except (ValueError, TypeError):
        raise TelemetryError("invalid phone-home period_state") from None
    return state, matches[0]


def _housekeeping(ref: str) -> bool:
    return ref == "recurring" or ref.startswith("recurring/")


def _movement(line: bytes) -> bool:
    try:
        match = _ENTRY.fullmatch(line.decode("utf-8").removesuffix("\r"))
        if not match or _housekeeping(match[2]):
            return False
        datetime.strptime(match[1], "%Y-%m-%d %H:%M")
        return _MOVEMENT.fullmatch(match[4]) is not None
    except (UnicodeDecodeError, ValueError):
        return False


def _cursor(raw: bytes, state: dict, *, baseline: bool) -> tuple[int, str, int, bool]:
    complete = raw[:raw.rfind(b"\n") + 1]
    offset = state["offset"]
    reset = offset > len(complete) or hashlib.sha256(complete[:offset]).hexdigest() != state["digest"]
    count = 0 if baseline or reset else sum(_movement(line) for line in set(complete[offset:].split(b"\n")))
    return len(complete), hashlib.sha256(complete).hexdigest(), count, reset and not baseline


def _inventory(cfg: Config) -> dict[str, int]:
    counts = {f"tickets_{s}": 0 for s in sorted(VALID_STATUSES)}
    for ref in list_tasks(cfg):
        if _housekeeping(ref.id_slug):
            continue
        ticket = read_ticket(ref)
        status = ticket.frontmatter.get("status")
        if not isinstance(status, str) or status not in VALID_STATUSES:
            raise TelemetryError("invalid task inventory; snapshot skipped")
        counts[f"tickets_{status}"] += 1
    return counts


def _development_tree(path: Path) -> bool:
    path = path.resolve()
    for root in (path, *path.parents):
        if not (root / "src/coga/runner.py").is_file() or not (root / "tests").is_dir():
            continue
        try:
            project = tomllib.loads((root / "pyproject.toml").read_text()).get("project", {})
        except (OSError, ValueError):
            # An unreadable development marker is not permission to send.
            return True
        if project.get("name") == "coga":
            return True
    return False


def _admitted(cfg: Config) -> bool:
    return (
        cfg.telemetry_enabled
        and "PYTEST_CURRENT_TEST" not in os.environ
        and os.environ.get("CI", "").strip().lower() in {"", "0", "false", "no", "off"}
        and not any(_development_tree(p) for p in (Path(__file__), cfg.repo_root, Path.cwd()))
    )


def _payload(repo_id: str, counts: dict[str, int], movement: int, now: datetime) -> dict:
    release = _NUMERIC.match(platform.release())
    event = {
        "event": _EVENT,
        "distinct_id": repo_id,
        "timestamp": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "properties": {
            "coga_version": version("coga"),
            "os_name": {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}.get(platform.system(), "other"),
            "os_version": release[0][:64].rstrip(".") if release else "",
            "python_version": ".".join(str(n) for n in sys.version_info[:3]),
            **counts,
            "movement_count": movement,
        },
    }
    _validate_payload(event)
    return event


def _validate_payload(event: dict) -> None:
    try:
        if set(event) != {"event", "distinct_id", "timestamp", "properties"} or event["event"] != _EVENT:
            raise ValueError
        if not _uuid(event["distinct_id"]):
            raise ValueError
        stamp = event["timestamp"]
        if not isinstance(stamp, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z", stamp):
            raise ValueError
        datetime.fromisoformat(stamp)
        props = event["properties"]
        if not isinstance(props, dict) or set(props) != _PROPERTY_KEYS:
            raise ValueError
        if any(type(props[k]) is not int or props[k] < 0 for k in _COUNT_KEYS):
            raise ValueError
        if props["os_name"] not in {"linux", "macos", "windows", "other"}:
            raise ValueError
        for key in ("coga_version", "python_version", "os_version"):
            value = props[key]
            if not isinstance(value, str) or len(value) > 64 or not value.isascii():
                raise ValueError
            pattern = _VERSION if key == "coga_version" else _NUMERIC
            if not (key == "os_version" and value == "") and not pattern.fullmatch(value):
                raise ValueError
    except (ValueError, TypeError, KeyError):
        raise TelemetryError("invalid phone-home event") from None


def _post_http(body: bytes) -> str:
    """One TLS POST, no redirect/retry/proxy/SDK enrichment or response body read."""
    connection = http.client.HTTPSConnection("us.i.posthog.com", timeout=_DEADLINE)
    try:
        connection.request("POST", "/i/v0/e/", body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        return "accepted" if 200 <= response.status < 300 else "rejected"
    except (OSError, http.client.HTTPException):
        return "network-error"
    finally:
        connection.close()


def _capture(cfg: Config, event: dict) -> str:
    if not _admitted(cfg):
        return "suppressed"
    _validate_payload(event)
    if not POSTHOG_CAPTURE_KEY:
        raise TelemetryError("phone-home capture key is missing from this build")
    body = json.dumps({"api_key": POSTHOG_CAPTURE_KEY, **event}, separators=(",", ":"), allow_nan=False).encode("ascii")
    return _post_http(body)


def _receipt(cfg: Config, event: dict, outcome: str) -> str:
    if not _admitted(cfg) or not cfg.slack_enabled or "slack" not in cfg.notification_channels:
        return "suppressed"
    _validate_payload(event)
    label = "HTTP accepted" if outcome == "accepted" else outcome
    # notification.post reports nonfatal failures on stderr, never on the audit
    # log here. Consume that diagnostic privately rather than exporting it.
    diagnostic = io.StringIO()
    with contextlib.redirect_stderr(diagnostic):
        notification.post(cfg, f"phone-home attempted / {label}: " + json.dumps(event, separators=(",", ":")), fatal=False, record_failure=False)
    return "network-error" if diagnostic.getvalue() else "accepted"


def _worker_main() -> None:
    """Private subprocess entry point. No public recipe, option, or bypass."""
    outcome = "network-error"
    try:
        cfg = load_config(Path(sys.argv[2]))
        if not _admitted(cfg):
            outcome = "suppressed"
        else:
            raw = sys.stdin.buffer.read(16385)
            if len(raw) > 16384:
                raise TelemetryError("oversized worker input")
            data = json.loads(raw)
            if sys.argv[1] == "capture":
                outcome = _capture(cfg, data)
            elif sys.argv[1] == "receipt" and set(data) == {"event", "outcome"} and data["outcome"] in _OUTCOMES:
                outcome = _receipt(cfg, data["event"], data["outcome"])
    except Exception:
        pass
    print(outcome)


def _bounded_worker(cfg: Config, kind: str, data: dict) -> str:
    if not _admitted(cfg):
        return "suppressed"
    started = time.monotonic()
    try:
        child = subprocess.Popen(
            [sys.executable, "-c", "from coga.telemetry import _worker_main; _worker_main()", kind, str(cfg.repo_root)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        try:
            output, _ = child.communicate(json.dumps(data).encode("ascii"), timeout=max(0, _DEADLINE - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
            return "timed-out"
        result = output.decode("ascii").strip()
        return result if child.returncode == 0 and result in _OUTCOMES else "network-error"
    except (OSError, UnicodeError):
        return "network-error"


def run_phone_home_recipe(
    cfg: Config, argv: list[str], *,
    sender: Callable[[Config, str, dict], str] | None = None,
    clock: Callable[[], datetime] | None = None,
    identity: Callable[[], UUID] = uuid4,
) -> int:
    if argv:
        raise TelemetryError("phone-home takes no options or arguments")
    admitted = _admitted(cfg)
    parent = recurring_dir(cfg) / "phone-home/ticket.md"
    warnings: list[str] = []
    event = None
    outcome = "suppressed" if not admitted else "skipped"
    with git.state_lock(cfg):
        raw = parent.read_bytes()
        region = read_blackboard(parent, expected_bytes=raw)
        state, match = _state(region)
        state["run"] += 1
        counts = None
        if admitted:
            try:
                counts = _inventory(cfg)
            except (TicketError, TelemetryError, DuplicateTaskSlugError, OSError, UnicodeError):
                warnings.append("invalid task inventory; snapshot skipped; identity and cursor preserved")
        if not admitted or counts is not None:
            try:
                log = log_path(cfg).read_bytes()
            except FileNotFoundError:
                log = b""
            offset, digest, movement, reset = _cursor(log, state, baseline=not admitted or state["repo_id"] is None)
            if reset:
                warnings.append("audit log rewritten or truncated; movement baselined to zero")
            if admitted:
                repo_id = state["repo_id"] or str(identity())
                event = _payload(repo_id, counts, movement, (clock or (lambda: datetime.now(timezone.utc)))())
                state["repo_id"] = repo_id
            state.update(offset=offset, digest=digest)
        replacement = region[:match.start()] + "period_state: " + json.dumps(state, separators=(",", ":")) + region[match.end():]
        replace_blackboard(parent, replacement, expected_bytes=raw)
        try:
            git.publish(cfg, [parent], "Telemetry: reserve weekly snapshot", expect={parent: raw})
        except git.GitError as exc:
            # Match ordinary sync's durable local failure evidence, scoped to
            # this parent. Publication failure never rolls back reservation.
            sys.stderr.write(f"[git] phone-home publication failed: {exc}\n")
            append_log(cfg, "recurring/phone-home", "git", f"sync failed: {exc}")
            warnings.append("parent publication failed; local state retained")
    receipt = "suppressed"
    if event is not None:
        send = sender or _bounded_worker
        outcome = send(cfg, "capture", event)
        if cfg.slack_enabled and "slack" in cfg.notification_channels:
            receipt = send(cfg, "receipt", {"event": event, "outcome": outcome})
        failures = [f"{name} {value}" for name, value in (("capture", outcome), ("receipt", receipt)) if value not in {"accepted", "suppressed"}]
        if failures:
            warnings.append("delivery: " + "; ".join(failures))
    report = f"## Phone home\n\nRun {state['run']}: capture {outcome}; receipt {receipt}.\n"
    if event:
        report += "Counts: " + json.dumps({k: event["properties"][k] for k in sorted(_COUNT_KEYS)}) + ".\n"
    if warnings:
        report += "Warning: " + "; ".join(warnings) + ".\n"
    period = blackboard_from_env(cfg.repo_root)
    if period:
        append_blackboard_report(cfg, period, report)
    else:
        print(report, end="")
    return 0
