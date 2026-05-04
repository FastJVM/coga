from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent


RUNNER = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "skills"
    / "bootstrap"
    / "dream"
    / "tasks"
    / "retro-done-ticket"
    / "run.py"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "relay-os")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Relay Test",
            "-c",
            "user.email=relay-test@example.com",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _run_worker(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--cwd", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _seed_repo(
    root: Path,
    *,
    task_status: str = "done",
    contexts: bool = True,
) -> Path:
    relay_os = root / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"

        [assignees.nick]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "nick"\n')
    _write(
        relay_os / "tasks" / "shipped-feature" / "ticket.md",
        f"""
        ---
        title: Shipped Feature
        status: {task_status}
        mode: interactive
        owner: nick
        assignee: claude1
        {'contexts:' if contexts else ''}
        {'  - relay/principles' if contexts else ''}
        workflow:
          name: code/with-review
          steps:
            - name: implement
              skill: code/implement-and-pr
            - name: review
        ---

        ## Description

        Implemented a feature after deciding the reusable behavior belongs in
        a context rather than a hidden service.

        ## Acceptance criteria

        - Tests must cover the workflow.
        """,
    )
    _write(
        relay_os / "tasks" / "shipped-feature" / "blackboard.md",
        """
        ## Dev

        branch: codex/shipped-feature
        pr: https://github.com/example/relay/pull/12

        ## Decisions

        - Prefer markdown-first state because humans can review it.
        - Follow-up: update the implement skill if this repeats.
        """,
    )
    _write(
        relay_os / "tasks" / "shipped-feature" / "log.md",
        """
        2026-05-01 10:00 [agent:nick] advanced to step 2 (review)
        2026-05-01 11:00 [human:nick] task done
        """,
    )
    _write(
        relay_os / "tasks" / "dream-run" / "blackboard.md",
        "Dream run scratch.\n",
    )
    _write(
        relay_os / "contexts" / "relay" / "principles" / "SKILL.md",
        """
        ---
        name: relay/principles
        description: Test context.
        ---

        # Principles
        """,
    )
    _git(root, "init", "-b", "main")
    _commit_all(root, "seed relay repo")
    _git(root, "branch", "codex/shipped-feature")
    return relay_os


def test_non_done_ticket_is_noop(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path, task_status="active")
    task = relay_os / "tasks" / "shipped-feature"
    blackboard = relay_os / "tasks" / "dream-run" / "blackboard.md"

    result = _run_worker(
        tmp_path,
        "--blackboard",
        str(blackboard),
        "shipped-feature",
    )

    assert result.returncode == 0, result.stderr
    assert task.is_dir()
    text = blackboard.read_text()
    assert "## Dream Worker: retro-done-ticket" in text
    assert "Result: no-op. Target status is `active`, not `done`." in text
    assert "Files changed: none." in text


def test_done_ticket_appends_context_report_and_leaves_task_and_branch(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "shipped-feature"
    blackboard = relay_os / "tasks" / "dream-run" / "blackboard.md"
    context = relay_os / "contexts" / "relay" / "principles" / "SKILL.md"
    head = _git(tmp_path, "rev-parse", "--short=12", "HEAD").stdout.strip()

    result = _run_worker(
        tmp_path,
        "--blackboard",
        str(blackboard),
        "shipped-feature",
    )

    assert result.returncode == 0, result.stderr
    assert task.is_dir()
    assert _git(tmp_path, "branch", "--list", "codex/shipped-feature").stdout
    text = blackboard.read_text()
    assert "Result: extracted 1 artifact(s)." in text
    assert f"Source ref: `{head}:relay-os/tasks/shipped-feature/`" in text
    assert "#### relay-os/contexts/relay/principles/SKILL.md" in text
    assert "Kind: context" in text
    assert "State: written" in text
    assert "### Explicitly Not Done" in text
    assert "The source ticket directory is not deleted by this skill." in text
    assert "Task branch cleanup belongs to separate Dream branch-cleanup skills." in text
    context_text = context.read_text()
    assert "<!-- relay-retro:shipped-feature -->" in context_text
    assert "## Retro: Shipped Feature" in context_text
    assert f"Source: `{head}:relay-os/tasks/shipped-feature/`." in context_text
    assert "- Prefer markdown-first state because humans can review it. (`blackboard.md`)" in context_text


def test_done_ticket_without_contexts_creates_retro_context(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path, contexts=False)
    task = relay_os / "tasks" / "shipped-feature"
    blackboard = relay_os / "tasks" / "dream-run" / "blackboard.md"
    context = relay_os / "contexts" / "retro" / "shipped-feature" / "SKILL.md"

    result = _run_worker(
        tmp_path,
        "--blackboard",
        str(blackboard),
        "shipped-feature",
    )

    assert result.returncode == 0, result.stderr
    assert task.is_dir()
    assert context.is_file()
    assert "name: retro/shipped-feature" in context.read_text()
    text = blackboard.read_text()
    assert "#### relay-os/contexts/retro/shipped-feature/SKILL.md" in text
    assert "State: written" in text


def test_retro_extraction_is_idempotent(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    context = relay_os / "contexts" / "relay" / "principles" / "SKILL.md"

    first = _run_worker(tmp_path, "shipped-feature")
    second = _run_worker(tmp_path, "shipped-feature")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert context.read_text().count("relay-retro:shipped-feature") == 1
    assert "State: already present" in second.stdout


def test_create_pr_requires_commit_and_push(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    result = _run_worker(tmp_path, "--create-pr", "shipped-feature")

    assert result.returncode == 2
    assert "--create-pr requires --commit-and-push" in result.stderr


def test_commit_and_push_refuses_main(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "shipped-feature"

    result = _run_worker(tmp_path, "--commit-and-push", "shipped-feature")

    assert result.returncode == 2
    assert task.is_dir()
    assert "refusing to push retro extraction directly from main" in result.stderr


def test_commit_and_push_publishes_extraction_branch(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    blackboard = relay_os / "tasks" / "dream-run" / "blackboard.md"
    remote = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "remote", "add", "origin", str(remote))
    _git(tmp_path, "checkout", "-b", "dream/retro-shipped-feature")
    _git(tmp_path, "config", "user.name", "Relay Test")
    _git(tmp_path, "config", "user.email", "relay-test@example.com")

    result = _run_worker(
        tmp_path,
        "--blackboard",
        str(blackboard),
        "--commit-and-push",
        "shipped-feature",
    )

    assert result.returncode == 0, result.stderr
    assert "## Dream Worker: retro-done-ticket" in blackboard.read_text()
    refs = _git(remote, "for-each-ref", "--format=%(refname)", "refs/heads").stdout
    assert "refs/heads/dream/retro-shipped-feature" in refs


def test_requires_exact_task_slug(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "shipped-feature"

    result = _run_worker(tmp_path, "shipped")

    assert result.returncode == 2
    assert task.is_dir()
    assert "requires an exact task slug" in result.stderr
