"""Tests for the bundled relay/google-calendar skill script.

The script is self-contained (not an installed module), so it's loaded by path.
A fake service stands in for google-api-python-client; no creds/network.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from googleapiclient.errors import HttpError

SKILL = (
    Path(__file__).resolve().parents[1]
    / "src" / "relay" / "resources" / "templates" / "relay-os"
    / "bootstrap" / "skills" / "relay" / "google-calendar" / "gcal.py"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gcal_skill", SKILL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cal = _load()


class _Req:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self._result, self._exc = result, exc

    def execute(self):
        if self._exc is not None:
            raise self._exc
        return self._result


class _Events:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self.result, self.exc, self.calls = result, exc, []

    def get(self, calendarId, eventId):  # noqa: N803
        self.calls.append(("get", calendarId, eventId))
        return _Req(self.result, self.exc)

    def insert(self, calendarId, body):  # noqa: N803
        self.calls.append(("insert", calendarId, body))
        return _Req(self.result, self.exc)

    def patch(self, calendarId, eventId, body):  # noqa: N803
        self.calls.append(("patch", calendarId, eventId, body))
        return _Req(self.result, self.exc)

    def delete(self, calendarId, eventId):  # noqa: N803
        self.calls.append(("delete", calendarId, eventId))
        return _Req(self.result, self.exc)


class _Service:
    def __init__(self, events: _Events) -> None:
        self._events = events

    def events(self):
        return self._events


def _ns(command, **kw) -> argparse.Namespace:
    return argparse.Namespace(command=command, **kw)


def _http_error(status: int) -> HttpError:
    resp = type("Resp", (), {"status": status, "reason": "x"})()
    return HttpError(resp, b"{}")


# --- ops ---


def test_get_returns_event() -> None:
    events = _Events(result={"id": "abc"})
    out = cal.run(_Service(events), _ns("get", calendar_id="c", event_id="abc"))
    assert out == {"id": "abc"}
    assert events.calls == [("get", "c", "abc")]


def test_create_inserts_parsed_body() -> None:
    events = _Events(result={"id": "n1"})
    out = cal.run(_Service(events), _ns("create", calendar_id="c", body='{"summary":"X"}'))
    assert out["id"] == "n1"
    assert events.calls == [("insert", "c", {"summary": "X"})]


def test_update_uses_patch() -> None:
    events = _Events(result={"id": "e1"})
    cal.run(_Service(events), _ns("update", calendar_id="c", event_id="e1", body="{}"))
    assert events.calls[0][0] == "patch"


def test_delete_returns_empty() -> None:
    events = _Events(result="")
    out = cal.run(_Service(events), _ns("delete", calendar_id="c", event_id="e1"))
    assert out == {}


def test_missing_event_exits_3() -> None:
    events = _Events(exc=_http_error(404))
    with pytest.raises(SystemExit) as exc:
        cal.run(_Service(events), _ns("get", calendar_id="c", event_id="gone"))
    assert exc.value.code == cal.EXIT_NOT_FOUND


def test_primary_403_hint(capsys) -> None:
    events = _Events(exc=_http_error(403))
    with pytest.raises(SystemExit):
        cal.run(_Service(events), _ns("create", calendar_id="primary", body="{}"))
    assert "personal Google account" in capsys.readouterr().err


def test_bad_json_body_exits(capsys) -> None:
    events = _Events()
    with pytest.raises(SystemExit):
        cal.run(_Service(events), _ns("create", calendar_id="c", body="{nope"))
    assert "not valid JSON" in capsys.readouterr().err


# --- credentials resolution ---


def _write_local(tmp_path: Path, body: str) -> None:
    (tmp_path / "relay.local.toml").write_text(body)


def test_resolve_creds_literal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_local(tmp_path, '[calendar]\nservice_account_file = "/keys/sa.json"\n')
    monkeypatch.setenv("RELAY_RELAY_OS_ROOT", str(tmp_path))
    assert cal.resolve_credentials_path() == "/keys/sa.json"


def test_resolve_creds_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_local(tmp_path, '[calendar]\nservice_account_file = "env:GCAL_SA_KEY"\n')
    monkeypatch.setenv("RELAY_RELAY_OS_ROOT", str(tmp_path))
    monkeypatch.setenv("GCAL_SA_KEY", "/run/sa.json")
    assert cal.resolve_credentials_path() == "/run/sa.json"


def test_resolve_creds_missing_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_local(tmp_path, 'user = "marc"\n')
    monkeypatch.setenv("RELAY_RELAY_OS_ROOT", str(tmp_path))
    with pytest.raises(SystemExit):
        cal.resolve_credentials_path()
