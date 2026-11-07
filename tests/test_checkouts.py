"""Shared checkout preparation: policy, ticket launch, and direct chat."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import append_test_usage as _usage_record

from coga import checkouts
from coga import git as coga_git
from coga import launch as launch_module
from coga.checkout_policy import select_checkout_policy
from coga.cli import app
from coga.compose import CheckoutNotice, compose_prompt_report
from coga.config import load_config
from coga.create import create_task
from coga.paths import bootstrap_skill_path, bootstrap_workflow_path
from coga.repl_supervisor import ReplOutcome
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import Ticket
from coga.workflow import Workflow


# --- policy -------------------------------------------------------------------


def _frozen(workflow: str, step: str, *, skills=None, drop=()) -> Ticket:  # type: ignore[no-untyped-def]
    frozen = Workflow.load(bootstrap_workflow_path(None, workflow)).freeze()  # type: ignore[arg-type]
    frozen["steps"] = [s for s in frozen["steps"] if s["name"] not in drop]
    for entry in frozen["steps"]:
        entry.pop("requires", None) if drop else None
    names = [s["name"] for s in frozen["steps"]]
    index = names.index(step)
    if skills is not None:
        frozen["steps"][index]["skills"] = list(skills)
    return Ticket(
        frontmatter={
            "title": "t", "status": "in_progress", "owner": "marc",
            "workflow": frozen, "step": f"{index + 1} ({step})",
        },
        body="\n<!-- coga:blackboard -->\n",
    )


SHIPPED_ROWS = [
    ("code/design-then-implement", "design", "control"),
    ("code/design-then-implement", "evaluate-design", "control"),
    ("code/design-then-implement", "review-design", "control"),
    ("code/design-then-implement", "implement", "create-or-reuse"),
    ("code/design-then-implement", "peer-review", "reuse-required"),
    ("code/design-then-implement", "open-pr", "control"),
    ("code/design-then-implement", "review", "reuse-required"),
    ("code/with-review", "implement", "create-or-reuse"),
    ("code/with-review", "peer-review", "reuse-required"),
    ("code/with-review", "open-pr", "control"),
    ("code/with-review", "review", "reuse-required"),
    ("code/with-self-review", "implement", "create-or-reuse"),
    ("code/with-self-review", "self-qa", "reuse-required"),
    ("code/with-self-review", "pr", "control"),
    ("code/with-self-review", "review", "reuse-required"),
    ("docs/with-review", "implement", "create-or-reuse"),
    ("docs/with-review", "peer-review", "reuse-required"),
    ("docs/with-review", "open-pr", "control"),
    ("docs/with-review", "review", "reuse-required"),
]


@pytest.mark.parametrize(("workflow", "step", "kind"), SHIPPED_ROWS)
def test_policy_maps_every_shipped_step(git_repo, workflow, step, kind) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    assert select_checkout_policy(cfg, _frozen(workflow, step)).kind == kind


def test_policy_supports_older_frozen_snapshots(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    old = _frozen("code/design-then-implement", "implement", drop=("evaluate-design",))
    assert old.current_step() is not None
    assert "requires" not in old.current_step()
    assert select_checkout_policy(cfg, old).kind == "create-or-reuse"
    legacy_review = _frozen("code/with-review", "review", skills=[])
    assert select_checkout_policy(cfg, legacy_review).kind == "reuse-required"
    legacy_peer = _frozen("code/with-review", "peer-review", skills=[])
    assert select_checkout_policy(cfg, legacy_peer).kind == "reuse-required"


@pytest.mark.parametrize(
    "skills",
    [["code/implement", "infra/extra"], ["code/self-qa"], []],
)
def test_policy_refuses_contradictory_step_skills(git_repo, skills) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    policy = select_checkout_policy(
        cfg, _frozen("code/with-review", "implement", skills=skills)
    )
    assert policy.kind == "manual"
    assert "not the shipped ones" in policy.reason


def test_policy_names_custom_workflows_manual(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    ref = _task(git_repo, "code")
    policy = select_checkout_policy(cfg, read_ticket(ref))
    assert policy.kind == "manual"
    assert "not a shipped step" in policy.reason


def test_policy_accepts_identical_local_twins_and_refuses_changed_ones(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    ticket = _frozen("code/with-review", "implement")
    local = git_repo.coga_os / "skills" / "code" / "implement" / "SKILL.md"
    local.parent.mkdir(parents=True)
    shipped = (
        Path(coga_git.__file__).parent
        / "resources/templates/coga/bootstrap/skills/code/implement/SKILL.md"
    )
    local.write_bytes(shipped.read_bytes())
    assert select_checkout_policy(cfg, ticket).kind == "create-or-reuse"
    local.write_text(shipped.read_text(encoding="utf-8") + "\nLocal tweak.\n", encoding="utf-8", newline="\n")
    policy = select_checkout_policy(cfg, ticket)
    assert policy.kind == "manual"
    assert "differs from the shipped copy" in policy.reason


@pytest.mark.parametrize(
    ("workflow", "legacy"),
    [
        ("code/with-review", False),
        ("code/with-review", True),
        ("code/design-then-implement", False),
    ],
)
def test_policy_checks_peer_review_skill_for_current_and_legacy_steps(
    git_repo, workflow: str, legacy: bool,
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    ticket = _frozen(workflow, "peer-review", skills=[] if legacy else None)
    local = git_repo.coga_os / "skills" / "code" / "peer-review" / "SKILL.md"
    local.parent.mkdir(parents=True)
    shipped = bootstrap_skill_path(cfg, "code/peer-review").read_text(encoding="utf-8")
    local.write_text(shipped, encoding="utf-8", newline="\n")
    assert select_checkout_policy(cfg, ticket).kind == "reuse-required"

    # The legacy inline section delegates to this skill too: custom review
    # instructions must select manual checkout preparation in either shape.
    local.write_text(shipped + "\nUse a custom checkout.\n", encoding="utf-8", newline="\n")
    policy = select_checkout_policy(cfg, ticket)
    assert policy.kind == "manual"
    assert "code/peer-review" in policy.reason
    assert "differs from the shipped copy" in policy.reason


def test_policy_reads_only_the_consumed_inline_section(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    shipped = bootstrap_workflow_path(cfg, "code/with-review").read_text(encoding="utf-8")
    local = git_repo.coga_os / "workflows" / "code" / "with-review.md"
    local.parent.mkdir(parents=True)
    local.write_text(shipped.replace("## open-pr\n", "## open-pr\n\nLocal framing.\n"), encoding="utf-8", newline="\n")
    peer = _frozen("code/with-review", "peer-review")
    assert select_checkout_policy(cfg, peer).kind == "reuse-required"
    local.write_text(shipped.replace("## peer-review\n", "## peer-review\n\nChanged.\n"), encoding="utf-8", newline="\n")
    # The current shape consumes `code/peer-review`, so the section is framing;
    # an older skill-less snapshot still consumes it.
    assert select_checkout_policy(cfg, peer).kind == "reuse-required"
    policy = select_checkout_policy(cfg, _frozen("code/with-review", "peer-review", skills=[]))
    assert policy.kind == "manual"
    assert "`## peer-review` section differs" in policy.reason


# --- linkage text ---------------------------------------------------------------


def test_insert_branch_line_creates_or_extends_the_live_dev_section() -> None:
    assert checkouts.insert_branch_line("\n## Notes\n\nx\n", "b") == (
        "\n## Dev\n\nbranch: b\n\n## Notes\n\nx\n"
    )
    assert checkouts.insert_branch_line(
        "\n## Dev\n\npr: https://example.test/pull/1\n", "b"
    ) == "\n## Dev\n\nbranch: b\npr: https://example.test/pull/1\n"
    fenced = "\n```\n## Dev\nbranch: example\n```\n"
    assert checkouts.insert_branch_line(fenced, "b").startswith("\n## Dev\n\nbranch: b\n")


# --- strict provenance ----------------------------------------------------------


def test_projected_baseline_is_strict_and_preserves_other_entries(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    root = git_repo.root
    log_oid = git_repo.git("rev-parse", "HEAD:coga/coga.toml").strip()
    coga_git._record_published(root, {"coga/coga.toml": log_oid})
    oid = git_repo.git("rev-parse", "HEAD:coga/workflows/code.md").strip()
    coga_git.record_projected_baseline(cfg, root, "coga/workflows/code.md", oid)
    published = coga_git.PUBLISHED_REF
    assert git_repo.git("rev-parse", f"{published}:coga/coga.toml").strip() == log_oid
    assert git_repo.git("rev-parse", f"{published}:coga/workflows/code.md").strip() == oid
    with pytest.raises(coga_git.GitError):
        coga_git.record_projected_baseline(cfg, root, "coga/x.md", "0" * 40)


# --- ticket launch --------------------------------------------------------------


def _task(git_repo, workflow: str, title: str = "Checkout prep") -> TaskRef:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg, title=title, workflow_name=workflow, contexts=[],
        owner="marc", agent="claude", status="active",
    )
    coga_git.sync_task_state(cfg, Path(created["path"]), message="Seed task")
    return next(ref for ref in list_tasks(cfg) if ref.id_slug == created["slug"])


def _rel(git_repo, ref: TaskRef) -> str:  # type: ignore[no-untyped-def]
    return ref.ticket_path.relative_to(git_repo.root).as_posix()


def _control(git_repo, rel: str) -> str:  # type: ignore[no-untyped-def]
    return git_repo.git("show", f"main:{rel}", cwd=git_repo.origin)


def _head(git_repo) -> str:  # type: ignore[no-untyped-def]
    return git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip()


def _dirty(git_repo) -> list[str]:  # type: ignore[no-untyped-def]
    out = git_repo.git("status", "--porcelain", "--untracked-files=all")
    return [line[3:] for line in out.splitlines()]


def _bump(git_repo, slug: str, *, subprocess_run: bool = False) -> None:  # type: ignore[no-untyped-def]
    if subprocess_run:
        env = {k: v for k, v in os.environ.items() if not k.startswith("COGA_")}
        env["PYTHONPATH"] = str(Path(checkouts.__file__).resolve().parents[1])
        result = subprocess.run(
            [sys.executable, "-m", "coga.cli", "bump", slug],
            cwd=git_repo.coga_os, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return
    prev = os.getcwd()
    os.chdir(git_repo.coga_os)
    try:
        result = CliRunner().invoke(app, ["bump", slug])
    finally:
        os.chdir(prev)
    assert result.exit_code == 0, result.output


class _Agent:
    """Replaces only the agent process: real spawn, composition and audit."""

    def __init__(self, git_repo, actions) -> None:  # type: ignore[no-untyped-def]
        self.git_repo = git_repo
        self.actions = list(actions)
        self.seen: list[dict] = []

    def __call__(self, cmd, env, **_kwargs):  # type: ignore[no-untyped-def]
        index = len(self.seen)
        prompt = "\n".join(cmd)
        if "will read it from" in prompt or not prompt.strip():
            prompt = ""
        record = {
            "head": _head(self.git_repo),
            "dirty": _dirty(self.git_repo),
            "prompt": prompt,
            "step": env.get("COGA_EXPECTED_STEP"),
        }
        self.seen.append(record)
        action = self.actions[index] if index < len(self.actions) else None
        if action is not None:
            action(record)
        return ReplOutcome(0, "done", done_signalled=True)


@pytest.fixture
def launch_env(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr("coga.launch.agent_sessions_supported", lambda: True)
    monkeypatch.setattr("coga.launch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.launch._preflight_push_auth", lambda *a, **k: None)
    monkeypatch.setattr(
        "coga.launch.usage_tracking.capture_session", lambda **kwargs: None
    )

    def install(agent: _Agent) -> None:
        monkeypatch.setattr("coga.launch.run_with_done_marker", agent)

    return install


def _launch(slug: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(app, ["launch", slug])


def _handoff(git_repo, ref: TaskRef, text: str) -> None:  # type: ignore[no-untyped-def]
    replace_blackboard(
        ref.ticket_path, read_blackboard(ref.ticket_path) + f"\n## Handoff\n\n{text}\n"
    )


def _startup_task(git_repo, status: str, checkout: str, *, workflow_ref: bool = False) -> TaskRef:  # type: ignore[no-untyped-def]
    """One shipped agent step followed by an owner handoff, with real publication."""
    from coga.taskfile import join_task_body
    import yaml

    workflow = "code/design-then-implement" if checkout == "control" else "code/with-self-review"
    if checkout == "control":
        with (git_repo.coga_os / "coga.local.toml").open("a", encoding="utf-8") as config:
            config.write('\n[agents.codex]\ncli = "codex"\nfile = "AGENTS.md"\n')
    ref = _task(git_repo, workflow)
    ticket = read_ticket(ref)
    steps = ticket.workflow["steps"]
    ticket.workflow["steps"] = [steps[0], steps[-1]]
    ticket.workflow["steps"][0].pop("requires", None)
    ticket.frontmatter["status"] = status
    if checkout == "reuse":
        ticket.body = join_task_body("## Description\n\nStartup test.\n", "## Dev\n\nbranch: feature/startup\n")
    if workflow_ref:
        path = git_repo.coga_os / "workflows" / f"{workflow}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump({"name": workflow, "steps": ticket.workflow["steps"]}) + "---\n", encoding="utf-8", newline="\n")
        ticket.frontmatter["workflow"] = workflow
        ticket.frontmatter.pop("step", None)
        ticket.frontmatter.pop("agent", None)
    ticket.write(ref.ticket_path)
    coga_git.sync_coga_state(load_config(git_repo.coga_os))
    if checkout == "reuse":
        git_repo.git("branch", "feature/startup")
    assert _dirty(git_repo) == []
    return ref


def _main(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    """Exercise the console entry point, including its outer sweep."""
    from coga import cli

    monkeypatch.setattr(sys, "argv", ["coga", *args])
    try:
        cli.main()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


@pytest.mark.parametrize("status", ["in_progress", "active", "draft"])
@pytest.mark.parametrize("checkout", ["control", "reuse", "create"])
def test_ordinary_launch_has_three_publications(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, status: str, checkout: str,
) -> None:  # type: ignore[no-untyped-def]
    _assert_startup_publications(git_repo, launch_env, monkeypatch, status, checkout)


@pytest.mark.parametrize("status,workflow_ref", [("draft", True), ("paused", False)])
def test_ordinary_activation_freezes_and_reactivates_in_one_publication(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, status: str, workflow_ref: bool,
) -> None:  # type: ignore[no-untyped-def]
    _assert_startup_publications(
        git_repo, launch_env, monkeypatch, status, "create", workflow_ref=workflow_ref,
    )


def _assert_startup_publications(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, status: str, checkout: str,
    *, workflow_ref: bool = False,
) -> None:  # type: ignore[no-untyped-def]
    from coga.recurring_activity import is_machine_commit

    ref = _startup_task(git_repo, status, checkout, workflow_ref=workflow_ref)
    rel = _rel(git_repo, ref)
    start = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    log_before = _control(git_repo, "coga/log.md")
    real_switch = checkouts._switch

    def switch(root, branch, stage):  # type: ignore[no-untyped-def]
        assert _dirty(git_repo) == []
        assert "launched" in _control(git_repo, "coga/log.md")[len(log_before):]
        real_switch(root, branch, stage)

    monkeypatch.setattr(checkouts, "_switch", switch)

    def handoff(seen: dict) -> None:
        startup = Ticket.parse(_control(git_repo, rel))
        assert startup.status == "in_progress"
        assert isinstance(startup.workflow, dict) and startup.agent
        assert ref.ticket_path.read_bytes() == _control(git_repo, rel).encode()
        assert '"session_id":"startup-usage"' not in _control(git_repo, "coga/log.md")
        if checkout != "control":
            assert checkouts.parse_branch_names(read_blackboard(ref.ticket_path)) == [seen["head"]]
        _handoff(git_repo, ref, "Exact handoff bytes: café → owner.")
        _bump(git_repo, ref.id_slug, subprocess_run=True)
        assert "step: 2 (review)" in _control(git_repo, rel)
        assert "Exact handoff bytes: café → owner." in _control(git_repo, rel)
        assert '"session_id":"startup-usage"' not in _control(git_repo, "coga/log.md")

    agent = _Agent(git_repo, [handoff])
    launch_env(agent)
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", _usage_record)
    assert _main(monkeypatch, "launch", ref.id_slug) == 0
    assert len(agent.seen) == 1
    commits = git_repo.git("rev-list", "--reverse", f"{start}..main", cwd=git_repo.origin).splitlines()
    subjects = [git_repo.git("show", "-s", "--format=%s", oid, cwd=git_repo.origin).strip() for oid in commits]
    branch = agent.seen[0]["head"]
    first = (
        f"Ticket: {ref.id_slug} — in_progress" if status != "in_progress"
        else f"Ticket: {ref.id_slug} — branch {branch}" if checkout == "create"
        else f"Log: {ref.id_slug}"
    )
    assert subjects == [first, f"Ticket: {ref.id_slug} — step 2 (review)", f"Log: {ref.id_slug}"]
    for index, oid in enumerate(commits):
        paths = git_repo.git("diff-tree", "--no-commit-id", "--name-only", "-r", oid, cwd=git_repo.origin).splitlines()
        expected = ["coga/log.md"] if index == 2 or (index == 0 and first.startswith("Log:")) else ["coga/log.md", rel]
        assert paths == expected
        assert is_machine_commit(subjects[index]) == subjects[index].startswith("Log:")
    startup_log = git_repo.git("show", f"{commits[0]}:coga/log.md", cwd=git_repo.origin)[len(log_before):]
    assert startup_log.count("launched") == 1
    assert startup_log.count("started (active → in_progress)") == int(status != "in_progress")
    assert startup_log.count(f"activated ({status} → active)") == int(status in {"draft", "paused"})
    if status in {"draft", "paused"}:
        assert startup_log.index("activated") < startup_log.index("started") < startup_log.index("launched")
    assert "Exact handoff bytes" not in git_repo.git("show", f"{commits[0]}:{rel}", cwd=git_repo.origin)
    assert '"session_id":"startup-usage"' not in git_repo.git("show", f"{commits[1]}:coga/log.md", cwd=git_repo.origin)
    final_log = _control(git_repo, "coga/log.md")
    assert final_log.count('"session_id":"startup-usage"') == 1
    end = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    assert _head(git_repo) == "main" and _dirty(git_repo) == []
    assert git_repo.git("rev-parse", "HEAD").strip() == end
    coga_git.sync_coga_state(load_config(git_repo.coga_os))
    assert git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip() == end


@pytest.mark.parametrize("failure", ["failed", "refused", "uncertain", "skipped", "after-push", "interrupted"])
@pytest.mark.parametrize("checkout", ["control", "create"])
def test_grouped_startup_failure_retains_evidence_and_withholds_sweep(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, capsys, failure: str, checkout: str,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "draft", checkout)
    rel = _rel(git_repo, ref)
    original = ref.ticket_path.read_bytes()
    start = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    real_publish = coga_git.publish

    def fail(cfg, paths, message, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("guard") is not None and message.endswith("— in_progress"):
            if failure == "skipped":
                return None
            if failure == "interrupted":
                raise KeyboardInterrupt()
            if failure == "after-push":
                real_publish(cfg, paths, message, **kwargs)
            error = {
                "failed": coga_git.GitError, "refused": coga_git.StateRegressionError,
                "uncertain": coga_git.UncertainPublishError, "after-push": coga_git.UncertainPublishError,
            }[failure]
            raise error("injected startup failure")
        return real_publish(cfg, paths, message, **kwargs)

    monkeypatch.setattr(coga_git, "publish", fail)
    agent = _Agent(git_repo, [])
    launch_env(agent)
    assert _main(monkeypatch, "launch", ref.id_slug) == 75
    output = capsys.readouterr()
    assert "startup publication" in output.err and "retained" in output.err
    assert agent.seen == [] and _head(git_repo) == "main"
    assert read_ticket(ref).status == "in_progress"
    assert "launched" in (git_repo.coga_os / "log.md").read_text(encoding="utf-8")
    count = int(git_repo.git("rev-list", "--count", f"{start}..main", cwd=git_repo.origin))
    assert count == int(failure == "after-push")
    if failure != "after-push":
        assert _control(git_repo, rel).encode() == original
    if checkout == "create":
        receipt = checkouts._read_receipt(load_config(git_repo.coga_os), git_repo.root, rel)
        assert receipt is not None and receipt["stage"] == "created"
        assert receipt["branch"] in git_repo.git("branch", "--list", "coga/*")
    # A later entry settles the already-recorded transition; it must not
    # reactivate or start again. No compensating transition moves control back.
    monkeypatch.setattr(coga_git, "publish", real_publish)
    assert _main(monkeypatch, "launch", ref.id_slug) == 0
    log = _control(git_repo, "coga/log.md")
    assert log.count("activated (draft → active)") == 1
    assert log.count("started (active → in_progress)") == 1
    assert _dirty(git_repo) == []


@pytest.mark.parametrize("change", ["step", "agent", "secrets", "branch", "notes"])
def test_control_only_resume_rechecks_ticket_after_log_publication(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "in_progress", "control")
    rel = _rel(git_repo, ref)
    real_publish = coga_git.publish
    raced = False

    def race(cfg, paths, message, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal raced
        result = real_publish(cfg, paths, message, **kwargs)
        if kwargs.get("guard") is not None and not raced:
            raced = True
            ticket = Ticket.parse(_control(git_repo, rel))
            if change == "step":
                ticket.frontmatter["step"] = "2 (review)"
            elif change == "agent":
                ticket.frontmatter["agent"] = "codex"
            elif change == "secrets":
                ticket.frontmatter["secrets"] = [{"NEW_SECRET": "env:NEW_SECRET"}]
            elif change == "branch":
                ticket.body += "\n## Dev\n\nbranch: feature/changed\n"
            else:
                ticket.body += "\nCompatible owner note.\n"
            git_repo.push_competing_commit(rel, ticket.render())
        return result

    monkeypatch.setattr(coga_git, "publish", race)
    agent = _Agent(git_repo, [])
    launch_env(agent)
    assert _main(monkeypatch, "launch", ref.id_slug) == (0 if change == "notes" else 75)
    assert raced
    if change == "notes":
        assert "Compatible owner note." in agent.seen[0]["prompt"]
    else:
        assert agent.seen == []
    assert _dirty(git_repo) == []


def test_log_only_startup_guards_an_unselected_ticket_during_push_retry(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "in_progress", "control")
    rel = _rel(git_repo, ref)
    real_push = coga_git._push
    raced = False

    def push(root, remote, refspec):  # type: ignore[no-untyped-def]
        nonlocal raced
        if not raced:
            raced = True
            ticket = Ticket.parse(_control(git_repo, rel))
            ticket.frontmatter["agent"] = "codex"
            git_repo.push_competing_commit(rel, ticket.render())
        return real_push(root, remote, refspec)

    monkeypatch.setattr(coga_git, "_push", push)
    agent = _Agent(git_repo, [])
    launch_env(agent)
    assert _main(monkeypatch, "launch", ref.id_slug) == 75
    assert agent.seen == [] and raced
    assert Ticket.parse(_control(git_repo, rel)).agent == "codex"
    assert "launched" not in _control(git_repo, "coga/log.md")
    assert "launched" in (git_repo.coga_os / "log.md").read_text(encoding="utf-8")


def test_startup_and_usage_preserve_concurrent_remote_log_appends(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "draft", "create")
    real_push = coga_git._push
    peers: list[str] = []

    def push(root, remote, refspec):  # type: ignore[no-untyped-def]
        subject = git_repo.git("show", "-s", "--format=%s", refspec.split(":")[0]).strip()
        if (subject.endswith("— in_progress") and not peers) or (subject.startswith("Log:") and len(peers) == 1):
            line = f"2026-10-27 00:00 v1 [peer] [system] concurrent {len(peers)}\n"
            peers.append(line)
            git_repo.push_competing_commit("coga/log.md", _control(git_repo, "coga/log.md") + line)
        return real_push(root, remote, refspec)

    monkeypatch.setattr(coga_git, "_push", push)
    launch_env(_Agent(git_repo, [lambda seen: _bump(git_repo, ref.id_slug, subprocess_run=True)]))
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", _usage_record)
    assert _main(monkeypatch, "launch", ref.id_slug) == 0
    final = _control(git_repo, "coga/log.md")
    assert len(peers) == 2
    for line in peers:
        assert final.count(line) == 1
    assert final.count("launched") == 1 and final.count('"session_id":"startup-usage"') == 1
    before = git_repo.git("rev-parse", "HEAD")
    coga_git.sync_log(load_config(git_repo.coga_os), message=f"Log: {ref.id_slug}")
    coga_git.sync_coga_state(load_config(git_repo.coga_os))
    assert git_repo.git("rev-parse", "HEAD") == before


@pytest.mark.parametrize("extra", ["entry", "command", "after-bump"])
def test_extra_state_publications_are_counted_outside_the_ordinary_bound(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, extra: str,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "draft", "control")
    start = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    knowledge = git_repo.coga_os / "context.md"
    if extra == "entry":
        knowledge.write_text("Extra eligible entry state.\n", encoding="utf-8", newline="\n")

    def work(seen: dict) -> None:
        _handoff(git_repo, ref, "First handoff edit.")
        if extra == "command":
            # A separate real mutating command sweeps the early blackboard.
            env = {k: v for k, v in os.environ.items() if not k.startswith("COGA_")}
            env["PYTHONPATH"] = str(Path(checkouts.__file__).resolve().parents[1])
            result = subprocess.run([sys.executable, "-m", "coga.cli", "run", "cleanup-orphan-markers"], cwd=git_repo.coga_os, env=env, capture_output=True, text=True, encoding="utf-8")
            assert result.returncode == 0, result.stdout + result.stderr
        _handoff(git_repo, ref, "Final handoff edit.")
        _bump(git_repo, ref.id_slug, subprocess_run=True)
        if extra == "after-bump":
            knowledge.write_text("Extra eligible return state.\n", encoding="utf-8", newline="\n")

    launch_env(_Agent(git_repo, [work]))
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", _usage_record)
    assert _main(monkeypatch, "launch", ref.id_slug) == 0
    assert int(git_repo.git("rev-list", "--count", f"{start}..main", cwd=git_repo.origin)) == 4
    assert "Final handoff edit." in _control(git_repo, _rel(git_repo, ref))
    if extra != "command":
        assert "Extra eligible" in _control(git_repo, "coga/context.md")
    assert _dirty(git_repo) == []


@pytest.mark.parametrize("failure", ["compose", "secret", "ignored-log", "source", "target"])
def test_grouped_preflight_refuses_before_any_startup_write(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "draft", "create")
    cfg = load_config(git_repo.coga_os)
    if failure in {"compose", "secret"}:
        ticket = read_ticket(ref)
        ticket.frontmatter["contexts" if failure == "compose" else "secrets"] = (
            ["missing/topic"] if failure == "compose" else [{"MISSING": "env:COGA_TEST_MISSING_SECRET"}]
        )
        ticket.write(ref.ticket_path)
        coga_git.sync_task_state(cfg, ref.path, message="Seed refused input")
    elif failure == "ignored-log":
        git_repo.git("rm", "-f", "coga/log.md")
        with (git_repo.root / ".gitignore").open("a", encoding="utf-8") as f:
            f.write("coga/log.md\n")
        git_repo.git("add", ".gitignore")
        git_repo.git("commit", "-m", "Ignore log")
        git_repo.git("push", "origin", "main")
    original = ref.ticket_path.read_bytes()
    log = git_repo.coga_os / "log.md"
    original_log = log.read_bytes() if log.exists() else None
    real_compose = launch_module.compose_prompt
    changed = False

    def compose(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal changed
        prompt = real_compose(*args, **kwargs)
        if kwargs.get("checkout") is not None and not changed:
            changed = True
            if failure == "source":
                ref.ticket_path.write_bytes(original + b"\nConcurrent local note.\n")
            elif failure == "target":
                branch = git_repo.git("branch", "--list", "coga/*").strip()
                tree = git_repo.git("rev-parse", "HEAD^{tree}").strip()
                other = git_repo.git("commit-tree", tree, "-p", "HEAD", "-m", "Target moved").strip()
                git_repo.git("update-ref", f"refs/heads/{branch}", other)
        return prompt

    monkeypatch.setattr(launch_module, "compose_prompt", compose)
    agent = _Agent(git_repo, [])
    launch_env(agent)
    assert _main(monkeypatch, "launch", ref.id_slug) in {2, 75}
    assert agent.seen == []
    assert read_ticket(ref).status == "draft"
    assert ref.ticket_path.read_bytes() == original + (b"\nConcurrent local note.\n" if failure == "source" else b"")
    assert (log.read_bytes() if log.exists() else None) == original_log
    assert _control(git_repo, _rel(git_repo, ref)).encode() == original


def test_failed_start_notification_is_nonfatal_after_clean_branch_entry(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    import requests

    ref = _startup_task(git_repo, "active", "create")
    calls: list[str] = []

    def fail_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(_head(git_repo))
        assert read_ticket(ref).status == "in_progress"
        assert "launched" in _control(git_repo, "coga/log.md")
        raise requests.ConnectionError("injected delivery failure")

    monkeypatch.setattr(requests, "post", fail_post)
    agent = _Agent(git_repo, [])
    launch_env(agent)
    assert _main(monkeypatch, "launch", ref.id_slug) == 0
    assert len(agent.seen) == 1 and len(calls) == 1
    assert calls[0].startswith("coga/")
    assert "post failed" in _control(git_repo, "coga/log.md")
    assert "post failed" in capsys.readouterr().err
    assert _dirty(git_repo) == []


@pytest.mark.parametrize("ending,exit_code", [
    ("natural", 0), ("nonzero", 3), ("timeout", 124), ("sigint", 130), ("sigterm", 143), ("spawn", 2),
])
def test_grouped_launch_cleanup_publishes_dirty_handoff_on_every_catchable_exit(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, ending: str, exit_code: int,
) -> None:  # type: ignore[no-untyped-def]
    import signal
    from coga.repl_supervisor import AgentCliNotFound

    ref = _startup_task(git_repo, "active", "create")
    launch_env(_Agent(git_repo, []))
    usages: list[str] = []

    def capture(**kwargs):  # type: ignore[no-untyped-def]
        usages.append(kwargs["outcome_status"])
        _usage_record(**kwargs)

    def child(*args, **kwargs):  # type: ignore[no-untyped-def]
        if ending == "spawn":
            raise AgentCliNotFound("missing test CLI")
        _handoff(git_repo, ref, "Dirty handoff without a transition.")
        if ending in {"sigint", "sigterm"}:
            signum = signal.SIGINT if ending == "sigint" else signal.SIGTERM
            signal.getsignal(signum)(signum, None)
        return ReplOutcome(exit_code, "timeout" if ending == "timeout" else "natural")

    monkeypatch.setattr(launch_module, "run_with_done_marker", child)
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", capture)
    assert _main(monkeypatch, "launch", ref.id_slug) == exit_code
    assert _head(git_repo) == "main" and _dirty(git_repo) == []
    assert read_ticket(ref).step == "1 (implement)"
    if ending != "spawn":
        assert usages and "Dirty handoff without a transition." in _control(git_repo, _rel(git_repo, ref))
        assert _control(git_repo, "coga/log.md").count('"session_id":"startup-usage"') == 1
    else:
        assert not usages


def test_abrupt_launch_death_is_recovered_at_the_next_entry(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "active", "create")
    script = tmp_path / "abrupt.py"
    script.write_text(dedent(f"""
        import os
        from pathlib import Path
        from coga import cli, launch
        launch.agent_sessions_supported = lambda: True
        launch._interactive_stdio_has_tty = lambda: True
        launch._preflight_push_auth = lambda *a, **k: None
        launch.shutil.which = lambda name: '/usr/bin/' + name
        def child(*args, **kwargs):
            path = Path({str(ref.ticket_path)!r})
            path.write_bytes(path.read_bytes() + b'\\nHandoff retained after abrupt death.\\n')
            os._exit(91)
        launch.run_with_done_marker = child
        cli.main()
    """), encoding="utf-8", newline="\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("COGA_")}
    env["PYTHONPATH"] = str(Path(checkouts.__file__).resolve().parents[1])
    result = subprocess.run([sys.executable, str(script), "launch", ref.id_slug], cwd=git_repo.coga_os, env=env, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 91, result.stdout + result.stderr
    assert _head(git_repo).startswith("coga/")
    assert "Handoff retained after abrupt death." not in _control(git_repo, _rel(git_repo, ref))
    assert '"session_id":"startup-usage"' not in _control(git_repo, "coga/log.md")
    agent = _Agent(git_repo, [])
    launch_env(agent)
    assert _main(monkeypatch, "launch", ref.id_slug) == 0
    assert "Handoff retained after abrupt death." in agent.seen[0]["prompt"]
    assert _dirty(git_repo) == [] and _head(git_repo) == "main"


def test_grouped_launch_usage_failure_keeps_the_child_result_and_reports_retained_log(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "active", "create")
    real_publish = coga_git.publish

    def publish(cfg, paths, message, **kwargs):  # type: ignore[no-untyped-def]
        if '"session_id":"startup-usage"' in (cfg.repo_root / "log.md").read_text(encoding="utf-8"):
            raise coga_git.GitError("usage publication unavailable")
        return real_publish(cfg, paths, message, **kwargs)

    monkeypatch.setattr(coga_git, "publish", publish)
    launch_env(_Agent(git_repo, []))
    monkeypatch.setattr(launch_module, "run_with_done_marker", lambda *a, **k: ReplOutcome(3, "natural"))
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", _usage_record)
    assert _main(monkeypatch, "launch", ref.id_slug) == 3
    err = capsys.readouterr().err
    assert "log publication was not confirmed" in err
    assert "Checkout return" in err and "preserved" in err
    assert "not on control" in err
    assert '"session_id":"startup-usage"' not in _control(git_repo, "coga/log.md")
    assert _head(git_repo).startswith("coga/")


def test_grouped_teardown_without_new_usage_attempts_publication_without_a_commit(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    ref = _startup_task(git_repo, "draft", "create")
    start = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    calls: list[bool | None] = []
    real_sync = coga_git.sync_log

    def sync(cfg, **kwargs):  # type: ignore[no-untyped-def]
        result = real_sync(cfg, **kwargs)
        calls.append(result)
        return result

    monkeypatch.setattr(coga_git, "sync_log", sync)
    launch_env(_Agent(git_repo, [lambda seen: _bump(git_repo, ref.id_slug, subprocess_run=True)]))
    assert _main(monkeypatch, "launch", ref.id_slug) == 0
    assert calls == [False]
    assert int(git_repo.git("rev-list", "--count", f"{start}..main", cwd=git_repo.origin)) == 2


@pytest.mark.parametrize("target", ["bootstrap/orient", "bootstrap/ticket"])
def test_bootstrap_keeps_its_start_and_usage_publications(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, target: str,
) -> None:  # type: ignore[no-untyped-def]
    start = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()

    def inspect(seen: dict) -> None:
        assert "launched" in _control(git_repo, "coga/log.md")
        assert _dirty(git_repo) == []

    launch_env(_Agent(git_repo, [inspect]))
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", _usage_record)
    assert _main(monkeypatch, "launch", target) == 0
    assert git_repo.git("log", "--reverse", "--format=%s", f"{start}..main", cwd=git_repo.origin).splitlines() == [f"Log: {target}"] * 2
    assert _dirty(git_repo) == []


@pytest.mark.parametrize("status,count", [("active", 4), ("draft", 5), ("in_progress", 3)])
def test_script_start_and_exit_keep_their_independent_publications(
    git_repo, monkeypatch: pytest.MonkeyPatch, status: str, count: int,
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg, title="Script publications", workflow_name="code", contexts=[],
        owner="marc", agent="claude", status="active", force_directory=True,
    )
    directory = Path(created["path"])
    ticket_path = directory / "ticket.md"
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = status
    ticket.workflow["steps"][1]["assignee"] = "owner"
    ticket.write(ticket_path)
    (directory / "ticket.py").write_text(
        "import subprocess, sys\n"
        f"subprocess.run([sys.executable, '-m', 'coga.cli', 'bump', {created['slug']!r}], check=True)\n",
        encoding="utf-8", newline="\n",
    )
    coga_git.sync_task_state(cfg, directory, message="Seed scripted task")
    start = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    monkeypatch.setenv("PYTHONPATH", str(Path(checkouts.__file__).resolve().parents[1]))
    assert _main(monkeypatch, "launch", created["slug"]) == 0
    subjects = git_repo.git("log", "--reverse", "--format=%s", f"{start}..main", cwd=git_repo.origin).splitlines()
    assert len(subjects) == count
    assert subjects[-2:] == [f"Ticket: {created['slug']} — step 2 (review)", "Sync coga state before checkout return"]
    assert _dirty(git_repo) == [] and _head(git_repo) == "main"


def test_implementation_starts_on_a_published_branch_and_chains_through_review(
    git_repo, launch_env
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    branch: list[str] = []

    def implement(seen: dict) -> None:
        branch.append(seen["head"])
        assert seen["head"].startswith("coga/")
        # Linkage reached control before the agent started.
        assert f"branch: {seen['head']}" in _control(git_repo, rel)
        assert seen["dirty"] == [rel]
        assert ref.ticket_path.read_text(encoding="utf-8") == _control(git_repo, rel)
        assert f"switched to branch `{seen['head']}`" in seen["prompt"]
        assert "## Checkout (runtime)" in seen["prompt"]
        (git_repo.root / "feature.py").write_text("print('work')\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "feature.py")
        git_repo.git("commit", "-m", "Implement feature")
        _handoff(git_repo, ref, "implemented")
        _bump(git_repo, ref.id_slug)

    def self_qa(seen: dict) -> None:
        assert seen["head"] == branch[0]
        assert "implemented" in ref.ticket_path.read_text(encoding="utf-8")
        assert "reused and switched" in seen["prompt"]
        _handoff(git_repo, ref, "qa done")
        _bump(git_repo, ref.id_slug)

    def publish(seen: dict) -> None:
        assert seen["head"] == "main"
        assert "which runs from control" in seen["prompt"]

    agent = _Agent(git_repo, [implement, self_qa, publish])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    assert [s["step"] for s in agent.seen] == ["1 (implement)", "2 (self-qa)", "3 (pr)"]
    assert _head(git_repo) == "main" and _dirty(git_repo) == []
    control = _control(git_repo, rel)
    assert "qa done" in control and "step: 3 (pr)" in control
    # The implementation commit carries no ticket.
    files = git_repo.git("show", "--name-only", "--format=", branch[0]).split()
    assert files == ["feature.py"]
    # The launch audit reached control on control, before the switch. (Union
    # publication collapses identical same-minute lines, so count >= 1.)
    assert "] launched (operator=claude" in _control(git_repo, "coga/log.md")


def test_resume_projects_newer_control_ticket_and_a_separate_bump_publishes(
    git_repo, launch_env
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    # Start the work, then mark it in progress with linkage, like an old session.
    git_repo.git("branch", "feature/old")
    _write_dev_branch(git_repo, ref, "feature/old")
    cfg = load_config(git_repo.coga_os)
    coga_git.sync_task_state(cfg, ref.path, message="link")
    # Already in progress, so launch writes no activation or linkage for it.
    _mark_in_progress(git_repo, ref)
    # Another checkout edits the ticket after the branch point.
    other = _clone_checkout(git_repo, "other")
    other_ticket = other / rel
    other_ticket.write_text(other_ticket.read_text(encoding="utf-8") + "\nnote from elsewhere\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "-C", str(other), "commit", "-qam", "edit"], check=True)
    subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "main"], check=True)

    def resumed(seen: dict) -> None:
        assert seen["head"] == "feature/old"
        text = ref.ticket_path.read_text(encoding="utf-8")
        assert "note from elsewhere" in text
        published = coga_git.PUBLISHED_REF
        assert git_repo.git("rev-parse", f"{published}:{rel}").strip() == (
            git_repo.git("rev-parse", f"origin/main:{rel}").strip()
        )
        _handoff(git_repo, ref, "resumed handoff")
        _bump(git_repo, ref.id_slug, subprocess_run=True)

    agent = _Agent(git_repo, [resumed])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    control = _control(git_repo, rel)
    assert "resumed handoff" in control and "note from elsewhere" in control
    assert "step: 2 (self-qa)" in control
    assert agent.seen[0]["step"] == "1 (implement)"


def test_competing_ticket_change_after_preparation_still_refuses(
    git_repo, launch_env
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    other = _clone_checkout(git_repo, "other")

    def compete_then_handoff(seen: dict) -> None:
        subprocess.run(["git", "-C", str(other), "fetch", "-q", "origin"], check=True)
        subprocess.run(
            ["git", "-C", str(other), "reset", "-q", "--hard", "origin/main"], check=True
        )
        theirs = other / rel
        theirs.write_text(theirs.read_text(encoding="utf-8") + "\ncompeting edit\n", encoding="utf-8", newline="\n")
        subprocess.run(["git", "-C", str(other), "commit", "-qam", "compete"], check=True)
        subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "main"], check=True)
        _handoff(git_repo, ref, "local handoff")
        prev = os.getcwd()
        os.chdir(git_repo.coga_os)
        try:
            CliRunner().invoke(app, ["bump", ref.id_slug])
        finally:
            os.chdir(prev)

    agent = _Agent(git_repo, [compete_then_handoff])
    launch_env(agent)

    _launch(ref.id_slug)

    control = _control(git_repo, rel)
    assert "competing edit" in control and "local handoff" not in control
    assert "local handoff" in ref.ticket_path.read_text(encoding="utf-8")
    assert _head(git_repo) == agent.seen[0]["head"]


def test_missing_recorded_branch_refuses_on_control(git_repo, launch_env) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    _write_dev_branch(git_repo, ref, "feature/gone")
    coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="link")
    agent = _Agent(git_repo, [])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
    assert "exists neither locally nor on origin" in result.output
    assert agent.seen == []
    assert _head(git_repo) == "main"
    assert git_repo.git("branch", "--list", "feature/gone").strip() == ""


def test_remote_only_branch_is_recreated_at_its_fetched_tip(git_repo, launch_env) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    git_repo.git("branch", "feature/remote")
    (git_repo.root / "remote.py").write_text("x\n", encoding="utf-8", newline="\n")
    git_repo.git("switch", "-q", "feature/remote")
    git_repo.git("add", "remote.py")
    git_repo.git("commit", "-qm", "remote work")
    tip = git_repo.git("rev-parse", "HEAD").strip()
    git_repo.git("push", "-q", "origin", "feature/remote")
    git_repo.git("switch", "-q", "main")
    git_repo.git("branch", "-D", "feature/remote")
    _write_dev_branch(git_repo, ref, "feature/remote")
    coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="link")
    agent = _Agent(git_repo, [lambda seen: None])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    assert agent.seen[0]["head"] == "feature/remote"
    assert git_repo.git("rev-parse", "feature/remote").strip() == tip


def test_local_ahead_branch_keeps_its_commits_and_says_so(git_repo, launch_env) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    git_repo.git("branch", "feature/ahead")
    git_repo.git("push", "-q", "origin", "feature/ahead")
    git_repo.git("switch", "-q", "feature/ahead")
    (git_repo.root / "ahead.py").write_text("x\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "ahead.py")
    git_repo.git("commit", "-qm", "unpushed")
    tip = git_repo.git("rev-parse", "HEAD").strip()
    git_repo.git("switch", "-q", "main")
    _write_dev_branch(git_repo, ref, "feature/ahead")
    coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="link")
    agent = _Agent(git_repo, [lambda seen: None])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    assert agent.seen[0]["head"] == "feature/ahead"
    assert git_repo.git("rev-parse", "feature/ahead").strip() == tip
    assert "is ahead of origin/feature/ahead" in agent.seen[0]["prompt"]


def test_branch_with_stranded_ticket_intent_refuses(git_repo, launch_env) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    git_repo.git("switch", "-q", "-c", "feature/stranded")
    ref.ticket_path.write_text(ref.ticket_path.read_text(encoding="utf-8") + "\nbranch-only intent\n", encoding="utf-8", newline="\n")
    git_repo.git("commit", "-qam", "strand the ticket")
    git_repo.git("switch", "-q", "main")
    _write_dev_branch(git_repo, ref, "feature/stranded")
    coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="link")
    agent = _Agent(git_repo, [])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
    assert "stranded ticket" in result.output
    assert agent.seen == [] and _head(git_repo) == "main"
    assert "branch-only intent" in git_repo.git("show", f"feature/stranded:{rel}")


def test_interrupted_linkage_publication_retries_the_same_reservation(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    real_sync = coga_git.publish
    calls = {"n": 0}

    def flaky(cfg, path, message, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("guard") is not None and calls["n"] == 0:
            calls["n"] += 1
            raise coga_git.GitError("offline")
        return real_sync(cfg, path, message=message, **kwargs)

    monkeypatch.setattr("coga.git.publish", flaky)
    agent = _Agent(git_repo, [lambda seen: None])
    launch_env(agent)

    first = _launch(ref.id_slug)

    assert first.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, first.output
    assert "startup publication" in first.output
    assert agent.seen == [] and _head(git_repo) == "main"
    reserved = Ticket.read(ref.ticket_path)
    local_branch = checkouts.parse_branch_names(read_blackboard(ref.ticket_path))[0]
    assert f"branch: {local_branch}" not in _control(git_repo, rel)
    assert git_repo.git("rev-parse", "--verify", f"refs/heads/{local_branch}")
    assert reserved.status == "in_progress"

    second = _launch(ref.id_slug)

    assert second.exit_code == 0, second.output
    assert agent.seen[0]["head"] == local_branch
    assert f"branch: {local_branch}" in _control(git_repo, rel)
    branches = git_repo.git("branch", "--list", "coga/*").split()
    assert branches == [local_branch]


@pytest.mark.parametrize("stage", ["entry", "launch audit"])
@pytest.mark.parametrize(
    "change",
    ["workflow", "step-name", "step-skills", "assignee", "skill-body", "inline-body"],
)
def test_launch_refuses_a_refreshed_step_contract(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, stage: str, change: str
) -> None:  # type: ignore[no-untyped-def]
    workflow = "docs/with-review" if change == "inline-body" else "code/with-self-review"
    if change == "inline-body":
        with (git_repo.coga_os / "coga.local.toml").open("a") as config:
            config.write('\n[agents.codex]\ncli = "codex"\nfile = "AGENTS.md"\n')
    ref = _task(git_repo, workflow)
    rel = _rel(git_repo, ref)
    real_prove = checkouts._prove_control
    changed_path: list[str] = []
    changed_bytes: list[str] = []

    def compete(cfg, current_stage):  # type: ignore[no-untyped-def]
        if current_stage == stage and not changed_path:
            current = Ticket.parse(_control(git_repo, rel))
            path = rel
            if change == "workflow":
                current.workflow["name"] = "code/with-review"
            elif change == "step-name":
                current.current_step()["name"] = "pr"
            elif change == "step-skills":
                current.current_step()["skills"] = ["code/self-qa"]
            elif change == "assignee":
                current.current_step()["assignee"] = "owner"
            if change == "skill-body":
                path = "coga/skills/code/implement/SKILL.md"
                text = bootstrap_skill_path(cfg, "code/implement").read_text(encoding="utf-8") + "\nChanged.\n"
            elif change == "inline-body":
                path = "coga/workflows/docs/with-review.md"
                text = bootstrap_workflow_path(cfg, workflow).read_text(encoding="utf-8").replace(
                    "## implement\n", "## implement\n\nChanged.\n"
                )
            else:
                # All races retain exactly the lifecycle tuple checked before this fix.
                assert (current.status, current.step) == (
                    read_ticket(ref).status, read_ticket(ref).step
                )
                text = current.render()
            git_repo.push_competing_commit(path, text)
            changed_path.append(path)
            changed_bytes.append(text)
        return real_prove(cfg, current_stage)

    monkeypatch.setattr(checkouts, "_prove_control", compete)
    agent = _Agent(git_repo, [])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
    assert f"stopped at {stage}" in result.output
    assert "retry the launch" in result.output
    assert agent.seen == [] and _head(git_repo) == "main"
    assert _dirty(git_repo) == []
    assert _control(git_repo, changed_path[0]) == changed_bytes[0]
    assert coga_git.state_sweep_withheld.get() is True
    branches = git_repo.git("branch", "--list", "coga/*").split()
    if stage == "entry":
        assert branches == []
    else:
        assert branches == checkouts.parse_branch_names(read_blackboard(ref.ticket_path))


@pytest.mark.parametrize("stage", ["entry", "launch audit"])
def test_launch_accepts_only_post_publication_notes_with_the_same_step_contract(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    real_prove = checkouts._prove_control
    changed = False

    def compete(cfg, current_stage):  # type: ignore[no-untyped-def]
        nonlocal changed
        if current_stage == stage and not changed:
            git_repo.push_competing_commit(rel, _control(git_repo, rel) + "\nNew owner note.\n")
            changed = True
        return real_prove(cfg, current_stage)

    monkeypatch.setattr(checkouts, "_prove_control", compete)
    agent = _Agent(git_repo, [])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == (75 if stage == "entry" else 0), result.output
    if stage == "entry":
        assert agent.seen == []
        assert "changed since startup preflight" in result.output
        assert "launched" not in _control(git_repo, "coga/log.md")
        return
    assert len(agent.seen) == 1
    assert "New owner note." in agent.seen[0]["prompt"]
    assert "New owner note." in _control(git_repo, rel)
    assert _head(git_repo) == "main" and _dirty(git_repo) == []


def test_failed_baseline_write_refuses_spawn_and_preserves_the_branch(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")

    def refuse(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise coga_git.GitError("read-only metadata")

    monkeypatch.setattr("coga.git.record_projected_baseline", refuse)
    agent = _Agent(git_repo, [])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
    assert "provenance" in result.output
    assert agent.seen == []
    branch = checkouts.parse_branch_names(read_blackboard(ref.ticket_path))[0]
    assert _head(git_repo) == branch
    assert coga_git.state_sweep_withheld.get() is True


def test_custom_workflow_gets_an_explicit_manual_notice(git_repo, launch_env) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code")

    def check(seen: dict) -> None:
        assert seen["head"] == "main"
        assert "did not set up a branch" in seen["prompt"]

    agent = _Agent(git_repo, [check])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    assert len(agent.seen) == 1


def test_reuse_step_without_branch_but_with_already_satisfied_stays_on_control(
    git_repo, launch_env
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "2 (self-qa)"
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    replace_blackboard(
        ref.ticket_path,
        read_blackboard(ref.ticket_path) + "\n## Already satisfied\n\nevidence\n",
    )
    coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="qa")

    def check(seen: dict) -> None:
        assert seen["head"] == "main"
        assert "Already satisfied" in seen["prompt"]

    agent = _Agent(git_repo, [check])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    assert git_repo.git("branch", "--list", "coga/*").strip() == ""


# --- composition ----------------------------------------------------------------


def test_compose_without_a_result_claims_no_preparation(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    ref = _task(git_repo, "code/with-self-review")
    report = compose_prompt_report(cfg, ref, read_ticket(ref))
    assert report.layers[-1].layer == "checkout_notice"
    assert "No checkout preparation was supplied" in report.prompt
    notice = CheckoutNotice(summary="On `b`.", return_owner="Launch returns it.", projected="t.md")
    supplied = compose_prompt_report(cfg, ref, read_ticket(ref), checkout=notice)
    assert "On `b`." in supplied.prompt and "`t.md`" in supplied.prompt
    assert "No checkout preparation" not in supplied.prompt


# --- direct chat ----------------------------------------------------------------


def _run_recipe(git_repo, *args: str):  # type: ignore[no-untyped-def]
    prev = os.getcwd()
    os.chdir(git_repo.coga_os)
    try:
        return CliRunner().invoke(app, ["run", "prepare-checkout", *args])
    finally:
        os.chdir(prev)


def test_chat_recipe_without_a_live_guard_refuses(git_repo) -> None:  # type: ignore[no-untyped-def]
    result = _run_recipe(git_repo, "--session", "abc")
    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    assert "no live direct chat" in result.output
    assert _head(git_repo) == "main"


def test_chat_recipe_usage_error(git_repo) -> None:  # type: ignore[no-untyped-def]
    assert _run_recipe(git_repo).exit_code == 2


def test_chat_discusses_on_control_then_prepares_and_reuses_one_branch(
    git_repo,
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    origin_before = git_repo.git("rev-parse", "main", cwd=git_repo.origin)
    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        assert session is not None
        # Discussion only: nothing allocated.
        assert git_repo.git("branch", "--list", session.branch).strip() == ""

        first = _run_recipe(git_repo, "--session", session.session)
        assert first.exit_code == 0, first.output
        assert f"prepared: branch {session.branch}" in first.output
        assert _head(git_repo) == session.branch

        (git_repo.root / "edit.py").write_text("dirty\n", encoding="utf-8", newline="\n")
        context = git_repo.coga_os / "notes.md"
        context.write_text("unfinished\n", encoding="utf-8", newline="\n")
        again = _run_recipe(git_repo, "--session", session.session)
        assert again.exit_code == 0, again.output
        assert "reused" in again.output
        assert (git_repo.root / "edit.py").read_text(encoding="utf-8") == "dirty\n"

        stale = _run_recipe(git_repo, "--session", "not-this-chat")
        assert stale.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE
        assert "is not the live chat" in stale.output

        git_repo.git("switch", "-q", "-c", "elsewhere")
        moved = _run_recipe(git_repo, "--session", session.session)
        assert moved.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE
        assert "nothing was adopted" in moved.output
    # No repeated call published the chat's unfinished state.
    assert git_repo.git("rev-parse", "main", cwd=git_repo.origin) == origin_before
    assert not session.receipt.exists()


def test_chat_recipe_refuses_a_dirty_control_checkout(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        (git_repo.root / "wip.py").write_text("unsaved\n", encoding="utf-8", newline="\n")
        result = _run_recipe(git_repo, "--session", session.session)
        assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE
        assert "wip.py" in result.output
        assert _head(git_repo) == "main"
        assert git_repo.git("branch", "--list", session.branch).strip() == ""


@pytest.mark.parametrize("failure", ["before-ref", "after-ref", "creation-receipt"])
def test_chat_retries_interrupted_creation_at_the_reserved_commit(
    git_repo, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    pinned = git_repo.git("rev-parse", "HEAD").strip()
    real_git = coga_git.run_git
    real_write = checkouts.atomic_write_text
    failed = False

    def flaky_git(root, *args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal failed
        if args[:2] == ("branch", "--no-track") and failure != "creation-receipt" and not failed:
            failed = True
            if failure == "after-ref":
                real_git(root, *args, **kwargs)
            raise coga_git.GitError("transient branch failure")
        return real_git(root, *args, **kwargs)

    def flaky_write(path, text, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal failed
        if path == session.receipt and failure == "creation-receipt" and not failed:
            if json.loads(text).get("created_oid"):
                # Only fail the receipt after the Git ref actually exists.
                if git_repo.git("branch", "--list", session.branch).strip():
                    failed = True
                    raise OSError("transient receipt failure")
        return real_write(path, text, **kwargs)

    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        assert session is not None
        monkeypatch.setattr(coga_git, "run_git", flaky_git)
        monkeypatch.setattr(checkouts, "atomic_write_text", flaky_write)

        first = _run_recipe(git_repo, "--session", session.session)

        assert first.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, first.output
        assert failed and _head(git_repo) == "main" and _dirty(git_repo) == []
        receipt = json.loads(session.receipt.read_text(encoding="utf-8"))
        assert bool(git_repo.git("branch", "--list", session.branch).strip()) == (
            failure != "before-ref"
        )
        git_repo.push_competing_commit("later.txt", "Control advanced while retrying.\n")
        remote = git_repo.git("rev-parse", "main", cwd=git_repo.origin)

        retry = _run_recipe(git_repo, "--session", session.session)

        assert retry.exit_code == 0, retry.output
        assert _head(git_repo) == session.branch
        assert git_repo.git("rev-parse", "HEAD").strip() == pinned
        assert git_repo.git("branch", "--list", "coga/*").split() == ["*", session.branch]
        assert receipt["reserved_oid"] == pinned
        assert receipt["created_oid"] is None
        assert json.loads(session.receipt.read_text(encoding="utf-8"))["created_oid"] == pinned
        assert git_repo.git("rev-parse", "main", cwd=git_repo.origin) == remote


@pytest.mark.parametrize("reserved", [False, True])
def test_chat_refuses_a_branch_without_matching_creation_evidence(
    git_repo, monkeypatch: pytest.MonkeyPatch, reserved: bool
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    real_git = coga_git.run_git

    def fail_creation(root, *args, **kwargs):  # type: ignore[no-untyped-def]
        if args[:2] == ("branch", "--no-track"):
            raise coga_git.GitError("transient branch failure")
        return real_git(root, *args, **kwargs)

    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        assert session is not None
        if reserved:
            with monkeypatch.context() as patch:
                patch.setattr(coga_git, "run_git", fail_creation)
                first = _run_recipe(git_repo, "--session", session.session)
            assert first.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, first.output
            git_repo.push_competing_commit("later.txt", "A different branch tip.\n")
            git_repo.git("fetch", "origin", "main")
        git_repo.git("branch", "--no-track", session.branch, "origin/main")
        tip = git_repo.git("rev-parse", session.branch)
        receipt = session.receipt.read_bytes()

        result = _run_recipe(git_repo, "--session", session.session)

        assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
        assert "nothing was adopted" in result.output
        assert _head(git_repo) == "main" and _dirty(git_repo) == []
        assert git_repo.git("rev-parse", session.branch) == tip
        assert session.receipt.read_bytes() == receipt


def test_chat_does_not_recreate_a_confirmed_branch_after_deletion(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)

    def refuse_switch(*args):  # type: ignore[no-untyped-def]
        raise checkouts.CheckoutPreparationError("switch", "interrupted before switch")

    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        assert session is not None
        monkeypatch.setattr(checkouts, "_switch", refuse_switch)
        first = _run_recipe(git_repo, "--session", session.session)
        assert first.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, first.output
        assert json.loads(session.receipt.read_text(encoding="utf-8"))["created_oid"]
        git_repo.git("branch", "-D", session.branch)

        retry = _run_recipe(git_repo, "--session", session.session)

        assert retry.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, retry.output
        assert "was created by this chat but no longer exists" in retry.output
        assert _head(git_repo) == "main" and _dirty(git_repo) == []
        assert git_repo.git("branch", "--list", session.branch).strip() == ""


def test_chat_launch_notice_carries_the_exact_invocation(
    git_repo, launch_env
) -> None:  # type: ignore[no-untyped-def]
    seen: list[str] = []

    def chat(record: dict) -> None:
        seen.append(record["prompt"])

    agent = _Agent(git_repo, [chat])
    launch_env(agent)

    result = _launch("bootstrap/orient")

    assert result.exit_code == 0, result.output
    assert "coga run prepare-checkout --session " in seen[0]
    assert "routine Coga-state-only edits stay on control" in seen[0]
    assert "Before editing any file" not in seen[0]
    assert "require success and a clean checkout" in seen[0]
    assert str(git_repo.coga_os) in seen[0]
    assert _head(git_repo) == "main"


@pytest.mark.parametrize("staged", [False, True])
@pytest.mark.parametrize("publish_during_chat", [False, True])
def test_state_only_chat_renames_publish_without_allocating_a_branch(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, staged: bool,
    publish_during_chat: bool,
) -> None:  # type: ignore[no-untyped-def]
    refs = [_task(git_repo, "code", title=f"Rename {i}") for i in range(3)]
    new = [ref.ticket_path.with_name(f"renamed-{i}.md") for i, ref in enumerate(refs)]
    captured: list[dict] = []
    index: list[str] = []
    sweeps: list[bool] = []
    from coga import cli
    real_sweep = cli._sweep_coga_state

    def sweep(cfg) -> None:  # type: ignore[no-untyped-def]
        sweeps.append(True)
        real_sweep(cfg)

    monkeypatch.setattr(cli, "_sweep_coga_state", sweep)
    paths = [path.relative_to(git_repo.root).as_posix() for path in [*(r.ticket_path for r in refs), *new]]

    def chat(seen: dict) -> None:
        assert seen["head"] == "main"
        session = launch_module._CHAT_SESSION.get()
        assert session is not None
        assert git_repo.git("branch", "--list", session.branch) == ""
        for ref, path in zip(refs, new):
            ref.ticket_path.rename(path)
        if staged:
            git_repo.git("--literal-pathspecs", "add", "--all", "--", *paths)
        index.append(git_repo.git("ls-files", "--stage", "--", *paths))
        for path in new:
            replace_blackboard(path, "\nWorking prose after renaming.\n")
        if publish_during_chat:
            coga_git.sync_coga_state(load_config(git_repo.coga_os))
            if staged:
                assert git_repo.git("ls-files", "--stage", "--", *paths) == index[0]

    def capture(**kwargs) -> None:  # type: ignore[no-untyped-def]
        captured.append(kwargs)
        _usage_record(**kwargs)

    launch_env(_Agent(git_repo, [chat]))
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", capture)
    assert _main(monkeypatch, "chat") == (75 if staged else 0)
    assert captured[0]["exit_code"] == 0
    assert captured[0]["exit_kind"] == "done"
    assert _head(git_repo) == "main"
    assert git_repo.git("branch", "--list", "coga/chat-*") == ""
    assert all(not git_repo.origin_tracks(path.relative_to(git_repo.root).as_posix()) for path in (ref.ticket_path for ref in refs))
    for path in new:
        assert "Working prose after renaming." in _control(git_repo, path.relative_to(git_repo.root).as_posix())
    assert '"session_id":"startup-usage"' in _control(git_repo, "coga/log.md")
    if staged:
        assert git_repo.git("ls-files", "--stage", "--", *paths) == index[0]
        assert sweeps == []
    else:
        assert _dirty(git_repo) == []
        assert git_repo.git("rev-parse", "HEAD") == git_repo.git("rev-parse", "main", cwd=git_repo.origin)


@pytest.mark.parametrize("layout", ["nested", "relocated", "root"])
def test_chat_publishes_routine_state_before_preparing_reviewed_work(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, layout: str,
) -> None:  # type: ignore[no-untyped-def]
    if layout == "root":
        # Windows cannot remove the process's current directory.
        monkeypatch.chdir(git_repo.root)
        for path in git_repo.coga_os.iterdir():
            path.rename(git_repo.root / path.name)
        git_repo.coga_os.rmdir()
        git_repo.coga_os = git_repo.root
        (git_repo.root / ".gitignore").write_text("coga.local.toml\n.agent-skills/\n.coga/\n", encoding="utf-8", newline="\n")
    elif layout == "relocated":
        contexts = git_repo.root / "knowledge library"
        contexts.mkdir()
        (contexts / ".gitkeep").write_text("", encoding="utf-8", newline="\n")
        with (git_repo.coga_os / "coga.toml").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write('[layout]\ncontexts = "knowledge library"\n')
    if layout != "nested":
        git_repo.git("add", "--all")
        git_repo.git("commit", "-m", "Configure roots")
        git_repo.git("push", "origin", "main")
    cfg = load_config(git_repo.coga_os)
    ref = _task(git_repo, "code")
    moved = ref.ticket_path.with_name("renamed.md")
    context = cfg.contexts_root / "team" / "SKILL.md"
    branch: list[str] = []

    def chat(seen: dict) -> None:
        assert str(cfg.repo_root) in seen["prompt"]
        if layout == "relocated":
            assert str(cfg.contexts_root) in seen["prompt"]
        ref.ticket_path.rename(moved)
        replace_blackboard(moved, "\nRoutine ticket prose.\n")
        context.parent.mkdir(parents=True)
        context.write_text("Routine knowledge.\n", encoding="utf-8", newline="\n")
        published = CliRunner().invoke(app, ["run", "publish-state"])
        assert published.exit_code == 0, published.output
        assert _dirty(git_repo) == []
        assert "Routine ticket prose" in _control(git_repo, moved.relative_to(git_repo.root).as_posix())
        assert not git_repo.origin_tracks(ref.ticket_path.relative_to(git_repo.root).as_posix())
        session = launch_module._CHAT_SESSION.get()
        prepared = _run_recipe(git_repo, "--session", session.session)
        assert prepared.exit_code == 0, prepared.output
        branch.append(_head(git_repo))
        source = git_repo.root / "work.py"
        source.write_text("reviewed implementation\n", encoding="utf-8", newline="\n")
        context.write_text("Deliberately reviewed knowledge.\n", encoding="utf-8", newline="\n")
        assert _run_recipe(git_repo, "--session", session.session).exit_code == 0
        assert _control(git_repo, context.relative_to(git_repo.root).as_posix()) == "Routine knowledge.\n"
        git_repo.git("add", "--", "work.py", context.relative_to(git_repo.root).as_posix())
        git_repo.git("commit", "-m", "Reviewed work")

    launch_env(_Agent(git_repo, [chat]))
    assert _main(monkeypatch, "chat") == 0
    assert _head(git_repo) == "main" and _dirty(git_repo) == []
    assert not git_repo.origin_tracks("work.py")
    assert git_repo.git("show", f"{branch[0]}:work.py") == "reviewed implementation\n"
    assert _control(git_repo, context.relative_to(git_repo.root).as_posix()) == "Routine knowledge.\n"


def test_failed_state_publication_does_not_prepare_a_chat_branch(git_repo, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        (git_repo.coga_os / "notes.md").write_text("pending\n", encoding="utf-8", newline="\n")
        monkeypatch.setattr(coga_git, "_push", lambda *a: "network unavailable")
        result = CliRunner().invoke(app, ["run", "publish-state"])
        assert result.exit_code == 1, result.output
        assert _head(git_repo) == "main"
        # Even a caller ignoring the failure cannot switch with dirty state.
        assert _run_recipe(git_repo, "--session", session.session).exit_code == 75
        assert git_repo.git("branch", "--list", session.branch) == ""


@pytest.mark.parametrize("publish_during_chat", [False, True])
def test_control_chat_keeps_distinct_staged_ticket_draft_through_return(
    git_repo, launch_env, publish_during_chat: bool,
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code")
    rel = _rel(git_repo, ref)
    index: list[str] = []

    def chat(seen: dict) -> None:
        assert seen["head"] == "main"
        replace_blackboard(ref.ticket_path, "\nUnique staged intent.\n")
        git_repo.git("add", "--", rel)
        index.append(git_repo.git("show", f":{rel}"))
        replace_blackboard(ref.ticket_path, "\nWorking prose.\n")
        if publish_during_chat:
            coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="Routine task write")
            assert git_repo.git("show", f":{rel}") == index[0]

    launch_env(_Agent(git_repo, [chat]))
    result = _launch("bootstrap/orient")
    assert result.exit_code == 75, result.output
    assert "Working prose." in _control(git_repo, rel)
    assert git_repo.git("show", f":{rel}") == index[0]
    assert "Working prose." in ref.ticket_path.read_text(encoding="utf-8")
    assert "working file matches control" in result.output
    assert "staged copy differs" in result.output


# --- helpers --------------------------------------------------------------------


def _write_dev_branch(git_repo, ref: TaskRef, branch: str) -> None:  # type: ignore[no-untyped-def]
    replace_blackboard(
        ref.ticket_path,
        checkouts.insert_branch_line(read_blackboard(ref.ticket_path), branch),
    )


def _mark_in_progress(git_repo, ref: TaskRef) -> None:  # type: ignore[no-untyped-def]
    ticket = read_ticket(ref)
    if ticket.status != "in_progress":
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(ref.ticket_path)
        coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="start")


def _clone_checkout(git_repo, name: str) -> Path:  # type: ignore[no-untyped-def]
    path = git_repo.root.parent / name
    subprocess.run(
        ["git", "clone", "-q", "-b", "main", str(git_repo.origin), str(path)], check=True
    )
    for key, value in (("user.email", "o@example.test"), ("user.name", "Other")):
        subprocess.run(["git", "-C", str(path), "config", key, value], check=True)
    subprocess.run(["git", "-C", str(path), "config", "commit.gpgsign", "false"], check=True)
    return path


# --- exemptions and procedures --------------------------------------------------


def test_script_phase_runs_on_control_before_branch_preparation(
    git_repo, launch_env, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg, title="Scripted prep", workflow_name="code/with-self-review",
        contexts=[], owner="marc", agent="claude", status="active",
        force_directory=True,
    )
    witness = tmp_path / "script-head.txt"
    task_dir = Path(created["path"])
    (task_dir / "ticket.py").write_text(
        "import subprocess, pathlib\n"
        "head = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],"
        " capture_output=True, text=True).stdout\n"
        f"pathlib.Path({str(witness)!r}).write_text(head)\n",
        encoding="utf-8", newline="\n",
    )
    coga_git.sync_task_state(cfg, task_dir, message="Seed scripted task")
    agent = _Agent(git_repo, [lambda seen: None])
    launch_env(agent)

    result = _launch(created["slug"])

    assert result.exit_code == 0, result.output
    assert witness.read_text(encoding="utf-8").strip() == "main"
    assert agent.seen[0]["head"].startswith("coga/")
    assert agent.seen[0]["dirty"] == [(task_dir / "ticket.md").relative_to(git_repo.root).as_posix()]


def test_recorded_clone_keeps_the_primary_on_control(git_repo, launch_env) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    git_repo.git("branch", "feature/clone")
    git_repo.git("push", "-q", "origin", "feature/clone")
    clone = _clone_checkout(git_repo, "sandbox")
    subprocess.run(["git", "-C", str(clone), "switch", "-q", "feature/clone"], check=True)
    replace_blackboard(
        ref.ticket_path,
        checkouts.insert_branch_line(read_blackboard(ref.ticket_path), "feature/clone")
        .replace("branch: feature/clone\n", f"branch: feature/clone\nworktree: {clone}\n"),
    )
    coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="link")

    def check(seen: dict) -> None:
        assert seen["head"] == "main" and seen["dirty"] == []
        assert f"the recorded clone `{clone}`" in seen["prompt"]

    agent = _Agent(git_repo, [check])
    launch_env(agent)
    assert _launch(ref.id_slug).exit_code == 0
    assert len(agent.seen) == 1

    subprocess.run(["git", "-C", str(clone), "switch", "-q", "main"], check=True)
    refused = _Agent(git_repo, [])
    launch_env(refused)
    result = _launch(ref.id_slug)
    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
    assert "not 'feature/clone'" in result.output
    assert refused.seen == [] and _head(git_repo) == "main"


def test_documented_rebase_keeps_projection_and_notes_out_of_commits(
    git_repo, launch_env
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    other = _clone_checkout(git_repo, "other")

    def implement_and_rebase(seen: dict) -> None:
        (git_repo.root / "feature.py").write_text("work\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "feature.py")
        git_repo.git("commit", "-qm", "Implement")
        _handoff(git_repo, ref, "notes before rebase")
        # Control moves under the session.
        subprocess.run(["git", "-C", str(other), "pull", "-q", "--ff-only"], check=True)
        (other / "upstream.py").write_text("upstream\n", encoding="utf-8", newline="\n")
        subprocess.run(["git", "-C", str(other), "add", "upstream.py"], check=True)
        subprocess.run(["git", "-C", str(other), "commit", "-qm", "upstream"], check=True)
        subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "main"], check=True)
        # coga/checkouts: copy the ticket out, restore it from HEAD, rebase,
        # write the copy back unstaged.
        saved = ref.ticket_path.read_bytes()
        git_repo.git("restore", "--source=HEAD", "--worktree", "--", rel)
        git_repo.git("fetch", "-q", "origin", "main")
        git_repo.git("rebase", "-q", "FETCH_HEAD")
        ref.ticket_path.write_bytes(saved)
        assert ref.ticket_path.read_bytes() == saved
        _bump(git_repo, ref.id_slug)

    agent = _Agent(git_repo, [implement_and_rebase, lambda seen: None])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    branch = agent.seen[0]["head"]
    for commit in git_repo.git("rev-list", f"origin/main..{branch}").split():
        assert rel not in git_repo.git("show", "--name-only", "--format=", commit)
    assert "upstream.py" in git_repo.git("ls-tree", "--name-only", branch)
    assert "notes before rebase" in _control(git_repo, rel)


def test_git_disabled_launch_claims_no_preparation(git_repo, launch_env) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    toml = git_repo.coga_os / "coga.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + "\n[git]\nenabled = false\n", encoding="utf-8", newline="\n")

    def check(seen: dict) -> None:
        assert seen["head"] == "main"
        assert "did not prepare a branch or claim freshness" in seen["prompt"]
        assert "Git sync is disabled" in seen["prompt"]

    agent = _Agent(git_repo, [check])
    launch_env(agent)

    assert _launch(ref.id_slug).exit_code == 0
    assert git_repo.git("branch", "--list", "coga/*").strip() == ""


def test_first_sandbox_refusal_preserves_work_until_host_recovery_and_relaunch(
    git_repo, launch_env
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    (git_repo.root / "old.py").write_text("old\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "old.py")
    git_repo.git("commit", "-qm", "seed old.py")
    git_repo.git("push", "-q", "origin", "main")

    def refused_commit(seen: dict) -> None:
        # The agent edits, then its first commit is refused by the sandbox:
        # it stops with every change in place and does not bump.
        (git_repo.root / "staged.py").write_text("staged\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "staged.py")
        (git_repo.root / "old.py").unlink()
        (git_repo.root / "untracked.py").write_text("untracked\n", encoding="utf-8", newline="\n")
        _handoff(git_repo, ref, "sandbox refused the commit")

    agent = _Agent(git_repo, [refused_commit])
    launch_env(agent)

    _launch(ref.id_slug)

    branch = agent.seen[0]["head"]
    assert _head(git_repo) == branch  # the return refused over source dirt
    assert (git_repo.root / "staged.py").read_text(encoding="utf-8") == "staged\n"
    assert (git_repo.root / "untracked.py").read_text(encoding="utf-8") == "untracked\n"
    assert not (git_repo.root / "old.py").exists()
    # The ticket handoff was routine state: the refused return published it.
    assert "sandbox refused the commit" in _control(git_repo, rel)

    # Host recovery (coga/checkouts/sandbox-clone): clone the prepared branch,
    # transfer and verify the source changes, then clear only the copies.
    clone = _clone_checkout(git_repo, "sandbox")
    subprocess.run(["git", "-C", str(clone), "fetch", "-q", str(git_repo.root), branch], check=True)
    subprocess.run(["git", "-C", str(clone), "switch", "-q", "-c", branch, "FETCH_HEAD"], check=True)
    for name in ("staged.py", "untracked.py"):
        (clone / name).write_bytes((git_repo.root / name).read_bytes())
    (clone / "old.py").unlink()
    for name in ("staged.py", "untracked.py"):
        assert (clone / name).read_bytes() == (git_repo.root / name).read_bytes()
    git_repo.git("restore", "--staged", "--worktree", "--source=HEAD", "--", "staged.py", "old.py")
    (git_repo.root / "staged.py").unlink(missing_ok=True)
    (git_repo.root / "untracked.py").unlink()
    git_repo.git("restore", "--source=HEAD", "--worktree", "--", rel)
    git_repo.git("switch", "-q", "main")
    git_repo.git("merge", "-q", "--ff-only", "origin/main")
    assert _dirty(git_repo) == []
    replace_blackboard(
        ref.ticket_path,
        read_blackboard(ref.ticket_path).replace(
            f"branch: {branch}\n", f"branch: {branch}\nworktree: {clone}\n"
        ),
    )
    coga_git.sync_task_state(
        load_config(git_repo.coga_os), ref.path, message="record clone", strict=True
    )
    assert f"worktree: {clone}" in _control(git_repo, rel)

    def resumed(seen: dict) -> None:
        assert seen["head"] == "main"
        assert f"the recorded clone `{clone}`" in seen["prompt"]

    relaunch = _Agent(git_repo, [resumed])
    launch_env(relaunch)
    assert _launch(ref.id_slug).exit_code == 0
    assert relaunch.seen[0]["step"] == "1 (implement)"
    assert (clone / "staged.py").read_text(encoding="utf-8") == "staged\n"


# --- review regressions (PR #1068) ----------------------------------------------


def test_chat_rerun_reuses_its_own_branch_after_committing_and_returning(
    git_repo,
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        assert session is not None
        first = _run_recipe(git_repo, "--session", session.session)
        assert first.exit_code == 0, first.output
        (git_repo.root / "chat.py").write_text("work\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "chat.py")
        git_repo.git("commit", "-qm", "chat work")
        tip = git_repo.git("rev-parse", "HEAD").strip()
        git_repo.git("switch", "-q", "main")

        again = _run_recipe(git_repo, "--session", session.session)

        assert again.exit_code == 0, again.output
        assert f"reused: branch {session.branch}" in again.output
        assert _head(git_repo) == session.branch
        assert git_repo.git("rev-parse", "HEAD").strip() == tip


def test_chat_rerun_refuses_its_branch_moved_off_the_creation_commit(
    git_repo,
) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    with launch_module._orientation_checkout_guard(cfg):
        session = launch_module._CHAT_SESSION.get()
        assert session is not None
        first = _run_recipe(git_repo, "--session", session.session)
        assert first.exit_code == 0, first.output
        git_repo.git("switch", "-q", "main")
        tree = git_repo.git("rev-parse", "HEAD^{tree}").strip()
        foreign = git_repo.git("commit-tree", tree, "-m", "unrelated root").strip()
        git_repo.git("update-ref", f"refs/heads/{session.branch}", foreign)

        again = _run_recipe(git_repo, "--session", session.session)

        assert again.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, again.output
        assert "nothing was adopted" in again.output
        assert _head(git_repo) == "main"
        assert git_repo.git("rev-parse", session.branch).strip() == foreign


def test_unpushed_recorded_branch_is_reused_without_parsing_fetch_stderr(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    git_repo.git("branch", "feature/local-only")
    _write_dev_branch(git_repo, ref, "feature/local-only")
    coga_git.sync_task_state(load_config(git_repo.coga_os), ref.path, message="link")
    real_git = coga_git.run_git

    def localized(root, *args, **kwargs):  # type: ignore[no-untyped-def]
        # A non-English git reports a missing remote ref in its own words.
        if args[:1] == ("fetch",) and any("feature/local-only" in a for a in args):
            raise coga_git.GitError("Konnte Remote-Referenz nicht finden")
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(coga_git, "run_git", localized)
    agent = _Agent(git_repo, [lambda seen: None])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == 0, result.output
    assert agent.seen[0]["head"] == "feature/local-only"


def test_completed_reservation_receipts_never_resurrect_a_removed_branch(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")
    rel = _rel(git_repo, ref)
    root = coga_git.toplevel(git_repo.root)
    receipt = checkouts._receipt_path(root, rel)
    real_sync = coga_git.publish
    calls = {"n": 0}

    def flaky(cfg, path, message, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("guard") is not None and calls["n"] == 0:
            calls["n"] += 1
            raise coga_git.GitError("offline")
        return real_sync(cfg, path, message=message, **kwargs)

    monkeypatch.setattr("coga.git.publish", flaky)
    agent = _Agent(git_repo, [lambda seen: None, lambda seen: None])
    launch_env(agent)

    assert _launch(ref.id_slug).exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    assert json.loads(receipt.read_text(encoding="utf-8"))["stage"] == "created"
    assert _launch(ref.id_slug).exit_code == 0
    # The linked reservation landed and was reused: nothing is retained.
    assert not receipt.exists()

    # An older completed receipt left behind (e.g. by a control-only step)
    # must not bring back its name or base once `## Dev` loses the line.
    stale_base = git_repo.git("rev-parse", "main").strip()
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "task": rel, "root": str(root), "branch": "coga/stale-old",
        "oid": stale_base, "stage": "admitted",
    }), encoding="utf-8", newline="\n")
    other = _task(git_repo, "code/with-self-review", title="Fresh reservation")
    other_receipt = checkouts._receipt_path(root, _rel(git_repo, other))
    other_receipt.write_text(json.dumps({
        "task": _rel(git_repo, other), "root": str(root),
        "branch": "coga/stale-old", "oid": stale_base, "stage": "published",
    }), encoding="utf-8", newline="\n")

    result = _launch(other.id_slug)

    assert result.exit_code == 0, result.output
    assert agent.seen[-1]["head"].startswith("coga/fresh")
    assert git_repo.git("branch", "--list", "coga/stale-old").strip() == ""


@pytest.mark.parametrize("failure", ["baseline-oserror", "receipt", "head"])
def test_failures_after_the_switch_report_that_launch_switched(
    git_repo, launch_env, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:  # type: ignore[no-untyped-def]
    ref = _task(git_repo, "code/with-self-review")

    def boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        if failure == "baseline-oserror":
            raise OSError("read-only metadata")
        if failure == "receipt":
            raise checkouts.CheckoutPreparationError("reservation", "receipt vanished")
        raise coga_git.GitError("rev-parse failed")

    if failure == "baseline-oserror":
        monkeypatch.setattr("coga.git.record_projected_baseline", boom)
    elif failure == "receipt":
        monkeypatch.setattr(checkouts, "_discard_receipt", boom)
    else:
        real_symbolic = coga_git.symbolic_head

        def flaky_symbolic(root):  # type: ignore[no-untyped-def]
            head = real_symbolic(root)
            if head and head.startswith("coga/"):
                boom()
            return head

        monkeypatch.setattr(checkouts.git, "symbolic_head", flaky_symbolic)
    agent = _Agent(git_repo, [])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
    assert "left where preparation stopped" in result.output
    assert agent.seen == []
    assert _head(git_repo).startswith("coga/")


def _make_stranded(git_repo, ref: TaskRef) -> None:  # type: ignore[no-untyped-def]
    git_repo.git("switch", "-q", "-c", "feature/stranded")
    ref.ticket_path.write_text(ref.ticket_path.read_text(encoding="utf-8") + "\nbranch-only intent\n", encoding="utf-8", newline="\n")
    git_repo.git("commit", "-qam", "strand the ticket")
    git_repo.git("switch", "-q", "main")
    _write_dev_branch(git_repo, ref, "feature/stranded")


@pytest.mark.parametrize("refusal", ["missing", "stranded", "held"])
def test_refused_preparation_records_no_launch(
    git_repo, launch_env, refusal: str
) -> None:  # type: ignore[no-untyped-def]
    from coga.logfile import log_path

    ref = _task(git_repo, "code/with-self-review")
    if refusal == "missing":
        _write_dev_branch(git_repo, ref, "feature/gone")
    elif refusal == "stranded":
        _make_stranded(git_repo, ref)
    else:
        git_repo.git("branch", "feature/held")
        git_repo.git("worktree", "add", "-q", str(git_repo.root.parent / "held"), "feature/held")
        _write_dev_branch(git_repo, ref, "feature/held")
    cfg = load_config(git_repo.coga_os)
    coga_git.sync_task_state(cfg, ref.path, message="link")
    agent = _Agent(git_repo, [])
    launch_env(agent)

    result = _launch(ref.id_slug)

    assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, result.output
    assert agent.seen == [] and _head(git_repo) == "main"
    assert "launched (operator=" not in _control(git_repo, "coga/log.md")
    assert "launched (operator=" not in log_path(cfg).read_text(encoding="utf-8")


def test_ref_helpers_use_the_shared_git_runner(git_repo, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    monkeypatch.setenv("PATH", str(git_repo.root / "no-git-here"))
    with pytest.raises(coga_git.GitError, match="not found"):
        checkouts._ref_oid(git_repo.root, "HEAD")
    with pytest.raises(coga_git.GitError, match="not found"):
        checkouts._require_valid_branch(cfg, git_repo.root, "feature/x", "linkage")


def _plan(policy, **kwargs):  # type: ignore[no-untyped-def]
    from coga.checkout_policy import CheckoutPolicy

    base = dict(
        policy=CheckoutPolicy(*policy), root=Path("/repo"), rel="coga/tasks/t.md",
        control_oid="0" * 40, ticket_bytes=b"", action="stay",
    )
    base.update(kwargs)
    return checkouts.TicketCheckoutPlan(**base)


def test_notice_names_the_step_from_the_policy_field(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    shipped = select_checkout_policy(cfg, _frozen("code/with-review", "open-pr"))
    assert shipped.step == "open-pr"
    plan = _plan(("control", "no quoted step name here", "design"))
    assert "for step `design`" in checkouts.ticket_notice(cfg, plan).summary


def test_notice_asks_to_push_only_when_there_is_a_branch(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    stays = [
        _plan(("control", "r", "open-pr")),
        _plan(("reuse-required", "r", "self-qa"), notes=("Already satisfied",)),
        _plan(("manual", "custom", "build")),
    ]
    for plan in stays:
        returns = checkouts.ticket_notice(cfg, plan).return_owner
        assert "Push your branch" not in returns
        assert "Run `coga bump` last." in returns
    switched = _plan(
        ("create-or-reuse", "r", "implement"), action="switch",
        branch="coga/t-1", branch_oid="1" * 40, outcome="created",
    )
    assert "Push your branch and run `coga bump` last." in (
        checkouts.ticket_notice(cfg, switched).return_owner
    )
