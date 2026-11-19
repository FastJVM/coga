"""Credential resolution for the packaged Google helper skills.

`gcal.py` and `gmail.py` read credentials from the environment that a ticket's
`secrets:` frontmatter populates, never from Coga config tables.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SKILLS = (Path(__file__).resolve().parents[1]
          / "src/coga/resources/templates/coga/bootstrap/skills/coga")


def _load(rel: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SKILLS / rel)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gcal = _load("google-calendar/gcal.py", "coga_skill_gcal")
gmail = _load("gmail/gmail.py", "coga_skill_gmail")

KEY = {"type": "service_account", "client_email": "sa@example.iam.gserviceaccount.com"}
GMAIL_ENV = {
    "GMAIL_CLIENT_ID": "id",
    "GMAIL_CLIENT_SECRET": "secret",
    "GMAIL_REFRESH_TOKEN": "refresh",
    "GMAIL_USER": "me@example.com",
}


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> pytest.MonkeyPatch:
    for var in (gcal.JSON_VAR, gcal.FILE_VAR, *GMAIL_ENV):
        monkeypatch.delenv(var, raising=False)
    # A coga.local.toml carrying the retired tables must not be consulted.
    (tmp_path / "coga.local.toml").write_text(
        '[calendar]\nservice_account_file = "/nope.json"\n'
        '[gmail]\nclient_id = "x"\nclient_secret = "x"\n'
        'refresh_token = "x"\nuser = "x"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("COGA_COGA_OS_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return monkeypatch


def test_gcal_reads_key_contents_from_env(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv(gcal.JSON_VAR, json.dumps(KEY))
    clean_env.setenv(gcal.FILE_VAR, "/does/not/exist.json")

    assert gcal.resolve_service_account_info() == KEY


def test_gcal_reads_key_file_path_from_env(clean_env: pytest.MonkeyPatch,
                                           tmp_path: Path) -> None:
    key_file = tmp_path / "sa.json"
    key_file.write_text(json.dumps(KEY), encoding="utf-8")
    clean_env.setenv(gcal.FILE_VAR, str(key_file))

    assert gcal.resolve_service_account_info() == KEY


def test_gcal_ignores_local_config_and_names_both_variables(
        clean_env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        gcal.resolve_service_account_info()

    assert exc.value.code == gcal.EXIT_ERROR
    err = capsys.readouterr().err
    assert gcal.JSON_VAR in err and gcal.FILE_VAR in err
    assert "coga.local.toml" not in err


def test_gcal_rejects_non_object_key(clean_env: pytest.MonkeyPatch,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    clean_env.setenv(gcal.JSON_VAR, "not json")

    with pytest.raises(SystemExit):
        gcal.resolve_service_account_info()

    assert "not valid JSON" in capsys.readouterr().err


def test_gmail_reads_credentials_from_env(clean_env: pytest.MonkeyPatch) -> None:
    for var, value in GMAIL_ENV.items():
        clean_env.setenv(var, value)

    assert gmail.resolve_gmail_config() == {
        "client_id": "id",
        "client_secret": "secret",
        "refresh_token": "refresh",
        "user": "me@example.com",
    }


def test_gmail_names_every_missing_variable(clean_env: pytest.MonkeyPatch,
                                            capsys: pytest.CaptureFixture[str]) -> None:
    clean_env.setenv("GMAIL_USER", "me@example.com")

    with pytest.raises(SystemExit) as exc:
        gmail.resolve_gmail_config()

    assert exc.value.code == gmail.EXIT_ERROR
    err = capsys.readouterr().err
    for var in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
        assert var in err
    assert "GMAIL_USER" not in err
