from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent


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

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--blackboard",
            str(blackboard),
            "--apply",
            "shipped-feature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert task.is_dir()
    text = blackboard.read_text()
    assert "## Dream Worker: retro-done-ticket" in text
    assert "Result: no-op. Target status is `active`, not `done`." in text
    assert "Files changed: none." in text
    assert _git(tmp_path, "branch", "--list", "codex/shipped-feature").stdout


def test_non_done_ticket_with_commit_and_push_is_still_noop(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path, task_status="active")
    task = relay_os / "tasks" / "shipped-feature"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--apply",
            "--commit-and-push",
            "shipped-feature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert task.is_dir()
    assert "Result: no-op. Target status is `active`, not `done`." in result.stdout


def test_done_ticket_apply_appends_report_and_deletes_task(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "shipped-feature"
    blackboard = relay_os / "tasks" / "dream-run" / "blackboard.md"
    context = relay_os / "contexts" / "relay" / "principles" / "SKILL.md"
    head = _git(tmp_path, "rev-parse", "--short=12", "HEAD").stdout.strip()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--blackboard",
            str(blackboard),
            "--apply",
            "shipped-feature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not task.exists()
    text = blackboard.read_text()
    assert "Result: deleted `relay-os/tasks/shipped-feature/`." in text
    assert f"Source ref: `{head}:relay-os/tasks/shipped-feature/`" in text
    assert "### Context Blocks" in text
    assert "#### relay-os/contexts/relay/principles/SKILL.md" in text
    assert "State: written" in text
    assert "### Branch Cleanup" in text
    assert "deleted local `codex/shipped-feature`" in text
    assert "### Evidence Read" in text
    assert "blackboard.md: Prefer markdown-first state" in text
    assert "### Intentionally Dropped" in text
    assert "### PR Body Snippet" in text
    assert "The deletion diff in this PR also contains the removed task files." in text
    context_text = context.read_text()
    assert "## Retro: Shipped Feature" in context_text
    assert f"Source: `{head}:relay-os/tasks/shipped-feature/`." in context_text
    assert "- Prefer markdown-first state because humans can review it. (`blackboard.md`)" in context_text
    assert not _git(tmp_path, "branch", "--list", "codex/shipped-feature").stdout


def test_done_ticket_without_contexts_renders_draft_context_block(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path, contexts=False)
    task = relay_os / "tasks" / "shipped-feature"
    blackboard = relay_os / "tasks" / "dream-run" / "blackboard.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--blackboard",
            str(blackboard),
            "--apply",
            "shipped-feature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not task.exists()
    text = blackboard.read_text()
    assert "#### relay-os/contexts/<review-needed>/shipped-feature/SKILL.md" in text
    assert "State: draft" in text
    assert "## Retro: Shipped Feature" in text


def test_delete_remote_branch_deletes_merged_origin_branch(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    remote = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "remote", "add", "origin", str(remote))
    _git(tmp_path, "push", "-u", "origin", "main")
    _git(tmp_path, "push", "origin", "codex/shipped-feature")
    _git(tmp_path, "fetch", "origin")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--apply",
            "--delete-remote-branch",
            "shipped-feature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "deleted local `codex/shipped-feature`" in result.stdout
    assert "deleted remote `origin/codex/shipped-feature`" in result.stdout
    refs = _git(remote, "for-each-ref", "--format=%(refname)", "refs/heads").stdout
    assert "refs/heads/codex/shipped-feature" not in refs


def test_apply_requires_exact_task_slug(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "shipped-feature"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--apply",
            "shipped",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert task.is_dir()
    assert "requires an exact task slug" in result.stderr


def test_apply_refuses_dirty_task_directory(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "shipped-feature"
    (task / "blackboard.md").write_text("uncommitted lesson\n")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--apply",
            "shipped-feature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert task.is_dir()
    assert "refusing to delete `relay-os/tasks/shipped-feature`" in result.stderr
    assert "uncommitted changes" in result.stderr


def test_commit_and_push_refuses_main_before_deleting(tmp_path: Path) -> None:
    relay_os = _seed_repo(tmp_path)
    task = relay_os / "tasks" / "shipped-feature"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "relay.dream_retro_done_ticket",
            "--cwd",
            str(tmp_path),
            "--apply",
            "--commit-and-push",
            "shipped-feature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert task.is_dir()
    assert "refusing to push retro cleanup directly from main" in result.stderr
