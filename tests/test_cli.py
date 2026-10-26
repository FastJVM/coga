"""Config leniency at the CLI surface — a clone without `coga.local.toml`.

A teammate's fresh clone of a coga repo has no gitignored `coga.local.toml`
yet. `coga --help`, per-command `--help`, and the read-only commands must
still run there; only commands that act *as* someone keep the hard
"No `user` set" error (raised from their own strict `load_config()`).
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app, main
from coga.repl_supervisor import ASSIST_BRANCH_ENV, EXPECTED_TASK_ENV


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


TICKET = """
---
title: X
status: draft
mode: agent
owner: marc
agent: claude
workflow: null
---

## Description

<!-- coga:blackboard -->
"""


@pytest.fixture
def clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A coga repo as a teammate first sees it: shared config committed,
    no gitignored `coga.local.toml`."""
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "tasks" / "fix-retry-logic" / "ticket.md", TICKET)
    monkeypatch.chdir(company)
    # main() registers alias placeholders on the module-global `app`;
    # re-registering across tests would accumulate duplicates.
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    return company


def test_root_help_runs_without_user(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["coga", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "Organize agent work" in capsys.readouterr().out


def test_windows_cli_uses_utf8_when_output_is_redirected(clone, monkeypatch):
    import io
    import sys
    from types import SimpleNamespace
    from coga import cli

    def command():
        print("Café → 語")
        print("Café → 語", file=sys.stderr)
        raise SystemExit(0)

    output, errors = io.BytesIO(), io.BytesIO()
    stdout = io.TextIOWrapper(output, encoding="cp1252")
    stderr = io.TextIOWrapper(errors, encoding="cp1252")
    monkeypatch.setattr(cli, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(cli, "app", command)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    monkeypatch.setattr(sys, "argv", ["coga", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    stdout.flush()
    stderr.flush()
    assert output.getvalue().decode("utf-8").strip() == "Café → 語"
    assert errors.getvalue().decode("utf-8").strip() == "Café → 語"


def test_command_help_runs_without_user(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Even a mutating command's `--help` must work — Typer prints help before
    the command body ever loads config strictly."""
    monkeypatch.setattr("sys.argv", ["coga", "create", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "--help" in capsys.readouterr().out


def test_pick_alias_expands_to_megalaunch(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`coga pick` is a built-in default alias for `megalaunch --pick`."""
    monkeypatch.setattr("sys.argv", ["coga", "pick"])
    # megalaunch needs a TTY, so the picker exits — but the expansion banner
    # printed before dispatch proves the alias resolves.
    with pytest.raises(SystemExit):
        main()
    assert "→ coga megalaunch --pick" in capsys.readouterr().err


@pytest.mark.parametrize("termination", ["return", "exit", "crash"])
def test_inherited_assist_still_sweeps_cli_state(
    clone: Path,
    monkeypatch: pytest.MonkeyPatch,
    termination: str,
) -> None:
    """An assist session has no separate publication path: the sweep runs."""
    _write(clone / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.setenv(ASSIST_BRANCH_ENV, "feature/review")
    monkeypatch.setenv(EXPECTED_TASK_ENV, str(clone / "tasks" / "fix-retry-logic"))
    monkeypatch.setattr("sys.argv", ["coga", "bump", "fix-retry-logic"])
    sweeps: list[object] = []
    monkeypatch.setattr("coga.cli._sweep_coga_state", sweeps.append)

    def terminate() -> None:
        if termination == "exit":
            raise SystemExit(2)
        if termination == "crash":
            raise RuntimeError("command failed before publication")

    monkeypatch.setattr("coga.cli.app", terminate)

    if termination == "exit":
        with pytest.raises(SystemExit, match="2"):
            main()
    elif termination == "crash":
        with pytest.raises(RuntimeError, match="before publication"):
            main()
    else:
        main()

    assert len(sweeps) == 1


def test_status_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0
    assert "fix-retry-logic" in result.output


def test_show_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["show", "fix-retry-logic"])
    assert result.exit_code == 0
    assert "fix-retry-logic" in result.output


def test_validate_runs_and_warns_without_user(clone: Path) -> None:
    """`coga validate` still runs on a fresh clone and points at the setup
    step as a warn-level finding instead of dying (or validating clean)."""
    result = CliRunner().invoke(app, ["validate", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    missing_user = [i for i in payload["issues"] if i["kind"] == "missing-user"]
    assert len(missing_user) == 1
    assert missing_user[0]["severity"] == "warn"
    assert "coga.local.toml" in missing_user[0]["message"]


def test_task_validate_runs_and_warns_without_user(clone: Path) -> None:
    result = CliRunner().invoke(
        app, ["validate", "--task", "fix-retry-logic", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    missing_user = [i for i in payload["issues"] if i["kind"] == "missing-user"]
    assert len(missing_user) == 1
    assert missing_user[0]["severity"] == "warn"


def test_usage_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["usage"])
    assert result.exit_code == 0


def test_skill_status_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["skill", "status"])
    assert result.exit_code == 0
    assert "No `user` set" not in result.output


def test_recurring_list_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["recurring", "list"])
    assert result.exit_code == 0
    assert "(no recurring templates)" in result.output


def test_mutating_command_still_requires_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["bump", "fix-retry-logic"])
    assert result.exit_code == 2
    assert "No `user` set in coga.local.toml" in result.output


def test_validate_does_not_warn_when_user_set(clone: Path) -> None:
    _write(clone / "coga.local.toml", 'user = "marc"\n')
    result = CliRunner().invoke(app, ["validate", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [i for i in payload["issues"] if i["kind"] == "missing-user"] == []


@pytest.mark.parametrize("failure", [SystemExit(9), OSError("spawn failed"), KeyboardInterrupt()])
def test_control_relay_suppresses_parent_sweep_and_resets_after_failure(
    clone: Path, monkeypatch: pytest.MonkeyPatch, failure: BaseException
) -> None:
    from coga.recurring_runner import control_relay_started

    monkeypatch.setattr("sys.argv", ["coga", "recurring"])
    sweeps: list[object] = []
    monkeypatch.setattr("coga.git.sync_coga_state", sweeps.append)
    prior = control_relay_started.get()

    def relay() -> None:
        control_relay_started.set(True)
        raise failure

    monkeypatch.setattr("coga.cli.app", relay)
    with pytest.raises(type(failure)):
        main()
    assert sweeps == []
    assert control_relay_started.get() == prior

    # A subsequent invocation in the same Python process still owns its sweep.
    monkeypatch.setattr("coga.cli.app", lambda: None)
    main()
    assert len(sweeps) == 1


@pytest.mark.parametrize("child_exit", [None, SystemExit(0), SystemExit(3)])
def test_withheld_launch_return_skips_the_sweep_and_keeps_the_exit(
    clone: Path, monkeypatch: pytest.MonkeyPatch, child_exit: SystemExit | None
) -> None:
    from coga import git

    monkeypatch.setattr("sys.argv", ["coga", "launch", "x"])
    sweeps: list[object] = []
    monkeypatch.setattr("coga.git.sync_coga_state", sweeps.append)

    def launch_with_refused_return() -> None:
        git.state_sweep_withheld.set(True)
        if child_exit is not None:
            raise child_exit

    monkeypatch.setattr("coga.cli.app", launch_with_refused_return)
    if child_exit is None:
        main()
    else:
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == child_exit.code
    assert sweeps == []
    assert git.state_sweep_withheld.get() is False

    # The next invocation in the same process sweeps again.
    monkeypatch.setattr("coga.cli.app", lambda: None)
    main()
    assert len(sweeps) == 1


@pytest.mark.parametrize(
    ("argv", "sweeps_expected"),
    [
        (["coga", "launch", "x", "--prompt-report"], 0),
        (["coga", "launch", "--prompt-report", "bootstrap/orient"], 0),
        (["coga", "launch", "x"], 1),
    ],
)
def test_prompt_report_skips_the_sweep(
    clone: Path,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    sweeps_expected: int,
) -> None:
    """A prompt report must not publish dirty knowledge edits it is measuring."""
    monkeypatch.setattr("sys.argv", argv)
    sweeps: list[object] = []
    monkeypatch.setattr("coga.git.sync_coga_state", sweeps.append)
    monkeypatch.setattr("coga.cli.app", lambda: None)
    main()
    assert len(sweeps) == sweeps_expected


def test_launch_entry_refusal_through_main_skips_the_sweep(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coga import git

    monkeypatch.setattr("sys.argv", ["coga", "launch", "x"])
    sweeps: list[object] = []
    monkeypatch.setattr("coga.git.sync_coga_state", sweeps.append)

    def refused() -> None:
        raise SystemExit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)

    monkeypatch.setattr("coga.cli.app", refused)
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    assert sweeps == []


@pytest.fixture
def published_repo(git_repo, monkeypatch: pytest.MonkeyPatch):
    """The real-git harness, with `clone`'s guard against alias re-registration."""
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    return git_repo


def _control_log(repo) -> str:
    from coga import git

    data = git.tree_bytes(repo.root, "origin/main", "coga/log.md")
    return "" if data is None else data.decode("utf-8")


def _write_log_line(message: str) -> None:
    from coga.config import load_config
    from coga.logfile import append_log

    append_log(load_config(), "fix-retry-logic", "system", message)


@pytest.mark.parametrize("retained", ["exit", "withheld"])
def test_skipped_sweep_names_log_lines_left_off_control(
    published_repo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    retained: str,
) -> None:
    """A command that keeps its state local still reports the audit line it left."""
    from coga import git

    monkeypatch.setattr("sys.argv", ["coga", "launch", "x"])

    def command_that_retains_state() -> None:
        _write_log_line("script exited with code 75")
        if retained == "withheld":
            git.state_sweep_withheld.set(True)
            return
        raise SystemExit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)

    monkeypatch.setattr("coga.cli.app", command_that_retains_state)
    if retained == "exit":
        with pytest.raises(SystemExit):
            main()
    else:
        main()

    err = capsys.readouterr().err
    assert "1 log line(s) are not on control" in err
    assert "[fix-retry-logic] [system] script exited with code 75" in err
    assert "coga run publish-state log.md" in err
    # Reported, not published: the retained line is still only local.
    assert "script exited with code 75" not in _control_log(published_repo)


def test_skipped_sweep_does_not_name_log_lines_already_on_control(
    published_repo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from coga import git
    from coga.config import load_config

    monkeypatch.setattr("sys.argv", ["coga", "launch", "x"])

    def command_that_publishes_its_line_then_withholds() -> None:
        _write_log_line("launched")
        assert git.sync_log(load_config(), message="Log: fix-retry-logic")
        git.state_sweep_withheld.set(True)

    monkeypatch.setattr("coga.cli.app", command_that_publishes_its_line_then_withholds)
    main()

    assert "not on control" not in capsys.readouterr().err


def test_readonly_command_does_not_warn_about_an_unchanged_log(
    published_repo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _write_log_line("previous command retained this line")
    monkeypatch.setattr("sys.argv", ["coga", "status"])
    monkeypatch.setattr("coga.cli.app", lambda: None)
    main()

    assert "not on control" not in capsys.readouterr().err


def test_completed_sweep_leaves_no_unpublished_log_warning(
    published_repo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["coga", "slack", "x"])
    monkeypatch.setattr("coga.cli.app", lambda: _write_log_line("slack: hi"))
    main()

    assert "not on control" not in capsys.readouterr().err
    assert "slack: hi" in _control_log(published_repo)


def test_completed_sweep_names_a_new_log_excluded_by_gitignore(
    published_repo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    ignore = published_repo.root / ".gitignore"
    with ignore.open("a", encoding="utf-8") as handle:
        handle.write("coga/log.md\n")
    published_repo.git("add", ".gitignore")
    published_repo.git("commit", "-m", "ignore the audit log")
    published_repo.git("push", "origin", "main")
    monkeypatch.setattr("sys.argv", ["coga", "create", "Review ignored log"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    err = capsys.readouterr().err
    assert "1 log line(s) are not on control" in err
    assert "[review-ignored-log] [human:marc] created (status=draft)" in err
    assert "coga run publish-state log.md" in err
    assert "created (status=draft)" not in _control_log(published_repo)


def test_skipped_sweep_with_git_disabled_keeps_its_own_note(
    published_repo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from coga import git

    with (published_repo.coga_os / "coga.toml").open("a", encoding="utf-8") as handle:
        handle.write("\n[git]\nenabled = false\n")
    monkeypatch.setattr("sys.argv", ["coga", "launch", "x"])

    def retains() -> None:
        _write_log_line("script exited with code 75")
        raise SystemExit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)

    monkeypatch.setattr("coga.cli.app", retains)
    with pytest.raises(SystemExit):
        main()

    assert "not on control" not in capsys.readouterr().err


@pytest.mark.parametrize("argv", [
    ["launch", "windows-agent"],
    ["chat"],
    ["build"],
    ["ticket", "A new Windows draft"],
    ["ticket", "--pick-agent", "A new Windows draft"],
    ["megalaunch"],
    ["megalaunch", "--pick"],
])
def test_windows_agent_refusal_keeps_checkout_and_control(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys, argv: list[str]
) -> None:
    from coga import launch as launch_module

    ticket = git_repo.coga_os / "tasks" / "windows-agent.md"
    _write(ticket, TICKET)
    git_repo.git("add", ".")
    git_repo.git("commit", "-m", "seed Windows agent ticket")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/keep-this-checkout")
    ticket.write_text(ticket.read_text(encoding="utf-8") + "\nUnpublished Café notes.\n", encoding="utf-8", newline="\n")
    (git_repo.coga_os / "log.md").write_text("Unpublished log.\n", encoding="utf-8", newline="\n")
    monkeypatch.chdir(git_repo.coga_os)
    monkeypatch.setattr(launch_module, "agent_sessions_supported", lambda: False, raising=False)
    monkeypatch.setattr("sys.argv", ["coga", *argv])
    before = {p.relative_to(git_repo.root): p.read_bytes() for p in git_repo.coga_os.rglob("*") if p.is_file()}
    head = git_repo.git("rev-parse", "HEAD")
    control = git_repo.git("rev-parse", "main", cwd=git_repo.origin)
    index = git_repo.git("ls-files", "--stage")

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code != 0
    output = capsys.readouterr()
    assert "agent sessions are not supported on native Windows yet" in output.err
    assert "windows-native/03-interactive-coga-launch-on-native-windows" in output.err
    assert {p.relative_to(git_repo.root): p.read_bytes() for p in git_repo.coga_os.rglob("*") if p.is_file()} == before
    assert git_repo.git("branch", "--show-current").strip() == "feature/keep-this-checkout"
    assert git_repo.git("rev-parse", "HEAD") == head
    assert git_repo.git("rev-parse", "main", cwd=git_repo.origin) == control
    assert git_repo.git("ls-files", "--stage") == index
