"""Test isolation guards.

Some tests invoke `relay init`, which calls `_try_install_shim` — that walks
the real user's `$PATH` and may symlink into `~/.local/bin/` on the host. To
prevent test runs from contaminating the developer's home, redirect `HOME`
and `PATH` to disposable values for every test by default. Tests that need
the real env can override these with `monkeypatch.setenv` themselves.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest


_TEMPLATES_RELAY_OS = (
    Path(__file__).resolve().parents[1]
    / "src" / "relay" / "resources" / "templates" / "relay-os"
)


def seed_direct_body_workflow(relay_os: Path) -> None:
    """Copy the shipped `direct/body` workflow + skill into a test repo.

    The scaffolder freezes `direct/body` onto workflow-less recurring/retire
    tasks (real repos get it from `relay init`), so any fixture that scaffolds
    one needs the file present. Copying the shipped bytes keeps it identical to
    the test-side re-seed, so a committed copy stays diff-clean.
    """
    skill_dst = relay_os / "skills" / "direct" / "body"
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        _TEMPLATES_RELAY_OS / "skills" / "direct" / "body",
        skill_dst,
        dirs_exist_ok=True,
    )
    wf_dst = relay_os / "workflows" / "direct" / "body.md"
    wf_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(_TEMPLATES_RELAY_OS / "workflows" / "direct" / "body.md", wf_dst)


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
    real slack behavior (test_notification.py, test_validate.py probe tests)
    re-monkeypatch these — autouse runs first, test-local setattr wins.
    """
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test-stub")

    def _noop_post(*args, **kwargs):
        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("relay.notification.slack.requests.post", _noop_post, raising=False)


@pytest.fixture(autouse=True)
def _clear_supervised_session_env(monkeypatch):
    """Detach the test run from any supervising `relay launch`.

    A supervisor exports `RELAY_DONE_SENTINEL` (the "session done" sentinel
    file it polls) and `RELAY_SUPERVISED` into the agent's env, and those leak
    into anything the agent spawns — including this test suite. Many tests
    invoke `relay bump` / `mark done` / `panic` (which call
    `emit_done_marker`) or call `emit_done_marker` directly; left unscrubbed,
    each one writes the *live* inherited sentinel and the supervisor SIGTERMs
    the whole process group, killing the test run mid-flight. Clearing both
    here makes the suite hermetic regardless of how it was launched. Tests
    that exercise the supervisor set `RELAY_DONE_SENTINEL` themselves
    (autouse runs first, so their `monkeypatch.setenv` wins)."""
    monkeypatch.delenv("RELAY_DONE_SENTINEL", raising=False)
    monkeypatch.delenv("RELAY_SUPERVISED", raising=False)


@pytest.fixture(autouse=True)
def _stub_git(monkeypatch, request):
    """Default-off git sync so the bulk of tests don't touch git.

    The git analogue of `_stub_slack`: most tests run in a non-git tmp dir
    and only care about file/Slack effects, so `relay.git.sync_task_state`
    is stubbed to a no-op. Without this, every `mark` / `bump` / `create`
    test would shell out to git on a non-git path (noise at best) and the
    tests that fake `subprocess.run` for the agent launch would break.

    Tests that exercise real git sync request the `git_repo` fixture (full
    real-git harness) or the `real_git` marker fixture (for branches like
    "not a git repo" that need the real helper without a repo); this stub
    steps aside for both (autouse runs first, but the opt-in is detected via
    the requested fixture names, so the real helper runs there)."""
    if {"git_repo", "real_git"} & set(request.fixturenames):
        return
    # Both public sync entry points are stubbed: `sync_task_state` (mark / bump /
    # create / panic) and `sync_paths` (the multi-path variant `relay ticket`
    # authoring uses). Stubbing only the former would let authoring shell out to
    # real git on a non-git tmp path and break the faked-subprocess tests.
    monkeypatch.setattr("relay.git.sync_task_state", lambda *a, **k: None)
    monkeypatch.setattr("relay.git.sync_paths", lambda *a, **k: None)


@pytest.fixture
def real_git():
    """Opt a test out of the `_stub_git` no-op without a full repo harness."""
    return None


# --- real-git harness ----------------------------------------------------------
#
# Ticket A builds the first real-git test fixture (today git is fully mocked).
# B and C reuse it: B extends with feature-branch assertions, C reuses it for
# its bespoke call sites. The shape mirrors the live repo — a git worktree
# whose `.git` is at the toplevel and whose `relay.toml` lives in a nested
# `relay-os/`, with a **bare** `origin` so `push` works without a network.


@dataclass
class GitRepo:
    """A real git working tree with a bare `origin`, laid out like the live repo.

    `root` is the git toplevel (holds `.git`); `relay_os` is the nested
    `relay-os/` that holds `relay.toml` (and is the cwd commands run from);
    `origin` is the bare remote that pushes land in.
    """

    root: Path
    relay_os: Path
    origin: Path

    def git(self, *args: str, cwd: Path | None = None) -> str:
        out = subprocess.run(
            ["git", "-C", str(cwd or self.root), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout

    def checkout_branch(self, name: str) -> None:
        """Switch the working tree onto a new feature branch (for B's tests)."""
        self.git("checkout", "-b", name)

    def origin_subjects(self) -> list[str]:
        """Commit subjects on `origin/main`, newest first."""
        out = self.git("log", "--format=%s", "main", cwd=self.origin)
        return [line for line in out.splitlines() if line]

    def origin_tracks(self, relpath: str) -> bool:
        """True when `relpath` (repo-relative) is committed on `origin/main`."""
        out = self.git("ls-tree", "-r", "--name-only", "main", cwd=self.origin)
        return relpath in out.splitlines()

    def push_competing_commit(self, relpath: str, text: str) -> None:
        """Land an unrelated commit straight on `origin/main` from a throwaway clone.

        Simulates another relay process (or machine) advancing the control
        branch under us, so B's cross-branch land hits a non-fast-forward and
        must refetch/rebuild. The file is committed and pushed without touching
        this working tree.
        """
        clone = self.origin.parent / "competing-clone"
        if not clone.exists():
            self.git("clone", str(self.origin), str(clone), cwd=self.origin.parent)
            self.git("config", "user.email", "rival@example.com", cwd=clone)
            self.git("config", "user.name", "Rival", cwd=clone)
            self.git("config", "commit.gpgsign", "false", cwd=clone)
            # The bare origin's symbolic HEAD isn't `main`, so the fresh clone
            # lands on an unborn default branch — pin it to origin/main.
            self.git("checkout", "-B", "main", "origin/main", cwd=clone)
        else:
            self.git("pull", "--ff-only", "origin", "main", cwd=clone)
        target = clone / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        self.git("add", "--", relpath, cwd=clone)
        self.git("commit", "-m", f"competing: {relpath}", cwd=clone)
        self.git("push", "origin", "main", cwd=clone)


def init_git_repo(tmp_path: Path) -> GitRepo:
    """Create a git working tree + bare `origin`, seeded with a relay-os layout.

    The control branch is `main`. The initial commit lands the config and an
    empty `tasks/` dir, then is pushed to `origin` so later `push`es are
    fast-forwards.
    """
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", str(origin)],
        check=True, capture_output=True, text=True,
    )

    root = tmp_path / "repo"
    relay_os = root / "relay-os"
    relay_os.mkdir(parents=True)

    def _g(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True, text=True,
        )

    _g("init", "-b", "main")
    _g("config", "user.email", "test@example.com")
    _g("config", "user.name", "Relay Test")
    _g("config", "commit.gpgsign", "false")

    (relay_os / "relay.toml").write_text(
        dedent(
            """
            version = 1
            default_status = "draft"
            [agents.claude]
            cli = "claude"
            auto = "-p"
            file = "CLAUDE.md"
            [notification]
            channels = ["slack"]
            [notification.slack]
            webhook = "env:SLACK_WEBHOOK_URL"
            """
        ).lstrip()
    )
    (relay_os / "relay.local.toml").write_text('user = "marc"\n')
    workflows = relay_os / "workflows"
    workflows.mkdir()
    (workflows / "code.md").write_text(
        dedent(
            """
            ---
            name: code
            description: tiny.
            steps:
              - name: implement
              - name: review
            ---

            ## implement
            Write the code.
            """
        ).lstrip()
    )
    seed_direct_body_workflow(relay_os)
    (relay_os / "tasks").mkdir()

    _g("remote", "add", "origin", str(origin))
    _g("add", "-A")
    _g("commit", "-m", "init relay-os")
    _g("push", "-u", "origin", "main")

    return GitRepo(root=root, relay_os=relay_os, origin=origin)


@pytest.fixture
def git_repo(tmp_path, monkeypatch) -> GitRepo:
    """A real-git repo with the working tree on `main`, cwd set to `relay-os/`.

    Requesting this fixture opts the test out of the `_stub_git` no-op, so
    `relay.git.sync_task_state` runs for real against this repo.
    """
    repo = init_git_repo(tmp_path)
    monkeypatch.chdir(repo.relay_os)
    return repo
