"""Test isolation guards.

Some tests invoke `relay init`, which calls `_try_install_shim` — that walks
the real user's `$PATH` and may symlink into `~/.local/bin/` on the host. To
prevent test runs from contaminating the developer's home, redirect `HOME`
and `PATH` to disposable values for every test by default. Tests that need
the real env can override these with `monkeypatch.setenv` themselves.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path_factory, monkeypatch):
    # Pointing HOME at a tmp dir is enough — `_try_install_shim` resolves
    # `Path.home() / ".local" / "bin"` against entries on $PATH, and the fake
    # home dir won't be on the host's real PATH. We deliberately leave PATH
    # alone so subprocess calls (git, etc.) still work in tests.
    fake_home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(fake_home))


@pytest.fixture(autouse=True)
def _stub_slack(monkeypatch):
    """Default-on Slack so commands don't crash on `$SLACK_WEBHOOK_URL` unset.

    Sets a fake webhook and stubs `requests.post` to a no-op. Tests that want
    real slack behavior (test_slack.py, test_validate.py probe tests)
    re-monkeypatch these — autouse runs first, test-local setattr wins.
    """
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test-stub")

    def _noop_post(*args, **kwargs):
        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("relay.slack.requests.post", _noop_post, raising=False)
