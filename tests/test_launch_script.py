from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

import coga
from coga.cli import app
from coga.create import create_task
from coga.config import load_config
from coga.tasks import list_tasks
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "ops.md",
        """
        ---
        name: ops
        description: single-step.
        steps:
          - name: run
            skills:
              - ops/checker
        ---
        """,
    )
    _write(
        company / "skills" / "ops" / "checker" / "SKILL.md",
        """
        ---
        name: ops/checker
        description: runs a health check.
        script: check.sh
        ---

        Runs the check.
        """,
    )
    script = company / "skills" / "ops" / "checker" / "check.sh"
    script.write_text(
        "#!/bin/sh\n"
        "{\n"
        "  echo \"token=$token\"\n"
        "  echo \"source=$TEST_TOKEN\"\n"
        "  echo \"slug=$COGA_TASK_SLUG\"\n"
        "  echo \"dir=$COGA_TASK_DIR\"\n"
        "  echo \"blackboard=$COGA_TASK_BLACKBOARD\"\n"
        "} > \"$PWD/script-output.txt\"\n"
    )
    script.chmod(0o755)

    monkeypatch.chdir(company)
    return company


def test_script_mode_executes_and_injects_secrets(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_TOKEN", "secret-abc")
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    # Declare the secret inline on the ticket: scoped `token` resolved from the
    # operator's `TEST_TOKEN` env var.
    _set_ticket_secrets(ref, [{"token": "env:TEST_TOKEN"}])

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "check"])
    assert result.exit_code == 0, result.output

    # Script wrote to the host repo (parent of coga/) with the secret
    output = (cfg.repo_root.parent / "script-output.txt").read_text()
    assert "token=secret-abc" in output
    # The raw source var `TEST_TOKEN` is scrubbed from the child env.
    assert "source=\n" in output
    assert "slug=check" in output
    # File-form task has no per-task directory, so COGA_TASK_DIR is the
    # `tasks/` parent the ticket file lives in.
    assert f"dir={ref.path.parent.resolve()}" in output
    # Single-file format: the blackboard region lives in the ticket file, so
    # COGA_TASK_BLACKBOARD points at the ticket itself.
    assert f"blackboard={ref.ticket_path.resolve()}" in output

    # Log records launch + exit (in the repo-global log)
    log = (repo / "log.md").read_text()
    assert "launched as a script" in log
    assert "script exited with code 0" in log


def _set_ticket_secrets(ref, value) -> None:
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["secrets"] = value
    t.write(ref.ticket_path)


def test_script_mode_fails_loud_on_unset_declared_secret(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TEST_TOKEN", raising=False)
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    _set_ticket_secrets(ref, [{"token": "env:TEST_TOKEN"}])

    result = CliRunner().invoke(app, ["launch", "check"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "token" in combined and "TEST_TOKEN" in combined
    # Fail-loud means the script never ran.
    assert not (cfg.repo_root.parent / "script-output.txt").exists()
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "active"
    log = (repo / "log.md").read_text()
    assert "started (active" not in log


def test_script_mode_least_privilege_empty_list_injects_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_TOKEN", "secret-abc")
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    _set_ticket_secrets(ref, [])

    result = CliRunner().invoke(app, ["launch", "check"])
    assert result.exit_code == 0, result.output
    output = (cfg.repo_root.parent / "script-output.txt").read_text()
    # `secrets: []` is a strict lockdown — no scoped secret is injected, so the
    # `token` NAME is empty in the child even though TEST_TOKEN is set in the env.
    assert "token=\n" in output
    # Scrubbing is tied to a ticket's inline `env:` refs; with none declared,
    # the operator's own `TEST_TOKEN` env var is not touched. The lockdown is
    # that Coga injects no *scoped* secret, not that it sanitizes the whole env.
    assert "source=secret-abc\n" in output


def test_script_mode_rejects_agent_override(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "check", "--agent", "claude"])
    assert result.exit_code == 2
    assert "--agent is only supported for agent launches" in (
        result.output + (result.stderr or "")
    )


def test_script_mode_nonzero_exit_logged(repo: Path) -> None:
    script = repo / "skills" / "ops" / "checker" / "check.sh"
    script.write_text("#!/bin/sh\nexit 3\n")
    script.chmod(0o755)

    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Fail", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fail"])
    assert result.exit_code == 3
    ref = list_tasks(cfg)[0]
    log = (repo / "log.md").read_text()
    assert "script exited with code 3" in log


def test_script_launch_refreshes_launch_checkout(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean script launch ends with the end-of-run refresh, exactly once."""
    refreshed: list[Path] = []
    monkeypatch.setattr(
        "coga.git.refresh_coga_state_from_control",
        lambda cfg, **kwargs: refreshed.append(cfg.repo_root),
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(app, ["launch", "check"])

    assert result.exit_code == 0, result.output
    assert len(refreshed) == 1
    assert refreshed[0].resolve() == repo.resolve()


def test_failed_script_launch_still_refreshes_launch_checkout(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing script exits through the supervisor's error path; the refresh
    still runs (once) before the exit surfaces."""
    script = repo / "skills" / "ops" / "checker" / "check.sh"
    script.write_text("#!/bin/sh\nexit 3\n")
    script.chmod(0o755)
    refreshed: list[Path] = []
    monkeypatch.setattr(
        "coga.git.refresh_coga_state_from_control",
        lambda cfg, **kwargs: refreshed.append(cfg.repo_root),
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Fail", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(app, ["launch", "fail"])

    assert result.exit_code == 3
    assert len(refreshed) == 1


def test_bootstrap_script_launch_is_stateless(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This is the one script test that executes a *real* bootstrap script
    # (`recurring-scan/run.py`), which imports `coga` in a `sys.executable`
    # child. `build_launch_env` inherits `os.environ`, but pytest's
    # `pythonpath = ["src"]` only patches the parent's `sys.path` — so the
    # child can import coga solely by accident of it being pip-installed in
    # the running interpreter. Export the path the parent actually imported
    # from to make the test hermetic under a bare `pytest`.
    monkeypatch.setenv("PYTHONPATH", str(Path(coga.__file__).resolve().parents[1]))

    result = CliRunner().invoke(app, ["launch", "bootstrap/recurring-scan"])
    assert result.exit_code == 0, result.output
    assert "bootstrap/recurring-scan: script ran successfully" in result.output

    cfg = load_config(repo)
    assert list_tasks(cfg) == []
    log_path = repo / "log.md"
    assert not log_path.exists() or log_path.read_text() == ""


def test_draft_bare_script_workflow_recomputes_dispatch_after_activation(
    repo: Path,
) -> None:
    """Activation freezes a hand-authored workflow ref before dispatch.

    Before activation there is no frozen current step to inspect. Once step 1
    is seeded, launch must re-deduce the script-backed skill instead of taking
    the agent/TTY path cached from the draft shape.
    """
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Draft check",
        workflow_name="ops",
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["workflow"] = "ops"
    ticket.frontmatter.pop("step", None)
    ticket.write(ref.ticket_path)

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert Ticket.read(ref.ticket_path).status == "done"


# --- deduced dispatch ----------------------------------------------------------
#
# There is no `mode:` frontmatter: `is_script_launch` deduces script-vs-agent
# per launch — a script-backed current step, else the ticket's own `script:`,
# else an agent launch.


def test_is_script_launch_deduces_from_script_backed_step(repo: Path) -> None:
    from coga.commands.launch_script import is_script_launch

    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.script is None
    assert is_script_launch(cfg, ticket) is True


def test_is_script_launch_deduces_from_ticket_owned_script(repo: Path) -> None:
    from coga.commands.launch_script import is_script_launch

    # Strip the skill's `script:` so the step is not script-backed; the
    # ticket's own `script:` alone must carry the deduction.
    skill_md = repo / "skills" / "ops" / "checker" / "SKILL.md"
    skill_md.write_text(
        "---\nname: ops/checker\ndescription: runs a health check.\n---\n"
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active", script="inline",
    )
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    assert is_script_launch(cfg, ticket) is True


def test_is_script_launch_deduces_agent_when_no_script_anywhere(repo: Path) -> None:
    from coga.commands.launch_script import is_script_launch

    skill_md = repo / "skills" / "ops" / "checker" / "SKILL.md"
    skill_md.write_text(
        "---\nname: ops/checker\ndescription: runs a health check.\n---\n"
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    assert is_script_launch(cfg, ticket) is False


def test_agent_deduction_without_tty_fails_on_tty_gate(repo: Path) -> None:
    """The accepted behavior change: a task whose script vanished deduces to
    an agent launch, and a TTY-less context then fails on the TTY gate rather
    than a missing-script bail."""
    skill_md = repo / "skills" / "ops" / "checker" / "SKILL.md"
    skill_md.write_text(
        "---\nname: ops/checker\ndescription: runs a health check.\n---\n"
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    result = CliRunner().invoke(app, ["launch", "check"])
    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "an agent launch requires a TTY" in combined


def test_script_launch_signals_done_sentinel_for_supervisor(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful script launch writes the slug-scoped done sentinel.

    This is what releases a supervised agent REPL whose agent drove its own
    script step via a nested `coga launch` — the step advance is that launch's
    `coga bump`, and before this signal the outer session hung until a manual
    Ctrl-C even though the step had advanced.
    """
    sentinel = tmp_path / "done-sentinel"
    monkeypatch.setenv("COGA_DONE_SENTINEL", str(sentinel))
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Check", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(app, ["launch", "check"])

    assert result.exit_code == 0, result.output
    assert sentinel.read_text() == "check\n"


def test_failed_script_launch_does_not_signal_done_sentinel(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing script never signals done — the session's work isn't done."""
    script = repo / "skills" / "ops" / "checker" / "check.sh"
    script.write_text("#!/bin/sh\nexit 3\n")
    script.chmod(0o755)
    sentinel = tmp_path / "done-sentinel"
    monkeypatch.setenv("COGA_DONE_SENTINEL", str(sentinel))
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Fail", workflow_name="ops",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(app, ["launch", "fail"])

    assert result.exit_code == 3
    assert not sentinel.exists()
