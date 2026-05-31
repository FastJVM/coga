"""Tests for the bundled relay/gmail skill script.

The script is self-contained (not an installed module), so it's loaded by path.
A fake service stands in for google-api-python-client; no creds/network.
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from googleapiclient.errors import HttpError

SKILL = (
    Path(__file__).resolve().parents[1]
    / "src" / "relay" / "resources" / "templates" / "relay-os"
    / "bootstrap" / "skills" / "relay" / "gmail" / "gmail.py"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gmail_skill", SKILL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gm = _load()


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


class _Req:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self._result, self._exc = result, exc

    def execute(self):
        if self._exc is not None:
            raise self._exc
        return self._result


class _Messages:
    def __init__(self, service) -> None:
        self._s = service

    def list(self, userId, q, pageToken=None, maxResults=None):  # noqa: N803
        self._s.calls.append(("list", q, pageToken, maxResults))
        return _Req(self._s.list_result, self._s.exc)

    def get(self, userId, id, format):  # noqa: A002,N803
        self._s.calls.append(("get", id, format))
        return _Req(self._s.get_result, self._s.exc)

    def attachments(self):
        return _Attachments(self._s)


class _Attachments:
    def __init__(self, service) -> None:
        self._s = service

    def get(self, userId, messageId, id):  # noqa: A002,N803
        self._s.calls.append(("attachment", messageId, id))
        return _Req(self._s.attachment_result, self._s.exc)


class _Service:
    def __init__(self, *, list_result=None, get_result=None, attachment_result=None, exc=None):
        self.list_result = list_result
        self.get_result = get_result
        self.attachment_result = attachment_result
        self.exc = exc
        self.calls: list = []

    def users(self):
        return self

    def messages(self):
        return _Messages(self)


def _ns(command, **kw) -> argparse.Namespace:
    return argparse.Namespace(command=command, **kw)


def _http_error(status: int) -> HttpError:
    resp = type("Resp", (), {"status": status, "reason": "x"})()
    return HttpError(resp, b"{}")


# --- normalize_message ---


def test_normalize_message_extracts_body_and_attachments() -> None:
    message = {
        "id": "m1",
        "threadId": "t1",
        "snippet": "hi",
        "payload": {
            "headers": [
                {"name": "From", "value": "a@b.com"},
                {"name": "Subject", "value": "Hello"},
                {"name": "Date", "value": "Mon, 5 May 2025 10:00:00 -0700"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("Body.")}},
                {
                    "mimeType": "application/pdf",
                    "filename": "doc.pdf",
                    "body": {"attachmentId": "att-1", "size": 99},
                },
            ],
        },
    }
    out = gm.normalize_message(message)
    assert out["sender"] == "a@b.com"
    assert out["subject"] == "Hello"
    assert "Body." in out["body_text"]
    assert out["attachments"] == [
        {"filename": "doc.pdf", "mimeType": "application/pdf", "size": 99, "attachmentId": "att-1"}
    ]


# --- ops ---


def test_search_returns_ids() -> None:
    svc = _Service(list_result={"messages": [{"id": "m1", "threadId": "t1"}]})
    out = gm.run(svc, "me", _ns("search", query="patent", max=10))
    assert out["messages"] == [{"id": "m1", "threadId": "t1"}]


def test_get_returns_normalized() -> None:
    svc = _Service(get_result={"id": "m1", "payload": {"headers": [], "parts": []}})
    out = gm.run(svc, "me", _ns("get", message_id="m1"))
    assert out["id"] == "m1"
    assert out["attachments"] == []


def test_download_writes_bytes(tmp_path: Path) -> None:
    svc = _Service(attachment_result={"data": _b64url("%PDF-1.4 bytes")})
    dest = tmp_path / "out" / "doc.pdf"
    out = gm.run(svc, "me", _ns("download", message_id="m1", attachment_id="att-1", out=str(dest)))
    assert dest.read_bytes().startswith(b"%PDF")
    assert out["bytes"] > 0
    assert out["path"] == str(dest)


def test_missing_message_exits_3() -> None:
    svc = _Service(exc=_http_error(404))
    with pytest.raises(SystemExit) as exc:
        gm.run(svc, "me", _ns("get", message_id="gone"))
    assert exc.value.code == gm.EXIT_NOT_FOUND


def test_auth_403_hint(capsys) -> None:
    svc = _Service(exc=_http_error(403))
    with pytest.raises(SystemExit):
        gm.run(svc, "me", _ns("search", query="x", max=5))
    assert "authorize" in capsys.readouterr().err
