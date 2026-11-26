from __future__ import annotations

import os
import signal
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from textwrap import dedent

import pytest


import requests
from types import SimpleNamespace
from typer.testing import CliRunner

from conftest import hold_by_agent, hold_by_owner, seed_direct_body_workflow
from coga import recurring_runner as recurring_cmd
from coga.cli import app
from coga.blackboard import append_blocker
from coga.commands import block as block_module
from coga import launch as launch_module
from coga.commands import unblock as unblock_module
from coga.create import create_task
from coga import launch as launch_cmd
from coga.launch import (
    _MAX_PROMPT_ARG_BYTES,
    _argv_prompt,
    _configured_secret_values,
    build_agent_command,
    missing_launch_file_message,
    spawn_agent_session,
)
from coga.config import AgentType, Config, load_config
from coga.launch_script import run_script_phase
from coga.repl_supervisor import (
    ASSIST_AGENT_ENV,
    EXPECTED_AGENT_ENV,
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
    SENTINEL_ENV,
    _TIMEOUT_EXIT_CODE,
    AgentCliNotFound,
    ReplOutcome,
)
from coga.taskfile import read_blackboard, replace_blackboard, upsert_blackboard
from coga.tasks import BootstrapRef, TaskRef, list_tasks
from coga.ticket import Ticket
from coga.validate import TaskValidationError


FLOW_WEBHOOK = "https://slack.example.test/flow"
IMPORTANT_WEBHOOK = "https://slack.example.test/important"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


def _read_log(repo: Path) -> str:
    """The repo-global audit log (`coga/log.md`)."""
    return (repo / "log.md").read_text(encoding="utf-8")


def _capture_slack(sink: list[str], json_payload):
    sink.append(json_payload["text"])
    class R:
        status_code = 200
        text = "ok"
    return R()


def _prompt_arg(cmd: list[str]) -> str:
    for arg in cmd:
        if isinstance(arg, str) and arg.startswith("# Coga task"):
            return arg
        if isinstance(arg, str) and arg.startswith("developer_instructions=# Coga task"):
            return arg.removeprefix("developer_instructions=")
    raise AssertionError(f"No Coga prompt in argv: {cmd!r}")


# --- unit: command construction ------------------------------------------------


def _agent(
    name_flag: str = "",
    session_id_flag: str = "",
    discussion: str = "",
    launch_args: str = "",
) -> AgentType:
    return AgentType(
        name="x",
        cli="my-cli",
        file="X.md",
        mode="local",
        name_flag=name_flag,
        session_id_flag=session_id_flag,
        discussion=discussion,
        launch_args=launch_args,
    )


def test_build_command_interactive_passes_prompt_positionally() -> None:
    cmd = build_agent_command(_agent(), prompt="full prompt text")
    assert cmd == ["my-cli", "full prompt text"]


def test_build_command_injects_name_flag_when_set() -> None:
    cmd = build_agent_command(
        _agent(name_flag="-n"),
        prompt="full prompt text",
        name="Fix retry backoff",
    )
    assert cmd == ["my-cli", "-n", "Fix retry backoff", "full prompt text"]


def test_build_command_injects_session_id_after_name_flag() -> None:
    cmd = build_agent_command(
        _agent(name_flag="-n", session_id_flag="--session-id"),
        prompt="full prompt text",
        name="Fix retry backoff",
        session_id="session-123",
    )
    assert cmd == [
        "my-cli",
        "-n",
        "Fix retry backoff",
        "--session-id",
        "session-123",
        "full prompt text",
    ]


def test_build_command_inserts_launch_args_right_after_cli() -> None:
    agent = AgentType(
        name="codex",
        cli="codex",
        file="AGENTS.md",
        mode="local",
        name_flag="-n",
        session_id_flag="--session-id",
        launch_args="--no-daemon",
    )
    cmd = build_agent_command(
        agent,
        prompt="full prompt text",
        name="Fix retry backoff",
        session_id="session-123",
    )
    assert cmd == [
        "codex",
        "--no-daemon",
        "-n",
        "Fix retry backoff",
        "--session-id",
        "session-123",
        "full prompt text",
    ]


def test_build_command_discussion_inserts_launch_args_right_after_cli() -> None:
    agent = AgentType(
        name="codex",
        cli="codex",
        file="AGENTS.md",
        mode="local",
        launch_args="--no-daemon",
    )
    cmd = build_agent_command(agent, prompt="orient body", discussion=True)
    assert cmd == [
        "codex",
        "--no-daemon",
        "-c",
        "developer_instructions=orient body",
    ]


def test_build_command_launch_args_keep_quoted_token_boundaries() -> None:
    cmd = build_agent_command(
        _agent(launch_args="--profile 'two words' -x"),
        prompt="full prompt text",
    )
    assert cmd == ["my-cli", "--profile", "two words", "-x", "full prompt text"]


def test_build_command_unset_launch_args_leave_argv_unchanged() -> None:
    agent = AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local")
    assert agent.launch_args == ""
    assert build_agent_command(agent, prompt="p") == ["codex", "p"]
    assert build_agent_command(agent, prompt="p", discussion=True) == [
        "codex",
        "-c",
        "developer_instructions=p",
    ]


def test_build_command_skips_name_flag_when_agent_has_none() -> None:
    cmd = build_agent_command(
        _agent(),
        prompt="full prompt text",
        name="Fix retry backoff",
    )
    assert cmd == ["my-cli", "full prompt text"]


def test_build_command_skips_name_flag_when_name_is_empty() -> None:
    cmd = build_agent_command(
        _agent(name_flag="-n"),
        prompt="full prompt text",
        name="",
    )
    assert cmd == ["my-cli", "full prompt text"]


def test_build_command_discussion_skips_name_flag() -> None:
    """Discussion mode intentionally leaves the session unnamed so the
    human's first ask becomes the title; name_flag must not pre-set it."""
    agent = _agent(name_flag="-n", discussion="--append-system-prompt {prompt}")
    cmd = build_agent_command(
        agent,
        prompt="orient body",
        name="Orient an agent in this coga/ repo",
        discussion=True,
    )
    assert cmd == ["my-cli", "--append-system-prompt", "orient body"]


def test_ambient_secret_redaction_uses_declared_env_source() -> None:
    ticket = Ticket(
        frontmatter={"secrets": [{"API_KEY": "env:SOURCE_KEY"}]}, body=""
    )

    values = _configured_secret_values(
        ticket,
        {"API_KEY": "unrelated-alias", "SOURCE_KEY": "configured-secret"},
        secrets_are_scoped=False,
    )

    assert values == ("configured-secret",)


def test_ambient_secret_redaction_rejects_unresolved_op_reference() -> None:
    ticket = Ticket(
        frontmatter={"secrets": [{"API_KEY": "op://vault/item/key"}]}, body=""
    )

    values = _configured_secret_values(
        ticket,
        {"API_KEY": "untrusted-ambient-value"},
        secrets_are_scoped=False,
    )

    assert values is None


def test_scoped_secret_redaction_uses_injected_alias() -> None:
    ticket = Ticket(
        frontmatter={"secrets": [{"API_KEY": "op://vault/item/key"}]}, body=""
    )

    values = _configured_secret_values(
        ticket,
        {"API_KEY": "resolved-secret"},
        secrets_are_scoped=True,
    )

    assert values == ("resolved-secret",)


def test_build_command_discussion_uses_template_for_claude() -> None:
    agent = _agent(discussion="--append-system-prompt {prompt}")
    cmd = build_agent_command(
        agent,
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["my-cli", "--append-system-prompt", "orient body"]


def test_build_command_discussion_uses_template_for_codex() -> None:
    agent = _agent(discussion="-c developer_instructions={prompt}")
    cmd = build_agent_command(
        agent,
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["my-cli", "-c", "developer_instructions=orient body"]


def test_build_command_discussion_uses_default_template_for_claude_cli() -> None:
    agent = AgentType(
        name="standard-claude",
        cli="claude", file="CLAUDE.md",
        mode="local",
    )
    cmd = build_agent_command(
        agent,
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["claude", "--append-system-prompt", "orient body"]


def test_build_command_discussion_uses_default_template_for_codex_cli() -> None:
    agent = AgentType(
        name="standard-codex",
        cli="codex", file="AGENTS.md",
        mode="local",
    )
    cmd = build_agent_command(
        agent,
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["codex", "-c", "developer_instructions=orient body"]


def test_build_command_discussion_falls_back_when_template_unset() -> None:
    agent = _agent(discussion="")
    cmd = build_agent_command(
        agent,
        prompt="orient body",
        discussion=True,
    )
    assert cmd == ["my-cli", "orient body"]


def test_argv_prompt_passes_small_prompt_verbatim(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    assert _argv_prompt("full prompt text", prompt_file) == "full prompt text"


def test_argv_prompt_swaps_oversized_prompt_for_file_pointer(tmp_path: Path) -> None:
    """A prompt over MAX_ARG_STRLEN can't ride argv — execvp fails with E2BIG
    and the launch dies with a bare 127. Oversized prompts are delivered as a
    short pointer at the prompt file instead."""
    prompt_file = tmp_path / "prompt.md"
    huge = "y" * (_MAX_PROMPT_ARG_BYTES + 1)
    arg = _argv_prompt(huge, prompt_file)
    assert arg != huge
    assert str(prompt_file) in arg
    assert len(arg.encode()) < _MAX_PROMPT_ARG_BYTES


def test_argv_prompt_pointer_repeats_launch_marker(tmp_path: Path) -> None:
    """Usage capture matches the marker in the transcript's own message, so an
    oversized prompt's pointer must carry it too."""
    huge = "y" * (_MAX_PROMPT_ARG_BYTES + 1)
    arg = _argv_prompt(huge, tmp_path / "prompt.md", "coga-launch: abc")
    assert arg.endswith("\n\ncoga-launch: abc\n")


# --- unit: shared single-shot spawn -------------------------------------------

_LAUNCH_MARKER = "00000000-0000-4000-8000-000000000000"
_MARKER_SUFFIX = f"\n\ncoga-launch: {_LAUNCH_MARKER}\n"


def _pin_launch_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("coga.launch.uuid4", lambda: _LAUNCH_MARKER)


def _ticket() -> Ticket:
    return Ticket(
        frontmatter={
            "title": "Spawn test",
            "status": "active",
            "assignee": "claude",
        },
        body="",
    )


def test_spawn_agent_session_appends_kickoff_for_claude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = TaskRef(slug="draft-ticket", path=tmp_path / "draft-ticket")
    ref.path.mkdir()
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )
    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    _pin_launch_marker(monkeypatch)

    result = spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="claude",
            cli="claude", file="CLAUDE.md",
            mode="local",
            discussion="--append-system-prompt {prompt}",
        ),
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
        kickoff="Begin",
    )

    assert result.exit_code == 0
    assert calls == [
        [
            "claude",
            "--append-system-prompt",
            "# Coga task\nbody" + _MARKER_SUFFIX,
            "Begin",
        ]
    ]
    assert "launched" in (tmp_path / "log.md").read_text(encoding="utf-8")


def test_spawn_agent_session_appends_kickoff_for_codex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = TaskRef(slug="draft-ticket", path=tmp_path / "draft-ticket")
    ref.path.mkdir()
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )
    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    _pin_launch_marker(monkeypatch)

    spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="codex",
            cli="codex", file="AGENTS.md",
            mode="local",
            discussion="-c developer_instructions={prompt}",
        ),
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
        kickoff="Begin",
    )

    assert calls == [
        [
            "codex",
            "-c",
            "developer_instructions=# Coga task\nbody" + _MARKER_SUFFIX,
            "Begin",
        ]
    ]


def test_spawn_agent_session_uses_precomposed_prompt_without_rederiving_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = TaskRef(slug="checked-ticket", path=tmp_path / "checked-ticket")
    ref.path.mkdir()
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fail_compose(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a precomposed prompt must not be recomposed")

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.launch.compose_prompt", fail_compose)
    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    _pin_launch_marker(monkeypatch)

    spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="claude",
            cli="claude",
            file="CLAUDE.md",
            mode="local",
            discussion="--append-system-prompt {prompt}",
        ),
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
        composed_prompt="# Materialized\nchecked once",
    )

    assert calls == [
        [
            "claude",
            "--append-system-prompt",
            "# Materialized\nchecked once" + _MARKER_SUFFIX,
        ]
    ]


def test_spawn_agent_session_rederives_nested_recurring_task_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    company = tmp_path / "coga"
    dream = company / "tasks" / "recurring" / "dream"
    _write(dream / "ticket.md", "---\ntitle: Dream\nstatus: active\n---\n")
    ref = TaskRef(slug="dream", path=dream, directory="recurring")
    parent_ticket = (
        tmp_path
        / "src"
        / "coga"
        / "resources"
        / "templates"
        / "coga"
        / "bootstrap"
        / "resolve-conflicts"
        / "ticket.md"
    )
    inherited_env = {
        "COGA_TASK_SLUG": "bootstrap/resolve-conflicts",
        "COGA_TASK_DIR": str(parent_ticket.parent),
        "COGA_TASK_TICKET": str(parent_ticket),
        "COGA_TASK_BLACKBOARD": str(parent_ticket),
        EXPECTED_TASK_ENV: str(parent_ticket.parent),
        EXPECTED_STEP_ENV: "3 (open-pr)",
        "KEEP_ME": "yes",
    }
    captured_env: dict[str, str] = {}

    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )

    def fake_run_with_done_marker(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        captured_env.update(env)
        assert callable(kwargs["terminal_status"])
        return ReplOutcome(exit_code=0, kind="natural")

    monkeypatch.setattr(
        "coga.launch.run_with_done_marker", fake_run_with_done_marker
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session", lambda **kwargs: None
    )

    spawn_agent_session(
        SimpleNamespace(repo_root=company),
        ref,
        _ticket(),
        AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local"),
        env=inherited_env,
        actor="system",
        log_message="launched by recurring scan",
    )

    assert captured_env["COGA_TASK_SLUG"] == "recurring/dream"
    assert captured_env["COGA_TASK_DIR"] == str(dream.resolve())
    assert captured_env["COGA_TASK_TICKET"] == str(ref.ticket_path.resolve())
    assert captured_env["COGA_TASK_BLACKBOARD"] == str(ref.ticket_path.resolve())
    assert captured_env[EXPECTED_TASK_ENV] == str(parent_ticket.parent)
    assert captured_env[EXPECTED_STEP_ENV] == "3 (open-pr)"
    assert captured_env["KEEP_ME"] == "yes"


def test_spawn_agent_session_gives_bootstrap_target_no_blackboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stateless bootstrap ticket exports no `COGA_TASK_BLACKBOARD`.

    Its `ticket.md` is normally a packaged resource, so a Dream recipe run from
    the session used to append its `## Dream Skill: <name>` report into a file
    that ships in the wheel. An inherited value must not paper over the gap
    either — the whole task namespace is cleared before it is rewritten.
    """
    company = tmp_path / "coga"
    packaged = (
        tmp_path
        / "src"
        / "coga"
        / "resources"
        / "templates"
        / "coga"
        / "bootstrap"
        / "orient"
    )
    _write(packaged / "ticket.md", "---\ntitle: Orient\n---\n")
    ref = BootstrapRef(name="orient", path=packaged)
    inherited_env = {
        "COGA_TASK_SLUG": "some-task",
        "COGA_TASK_BLACKBOARD": str(company / "tasks" / "some-task" / "ticket.md"),
        "KEEP_ME": "yes",
    }
    captured_env: dict[str, str] = {}

    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )

    def fake_run_with_done_marker(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        captured_env.update(env)
        assert kwargs["terminal_status"] is None
        return ReplOutcome(exit_code=0, kind="natural")

    monkeypatch.setattr(
        "coga.launch.run_with_done_marker", fake_run_with_done_marker
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session", lambda **kwargs: None
    )

    spawn_agent_session(
        SimpleNamespace(repo_root=company),
        ref,
        _ticket(),
        AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local"),
        env=inherited_env,
        actor="system",
        log_message="launched bootstrap/orient",
    )

    assert captured_env["COGA_TASK_SLUG"] == "bootstrap/orient"
    assert captured_env["COGA_TASK_TICKET"] == str(ref.ticket_path.resolve())
    assert "COGA_TASK_BLACKBOARD" not in captured_env
    assert captured_env["KEEP_ME"] == "yes"


def test_spawn_agent_session_oversized_prompt_rides_argv_as_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The composed prompt can outgrow Linux's per-argument exec limit (a
    142 KB prompt did, killing the launch with a bare 127). Over the limit,
    the argv carries a pointer at the prompt file, never the prompt itself."""
    ref = TaskRef(slug="draft-ticket", path=tmp_path / "draft-ticket")
    ref.path.mkdir()
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    huge_prompt = "# Coga task\n" + "y" * (_MAX_PROMPT_ARG_BYTES + 1)
    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: huge_prompt,
    )
    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)

    result = spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local"),
        env={},
        actor="human:marc",
        log_message="launched",
    )

    assert result.exit_code == 0
    (cmd,) = calls
    assert all(len(arg.encode()) < _MAX_PROMPT_ARG_BYTES for arg in cmd)
    assert huge_prompt not in cmd
    pointer = cmd[-1]
    assert "coga-draft-ticket-" in pointer  # names the prompt file


def test_spawn_agent_session_without_kickoff_stays_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = BootstrapRef(name="orient", path=tmp_path / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )
    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    _pin_launch_marker(monkeypatch)

    spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="claude",
            cli="claude", file="CLAUDE.md",
            mode="local",
            discussion="--append-system-prompt {prompt}",
        ),
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
    )

    assert calls == [
        ["claude", "--append-system-prompt", "# Coga task\nbody" + _MARKER_SUFFIX]
    ]


def test_spawn_captures_stateless_discussion_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = BootstrapRef(name="orient", path=tmp_path / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)
    captured: list[dict] = []
    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )
    monkeypatch.setattr(
        "coga.launch.run_with_done_marker",
        lambda *a, **k: ReplOutcome(exit_code=0, kind="natural"),
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: captured.append(kwargs),
    )

    spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(
            name="codex",
            cli="codex",
            file="AGENTS.md",
            mode="local",
            discussion="-c developer_instructions={prompt}",
        ),
        env={},
        actor="human:marc",
        log_message="launched",
        discussion=True,
    )

    assert len(captured) == 1
    assert captured[0]["slug"] == "bootstrap/orient"
    assert captured[0]["title"] == "Spawn test"
    assert captured[0]["step"] is None
    assert captured[0]["outcome_status"] == "completed"
    launch_marker = captured[0]["launch_marker"]
    assert launch_marker
    # The marker ends the prompt, so the whole prompt (marker included) stays
    # excluded from human activity.
    assert captured[0]["excluded_user_texts"] == (
        f"# Coga task\nbody\n\ncoga-launch: {launch_marker}\n",
    )


def test_spawn_uses_bootstrap_identity_when_authoring_real_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = TaskRef(slug="draft-ticket", path=tmp_path / "tasks" / "draft-ticket")
    ref.path.mkdir(parents=True)
    captured: list[dict] = []
    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )
    def author_session(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["terminal_status"] is None
        return ReplOutcome(exit_code=0, kind="natural")

    monkeypatch.setattr("coga.launch.run_with_done_marker", author_session)
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: captured.append(kwargs),
    )

    spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local"),
        env={},
        actor="human:marc",
        log_message="ticket authoring launched",
        discussion=True,
        kickoff="Begin (editing existing ticket)",
        stateless_identity=("bootstrap/ticket", "Author a ticket"),
    )

    assert captured[0]["slug"] == "bootstrap/ticket"
    assert captured[0]["title"] == "Author a ticket"
    assert captured[0]["step"] is None
    assert "Begin (editing existing ticket)" in captured[0]["excluded_user_texts"]


@pytest.mark.parametrize(
    ("repl_outcome", "expected_status"),
    [
        (ReplOutcome(exit_code=7, kind="natural"), "failed"),
        (ReplOutcome(exit_code=_TIMEOUT_EXIT_CODE, kind="timeout"), "timed_out"),
        # A SIGINT death (Codex on a fast double Ctrl-C) is an interrupt; every
        # other crash and every non-zero natural exit stays a failure.
        (ReplOutcome(exit_code=128 + signal.SIGINT, kind="crash"), "interrupted"),
        (ReplOutcome(exit_code=128 + signal.SIGSEGV, kind="crash"), "failed"),
        (ReplOutcome(exit_code=137, kind="crash"), "failed"),  # recorded POSIX SIGKILL
        (ReplOutcome(exit_code=1, kind="crash"), "failed"),
        (ReplOutcome(exit_code=130, kind="natural"), "failed"),
        (ReplOutcome(exit_code=-signal.SIGINT, kind="natural"), "failed"),
        (ReplOutcome(exit_code=0, kind="done"), "completed"),
        (ReplOutcome(exit_code=0, kind="natural"), "completed"),
    ],
)
def test_spawn_captures_failed_and_timed_out_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    repl_outcome: ReplOutcome,
    expected_status: str,
) -> None:
    ref = BootstrapRef(name="orient", path=tmp_path / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)
    captured: list[dict] = []
    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )
    monkeypatch.setattr(
        "coga.launch.run_with_done_marker",
        lambda *a, **k: repl_outcome,
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: captured.append(kwargs),
    )

    result = spawn_agent_session(
        SimpleNamespace(repo_root=tmp_path),
        ref,
        _ticket(),
        AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local"),
        env={},
        actor="human:marc",
        log_message="launched",
    )

    assert result.exit_code == repl_outcome.exit_code
    assert result.termination_kind == repl_outcome.kind
    assert result.termination_reason == repl_outcome.reason
    assert captured[0]["outcome_status"] == expected_status
    assert captured[0]["exit_code"] == repl_outcome.exit_code
    assert captured[0]["exit_kind"] == repl_outcome.kind


def test_spawn_captures_interrupted_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = BootstrapRef(name="orient", path=tmp_path / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)
    captured: list[dict] = []
    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )

    def interrupt(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise KeyboardInterrupt

    monkeypatch.setattr("coga.launch.run_with_done_marker", interrupt)
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: captured.append(kwargs),
    )

    with pytest.raises(KeyboardInterrupt):
        spawn_agent_session(
            SimpleNamespace(repo_root=tmp_path),
            ref,
            _ticket(),
            AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local"),
            env={},
            actor="human:marc",
            log_message="launched",
        )

    assert captured[0]["outcome_status"] == "interrupted"
    assert captured[0]["exit_code"] is None
    assert captured[0]["exit_kind"] is None


def test_spawn_captures_supervisor_exception_as_failed_without_exit_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = BootstrapRef(name="orient", path=tmp_path / "bootstrap" / "orient")
    ref.path.mkdir(parents=True)
    captured: list[dict] = []
    monkeypatch.setattr(
        "coga.launch.compose_prompt",
        lambda cfg, ref, ticket, **kwargs: "# Coga task\nbody",
    )

    def explode(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("supervisor broke")

    monkeypatch.setattr("coga.launch.run_with_done_marker", explode)
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: captured.append(kwargs),
    )

    with pytest.raises(RuntimeError, match="supervisor broke"):
        spawn_agent_session(
            SimpleNamespace(repo_root=tmp_path),
            ref,
            _ticket(),
            AgentType(name="codex", cli="codex", file="AGENTS.md", mode="local"),
            env={},
            actor="human:marc",
            log_message="launched",
        )

    assert captured[0]["outcome_status"] == "failed"
    assert captured[0]["exit_code"] is None
    assert captured[0]["exit_kind"] is None


# --- integration: end-to-end via CliRunner with mocked subprocess --------------


@pytest.fixture
def active_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')

    seed_direct_body_workflow(company)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", FLOW_WEBHOOK)
    monkeypatch.setenv("COGA_IMPORTANT_WEBHOOK_URL", IMPORTANT_WEBHOOK)
    monkeypatch.chdir(company)
    cfg = load_config(company)
    create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    return company


def _allow_slack(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://slack.example.test")
    slack_msgs: list[str] = []
    monkeypatch.setattr(
        "requests.post",
        lambda url, json=None, timeout=None: _capture_slack(slack_msgs, json),
    )
    return slack_msgs


def _allow_interactive_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "coga.launch.interactive_stdio_has_tty",
        lambda: True,
    )




def _deny_interactive_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "coga.launch.interactive_stdio_has_tty",
        lambda: False,
    )


def _write_skill(repo: Path, ref: str, body: str) -> None:
    _write(
        repo / "skills" / ref / "SKILL.md",
        f"""
        ---
        name: {ref}
        description: test skill.
        ---

        {body}
        """,
    )


def _create_chain_task(active_task: Path) -> dict[str, object]:
    _write(
        active_task / "workflows" / "chain.md",
        """
        ---
        name: chain
        description: Agent chain.
        steps:
          - name: implement
            skills:
              - code/implement
            assignee: agent
          - name: self-review
            skills:
              - code/self-review
            assignee: agent
          - name: review
            assignee: owner
        ---

        ## review
        Review the change.
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    _write_skill(active_task, "code/self-review", "Review your own change.")

    cfg = load_config(active_task)
    return create_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="chain",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )


def test_launch_flow(active_task: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    slack_urls: list[str] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    def capture_slack(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        slack_urls.append(url)

        class Response:
            status_code = 200
            text = "ok"

        return Response()

    monkeypatch.setattr("requests.post", capture_slack)

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    # Agent called with `claude <composed-prompt-text>` — composed prompt
    # arrives as the first user message in the REPL.
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert len(calls[0]) == 2
    assert "Coga task" in calls[0][1]

    # Log entry written
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "in_progress"
    assert slack_urls == [FLOW_WEBHOOK]
    log = _read_log(active_task)
    assert "started (active → in_progress) via coga launch" in log
    assert "launched (operator=claude, agent=claude)" in log


def test_launch_routes_materialized_recurring_delegate_from_ticket(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A direct task launch dispatches a frozen period delegate instead of
    composing an agent wrapper on the recurring task itself.
    """
    cfg = load_config(active_task)
    created = create_task(
        cfg=cfg,
        title="Delegated period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        slug_override="recurring/delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
    )
    calls: list[tuple[str, str]] = []

    def fake_delegated(task_cfg, ref, **kwargs):  # type: ignore[no-untyped-def]
        calls.append((ref.id_slug, Ticket.read(ref.ticket_path).delegate or ""))
        return recurring_cmd.DelegatedRunResult(0, "done")

    monkeypatch.chdir(active_task)
    monkeypatch.setattr(recurring_cmd, "_run_delegated_task", fake_delegated)

    result = CliRunner().invoke(app, ["launch", created["slug"]])

    assert result.exit_code == 0, result.output
    assert calls == [
        ("recurring/delegate-check", "bootstrap/resolve-conflicts")
    ]


def test_direct_recurring_launch_uses_local_control_without_a_remote(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An actually remote-less Git checkout admits its local period state."""
    created = create_task(
        cfg=load_config(git_repo.coga_os),
        title="Delegated local period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        slug_override="recurring/local-delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
    )
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed local recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("remote", "remove", "origin")
    launched: list[str] = []

    def fake_delegated(task_cfg, ref, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref.id_slug)
        return recurring_cmd.DelegatedRunResult(0, "done")

    monkeypatch.setattr(recurring_cmd, "_run_delegated_task", fake_delegated)

    result = CliRunner().invoke(app, ["launch", created["slug"]])

    assert result.exit_code == 0, result.output
    assert launched == ["recurring/local-delegate-check"]


@pytest.mark.parametrize(
    "delegate_present", [True, False], ids=("delegated", "delegate-field-missing")
)
def test_direct_recurring_task_enforces_recurring_launch_gates_before_dispatch(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    delegate_present: bool,
) -> None:
    """Recurring authorization follows the ref, not optional dispatch state."""
    cfg = load_config(active_task)
    created = create_task(
        cfg=cfg,
        title="Gated delegated period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        slug_override="recurring/delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
    )
    ticket_path = Path(created["path"]) / "ticket.md"
    if not delegate_present:
        ticket = Ticket.read(ticket_path)
        ticket.frontmatter.pop("delegate")
        ticket.write(ticket_path)
    launches: list[str] = []

    monkeypatch.chdir(active_task)
    monkeypatch.setattr(
        recurring_cmd,
        "recurring_owner_refusal",
        lambda task_cfg: "recurring belongs to a different owner",
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_run_delegated_task",
        lambda task_cfg, ref, **kwargs: launches.append(ref.id_slug),
    )

    result = CliRunner().invoke(app, ["launch", created["slug"]])

    assert result.exit_code == 2
    assert launches == []
    assert Ticket.read(ticket_path).status == "active"


def test_direct_recurring_delegate_rejects_period_ticket_script(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A frozen period with both dispatch signals refuses instead of picking one."""
    cfg = load_config(active_task)
    created = create_task(
        cfg=cfg,
        title="Conflicting delegated period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        slug_override="recurring/delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
    )
    task_dir = Path(created["path"])
    ticket_path = task_dir / "ticket.md"
    (task_dir / "ticket.py").write_text("raise SystemExit(0)\n", encoding="utf-8", newline="\n")

    monkeypatch.chdir(active_task)
    monkeypatch.setattr(recurring_cmd, "_refuse_non_owner", lambda task_cfg: False)

    result = CliRunner().invoke(app, ["launch", created["slug"]])

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output
    assert Ticket.read(ticket_path).status == "active"


def test_launch_missing_onboarding_ticket_explains_filled_init(
    active_task: Path,
) -> None:
    """`coga build` → `launch coga-build` with no onboarding ticket explains
    that init skips it on a filled repo (or it was removed) and what to do
    instead, rather than the bare resolver miss."""
    result = CliRunner().invoke(app, ["launch", "coga-build"])

    assert result.exit_code == 2
    assert "No task matches 'coga-build'" in result.output
    assert "skipped at init or removed since" in result.output
    assert 'coga ticket "<title>"' in result.output


def test_launch_missing_ordinary_task_keeps_bare_miss(active_task: Path) -> None:
    """Only the onboarding slug gets the init explanation."""
    result = CliRunner().invoke(app, ["launch", "no-such-task"])

    assert result.exit_code == 2
    assert "No task matches 'no-such-task'" in result.output
    assert "onboarding" not in result.output


# --- push-auth gate -----------------------------------------------------------
#
# Coga drives the whole session through git/gh, so launch refuses to spawn an
# agent when push access to the configured remote is broken — fail loud at the
# door, not after a long run that can't ship.


def _ok_remote(_remote):
    return CheckResult("git-remote", True, "remote 'origin' -> url", "url")


def test_launch_captures_usage_with_session_id(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = (active_task / "coga.toml").read_text(encoding="utf-8")
    (active_task / "coga.toml").write_text(
        text.replace(
            'file = "CLAUDE.md"',
            'file = "CLAUDE.md"\nsession_id_flag = "--session-id"',
            1,
        ),
        encoding="utf-8", newline="\n",
    )
    calls: list[list[str]] = []
    captures: list[dict] = []
    _allow_interactive_tty(monkeypatch)

    def fake_supervisor(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return ReplOutcome(0, "natural")

    def fake_capture(**kwargs):  # type: ignore[no-untyped-def]
        captures.append(kwargs)

    monkeypatch.setattr(
        "coga.launch.run_with_done_marker", fake_supervisor
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session", fake_capture
    )
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "--session-id" in calls[0]
    session_id = calls[0][calls[0].index("--session-id") + 1]
    assert len(captures) == 1
    assert captures[0]["session_id"] == session_id
    assert captures[0]["slug"] == "fix-retry-logic"
    assert captures[0]["step"] == "execute"
    assert captures[0]["agent"] == "claude"
    assert captures[0]["cli"] == "claude"


def test_launch_fails_loud_on_unset_declared_secret(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    # Inline per-ticket secret pointing at an env var that is not exported.
    t.frontmatter["secrets"] = [{"stripe_key": "env:STRIPE_SECRET_KEY"}]
    t.write(ref.ticket_path)

    calls: list[list[str]] = []
    monkeypatch.setattr(
        "coga.launch.subprocess.run",
        lambda cmd, env=None, check=False, cwd=None: calls.append(cmd),
    )
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "stripe_key" in combined and "STRIPE_SECRET_KEY" in combined
    # Fail-loud: no agent process was ever spawned.
    assert calls == []
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "active"
    log = _read_log(active_task)
    assert "started (active" not in log


def test_launch_rejects_secret_alias_in_reserved_coga_namespace(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setenv("SECRET_BLACKBOARD_ALIAS", "must-not-be-overwritten")
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["secrets"] = [
        {"COGA_TASK_BLACKBOARD": "env:SECRET_BLACKBOARD_ALIAS"}
    ]
    ticket.write(ref.ticket_path)

    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "COGA_TASK_BLACKBOARD" in combined
    assert "reserved `COGA_` namespace" in combined
    assert Ticket.read(ref.ticket_path).status == "active"
    assert "started (active" not in _read_log(active_task)


def test_launch_injects_only_declared_secret(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live")
    monkeypatch.setenv("OTHER_SECRET", "nope")
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    # Only `stripe_key` is declared inline; `OTHER_SECRET` is set in the env but
    # the ticket never references it, so it must not leak to the child.
    t.frontmatter["secrets"] = [{"stripe_key": "env:STRIPE_SECRET_KEY"}]
    t.write(ref.ticket_path)

    captured: dict[str, str] = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured.update(env or {})
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    # Only the declared secret was injected, under its scoped NAME.
    assert captured.get("stripe_key") == "sk_live"
    assert "other" not in captured
    # The raw source env var the `env:` ref points at is scrubbed from the
    # child; an undeclared env var that was never referenced is left untouched.
    assert "STRIPE_SECRET_KEY" not in captured
    assert captured.get("OTHER_SECRET") == "nope"


def test_launch_fails_loud_on_op_read_error(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A declared `op://` secret that can't be resolved fails loud before any
    # agent is spawned, naming the key and reference (never a value).
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["secrets"] = [{"stripe_key": "op://vault/stripe/key"}]
    t.write(ref.ticket_path)

    # `coga.config` and `coga.launch` import the same `subprocess`
    # module, so patching `coga.config.subprocess.run` covers both the `op read`
    # resolution and the agent spawn. The op read is mocked non-zero → SecretError
    # before any spawn, so `calls` stays empty.
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["op", "read"]:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="[ERROR] not signed in"
            )
        calls.append(cmd)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "stripe_key" in combined and "op://vault/stripe/key" in combined
    # Fail-loud: no agent process was ever spawned, ticket stays active.
    assert calls == []
    assert Ticket.read(ref.ticket_path).status == "active"


def test_launch_injects_op_secret(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["secrets"] = [{"stripe_key": "op://vault/stripe/key"}]
    t.write(ref.ticket_path)

    # One dispatching mock for both modules' shared `subprocess`: `op read`
    # returns the secret; the agent spawn records its injected env.
    captured: dict[str, str] = {}

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["op", "read"]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="sk_op_secret\n", stderr=""
            )
        captured.update(kwargs.get("env") or {})
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert captured.get("stripe_key") == "sk_op_secret"


def test_launch_resolves_op_secret_but_scrubs_1password_auth_from_agent(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    op_auth = {
        "OP_SERVICE_ACCOUNT_TOKEN": "ops_token",
        "OP_CONNECT_TOKEN": "connect_token",
        "OP_CONNECT_HOST": "https://connect.example",
        "OP_SESSION_my": "personal_session",
    }
    for key, value in op_auth.items():
        monkeypatch.setenv(key, value)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["secrets"] = [{"stripe_key": "op://vault/stripe/key"}]
    t.write(ref.ticket_path)

    captured: dict[str, str] = {}

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["op", "read"]:
            # Resolution runs in the parent, which still holds the token.
            assert os.environ["OP_SERVICE_ACCOUNT_TOKEN"] == "ops_token"
            return subprocess.CompletedProcess(
                cmd, 0, stdout="sk_op_secret\n", stderr=""
            )
        captured.update(kwargs.get("env") or {})
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert captured.get("stripe_key") == "sk_op_secret"
    assert not [key for key in captured if key in op_auth]


def test_direct_launch_timeout_exits_non_zero(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A public `coga launch --idle-timeout` timeout must fail loud.

    Recurring gets an internal return-value path so it can record the watchdog
    timeout and continue its sweep, but the visible CLI should still propagate
    the supervisor's non-zero timeout code to scripts and shells.
    """
    _allow_interactive_tty(monkeypatch)
    # Native Windows refuses the explicit `--idle-timeout` flag (covered in
    # test_cli); the same propagation contract holds for `--max-session`.
    if os.name == "nt":
        option, reason = "--max-session", "max-session (wall-clock exceeded 1s)"
    else:
        option, reason = "--idle-timeout", "idle-timeout (no REPL activity for 1s)"

    def fake_supervisor(*args, **kwargs):  # type: ignore[no-untyped-def]
        return ReplOutcome(_TIMEOUT_EXIT_CODE, "timeout", reason)

    monkeypatch.setattr(
        "coga.launch.run_with_done_marker", fake_supervisor
    )
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic", option, "1"])

    assert result.exit_code == _TIMEOUT_EXIT_CODE, result.output
    assert "Agent timed out" in result.output
    assert reason in result.output


def test_launch_uses_local_agent_override(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Machine-local CLI selection layers over the shared agent table."""
    _write(
        active_task / "coga.local.toml",
        """
        user = "marc"

        [agents.claude]
        cli = "claude-nightly"
        """,
    )
    _allow_interactive_tty(monkeypatch)

    calls: list[list[str]] = []

    def fake_supervisor(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return ReplOutcome(0, "natural")

    monkeypatch.setattr(
        "coga.launch.run_with_done_marker", fake_supervisor
    )
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert calls and calls[0][0] == "claude-nightly"


def test_launch_bails_on_missing_context(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ticket referencing a context with no file must refuse to launch,
    rather than starting an agent with a silently-missing prompt layer."""
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket_md = ref.ticket_path
    ticket_md.write_text(
        ticket_md.read_text(encoding="utf-8").replace(
            "status: active", "status: active\ncontexts:\n- email/ghost"
        ),
        encoding="utf-8", newline="\n",
    )

    def fail_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError(f"agent must not be launched, got {cmd!r}")

    monkeypatch.setattr("coga.launch.subprocess.run", fail_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2, result.output
    assert "email/ghost" in result.output
    # Ticket was not flipped to in_progress — launch refused before starting.
    assert Ticket.read(ticket_md).status == "active"


def test_launch_refuses_invalid_inline_workflow_before_start(
    active_task: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _allow_interactive_tty(monkeypatch)
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter.update({
        "workflow": {"name": "audit-inline", "steps": [
            {"name": "implement", "assignee": "agent"},
        ]},
        "step": "1 (implement)",
    })
    ticket.write(ref.ticket_path)
    path = active_task / "workflows" / "audit-inline.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("---\nname: audit-inline\nsteps: [\n---\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(launch_module.shutil, "which", lambda name, **kwargs: f"/usr/bin/{name}")
    monkeypatch.setattr(launch_module, "spawn_agent_session", lambda **kw: pytest.fail("agent started"))

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 2, result.output
    assert "invalid YAML" in result.output
    assert str(path) in result.output
    assert Ticket.read(ref.ticket_path).status == "active"


def test_launch_handles_agent_self_deleting_task(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workflow-less agent (e.g. a Dream run retiring itself) may delete its
    own task directory as a final action. Launch must treat the missing
    ticket.md as a clean terminal state, not crash reading the ticket back."""
    _allow_interactive_tty(monkeypatch)
    # File-form task: the whole ticket lives in `tasks/<slug>.md`.
    ticket_md = active_task / "tasks" / "fix-retry-logic.md"
    assert ticket_md.exists()

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        # Simulate the agent deleting its own task before exit.
        ticket_md.unlink()
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert not ticket_md.exists()


def test_launch_marks_llm_session_supervised(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Agent launches chain across agent-owned steps, so the child
    inherits `COGA_SUPERVISED=1`. `coga bump` keys its supervised-launch
    hint off that env var."""
    envs: list[dict] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        envs.append(env or {})
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    assert envs
    assert envs[0].get("COGA_SUPERVISED") == "1"
    assert envs[0].get(EXPECTED_STEP_ENV) == "1 (execute)"
    assert Path(envs[0].get(EXPECTED_TASK_ENV, "")).as_posix().endswith(
        "/tasks/fix-retry-logic.md"
    )


def test_launch_in_progress_resumes_without_status_transition(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    log = _read_log(active_task)
    assert "started (active → in_progress) via coga launch" not in log


def test_launch_llm_without_tty_fails_before_lock(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False
    _deny_interactive_tty(monkeypatch)

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("interactive launch should fail before spawning agent")

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code == 2
    assert "Cannot launch 'fix-retry-logic': an agent launch requires a TTY" in (
        result.output + (result.stderr or "")
    )
    assert not called

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]


def test_launch_llm_chains_consecutive_agent_steps(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent launches chain while the next step is still the agent's.

    After `coga bump` advances from step 1 (agent) to step 2 (also agent),
    the launch loop re-composes the prompt and spawns a fresh REPL. The
    chain stops at the first human-assigned step (step 3 here).
    """
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        # Each spawned "agent" bumps once. After the 1→2 bump the agent is
        # still the assignee → launch should respawn. After the 2→3 bump
        # the next step is human-assigned → launch should stop.
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Two REPLs: step 1, then a fresh one for step 2. Step 3 is the human's,
    # so the loop stops without spawning a third.
    assert len(calls) == 2

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "3 (review)"


@pytest.mark.parametrize("activate_draft", [False, True])
def test_launch_agent_override_follows_consecutive_agent_role_steps(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    activate_draft: bool,
) -> None:
    """An explicit agent keeps a same-role chain on the selected CLI.

    This is the shape used by coga-build: both onboarding steps explicitly
    declare the workflow role ``agent``. The override remains in-memory and
    never rewrites the ticket's own main-agent choice.
    """
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    if activate_draft:
        # Park it as a draft carrying a bare workflow ref, so the launch has to
        # freeze the snapshot and seed step 1 before it can route at all.
        ticket_path = Path(ref["path"])
        ticket = Ticket.read(ticket_path)
        ticket.frontmatter["status"] = "draft"
        ticket.frontmatter["workflow"] = "chain"
        ticket.frontmatter.pop("step")
        ticket.write(ticket_path)
    # The ticket's main agent stays `claude` and stays configured; codex is
    # added alongside it so the explicit selection is a real, valid override.
    _write(
        active_task / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"
        """,
    )
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", slug, "--agent", "codex"])

    assert result.exit_code == 0, result.output
    assert [call[0] for call in calls] == ["codex", "codex"]
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "3 (review)"
    assert ticket.current_step()["assignee"] == "owner"
    # Ephemeral: the ticket's own main-agent choice is untouched.
    assert ticket.agent == "claude"
    assert "assignee" not in ticket.frontmatter


def test_launch_override_refuses_when_the_main_agent_is_unconfigured(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An override cannot repair an invalid routing input.

    This deliberately removes an old recovery path: a ticket that selected
    `claude` in a repo that has since become codex-only used to be launchable
    with `--agent codex`. The main-agent choice is a real routing input now, so
    the launch refuses *before dispatch* and the operator either restores the
    agent's `[agents.*]` table or changes the ticket's choice through authoring.
    """
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _write(
        active_task / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"
        """,
    )
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    def fail_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError(f"no agent may be spawned, got {cmd!r}")

    monkeypatch.setattr("coga.launch.subprocess.run", fail_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", slug, "--agent", "codex"])

    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "is not a configured agent type" in combined
    assert "cannot repair an invalid routing input" in combined
    # Refused before dispatch: no lifecycle mutation.
    assert Ticket.read(Path(ref["path"])).status == "active"


def test_launch_chains_when_ticket_has_ticket_level_skills(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ticket-level `skills:` list must not stop the supervised chain.

    Regression: the loop used to break on `is_bootstrap or ticket.skills`,
    a rename artifact of the old singular skill-shim field. That silently
    stopped any normal workflow ticket carrying ticket-level skills from
    chaining to its next agent step. Only bootstrap tickets should stop here.
    """
    _write(
        active_task / "workflows" / "chain.md",
        """
        ---
        name: chain
        description: Agent chain.
        steps:
          - name: implement
            skills:
              - code/implement
            assignee: agent
          - name: self-review
            skills:
              - code/self-review
            assignee: agent
          - name: review
            assignee: owner
        ---

        ## review
        Review the change.
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    _write_skill(active_task, "code/self-review", "Review your own change.")

    cfg = load_config(active_task)
    ref = create_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="chain",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        skills=["code/implement"],
        # ticket-level skills — must not block chaining,
    )
    slug = str(ref["slug"])

    from coga.ticket import Ticket
    assert Ticket.read(Path(ref["path"])).skills == ["code/implement"]

    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Step 1 (agent) chains to step 2 (agent); stops at step 3 (human).
    assert len(calls) == 2
    assert Ticket.read(Path(ref["path"])).step == "3 (review)"


def test_launch_harness_stops_when_next_skilled_step_changes_assignee(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        active_task / "workflows" / "handoff.md",
        """
        ---
        name: handoff
        description: Skilled handoff.
        steps:
          - name: implement
            skills:
              - code/implement
            assignee: agent
          - name: human-check
            skills:
              - code/human-check
            assignee: owner
        ---
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    _write_skill(active_task, "code/human-check", "Human checks the change.")
    cfg = load_config(active_task)
    ref = create_task(
        cfg=cfg,
        title="Handoff work",
        workflow_name="handoff",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Interactive does not chain — one agent run, then back to the caller.
    # The assignee transition surfaces in `coga status`, not in launch
    # output, because the human is the one driving step transitions.
    assert len(calls) == 1

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "2 (human-check)"
    assert ticket.current_step()["assignee"] == "owner"


def test_launch_harness_stops_on_agent_block(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(
            app,
            ["block", "--task", slug, "--reason", "test block"],
        )
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "task status is 'blocked'" in result.output
    assert "test block" in read_blackboard(Path(ref["path"]))


# --- launching a blocked ticket -------------------------------------------------
#
# An explicit interactive launch of a blocked ticket resumes it inline
# (blocked status and step preserved) and the composed prompt's
# first job becomes resolving the open asks with the human. Batch surfaces
# (no TTY) keep the hard refusal.


def _block_task(slug: str) -> None:
    result = CliRunner().invoke(
        app, ["block", "--task", slug, "--reason", "which retry ceiling?"]
    )
    assert result.exit_code == 0, result.output


def test_launch_blocked_interactive_resumes_with_preamble(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _block_task(slug)

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        ticket = Ticket.read(Path(ref["path"]))
        assert ticket.status == "blocked"
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "blocked"
    assert ticket.step == "1 (implement)"
    assert "- [ ]" in read_blackboard(Path(ref["path"]))

    # The composed prompt leads with the resolve-or-re-block preamble,
    # carrying the ask verbatim and both recording commands.
    assert len(calls) == 1
    prompt = calls[0][1]
    assert "Resolve the open blocker first" in prompt
    assert "which retry ceiling?" in prompt
    assert f"coga unblock {slug} --answer" in prompt
    assert f"coga block --task {slug} --reason" in prompt


def test_launch_blocked_timeout_reblocks_unresolved_ask(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _block_task(slug)

    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")
    monkeypatch.setattr(
        "coga.launch.run_with_done_marker",
        lambda *a, **k: ReplOutcome(_TIMEOUT_EXIT_CODE, "timeout"),
    )

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == _TIMEOUT_EXIT_CODE

    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "blocked"
    assert ticket.step == "1 (implement)"
    assert "- [ ]" in read_blackboard(Path(ref["path"]))


# --- unsignalled-advance advisory (coga-dev/internals/agent-spawn) -----------------

_UNSIGNALLED = "but the supervisor saw no done signal"


def _session_edits_ticket(
    monkeypatch: pytest.MonkeyPatch,
    ref: dict[str, object],
    outcome: ReplOutcome,
    edit=None,  # type: ignore[no-untyped-def]
) -> None:
    """Run the real spawn path with a fake supervisor that edits the ticket.

    The real `spawn_agent_session` still calls its `before_spawn` boundary, so
    the pre-session snapshot is frozen exactly where production freezes it.
    """
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    def fake_supervisor(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        if edit is not None:
            edit(Path(ref["path"]))
        return outcome

    monkeypatch.setattr("coga.launch.run_with_done_marker", fake_supervisor)


def _advance_to_owner_review(path: Path) -> None:
    ticket = Ticket.read(path)
    ticket.frontmatter["step"] = "3 (review)"
    ticket.write(path)


@pytest.mark.parametrize(
    ("outcome", "exit_code", "warns"),
    [
        (ReplOutcome(0, "natural"), 0, True),
        (ReplOutcome(0, "done", None, True), 0, False),
        (ReplOutcome(_TIMEOUT_EXIT_CODE, "timeout", "idle"), _TIMEOUT_EXIT_CODE, True),
        (ReplOutcome(3, "natural"), 3, True),
        # Done signal followed by a real crash: the crash result stands, but
        # the observed signal suppresses the advisory.
        (ReplOutcome(128 + 11, "crash", None, True), 128 + 11, False),
    ],
)
def test_launch_warns_when_ticket_advances_without_done_signal(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: ReplOutcome,
    exit_code: int,
    warns: bool,
) -> None:
    ref = _create_chain_task(active_task)
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _session_edits_ticket(monkeypatch, ref, outcome, _advance_to_owner_review)

    result = CliRunner().invoke(app, ["launch", str(ref["slug"])])

    assert result.exit_code == exit_code, result.output
    assert (_UNSIGNALLED in result.output) is warns
    if warns:
        assert f"Warning: {ref['slug']} changed from in_progress @ 1 (implement)" in (
            result.output
        )
        assert "to in_progress @ 3 (review)" in result.output
        assert 'launch_args = "--no-daemon" under [agents.codex]' in result.output
    assert Ticket.read(Path(ref["path"])).step == "3 (review)"


def test_launch_does_not_warn_when_ticket_is_unchanged(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _create_chain_task(active_task)
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _session_edits_ticket(monkeypatch, ref, ReplOutcome(0, "natural"))

    result = CliRunner().invoke(app, ["launch", str(ref["slug"])])

    assert result.exit_code == 0, result.output
    assert _UNSIGNALLED not in result.output


@pytest.mark.parametrize(
    ("edit", "exit_code"),
    [
        (lambda path: path.unlink(), 0),
        (lambda path: path.write_text("not a ticket\n", encoding="utf-8", newline="\n"), 3),
    ],
    ids=["removed", "unreadable"],
)
def test_launch_skips_the_advisory_when_post_session_state_is_unavailable(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    edit,  # type: ignore[no-untyped-def]
    exit_code: int,
) -> None:
    ref = _create_chain_task(active_task)
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _session_edits_ticket(monkeypatch, ref, ReplOutcome(exit_code, "natural"), edit)

    result = CliRunner().invoke(app, ["launch", str(ref["slug"])])

    assert result.exit_code == exit_code, result.output
    assert _UNSIGNALLED not in result.output


def test_launch_supervisor_reblock_is_not_reported_as_an_agent_change(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _block_task(slug)
    _session_edits_ticket(monkeypatch, ref, ReplOutcome(0, "natural"))

    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code == 0, result.output
    assert Ticket.read(Path(ref["path"])).status == "blocked"
    assert _UNSIGNALLED not in result.output


def test_launch_blocked_without_tty_still_refuses(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _allow_slack(monkeypatch)
    _block_task(slug)
    _deny_interactive_tty(monkeypatch)

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError("a blocked ticket must not spawn without a TTY")

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 2
    assert "it is blocked" in result.output

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "blocked"
    assert ticket.step == "1 (implement)"


def test_launch_blocked_without_open_ask_refuses(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _allow_interactive_tty(monkeypatch)

    ticket = Ticket.read(Path(ref["path"]))
    ticket.frontmatter["status"] = "blocked"
    ticket.write(Path(ref["path"]))

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError("a blocked ticket with no ask must not spawn")

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 2
    assert "no open blocker asks" in result.output

    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "blocked"
    assert ticket.step == "1 (implement)"


def test_launch_blocked_preflight_failure_leaves_ticket_blocked(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _block_task(slug)

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError("a failed preflight must not spawn")

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: None)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 2
    assert "Agent CLI" in result.output

    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "blocked"
    assert ticket.step == "1 (implement)"
    assert "- [ ]" in read_blackboard(Path(ref["path"]))


def test_launch_blocked_session_records_resolution_in_flight(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one-session loop: the launched agent resolves the asks with
    `coga unblock --answer` mid-step, without a status flip or a second
    launch."""
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    _block_task(slug)

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        with monkeypatch.context() as child:
            child.setenv("COGA_TASK_TICKET", env["COGA_TASK_TICKET"])
            result = CliRunner().invoke(
                app, ["unblock", slug, "--answer", "cap at 5 minutes"]
            )
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "in_progress"
    assert ticket.step == "1 (implement)"
    blackboard = read_blackboard(Path(ref["path"]))
    assert "- [x]" in blackboard
    assert "cap at 5 minutes" in blackboard


def _launch_single_spawn(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Mock the agent spawn so launch runs one REPL and stops (no bump → no
    progress → supervisor halts). Returns the list of spawned argvs."""
    calls: list[list[str]] = []
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )
    return calls


@pytest.mark.parametrize("prior", ["draft", "paused"])
def test_launch_auto_activates_draft_and_paused(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, prior: str
) -> None:
    """`coga launch` is itself the readiness signal: a draft/paused ticket
    with a workflow is activated inline, then flipped to in_progress."""
    from coga.ticket import Ticket

    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = prior
    t.write(ticket_md)

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1  # agent spawned

    after = Ticket.read(ticket_md)
    assert after.status == "in_progress"
    assert after.step == "1 (implement)"
    log = _read_log(active_task)
    assert f"activated ({prior} → active) — auto on launch" in log


@pytest.mark.parametrize("prior_agent", ["claude", "codex"])
def test_launch_uses_step_one_role_after_freezing_draft(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, prior_agent: str
) -> None:
    """Launch routes from the *prepared activation*, not the parked draft.

    Activation freezes the bare workflow ref and seeds step 1, so step 1's role
    is what picks the agent — whichever main agent the draft happens to name.
    """
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_path = Path(ref["path"])
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "draft"
    ticket.frontmatter["workflow"] = "chain"
    ticket.frontmatter.pop("step")
    ticket.frontmatter["agent"] = prior_agent
    ticket.write(ticket_path)

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    # Step 1's `agent` role resolves to whichever main agent the draft names.
    assert calls[0][0] == prior_agent
    after = Ticket.read(ticket_path)
    assert after.status == "in_progress"
    assert after.step == "1 (implement)"
    assert after.current_step()["assignee"] == "agent"
    assert (
        f"launched (operator={prior_agent}, agent={prior_agent})"
        in _read_log(active_task)
    )




def test_launch_does_not_enter_assist_handling_for_a_human_to_agent_draft(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--agent` on a human-assigned draft whose step 1 resolves to an agent.

    The recorded-assist classification read the *stale* draft assignee, so this
    human->agent transition entered strict human-assist handling and performed
    the recorded-PR lookup for a step that is agent-owned once frozen.
    `coga/workflows` requires the check to use the prepared activation's
    resolved assignee.
    """
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_path = Path(ref["path"])
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "draft"
    ticket.frontmatter["workflow"] = "chain"
    ticket.frontmatter.pop("step")
    # A parked draft has no position at all, so nothing about it looks
    # owner-held until activation freezes the snapshot; step 1 then declares
    # `assignee: agent`, which routes to the ticket's `agent:` (claude).
    ticket.write(ticket_path)

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug, "--agent", "claude"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert Ticket.read(ticket_path).current_step()["assignee"] == "agent"


def test_launch_preflights_resolved_step_one_agent_before_activation(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_path = Path(ref["path"])
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "draft"
    ticket.frontmatter["workflow"] = "chain"
    ticket.frontmatter.pop("step")
    ticket.write(ticket_path)
    before = ticket_path.read_bytes()
    calls = _launch_single_spawn(monkeypatch)
    monkeypatch.setattr(
        "coga.launch.shutil.which",
        lambda name: None if name == "claude" else f"/usr/bin/{name}",
    )

    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code == 2, result.output
    assert "Agent CLI 'claude' not found" in result.output
    assert "Set `cli` in [agents.claude] in coga.toml" in result.output
    assert calls == []
    assert ticket_path.read_bytes() == before
    assert "activated (draft" not in _read_log(active_task)


@pytest.mark.parametrize("prior", ["draft", "paused"])
def test_launch_refusal_leaves_draft_unactivated(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, prior: str
) -> None:
    """A preflight refusal must not leave the activation behind.

    `coga launch` used to write the draft/paused → `active` transition before
    the preflights that can refuse the launch, so an unresolvable secret left
    the ticket on disk claiming a session started — frozen workflow, seeded
    step, and an `activated … — auto on launch` audit line — for an agent that
    never ran. The activation is staged in memory and only written once every
    refusal is behind it.
    """
    from coga.ticket import Ticket

    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = prior
    t.frontmatter["secrets"] = [{"stripe_key": "op://vault/stripe/key"}]
    t.write(ticket_md)
    before = ticket_md.read_text(encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["op", "read"]:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="[ERROR] not signed in"
            )
        calls.append(cmd)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "stripe_key" in combined and "op://vault/stripe/key" in combined
    assert calls == []  # no agent spawned
    # The whole point: nothing durable was written for a session that never ran.
    assert ticket_md.read_text(encoding="utf-8") == before
    assert "activated (" not in _read_log(active_task)


def test_launch_refuses_unsynthesized_draft_blackboard(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = "draft"
    t.write(ticket_md)
    before_blackboard = "\n## Ticket authoring notes\n\nNeeds body synthesis.\n"
    replace_blackboard(ticket_md, before_blackboard)
    before = ticket_md.read_text(encoding="utf-8")

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "pre-launch notes" in combined
    assert (
        "Merge the important parts into `## Description` / `## Context`"
        in combined
    )
    assert calls == []
    assert ticket_md.read_text(encoding="utf-8") == before
    assert "activated (draft" not in _read_log(active_task)


def test_launch_refuses_done_ticket(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launching a `done` ticket must not restart its frozen workflow:
    re-activating would re-seed `step: 1` without re-resolving `assignee` and
    wedge the ticket. Launch refuses loud and leaves the ticket untouched."""
    from coga.ticket import Ticket

    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
    t = Ticket.read(ticket_md)
    t.frontmatter["status"] = "done"
    t.frontmatter.pop("step", None)  # mark done clears the step
    t.write(ticket_md)
    before = ticket_md.read_text(encoding="utf-8")

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "is done" in combined
    assert "terminal status" in combined
    assert calls == []  # no agent spawned

    after = Ticket.read(ticket_md)
    assert after.status == "done"
    assert after.step is None
    assert ticket_md.read_text(encoding="utf-8") == before  # ticket file untouched


def test_launch_refuses_canceled_ticket(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _create_chain_task(active_task)
    slug = str(ref["slug"])
    ticket_md = Path(ref["path"])
    ticket = Ticket.read(ticket_md)
    ticket.frontmatter["status"] = "canceled"
    ticket.frontmatter.pop("step", None)
    ticket.write(ticket_md)
    before = ticket_md.read_text(encoding="utf-8")

    calls = _launch_single_spawn(monkeypatch)
    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "is canceled" in combined
    assert "terminal status" in combined
    assert calls == []
    assert ticket_md.read_text(encoding="utf-8") == before


def _seed_released_launch_admission(
    git_repo, control_generation: str,
) -> tuple[Config, TaskRef, bytes]:
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg,
        title="Reconcile released admission",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = next(item for item in list_tasks(cfg) if item.id_slug == created["slug"])
    coga_git.sync_task_state(
        cfg, ref.path, message="Seed released-admission reconciliation"
    )
    control = Ticket.read(ref.ticket_path)
    control.frontmatter["status"] = "in_progress"
    control.frontmatter["launch_generation"] = control_generation
    control.write(ref.ticket_path)
    ticket_rel = ref.ticket_path.relative_to(git_repo.root).as_posix()
    git_repo.git("add", ticket_rel)
    git_repo.git("commit", "-m", "Publish launch admission state")
    git_repo.git("push", "origin", "main")

    released = Ticket.read(ref.ticket_path)
    released.frontmatter["launch_generation"] = "released:held-generation"
    released_bytes = released.render().encode()
    released.write(ref.ticket_path)
    return cfg, ref, released_bytes


def test_launch_auto_activate_bails_without_workflow(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workflow-less ticket still can't be activated — launch fails loud
    (it can never be advanced by `coga bump`) and never spawns an agent."""
    from coga.ticket import Ticket

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    # Strip the workflow and drop to draft so launch's auto-activate hits the
    # workflow-less path (a workflow-less non-draft can't be created now).
    t = Ticket.read(ref.ticket_path)
    t.frontmatter["status"] = "draft"
    t.frontmatter["workflow"] = None
    t.write(ref.ticket_path)

    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 2, result.output
    combined = result.output + (result.stderr or "")
    assert "no workflow" in combined or "carries no frozen workflow" in combined
    assert not calls  # agent never spawned

    # Ticket stayed draft — the failed activation did not mutate status.
    assert Ticket.read(ref.ticket_path).status == "draft"


@pytest.mark.parametrize("status", ["draft", "active"])
def test_launch_reports_unknown_workflow_before_start(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, status: str,
) -> None:
    ref = list_tasks(load_config(active_task))[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter.update(status=status, workflow="code")
    if status == "draft":
        ticket.frontmatter.pop("step")
    ticket.write(ref.ticket_path)
    original = ref.ticket_path.read_bytes()
    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 2, result.output
    assert len(result.output.splitlines()) == 1
    assert "'code' is a workflow group" in result.output
    assert "code/with-review" in result.output
    assert calls == []
    assert ref.ticket_path.read_bytes() == original


@pytest.mark.parametrize("slug", ["fix-retry-logic", "coga-build"])
def test_launch_agent_not_in_path(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, slug: str
) -> None:
    """Every launch, including onboarding, gives only the `coga.toml` remedy."""
    if slug == "coga-build":
        create_task(
            cfg=load_config(active_task),
            title="coga-build",
            workflow_name="direct/body",
            contexts=[],
            owner="marc",
            agent="claude",
            status="active",
        )
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: None)
    runner = CliRunner()
    result = runner.invoke(app, ["launch", slug])
    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "Agent CLI 'claude' not found" in combined
    diagnostic = next(line for line in combined.splitlines() if "Agent CLI 'claude' not found" in line)
    assert "Set `cli` in [agents.claude] in coga.toml" in diagnostic
    assert "http" not in diagnostic
    assert "install" not in diagnostic.lower()


def test_launch_warns_for_large_blackboard(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    upsert_blackboard(ref.ticket_path, "\n\n" + "x" * (33 * 1024) + "\n")
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        "coga.launch.subprocess.run",
        lambda cmd, env=None, check=False, cwd=None: _Result(),
    )
    monkeypatch.setattr(
        "coga.launch.shutil.which",
        lambda name, **kwargs: f"/usr/bin/{name}",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output
    assert "blackboard region is" in (result.output + (result.stderr or ""))


def test_launch_prompt_report_warns_for_uncomposed_sections(
    active_task: Path,
) -> None:
    """The report sizes only composed layers, so it names the `##` sections it
    left out rather than letting them vanish silently."""
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    text = ref.ticket_path.read_text(encoding="utf-8")
    ref.ticket_path.write_text(text.replace(
        "\n<!-- coga:blackboard -->",
        "\n## Acceptance Criteria\n\n- Done.\n\n<!-- coga:blackboard -->",
        1,
    ), encoding="utf-8", newline="\n")

    result = CliRunner().invoke(app, ["launch", ref.id_slug, "--prompt-report"])

    assert result.exit_code == 0, result.output
    combined = result.output + (result.stderr or "")
    assert "sections no launch prompt carries: `## Acceptance Criteria`" in combined


@pytest.mark.parametrize("prompt_report", [False, True])
@pytest.mark.parametrize("sections", ["", "## Description\nIntent.\n## Context\nContext.\n"])
@pytest.mark.parametrize("preamble", ["Lost preamble prose.\n\n", " \t\n\n"])
def test_launch_warns_for_uncomposed_preamble(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, prompt_report: bool, sections: str,
    preamble: str,
) -> None:
    from coga.taskfile import join_task_body, uncomposed_sections_warning

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.body = join_task_body(preamble + sections, "")
    ticket.write(ref.ticket_path)
    calls = _launch_single_spawn(monkeypatch)
    argv = ["launch", ref.id_slug] + (["--prompt-report"] if prompt_report else [])

    result = CliRunner().invoke(app, argv)

    assert result.exit_code == 0, result.output
    combined = result.output + (result.stderr or "")
    warning = uncomposed_sections_warning(ref.ticket_path)
    if preamble.strip():
        assert warning is not None
        assert warning in combined
        assert "preamble before the first `##` heading" in combined
    else:
        assert warning is None
        assert "preamble before the first `##` heading" not in combined
    if not prompt_report:
        prompt = _prompt_arg(calls[0])
        assert "Lost preamble prose." not in prompt
        if sections:
            assert "Intent." in prompt
            assert "Context." in prompt


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_launch_ignores_blocker_examples(
    active_task: Path, monkeypatch: pytest.MonkeyPatch, fence: str,
) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    replace_blackboard(ref.ticket_path,
        f"\n{fence}markdown\n"
        "- [ ] [2026-09-18 12:00] [human:marc] id=example Fenced ask\n"
        f"{fence}\n## Superseded designs\n"
        "- [ ] [2026-09-18 12:00] [human:marc] id=old Archived ask\n"
    )
    calls = _launch_single_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "Resolve the open blocker first" not in _prompt_arg(calls[0])


def test_launch_prompt_report_prints_layers_without_launching(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        active_task / "contexts" / "email" / "payment-flow" / "SKILL.md",
        """
        ---
        name: email/payment-flow
        description: Payment context.
        ---

        Stripe retries on 429.
        """,
    )
    _write(
        active_task / "workflows" / "code" / "measure.md",
        """
        ---
        name: code/measure
        description: Measure prompt scope.
        steps:
          - name: implement
            skills:
              - code/implement
            assignee: agent
        ---
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    cfg = load_config(active_task)
    ref = create_task(
        cfg=cfg,
        title="Measure prompt scope",
        workflow_name="code/measure",
        contexts=["email/payment-flow"],
        owner="marc",
        agent="claude",
        status="draft",
    )

    def fail_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError("prompt report must not spawn an agent")

    monkeypatch.setattr("coga.launch.subprocess.run", fail_run)
    monkeypatch.setattr("coga.launch.interactive_stdio_has_tty", lambda: False)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: None)

    result = CliRunner().invoke(app, ["launch", str(ref["slug"]), "--prompt-report"])
    assert result.exit_code == 0, result.output
    assert "Prompt report for measure-prompt-scope" in result.output
    assert "ticket_context" in result.output
    assert "email/payment-flow" in result.output
    assert "workflow_skill" in result.output
    assert "code/implement" in result.output
    assert "Total composed prompt" in result.output

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.status == "draft"
    assert "launched in agent mode" not in _read_log(active_task)


def test_launch_prompt_report_names_repo_resource_overrides(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fixed layer read from `<coga root>/resources/` reports its override
    file; packaged layers stay unlisted."""
    _write(active_task / "resources" / "prompt.md", "Repo base prompt.\n")
    _write(
        active_task / "workflows" / "code" / "measure.md",
        """
        ---
        name: code/measure
        description: Measure prompt scope.
        steps:
          - name: implement
            skills:
              - code/implement
            assignee: agent
        ---
        """,
    )
    _write_skill(active_task, "code/implement", "Implement the change.")
    cfg = load_config(active_task)
    ref = create_task(
        cfg=cfg,
        title="Measure overrides",
        workflow_name="code/measure",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
    )

    def fail_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        raise AssertionError("prompt report must not spawn an agent")

    monkeypatch.setattr("coga.launch.subprocess.run", fail_run)
    monkeypatch.setattr("coga.launch.interactive_stdio_has_tty", lambda: False)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: None)

    result = CliRunner().invoke(app, ["launch", str(ref["slug"]), "--prompt-report"])
    assert result.exit_code == 0, result.output
    assert "Repo resource overrides:" in result.output
    assert (
        f"base_prompt: prompt.md <- {active_task / 'resources' / 'prompt.md'}"
        in result.output
    )
    assert "session_conduct: " not in result.output


# --- bootstrap tickets ---------------------------------------------------------


def test_resolve_conflicts_bootstrap_launch_is_stateless_and_receives_pr_arg(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shipped command ticket stays agent-backed and receives its optional
    PR selector through the generic launch-argument prompt seam."""
    _allow_interactive_tty(monkeypatch)
    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    cfg = load_config(active_task)
    before = [(ref.id_slug, Ticket.read(ref.ticket_path).status) for ref in list_tasks(cfg)]
    result = CliRunner().invoke(
        app, ["launch", "bootstrap/resolve-conflicts", "631"]
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    prompt = _prompt_arg(calls[0])
    assert "## Launch arguments" in prompt
    assert '["631"]' in prompt
    assert "gh pr list --state open --limit 10000" in prompt
    assert "Continue only\n   when it reports `CONFLICTING`" in prompt
    assert "git merge-base --is-ancestor origin/main HEAD" not in prompt
    assert "open PRs only" in prompt
    after = [(ref.id_slug, Ticket.read(ref.ticket_path).status) for ref in list_tasks(cfg)]
    assert after == before


@pytest.fixture
def bootstrap_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A coga/ with a bootstrap/ticket launch target and a stub skill, no tasks."""
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        skills:
          - bootstrap/ticket
        ---

        ## Description

        Persistent launch target for the bootstrap/ticket skill.
        """,
    )
    _write(
        company / "skills" / "bootstrap" / "ticket" / "SKILL.md",
        """
        ---
        name: bootstrap/ticket
        description: Author a Coga task.
        ---

        Interview, create, fill in the ticket. Stop.
        """,
    )
    monkeypatch.chdir(company)
    return company


@pytest.mark.parametrize(
    "outcome",
    [
        ReplOutcome(exit_code=0, kind="done"),
        ReplOutcome(exit_code=0, kind="natural"),
        ReplOutcome(exit_code=7, kind="natural"),
        ReplOutcome(exit_code=143, kind="crash"),
        ReplOutcome(exit_code=_TIMEOUT_EXIT_CODE, kind="timeout"),
    ],
    ids=("done", "natural-zero", "natural-nonzero", "crash", "timeout"),
)
def test_launch_returns_spawned_bootstrap_termination_kind(
    bootstrap_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: ReplOutcome,
) -> None:
    """An in-process delegator can distinguish the bootstrap done sentinel
    from every spawned failure; pre-spawn refusals raise LaunchBail.
    """
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )
    monkeypatch.setattr(
        "coga.launch.run_with_done_marker",
        lambda *args, **kwargs: outcome,
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: None,
    )

    kind = launch_module.launch(
        "bootstrap/ticket",
        args=[],
        agent_override=None,
        prompt_report=False,
        idle_timeout=900.0,
        max_session=None,
        return_timeout=True,
    )

    assert kind.kind == outcome.kind
    assert kind.exit_code == outcome.exit_code


def test_launch_before_spawn_callback_runs_at_bootstrap_spawn_boundary(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The in-process hook runs after preflight but before the agent starts."""
    events: list[str] = []
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    def fake_supervisor(*args, **kwargs) -> ReplOutcome:  # type: ignore[no-untyped-def]
        assert events == ["before-spawn"]
        events.append("spawn")
        return ReplOutcome(exit_code=0, kind="done")

    monkeypatch.setattr(
        "coga.launch.run_with_done_marker", fake_supervisor
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: None,
    )

    kind = launch_module.launch_with_before_spawn(
        "bootstrap/ticket",
        agent_override=None,
        idle_timeout=900.0,
        max_session=None,
        return_timeout=True,
        launch_context="recurring",
        before_spawn=lambda: events.append("before-spawn"),
    )

    assert kind.kind == "done"
    assert events == ["before-spawn", "spawn"]


def test_python_launch_uses_ordinary_defaults(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An internal caller can omit every CLI option without leaking sentinels."""
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr(launch_module.shutil, "which", lambda name, **kwargs: f"/usr/bin/{name}")
    calls = []
    def supervisor(*args, **kwargs):
        calls.append(kwargs)
        assert kwargs["idle_timeout"] is None
        assert kwargs["max_session"] is None
        return ReplOutcome(0, "natural")
    monkeypatch.setattr(launch_module, "run_with_done_marker", supervisor)
    result = launch_module.launch("bootstrap/ticket")
    assert result == launch_module.LaunchResult()
    assert len(calls) == 1


def test_python_launch_refusal_is_an_exception_with_a_reason(
    bootstrap_repo: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(launch_module.LaunchBail) as caught:
        launch_module.launch("bootstrap/nonexistent-audit-target")
    assert caught.value.code == 2
    assert "nonexistent-audit-target" in caught.value.reason
    assert isinstance(caught.value, Exception)
    assert "nonexistent-audit-target" not in capsys.readouterr().err


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_python_launch_translates_signal_after_unwinding_library_handlers(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch, signum: int,
) -> None:
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr(launch_module.shutil, "which", lambda name, **kwargs: f"/usr/bin/{name}")
    handlers: dict[int, object] = {}

    def remember_handler(received: int, handler: object) -> None:
        handlers[received] = handler

    def supervisor(*args: object, **kwargs: object) -> ReplOutcome:
        handler = handlers[signum]
        assert callable(handler)
        try:
            handler(signum, None)
        except Exception as exc:
            pytest.fail(f"termination reached a recoverable exception handler: {exc}")
        raise AssertionError("termination handler returned")

    monkeypatch.setattr(launch_module.signal, "signal", remember_handler)
    monkeypatch.setattr(launch_module, "run_with_done_marker", supervisor)
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", lambda **kwargs: None)
    with pytest.raises(launch_module.LaunchBail) as caught:
        launch_module.launch("bootstrap/ticket")
    assert caught.value.code == 128 + signum
    assert isinstance(caught.value, Exception)


def test_python_launch_translates_dependency_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def dependency_exit(*args, **kwargs):
        raise SystemExit(17)
    monkeypatch.setattr(launch_module, "_launch", dependency_exit)
    with pytest.raises(launch_module.LaunchBail) as caught:
        launch_module.launch("ordinary-task")
    assert caught.value.code == 17
    assert isinstance(caught.value, Exception)


def test_successive_launches_keep_arguments_and_refusal_state_separate(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr(launch_module.shutil, "which", lambda name, **kwargs: f"/usr/bin/{name}")
    prompts: list[str] = []
    def supervisor(cmd, *args, **kwargs):
        prompts.append(_prompt_arg(cmd))
        return ReplOutcome(0, "natural")
    monkeypatch.setattr(launch_module, "run_with_done_marker", supervisor)

    launch_module.launch("bootstrap/ticket", args=["first invocation"])
    with pytest.raises(launch_module.LaunchBail):
        launch_module.launch("bootstrap/ticket", agent_override="missing-agent")
    launch_module.launch("bootstrap/ticket", args=["second invocation"])

    assert len(prompts) == 2
    assert '["first invocation"]' in prompts[0]
    assert '["second invocation"]' in prompts[1]
    assert "first invocation" not in prompts[1]


def test_launch_before_spawn_callback_skipped_on_preflight_refusal(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CLI preflight refusal cannot publish caller-owned start state."""
    events: list[str] = []
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: None)

    with pytest.raises(launch_module.LaunchBail) as excinfo:
        launch_module.launch_with_before_spawn(
            "bootstrap/ticket",
            agent_override=None,
            idle_timeout=900.0,
            max_session=None,
            return_timeout=True,
            launch_context="recurring",
            before_spawn=lambda: events.append("before-spawn"),
        )

    assert excinfo.value.code == 2
    assert events == []


def test_local_bootstrap_ticket_resolves_without_packaged_twin(
    bootstrap_repo: Path,
) -> None:
    """A repo-local agent command ticket can mint its own bootstrap target."""
    from coga.tasks import resolve_bootstrap

    local = bootstrap_repo / "bootstrap" / "custom-check"
    _write(
        local / "ticket.md",
        """
        ---
        title: Local check
        ---

        ## Description

        Run the repo-local check.
        """,
    )

    cfg = load_config(bootstrap_repo)
    ref = resolve_bootstrap(cfg, "custom-check")

    assert ref.path == local
    assert ref.id_slug == "bootstrap/custom-check"


def test_unknown_bootstrap_ticket_names_both_checked_paths(
    bootstrap_repo: Path,
) -> None:
    from coga.tasks import TaskNotFoundError, resolve_bootstrap

    cfg = load_config(bootstrap_repo)
    with pytest.raises(TaskNotFoundError) as exc:
        resolve_bootstrap(cfg, "no-such-verb")

    message = str(exc.value)
    assert str(
        bootstrap_repo / "bootstrap" / "no-such-verb" / "ticket.md"
    ) in message
    assert "bootstrap/no-such-verb" in message


def test_local_agent_command_ticket_plus_alias_mints_new_verb(
    bootstrap_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A local command ticket plus an alias adds a judgment-bearing verb."""
    from coga.cli import main

    _write(
        bootstrap_repo / "bootstrap" / "hello" / "ticket.md",
        """
        ---
        title: Hello
        ---

        ## Description

        Greet the launch argument.
        """,
    )
    (bootstrap_repo / "coga.toml").write_text(
        (bootstrap_repo / "coga.toml").read_text(encoding="utf-8")
        + '\n[aliases]\nhello = "launch bootstrap/hello"\n',
        encoding="utf-8", newline="\n",
    )

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )
    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("sys.argv", ["coga", "hello", "world"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code in (0, None)
    assert len(calls) == 1
    prompt = _prompt_arg(calls[0])
    assert "Greet the launch argument." in prompt
    assert "## Launch arguments" in prompt
    assert '["world"]' in prompt
    assert list_tasks(load_config(bootstrap_repo)) == []


def test_launch_bare_bootstrap_does_not_post_to_slack(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare bootstrap-ticket launches (e.g. `coga chat`) are stateless re-entry points,
    not "started work" events — they must not post to Slack."""
    posts: list[str] = []
    _allow_interactive_tty(monkeypatch)

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        posts.append((json or {}).get("text", ""))

        class R:
            status_code = 200

        return R()

    class _Result:
        returncode = 0

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr(
        "coga.launch.subprocess.run",
        lambda cmd, env=None, check=False, cwd=None: _Result(),
    )
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output
    assert posts == []


def test_launch_bootstrap_skips_status_and_lock(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["prompt"] = _prompt_arg(cmd)
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output

    # No lock file left behind; in fact none was ever written.

    # Skill body composed into the prompt.
    prompt = captured["prompt"]
    assert isinstance(prompt, str)
    assert "Skill: bootstrap/ticket" in prompt
    assert "Interview, create, fill in the ticket." in prompt
    # Header still uses the bootstrap/<name> id_slug.
    assert "bootstrap/ticket" in prompt

    # The repo-global log recorded the launch.
    log = _read_log(bootstrap_repo)
    assert "launched (operator=claude, agent=claude)" in log


def test_launch_discussion_bootstrap_uses_discussion_template(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discussion tickets ride the composed prompt as system context instead of
    making it the first user message."""
    # Rewrite the fixture's coga.toml to add a discussion template on claude.
    _write(
        bootstrap_repo / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        discussion = "--append-system-prompt {prompt}"
        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"
        """,
    )

    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    # Argv: [cli, --append-system-prompt, <prompt>]
    assert cmd[0] == "claude"
    assert cmd[1] == "--append-system-prompt"
    assert "Skill: bootstrap/ticket" in cmd[2]
    assert cmd[3] == "Begin"


def test_launch_orient_bootstrap_stays_silent(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        bootstrap_repo / "bootstrap" / "orient" / "ticket.md",
        """
        ---
        title: Chat
        ---

        ## Description

        Persistent launch target for a discussion session.
        """,
    )
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/orient"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[-1] != "Begin"


def test_launch_regular_task_does_not_use_discussion_template(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        active_task / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        discussion = "--append-system-prompt {prompt}"
        """,
    )
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert cmd[0] == "claude"
    assert "Fix retry logic" in _prompt_arg(cmd)


def test_launch_bootstrap_agent_override_uses_requested_agent(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/ticket", "--agent", "codex"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "codex"
    assert cmd[1] == "-c"
    assert "Skill: bootstrap/ticket" in _prompt_arg(cmd)
    assert cmd[-1] == "Begin"

    log = _read_log(bootstrap_repo)
    # A stateless bootstrap target's own agent is its operator, so an override
    # is still recorded as the temporary worker beside it.
    assert "operator=claude, launch_agent=codex, agent=codex" in log


def test_launch_agent_override_normal_task_uses_requested_agent_without_reassigning(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["env"] = env
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "fix-retry-logic", "--agent", "codex"])
    assert result.exit_code == 0, result.output

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "codex"
    # Completion attribution credits the agent that ran, not the routed one.
    env = captured["env"]
    assert isinstance(env, dict)
    assert env[EXPECTED_AGENT_ENV] == "codex"

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    from coga.ticket import Ticket
    # The override never writes to the ticket: its main-agent choice is intact.
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.agent == "claude"
    assert "assignee" not in ticket.frontmatter

    log = _read_log(active_task)
    assert "operator=claude, launch_agent=codex, agent=codex" in log




@pytest.mark.parametrize(
    ("local_status", "control_status"),
    [
        ("active", "paused"),
        ("active", "blocked"),
        ("in_progress", "done"),
    ],
)
@pytest.mark.parametrize(
    "initial_status",
    ["draft", "active", "paused", "blocked"],
)
def _seed_single_checkout_human_review(
    git_repo,
    *,
    title: str,
    status: str,
    branch: str = "feature/review",
    force_directory: bool = False,
    keep_steps: int | None = None,
) -> tuple[dict[str, str], Path]:
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg,
        title=title,
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
        force_directory=force_directory,
    )
    created_path = Path(created["path"])
    ticket_path = (
        created_path / "ticket.md" if created_path.is_dir() else created_path
    )
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = status
    ticket.frontmatter["step"] = "2 (review)"
    if keep_steps is not None:
        # Trimming the frozen snapshot has to happen *before* the control
        # commit: the frozen step roles are routing inputs, so a feature-only
        # edit is exactly the drift the publication lease refuses.
        assert isinstance(ticket.workflow, dict)
        ticket.workflow["steps"] = ticket.workflow["steps"][:keep_steps]
    hold_by_owner(ticket)
    ticket.write(ticket_path)
    replace_blackboard(
        ticket_path,
        dedent(
            f"""
            ## Dev
            branch: {branch}
            worktree: {git_repo.root}
            pr: https://github.com/example/repo/pull/8
            """
        ),
    )
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", f"ticket: seed {status} review")
    git_repo.git("push", "origin", "main")
    if branch != "main":
        git_repo.checkout_branch(branch)
    (git_repo.root / "implementation.txt").write_text("reviewed branch\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "implementation.txt")
    git_repo.git("commit", "-m", "feature: reviewed branch")
    git_repo.git("push", "-u", "origin", branch)
    return created, ticket_path


def test_human_assist_without_tty_refuses_before_alignment(
    git_repo,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    created, _ticket_path = _seed_single_checkout_human_review(
        git_repo,
        title="Require a TTY before assist alignment",
        status="in_progress",
    )
    _deny_interactive_tty(monkeypatch)

    with pytest.raises(launch_module.LaunchBail) as excinfo:
        launch_module.launch(
            str(created["slug"]),
            agent_override="claude",
            prompt_report=False,
            idle_timeout=None,
            max_session=None,
            return_timeout=False,
        )

    assert excinfo.value.code == 2
    assert "agent launch requires a TTY" in excinfo.value.reason


def test_human_assist_without_tty_does_not_protect_rewritten_log(
    git_repo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created, _ticket_path = _seed_single_checkout_human_review(
        git_repo,
        title="Reject rewritten TTY-less assist log",
        status="in_progress",
    )
    (git_repo.coga_os / "log.md").write_text("rewritten audit log\n", encoding="utf-8", newline="\n")
    _deny_interactive_tty(monkeypatch)

    with pytest.raises(launch_module.LaunchBail) as excinfo:
        launch_module.launch(
            str(created["slug"]),
            agent_override="claude",
            prompt_report=False,
            idle_timeout=None,
            max_session=None,
            return_timeout=False,
        )

    assert excinfo.value.code == 2


def test_launch_human_handoff_without_agent_override_is_still_refused(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    hold_by_owner(ticket)
    ticket.write(ref.ticket_path)
    _allow_interactive_tty(monkeypatch)

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("human handoff should fail before spawning an agent")

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code == 2
    assert "Cannot launch fix-retry-logic" in (
        result.output + (result.stderr or "")
    )
    assert "hands off to the owner (marc)" in (
        result.output + (result.stderr or "")
    )
    assert Ticket.read(ref.ticket_path).current_step()["assignee"] == "owner"


def test_launch_bootstrap_unknown_ticket(
    bootstrap_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["launch", "bootstrap/does-not-exist"])
    assert result.exit_code == 2
    assert "bootstrap/does-not-exist" in (result.output + (result.stderr or ""))


# --- unit: supervisor stop logic (agent rotation vs human handoff) -------------


def _wf_ticket(
    step: str,
    second_role: str = "other-agent",
    status: str = "in_progress",
    agent: str = "claude",
) -> Ticket:
    """Build an in-memory 2-step-workflow ticket for stop-reason tests.

    The *roles* decide who holds each step, so `second_role` is what a
    stop-reason test varies — there is no stored assignment to set.
    """
    return Ticket(
        frontmatter={
            "status": status,
            "owner": "marc",
            "agent": agent,
            "step": step,
            "workflow": {
                "name": "test/wf",
                "steps": [
                    {"name": "a", "assignee": "agent"},
                    {"name": "b", "assignee": second_role},
                ],
            },
        },
        body="",
    )


def test_harness_chains_across_agent_rotation(active_task: Path) -> None:
    """main -> peer (an `other-agent` step) must NOT stop."""
    from coga.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)")
    after = _wf_ticket("2 (b)")
    assert _harness_stop_reason(ref, before, after, cfg) is None


def test_harness_chains_same_agent(active_task: Path) -> None:
    from coga.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "agent")
    after = _wf_ticket("2 (b)", "agent")
    assert _harness_stop_reason(ref, before, after, cfg) is None


def test_harness_stops_on_human_handoff(active_task: Path) -> None:
    """A next step the workflow hands to the owner returns control."""
    from coga.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "owner")
    after = _wf_ticket("2 (b)", "owner")
    reason = _harness_stop_reason(ref, before, after, cfg)
    assert reason is not None
    assert "hands off to marc" in reason


def test_harness_stops_on_terminal_and_paused(active_task: Path) -> None:
    from coga.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    done = _wf_ticket("2 (b)", "claude", status="done")
    canceled = _wf_ticket("2 (b)", "claude", status="canceled")
    paused = _wf_ticket("2 (b)", "claude", status="paused")
    assert "done" in (_harness_stop_reason(ref, before, done, cfg) or "")
    assert "canceled" in (_harness_stop_reason(ref, before, canceled, cfg) or "")
    assert "paused" in (_harness_stop_reason(ref, before, paused, cfg) or "")


def test_harness_stops_when_no_progress(active_task: Path) -> None:
    from coga.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    before = _wf_ticket("1 (a)", "claude")
    after = _wf_ticket("1 (a)", "claude")
    reason = _harness_stop_reason(ref, before, after, cfg)
    assert reason is not None
    assert "still on" in reason


def test_harness_stops_on_workflowless_task_without_marking_done(
    active_task: Path,
) -> None:
    """A workflow-less task left in_progress reports 'no workflow to chain',
    not the misleading 'still on no workflow step' no-progress message."""
    from coga.launch import _harness_stop_reason

    cfg = load_config(active_task)
    ref = list_tasks(cfg)[0]
    wfless = Ticket(
        frontmatter={
            "status": "in_progress",
            "assignee": "claude",
            "workflow": None,
        },
        body="",
    )
    reason = _harness_stop_reason(ref, wfless, wfless, cfg)
    assert reason is not None
    assert "no workflow to chain" in reason
    assert "still on" not in reason


def test_launch_interactive_rotates_across_agents(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The supervisor relaunches the *next* agent across an assignee change.

    Workflow: implement (agent=claude) → peer (other-agent=codex) →
    review (human). One `coga launch` should spawn claude, then — after the
    claude→codex bump — auto-relaunch codex as a fresh process, then stop at
    the human review step. This is the cross-agent auto-relaunch.
    """
    _write(
        active_task / "workflows" / "rotate.md",
        """
        ---
        name: rotate
        description: Agent rotation chain.
        steps:
          - name: implement
            assignee: agent
          - name: peer
            assignee: other-agent
          - name: review
            assignee: owner
        ---

        ## implement
        Do the work.

        ## peer
        Peer review by the other agent.

        ## review
        Review the result.
        """,
    )
    cfg = load_config(active_task)
    ref = create_task(
        cfg=cfg,
        title="Rotate work",
        workflow_name="rotate",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    # Two agent runs: claude (implement), then codex (peer) auto-relaunched
    # across the assignee change. The chain stops at the human review step.
    assert len(calls) == 2, calls
    assert calls[0][0] == "claude"
    assert calls[1][0] == "codex"

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "3 (review)"
    assert ticket.current_step()["assignee"] == "owner"


def test_launch_rotation_stops_when_next_agent_cli_missing(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the chain rotates to an agent whose CLI is absent, stop cleanly."""
    _write(
        active_task / "workflows" / "rotate2.md",
        """
        ---
        name: rotate2
        description: Agent rotation chain.
        steps:
          - name: implement
            assignee: agent
          - name: peer
            assignee: other-agent
        ---

        ## implement
        Do the work.

        ## peer
        Peer review.
        """,
    )
    cfg = load_config(active_task)
    ref = create_task(
        cfg=cfg,
        title="Rotate2 work",
        workflow_name="rotate2",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    slug = ref["slug"]
    calls: list[list[str]] = []
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return _Result()

    # claude resolves, codex does not (simulate codex not installed).
    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which",
        lambda name: "/usr/bin/claude" if name == "claude" else None,
    )

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    # Only claude ran; codex CLI missing → stop cleanly, hand back to caller.
    assert len(calls) == 1, calls
    assert calls[0][0] == "claude"
    assert "Agent CLI 'codex' not found" in result.output
    assert "Set `cli` in [agents.codex] in coga.toml" in result.output
    assert "http" not in result.output

    from coga.ticket import Ticket
    ticket = Ticket.read(Path(ref["path"]))
    assert ticket.step == "2 (peer)"
    assert ticket.current_step()["assignee"] == "other-agent"


def test_conduct_is_a_composed_layer_not_a_prompt_suffix(
    active_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Conduct reaches the agent as the selected `session_conduct` layer.

    `prompt_suffix` is left for genuinely appended invocation input such as
    `## Launch arguments`; an appended conduct block is what made a queued
    prompt carry a rule and its inverse.
    """
    seen: dict[str, object] = {}
    real_spawn = launch_module.spawn_agent_session

    def capture(*args, **kwargs):  # type: ignore[no-untyped-def]
        seen["prompt_suffix"] = kwargs.get("prompt_suffix", "")
        seen["launch_context"] = kwargs.get("launch_context")
        return real_spawn(*args, **kwargs)

    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )
    monkeypatch.setattr(
        "coga.launch.run_with_done_marker",
        lambda *args, **kwargs: ReplOutcome(exit_code=0, kind="done"),
    )
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(launch_module, "spawn_agent_session", capture)

    launch_module.launch(
        "fix-retry-logic",
        args=[],
        agent_override=None,
        prompt_report=False,
        idle_timeout=None,
        max_session=None,
        return_timeout=False,
    )

    # The public CLI spelling is attended, and it appends no conduct.
    assert seen["launch_context"] == "attended"
    assert seen["prompt_suffix"] == ""


def test_queue_conduct_resources_require_durable_terminal_transitions() -> None:
    """Both queue conduct layers still demand a real Coga transition."""
    from coga.compose import SESSION_CONDUCT_RESOURCES

    recurring = (
        files("coga.resources")
        .joinpath(SESSION_CONDUCT_RESOURCES["recurring"])
        .read_text(encoding="utf-8")
    )
    assert "coga block" in recurring
    assert "coga bump" in recurring
    assert "stateless `bootstrap/<name>` command ticket" in recurring
    assert "coga mark done bootstrap/<name>" in recurring
    assert "`coga slack` is only a non-terminal FYI" in recurring
    assert "does not release the queue" in recurring


# --- pre-spawn file errors are not "the agent CLI is missing" -----------------
#
# `spawn_agent_session` composes the prompt, writes it to disk, and appends the
# log before it spawns anything. A blanket `except FileNotFoundError` around
# that call therefore reported a vanished skill/context — or any other missing
# path — as `Failed to spawn agent: 'claude' not found.`, sending the operator
# to debug a `cli` setting that `shutil.which` had already verified two lines
# earlier. Only `AgentCliNotFound` carries the genuine CLI case.


def test_launch_names_the_missing_file_instead_of_blaming_the_cli(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reported incident: the entry preflight resolves every layer fine,
    then the step's one composition hits a file that vanished under it (a
    concurrent checkout / mid-sync tree). That must name the path — the old
    blanket handler called it `'claude' not found` two lines after
    `shutil.which` had already located the CLI."""
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    missing = str(active_task / "skills" / "code" / "open-pr" / "SKILL.md")
    calls: list[int] = []

    def vanished(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(1)
        raise FileNotFoundError(2, "No such file or directory", missing)

    monkeypatch.setattr("coga.launch.compose_prompt", vanished)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    slug = list_tasks(load_config(active_task))[0].id_slug
    result = CliRunner().invoke(app, ["launch", slug])

    assert len(calls) == 1, calls
    assert result.exit_code != 0
    assert missing in result.output
    assert "No such file or directory" in result.output
    assert "not the agent CLI" in result.output
    assert "'claude' not found" not in result.output


def test_launch_preflight_names_the_missing_file_too(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A layer file that vanishes between resolve and read in the entry
    preflight is named, not dumped as a bare traceback, and refuses before
    any lifecycle write."""
    slack = _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    missing = str(active_task / "context.md")

    def boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError(2, "No such file or directory", missing)

    def never_compose(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a refused preflight must not compose")

    monkeypatch.setattr("coga.launch.resolve_prompt_layers", boom)
    monkeypatch.setattr("coga.launch.compose_prompt", never_compose)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    ref = list_tasks(load_config(active_task))[0]
    original = ref.ticket_path.read_bytes()
    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code != 0
    assert missing in result.output
    assert "not the agent CLI" in result.output
    assert "'claude' not found" not in result.output
    assert ref.ticket_path.read_bytes() == original
    assert slack == []


def _count_prompt_work(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Count launch's prompt compositions and the layer resolutions under them.

    `compose_prompt` is counted where launch calls it; resolution is counted in
    both modules, since a composition that cannot reuse the preflight's layers
    resolves them itself inside `coga.compose`.
    """
    import coga.compose as compose_module

    counts = {"compose": 0, "resolve": 0}
    real_compose = launch_module.compose_prompt
    real_resolve = compose_module.resolve_prompt_layers

    def compose(*args, **kwargs):  # type: ignore[no-untyped-def]
        counts["compose"] += 1
        return real_compose(*args, **kwargs)

    def resolve(*args, **kwargs):  # type: ignore[no-untyped-def]
        counts["resolve"] += 1
        return real_resolve(*args, **kwargs)

    monkeypatch.setattr("coga.launch.compose_prompt", compose)
    monkeypatch.setattr("coga.launch.resolve_prompt_layers", resolve)
    monkeypatch.setattr("coga.compose.resolve_prompt_layers", resolve)
    return counts


def test_plain_attended_launch_composes_its_first_prompt_once(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The entry preflight resolves the layers; the spawn composes once from
    them, rendering the ticket it starts on (now `in_progress`) and the
    checkout notice."""
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    counts = _count_prompt_work(monkeypatch)
    prompts: list[str] = []

    def fake_run(cmd, env=None, check=False, cwd=None):  # type: ignore[no-untyped-def]
        prompts.append(cmd[-1])

        class _Result:
            returncode = 0

        return _Result()

    monkeypatch.setattr("coga.launch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    result = CliRunner().invoke(app, ["launch", "fix-retry-logic"])

    assert result.exit_code == 0, result.output
    assert counts == {"compose": 1, "resolve": 1}
    assert len(prompts) == 1
    assert "Status: in_progress" in prompts[0]
    assert "## Checkout (runtime)" not in prompts[0]
    assert "using preflighted prompt" not in result.output


def test_plain_attended_launch_refuses_missing_layer_before_lifecycle_write(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slack = _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    counts = _count_prompt_work(monkeypatch)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )
    ref = list_tasks(load_config(active_task))[0]
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["contexts"] = ["missing/topic"]
    ticket.write(ref.ticket_path)
    original = ref.ticket_path.read_bytes()
    log = active_task / "log.md"
    log_before = log.read_bytes() if log.exists() else None

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code != 0
    assert "references context 'missing/topic'" in result.output
    assert counts == {"compose": 0, "resolve": 1}
    assert ref.ticket_path.read_bytes() == original
    assert (log.read_bytes() if log.exists() else None) == log_before
    assert slack == []


def test_launch_still_reports_a_genuinely_missing_agent_cli(
    active_task: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`AgentCliNotFound` keeps the shared `coga.toml` remedy."""
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)

    def boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AgentCliNotFound("claude")

    monkeypatch.setattr("coga.launch.run_with_done_marker", boom)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )

    slug = list_tasks(load_config(active_task))[0].id_slug
    result = CliRunner().invoke(app, ["launch", slug])

    assert result.exit_code != 0
    assert (
        "Failed to spawn agent: Agent CLI 'claude' not found."
        in result.output
    )
    assert "Set `cli` in [agents.claude] in coga.toml" in result.output
    assert "http" not in result.output


def test_missing_launch_file_message_survives_a_filename_less_error() -> None:
    """Not every FileNotFoundError carries `.filename`; still don't blame the CLI."""
    message = missing_launch_file_message(FileNotFoundError("prompt dir gone"))
    assert "a file it needed" in message
    assert "not the agent CLI" in message


# --- checkout normalization (coga/checkouts) -------------------------------------


class _CheckoutSession:
    """Fake agent session that records its checkout and then acts like an agent.

    `actions[i]` runs inside session `i` from the primary `coga/` directory
    before the session's final `coga bump` (skipped when it returns False).
    """

    def __init__(self, git_repo, actions=(), exit_codes=()) -> None:  # type: ignore[no-untyped-def]
        self.git_repo = git_repo
        self.actions = list(actions)
        self.exit_codes = list(exit_codes)
        self.seen: list[tuple[str, str | None, str | None]] = []

    def __call__(self, cfg, ref, ticket, agent, *args, **kwargs):  # type: ignore[no-untyped-def]
        env = kwargs.get("env") or {}
        index = len(self.seen)
        self.seen.append(
            (
                self.git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip(),
                env.get("COGA_CHECKOUT_RETURN"),
                ticket.step,
            )
        )
        action = self.actions[index] if index < len(self.actions) else None
        bump = True if action is None else action(ref) is not False
        if bump:
            prev = os.getcwd()
            os.chdir(self.git_repo.coga_os)
            try:
                result = CliRunner().invoke(app, ["bump", ref.id_slug])
            finally:
                os.chdir(prev)
            assert result.exit_code == 0, result.output
        code = self.exit_codes[index] if index < len(self.exit_codes) else 0
        return launch_module.AgentSessionResult(code, "done" if code == 0 else "crash")


def _checkout_launch_env(monkeypatch: pytest.MonkeyPatch, session) -> None:  # type: ignore[no-untyped-def]
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr(
        "coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}"
    )
    monkeypatch.setattr("coga.launch.spawn_agent_session", session)


def _published_checkout_task(git_repo, title: str = "Checkout normalization") -> TaskRef:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg,
        title=title,
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    git_repo.git("add", "--", str(created["path"]))
    git_repo.git("commit", "-m", "Seed checkout task")
    git_repo.git("push", "origin", "main")
    return next(ref for ref in list_tasks(cfg) if ref.id_slug == created["slug"])


def _branch_and_tip(git_repo) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    return (
        git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        git_repo.git("rev-parse", "HEAD").strip(),
    )


def _origin_main(git_repo) -> str:  # type: ignore[no-untyped-def]
    return git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()


def _assert_clean_control(git_repo) -> None:  # type: ignore[no-untyped-def]
    assert _branch_and_tip(git_repo) == ("main", _origin_main(git_repo))
    assert git_repo.git("status", "--porcelain", "--untracked-files=all") == ""


def _work_on_feature_branch(git_repo, *, handoff: str, leave: str | None = None):  # type: ignore[no-untyped-def]
    """An implement-style session: branch, commit code, write the handoff."""

    def act(ref: TaskRef) -> None:
        git_repo.git("switch", "-c", "feature/work")
        (git_repo.root / "feature.py").write_text("print('work')\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "feature.py")
        git_repo.git("commit", "-m", "Implement feature")
        # The ticket copy on the branch predates control; load control's copy
        # before writing the handoff (coga/checkouts).
        rel = ref.ticket_path.relative_to(git_repo.root).as_posix()
        git_repo.git("restore", "--source=origin/main", "--worktree", "--", rel)
        replace_blackboard(
            ref.ticket_path,
            read_blackboard(ref.ticket_path) + f"\n## Handoff\n\n{handoff}\n",
        )
        if leave is not None:
            (git_repo.root / leave).write_text("unpublished work\n", encoding="utf-8", newline="\n")

    return act


class _UnsignalledCheckoutSession(_CheckoutSession):
    """A `_CheckoutSession` that crosses the real pre-spawn boundary and whose
    first session reports no done signal (as with a lost `COGA_*` env)."""

    def __call__(self, cfg, ref, ticket, agent, *args, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("before_spawn") is not None:
            kwargs["before_spawn"]()
        first = not self.seen
        result = super().__call__(cfg, ref, ticket, agent, *args, **kwargs)
        return result._replace(done_signalled=not first)


@pytest.mark.parametrize("argv", [
    ["launch", "bootstrap/orient", "--prompt-report"],
    ["launch", "bootstrap/resolve-conflicts"],
])
def test_launch_prompt_report_and_other_bootstrap_keep_the_checkout(
    argv: list[str],
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _published_checkout_task(git_repo)
    git_repo.checkout_branch("feature/x")
    session = _CheckoutSession(git_repo, actions=[lambda _ref: False])
    _checkout_launch_env(monkeypatch, session)
    before = _branch_and_tip(git_repo)

    report = CliRunner().invoke(app, ["launch", ref.id_slug, "--prompt-report"])
    bootstrap = CliRunner().invoke(app, argv)

    assert report.exit_code == 0, report.output
    assert bootstrap.exit_code == 0, bootstrap.output
    expected = [] if "--prompt-report" in argv else [("feature/x", None)]
    assert [seen[:2] for seen in session.seen] == expected
    assert _branch_and_tip(git_repo) == before


def test_delegated_orientation_keeps_callers_checkout(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    git_repo.checkout_branch("feature/delegated")
    before = _branch_and_tip(git_repo)
    session = _CheckoutSession(git_repo, actions=[lambda _ref: False])
    _checkout_launch_env(monkeypatch, session)

    launch_module.launch_with_before_spawn(
        "bootstrap/orient",
        agent_override=None,
        idle_timeout=None,
        max_session=None,
        return_timeout=True,
        launch_context="recurring",
        before_spawn=lambda: None,
    )

    assert [seen[:2] for seen in session.seen] == [("feature/delegated", None)]
    assert _branch_and_tip(git_repo) == before


@pytest.mark.parametrize("target", ["task", "bootstrap/orient"])
def test_launch_without_a_remote_keeps_its_checkout(
    target: str,
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = _published_checkout_task(git_repo)
    git_repo.checkout_branch("feature/x")
    git_repo.git("remote", "remove", "origin")
    session = _CheckoutSession(git_repo, actions=[lambda _ref: False])
    _checkout_launch_env(monkeypatch, session)

    result = CliRunner().invoke(
        app, ["launch", ref.id_slug if target == "task" else target]
    )

    assert result.exit_code == 0, result.output
    assert session.seen[0][:2] == ("feature/x", None)
    assert _branch_and_tip(git_repo)[0] == "feature/x"


@pytest.mark.parametrize("file_form", [False, True])
@pytest.mark.parametrize("status", ["done", "canceled"])
def test_terminal_status_probe_waits_for_stable_exact_ticket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_form: bool, status: str
) -> None:
    ref = TaskRef("dream", tmp_path / ("dream.md" if file_form else "dream"), file_form=file_form)
    _write(ref.ticket_path, "---\nstatus: in_progress\nperiod_generation: current\n---\n")
    now = [10.0]
    monkeypatch.setattr("coga.launch.time.monotonic", lambda: now[0])
    probe = launch_module._terminal_status_probe(
        SimpleNamespace(repo_root=tmp_path, git_enabled=False), ref, Ticket.read(ref.ticket_path)
    )
    assert probe is not None
    _write(tmp_path / "other.md", "---\nstatus: done\n---\n")
    assert probe() is None
    _write(ref.ticket_path, f"---\nstatus: {status}\nperiod_generation: current\n---\n")
    assert probe() is None  # Cached until the one-second poll.
    now[0] += 1
    assert probe() is None
    now[0] += 4
    assert probe() is None
    now[0] += 1
    assert probe() == status


@pytest.mark.parametrize("replacement", [
    None,
    "not a ticket",
    "---\nstatus: [done]\n---\n",
    "---\nstatus: blocked\nperiod_generation: current\n---\n",
    "---\nstatus: in_progress\nstep: 2 (next)\nperiod_generation: current\n---\n",
])
def test_terminal_status_probe_ignores_unproven_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str | None
) -> None:
    ref = TaskRef("dream", tmp_path / "dream")
    _write(ref.ticket_path, "---\nstatus: in_progress\nperiod_generation: current\n---\n")
    now = [10.0]
    monkeypatch.setattr("coga.launch.time.monotonic", lambda: now[0])
    probe = launch_module._terminal_status_probe(
        SimpleNamespace(repo_root=tmp_path, git_enabled=False), ref, Ticket.read(ref.ticket_path)
    )
    assert probe is not None
    _write(ref.ticket_path, "---\nstatus: done\nperiod_generation: current\n---\n")
    assert probe() is None
    if replacement is None:
        ref.ticket_path.unlink()
    else:
        _write(ref.ticket_path, replacement)
    now[0] += 5
    assert probe() is None
    _write(ref.ticket_path, "---\nstatus: done\nperiod_generation: current\n---\n")
    now[0] += 1
    assert probe() is None  # Lost proof resets the settling period.
    now[0] += 5
    assert probe() == "done"


def test_terminal_status_probe_ignores_state_terminal_since_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A copy already terminal at the first observation (for example a stale
    published blob from an earlier life of the path) is not this session's
    transition; only a terminal state observed after an open one counts."""
    ref = TaskRef("dream", tmp_path / "dream")
    _write(ref.ticket_path, "---\nstatus: done\n---\n")
    now = [10.0]
    monkeypatch.setattr("coga.launch.time.monotonic", lambda: now[0])
    probe = launch_module._terminal_status_probe(
        SimpleNamespace(repo_root=tmp_path, git_enabled=False), ref, Ticket.read(ref.ticket_path)
    )
    assert probe is not None
    for _ in range(8):
        assert probe() is None
        now[0] += 1
    _write(ref.ticket_path, "---\nstatus: in_progress\n---\n")
    assert probe() is None
    _write(ref.ticket_path, "---\nstatus: done\n---\n")
    now[0] += 1
    assert probe() is None
    now[0] += 5
    assert probe() == "done"


def test_terminal_status_probe_reads_local_ticket_outside_git_root(
    git_repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The terminal backstop needs only the local ticket path."""
    cfg = load_config(git_repo.coga_os)
    outside = tmp_path / "elsewhere" / "dream"
    _write(outside / "ticket.md", "---\nstatus: in_progress\n---\n")
    ref = TaskRef("dream", outside)
    now = [10.0]
    monkeypatch.setattr("coga.launch.time.monotonic", lambda: now[0])
    probe = launch_module._terminal_status_probe(cfg, ref, Ticket.read(ref.ticket_path))
    assert probe is not None
    assert probe() is None
    _write(outside / "ticket.md", "---\nstatus: done\n---\n")
    now[0] += 1
    assert probe() is None
    now[0] += 5
    assert probe() == "done"



def test_owner_step_assist_credits_the_agent_without_a_git_record(active_task, monkeypatch):
    from unittest.mock import patch

    created = _create_chain_task(active_task)
    ticket_path = Path(created["path"])
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter.update(status="in_progress", step="3 (review)")
    ticket.write(ticket_path)
    _allow_slack(monkeypatch)
    _allow_interactive_tty(monkeypatch)
    monkeypatch.setattr("coga.launch.shutil.which", lambda cli, **kw: f"/usr/bin/{cli}")

    def finish(cmd, env=None, check=False, cwd=None):
        assert env[ASSIST_AGENT_ENV] == "codex"
        with patch.dict(os.environ, env):
            result = CliRunner().invoke(app, ["bump", created["slug"]])
        assert result.exit_code == 0, result.output
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("coga.launch.subprocess.run", finish)
    result = CliRunner().invoke(app, ["launch", created["slug"], "--agent", "codex"])
    assert result.exit_code == 0, result.output
    assert Ticket.read(ticket_path).status == "done"
    assert "[agent:codex] task done" in _read_log(active_task)
