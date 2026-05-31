#!/usr/bin/env python3
"""Gmail capability — a self-contained relay skill script.

The reusable way for relay skills to read a Gmail mailbox — search, fetch a
parsed message, and **download attachment bytes** — without a per-host binary.
Other skills shell to this script (the Gmail analogue of shelling to `gcal.py`
or `relay slack`):

    python <relay-os>/skills/relay/gmail/gmail.py search \
        --query 'from:uspto.gov has:attachment newer_than:12m' --max 50
    python .../gmail.py get --message-id <id>
    python .../gmail.py download --message-id <id> --attachment-id <id> \
        --out /path/to/file.pdf
    python .../gmail.py authorize --client-secret /path/to/client_secret.json

`search` prints `{messages: [{id, threadId}], nextPageToken?}`; `get` prints a
normalized message `{id, threadId, date, sender, subject, snippet, body_text,
attachments: [{filename, mimeType, size, attachmentId}]}`; `download` writes
the bytes to `--out` and prints `{path, bytes}`; `authorize` prints the
`[gmail]` block to paste into `relay.local.toml`. Exit codes are the contract:

    0  ok
    1  config / auth / API error (message on stderr)
    3  message or attachment not found (so a caller can tell "gone" from "broken")

Auth — OAuth user credentials
  Reads `[gmail]` from `relay.local.toml`: `client_id`, `client_secret`,
  `refresh_token`, and `user` (the mailbox address). Unlike the calendar
  service account, OAuth works on any Google account — Workspace or personal —
  and needs no admin, which is what reading a human's mailbox requires. Scope
  is `gmail.readonly`: this capability never sends or modifies mail. Mint the
  credentials once with `authorize`.

Dependencies (google-api-python-client, google-auth, google-auth-oauthlib) are
declared in this skill's requirements.txt and installed into `.relay/.venv` at
bootstrap by relay's per-skill install pass.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_URI = "https://oauth2.googleapis.com/token"

EXIT_ERROR = 1
EXIT_NOT_FOUND = 3


def _bail(message: str, code: int = EXIT_ERROR) -> None:
    sys.stderr.write(f"gmail: {message}\n")
    sys.exit(code)


# --- credentials ---------------------------------------------------------------


def _relay_os_root() -> Path:
    """Locate the relay-os dir holding relay.local.toml.

    Prefers RELAY_RELAY_OS_ROOT (set for skill/script launches), else walks up
    from cwd looking for relay.local.toml or relay.toml.
    """
    env_root = os.environ.get("RELAY_RELAY_OS_ROOT")
    if env_root:
        return Path(env_root)
    cur = Path.cwd().resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "relay.local.toml").is_file() or (candidate / "relay.toml").is_file():
            return candidate
        nested = candidate / "relay-os"
        if (nested / "relay.toml").is_file():
            return nested
    return cur


def resolve_gmail_config() -> dict[str, str]:
    """Read and validate the `[gmail]` block from relay.local.toml.

    Each value supports `env:VAR` indirection (same convention as relay's
    `[secrets]`). Bails with a clear setup message when unset or incomplete.
    """
    local = _relay_os_root() / "relay.local.toml"
    section: Any = None
    if local.is_file():
        with local.open("rb") as fh:
            section = tomllib.load(fh).get("gmail")
    if not isinstance(section, dict):
        _bail(
            "no Gmail credentials configured. Set the [gmail] block in "
            "relay.local.toml (run `gmail.py authorize` to mint one)."
        )
    required = ("client_id", "client_secret", "refresh_token", "user")
    out: dict[str, str] = {}
    for key in required:
        raw = section.get(key)  # type: ignore[union-attr]
        if isinstance(raw, str) and raw.startswith("env:"):
            raw = os.environ.get(raw[4:])
        if not isinstance(raw, str) or not raw:
            _bail(f"[gmail] is missing {key!r}; re-run `gmail.py authorize`")
        out[key] = raw
    return out


def build_service(config: dict[str, str]) -> Any:
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        _bail(
            "google-api-python-client / google-auth not installed: "
            f"{exc}. They are declared in this skill's requirements.txt; run "
            "`relay init --update` to install skill deps into .relay/.venv."
        )
    creds = Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# --- message parsing (generic MIME walk) ---------------------------------------


def _decode_b64url(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii") + b"==")


def _header(payload: dict[str, Any], name: str) -> str:
    for h in payload.get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _walk_parts(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Return (plain-text body, attachment descriptors) from a message payload."""
    text_chunks: list[str] = []
    attachments: list[dict[str, Any]] = []

    def visit(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        filename = part.get("filename") or ""
        body = part.get("body", {}) or {}
        if filename and (body.get("attachmentId") or body.get("data")):
            attachments.append(
                {
                    "filename": filename,
                    "mimeType": mime,
                    "size": int(body.get("size", 0) or 0),
                    "attachmentId": body.get("attachmentId"),
                }
            )
        elif mime == "text/plain" and body.get("data"):
            try:
                text_chunks.append(_decode_b64url(body["data"]).decode("utf-8", "replace"))
            except Exception:  # noqa: BLE001 - body decode is best-effort
                pass
        for child in part.get("parts", []) or []:
            visit(child)

    visit(payload)
    return "\n".join(text_chunks), attachments


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Gmail API message resource into a stable, generic shape."""
    payload = message.get("payload", {}) or {}
    body_text, attachments = _walk_parts(payload)
    return {
        "id": message.get("id"),
        "threadId": message.get("threadId"),
        "date": _header(payload, "Date"),
        "sender": _header(payload, "From"),
        "subject": _header(payload, "Subject"),
        "snippet": message.get("snippet", ""),
        "body_text": body_text,
        "attachments": attachments,
    }


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


def _handle_api_error(exc: Exception, *, what: str | None) -> None:
    status = _http_status(exc)
    if status == 404 and what is not None:
        _bail(f"gmail {what} not found", code=EXIT_NOT_FOUND)
    if status in (401, 403):
        _bail(
            f"Google returned {status}. The [gmail] credentials are likely "
            "expired or lack gmail.readonly scope — re-run `gmail.py authorize`."
        )
    _bail(str(exc))


def op_search(service: Any, user: str, query: str, max_messages: int) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    page_token: str | None = None
    next_token: str | None = None
    while len(messages) < max_messages:
        resp = (
            service.users()
            .messages()
            .list(
                userId=user,
                q=query,
                pageToken=page_token,
                maxResults=min(100, max_messages - len(messages)),
            )
            .execute()
        )
        messages.extend(
            {"id": m["id"], "threadId": m.get("threadId")} for m in resp.get("messages", [])
        )
        next_token = resp.get("nextPageToken")
        page_token = next_token
        if not page_token:
            break
    out: dict[str, Any] = {"messages": messages[:max_messages]}
    if next_token and len(messages) >= max_messages:
        out["nextPageToken"] = next_token
    return out


def op_get(service: Any, user: str, message_id: str) -> dict[str, Any]:
    message = (
        service.users().messages().get(userId=user, id=message_id, format="full").execute()
    )
    return normalize_message(message)


def op_download(
    service: Any, user: str, message_id: str, attachment_id: str, out_path: Path
) -> dict[str, Any]:
    resp = (
        service.users()
        .messages()
        .attachments()
        .get(userId=user, messageId=message_id, id=attachment_id)
        .execute()
    )
    data = _decode_b64url(resp["data"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return {"path": str(out_path), "bytes": len(data)}


def run(service: Any, user: str, args: argparse.Namespace) -> dict[str, Any]:
    try:
        if args.command == "search":
            return op_search(service, user, args.query, args.max)
        if args.command == "get":
            return op_get(service, user, args.message_id)
        if args.command == "download":
            return op_download(
                service, user, args.message_id, args.attachment_id, Path(args.out)
            )
    except Exception as exc:  # noqa: BLE001 - normalized to exit codes
        what = "message" if args.command in ("get", "download") else None
        _handle_api_error(exc, what=what)
    return {}  # unreachable


# --- authorize -----------------------------------------------------------------


def op_authorize(client_secret_file: Path) -> dict[str, Any]:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        _bail(
            "google-auth-oauthlib not installed: "
            f"{exc}. Declared in this skill's requirements.txt; run "
            "`relay init --update` to install skill deps into .relay/.venv."
        )
    if not client_secret_file.is_file():
        _bail(
            f"client secret file not found: {client_secret_file}. Create an OAuth "
            "'Desktop app' client in Google Cloud Console, enable the Gmail API, "
            "and download its JSON."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), scopes=SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    import urllib.request

    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        user = json.loads(resp.read()).get("email", "<unknown>")
    block = (
        "\n[gmail]\n"
        f'user = "{user}"\n'
        f'client_id = "{creds.client_id}"\n'
        f'client_secret = "{creds.client_secret}"\n'
        f'refresh_token = "{creds.refresh_token}"\n'
    )
    sys.stderr.write(
        f"Authorized as {user}. Paste the block below into "
        "relay-os/relay.local.toml (it is gitignored):\n"
    )
    return {"user": user, "toml_block": block}


# --- cli -----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gmail read + attachment-download capability.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="search messages, print ids")
    p_search.add_argument("--query", required=True, help="Gmail search query")
    p_search.add_argument("--max", type=int, default=100, help="cap on messages returned")

    p_get = sub.add_parser("get", help="fetch one message, print normalized JSON")
    p_get.add_argument("--message-id", required=True)

    p_dl = sub.add_parser("download", help="download one attachment to --out")
    p_dl.add_argument("--message-id", required=True)
    p_dl.add_argument("--attachment-id", required=True)
    p_dl.add_argument("--out", required=True, help="output file path")

    p_auth = sub.add_parser("authorize", help="one-time OAuth consent")
    p_auth.add_argument(
        "--client-secret", required=True, help="OAuth 'Desktop app' client_secret JSON"
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "authorize":
        payload = op_authorize(Path(args.client_secret))
        sys.stdout.write(payload["toml_block"])
        return
    config = resolve_gmail_config()
    service = build_service(config)
    payload = run(service, config["user"], args)
    sys.stdout.write(json.dumps(payload) + "\n")


if __name__ == "__main__":
    main()
