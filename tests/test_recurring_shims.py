"""The four recurring templates' `ticket.py` deterministic halves.

Coga's own bundled scripts are covered from `tests/`, never by collecting the
live dogfooded `coga/` tree: the contract checks read the *packaged* templates,
and the end-to-end run happens against a copy of the seeded `example/` repo.
"""

from __future__ import annotations

import ast
import importlib
import shutil
from pathlib import Path

import pytest
from conftest import load_phone_home
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.launch_script import SCRIPT_ENTRY_POINT
from coga.recurring import create_named
from coga.runner import RECIPES, run_recipe
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import read_ticket


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "example"
PACKAGED = REPO_ROOT / "src" / "coga" / "resources" / "templates" / "coga"

# Every template that used to declare `recipe: <name>`, and the registry entry
# its shim must now reach directly.
SHIMMED_TEMPLATES = (
    ("autoclose-merged", "autoclose"),
    ("blocker-reminders", "blocker-reminders"),
    ("branch-sweep", "branch-sweep"),
    ("skill-update", "skill-update"),
)


@pytest.mark.parametrize(("template", "recipe_name"), SHIMMED_TEMPLATES)
def test_shim_calls_the_registered_recipe_and_bumps_through_the_cli(
    template: str, recipe_name: str
) -> None:
    """Each shim runs its recipe through the registry and completes its own step.

    Three things this pins. The shim must reach the recipe through
    `coga.runner.run_recipe`, not by importing the recipe function: that
    function is the recipe layer's failure surface, the one place a non-zero
    exit is recorded on the period blackboard, and a direct import would skip
    it. The name it passes must be a registry key — a typo would only surface
    on the next scheduled firing. And the step must be completed by
    subprocessing the CLI: calling the Typer command function in-process passes
    `OptionInfo` sentinels instead of real option defaults.
    """
    script = PACKAGED / "recurring" / template / SCRIPT_ENTRY_POINT
    source = script.read_text()
    tree = ast.parse(source, filename=str(script))

    imported: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            assert node.module is not None
            for alias in node.names:
                imported[alias.asname or alias.name] = node.module

    # The step is completed by subprocess only. Importing the bump command and
    # calling it is the `OptionInfo`-sentinel bug this shape exists to avoid.
    assert not [name for name in imported.values() if name.endswith("bump")]

    assert imported == {"load_config": "coga.config", "run_recipe": "coga.runner"}
    assert getattr(importlib.import_module("coga.runner"), "run_recipe") is run_recipe

    assert recipe_name in RECIPES
    assert f'run_recipe(load_config(), "{recipe_name}", [])' in source

    argv = _subprocess_argv(tree)
    assert argv[:1] == [_SYS_EXECUTABLE]
    assert argv[1:4] == ["-m", "coga.cli", "bump"]
    assert argv[4] == _TASK_SLUG_ENV


_SYS_EXECUTABLE = "<sys.executable>"
_TASK_SLUG_ENV = "<os.environ[COGA_TASK_SLUG]>"


def _subprocess_argv(tree: ast.Module) -> list[str]:
    """The argv literal the shim hands `subprocess.run`, one entry per element.

    Read structurally rather than by matching source text, so reformatting the
    shim cannot silently retire this check.
    """
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    (call,) = calls
    (argv,) = call.args
    assert isinstance(argv, ast.List)
    return [_describe(element) for element in argv.elts]


def _describe(node: ast.expr) -> str:
    if isinstance(node, ast.Constant):
        return node.value
    if (
        isinstance(node, ast.Attribute)
        and node.attr == "executable"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    ):
        return _SYS_EXECUTABLE
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "environ"
        and isinstance(node.slice, ast.Constant)
    ):
        return f"<os.environ[{node.slice.value}]>"
    return ast.dump(node)


def test_every_shimmed_template_dropped_the_recipe_field() -> None:
    """`recipe:` left the format; the file beside `ticket.md` is the signal."""
    for template, _ in SHIMMED_TEMPLATES:
        ticket = (PACKAGED / "recurring" / template / "ticket.md").read_text()
        assert "\nrecipe:" not in ticket, template


@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway copy of the seeded example repo (see `test_smoke`)."""
    dest = tmp_path / "example"
    shutil.copytree(
        EXAMPLE,
        dest,
        ignore=shutil.ignore_patterns(".claude", ".codex", ".git", ".venv*", "venv"),
        ignore_dangling_symlinks=True,
    )
    monkeypatch.chdir(dest / "coga")
    return dest / "coga"


@pytest.mark.parametrize(("template", "recipe_name"), SHIMMED_TEMPLATES)
def test_period_task_runs_its_shim_headlessly_and_closes_its_own_step(
    seeded: Path,
    template: str,
    recipe_name: str,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """End-to-end: install a packaged template, create its period task, launch.

    Replace the registry with one no-op recipe in the copied shim so production
    maintenance never runs. The run proves the whole chain: `_create_at_slug`
    copies `ticket.py`, `coga launch` classifies it, the recipe runs with no agent
    and no TTY (CliRunner supplies neither), and the shim's own `coga bump`
    finishes the one-step workflow.
    """
    shutil.copytree(
        PACKAGED / "recurring" / template,
        seeded / "recurring" / template,
    )
    shutil.copytree(
        PACKAGED / "workflows" / template,
        seeded / "workflows" / template,
    )

    cfg = load_config(seeded)
    outcome = create_named(cfg, template)
    ref = outcome.ref

    assert outcome.created is True
    assert (ref.task_dir / SCRIPT_ENTRY_POINT).is_file()
    # Only the reserved name travels; other template siblings stay put.
    assert sorted(path.name for path in ref.task_dir.iterdir()) == sorted(
        ("ticket.md", SCRIPT_ENTRY_POINT)
    )
    script = ref.task_dir / SCRIPT_ENTRY_POINT
    script.write_text(script.read_text().replace(
        "from coga.runner import run_recipe",
        "from coga.runner import RECIPES, run_recipe\n"
        "RECIPES.clear()\n"
        f"RECIPES[{recipe_name!r}] = lambda cfg, args: 0",
    ))

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert read_ticket(ref).status == "done"
    audit = (seeded / "log.md").read_text()
    assert audit.count("[system] task done") == 1
    assert "[human:marc] task done" not in audit
    assert f"system finished *{ref.id_slug}*" in capfd.readouterr().err


def test_period_task_left_unfinished_when_its_shim_fails(seeded: Path) -> None:
    """A non-zero deterministic phase halts the launch before any agent work."""
    shutil.copytree(
        PACKAGED / "recurring" / "blocker-reminders",
        seeded / "recurring" / "blocker-reminders",
    )
    shutil.copy(
        PACKAGED / "workflows" / "blocker-reminders" / "run.md",
        _mkdir(seeded / "workflows" / "blocker-reminders") / "run.md",
    )
    cfg = load_config(seeded)
    ref = create_named(cfg, "blocker-reminders").ref
    (ref.task_dir / SCRIPT_ENTRY_POINT).write_text("raise SystemExit(17)\n")

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 17, result.output
    # The launcher never advances the workflow on the script's behalf.
    assert read_ticket(ref).status == "in_progress"


def test_failing_recipe_leaves_its_reason_on_the_period_blackboard(
    seeded: Path,
) -> None:
    """End-to-end for the recipe layer's failure surface.

    The launcher hands `ticket.py` the period task's `COGA_TASK_BLACKBOARD`;
    a recipe run through `run_recipe` that exits non-zero has its stderr
    appended there as `## Recipe Failure`, which is what the sweep's run
    record reads. The console output the child produced is discarded by the
    sweep, so this section is the only reason the period keeps.
    """
    shutil.copytree(
        PACKAGED / "recurring" / "blocker-reminders",
        seeded / "recurring" / "blocker-reminders",
    )
    shutil.copy(
        PACKAGED / "workflows" / "blocker-reminders" / "run.md",
        _mkdir(seeded / "workflows" / "blocker-reminders") / "run.md",
    )
    cfg = load_config(seeded)
    ref = create_named(cfg, "blocker-reminders").ref
    (ref.task_dir / SCRIPT_ENTRY_POINT).write_text(
        "import sys\n"
        "from coga import runner\n"
        "from coga.config import load_config\n"
        "def fail(cfg, argv):\n"
        "    sys.stderr.write('[blockers] webhook refused the reminder\\n')\n"
        "    return 2\n"
        "runner.RECIPES['blocker-reminders'] = fail\n"
        "sys.exit(runner.run_recipe(load_config(), 'blocker-reminders', []))\n"
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 2, result.output
    assert read_ticket(ref).status == "in_progress"
    blackboard = read_blackboard(ref.ticket_path)
    assert "## Recipe Failure" in blackboard
    assert "Recipe: `blocker-reminders`" in blackboard
    assert f"Task: `{ref.id_slug}`" in blackboard
    assert "[blockers] webhook refused the reminder" in blackboard


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_phone_home_real_suppressed_shim_updates_parent_and_finishes(seeded, capfd):
    """The first due run uses the real ticket code, never an agent or production HTTP."""
    _state = load_phone_home()._state
    for area in ("recurring", "workflows"):
        shutil.copytree(PACKAGED / area / "phone-home", seeded / area / "phone-home")
    cfg = load_config(seeded)
    outcome = create_named(cfg, "phone-home")
    assert outcome.created
    result = CliRunner().invoke(app, ["launch", outcome.ref.id_slug])
    assert result.exit_code == 0, result.output
    assert read_ticket(outcome.ref).status == "done"
    state, _ = _state(read_blackboard(seeded / "recurring/phone-home/ticket.md"))
    assert state["run"] == 1 and state["repo_id"] is None
    assert "capture suppressed" in read_blackboard(outcome.ref.ticket_path)
    assert "stale" not in capfd.readouterr().err.lower()


def test_phone_home_failure_reaches_the_period_blackboard_without_a_registry_entry(seeded):
    """Edge code keeps the `## Recipe Failure` floor through `run_reported`."""
    assert "phone-home" not in RECIPES
    for area in ("recurring", "workflows"):
        shutil.copytree(PACKAGED / area / "phone-home", seeded / area / "phone-home")
    parent = seeded / "recurring/phone-home/ticket.md"
    replace_blackboard(parent, "\nperiod_state: {}\n")
    cfg = load_config(seeded)
    outcome = create_named(cfg, "phone-home")
    assert outcome.created
    result = CliRunner().invoke(app, ["launch", outcome.ref.id_slug])
    assert result.exit_code != 0
    assert read_ticket(outcome.ref).status != "done"
    report = read_blackboard(outcome.ref.ticket_path)
    assert "## Recipe Failure" in report and "Recipe: `phone-home`" in report
    assert "invalid phone-home period_state" in report
