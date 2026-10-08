from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from textwrap import dedent

import pytest

from coga.blackboard import append_blocker, resolve_open_blockers
from coga.create import create_task
from coga.slugify import slugify
from coga.compose import (
    SESSION_CONDUCT_RESOURCES,
    ComposeError,
    compose_prompt,
    compose_prompt_report,
    write_prompt_file,
)
from conftest import hold_by_agent, hold_by_owner
from coga.config import load_config
from coga.tasks import list_tasks, read_ticket, resolve_bootstrap
from coga.taskfile import replace_blackboard
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_workflow_less_task(
    repo: Path, *, title: str, status: str = "active"
) -> str:
    """Write a workflow-less task directly to disk. `create_task` refuses to
    create a workflow-less non-draft task now, but compose handles a
    workflow-less ticket fine, so on-disk construction keeps these
    compose-only tests focused on a minimal (no workflow-step layer) prompt."""
    slug = slugify(title)
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    # Single-file format: body + fence + blackboard region, no sibling
    # blackboard.md / log.md (history lives in the repo-global log).
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        title: {title}
        status: {status}
        owner: marc
        agent: claude
        workflow: null
        ---

        ## Description

        ## Context

        <!-- coga:blackboard -->

        # Blackboard
    """).lstrip())
    return slug


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "coga"

    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
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
        company / "workflows" / "code" / "with-review.md",
        """
        ---
        name: code/with-review
        description: Standard.
        steps:
          - name: implement
            skills:
              - infra/testing-conventions
            assignee: agent
          - name: pr
            assignee: agent
        ---

        ## pr
        Open a PR. Push branch first.
        """,
    )
    _write(
        company / "skills" / "infra" / "testing-conventions" / "SKILL.md",
        "---\nname: infra/testing-conventions\n---\n\nRun tests with pytest.\n",
    )
    _write(
        company / "contexts" / "email" / "payment-flow" / "SKILL.md",
        "---\nname: email/payment-flow\n---\n\nStripe retries on 429.\n",
    )
    _write(company / "context.md", "Email tool is YC-backed.\n")
    return company


def test_compose_includes_all_sections(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    # Header
    assert "Coga task — fix-retry-logic" in prompt
    assert "Task directory: coga/tasks/fix-retry-logic" in prompt
    # Base prompt
    assert "You are an agent working on a ticket inside Coga" in prompt
    # Session conduct — the attended default when no context is given
    assert "Session conduct — attended" in prompt
    # Repo context
    assert "Email tool is YC-backed" in prompt
    # Ticket context
    assert "Stripe retries on 429" in prompt
    # Step skill
    assert "Run tests with pytest" in prompt
    assert "Current step: implement" in prompt
    # Blackboard present
    assert "Blackboard" in prompt


def _conduct_step_task(repo: Path) -> tuple[object, object, object]:
    """A full ordinary step prompt on a shipped inline peer-review step.

    Exercises the stock workflow rather than the fixture's neutral local one,
    so a later-composed shipped layer cannot contradict the selected conduct
    unnoticed.
    """
    (repo / "workflows" / "code" / "with-review.md").unlink()
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "2 (peer-review)"
    ticket.write(ref.ticket_path)
    return cfg, ref, read_ticket(ref)


# The clauses each launch context must carry, and the opposite contract it must
# not. Selection replaced precedence: instead of ranking a rule against its
# inverse, the guard is that exactly one conduct block is composed and it is
# the right one.
_ATTENDED_CLAUSES = (
    "Session conduct — attended",
    "A human launched this session and is present in the REPL.",
    "ask the human directly and wait for their answer",
    "`coga block` is for one case only: the human explicitly asks you to park"
    " or block the ticket",
    "State a one- or two-sentence plan and its tradeoff, then let the human"
    " confirm or redirect before you write code.",
)
_QUEUE_CLAUSES = (
    "the TTY is transport, not evidence that a human is waiting",
    "State a concise plan and its tradeoff, then continue.",
    "Do not ask for plan confirmation or end a turn waiting for permission",
    "as the terminal action",
)

CONDUCT_CASES = {
    "attended": (_ATTENDED_CLAUSES, _QUEUE_CLAUSES),
    "megalaunch": (
        _QUEUE_CLAUSES
        + (
            "Session conduct — megalaunch queue",
            "one step in a sequential `coga megalaunch` queue",
            "include that task's exact path-qualified slug in `--reason`",
            "Existing blocker-resolution exception",
        ),
        _ATTENDED_CLAUSES,
    ),
    "recurring": (
        _QUEUE_CLAUSES
        + (
            "Session conduct — recurring queue",
            "one task in a sequential automated queue (a `coga recurring`"
            " sweep)",
            "A stateless `bootstrap/<name>` command ticket has no task"
            " lifecycle to bump, mark, or block.",
            "`coga slack --task bootstrap/<name> ...` posts its roll-up",
        ),
        _ATTENDED_CLAUSES,
    ),
}


@pytest.mark.parametrize("launch_context", sorted(CONDUCT_CASES))
def test_compose_selects_exactly_one_session_conduct_layer(
    repo: Path, launch_context: str
) -> None:
    """Each launch context composes its own conduct resource, once."""
    cfg, ref, ticket = _conduct_step_task(repo)
    composition = compose_prompt_report(
        cfg, ref, ticket, launch_context=launch_context
    )

    conduct = [
        layer for layer in composition.layers if layer.layer == "session_conduct"
    ]
    assert len(conduct) == 1
    assert conduct[0].ref == SESSION_CONDUCT_RESOURCES[launch_context]
    # Conduct is read before any task material, so it sits directly after the
    # neutral base prompt.
    layer_names = [layer.layer for layer in composition.layers]
    assert layer_names[:3] == ["header", "base_prompt", "session_conduct"]

    normalized = " ".join(composition.prompt.split())
    present, absent = CONDUCT_CASES[launch_context]
    for clause in present:
        assert clause in normalized, clause
    for clause in absent:
        assert clause not in normalized, clause
    # The composed step skill is still there — conduct did not displace it.
    assert "Current step: peer-review" in normalized


@pytest.mark.parametrize("launch_context", sorted(CONDUCT_CASES))
def test_compose_conduct_carries_no_precedence_prose(
    repo: Path, launch_context: str
) -> None:
    """Nothing ranks one conduct block against another, because there is only
    one. The base prompt is neutral and no resource claims to override."""
    cfg, ref, ticket = _conduct_step_task(repo)
    normalized = " ".join(
        compose_prompt(cfg, ref, ticket, launch_context=launch_context).split()
    )

    assert "This launch is attended — ask and wait." not in normalized
    assert "authoritative over any generic instruction" not in normalized
    assert (
        "Only an execution directive appended *after* the task layers"
        not in normalized
    )
    assert "overrides the attended ask-and-wait default" not in normalized
    assert "This queue directive overrides" not in normalized
    # No stray layer steers the agent to block merely because input is needed.
    assert "Ask or block when uncertain" not in normalized
    assert "call `coga block` with a specific ask" not in normalized
    assert "that's `coga block` — never a quiet exit" not in normalized
    assert (
        "Use `coga block` when progress needs a concrete decision"
        not in normalized
    )
    assert "blackboard and `coga block` instead" not in normalized
    # The base prompt defers to the selected layer instead of deciding.
    assert (
        "The `Session conduct` layer in this prompt is what decides whether"
        " input is available" in normalized
    )


def test_compose_rejects_an_unknown_launch_context(repo: Path) -> None:
    """A bad selector fails loud rather than composing no conduct at all."""
    cfg, ref, ticket = _conduct_step_task(repo)
    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket, launch_context="unattended")
    assert "unattended" in str(exc.value)


def test_queue_conduct_resources_share_their_invariants() -> None:
    """The two queue resources are deliberately complete, not a shared
    fragment plus tails — so pin the wording they must agree on."""
    texts = {
        context: (
            files("coga.resources")
            .joinpath(SESSION_CONDUCT_RESOURCES[context])
            .read_text()
        )
        for context in ("megalaunch", "recurring")
    }
    for context, text in texts.items():
        normalized = " ".join(text.split())
        for clause in _QUEUE_CLAUSES:
            assert clause in normalized, (context, clause)
        assert "`coga block --task <slug> --reason" in normalized
        assert "`coga bump`" in normalized
        assert "does not release the queue" in normalized


_PACKAGED_PROMPT_LAYERS = (
    "prompt.md",
    "prompt-blocker-resolution.md",
    *SESSION_CONDUCT_RESOURCES.values(),
)


@pytest.mark.parametrize("resource", _PACKAGED_PROMPT_LAYERS)
def test_packaged_prompt_layers_carry_no_coga_source_rules(resource: str) -> None:
    """Every repo composes these layers from the installed package, so a rule
    about Coga's own source tree belongs in this repo's `coga/context.md`."""
    text = files("coga.resources").joinpath(resource).read_text()

    for marker in (
        "src/coga",
        "coga_edge",
        "runner.RECIPES",
        "microkernel",
        "When changing Coga itself",
    ):
        assert marker not in text, (resource, marker)


def test_coga_repo_context_carries_the_minimal_core_boundary() -> None:
    """The rule moved out of `prompt.md` still reaches Coga's own tickets."""
    repo_root = Path(__file__).resolve().parents[1]
    text = " ".join((repo_root / "coga" / "context.md").read_text().split())

    assert "## Keep Coga small and legible" in text
    assert "shared infrastructure with at least two real consumers" in text
    assert "registered in `runner.RECIPES` behind" in text
    assert "reviewed, co-versioned command contracts" in text
    assert "Python logic or inability to use an alias does not establish a core home" in text
    assert "argv rewrite in `[aliases]`" in text
    assert "When changing Coga itself" not in text


@pytest.mark.parametrize(
    "workflow_name",
    [
        "code/with-review",
        "code/with-self-review",
        "code/design-then-implement",
        "docs/with-review",
    ],
)
def test_bundled_review_step_composes_address_pr_comments_skill(
    repo: Path,
    workflow_name: str,
) -> None:
    (repo / "workflows" / "code" / "with-review.md").unlink(missing_ok=True)
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title=f"Assist {workflow_name}",
        workflow_name=workflow_name,
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    steps = ticket.workflow["steps"]
    review_index = next(
        index for index, step in enumerate(steps, start=1)
        if step["name"] == "review"
    )
    review_step = steps[review_index - 1]

    assert review_step["skills"] == ["code/address-pr-comments"]

    ticket.frontmatter["step"] = f"{review_index} (review)"
    hold_by_owner(ticket)
    ticket.write(ref.ticket_path)
    prompt = compose_prompt(cfg, ref, read_ticket(ref))

    assert "Current step: review (skill: code/address-pr-comments)" in prompt
    assert "Address PR review comments" in prompt
    assert "Do not run `coga bump`" in prompt
    assert "A pure prose edit does not require pytest" in prompt


def test_created_ticket_implement_prompt_includes_code_citation_guidance(
    repo: Path,
) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Implement directly from a raw ticket",
        workflow_name="code/with-self-review",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    assert "Current step: implement (skill: code/implement)" in prompt
    assert "Skill — bootstrap/ticket" not in prompt
    assert "Skill — code/design" not in prompt
    assert "Cite module plus symbol, never a bare line number." in prompt


def test_design_workflow_routes_a_cold_peer_review_before_owner_approval(
    repo: Path,
) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Design a retry policy",
        workflow_name="code/design-then-implement",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    steps = ticket.workflow["steps"]

    assert [step["name"] for step in steps[:3]] == [
        "design",
        "evaluate-design",
        "review-design",
    ]
    assert steps[1]["assignee"] == "other-agent"
    assert steps[1]["skills"] == ["code/review-design"]
    assert steps[2]["assignee"] == "owner"

    ticket.frontmatter["step"] = "2 (evaluate-design)"
    hold_by_agent(ticket, "other-agent")
    ticket.write(ref.ticket_path)
    prompt = compose_prompt(cfg, ref, read_ticket(ref))

    assert "Current step: evaluate-design (skill: code/review-design)" in prompt
    assert "Review the design cold" in prompt
    assert "## Evaluator review" in prompt
    assert "The next `review-design` step is the owner gate" in prompt


def test_design_prompts_remain_accurate_for_pre_evaluator_snapshots(
    repo: Path,
) -> None:
    """Skills and inline step prose stay live after workflow steps freeze."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Legacy design snapshot",
        workflow_name="code/design-then-implement",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.frontmatter["workflow"]["steps"] = [
        step
        for step in ticket.workflow["steps"]
        if step["name"] != "evaluate-design"
    ]
    ticket.write(ref.ticket_path)

    design_prompt = compose_prompt(cfg, ref, read_ticket(ref))
    assert "advances the workflow to its next frozen step" in design_prompt
    assert "advances the workflow to `evaluate-design`" not in design_prompt

    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "2 (review-design)"
    hold_by_owner(ticket)
    ticket.write(ref.ticket_path)
    owner_prompt = " ".join(
        compose_prompt(cfg, ref, read_ticket(ref)).split()
    )

    assert "If an `## Evaluator review` section is present" in owner_prompt
    assert "the cold peer's `## Evaluator review`" not in owner_prompt


@pytest.mark.parametrize(
    ("workflow_name", "step", "heading", "legacy_direction"),
    [
        (
            "code/with-self-review",
            "2 (self-qa)",
            "Self-QA the diff",
            "`coga block` — something is off",
        ),
        (
            "code/with-review",
            "3 (open-pr)",
            "Push and open the PR",
            "earlier-step gap — `coga block` with a one-line reason",
        ),
        (
            "direct/body",
            "1 (execute)",
            "Run the ticket body directly",
            "If you are blocked before completion, `coga block` with a reason",
        ),
    ],
)
def test_stock_step_prompt_escalates_per_launch_mode(
    repo: Path,
    workflow_name: str,
    step: str,
    heading: str,
    legacy_direction: str,
) -> None:
    """Other shipped agent steps do not append a generic block command."""
    if workflow_name == "code/with-review":
        (repo / "workflows" / "code" / "with-review.md").unlink()
    elif workflow_name == "direct/body":
        resources = files("coga.resources").joinpath("templates/coga")
        _write(
            repo / "workflows" / "direct" / "body.md",
            resources.joinpath("workflows/direct/body.md").read_text(),
        )
        _write(
            repo / "skills" / "direct" / "body" / "SKILL.md",
            resources.joinpath("skills/direct/body/SKILL.md").read_text(),
        )
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Check stock escalation",
        workflow_name=workflow_name,
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = step
    ticket.write(ref.ticket_path)

    normalized_prompt = " ".join(
        compose_prompt(cfg, ref, read_ticket(ref)).split()
    )

    assert heading in normalized_prompt
    assert "escalate per your launch mode" in normalized_prompt
    assert legacy_direction not in normalized_prompt


def test_compose_browser_automation_bootstrap_uses_bundled_router_skill(
    repo: Path,
) -> None:
    """The browser entry point composes package-backed orchestration without
    creating a standing task or loading the lower-level runner prematurely."""
    _write(
        repo / "contexts" / "browser" / "api-first" / "SKILL.md",
        "---\nname: browser/api-first\n---\n\nPrefer the API marker.\n",
    )
    cfg = load_config(repo)
    ref = resolve_bootstrap(cfg, "browser-automation")
    ticket = read_ticket(ref)

    composition = compose_prompt_report(cfg, ref, ticket)
    prompt = composition.prompt
    normalized_prompt = " ".join(prompt.split())
    layers = {(layer.layer, layer.ref) for layer in composition.layers}

    assert ticket.status == ""
    assert ticket.workflow is None
    assert ticket.step is None
    assert ("ticket_context", "browser/api-first") in layers
    assert ("top_level_skill", "browser/build-automation") in layers
    assert "Coga task — bootstrap/browser-automation" in prompt
    assert "Prefer the API marker." in prompt
    assert "Skill: browser/build-automation" in prompt
    assert "The skill does not drive the browser itself" in normalized_prompt
    assert "# Playwright CLI Skill" not in prompt
    assert list_tasks(cfg) == []


def test_compose_header_uses_resolved_nested_task_directory(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Fix retry logic")
    top = repo / "tasks" / "fix-retry-logic"
    nested = repo / "tasks" / "auto" / "fix-retry-logic"
    nested.parent.mkdir()
    top.rename(nested)

    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    # A nested task is identified by its path under `tasks/`.
    assert "Coga task — auto/fix-retry-logic" in prompt
    assert "Task directory: coga/tasks/auto/fix-retry-logic" in prompt


def test_base_prompt_teaches_exit_after_bump(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="code/with-review",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    assert "Run `bump` as the *last* thing in the current step" in prompt
    assert "After bumping, exit cleanly" in prompt
    assert "One step, one session" in prompt
    assert "API/manual sessions don't chain" in prompt
    assert "coga mark done" in prompt
    assert "Never stop silently" in prompt
    # Supervisor respawn/teardown mechanics are reference the agent can't act
    # on; they live in coga/launch now (loaded only when a ticket
    # attaches it), not in every base prompt. This ticket has no contexts, so
    # those phrases are absent here.
    assert "How the supervisor chains steps is in `coga/launch`" in prompt
    assert "respawns the next agent step" not in prompt
    assert "clean prompt scope" not in prompt
    # Old continue-in-same-session rule must be gone.
    assert "After bumping, inspect the new state" not in prompt
    assert "continue that next step in this same session" not in prompt
    assert "On the final step, `coga bump` marks" in prompt
    assert "the task `done`" in prompt
    # Coga's own minimal-core boundary is this repo's `coga/context.md`, not
    # the shipped base prompt every other repo composes.
    assert "Keep Coga small and legible" not in prompt
    assert "registered in `runner.RECIPES` behind" not in prompt
    # `coga bump` exposes human-only `--to`/`--backward`; the prompt says so.
    assert "`--to` and `--backward`" in prompt
    assert "are human-only" in prompt


def test_compose_prompt_report_tracks_layers_and_refs(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)

    composition = compose_prompt_report(cfg, ref, ticket)
    assert composition.prompt == compose_prompt(cfg, ref, ticket)
    assert composition.byte_count > 0
    assert composition.approx_tokens > 0

    layers = {(layer.layer, layer.ref): layer for layer in composition.layers}
    assert ("ticket_context", "email/payment-flow") in layers
    assert ("workflow_skill", "infra/testing-conventions") in layers
    assert ("blackboard", "ticket.md##blackboard") in layers
    assert layers[("ticket_context", "email/payment-flow")].approx_tokens > 0


@pytest.mark.parametrize("archive_repetitions", [1, 3000])
@pytest.mark.parametrize("file_form", [False, True])
def test_compose_omits_superseded_designs_without_rewriting_ticket(
    repo: Path, archive_repetitions: int, file_form: bool
) -> None:
    cfg = load_config(repo)
    slug = _write_workflow_less_task(repo, title="Archived design")
    if file_form:
        directory = repo / "tasks" / slug
        (directory / "ticket.md").rename(repo / "tasks" / f"{slug}.md")
        directory.rmdir()
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.body = ticket.body.replace(
        "## Description", "## Description\n\nCurrent requirements remain binding."
    ).replace("## Context", "## Context\n\nCurrent decision and reason.")
    ticket.write(ref.ticket_path)
    live_before = "\n## Notes\n\nLive reasoning before the archive.\n\n"
    archive = (
        "## Superseded designs\n\n### 2026-09-18 — Abandoned plan\n\n"
        "Superseded by: Current plan\n\nReason: Simpler implementation\n\n"
        "#### Prior requirements\n\n"
        + "ABANDONED-DESIGN-DETAIL — " * archive_repetitions
        + "\n\n"
    )
    live_after = dedent(
        """\
        ## Dev
        branch: feature/current
        worktree: /tmp/current
        pr: https://github.com/acme/repo/pull/1

        ## Blockers
        - [ ] [2026-09-18 12:00] [human:marc] id=current Current open question

        ## Next steps
        Live reasoning after the archive.
        """
    )
    replace_blackboard(ref.ticket_path, live_before + archive + live_after)
    before = ref.ticket_path.read_bytes()
    ticket = read_ticket(ref)
    original_body = ticket.body

    composition = compose_prompt_report(cfg, ref, ticket)
    prompt = compose_prompt(cfg, ref, ticket)
    blackboard = next(layer for layer in composition.layers if layer.layer == "blackboard")

    assert prompt == composition.prompt
    assert "ABANDONED-DESIGN-DETAIL" not in prompt
    assert "2026-09-18 — Abandoned plan" not in prompt
    assert "Current requirements remain binding." in prompt
    assert "Current decision and reason." in prompt
    assert live_before + live_after in blackboard.text
    assert "Current open question" in prompt
    assert "Resolve the open blocker first" in prompt
    assert str(ref.ticket_path) in blackboard.text
    assert "`## Superseded designs`" in blackboard.text
    assert "omitted" in blackboard.text
    assert blackboard.byte_count == len(blackboard.rendered.encode())
    assert blackboard.char_count == len(blackboard.rendered)
    assert blackboard.approx_tokens == (blackboard.char_count + 3) // 4
    assert blackboard.byte_count < 1200
    assert composition.byte_count == len(prompt.encode())
    assert ref.ticket_path.read_bytes() == before
    assert ticket.body == original_body


@pytest.mark.parametrize(
    "example",
    [
        "## Superseded designs (notes)\n",
        "## superseded designs\n",
        "## Superseded designs ##\n",
        "##  Superseded designs\n",
        "### Superseded designs\n",
        "# Superseded designs\n",
        "Mention `## Superseded designs` in prose.\n",
        "> ## Superseded designs\n",
        "    ## Superseded designs\n",
        " ## Superseded designs\n",
        "```markdown\n## Superseded designs\nEXAMPLE\n```\n",
        "~~~markdown\n## Superseded designs\nEXAMPLE\n~~~\n",
        "````markdown\n```\n## Superseded designs\nEXAMPLE\n```\n````\n",
        "   ~~~markdown\n## Superseded designs\nEXAMPLE\n   ~~~~\n",
        "```markdown\n~~~\n## Superseded designs\nEXAMPLE\n```\n",
        "```markdown\n```not-a-closer\n## Superseded designs\nEXAMPLE\n```\n",
        "```markdown\n## Superseded designs\nUnclosed example.\n",
    ],
)
def test_compose_keeps_similar_headings_and_archive_examples(
    repo: Path, example: str
) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Heading examples")
    ref = list_tasks(cfg)[0]
    text = "\n## Notes\n\n" + example + "Live content.\n"
    replace_blackboard(ref.ticket_path, text)

    report = compose_prompt_report(cfg, ref, read_ticket(ref))
    blackboard = next(layer for layer in report.layers if layer.layer == "blackboard")

    assert blackboard.text == text


@pytest.mark.parametrize("ending", ["", "\n", " \t\r\n"])
def test_compose_archive_only_blackboard_keeps_a_pointer(repo: Path, ending: str) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="History only")
    ref = list_tasks(cfg)[0]
    replace_blackboard(ref.ticket_path, "\n## Superseded designs" + ending)
    before = ref.ticket_path.read_bytes()

    report = compose_prompt_report(cfg, ref, read_ticket(ref))
    blackboard = next(layer for layer in report.layers if layer.layer == "blackboard")

    assert str(ref.ticket_path) in blackboard.text
    assert "`## Superseded designs`" in blackboard.text
    assert "omitted" in blackboard.text
    assert ref.ticket_path.read_bytes() == before


def test_compose_omits_duplicate_archives_and_fenced_historical_headings(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Repeated archive")
    ref = list_tasks(cfg)[0]
    replace_blackboard(ref.ticket_path, "\n" + dedent(
        """\
        ## Superseded designs
        ### 2026-09-17 — First discarded plan
        #### Old requirements
        ````markdown
        ```
        ## Dev
        branch: abandoned
        ```
        ````
        - [ ] [2026-09-17 12:00] [human:marc] id=old Abandoned open question

        ## Notes
        Live middle note.

        ## Superseded designs
        ### 2026-09-18 — Second discarded plan
        ~~~markdown
        ## Notes
        Abandoned fenced note.
        ~~~~
        Abandoned trailing note.

        # Current handoff
        Live final note.
        """
    ))
    before = ref.ticket_path.read_bytes()

    report = compose_prompt_report(cfg, ref, read_ticket(ref))

    assert "discarded plan" not in report.prompt
    assert "Abandoned" not in report.prompt
    assert "branch: abandoned" not in report.prompt
    assert "Resolve the open blocker first" not in report.prompt
    assert "Live middle note." in report.prompt
    assert "Live final note." in report.prompt
    blackboard = next(layer for layer in report.layers if layer.layer == "blackboard")
    assert blackboard.text.count(str(ref.ticket_path)) == 1
    assert ref.ticket_path.read_bytes() == before


def test_compose_defaults_to_attended_session_conduct(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Agent task")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Session conduct — attended" in prompt


def test_compose_open_blockers_add_resolution_preamble(repo: Path) -> None:
    """An Agent ticket with open asks composes the resolve-or-re-block
    preamble, listing each ask verbatim (stale/junk ones included)."""
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Blocked work")
    ref = list_tasks(cfg)[0]
    append_blocker(ref.ticket_path, "agent:claude", "which retry ceiling?")
    append_blocker(ref.ticket_path, "human:marc", "test")

    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    assert "Resolve the open blocker first" in prompt
    assert "which retry ceiling?" in prompt
    assert "test" in prompt
    assert f"coga unblock {ref.id_slug} --answer" in prompt
    assert f"coga block --task {ref.id_slug} --reason" in prompt
    # Leading: the preamble sits before the repo context layer.
    assert prompt.index("Resolve the open blocker first") < prompt.index(
        "Email tool is YC-backed"
    )

    composition = compose_prompt_report(cfg, ref, ticket)
    assert any(layer.layer == "blocker_preamble" for layer in composition.layers)


def test_compose_resolved_blockers_compose_no_preamble(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Answered work")
    ref = list_tasks(cfg)[0]
    append_blocker(ref.ticket_path, "agent:claude", "which retry ceiling?")
    resolve_open_blockers(ref.ticket_path, "human:marc", "cap at 5 minutes")

    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    assert "Resolve the open blocker first" not in prompt


def test_compose_inline_step_instructions(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="T",
        workflow_name="code/with-review",
        contexts=[],
        owner=None,
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    # Advance to step 2 (pr) — has inline instructions, no skill
    ticket.frontmatter["step"] = "2 (pr)"
    ticket.write(ref.ticket_path)
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Open a PR. Push branch first." in prompt
    assert "Current step: pr" in prompt


def test_compose_raises_on_missing_context(repo: Path) -> None:
    """A referenced context with no file fails loud instead of silently dropping."""
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Ghost ctx")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    # Simulate a context ref whose file was deleted after the ticket was authored.
    ticket.frontmatter["contexts"] = ["email/ghost"]

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket)
    msg = str(exc.value)
    assert "email/ghost" in msg
    assert ref.id_slug in msg
    # Names the exact path the user should create.
    assert "email/ghost/SKILL.md" in msg


def test_compose_raises_on_missing_ticket_level_skill(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Ghost skill")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.frontmatter["skills"] = ["infra/ghost"]

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket)
    msg = str(exc.value)
    assert "infra/ghost" in msg
    assert ref.id_slug in msg
    assert "infra/ghost/SKILL.md" in msg


def test_compose_raises_on_missing_step_skill(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Ghost step skill")
    ref = list_tasks(cfg)[0]
    # Hand-build a ticket whose frozen workflow step points at a missing skill.
    ticket = Ticket(
        frontmatter={
            "title": "Ghost step skill",
            "status": "in_progress",
            "mode": "agent",
            "contexts": [],
            "skills": [],
            "workflow": {
                "name": "code/with-review",
                "steps": [{"name": "implement", "skills": ["infra/ghost"]}],
            },
            "step": "1 (implement)",
        },
        body="## Description\n\nDo the thing.\n\n<!-- coga:blackboard -->\n\n# Blackboard\n",
    )

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket)
    assert "infra/ghost" in str(exc.value)


def test_write_prompt_file(repo: Path, tmp_path: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="X")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    out = write_prompt_file(prompt, ref, dest_dir=tmp_path)
    assert out.exists()
    assert out.read_text() == prompt
    assert out.name.startswith("coga-x-")


def test_compose_missing_packaged_resource_raises_compose_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable packaged prompt layer is a ComposeError, not a bare OSError.

    Packaged resources are read lazily, so a CLI reinstall under a long-running
    supervisor can delete them mid-process. Treat that like any other missing
    layer: refuse the compose through the exception `coga launch` and the
    megalaunch sweep already catch per task.
    """
    import coga.paths

    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Vanished prompt")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)

    real_files = coga.paths.files

    class _GoneResource:
        def read_text(self, *args: object, **kwargs: object) -> str:
            raise FileNotFoundError(2, "No such file or directory", "prompt.md")

    class _Shim:
        def __init__(self, real: object) -> None:
            self._real = real

        def joinpath(self, *parts: str) -> object:
            if parts == ("prompt.md",):
                return _GoneResource()
            return self._real.joinpath(*parts)  # type: ignore[attr-defined]

    monkeypatch.setattr("coga.paths.files", lambda package: _Shim(real_files(package)))

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket)
    msg = str(exc.value)
    assert "prompt.md" in msg
    assert "installed Coga package" in msg


_MANUAL_SPEC_BODY = """\
## Description

Introductory prose that the agent must read.

```markdown
## Fenced example
Still part of the description.
```

## Notes

Lost after the prose.

## Context

Context text.

## Acceptance Criteria

- Criterion one.

## Proposed Shape

Shape text.
"""


def _write_manual_spec_task(repo: Path, body: str) -> object:
    slug = _write_workflow_less_task(repo, title="Manual spec")
    path = repo / "tasks" / slug / "ticket.md"
    head, _, tail = path.read_text().partition("## Description")
    _, _, blackboard = tail.partition("<!-- coga:blackboard -->")
    path.write_text(
        head + body + "\n<!-- coga:blackboard -->"
        + blackboard + "\n## Notes\n\nBlackboard heading stays.\n"
    )
    cfg = load_config(repo)
    return cfg, list_tasks(cfg)[0]


def test_compose_carries_only_description_and_context_of_a_manual_spec(
    repo: Path,
) -> None:
    """Only `## Description` and `## Context` compose; any other `##` above the
    fence is uncomposed (coga/tickets, Body regions), and a fenced `##` example
    is text, not a section boundary."""
    cfg, ref = _write_manual_spec_task(repo, _MANUAL_SPEC_BODY)

    report = compose_prompt_report(cfg, ref, read_ticket(ref))
    text = {layer.layer: layer.text for layer in report.layers}

    assert text["task_description"] == (
        "Introductory prose that the agent must read.\n\n"
        "```markdown\n## Fenced example\nStill part of the description.\n```"
    )
    assert text["task_context"] == "Context text."
    assert "## Notes\n\nBlackboard heading stays." in text["blackboard"]
    prompt = report.prompt
    for dropped in ("Lost after the prose", "Criterion one", "Shape text"):
        assert dropped not in prompt


def test_compose_carries_a_manual_spec_written_as_subsections(repo: Path) -> None:
    """The documented repair: the same spec with `###` subsections composes."""
    body = (
        _MANUAL_SPEC_BODY.replace("## Notes", "### Notes")
        .replace("## Acceptance Criteria", "### Acceptance Criteria")
        .replace("## Proposed Shape", "### Proposed Shape")
    )
    cfg, ref = _write_manual_spec_task(repo, body)

    report = compose_prompt_report(cfg, ref, read_ticket(ref))
    text = {layer.layer: layer.text for layer in report.layers}

    assert "### Notes\n\nLost after the prose." in text["task_description"]
    assert text["task_context"].startswith("Context text.")
    assert "### Acceptance Criteria\n\n- Criterion one." in text["task_context"]
    assert "### Proposed Shape\n\nShape text." in text["task_context"]


def test_compose_uses_repo_base_prompt_override(repo: Path) -> None:
    """A repo `resources/prompt.md` wholly replaces the packaged base prompt,
    and the report names the override file as the layer's path."""
    _write(repo / "resources" / "prompt.md", "Repo base prompt marker.\n")
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Overridden base")
    ref = list_tasks(cfg)[0]

    composition = compose_prompt_report(cfg, ref, read_ticket(ref))

    base = next(l for l in composition.layers if l.layer == "base_prompt")
    assert base.text == "Repo base prompt marker.\n"
    assert base.ref == "prompt.md"
    assert base.path == str(repo / "resources" / "prompt.md")
    assert "Repo base prompt marker." in composition.prompt
    assert "You are an agent working on a ticket inside Coga" not in (
        composition.prompt
    )


def test_compose_falls_back_to_packaged_resources(repo: Path) -> None:
    """Without an override the packaged text is composed and `path` is unset."""
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Stock base")
    ref = list_tasks(cfg)[0]

    composition = compose_prompt_report(cfg, ref, read_ticket(ref))

    fixed = {
        l.layer: l for l in composition.layers
        if l.layer in {"base_prompt", "session_conduct"}
    }
    assert fixed["base_prompt"].text == (
        files("coga.resources").joinpath("prompt.md").read_text()
    )
    assert fixed["base_prompt"].path is None
    assert fixed["session_conduct"].path is None


def test_compose_uses_repo_conduct_override_for_its_context_only(
    repo: Path,
) -> None:
    """Overriding one conduct variant changes only that launch context."""
    _write(
        repo / "resources" / "prompt-megalaunch.md",
        "## Session conduct — megalaunch\n\nRepo queue conduct marker.\n",
    )
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Overridden conduct")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)

    queued = compose_prompt_report(cfg, ref, ticket, launch_context="megalaunch")
    conduct = next(l for l in queued.layers if l.layer == "session_conduct")
    assert conduct.ref == "prompt-megalaunch.md"
    assert conduct.path == str(repo / "resources" / "prompt-megalaunch.md")
    assert "Repo queue conduct marker." in queued.prompt

    attended = compose_prompt_report(cfg, ref, ticket, launch_context="attended")
    conduct = next(l for l in attended.layers if l.layer == "session_conduct")
    assert conduct.path is None
    assert "Repo queue conduct marker." not in attended.prompt


def test_compose_applies_repo_overrides_to_bootstrap_launches(repo: Path) -> None:
    _write(repo / "resources" / "prompt.md", "Repo base prompt marker.\n")
    cfg = load_config(repo)
    ref = resolve_bootstrap(cfg, "browser-automation")

    composition = compose_prompt_report(cfg, ref, read_ticket(ref))

    base = next(l for l in composition.layers if l.layer == "base_prompt")
    assert base.path == str(repo / "resources" / "prompt.md")
    assert "Repo base prompt marker." in composition.prompt


def test_compose_unreadable_repo_override_raises_compose_error(
    repo: Path,
) -> None:
    """An override that exists but can't be read refuses the compose, naming
    the repo file — it never silently falls back to the packaged text."""
    override = repo / "resources" / "prompt.md"
    override.parent.mkdir(parents=True)
    override.write_bytes(b"\xff\xfe not utf-8")
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Broken override")
    ref = list_tasks(cfg)[0]

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, read_ticket(ref))
    msg = str(exc.value)
    assert str(override) in msg
    assert "installed Coga package" not in msg


@pytest.mark.parametrize('kind', ['broken-link', 'directory'])
def test_compose_rejects_unusable_override_path(repo: Path, kind: str) -> None:
    override = repo / 'resources' / 'prompt.md'
    override.parent.mkdir()
    if kind == 'broken-link':
        override.symlink_to('missing.md')
    else:
        override.mkdir()
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title='Unusable override')
    ref = list_tasks(cfg)[0]

    with pytest.raises(ComposeError, match=str(override)):
        compose_prompt(cfg, ref, read_ticket(ref))
