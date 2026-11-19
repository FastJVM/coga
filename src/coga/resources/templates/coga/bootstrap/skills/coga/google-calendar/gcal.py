#!/usr/bin/env python3
"""Google Calendar capability — a self-contained coga skill script.

The reusable way for coga skills to create/read/update/delete Google Calendar
events without a per-host `gws`/`gcloud` binary. Other skills shell to this
script (the calendar analogue of shelling to `coga slack`):

    python <coga>/skills/coga/google-calendar/gcal.py get \
        --calendar-id <id> --event-id <id>
    python .../gcal.py create --calendar-id <id> --body '<json event>'
    python .../gcal.py update --calendar-id <id> --event-id <id> --body '<json>'
    python .../gcal.py delete --calendar-id <id> --event-id <id>

`get`/`create`/`update` print the Google event resource as JSON on stdout;
`delete` prints `{}`. Exit codes are the contract:

    0  ok
    1  config / auth / API error (message on stderr)
    3  event not found (so a caller can tell "gone" from "broken")

Auth — service account
  Reads a service-account JSON key from the environment: its contents from
  `GCAL_SERVICE_ACCOUNT_JSON`, else a path from `GCAL_SERVICE_ACCOUNT_FILE`.
  A consuming ticket delivers either through its `secrets:` frontmatter
  (`op://` or `env:VAR`, see coga/secrets); a manual run exports one. A
  service account authenticates headlessly, which is what an unattended cron
  needs.

  Consequence: a service account is a robot identity. On a personal
  (non-Workspace) Google account there is no domain-wide delegation, so it can
  only touch a calendar **shared with the service account's email** — never a
  human's `primary`. A 403/404 is surfaced with that hint rather than the raw
  Google error.

Dependencies (google-api-python-client, google-auth) are declared in this
skill's requirements.txt. Coga installs nothing for a skill — install them
into the Python this script runs under.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

EXIT_ERROR = 1
EXIT_NOT_FOUND = 3


def _bail(message: str, code: int = EXIT_ERROR) -> None:
    sys.stderr.write(f"calendar: {message}\n")
    sys.exit(code)


# --- credentials ---------------------------------------------------------------


JSON_VAR = "GCAL_SERVICE_ACCOUNT_JSON"
FILE_VAR = "GCAL_SERVICE_ACCOUNT_FILE"


def resolve_service_account_info() -> dict[str, Any]:
    """Return the service-account key as a dict, read from the environment.

    `GCAL_SERVICE_ACCOUNT_JSON` (the key's JSON contents) wins over
    `GCAL_SERVICE_ACCOUNT_FILE` (a path to it). Bails with a setup message
    when neither is set or the key is not a JSON object.
    """
    raw = os.environ.get(JSON_VAR)
    source = JSON_VAR
    if not raw:
        path = os.environ.get(FILE_VAR)
        if not path:
            _bail(
                f"no service-account credentials configured. Set {JSON_VAR} "
                f"(the JSON key contents) or {FILE_VAR} (a path to it), e.g. via "
                "the ticket's secrets: frontmatter."
            )
        source = f"{FILE_VAR} ({path})"
        try:
            raw = Path(path).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            _bail(f"could not read service-account key from {source}: {exc}")
    try:
        info = json.loads(raw)  # type: ignore[arg-type]
    except json.JSONDecodeError as exc:
        _bail(f"service-account key in {source} is not valid JSON: {exc}")
    if not isinstance(info, dict):
        _bail(f"service-account key in {source} is not a JSON object")
    return info  # type: ignore[return-value]


def build_service(info: dict[str, Any]) -> Any:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        _bail(
            "google-api-python-client / google-auth not installed: "
            f"{exc}. They are declared in this skill's requirements.txt; run "
            "`python -m pip install -r requirements.txt` from this skill's dir, "
            "using the same Python that runs this script."
        )
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    except ValueError as exc:
        _bail(f"could not load service-account key: {exc}")
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# --- operations ----------------------------------------------------------------


def _http_status(exc: Exception) -> int | None:
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        return None
    if isinstance(exc, HttpError) and exc.resp is not None:
        try:
            return int(exc.resp.status)
        except (TypeError, ValueError):
            return None
    return None


def _handle_api_error(exc: Exception, calendar_id: str, event_id: str | None) -> None:
    status = _http_status(exc)
    if status == 404 and event_id is not None:
        _bail(f"calendar event not found: {event_id}", code=EXIT_NOT_FOUND)
    if status in (403, 404):
        primary = (
            " The 'primary' calendar belongs to a human user; a service account "
            "cannot reach it on a personal Google account. Target a calendar "
            "shared with the service account's email instead."
            if calendar_id == "primary"
            else ""
        )
        _bail(
            f"Google returned {status} for calendar {calendar_id!r}. The service "
            "account likely isn't a member of this calendar — share it with the "
            f"service account's email (Make changes to events).{primary}"
        )
    _bail(str(exc))


def run(service: Any, args: argparse.Namespace) -> dict[str, Any]:
    events = service.events()
    cal, ev = args.calendar_id, getattr(args, "event_id", None)
    try:
        if args.command == "get":
            return events.get(calendarId=cal, eventId=ev).execute()
        if args.command == "create":
            return events.insert(calendarId=cal, body=_parse_body(args.body)).execute()
        if args.command == "update":
            # patch (partial merge): callers send only the fields they manage.
            return events.patch(calendarId=cal, eventId=ev, body=_parse_body(args.body)).execute()
        if args.command == "delete":
            events.delete(calendarId=cal, eventId=ev).execute()
            return {}
    except Exception as exc:  # noqa: BLE001 - normalized to exit codes
        _handle_api_error(exc, cal, ev)
    return {}  # unreachable


def _parse_body(body: str) -> dict[str, Any]:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        _bail(f"--body is not valid JSON: {exc}")
    if not isinstance(parsed, dict):
        _bail("--body must be a JSON object (a Google event resource)")
    return parsed  # type: ignore[return-value]


# --- cli -----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Google Calendar events capability.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("get", "create", "update", "delete"):
        p = sub.add_parser(name)
        p.add_argument("--calendar-id", required=True)
        if name in ("get", "update", "delete"):
            p.add_argument("--event-id", required=True)
        if name in ("create", "update"):
            p.add_argument("--body", required=True, help="Event resource as JSON.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    service = build_service(resolve_service_account_info())
    payload = run(service, args)
    sys.stdout.write(json.dumps(payload) + "\n")


if __name__ == "__main__":
    main()
