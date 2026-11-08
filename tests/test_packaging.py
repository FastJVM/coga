from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import tomllib

if TYPE_CHECKING:
    import pytest

import coga.resources
from coga.paths import (
    bootstrap_context_path,
    bootstrap_workflow_path,
    packaged_template_path,
    resolve_context_path,
    resolve_workflow_path,
)
from coga.ticket import Ticket


EXPECTED_BOOTSTRAP_RESOURCES = (
    "coga/resources/templates/coga/recurring/trim-log/ticket.md",
    "coga/resources/templates/coga/recurring/trim-log/ticket.py",
    "coga/resources/templates/coga/recurring/trim-log/operations.md",
    "coga/resources/templates/coga/bootstrap/workflows/trim-log/run.md",
    "coga/resources/templates/coga/recurring/phone-home/ticket.md",
    "coga/resources/templates/coga/recurring/phone-home/ticket.py",
    "coga/resources/templates/coga/bootstrap/workflows/phone-home/run.md",
    "coga/resources/templates/coga/recurring/phone-home/operations.md",
    "coga/resources/templates/coga/recurring/autoclose-merged/operations.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md",
    # Keeps `coga.resources` a regular package in the built wheel, not a
    # namespace package — see `test_coga_resources_is_a_regular_package`.
    "coga/resources/__init__.py",
    # Every top-level resource, not just the two that had a test. These ride
    # the `packages` walk rather than the `bootstrap/` force-include, so a
    # packaging change that drops them would otherwise only surface as a
    # runtime read failure inside a composed launch.
    "coga/resources/blackboard.md",
    "coga/resources/ticket.md",
    "coga/resources/prompt.md",
    "coga/resources/prompt-attended.md",
    "coga/resources/prompt-blocker-resolution.md",
    "coga/resources/prompt-megalaunch.md",
    "coga/resources/prompt-queue.md",
    "coga/resources/prompt-ticket.md",
    "coga/resources/retire.md",
    "coga/resources/templates/coga/bootstrap/address-pr-comments/ticket.md",
    "coga/resources/templates/coga/bootstrap/orient/ticket.md",
    "coga/resources/templates/coga/bootstrap/resolve-conflicts/ticket.md",
    "coga/resources/templates/coga/bootstrap/retire/ticket.md",
    "coga/resources/templates/coga/bootstrap/retire/ticket.py",
    "coga/resources/templates/coga/bootstrap/ticket/ticket.md",
    "coga/resources/templates/coga/bootstrap/skills/bootstrap/"
    "ticket/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/"
    "scan-protocol/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "autoclose/sweep/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "blockers/remind/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/coga/"
    "ticket/finalize/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md",
    "coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md",
    "coga/resources/templates/coga/recurring/address-pr-comments/ticket.md",
    "coga/resources/templates/coga/recurring/autoclose-merged/ticket.md",
    "coga/resources/templates/coga/recurring/blocker-reminders/ticket.md",
    "coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md",
    "coga/resources/templates/coga/recurring/skill-update/ticket.md",
    "coga/resources/templates/coga/bootstrap/workflows/autoclose-merged/sweep.md",
    "coga/resources/templates/coga/bootstrap/workflows/blocker-reminders/run.md",
    "coga/resources/templates/coga/bootstrap/workflows/direct/body.md",
    "coga/resources/templates/coga/bootstrap/workflows/skill-update/run.md",
    # Bundled reusable workflows ship under bootstrap/workflows/ (local-first
    # fallback) so a fresh repo can run the core code loop, the docs flow, the
    # Dream workflow without hand-copying.
    "coga/resources/templates/coga/bootstrap/workflows/brief-for-human.md",
    "coga/resources/templates/coga/bootstrap/workflows/draft-for-human.md",
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "with-review.md",
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "design-then-implement.md",
    "coga/resources/templates/coga/bootstrap/workflows/code/"
    "with-self-review.md",
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
    "coga/resources/templates/coga/bootstrap/skills/code/peer-review/SKILL.md",
    "coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md",
    "coga/resources/templates/coga/skills/_template/SKILL.md",
    "coga/resources/templates/coga/contexts/.gitignore",
    "coga/resources/templates/coga/bootstrap/workflows/branch-sweep/sweep.md",
    "coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md",
    "coga/resources/templates/coga/workflows/_template.md",
    "coga/resources/templates/coga/recurring/branch-sweep/ticket.md",
    "coga/resources/templates/coga/recurring/branch-sweep/ticket.py",
    "coga/resources/templates/coga/recurring/dream/ticket.md",
    "coga/resources/templates/coga/recurring/blocker-reminders/ticket.py",
    "coga/resources/templates/coga/recurring/autoclose-merged/ticket.py",
    "coga/resources/templates/coga/recurring/skill-update/ticket.py",
    "coga/resources/templates/coga/tasks/coga-build.md",
    "coga/resources/templates/coga/bootstrap/skills/direct/body/SKILL.md",
)


# Shipped definitions have one committed owner. Derive every possible live
# counterpart from the actual package tree; only explained scaffolds, validated
# state carriers and reviewed overrides may be present in this source repo.
REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGED_ROOT = Path("src/coga/resources/templates/coga")
LIVE_ROOT = Path("coga")
BUNDLED_AREAS = frozenset({"contexts", "skills", "workflows"})
GENERATED_TEMPLATE_DIRS = frozenset(
    {".coga", ".venv", ".agent-skills", ".claude", ".codex", "__pycache__"}
)
REQUIRED_RESOURCES_FILE = Path("tests/required_package_resources.txt")

SCAFFOLD_COUNTERPARTS = {
    "coga/coga.toml": "the repo's real configuration, seeded once by init",
    "coga/context.md": "the repo's context, seeded once by init",
    "coga/log.md": "real retained audit history",
    "coga/.gitattributes": "Git requires physical merge attributes",
    "coga/.gitignore": "physical ignore rules and init's managed block",
    "docs/contexts/.gitignore": "keeps the configured contexts root's ignore rules physical",
}
STATE_CARRIER_COUNTERPARTS = {
    "coga/recurring/address-pr-comments/ticket.md": "saved parent blackboard, independent of its delegated definition",
    "coga/recurring/autoclose-merged/ticket.md": "saved cross-run notes; retires.md remains a separate worklist",
    "coga/recurring/blocker-reminders/ticket.md": "saved parent blackboard, including state without declared state_keys",
    "coga/recurring/branch-sweep/ticket.md": "saved parent notes; clone success ledgers remain machine-local",
    "coga/recurring/dream/ticket.md": "saved cross-run sweep state and notes",
    "coga/recurring/phone-home/ticket.md": "complete movement cursor, counters, identity and unrelated blackboard state",
    "coga/recurring/resolve-conflicts/ticket.md": "saved parent blackboard, independent of its delegated definition",
    "coga/recurring/skill-update/ticket.md": "saved cross-run state and notes",
}
# A future reviewed local fork must explain every counterpart it retains.
LOCAL_DEFINITION_OVERRIDES: dict[str, str] = {}

# Only physical scaffolds may differ from their seed without being a fork.
# Stale explanations fail, including an exception whose file was deleted.
INTENTIONALLY_DIVERGENT_TWINS = {
    "coga/.gitattributes": (
        "Audit retention has not been adopted here: preserve the existing log "
        "union rule until the explicit trim-log installer updates the physical "
        "attribute and selects that job. Definition cutover does not enable it."
    ),
    "coga/.gitignore": "init wraps the seed in the repo's coga-managed markers",
    "coga/coga.toml": "this repo's real owner, agents and notification configuration",
    "coga/context.md": "this repository's context rather than the fresh-repo stub",
    "coga/log.md": "the retained audit trail rather than the unused empty seed",
}


def _read_required_resources() -> frozenset[str]:
    return frozenset(
        line for line in (REPO_ROOT / REQUIRED_RESOURCES_FILE).read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )


def _canonical_contexts_root() -> Path:
    """Read the committed layout, never a machine-local override."""
    toml_path = REPO_ROOT / LIVE_ROOT / "coga.toml"
    configured = None
    if toml_path.is_file():
        shared = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        configured = shared.get("layout", {}).get("contexts")
    return Path(configured) if configured else LIVE_ROOT / "contexts"


def _live_counterparts(relative: Path) -> tuple[Path, ...]:
    """Every live location for a template, including obsolete bootstrap mirrors."""
    parts = relative.parts
    if len(parts) > 1 and parts[0] == "contexts":
        return tuple(dict.fromkeys((_canonical_contexts_root().joinpath(*parts[1:]), LIVE_ROOT / relative)))
    if len(parts) > 2 and parts[:2] == ("bootstrap", "contexts"):
        return tuple(dict.fromkeys((
            _canonical_contexts_root().joinpath(*parts[2:]),
            LIVE_ROOT / relative, LIVE_ROOT.joinpath(*parts[1:]),
        )))
    candidates = [LIVE_ROOT / relative]
    if len(parts) > 2 and parts[0] == "recurring":
        candidates.append(LIVE_ROOT / "recurring" / ("_" + parts[1]) / Path(*parts[2:]))
    if len(parts) > 2 and parts[0] == "bootstrap" and parts[1] in BUNDLED_AREAS:
        candidates.append(LIVE_ROOT.joinpath(*parts[1:]))
    return tuple(candidates)


def _carrier_counterparts(live: str) -> tuple[str, str]:
    path = Path(live)
    return live, (path.parent.with_name("_" + path.parent.name) / path.name).as_posix()


def _packaged_template_files(subdir: Path = Path()) -> tuple[Path, ...]:
    packaged_root = REPO_ROOT / PACKAGED_ROOT
    found = []
    for directory, dirs, names in os.walk(packaged_root / subdir):
        dirs[:] = sorted(name for name in dirs if name not in GENERATED_TEMPLATE_DIRS)
        for name in sorted(names):
            if name == "coga.local.toml":
                continue
            packaged = Path(directory) / name
            if packaged.is_file():
                found.append(packaged.relative_to(packaged_root))
    return tuple(found)


def _ignored_starter(live: Path) -> bool:
    if "_template" not in live.parts and live.name != "_template.md":
        return False
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", live.as_posix()],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", live.as_posix()],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    return tracked.returncode == 1 and ignored.returncode == 0


def _discover_live_packaged_twins() -> tuple[tuple[str, str], ...]:
    candidates = [
        (live, PACKAGED_ROOT / relative)
        for relative in _packaged_template_files()
        for live in _live_counterparts(relative)
    ]
    candidates.extend(
        (LIVE_ROOT / "resources" / path.name, path.relative_to(REPO_ROOT))
        for path in sorted((REPO_ROOT / "src/coga/resources").glob("*.md"))
    )
    return tuple(
        (live.as_posix(), packaged.as_posix())
        for live, packaged in candidates
        if ((REPO_ROOT / live).exists() or (REPO_ROOT / live).is_symlink())
        and not _ignored_starter(live)
    )


def _ownership_problems() -> list[str]:
    """Inverse check: even a byte-identical, unapproved live copy is a failure."""
    from coga.recurring_state import CARRIER, inspect_parent_dir

    problems = []
    for live, packaged in _discover_live_packaged_twins():
        path = REPO_ROOT / live
        if any(live in _carrier_counterparts(name) for name in STATE_CARRIER_COUNTERPARTS):
            parent = inspect_parent_dir(path.parent)
            if parent.kind != CARRIER:
                problems.append(f"{live}: expected state-only carrier; {parent.problem or parent.kind}")
        elif live not in SCAFFOLD_COUNTERPARTS and live not in LOCAL_DEFINITION_OVERRIDES:
            problems.append(f"unapproved live counterpart {live}; owner: {packaged}")
    return problems


def test_package_definitions_have_no_unapproved_live_counterparts() -> None:
    assert _ownership_problems() == []


def test_required_package_resources_exist() -> None:
    required = _read_required_resources()
    assert required
    for name in required:
        assert name.startswith("src/coga/resources/"), name
        assert (REPO_ROOT / name).is_file(), f"required package resource missing: {name}"
    actual = {(PACKAGED_ROOT / relative).as_posix() for relative in _packaged_template_files()}
    actual.update(path.relative_to(REPO_ROOT).as_posix() for path in (REPO_ROOT / "src/coga/resources").glob("*.md"))
    assert actual == required, "record added or deliberately retired resources in the required manifest"


def test_live_counterpart_exceptions_stay_real_and_explained() -> None:
    twins = dict(_discover_live_packaged_twins())
    seen = set()
    for exceptions in (SCAFFOLD_COUNTERPARTS, STATE_CARRIER_COUNTERPARTS, LOCAL_DEFINITION_OVERRIDES):
        for live, reason in exceptions.items():
            assert live not in seen, f"duplicate ownership exception: {live}"
            seen.add(live)
            assert reason.strip(), f"{live} needs a reason"
            candidates = _carrier_counterparts(live) if exceptions is STATE_CARRIER_COUNTERPARTS else (live,)
            present = [name for name in candidates if name in twins]
            assert present, f"stale ownership exception: {live}"
            assert len(present) == 1, f"ambiguous active/parked state: {live}"
            path = REPO_ROOT / present[0]
            assert path.is_file() and not path.is_symlink(), live
    for live, packaged in twins.items():
        if live in SCAFFOLD_COUNTERPARTS and live not in INTENTIONALLY_DIVERGENT_TWINS:
            assert (REPO_ROOT / live).read_bytes() == (REPO_ROOT / packaged).read_bytes(), live
    for live, reason in INTENTIONALLY_DIVERGENT_TWINS.items():
        assert reason.strip() and live in SCAFFOLD_COUNTERPARTS, live
        assert live in twins, f"stale scaffold divergence: {live}"
        assert (REPO_ROOT / live).read_bytes() != (REPO_ROOT / twins[live]).read_bytes(), live


def test_inventory_rejects_an_accidental_twin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    packaged = tmp_path / PACKAGED_ROOT / "bootstrap/skills/new/thing/SKILL.md"
    # Both possible live roots must be checked, not just the first match.
    lives = ["coga/skills/new/thing/SKILL.md", "coga/bootstrap/skills/new/thing/SKILL.md"]
    for path in [packaged, *(tmp_path / name for name in lives)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("same\n", encoding="utf-8")
    problems = _ownership_problems()
    assert len(problems) == 2
    for name in lives:
        assert any(f"unapproved live counterpart {name};" in problem for problem in problems)


def test_ownership_rejects_a_prompt_resource_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    for name in ("src/coga/resources/prompt.md", "coga/resources/prompt.md"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("same prompt\n", encoding="utf-8")
    assert "unapproved live counterpart coga/resources/prompt.md" in _ownership_problems()[0]


def test_ownership_accepts_carriers_but_rejects_definitions_and_incomplete_forks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from coga.recurring_state import render_carrier

    live = "coga/recurring/phone-home/ticket.md"
    packaged = f"{PACKAGED_ROOT}/recurring/phone-home/ticket.md"
    seed = (REPO_ROOT / packaged).read_bytes()
    for name in (live, packaged):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(seed)
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    parent = tmp_path / live
    assert "expected state-only carrier" in _ownership_problems()[0]
    parent.write_text(render_carrier("\n\ncustom state without declared keys\n"), encoding="utf-8")
    assert _ownership_problems() == []
    parked = parent.parent.with_name("_phone-home")
    parent.parent.rename(parked)
    assert _ownership_problems() == []
    parked.rename(parent.parent)
    parent.with_name("operations.md").write_text("orphaned definition\n", encoding="utf-8")
    assert "incomplete fork" in _ownership_problems()[0]
    parent.with_name("operations.md").unlink()
    parent.write_text(parent.read_text().replace("{}", "schedule: daily"), encoding="utf-8")
    assert "must be exactly a state-only carrier" in _ownership_problems()[0]


def test_ownership_rejects_a_parked_definition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    for name in ("coga/recurring/_new-job/ticket.md", f"{PACKAGED_ROOT}/recurring/new-job/ticket.md"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("same definition\n", encoding="utf-8")
    assert "unapproved live counterpart coga/recurring/_new-job/ticket.md" in _ownership_problems()[0]


def test_inventory_rejects_a_deleted_package_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pytest

    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    path = tmp_path / REQUIRED_RESOURCES_FILE
    path.parent.mkdir(parents=True)
    path.write_text(f"{PACKAGED_ROOT.as_posix()}/bootstrap/skills/gone/SKILL.md\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="required package resource missing"):
        test_required_package_resources_exist()


def test_ownership_rejects_a_stale_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pytest

    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    with pytest.raises(AssertionError, match="stale ownership exception"):
        test_live_counterpart_exceptions_stay_real_and_explained()


def test_authoring_starters_must_be_ignored_and_untracked(git_repo, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", git_repo.root)
    live = "coga/skills/_template/SKILL.md"
    for name in (live, f"{PACKAGED_ROOT}/skills/_template/SKILL.md"):
        path = git_repo.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("starter\n", encoding="utf-8")
    (git_repo.root / ".gitignore").write_text("coga/skills/_template/\n", encoding="utf-8")
    assert _discover_live_packaged_twins() == ()
    git_repo.git("add", "-f", "--", live)
    assert "unapproved live counterpart" in _ownership_problems()[0]


def test_twin_discovery_ignores_generated_installation_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    expected = (
        (
            "coga/contexts/.gitignore",
            "src/coga/resources/templates/coga/contexts/.gitignore",
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
            path.write_text("shipped content\n", encoding="utf-8", newline="\n")

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
            path.write_text(f"local to {base}\n", encoding="utf-8", newline="\n")

    assert set(_discover_live_packaged_twins()) == set(expected)


# Context distribution.
#
# Correspondence alone cannot notice a topic deleted from *both* its canonical
# and packaged copies, so the delivered topics are listed here as reviewed
# expectations — never inferred from whatever files survive. A packaged topic
# reaches a repo one of two ways:
#
#   bootstrap fallback — `templates/coga/bootstrap/contexts/<ref>/SKILL.md`,
#     which `paths.resolve_context_path` reads when the repo has no local copy;
#   init-seeded — `templates/coga/contexts/<path>`, which `coga init` copies
#     into the repo's contexts directory once (`copy_fresh_templates`).
#
# The whole Coga-dev audience is local-only. Namespace membership expresses
# that policy without repeating the same reason for every development topic.
REQUIRED_BOOTSTRAP_CONTEXT_REFS = frozenset(
    {
        "coga/architecture",
        "coga/blackboard",
        "coga/cli",
        "coga/configuration",
        "coga/context-layout",
        "coga/edge-code",
        "coga/extension-model",
        "coga/first-task",
        "coga/important",
        "coga/init",
        "coga/human-assist",
        "coga/pr-publication",
        "coga/pr-publication/preparation",
        "coga/state-publication",
        "coga/state-publication/launch-boundaries",
        "coga/knowledge",
        "coga/launch",
        "coga/lifecycle",
        "coga/megalaunch",
        "coga/notifications",
        "coga/notifications/producers",
        "coga/period-task",
        "coga/prompt-composition",
        "coga/recurring",
        "coga/recurring/autofix",
        "coga/recurring/delegation",
        "coga/recurring/scheduling",
        "coga/recurring/scheduling/inactivity",
        "coga/recurring/templates",
        "coga/sandboxes",
        "coga/script-tickets",
        "coga/secrets",
        "coga/skill-management",
        "coga/sync",
        "coga/tickets",
        "coga/tickets/authoring",
        "coga/tickets/discovery",
        "coga/uninstall",
        "coga/usage",
        "coga/workflows",
        "coga/checkout-cleanup",
        "coga/checkout-cleanup/branch-sweep",
        "coga/checkout-cleanup/terminal-owners",
        "coga/checkouts",
        "coga/checkouts/reconciliation",
        "coga/checkouts/launch-boundary",
        "coga/checkouts/chat",
        "coga/checkouts/manual",
        "coga/checkouts/sandbox-clone",
    }
)

# Init seeds are scaffolding only: the starter template and the ignore rules
# that keep it out of the context catalogue. No topic is init-seeded.
REQUIRED_INIT_CONTEXT_FILES = frozenset({".gitignore", "_template/SKILL.md"})

LOCAL_ONLY_CONTEXT_NAMESPACES = {
    "coga-dev/": "Developing Coga itself; never a dependency of shipped instructions.",
}

BOOTSTRAP_CONTEXTS = Path("bootstrap/contexts")
SEEDED_CONTEXTS = Path("contexts")


def _local_only_context(ref: str) -> bool:
    return any(ref.startswith(namespace) for namespace in LOCAL_ONLY_CONTEXT_NAMESPACES)


def _canonical_context_refs() -> frozenset[str]:
    """Every topic under the canonical root: each directory with a SKILL.md."""
    root = REPO_ROOT / _canonical_contexts_root()
    return frozenset(
        skill.parent.relative_to(root).as_posix()
        for skill in root.rglob("SKILL.md")
        if "_template" not in skill.relative_to(root).parts
    )


def _packaged_context_refs(subdir: Path) -> frozenset[str]:
    return frozenset(
        relative.parent.relative_to(subdir).as_posix()
        for relative in _packaged_template_files(subdir)
        if relative.name == "SKILL.md"
        and "_template" not in relative.relative_to(subdir).parts
    )


def _context_distribution_problems() -> list[str]:
    """Why this checkout's context distribution is incomplete, if it is."""
    problems = []
    for subdir in (BOOTSTRAP_CONTEXTS, SEEDED_CONTEXTS):
        for relative in _packaged_template_files(subdir):
            if _local_only_context(relative.relative_to(subdir).as_posix()):
                problems.append(f"local-only context file {relative.as_posix()!r} is packaged")

    canonical_refs = _canonical_context_refs()
    bootstrap_refs = _packaged_context_refs(BOOTSTRAP_CONTEXTS)
    seeded_refs = _packaged_context_refs(SEEDED_CONTEXTS)
    for ref in sorted(REQUIRED_BOOTSTRAP_CONTEXT_REFS):
        if _local_only_context(ref):
            problems.append(f"local-only context {ref!r} is required as bootstrap")
    for ref in sorted(REQUIRED_BOOTSTRAP_CONTEXT_REFS - bootstrap_refs):
        problems.append(f"required bootstrap context {ref!r} is not packaged")
    for name in sorted(REQUIRED_INIT_CONTEXT_FILES):
        if not (REPO_ROOT / PACKAGED_ROOT / SEEDED_CONTEXTS / name).is_file():
            problems.append(f"required init-seeded context file {name!r} is missing")
    local_only_refs = {ref for ref in canonical_refs if _local_only_context(ref)}
    unclassified = canonical_refs - bootstrap_refs - seeded_refs - local_only_refs
    for ref in sorted(unclassified):
        problems.append(
            f"canonical context {ref!r} is neither packaged nor under "
            "LOCAL_ONLY_CONTEXT_NAMESPACES"
        )
    for ref in sorted(bootstrap_refs - REQUIRED_BOOTSTRAP_CONTEXT_REFS):
        problems.append(
            f"packaged bootstrap context {ref!r} is missing from "
            "REQUIRED_BOOTSTRAP_CONTEXT_REFS"
        )
    return problems


def test_context_distribution_is_complete() -> None:
    assert _context_distribution_problems() == []


def test_adopting_repo_resolves_only_user_fallbacks_and_can_author_local_topics(
    tmp_path: Path,
) -> None:
    contexts = tmp_path / "contexts"
    contexts.mkdir()
    cfg = SimpleNamespace(repo_root=tmp_path, contexts_root=contexts)
    for ref in REQUIRED_BOOTSTRAP_CONTEXT_REFS:
        assert resolve_context_path(cfg, ref) == bootstrap_context_path(cfg, ref)
    for ref in _canonical_context_refs():
        if _local_only_context(ref):
            assert resolve_context_path(cfg, ref) is None

    local = contexts / "coga-dev/testing/SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("repo-owned development guidance\n", encoding="utf-8", newline="\n")
    assert resolve_context_path(cfg, "coga-dev/testing") == local


def _seed_distribution_fixture(root: Path, contexts_dir: str | None) -> Path:
    """A minimal checkout satisfying the distribution rules, under `root`."""
    toml = "version = 1\n"
    if contexts_dir is not None:
        toml += f'[layout]\ncontexts = "{contexts_dir}"\n'
    (root / LIVE_ROOT).mkdir(parents=True)
    (root / LIVE_ROOT / "coga.toml").write_text(toml, encoding="utf-8", newline="\n")
    canonical = root / (contexts_dir or "coga/contexts")
    packaged = root / PACKAGED_ROOT
    for ref in REQUIRED_BOOTSTRAP_CONTEXT_REFS:
        for base in (canonical, packaged / BOOTSTRAP_CONTEXTS):
            path = base / ref / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{ref}\n", encoding="utf-8", newline="\n")
    for name in REQUIRED_INIT_CONTEXT_FILES:
        bases = [packaged / SEEDED_CONTEXTS]
        if name != "_template/SKILL.md":
            bases.append(canonical)
        for base in bases:
            path = base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{name}\n", encoding="utf-8", newline="\n")
    for namespace in LOCAL_ONLY_CONTEXT_NAMESPACES:
        path = canonical / namespace / "example/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("local-only example\n", encoding="utf-8", newline="\n")
    return canonical


def test_context_distribution_follows_the_configured_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    _seed_distribution_fixture(tmp_path, "docs/contexts")

    assert _canonical_contexts_root() == Path("docs/contexts")
    assert _context_distribution_problems() == []
    live_paths = {live for live, _ in _discover_live_packaged_twins()}
    assert "docs/contexts/coga/sync/SKILL.md" in live_paths
    assert "docs/contexts/.gitignore" in live_paths
    assert "docs/contexts/_template/SKILL.md" not in live_paths
    assert not any(path.startswith("coga/contexts/") for path in live_paths)


def test_context_distribution_tolerates_a_removed_canonical_counterpart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    canonical = _seed_distribution_fixture(tmp_path, "docs/contexts")
    (canonical / "coga/sync/SKILL.md").unlink()
    (canonical / ".gitignore").unlink()

    # The package owner still ships, so removing the legacy copy is fine.
    assert _context_distribution_problems() == []


def test_context_distribution_reports_a_topic_deleted_from_both_copies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    canonical = _seed_distribution_fixture(tmp_path, "docs/contexts")
    packaged = tmp_path / PACKAGED_ROOT
    (canonical / "coga/sync/SKILL.md").unlink()
    (packaged / BOOTSTRAP_CONTEXTS / "coga/sync/SKILL.md").unlink()
    (packaged / SEEDED_CONTEXTS / "_template/SKILL.md").unlink()

    problems = _context_distribution_problems()
    assert "required bootstrap context 'coga/sync' is not packaged" in problems
    assert "required init-seeded context file '_template/SKILL.md' is missing" in (
        problems
    )


def test_context_distribution_reports_an_unclassified_local_topic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    canonical = _seed_distribution_fixture(tmp_path, None)
    stray = canonical / "team/new-topic/SKILL.md"
    stray.parent.mkdir(parents=True)
    stray.write_text("new\n", encoding="utf-8", newline="\n")

    assert _context_distribution_problems() == [
        "canonical context 'team/new-topic' is neither packaged nor under "
        "LOCAL_ONLY_CONTEXT_NAMESPACES"
    ]


def test_context_distribution_accepts_new_development_topics_without_exceptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    canonical = _seed_distribution_fixture(tmp_path, "docs/contexts")
    topic = canonical / "coga-dev/internals/new-topic/SKILL.md"
    topic.parent.mkdir(parents=True)
    topic.write_text("development details\n", encoding="utf-8", newline="\n")

    assert _context_distribution_problems() == []


def test_context_distribution_rejects_packaged_development_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    canonical = _seed_distribution_fixture(tmp_path, "docs/contexts")
    for subdir in (BOOTSTRAP_CONTEXTS, SEEDED_CONTEXTS):
        for name in ("SKILL.md", "notes.md"):
            relative = Path("coga-dev/example") / name
            (canonical / relative).write_text("local only\n", encoding="utf-8", newline="\n")
            packaged = tmp_path / PACKAGED_ROOT / subdir / relative
            packaged.parent.mkdir(parents=True, exist_ok=True)
            packaged.write_text("local only\n", encoding="utf-8", newline="\n")

    problems = _context_distribution_problems()
    assert len([problem for problem in problems if "local-only context file" in problem]) == 4


def test_context_distribution_rejects_requiring_a_development_topic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    _seed_distribution_fixture(tmp_path, "docs/contexts")
    monkeypatch.setattr(
        sys.modules[__name__], "REQUIRED_BOOTSTRAP_CONTEXT_REFS",
        REQUIRED_BOOTSTRAP_CONTEXT_REFS | {"coga-dev/example"},
    )

    assert "local-only context 'coga-dev/example' is required as bootstrap" in (
        _context_distribution_problems()
    )


def test_local_only_context_namespaces_have_explicit_reasons() -> None:
    assert LOCAL_ONLY_CONTEXT_NAMESPACES
    for namespace, reason in LOCAL_ONLY_CONTEXT_NAMESPACES.items():
        assert namespace.endswith("/")
        assert reason.strip()


MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
REPO_BLOB_URL = "https://github.com/FastJVM/coga/blob/main/"


def _context_navigation_sources() -> tuple[Path, ...]:
    """Live guidance and shipped prose, without archives or generated views."""
    from coga.recurring_state import is_carrier_file
    from coga.skill_manager import gh_skill_repo

    contexts = REPO_ROOT / _canonical_contexts_root()
    sources = set(contexts.rglob("*.md"))
    sources.update(
        REPO_ROOT / PACKAGED_ROOT / relative
        for relative in _packaged_template_files()
        if relative.suffix == ".md"
    )
    sources.update((REPO_ROOT / "src/coga/resources").glob("*.md"))
    for area in ("skills", "workflows", "bootstrap", "recurring"):
        for directory, dirs, names in os.walk(REPO_ROOT / LIVE_ROOT / area):
            if area == "skills" and "SKILL.md" in names and gh_skill_repo(Path(directory)):
                dirs[:] = []
                continue  # Upstream-managed documentation is not this repo's prose.
            dirs[:] = [name for name in dirs if name not in GENERATED_TEMPLATE_DIRS]
            sources.update(
                Path(directory) / name for name in names
                if name.endswith(".md") and not is_carrier_file(Path(directory) / name)
            )
    sources.update((REPO_ROOT / "docs/release-notes").glob("*.md"))
    sources.update(
        REPO_ROOT / name
        for name in ("AGENTS.md", "README.md", "CONTRIBUTING.md", "docs/README.md")
        if (REPO_ROOT / name).is_file()
    )
    return tuple(sorted(sources))


def _markdown_anchors(raw: str) -> set[str]:
    anchors = set()
    for title in re.findall(r"^#{1,6}\s+(.+)$", raw, flags=re.MULTILINE):
        title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)
        slug = re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")
        anchor = slug
        suffix = 0
        while anchor in anchors:
            suffix += 1
            anchor = f"{slug}-{suffix}"
        anchors.add(anchor)
    return anchors


def _context_link_problems(source: Path) -> list[str]:
    """Resolve links at their actual package or repo location; never remap them."""
    problems = []
    rel_source = source.relative_to(REPO_ROOT).as_posix()
    for href in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8")):
        target, _, anchor = href.partition("#")
        if target.startswith(REPO_BLOB_URL):
            destination = REPO_ROOT / target.removeprefix(REPO_BLOB_URL)
        elif re.match(r"\w+:|//", target):
            continue
        else:
            destination = (source.parent / target).resolve() if target else source
        if destination.is_relative_to(REPO_ROOT / "docs/archive"):
            continue  # Dated history is outside this audit; never read it.
        if not destination.exists():
            problems.append(f"{rel_source}: missing link {href}")
            continue
        if anchor and destination.suffix == ".md":
            if anchor not in _markdown_anchors(destination.read_text(encoding="utf-8")):
                problems.append(f"{rel_source}: missing anchor {href}")
    return problems


def test_context_navigation_has_no_broken_links() -> None:
    problems = [
        problem
        for source in _context_navigation_sources()
        for problem in _context_link_problems(source)
    ]
    assert problems == []


def test_navigation_checks_package_relative_links(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    topic = tmp_path / PACKAGED_ROOT / "bootstrap/contexts/coga/cli/SKILL.md"
    topic.parent.mkdir(parents=True)
    topic.write_text("[Missing](../gone/SKILL.md)\n", encoding="utf-8")
    assert "missing link ../gone/SKILL.md" in _context_link_problems(topic)[0]
    legacy = tmp_path / "docs/contexts/coga/gone/SKILL.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("# A live copy cannot repair package navigation\n", encoding="utf-8")
    assert "missing link" in _context_link_problems(topic)[0]


def _unbundled_development_refs(raw: str) -> list[str]:
    # Optional absolute GitHub links are navigation, not an attachment or a
    # relative dependency. Their labels may spell the destination ref.
    raw = re.sub(
        r"\[[^\]]*\]\(https://github\.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/[^)]+\)",
        "", raw,
    )
    raw = re.sub(
        r"https://github\.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/[^\s)`]+",
        "", raw,
    )
    return re.findall(r"\bcoga-dev/[\w][\w/-]*", raw)


def test_shipped_guidance_never_requires_local_development_refs() -> None:
    sources = [
        REPO_ROOT / PACKAGED_ROOT / relative
        for relative in _packaged_template_files()
        if relative.suffix in {".md", ".toml"}
    ]
    sources.extend((REPO_ROOT / "src/coga/resources").glob("*.md"))
    problems = {
        source.relative_to(REPO_ROOT).as_posix(): refs
        for source in sources
        if (refs := _unbundled_development_refs(source.read_text(encoding="utf-8")))
    }
    assert problems == {}


def test_development_ref_check_only_allows_absolute_repository_navigation() -> None:
    assert _unbundled_development_refs("contexts:\n  - coga-dev/testing\n") == [
        "coga-dev/testing"
    ]
    assert _unbundled_development_refs("[testing](../../coga-dev/testing/SKILL.md)")
    assert _unbundled_development_refs(
        f"[coga-dev/testing]({REPO_BLOB_URL}docs/contexts/coga-dev/testing/SKILL.md)"
    ) == []


def test_executable_context_instructions_honor_layout_override() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    knowledge_scan = (
        repo_root
        / (
            "src/coga/resources/templates/coga/bootstrap/skills/bootstrap/"
            "dream/scan/knowledge-scan/SKILL.md"
        )
    ).read_text(encoding="utf-8")
    onboarding = (repo_root / PACKAGED_ROOT / "bootstrap/workflows/build/onboarding.md").read_text(encoding="utf-8")
    onboarding_ticket = (
        repo_root / "src/coga/resources/templates/coga/tasks/coga-build.md"
    ).read_text(encoding="utf-8")

    assert "coga/contexts/**/SKILL.md" not in knowledge_scan
    assert "[layout] contexts" in knowledge_scan
    assert "<contexts-dir>/product/vision/SKILL.md" in onboarding
    assert "under the configured contexts directory" in onboarding_ticket


def test_context_template_ignores_move_with_contexts_tree() -> None:
    rules = (
        (REPO_ROOT / _canonical_contexts_root() / ".gitignore").read_text(encoding="utf-8").splitlines()
    )

    assert "**/_template/" in rules
    assert "**/_template.md" in rules


def test_package_includes_coga_resources() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    # Resources live inside the `coga` package (`src/coga/resources/...`), so
    # declaring `packages = ["src/coga"]` ships them — no separate
    # `force-include` is needed (#259 dropped that duplicate). Guard that the
    # package is still declared and that the bootstrap battery sources exist on
    # disk to be shipped. `test_wheel_includes_bootstrap_batteries` proves they
    # actually land in a built wheel.
    packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert "src/coga" in packages
    assert "src/coga_edge" in packages
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
    lives only there is repo-owned and deletable — a shipped
    launcher that once attached a context from that tree could not launch in a
    repo that had pruned it. The authoring rule
    is stated in `coga/context-layout`; this is its enforcement.
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


# `--workflow <name>` as shipped text spells it; `<name>` placeholders in the
# CLI prose do not match because the name must start with a word character.
WORKFLOW_FLAG_REF = re.compile(r"--workflow[ =]+[`'\"]?(\w(?:[\w./-]*\w)?)")


def test_shipped_workflow_refs_resolve_without_a_seeded_copy(
    tmp_path: Path,
) -> None:
    """Every `--workflow <name>` in shipped text must resolve from the package.

    `paths.resolve_workflow_path` falls back to `bootstrap/workflows/` only.
    `templates/coga/workflows/**` is seeded into a repo once by `coga init`
    and is never a runtime fallback, so a workflow that lives only there is
    missing from every repo initialized before it was added. Dream once told
    agents to file drafts with `--workflow brief-for-human` while that
    workflow was scaffold-only, and `coga create` failed with "Workflow not
    found" in such a repo.
    """
    packaged_root = REPO_ROOT / PACKAGED_ROOT
    cfg = SimpleNamespace(repo_root=tmp_path)
    refs: dict[str, list[str]] = {}
    for path in sorted(packaged_root.rglob("*.md")):
        for name in WORKFLOW_FLAG_REF.findall(path.read_text(encoding="utf-8")):
            refs.setdefault(name, []).append(
                path.relative_to(REPO_ROOT).as_posix()
            )
    assert "brief-for-human" in refs

    for name, sources in sorted(refs.items()):
        resolved = resolve_workflow_path(cfg, name)
        assert resolved == bootstrap_workflow_path(cfg, name), (
            f"--workflow {name} (named in {', '.join(sorted(set(sources)))}) "
            "does not resolve from the packaged bootstrap/workflows/; a "
            "workflow that shipped text depends on must be a bootstrap battery."
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
    ).read_text(encoding="utf-8")
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
    ).read_text(encoding="utf-8")
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


def _pristine_source(tmp_path: Path) -> Path:
    """A disposable copy of exactly the files Git would ship from this tree.

    Tracked and unignored new files only, read from the working tree: no
    `__pycache__`, `.venv`, `.coga`, agent views or init symlinks, so Hatch's
    walk/force-include pairing is exercised the way a clean checkout builds.
    """
    source = tmp_path / "source"
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT, capture_output=True, check=True,
    ).stdout.decode("utf-8").split("\0")
    import shutil

    for name in filter(None, listed):
        origin = REPO_ROOT / name
        if not origin.is_file() or origin.is_symlink():
            continue  # deleted in the working tree, or a link view
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, destination)
    return source


def _build_wheel(tmp_path: Path) -> Path:
    source = _pristine_source(tmp_path)
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()
    result = subprocess.run(
        [
            sys.executable, "-m", "pip", "wheel", "--quiet",
            "--no-build-isolation", "--no-deps", ".", "-w", str(wheel_dir),
        ],
        cwd=source, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stderr
    [wheel] = wheel_dir.glob("coga-*.whl")
    return wheel


def test_wheel_includes_bootstrap_batteries(tmp_path: Path) -> None:
    wheel = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    # One packaged definition per logical ref: a Hatch walk/force-include
    # collision would ship a path twice.
    assert len(names) == len(set(names))
    names = set(names)

    assert {"coga_edge/__init__.py", "coga_edge/phone_home.py"} <= names
    for name in EXPECTED_BOOTSTRAP_RESOURCES:
        assert name in names
    for packaged in _read_required_resources():
        assert packaged.removeprefix("src/") in names, packaged
    assert not any("__pycache__" in name for name in names)
    for ref in REQUIRED_BOOTSTRAP_CONTEXT_REFS:
        assert (
            f"coga/resources/templates/coga/bootstrap/contexts/{ref}/SKILL.md" in names
        )
    for subdir in (BOOTSTRAP_CONTEXTS, SEEDED_CONTEXTS):
        prefix = f"coga/resources/templates/coga/{subdir.as_posix()}/"
        assert not any(
            name.startswith(prefix) and _local_only_context(name.removeprefix(prefix))
            for name in names
        )
    # Reusable workflows/skills ship only under bootstrap/, never at the old
    # seed paths as a second copy.
    assert not any(
        name.startswith("coga/resources/templates/coga/workflows/")
        and not name.endswith("/_template.md")
        for name in names
    )
    assert not any(
        name.startswith("coga/resources/templates/coga/skills/")
        and "/_template/" not in name
        for name in names
    )


NINE_BUNDLED_PARENTS = (
    "address-pr-comments", "autoclose-merged", "blocker-reminders", "branch-sweep",
    "dream", "phone-home", "resolve-conflicts", "skill-update", "trim-log",
)


def test_phone_home_preserves_state_and_seed_is_unused():
    """The package seed stays unused; repo-owned state remains independently valid."""
    from coga.taskfile import read_blackboard
    from conftest import load_phone_home
    _state = load_phone_home()._state
    live = REPO_ROOT / "coga/recurring/phone-home/ticket.md"
    seed = REPO_ROOT / PACKAGED_ROOT / "recurring/phone-home/ticket.md"
    if live.exists():
        from coga.recurring_state import CARRIER, inspect_parent_dir
        assert inspect_parent_dir(live.parent).kind == CARRIER
        _state(read_blackboard(live))
    state, _ = _state(read_blackboard(seed))
    assert state["schema"] == 2
    assert state["run"] == 0
    assert state["repo_id"] is None
    assert state["seen_movements"] == []


def test_installed_wheel_init_and_phone_home_are_isolated(tmp_path):
    """Exercise the installed artifact outside source; preserve CI and fake HTTP.

    Built from a pristine copy, installed into an isolated target with no
    inherited editable `PYTHONPATH`, made read-only, and run from a separate
    project: fresh init copies no definitions, all nine bundled parents
    resolve from the package, and the first phone-home run creates the repo
    carrier from the unused seed. Package resource bytes must not change.
    """
    wheel = _build_wheel(tmp_path)
    installed = tmp_path/"installed"
    subprocess.run([sys.executable,"-m","pip","install","--no-deps","--target",str(installed),str(wheel)],capture_output=True,check=True)
    resources = installed / "coga" / "resources"

    def snapshot_tree() -> dict[str, bytes]:
        return {
            p.relative_to(resources).as_posix(): p.read_bytes()
            for p in sorted(resources.rglob("*")) if p.is_file()
        }

    before = snapshot_tree()
    for path in sorted(resources.rglob("*"), reverse=True):
        path.chmod(path.stat().st_mode & ~0o222)
    target = tmp_path/"company"
    target.mkdir()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update({"PYTHONPATH": str(installed), "PYTHONIOENCODING": "utf-8", "CI": "true",
                "PYTHONDONTWRITEBYTECODE": "1"})
    script = r'''
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner
import coga
from coga.cli import app
from coga.config import load_config
from coga.recurring import create_named, iter_template_sources, resolve_template_source
from coga.taskfile import read_blackboard
from coga.paths import resolve_skill_path, resolve_workflow_path, resolve_context_path
from coga.tasks import resolve_bootstrap
import subprocess, sys
assert "installed" in coga.__file__, coga.__file__
subprocess.run(["git","init","-b","main"],check=True,capture_output=True)
subprocess.run(["git","config","user.name","Test"],check=True)
subprocess.run(["git","config","user.email","test@example.test"],check=True)
def forbidden(*args, **kwargs):
    raise AssertionError("production transport/worker invoked")
with patch("coga.commands.init._require_init_tools"), patch("coga.commands.init._offer_optional_tools"):
    result=CliRunner().invoke(app,["init",".","--user","tester"])
assert result.exit_code == 0, result.output
for gone in ("recurring/phone-home", "recurring/dream", "workflows/direct", "skills/direct"):
    assert not Path("coga", gone).exists(), gone
cfg=load_config(Path("coga"))
# Every resource type resolves from the installed package.
assert "installed" in str(resolve_skill_path(cfg, "direct/body"))
assert "installed" in str(resolve_workflow_path(cfg, "direct/body"))
assert "installed" in str(resolve_workflow_path(cfg, "phone-home/run"))
assert "installed" in str(resolve_context_path(cfg, "coga/recurring/templates"))
assert "installed" in str(resolve_bootstrap(cfg, "bootstrap/retire").path)
names = set(sys.argv[1].split(","))
sources = {s.name: s for s in iter_template_sources(cfg)}
for name in names:
    s = sources[name]
    assert s.enabled and s.origin == "package" and "installed" in str(s.definition_dir), (name, s)
    s.load()
# Materialize every repo job through the real fallback/workflow transform,
# compose agent/delegate prompts, and execute every deterministic shim with
# only outward work and lifecycle subprocesses stubbed.
import os, runpy
from coga.compose import compose_prompt
from coga.recurring import frozen_task_delegate, scan_clone_due
from coga.tasks import read_ticket
from coga.runner import RECIPES
from coga_edge import trim_log
real_run = subprocess.run
def stub_bump(argv, **kwargs):
    if argv[1:4] == ["-m", "coga.cli", "bump"]:
        assert argv[4].startswith("recurring/")
        return subprocess.CompletedProcess(argv, 0)
    assert argv[0] == "git", argv
    return real_run(argv, **kwargs)
calls = []
def recipe(name):
    def run(cfg, argv):
        assert argv == []
        calls.append(name)
        return 0
    return run
for name in sorted(names - {"phone-home"}):
    template = sources[name].load()
    if template.clone_scoped:
        due = scan_clone_due(cfg, only=name).due
        assert len(due) == 1 and due[0].template.path == template.path
        script = template.script_entry_point
        task_env = {}
        assert not Path("coga/recurring", name).exists()
    else:
        outcome = create_named(cfg, name)
        assert outcome.created
        ticket = read_ticket(outcome.ref)
        delegate = frozen_task_delegate(outcome.ref, ticket)
        target = resolve_bootstrap(cfg, delegate) if delegate else outcome.ref
        prompt = compose_prompt(cfg, target, read_ticket(target))
        assert prompt and (delegate is None or "installed" in str(target.path))
        script = outcome.ref.task_dir / "ticket.py"
        task_env = {"COGA_TASK_SLUG": outcome.ref.id_slug,
                    "COGA_TASK_BLACKBOARD": str(outcome.ref.ticket_path)}
    if script and script.is_file():
        with patch.dict(os.environ, task_env), patch.dict(RECIPES, {key: recipe(key) for key in RECIPES}), \
             patch("coga.config.load_config", return_value=cfg), \
             patch.object(trim_log, "load_config", return_value=cfg), \
             patch.object(trim_log, "trim", return_value="Installed smoke: no retention side effects"), \
             patch.object(sys, "argv", [str(script)]), patch("subprocess.run", stub_bump):
            try:
                runpy.run_path(str(script), run_name="__main__")
            except SystemExit as exc:
                assert exc.code == 0, (name, exc.code)
assert set(calls) == {"autoclose", "blocker-reminders", "skill-update", "branch-sweep"}, calls
import coga_edge.phone_home as t
assert "installed" in t.__file__
assert "installed" in str(t._PACKAGE_FILE)
with patch.object(t,"_post_http",forbidden), patch.object(t,"_bounded_worker",forbidden):
    parent=Path("coga/recurring/phone-home/ticket.md")
    assert not parent.exists()
    outcome=create_named(cfg,"phone-home")
    assert outcome.created
    assert parent.read_text(encoding="utf-8").startswith("---\n{}\n---\n<!-- coga:recurring-state -->")
    assert t._state(read_blackboard(parent))[0]["run"] == 0
    shim=outcome.ref.task_dir/"ticket.py"
    assert shim.is_file()
    assert t.run_phone_home(cfg,[]) == 0
    assert t.run_phone_home(cfg,[]) == 0
    state=t._state(read_blackboard(parent))[0]
    assert state["run"] == 2 and state["repo_id"] is None
    assert not t._admitted(cfg)
result = CliRunner().invoke(app, ["validate", "--json"])
assert '"recurring/' not in result.output or "bad-recurring-template" not in result.output, result.output
print("installed init and suppressed first snapshot passed")
'''
    try:
        result = subprocess.run(
            [sys.executable, "-c", script, ",".join(NINE_BUNDLED_PARENTS)],
            cwd=target, env=env, capture_output=True, text=True, encoding="utf-8",
            timeout=60,
        )
    finally:
        for path in resources.rglob("*"):
            path.chmod(path.stat().st_mode | 0o200)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "suppressed first snapshot passed" in result.stdout
    assert snapshot_tree() == before
