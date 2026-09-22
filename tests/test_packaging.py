from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

import tomllib

if TYPE_CHECKING:
    import pytest

import coga.resources
from coga.paths import packaged_template_path
from coga.ticket import Ticket


EXPECTED_BOOTSTRAP_RESOURCES = (
    "coga/resources/templates/coga/recurring/phone-home/ticket.md",
    "coga/resources/templates/coga/recurring/phone-home/ticket.py",
    "coga/resources/templates/coga/workflows/phone-home/run.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/telemetry/SKILL.md",
    # Keeps `coga.resources` a regular package in the built wheel, not a
    # namespace package — see `test_coga_resources_is_a_regular_package`.
    "coga/resources/__init__.py",
    # Every top-level resource, not just the two that had a test. These ride
    # the `packages` walk rather than the `bootstrap/` force-include, so a
    # packaging change that drops them would otherwise only surface as a
    # runtime read failure inside a composed launch.
    "coga/resources/blackboard.md",
    "coga/resources/prompt.md",
    "coga/resources/prompt-attended.md",
    "coga/resources/prompt-blocker-resolution.md",
    "coga/resources/prompt-megalaunch.md",
    "coga/resources/prompt-queue.md",
    "coga/resources/retire.md",
    "coga/resources/templates/coga/bootstrap/address-pr-comments/ticket.md",
    "coga/resources/templates/coga/bootstrap/orient/ticket.md",
    "coga/resources/templates/coga/bootstrap/browser-automation/ticket.md",
    "coga/resources/templates/coga/bootstrap/resolve-conflicts/ticket.md",
    "coga/resources/templates/coga/bootstrap/ticket/ticket.md",
    "coga/resources/templates/coga/bootstrap/skills/bootstrap/"
    "ticket/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/"
    "scan-protocol/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/browser/"
    "build-automation/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/browser/"
    "playwright/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "autoclose/sweep/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "blockers/remind/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "ticket/finalize/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md",
    "coga/resources/templates/coga/recurring/address-pr-comments/ticket.md",
    "coga/resources/templates/coga/recurring/autoclose-merged/ticket.md",
    "coga/resources/templates/coga/recurring/blocker-reminders/ticket.md",
    "coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md",
    "coga/resources/templates/coga/recurring/skill-update/ticket.md",
    "coga/resources/templates/coga/workflows/autoclose-merged/sweep.md",
    "coga/resources/templates/coga/workflows/blocker-reminders/run.md",
    "coga/resources/templates/coga/workflows/brief-for-human.md",
    "coga/resources/templates/coga/workflows/direct/body.md",
    "coga/resources/templates/coga/workflows/draft-for-human.md",
    "coga/resources/templates/coga/workflows/skill-update/run.md",
    # Bundled reusable workflows ship under bootstrap/workflows/ (local-first
    # fallback) so a fresh repo can run the core code loop, the docs flow, the
    # Dream workflow without hand-copying.
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "with-review.md",
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "design-then-implement.md",
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "with-self-review.md",
    "coga/resources/templates/coga/bootstrap/workflows/docs/"
    "create-google-doc.md",
    "coga/resources/templates/coga/bootstrap/workflows/docs/"
    "with-review.md",
    # …and the code/* skills those workflows reference.
    "coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/review-design/"
    "SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/address-pr-comments/"
    "SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/implement/"
    "SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/implement/seed_local_config.py",
    "coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md",
    "coga/resources/templates/coga/skills/_template/SKILL.md",
    "coga/resources/templates/coga/contexts/.gitignore",
    "coga/resources/templates/coga/skills/direct/body/SKILL.md",
)


# The live/packaged sync rule, enforced instead of remembered.
#
# `CLAUDE.md` says a shipped Coga OS context or template has two copies — the
# live one under `coga/` and the packaged one under
# `src/coga/resources/templates/coga/` — and that both get edited together.
# This module derives the pairs instead of keeping a hand-maintained list,
# because a hand-maintained list only covers the twins someone remembered to
# register, and an unregistered twin is exactly how a pair silently diverges:
#
#   Every packaged file whose live counterpart exists at the mapped path must
#   be byte-identical to it, unless the pair is named in
#   `INTENTIONALLY_DIVERGENT_TWINS` with a written reason.
#
# Two mappings produce a counterpart path, tried in this order:
#
#   templates/coga/<path>                     -> coga/<path>
#   templates/coga/bootstrap/<area>/<path>    -> coga/<area>/<path>
#
# A packaged file with no live counterpart under either mapping is a curated
# battery the source repo does not install into itself — `bootstrap/orient/`,
# `bootstrap/skills/bootstrap/**`, the `bootstrap/workflows/` fallbacks,
# `tasks/coga-build.md`. There is nothing to compare, so it is not a pair; the
# `EXPECTED_BOOTSTRAP_RESOURCES` checks above are what keep those shipping.
# Live files with no packaged copy are repo-specific and are likewise not this
# test's business. Neither direction is a tree diff: only actual twins count.

REPO_ROOT = Path(__file__).resolve().parents[1]

PACKAGED_ROOT = Path("src/coga/resources/templates/coga")
LIVE_ROOT = Path("coga")

# Packaged areas that ship as *bundled batteries*: the source repo installs
# them at the top of its own live tree rather than under `coga/bootstrap/`.
BUNDLED_AREAS = frozenset({"contexts", "skills", "workflows"})

# These are generated local state, not shipped template content. Match the
# build exclusions in pyproject.toml and the installation/agent state that
# coga init ignores. Prune the directories before descending into a venv.
GENERATED_TEMPLATE_DIRS = frozenset(
    {".coga", ".venv", ".agent-skills", ".claude", ".codex", "__pycache__"}
)


# Twins that are deliberately not identical, each with the reason it is
# exempt. An entry that stops describing a real divergence fails the suite,
# so this map prunes itself rather than accumulating stale allowances.
INTENTIONALLY_DIVERGENT_TWINS = {
    "coga/.gitignore": (
        "The live copy carries `coga init`'s `>>> coga-managed >>>` markers; "
        "the packaged copy is the marker-free body that init writes between "
        "them."
    ),
    "coga/coga.toml": (
        "The live copy is this repo's real config (a set `owner`, live agent "
        "and notification wiring); the packaged copy is the commented seed a "
        "fresh repo starts from."
    ),
    "coga/log.md": (
        "The live copy is this repo's append-only audit trail; the packaged "
        "copy is the empty log a fresh repo starts with."
    ),
}


def _live_counterparts(relative: Path) -> tuple[Path, ...]:
    """Live paths a packaged template file could mirror, best guess first."""
    candidates = [LIVE_ROOT / relative]
    parts = relative.parts
    if len(parts) > 2 and parts[0] == "bootstrap" and parts[1] in BUNDLED_AREAS:
        candidates.append(LIVE_ROOT.joinpath(*parts[1:]))
    return tuple(candidates)


def _discover_live_packaged_twins() -> tuple[tuple[str, str], ...]:
    packaged_root = REPO_ROOT / PACKAGED_ROOT
    twins = []
    for directory, dirs, files in os.walk(packaged_root):
        dirs[:] = sorted(name for name in dirs if name not in GENERATED_TEMPLATE_DIRS)
        for name in sorted(files):
            if name == "coga.local.toml":
                continue
            packaged = Path(directory) / name
            if not packaged.is_file():
                continue
            relative = packaged.relative_to(packaged_root)
            for live in _live_counterparts(relative):
                if (REPO_ROOT / live).is_file():
                    twins.append(
                        (live.as_posix(), (PACKAGED_ROOT / relative).as_posix())
                    )
                    break
    return tuple(twins)


# Every live/packaged twin in the repo, divergent ones included.
LIVE_PACKAGED_TWINS = _discover_live_packaged_twins()

# The enforced subset: every twin that is not a documented exception. Dream's
# copy-divergence shard reads this name.
IDENTICAL_LIVE_PACKAGED_PAIRS = tuple(
    (live, packaged)
    for live, packaged in LIVE_PACKAGED_TWINS
    if live not in INTENTIONALLY_DIVERGENT_TWINS
)


def test_live_and_packaged_copies_stay_identical() -> None:
    assert IDENTICAL_LIVE_PACKAGED_PAIRS
    for live, packaged in IDENTICAL_LIVE_PACKAGED_PAIRS:
        assert (REPO_ROOT / live).read_bytes() == (
            REPO_ROOT / packaged
        ).read_bytes(), (
            f"{live} and {packaged} have drifted; edit both copies together. "
            "If the difference is deliberate, add the live path to "
            "INTENTIONALLY_DIVERGENT_TWINS with the reason."
        )


def test_twin_discovery_still_walks_the_packaged_tree() -> None:
    # The pair list is derived, so a mapping regression would not fail
    # loudly — it would quietly shrink the tuple and turn the identity test
    # above into a vacuous pass. This is the floor that catches that. The
    # count sits near 70; the bound is slack, not a target to update on
    # every added template.
    assert len(LIVE_PACKAGED_TWINS) >= 60

    # Both mappings must still resolve, since each covers twins the other
    # cannot see.
    live_paths = {live for live, _ in LIVE_PACKAGED_TWINS}
    assert "coga/workflows/draft-for-human.md" in live_paths
    assert "coga/skills/code/implement/SKILL.md" in live_paths


def test_twin_discovery_ignores_generated_installation_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    expected = (
        (
            "coga/contexts/_template/SKILL.md",
            "src/coga/resources/templates/coga/contexts/_template/SKILL.md",
        ),
        (
            "coga/skills/new-skill/attachment.py",
            "src/coga/resources/templates/coga/bootstrap/skills/new-skill/attachment.py",
        ),
    )
    for pair in expected:
        for relative in pair:
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("shipped content\n")

    # Local installations in both roots carry path-specific bytes. They must
    # neither become twin pairs nor require intentional-divergence entries.
    for base in (LIVE_ROOT, PACKAGED_ROOT):
        for relative in (
            ".coga/.venv/bin/activate",
            ".coga/bin/coga",
            ".venv/bin/activate",
            ".agent-skills/generated/SKILL.md",
            ".claude/settings.json",
            ".codex/config.toml",
            "__pycache__/ticket.cpython-312.pyc",
            "coga.local.toml",
        ):
            path = tmp_path / base / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"local to {base}\n")

    assert set(_discover_live_packaged_twins()) == set(expected)


def test_intentional_divergences_stay_real_and_explained() -> None:
    twins = dict(LIVE_PACKAGED_TWINS)
    for live, reason in INTENTIONALLY_DIVERGENT_TWINS.items():
        assert reason.strip(), f"{live} needs a stated reason to be exempt"
        packaged = twins.get(live)
        assert packaged is not None, (
            f"{live} is no longer a live/packaged twin; "
            "drop its INTENTIONALLY_DIVERGENT_TWINS entry"
        )
        assert (REPO_ROOT / live).read_bytes() != (
            REPO_ROOT / packaged
        ).read_bytes(), (
            f"{live} now matches {packaged}; drop its "
            "INTENTIONALLY_DIVERGENT_TWINS entry so the pair is enforced"
        )


def test_dochub_skill_keeps_portable_leaf_name() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill = (repo_root / "coga/skills/browser/dochub/SKILL.md").read_text()
    frontmatter = skill.split("---", 2)[1]

    assert '\nname: "dochub"\n' in frontmatter
    assert "browser/dochub" not in frontmatter


def test_executable_context_instructions_honor_layout_override() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    knowledge_scan = (
        repo_root
        / (
            "src/coga/resources/templates/coga/bootstrap/skills/bootstrap/"
            "dream/scan/knowledge-scan/SKILL.md"
        )
    ).read_text()
    onboarding = (repo_root / "coga/workflows/build/onboarding.md").read_text()
    onboarding_ticket = (
        repo_root / "src/coga/resources/templates/coga/tasks/coga-build.md"
    ).read_text()

    assert "coga/contexts/**/SKILL.md" not in knowledge_scan
    assert "[layout] contexts" in knowledge_scan
    assert "<contexts-dir>/product/vision/SKILL.md" in onboarding
    assert "under the configured contexts directory" in onboarding_ticket


def test_context_template_ignores_move_with_contexts_tree() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    rules = (repo_root / "coga/contexts/.gitignore").read_text().splitlines()

    assert "**/_template/" in rules
    assert "**/_template.md" in rules


def test_package_includes_coga_resources() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())

    # Resources live inside the `coga` package (`src/coga/resources/...`), so
    # declaring `packages = ["src/coga"]` ships them — no separate
    # `force-include` is needed (#259 dropped that duplicate). Guard that the
    # package is still declared and that the bootstrap battery sources exist on
    # disk to be shipped. `test_wheel_includes_bootstrap_batteries` proves they
    # actually land in a built wheel.
    packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert "src/coga" in packages
    for wheel_name in EXPECTED_BOOTSTRAP_RESOURCES:
        source_name = wheel_name.removeprefix("coga/resources/")
        assert (repo_root / "src" / "coga" / "resources" / source_name).is_file()


def test_coga_resources_is_a_regular_package() -> None:
    """`coga.resources` must not degrade back into a namespace package.

    `importlib.resources.files()` returns a plain `pathlib.Path` for a regular
    package but a `MultiplexedPath` for a namespace one, and on Python 3.11 —
    the oldest interpreter Coga supports — `MultiplexedPath.joinpath` accepts
    exactly one segment (it only became `joinpath(*descendants)` in 3.12). That
    made every multi-segment resource lookup raise `TypeError` on 3.11 and
    crashed `coga init`. Deleting `resources/__init__.py` as a stray empty
    marker reintroduces the crash, and 3.12 would not notice — so assert the
    invariant directly rather than relying on the interpreter under test.
    """
    assert coga.resources.__file__ is not None
    assert isinstance(files("coga.resources"), Path)


def test_packaged_template_path_accepts_multiple_segments() -> None:
    """The multi-segment lookup `coga init` makes must resolve to a real file.

    This is the call shape that raised `TypeError: MultiplexedPath.joinpath()
    takes 2 positional arguments but 7 were given` under a namespace
    `coga.resources` on Python 3.11 (`coga init` itself died one frame earlier
    in `packaged_template_root`, on the two-segment `templates/coga`).
    """
    workflow = packaged_template_path(
        "bootstrap", "workflows", "code", "with-review.md"
    )

    assert isinstance(workflow, Path)
    assert workflow.is_file()


def test_bundled_bootstrap_tickets_attach_only_bootstrap_contexts() -> None:
    """A bundled bootstrap ticket must compose from bundled resources alone.

    `paths.resolve_context_path` falls back to `bootstrap/contexts/` only.
    `templates/coga/contexts/**` is seeded into a repo once by `coga init`
    (`copy_fresh_templates`) and is never a runtime fallback, so a context that
    lives only there is repo-owned and deletable — the shipped
    `browser-automation` launcher once attached `browser/api-first` from that
    tree and could not launch in a repo that had pruned it. The authoring rule
    is stated in `coga/codebase`; this is its enforcement.
    """
    bootstrap_root = REPO_ROOT / PACKAGED_ROOT / "bootstrap"
    launchers = sorted(bootstrap_root.glob("*/ticket.md"))
    assert launchers

    for launcher in launchers:
        for ref in Ticket.read(launcher).contexts:
            bundled = bootstrap_root / "contexts" / ref / "SKILL.md"
            assert bundled.is_file(), (
                f"{launcher.relative_to(REPO_ROOT)} attaches context {ref!r}, "
                f"which does not resolve from {bundled.relative_to(REPO_ROOT)}; "
                "a bundled bootstrap ticket may only attach bootstrap contexts."
            )


def test_no_launch_entrypoint_run_py_files_remain() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    packaged_root = repo_root / "src" / "coga" / "resources" / "templates" / "coga"
    packaged = {
        path.relative_to(packaged_root).as_posix()
        for path in packaged_root.rglob("run.py")
    }
    live = {
        path.relative_to(repo_root / "coga").as_posix()
        for path in (repo_root / "coga").rglob("run.py")
    }

    assert packaged == set()
    assert live == set()


def test_resolve_conflicts_recurring_wrapper_replaces_stale_worktree_sweep() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap_root = (
        repo_root
        / "src"
        / "coga"
        / "resources"
        / "templates"
        / "coga"
        / "bootstrap"
    )
    recurring_root = (
        repo_root
        / "src"
        / "coga"
        / "resources"
        / "templates"
        / "coga"
        / "recurring"
    )
    command = Ticket.read(bootstrap_root / "resolve-conflicts" / "ticket.md")
    wrapper = Ticket.read(recurring_root / "resolve-conflicts" / "ticket.md")

    assert "gh pr list --state open --limit 10000" in command.body
    assert "mergeable" in command.body
    assert "git merge-base --is-ancestor origin/main HEAD" not in command.body
    assert wrapper.frontmatter["schedule"] == "0 8 * * 1"
    assert "\nscript:" not in (
        recurring_root / "resolve-conflicts" / "ticket.md"
    ).read_text()
    # The template declares its delegation instead of instructing a wrapper
    # agent to shell out to a nested `coga launch` (the double hop that could
    # not run without a fake pty). The sweep owns the period task's lifecycle,
    # so the body must not tell an agent to mark it done by hand.
    assert wrapper.frontmatter["delegate"] == "bootstrap/resolve-conflicts"
    assert "recipe" not in wrapper.frontmatter
    assert "coga resolve-conflicts --agent" not in wrapper.body
    assert "coga mark done" not in wrapper.body
    assert "script -qec" not in wrapper.body
    assert "open PRs only" in wrapper.body
    assert not (recurring_root / "rebase-stale-worktrees").exists()


def test_address_pr_comments_recurring_wrapper_delegates_to_command_ticket() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap_root = (
        repo_root
        / "src"
        / "coga"
        / "resources"
        / "templates"
        / "coga"
        / "bootstrap"
    )
    recurring_root = (
        repo_root
        / "src"
        / "coga"
        / "resources"
        / "templates"
        / "coga"
        / "recurring"
    )
    command = Ticket.read(bootstrap_root / "address-pr-comments" / "ticket.md")
    wrapper = Ticket.read(recurring_root / "address-pr-comments" / "ticket.md")

    assert "gh pr list --state open --limit 10000" in command.body
    assert "usage: coga address-pr-comments [PR]" in command.body
    # The sweep reuses the per-PR mechanics from the skill by citation and
    # must say which parts of the skill do not apply to an unattended run.
    assert "coga/skills/code/address-pr-comments/SKILL.md" in command.body
    assert "do not apply" in command.body
    # Re-run guard is the fixed marker, never the reply's author.
    assert "<!-- coga:address-pr-comments reply-to:" in command.body
    assert "resolveReviewThread" in command.body
    assert "coga slack --task bootstrap/address-pr-comments" in command.body
    assert "coga bump" in command.body
    assert wrapper.frontmatter["schedule"] == "0 7 * * *"
    assert "\nscript:" not in (
        recurring_root / "address-pr-comments" / "ticket.md"
    ).read_text()
    # Same shape as the `resolve-conflicts` wrapper: the delegation is the
    # frozen field, the sweep owns the period lifecycle, and a delegated
    # period must stay workflow-less so it resolves to the one-step default.
    assert wrapper.frontmatter["delegate"] == "bootstrap/address-pr-comments"
    assert "workflow" not in wrapper.frontmatter
    assert "recipe" not in wrapper.frontmatter
    assert not (recurring_root / "address-pr-comments" / "ticket.py").exists()
    assert not (bootstrap_root / "address-pr-comments" / "ticket.py").exists()
    assert "coga address-pr-comments --agent" not in wrapper.body
    assert "coga mark done" not in wrapper.body
    assert "script -qec" not in wrapper.body
    assert "open PRs only" in wrapper.body


def test_wheel_includes_bootstrap_batteries(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--quiet",
            "--no-build-isolation",
            "--no-deps",
            ".",
            "-w",
            str(wheel_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    [wheel] = wheel_dir.glob("coga-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    for name in EXPECTED_BOOTSTRAP_RESOURCES:
        assert name in names


def test_phone_home_parent_header_matches_and_packaged_seed_is_unused():
    from coga.taskfile import read_blackboard
    from coga.telemetry import _state
    live = REPO_ROOT / "coga/recurring/phone-home/ticket.md"
    seed = REPO_ROOT / PACKAGED_ROOT / "recurring/phone-home/ticket.md"
    fence = b"<!-- coga:blackboard -->"
    assert live.read_bytes().split(fence)[0] == seed.read_bytes().split(fence)[0]
    state, _ = _state(read_blackboard(seed))
    assert state["run"] == state["offset"] == 0
    assert state["repo_id"] is None
    import hashlib
    assert state["digest"] == hashlib.sha256(b"").hexdigest()


def test_installed_wheel_init_and_phone_home_are_isolated(tmp_path):
    """Exercise the installed artifact outside source; preserve CI and fake HTTP."""
    wheel_dir = tmp_path / "dist"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-build-isolation", "--no-deps", ".", "-w", str(wheel_dir)], cwd=REPO_ROOT, capture_output=True, check=True)
    [wheel] = wheel_dir.glob("coga-*.whl")
    installed = tmp_path/"installed"
    subprocess.run([sys.executable,"-m","pip","install","--no-deps","--target",str(installed),str(wheel)],capture_output=True,check=True)
    target = tmp_path/"company"
    target.mkdir()
    env = {**os.environ, "PYTHONPATH":str(installed), "CI":"true"}
    script = r'''
import json
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner
from coga.cli import app
from coga.config import load_config
from coga.recurring import create_named
from coga.runner import run_recipe
from coga.taskfile import read_blackboard
from coga import telemetry as t
import subprocess
assert "installed" in t.__file__
subprocess.run(["git","init","-b","main"],check=True,capture_output=True)
subprocess.run(["git","config","user.name","Test"],check=True)
subprocess.run(["git","config","user.email","test@example.test"],check=True)
def forbidden(*args, **kwargs):
    raise AssertionError("production transport/worker invoked")
with patch("coga.commands.init._check_external_dependencies"), patch.object(t,"_post_http",forbidden), patch.object(t,"_bounded_worker",forbidden):
    result=CliRunner().invoke(app,["init",".","--user","tester"])
    assert result.exit_code == 0, result.output
    cfg=load_config(Path("coga"))
    parent=Path("coga/recurring/phone-home/ticket.md")
    assert t._state(read_blackboard(parent))[0]["run"] == 0
    outcome=create_named(cfg,"phone-home")
    assert outcome.created
    shim=outcome.ref.task_dir/"ticket.py"
    assert shim.is_file()
    assert run_recipe(cfg,"phone-home",[]) == 0
    state=t._state(read_blackboard(parent))[0]
    assert state["run"] == 1 and state["repo_id"] is None
    assert not t._admitted(cfg)
print("installed init and suppressed first snapshot passed")
'''
    result = subprocess.run([sys.executable,"-c",script],cwd=target,env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "suppressed first snapshot passed" in result.stdout
