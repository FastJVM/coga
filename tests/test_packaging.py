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


# The live/packaged sync rule, enforced instead of remembered.
#
# `AGENTS.md` says a shipped Coga OS context or template has two copies — the
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
# Contexts are the exception: this repo authors them under its configured
# contexts root (`[layout] contexts` in the committed `coga/coga.toml`, else
# `coga/contexts/`), so both packaged context trees map there instead:
#
#   templates/coga/contexts/<path>            -> <contexts-root>/<path>
#   templates/coga/bootstrap/contexts/<path>  -> <contexts-root>/<path>
#
# The starter template is package-only scaffolding, not a canonical topic.
# Every other packaged context file must have its canonical counterpart, and
# every canonical topic must be classified as bootstrap, init-seeded, or local-only — see "Context distribution" below.
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
    "coga/.gitattributes": (
        "trim-log two-phase rollout: enable /log.md -merge through the feature installer "
        "after compatible core lands; rollout/trim-log/coga holds the exact staged twin."
    ),
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
    "coga/context.md": (
        "The live copy describes this repository; the packaged copy is the "
        "stub a fresh repo starts from."
    ),
    "coga/log.md": (
        "The live copy is this repo's append-only audit trail; the packaged "
        "copy is the empty log a fresh repo starts with."
    ),
}


# Stage A transitional ownership policy (v1/package-definitions). The package
# is the single committed owner of every shipped definition; the live copies
# this repo still carries are optional legacy counterparts, removed or
# converted by stage B. While present they must match the package (or carry a
# reviewed difference below). The exact set is pinned, so it cannot grow.
INVENTORY_FILE = Path("tests/legacy_removal_inventory.txt")

# Live counterparts that stay physical after the cutover, with the reason.
SCAFFOLD_COUNTERPARTS = {
    "coga/coga.toml": "the repo's real configuration, seeded once by init",
    "coga/context.md": "the repo's context, seeded once by init",
    "coga/log.md": "real retained audit history",
    "coga/.gitattributes": "Git requires physical merge attributes",
    "coga/.gitignore": "physical ignore rules and init's managed block",
    "docs/contexts/.gitignore": "keeps the configured contexts root's ignore rules physical",
}

# Reviewed differences between a still-present legacy live definition and its
# package owner: stage A authors instruction/link changes only in the package
# and leaves the live definition byte-for-byte unchanged until stage B. Each
# entry pins the live file's unchanged sha256 and states why it differs.
_LINKS_TO_PACKAGE_OWNERS = (
    "stage A points the packaged definition's links at package owners "
    "(removable legacy copies may be absent); the live definition stays "
    "unchanged until stage B removes or converts it"
)
LEGACY_DEFINITION_DIFFERENCES: dict[str, tuple[str, str]] = {
    "coga/recurring/autoclose-merged/ticket.md": (
        "4a6560da0ccd7a44cda17a0c6b63126352d24ca7a19e7f019e98db7c1a9d3f1d",
        _LINKS_TO_PACKAGE_OWNERS,
    ),
    "coga/recurring/blocker-reminders/ticket.md": (
        "1833e9035016eb41c5d72202c513eb20b0d4ef7f02373d2fdc0efff4d26c24a1",
        _LINKS_TO_PACKAGE_OWNERS,
    ),
    "coga/recurring/phone-home/operations.md": (
        "80fee3648b7ca9cc4051e142d73c33642cdad23e089a1879cd4ee9dff559820a",
        _LINKS_TO_PACKAGE_OWNERS + "; packaged instructions also state the "
        "[test]-extra builder prerequisite for the --no-build-isolation wheel "
        "build in the clean installed-wheel proof",
    ),
    "coga/recurring/phone-home/ticket.md": (
        "aa73bf4301af4d01352531f54af03d004b5b072195843fecdc7083a411f33d78",
        _LINKS_TO_PACKAGE_OWNERS + "; packaged instructions also explain "
        "carrier initialization/CAS and replace the obsolete twin exemption; "
        "its complete blackboard (period_state) is state, compared separately",
    ),
    "rollout/trim-log/coga/recurring/trim-log/operations.md": (
        "965a07e9c99ff4516353bf785887943a48ff8040344be702b0b5226f6c66e5b6",
        _LINKS_TO_PACKAGE_OWNERS + "; adoption now selects instead of copying, "
        "accepts valid carriers and pins packaged script identity on retries",
    ),
    "rollout/trim-log/coga/recurring/trim-log/ticket.md": (
        "f486d382aca3cc15ad836615e30293ba90f5897cce7eec68b757349dc950d095",
        _LINKS_TO_PACKAGE_OWNERS,
    ),
}


def _definition_bytes(path: Path) -> bytes:
    """The definition part of a file: a recurring parent's text above its fence.

    A recurring parent ticket's blackboard is repo-owned cross-run state (run
    cursors, saved notes), never part of the definition twin comparison. Every
    other file compares whole.
    """
    raw = path.read_bytes()
    if path.name == "ticket.md" and "recurring" in path.parts[-3:-1]:
        return raw.split(b"<!-- coga:blackboard -->", 1)[0]
    return raw


def _legacy_carrier(path: Path) -> bool:
    """Recognized parent state is validated, never compared as a definition."""
    from coga.recurring_state import CARRIER, has_state_marker, inspect_parent_dir

    if path.name != "ticket.md" or "recurring" not in path.parts[-3:-1]:
        return False
    if not has_state_marker(path.read_text(encoding="utf-8")):
        return False
    parent = inspect_parent_dir(path.parent)
    assert parent.kind == CARRIER, parent.problem
    return True


def _read_inventory() -> dict[str, str]:
    path = REPO_ROOT / INVENTORY_FILE
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        live, packaged = line.split("\t")
        rows[live] = packaged
    return rows


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(_definition_bytes(path)).hexdigest()


def _canonical_contexts_root() -> Path:
    """This repo's contexts directory, relative to the checkout root.

    Read from the committed shared TOML only: machine-local configuration must
    not change which pairs the suite enforces.
    """
    toml_path = REPO_ROOT / LIVE_ROOT / "coga.toml"
    configured = None
    if toml_path.is_file():
        shared = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        configured = shared.get("layout", {}).get("contexts")
    return Path(configured) if configured else LIVE_ROOT / "contexts"


def _live_counterparts(relative: Path) -> tuple[Path, ...]:
    """Live paths a packaged template file could mirror, best guess first."""
    if relative == Path("contexts/_template/SKILL.md"):
        return ()  # Author the starter only in the package, outside the topic library.
    parts = relative.parts
    if len(parts) > 1 and parts[0] == "contexts":
        return (_canonical_contexts_root().joinpath(*parts[1:]),)
    if len(parts) > 2 and parts[:2] == ("bootstrap", "contexts"):
        return (_canonical_contexts_root().joinpath(*parts[2:]),)
    candidates = [LIVE_ROOT / relative]
    if len(parts) > 2 and parts[0] == "bootstrap" and parts[1] in BUNDLED_AREAS:
        candidates.append(LIVE_ROOT.joinpath(*parts[1:]))
    return tuple(candidates)


def _packaged_template_files(subdir: Path = Path()) -> tuple[Path, ...]:
    """Shipped template files under `subdir`, relative to the packaged root."""
    packaged_root = REPO_ROOT / PACKAGED_ROOT
    found = []
    for directory, dirs, files in os.walk(packaged_root / subdir):
        dirs[:] = sorted(name for name in dirs if name not in GENERATED_TEMPLATE_DIRS)
        for name in sorted(files):
            if name == "coga.local.toml":
                continue
            packaged = Path(directory) / name
            if packaged.is_file():
                found.append(packaged.relative_to(packaged_root))
    return tuple(found)


def _discover_live_packaged_twins() -> tuple[tuple[str, str], ...]:
    twins = []
    for relative in _packaged_template_files():
        for live in _live_counterparts(relative):
            if (REPO_ROOT / live).is_file():
                twins.append((live.as_posix(), (PACKAGED_ROOT / relative).as_posix()))
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
    # Deliberately no non-empty floor: stage B removes the legacy copies, and
    # required package resources (EXPECTED_BOOTSTRAP_RESOURCES and the
    # inventory owners below) keep deletion from becoming a vacuous pass.
    for live, packaged in IDENTICAL_LIVE_PACKAGED_PAIRS:
        if _legacy_carrier(REPO_ROOT / live):
            continue
        if live in LEGACY_DEFINITION_DIFFERENCES:
            continue
        assert _definition_bytes(REPO_ROOT / live) == _definition_bytes(
            REPO_ROOT / packaged
        ), (
            f"{live} and {packaged} have drifted; edit both copies together. "
            "If the difference is deliberate, add the live path to "
            "INTENTIONALLY_DIVERGENT_TWINS with the reason."
        )


def test_live_counterparts_are_inventoried_or_scaffolds() -> None:
    """No new live copy of a package definition may appear during stage A."""
    inventory = _read_inventory()
    unexpected = sorted(
        live for live, _ in LIVE_PACKAGED_TWINS
        if live not in inventory and live not in SCAFFOLD_COUNTERPARTS
    )
    assert unexpected == [], (
        "new live counterparts of package-owned definitions; resolve them from "
        "the package instead of copying: " + ", ".join(unexpected)
    )
    for live, packaged in LIVE_PACKAGED_TWINS:
        if live in inventory:
            assert inventory[live] == packaged, (live, packaged, inventory[live])


def test_legacy_inventory_names_existing_package_owners() -> None:
    """Every inventoried definition keeps its package owner (required resource)."""
    inventory = _read_inventory()
    assert inventory
    for live, packaged in inventory.items():
        assert (REPO_ROOT / packaged).is_file(), (
            f"{packaged}, the package owner of legacy {live}, is missing; a "
            "shipped definition must keep exactly one package copy"
        )
        assert not live.startswith("src/"), live
    for live in SCAFFOLD_COUNTERPARTS:
        assert live not in inventory
        assert (REPO_ROOT / live).is_file(), f"scaffold {live} must stay physical"


def test_legacy_definition_differences_pin_unchanged_live_bytes() -> None:
    inventory = _read_inventory()
    for live, (digest, reason) in LEGACY_DEFINITION_DIFFERENCES.items():
        assert reason.strip() and live in inventory, live
        path = REPO_ROOT / live
        if not path.exists():
            continue  # stage B removed it; drop the entry then.
        if _legacy_carrier(path):
            continue  # stage B preserved the complete blackboard as state.
        assert _sha256(path) == digest, (
            f"{live} changed; stage A leaves live definitions untouched"
        )
        assert _definition_bytes(path) != _definition_bytes(REPO_ROOT / inventory[live]), (
            f"{live} matches its package owner again; drop its entry"
        )


def test_inventory_rejects_an_accidental_twin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    packaged = tmp_path / PACKAGED_ROOT / "bootstrap/skills/new/thing/SKILL.md"
    live = tmp_path / LIVE_ROOT / "skills/new/thing/SKILL.md"
    for path in (packaged, live):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("same\n", encoding="utf-8")
    (tmp_path / INVENTORY_FILE).parent.mkdir(parents=True)
    (tmp_path / INVENTORY_FILE).write_text("# empty\n", encoding="utf-8")
    twins = _discover_live_packaged_twins()
    assert ("coga/skills/new/thing/SKILL.md", (PACKAGED_ROOT / "bootstrap/skills/new/thing/SKILL.md").as_posix()) in twins
    monkeypatch.setattr(sys.modules[__name__], "LIVE_PACKAGED_TWINS", twins)
    import pytest

    with pytest.raises(AssertionError, match="new live counterparts"):
        test_live_counterparts_are_inventoried_or_scaffolds()


def test_transitional_checks_accept_carriers_but_reject_incomplete_forks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pytest
    from coga.recurring_state import render_carrier
    from coga.taskfile import read_blackboard

    live = "coga/recurring/phone-home/ticket.md"
    packaged = f"{PACKAGED_ROOT}/recurring/phone-home/ticket.md"
    seed = (REPO_ROOT / packaged).read_bytes()
    for rel in (live, packaged):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(seed)
    parent = tmp_path / live
    parent.write_text(render_carrier(read_blackboard(parent)), encoding="utf-8")
    (tmp_path / INVENTORY_FILE).parent.mkdir(parents=True)
    (tmp_path / INVENTORY_FILE).write_bytes((REPO_ROOT / INVENTORY_FILE).read_bytes())
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "IDENTICAL_LIVE_PACKAGED_PAIRS", ((live, packaged),))
    test_live_and_packaged_copies_stay_identical()
    test_legacy_definition_differences_pin_unchanged_live_bytes()
    test_phone_home_preserves_state_and_seed_is_unused()
    parent.with_name("operations.md").write_text("orphaned definition\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="incomplete fork"):
        test_live_and_packaged_copies_stay_identical()


def test_inventory_rejects_a_deleted_package_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    (tmp_path / INVENTORY_FILE).parent.mkdir(parents=True)
    (tmp_path / INVENTORY_FILE).write_text(
        f"coga/skills/gone/SKILL.md\t{PACKAGED_ROOT.as_posix()}/bootstrap/skills/gone/SKILL.md\n",
        encoding="utf-8",
    )
    for live in SCAFFOLD_COUNTERPARTS:
        (tmp_path / live).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / live).write_text("x\n", encoding="utf-8")
    import pytest

    with pytest.raises(AssertionError, match="package owner"):
        test_legacy_inventory_names_existing_package_owners()


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


def test_intentional_divergences_stay_real_and_explained() -> None:
    twins = dict(LIVE_PACKAGED_TWINS)
    inventory = _read_inventory()
    for live, reason in INTENTIONALLY_DIVERGENT_TWINS.items():
        assert reason.strip(), f"{live} needs a stated reason to be exempt"
        if live in inventory and not (REPO_ROOT / live).exists():
            continue  # a removed legacy counterpart; stage B drops the entry
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
        "coga/install",
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
            # Stage A: the package owns user topics. A canonical copy under
            # the contexts root is an optional legacy counterpart (removed by
            # stage B), compared by the twin tests while it exists.

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
    contexts = REPO_ROOT / _canonical_contexts_root()
    sources = set(contexts.rglob("*.md"))
    sources.update(
        REPO_ROOT / PACKAGED_ROOT / relative
        for relative in _packaged_template_files()
        if relative.suffix == ".md"
    )
    sources.update((REPO_ROOT / "src/coga/resources").glob("*.md"))
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


def _context_link_problems(
    source: Path, removable: frozenset[str] | None = None
) -> list[str]:
    """Broken links in `source`, resolved where the file actually lives.

    Package files resolve relative links inside the real package tree; no
    remapping onto live counterparts. A source that survives stage B (anything
    not in the legacy removal inventory) must not depend on a removable
    legacy copy: it links the package owner instead.
    """
    if removable is None:
        removable = frozenset(_read_inventory())
    problems = []
    rel_source = source.relative_to(REPO_ROOT).as_posix()
    survives = rel_source not in removable
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
        if survives and destination.is_relative_to(REPO_ROOT):
            rel_destination = destination.relative_to(REPO_ROOT).as_posix()
            if rel_destination in removable:
                problems.append(
                    f"{rel_source}: links removable legacy copy {href}; link its "
                    f"package owner {_read_inventory()[rel_destination]}"
                )
            elif destination.is_dir() and any(
                path.startswith(rel_destination + "/") for path in removable
            ):
                # A directory link also disappears when all of its files are
                # removed. Do not traverse archives to make this decision.
                pending = [destination]
                survives_removal = False
                while pending and not survives_removal:
                    for child in pending.pop().iterdir():
                        if child == REPO_ROOT / "docs/archive":
                            survives_removal = True
                            break
                        if child.is_dir():
                            pending.append(child)
                        elif child.relative_to(REPO_ROOT).as_posix() not in removable:
                            survives_removal = True
                            break
                if not survives_removal:
                    problems.append(
                        f"{rel_source}: links removable legacy directory {href}; "
                        "link its package owner"
                    )
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


def test_navigation_rejects_a_directory_that_disappears_at_cutover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    topic = tmp_path / "docs/contexts/coga/cli/SKILL.md"
    topic.parent.mkdir(parents=True)
    topic.write_text("# CLI\n", encoding="utf-8")
    index = tmp_path / "README.md"
    index.write_text("[User topics](docs/contexts/coga/)\n", encoding="utf-8")
    removable = frozenset({"docs/contexts/coga/cli/SKILL.md"})
    assert "removable legacy directory" in _context_link_problems(index, removable)[0]
    (topic.parent / "local.md").write_text("Local topic\n", encoding="utf-8")
    assert _context_link_problems(index, removable) == []


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
    for packaged in _read_inventory().values():
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
    """The package seed is unused; a legacy live parent keeps complete state.

    The live definition is optional in stage A (stage B converts it to a
    state-only carrier). While present, its definition text is pinned by
    `LEGACY_DEFINITION_DIFFERENCES`; here only its mutable blackboard is
    compared: everything but the `period_state:` value matches the seed.
    """
    from coga.taskfile import read_blackboard
    from conftest import load_phone_home
    _state = load_phone_home()._state
    live = REPO_ROOT / "coga/recurring/phone-home/ticket.md"
    seed = REPO_ROOT / PACKAGED_ROOT / "recurring/phone-home/ticket.md"
    period_state = re.compile(r"(?m)^period_state: .*$")
    if live.exists():
        assert period_state.sub("period_state:", read_blackboard(live)) == (
            period_state.sub("period_state:", read_blackboard(seed))
        )
        _state(read_blackboard(live))  # the live counter stays readable
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


def test_staged_trim_log_rollout_matches_packaged_files():
    """The temporary staged copies stay checked until stage B removes them."""
    inventory = _read_inventory()
    staged = REPO_ROOT / "rollout/trim-log/coga"
    for path in staged.rglob("*"):
        if path.is_file():
            live = path.relative_to(REPO_ROOT).as_posix()
            assert live in inventory, live
            if live in LEGACY_DEFINITION_DIFFERENCES or live in {"rollout/trim-log/coga/.gitattributes"}:
                continue
            assert _definition_bytes(path) == _definition_bytes(REPO_ROOT / inventory[live])
