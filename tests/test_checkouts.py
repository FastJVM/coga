"""Shared checkout preparation: policy, ticket launch, and direct chat."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import checkouts
from coga import git as coga_git
from coga import launch as launch_module
from coga.checkout_policy import select_checkout_policy
from coga.cli import app
from coga.compose import CheckoutNotice, compose_prompt_report
from coga.config import load_config
from coga.create import create_task
from coga.paths import bootstrap_workflow_path
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
    local.write_text(shipped.read_text() + "\nLocal tweak.\n")
    policy = select_checkout_policy(cfg, ticket)
    assert policy.kind == "manual"
    assert "differs from the shipped copy" in policy.reason


def test_policy_reads_only_the_consumed_inline_section(git_repo) -> None:  # type: ignore[no-untyped-def]
    cfg = load_config(git_repo.coga_os)
    shipped = bootstrap_workflow_path(cfg, "code/with-review").read_text()
    local = git_repo.coga_os / "workflows" / "code" / "with-review.md"
    local.parent.mkdir(parents=True)
    local.write_text(shipped.replace("## open-pr\n", "## open-pr\n\nLocal framing.\n"))
    peer = _frozen("code/with-review", "peer-review")
    assert select_checkout_policy(cfg, peer).kind == "reuse-required"
    local.write_text(shipped.replace("## peer-review\n", "## peer-review\n\nChanged.\n"))
    policy = select_checkout_policy(cfg, peer)
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
    return str(ref.ticket_path.relative_to(git_repo.root))


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
            cwd=git_repo.coga_os, env=env, capture_output=True, text=True,
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
        assert ref.ticket_path.read_text() == _control(git_repo, rel)
        assert f"switched to branch `{seen['head']}`" in seen["prompt"]
        assert "## Checkout (runtime)" in seen["prompt"]
        (git_repo.root / "feature.py").write_text("print('work')\n")
        git_repo.git("add", "feature.py")
        git_repo.git("commit", "-m", "Implement feature")
        _handoff(git_repo, ref, "implemented")
        _bump(git_repo, ref.id_slug)

    def self_qa(seen: dict) -> None:
        assert seen["head"] == branch[0]
        assert "implemented" in ref.ticket_path.read_text()
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
    other_ticket.write_text(other_ticket.read_text() + "\nnote from elsewhere\n")
    subprocess.run(["git", "-C", str(other), "commit", "-qam", "edit"], check=True)
    subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "main"], check=True)

    def resumed(seen: dict) -> None:
        assert seen["head"] == "feature/old"
        text = ref.ticket_path.read_text()
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
        theirs.write_text(theirs.read_text() + "\ncompeting edit\n")
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
    assert "local handoff" in ref.ticket_path.read_text()
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
    (git_repo.root / "remote.py").write_text("x\n")
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
    (git_repo.root / "ahead.py").write_text("x\n")
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
    ref.ticket_path.write_text(ref.ticket_path.read_text() + "\nbranch-only intent\n")
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
    real_sync = coga_git.sync_task_state
    calls = {"n": 0}

    def flaky(cfg, path, *, message, **kwargs):  # type: ignore[no-untyped-def]
        if "— branch " in message and calls["n"] == 0:
            calls["n"] += 1
            raise coga_git.GitError("offline")
        return real_sync(cfg, path, message=message, **kwargs)

    monkeypatch.setattr("coga.git.sync_task_state", flaky)
    agent = _Agent(git_repo, [lambda seen: None])
    launch_env(agent)

    first = _launch(ref.id_slug)

    assert first.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE, first.output
    assert "linkage publication" in first.output
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

        (git_repo.root / "edit.py").write_text("dirty\n")
        context = git_repo.coga_os / "notes.md"
        context.write_text("unfinished\n")
        again = _run_recipe(git_repo, "--session", session.session)
        assert again.exit_code == 0, again.output
        assert "reused" in again.output
        assert (git_repo.root / "edit.py").read_text() == "dirty\n"

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
        (git_repo.root / "wip.py").write_text("unsaved\n")
        result = _run_recipe(git_repo, "--session", session.session)
        assert result.exit_code == coga_git.RETRY_WITHOUT_SWEEP_EXIT_CODE
        assert "wip.py" in result.output
        assert _head(git_repo) == "main"
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
    assert _head(git_repo) == "main"


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
        f"pathlib.Path({str(witness)!r}).write_text(head)\n"
    )
    coga_git.sync_task_state(cfg, task_dir, message="Seed scripted task")
    agent = _Agent(git_repo, [lambda seen: None])
    launch_env(agent)

    result = _launch(created["slug"])

    assert result.exit_code == 0, result.output
    assert witness.read_text().strip() == "main"
    assert agent.seen[0]["head"].startswith("coga/")
    assert agent.seen[0]["dirty"] == [str((task_dir / "ticket.md").relative_to(git_repo.root))]


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
        (git_repo.root / "feature.py").write_text("work\n")
        git_repo.git("add", "feature.py")
        git_repo.git("commit", "-qm", "Implement")
        _handoff(git_repo, ref, "notes before rebase")
        # Control moves under the session.
        subprocess.run(["git", "-C", str(other), "pull", "-q", "--ff-only"], check=True)
        (other / "upstream.py").write_text("upstream\n")
        subprocess.run(["git", "-C", str(other), "add", "upstream.py"], check=True)
        subprocess.run(["git", "-C", str(other), "commit", "-qm", "upstream"], check=True)
        subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "main"], check=True)
        # dev/checkouts: copy the ticket out, restore it from HEAD, rebase,
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
    toml.write_text(toml.read_text() + "\n[git]\nenabled = false\n")

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
    (git_repo.root / "old.py").write_text("old\n")
    git_repo.git("add", "old.py")
    git_repo.git("commit", "-qm", "seed old.py")
    git_repo.git("push", "-q", "origin", "main")

    def refused_commit(seen: dict) -> None:
        # The agent edits, then its first commit is refused by the sandbox:
        # it stops with every change in place and does not bump.
        (git_repo.root / "staged.py").write_text("staged\n")
        git_repo.git("add", "staged.py")
        (git_repo.root / "old.py").unlink()
        (git_repo.root / "untracked.py").write_text("untracked\n")
        _handoff(git_repo, ref, "sandbox refused the commit")

    agent = _Agent(git_repo, [refused_commit])
    launch_env(agent)

    _launch(ref.id_slug)

    branch = agent.seen[0]["head"]
    assert _head(git_repo) == branch  # the return refused over source dirt
    assert (git_repo.root / "staged.py").read_text() == "staged\n"
    assert (git_repo.root / "untracked.py").read_text() == "untracked\n"
    assert not (git_repo.root / "old.py").exists()
    # The ticket handoff was routine state: the refused return published it.
    assert "sandbox refused the commit" in _control(git_repo, rel)

    # Host recovery (dev/checkouts/sandbox-clone): clone the prepared branch,
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
    assert (clone / "staged.py").read_text() == "staged\n"
