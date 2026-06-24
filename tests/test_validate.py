from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

import requests

from relay.create import create_task
from relay.config import load_config
from relay.tasks import list_tasks
from relay.ticket import Ticket
from relay.validate import apply_safe_fixes, probe_slack, run


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path):
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _write(company / "contexts" / "email" / "payment-flow" / "SKILL.md", "---\nname: x\n---\n")
    _write(company / "skills" / "infra" / "tests" / "SKILL.md", "---\nname: x\n---\n")
    _write(
        company / "workflows" / "code" / "with-review.md",
        """
        ---
        name: code/with-review
        description: Standard code workflow.
        steps:
          - name: implement
          - name: pr
        ---
        """,
    )
    return company


def test_clean_repo_has_no_issues(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name="code/with-review",
        contexts=["email/payment-flow"], autonomy="interactive",
        owner="marc", assignee="claude", watchers=[], status="draft",
    )
    report = run(cfg)
    assert report.issues == []
    assert report.ok_count == 1


def test_broken_skill_ref(repo: Path) -> None:
    cfg = load_config(repo)
    # Directly write a ticket with a bogus skill reference in its frozen workflow.
    task_dir = repo / "tasks" / "001-x"
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent("""
        ---
        slug: 001-x
        title: X
        status: active
        autonomy: interactive
        assignee: claude
        owner: marc
        workflow:
          name: x
          steps:
            - name: a
              skills:
                - does/not/exist
        step: 1 (a)
        ---

        ## Description
    """).lstrip())
    (task_dir / "blackboard.md").write_text("# Blackboard\n")
    (task_dir / "log.md").write_text("")
    report = run(cfg)
    assert any(i.kind == "broken-skill" for i in report.issues)


def test_unfrozen_workflow_string_does_not_crash(repo: Path) -> None:
    """Hand-authored tickets carrying `workflow: <name>` (a string ref) used
    to crash the validator at `wf.get("steps", [])`. Regression: surface
    them as a warning instead."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["workflow"] = "code/with-review"
    t.write(ref.path / "ticket.md")
    report = run(cfg)
    kinds = [i.kind for i in report.issues]
    assert "unfrozen-workflow" in kinds


def test_invalid_status(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["status"] = "bogus"
    t.write(ref.path / "ticket.md")
    report = run(cfg)
    assert any(i.kind == "invalid-status" for i in report.issues)


def _draft_with_secrets(repo: Path, cfg, secrets_value) -> None:
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["secrets"] = secrets_value
    t.write(ref.path / "ticket.md")


def test_secrets_null_is_valid(repo: Path) -> None:
    cfg = load_config(repo)
    _draft_with_secrets(repo, cfg, None)
    report = run(cfg)
    assert not [i for i in report.issues if "secret" in i.kind]


def test_secrets_non_list_is_error(repo: Path) -> None:
    cfg = load_config(repo)
    _draft_with_secrets(repo, cfg, "stripe_key")
    report = run(cfg)
    bad = [i for i in report.issues if i.kind == "bad-shape" and "secrets" in i.message]
    assert bad and bad[0].severity == "error"


def test_secrets_undeclared_key_warns(repo: Path) -> None:
    cfg = load_config(repo)
    _draft_with_secrets(repo, cfg, ["nope"])
    report = run(cfg)
    issues = [i for i in report.issues if i.kind == "undeclared-secret"]
    assert issues and issues[0].severity == "warn"


def test_secrets_unset_env_warns(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"
        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"
        """,
    )
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(repo)
    _draft_with_secrets(repo, cfg, ["stripe_key"])
    report = run(cfg)
    issues = [i for i in report.issues if i.kind == "unset-secret-env"]
    assert issues and issues[0].severity == "warn"
    assert "STRIPE_SECRET_KEY" in issues[0].message


def test_secrets_declared_and_set_is_clean(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"
        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"
        """,
    )
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    cfg = load_config(repo)
    _draft_with_secrets(repo, cfg, ["stripe_key"])
    report = run(cfg)
    assert not [i for i in report.issues if "secret" in i.kind]


def test_missing_blackboard_fence_is_error(repo: Path) -> None:
    # Single-file format: ticket.md is the only required per-task file, and it
    # must carry exactly one blackboard fence (the body/blackboard split). A
    # fence-less ticket.md — the structural-integrity failure that replaces the
    # old missing-blackboard.md check — is a `blackboard-fence` error.
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    ticket_path = ref.path / "ticket.md"
    ticket_path.write_text(
        ticket_path.read_text().replace("<!-- relay:blackboard -->\n", "")
    )
    report = run(cfg)
    assert any(
        i.kind == "blackboard-fence" and i.severity == "error"
        for i in report.issues
    )


def test_apply_safe_fixes_adds_missing_blackboard_fence(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    # Single-file format: strip the blackboard fence so the ticket.md is
    # fence-less; the safe fix re-appends a fence + rendered region.
    ticket_path = ref.path / "ticket.md"
    ticket_path.write_text(
        ticket_path.read_text().replace("<!-- relay:blackboard -->\n", "")
    )

    fixes = apply_safe_fixes(cfg)

    assert [fix.message for fix in fixes] == ["added blackboard fence + region"]
    assert all(fix.kind == "blackboard-fence" for fix in fixes)
    from relay.taskfile import fence_count
    assert fence_count(ticket_path.read_text()) == 1


def test_run_fix_repairs_before_reporting(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    # Single-file format: strip the fence so the ticket.md is fence-less; the
    # fix pass re-adds it before the issue scan runs.
    ticket_path = ref.path / "ticket.md"
    ticket_path.write_text(
        ticket_path.read_text().replace("<!-- relay:blackboard -->\n", "")
    )

    report = run(cfg, fix=True)

    assert len(report.fixes) == 1
    assert report.fixes[0].message == "added blackboard fence + region"
    assert not any(i.kind == "blackboard-fence" for i in report.issues)


def test_large_blackboard_warns(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    # Single-file format: the measured blackboard is the region below the fence
    # in ticket.md, not a sibling blackboard.md. The region content starts on its
    # own line after the fence (as every real blackboard writer leaves it).
    from relay.taskfile import replace_blackboard
    replace_blackboard(ref.path / "ticket.md", "\n\n" + "x" * 2048 + "\n")

    report = run(cfg, max_blackboard_bytes=1024)
    issue = next(i for i in report.issues if i.kind == "large-blackboard")
    assert issue.severity == "warn"
    assert "included in launch prompts" in issue.message


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def _fake_post_factory(response: _FakeResponse | Exception):
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(response, Exception):
            raise response
        return response

    return fake_post


def test_probe_slack_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(_FakeResponse(400, "no_text")),
    )
    status, detail = probe_slack("https://hooks.slack.com/services/x")
    assert status == "live"
    assert "400" in detail


def test_probe_slack_revoked_by_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(_FakeResponse(404, "no_service")),
    )
    status, _ = probe_slack("https://hooks.slack.com/services/x")
    assert status == "revoked"


def test_probe_slack_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(requests.ConnectionError("dns fail")),
    )
    status, detail = probe_slack("https://hooks.slack.com/services/x")
    assert status == "unreachable"
    assert "ConnectionError" in detail


def test_run_check_slack_emits_issue_for_revoked(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Add slack webhook to the repo's config.
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[slack]\nwebhook = "https://hooks.slack.com/services/dead"\n'
    )
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(_FakeResponse(404, "no_service")),
    )
    cfg = load_config(repo)
    report = run(cfg, check_slack=True)
    kinds = [i.kind for i in report.issues]
    assert "slack-revoked" in kinds


def test_run_check_slack_misconfigured_when_selected_without_webhook(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selecting Slack but leaving the webhook unset still fails loud."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[notification]\nchannels = ["slack"]\n'
        '[notification.slack]\nwebhook = "env:SLACK_WEBHOOK_URL"\n'
    )
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("must not probe the network with no webhook")

    monkeypatch.setattr("relay.validate.requests.post", boom)
    cfg = load_config(repo)
    report = run(cfg, check_slack=True)
    misconfigured = [i for i in report.issues if i.kind == "slack-misconfigured"]
    assert misconfigured
    assert misconfigured[0].severity == "error"


def test_run_no_slack_check_by_default(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[slack]\nwebhook = "https://hooks.slack.com/services/dead"\n'
    )

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("network must not be called when --check-slack is off")

    monkeypatch.setattr("relay.validate.requests.post", boom)
    cfg = load_config(repo)
    run(cfg)  # must not raise


# --- github preflight (--check-github) --------------------------------------


class _FakeProc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_subprocess_factory(responses: dict[tuple[str, ...], object]):
    """Dispatch `subprocess.run` by matching the start of its argv.

    A value may be a `_FakeProc` (returned) or an `Exception` (raised, e.g.
    `FileNotFoundError` to model a missing binary). An argv that matches no key
    fails the test — that proves probes we expect to be *skipped* are not run.
    """

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        for key, resp in responses.items():
            if tuple(args[: len(key)]) == key:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"unexpected subprocess call: {args}")

    return fake_run


def _github_kinds(report) -> list[str]:
    return [i.kind for i in report.issues if i.task == "(github)"]


def test_check_github_success(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.github_preflight.subprocess.run",
        _fake_subprocess_factory(
            {
                ("git", "remote", "get-url", "origin"): _FakeProc(
                    0, "git@github.com:o/r.git\n"
                ),
                ("git", "push", "--dry-run", "origin"): _FakeProc(0),
                ("gh", "--version"): _FakeProc(0, "gh version 2.90.0\n"),
                ("gh", "auth", "status", "--hostname", "github.com"): _FakeProc(
                    0, "", "Logged in to github.com"
                ),
            }
        ),
    )
    cfg = load_config(repo)
    report = run(cfg, check_github=True)
    assert _github_kinds(report) == []


def test_check_github_missing_remote(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No push entry: a missing remote must short-circuit before the auth probe
    # runs (the factory raises on any unexpected call).
    monkeypatch.setattr(
        "relay.github_preflight.subprocess.run",
        _fake_subprocess_factory(
            {
                ("git", "remote", "get-url", "origin"): _FakeProc(
                    2, "", "error: No such remote 'origin'"
                ),
                ("gh", "--version"): _FakeProc(0, "gh version 2.90.0\n"),
                ("gh", "auth", "status"): _FakeProc(0, "", "Logged in"),
            }
        ),
    )
    cfg = load_config(repo)
    report = run(cfg, check_github=True)
    kinds = _github_kinds(report)
    assert "github-git-remote" in kinds
    assert "github-git-auth" not in kinds


def test_check_github_missing_gh(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `gh` absent (FileNotFoundError): gh-auth must be skipped.
    monkeypatch.setattr(
        "relay.github_preflight.subprocess.run",
        _fake_subprocess_factory(
            {
                ("git", "remote", "get-url", "origin"): _FakeProc(
                    0, "git@github.com:o/r.git\n"
                ),
                ("git", "push", "--dry-run", "origin"): _FakeProc(0),
                ("gh", "--version"): FileNotFoundError(),
            }
        ),
    )
    cfg = load_config(repo)
    report = run(cfg, check_github=True)
    kinds = _github_kinds(report)
    assert "github-gh-installed" in kinds
    assert "github-gh-auth" not in kinds


def test_check_github_gh_unauthenticated(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "relay.github_preflight.subprocess.run",
        _fake_subprocess_factory(
            {
                ("git", "remote", "get-url", "origin"): _FakeProc(
                    0, "git@ghe.example.com:o/r.git\n"
                ),
                ("git", "push", "--dry-run", "origin"): _FakeProc(0),
                ("gh", "--version"): _FakeProc(0, "gh version 2.90.0\n"),
                ("gh", "auth", "status", "--hostname", "ghe.example.com"): _FakeProc(
                    1, "", "not logged in to ghe.example.com"
                ),
            }
        ),
    )
    cfg = load_config(repo)
    report = run(cfg, check_github=True)
    kinds = _github_kinds(report)
    assert "github-gh-auth" in kinds
    auth_issue = next(i for i in report.issues if i.kind == "github-gh-auth")
    assert "gh auth login --hostname ghe.example.com" in auth_issue.message
    assert auth_issue.severity == "error"


def test_check_github_push_auth_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "relay.github_preflight.subprocess.run",
        _fake_subprocess_factory(
            {
                ("git", "remote", "get-url", "origin"): _FakeProc(
                    0, "https://github.com/o/r.git\n"
                ),
                ("git", "push", "--dry-run", "origin"): _FakeProc(
                    128, "", "remote: Permission to o/r.git denied"
                ),
                ("gh", "--version"): _FakeProc(0, "gh version 2.90.0\n"),
                ("gh", "auth", "status", "--hostname", "github.com"): _FakeProc(
                    0, "", "Logged in to github.com"
                ),
            }
        ),
    )
    cfg = load_config(repo)
    report = run(cfg, check_github=True)
    kinds = _github_kinds(report)
    assert "github-git-auth" in kinds
    auth_issue = next(i for i in report.issues if i.kind == "github-git-auth")
    assert "push access" in auth_issue.message


def test_run_no_github_check_by_default(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("git/gh must not run when --check-github is off")

    monkeypatch.setattr("relay.github_preflight.subprocess.run", boom)
    cfg = load_config(repo)
    run(cfg)  # must not raise


# --- ticket frontmatter extensions ------------------------------------------


def test_validate_accepts_declared_extension_fields(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "d"\n'
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name="code/with-review",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    report = run(cfg)
    assert report.issues == []


def test_validate_flags_missing_declared_extension(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    # Add the declaration AFTER the ticket exists — simulates declaring a new
    # extension once tickets are already on disk.
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "d"\n'
    )
    cfg = load_config(repo)
    report = run(cfg)
    kinds = [(i.kind, i.severity) for i in report.issues]
    assert ("missing-extension", "error") in kinds


def test_validate_warns_orphan_extension(repo: Path) -> None:
    """A field present on disk but not declared in TOML → warn, not error."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "d"\n'
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    # Now remove the declaration.
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text().replace(
            '\n[ticket.fields.docket]\ndescription = "d"\n', ""
        )
    )
    cfg = load_config(repo)
    report = run(cfg)
    orphans = [i for i in report.issues if i.kind == "orphan-extension"]
    assert orphans, [i.kind for i in report.issues]
    assert all(i.severity == "warn" for i in orphans)


def test_validate_flags_enum_violation(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "p"\n'
            'values = ["P0", "P1", "P2"]\n'
            'default = "P2"\n'
        )
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["priority"] = "P9"
    t.write(ref.path / "ticket.md")
    report = run(cfg)
    assert any(
        i.kind == "bad-extension-value" and i.severity == "error"
        for i in report.issues
    ), [(i.kind, i.severity) for i in report.issues]


def test_validate_allows_empty_extension_value(repo: Path) -> None:
    """Empty extension values are fine at validate time — they only block
    `mark active` when the field is `required = true`."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "p"\n'
            'values = ["P0", "P1"]\n'
            "required = true\n"
        )
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name="code/with-review",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    report = run(cfg)
    assert report.issues == []


def test_workflow_less_draft_is_clean(repo: Path) -> None:
    """A `draft` with `workflow: null` is valid (concept-capture: stash the
    idea before its shape settles). It is NOT flagged — `draft` is the one
    status where a workflow is optional."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="draft",
    )
    report = run(cfg)
    kinds = [i.kind for i in report.issues]
    assert "missing-workflow" not in kinds
    assert "active-no-workflow" not in kinds


def _write_workflow_less_task(repo: Path, slug: str, status: str) -> Path:
    """Write a workflow-less task directly to disk. `create_task` refuses to
    create a workflow-less non-draft task now, so on-disk construction is the
    only way to exercise the validator against that (invalid) shape."""
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        slug: {slug}
        title: X
        status: {status}
        autonomy: interactive
        owner: marc
        assignee: claude
        workflow: null
        ---

        ## Description

        <!-- relay:blackboard -->

        # Blackboard
    """).lstrip())
    return task_dir


@pytest.mark.parametrize("status", ["active", "in_progress", "paused"])
def test_workflow_less_non_draft_is_error(repo: Path, status: str) -> None:
    """A workflow-less `active`/`in_progress`/`paused` ticket can never be
    bumped — it is structurally stuck. The validator flags it as an error."""
    cfg = load_config(repo)
    _write_workflow_less_task(repo, "stuck-x", status)
    report = run(cfg)
    stuck = [i for i in report.issues if i.kind == "active-no-workflow"]
    assert stuck, [i.kind for i in report.issues]
    assert all(i.severity == "error" for i in stuck)


def test_workflow_less_done_is_not_flagged(repo: Path) -> None:
    """A `done` workflow-less task is finished and immutable — flagging it
    would only nag history. It is left alone."""
    cfg = load_config(repo)
    _write_workflow_less_task(repo, "finished-x", "done")
    report = run(cfg)
    assert "active-no-workflow" not in [i.kind for i in report.issues]


def test_stuck_in_progress_flagged(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="X", workflow_name="code/with-review",
        contexts=[], autonomy="interactive", owner="marc", assignee="claude",
        watchers=[], status="in_progress",
    )
    ref = list_tasks(cfg)[0]
    # Single-file format: idle time derives from the task's most recent line in
    # the repo-global log (tagged by ref), not a per-task log.md mtime. Seed a
    # backdated activity line 100 hours ago.
    from datetime import datetime, timedelta
    from relay.paths import log_path
    stamp = (datetime.now() - timedelta(hours=100)).strftime("%Y-%m-%d %H:%M")
    log = log_path(cfg)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"{stamp} [{ref.id_slug}] [agent:claude] picked up\n")
    report = run(cfg, idle_hours=72.0)
    assert any(i.kind == "stuck-in-progress" for i in report.issues)


def _write_full_task(repo: Path, rel: str, title: str = "X") -> Path:
    """A complete, schema-clean task dir at `tasks/<rel>` (rel may be nested)."""
    task_dir = repo / "tasks" / rel
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        slug: {rel}
        title: {title}
        status: draft
        autonomy: interactive
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        ---

        ## Description

        <!-- relay:blackboard -->

        # Blackboard
    """).lstrip())
    return task_dir


def test_nested_task_validates_clean(repo: Path) -> None:
    cfg = load_config(repo)
    _write_full_task(repo, "auto/digest-sweep", title="Digest sweep")
    report = run(cfg)
    assert [i for i in report.issues if i.severity == "error"] == []
    assert report.ok_count == 1


def test_same_leaf_name_in_different_directories_validates_clean(repo: Path) -> None:
    # A leaf name reused across two directories is no longer a collision — the
    # path under `tasks/` disambiguates, so validate reports no duplicate.
    cfg = load_config(repo)
    _write_full_task(repo, "marketing/dup-task")
    _write_full_task(repo, "eng/dup-task")
    report = run(cfg)
    assert "duplicate-slug" not in [i.kind for i in report.issues]
