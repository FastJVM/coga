"""The shipped recurring templates' `ticket.py` deterministic halves.

Coga's own bundled scripts are covered from `tests/`, never by collecting the
live dogfooded `coga/` tree: the contract checks read the *packaged* templates,
and the end-to-end run happens against a copy of the seeded `tests/fixtures/seeded-repo/` fixture.
"""

from __future__ import annotations

import ast
import importlib
import runpy
import shutil
import subprocess
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
SEEDED_REPO = REPO_ROOT / "tests" / "fixtures" / "seeded-repo"
PACKAGED = REPO_ROOT / "src" / "coga" / "resources" / "templates" / "coga"

# Every template that used to declare `recipe: <name>`, and the registry entry
# its shim must now reach directly.
# Templates whose job moved to `coga_edge`: (template, module, worker). The
# shim imports the module's `main`; the recipe name left the registry.
EDGE_SHIMMED_TEMPLATES = (
    ("blocker-reminders", "blocker_reminders", "run_blocker_reminders"),
    ("skill-update", "skill_update", "run_skill_update"),
)
# `scope: clone` shims: no period task, so the exit code is the whole outcome.




@pytest.mark.parametrize(("template", "module", "worker"), EDGE_SHIMMED_TEMPLATES)
def test_edge_shim_runs_its_installed_module_main(template: str, module: str, worker: str) -> None:
    """The shim holds no job logic and no completion of its own.

    `main` uses `runner.run_entry` to run and report the job, then bump a
    launched script task on success. The removed recipe name is not
    registered, so `coga run <name>` takes the unknown-recipe exit.
    """
    script = PACKAGED / "recurring" / template / SCRIPT_ENTRY_POINT
    tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    imported = {
        alias.asname or alias.name: node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
        for alias in node.names
    }
    assert imported == {"main": f"coga_edge.{module}"}
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert [ast.unparse(call) for call in calls] == ["SystemExit(main([], scheduled=True))", "main([], scheduled=True)"]
    job = importlib.import_module(f"coga_edge.{module}")
    assert callable(job.main) and callable(getattr(job, worker))
    assert template not in RECIPES


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
    templates = [t for t, *_ in EDGE_SHIMMED_TEMPLATES]
    for template in templates:
        ticket = (PACKAGED / "recurring" / template / "ticket.md").read_text(encoding="utf-8")
        assert "\nrecipe:" not in ticket, template




@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway copy of the seeded fixture repo (see `test_smoke`)."""
    dest = tmp_path / "example"
    shutil.copytree(
        SEEDED_REPO,
        dest,
        ignore=shutil.ignore_patterns(".claude", ".codex", ".git", ".venv*", "venv"),
        ignore_dangling_symlinks=True,
    )
    monkeypatch.chdir(dest / "coga")
    return dest / "coga"


# How each shipped shim's production work is replaced with a no-op in a copied
# period script: (template, shim text, replacement text).
_NOOP_SHIM_PATCHES = [
    (template, f"from coga_edge.{module} import main",
     f"import coga_edge.{module} as job\n"
     f"job.{worker} = lambda cfg, args: 0\n"
     f"from coga_edge.{module} import main")
    for template, module, worker in EDGE_SHIMMED_TEMPLATES
]


@pytest.mark.parametrize(("template", "shim_text", "noop_text"), _NOOP_SHIM_PATCHES)
def test_period_task_runs_its_shim_headlessly_and_closes_its_own_step(
    seeded: Path,
    template: str,
    shim_text: str,
    noop_text: str,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """End-to-end: install a packaged template, create its period task, launch.

    Replace the production work with a no-op in the copied shim so maintenance
    never runs. The run proves the whole chain: `_create_at_slug` copies
    `ticket.py`, `coga launch` classifies it, the job runs with no agent and no
    TTY (CliRunner supplies neither), and the shim's own `coga bump` (an edge
    module's `runner.run_entry`) finishes the one-step workflow.
    """
    shutil.copytree(
        PACKAGED / "recurring" / template,
        seeded / "recurring" / template,
    )
    shutil.copytree(
        PACKAGED / "bootstrap" / "workflows" / template,
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
    source = script.read_text(encoding="utf-8")
    assert source.count(shim_text) == 1
    script.write_text(source.replace(shim_text, noop_text), encoding="utf-8", newline="\n")

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert read_ticket(ref).status == "done"
    audit = (seeded / "log.md").read_text(encoding="utf-8")
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
        PACKAGED / "bootstrap" / "workflows" / "blocker-reminders" / "run.md",
        _mkdir(seeded / "workflows" / "blocker-reminders") / "run.md",
    )
    cfg = load_config(seeded)
    ref = create_named(cfg, "blocker-reminders").ref
    (ref.task_dir / SCRIPT_ENTRY_POINT).write_text("raise SystemExit(17)\n", encoding="utf-8", newline="\n")

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 17, result.output
    # The launcher never advances the workflow on the script's behalf.
    assert read_ticket(ref).status == "in_progress"


def test_failing_recipe_leaves_its_reason_on_the_period_blackboard(
    seeded: Path,
) -> None:
    """End-to-end for the shared failure surface, through the stock shim.

    The launcher hands `ticket.py` the period task's `COGA_TASK_BLACKBOARD`;
    a job run through `runner.run_entry` (`run_reported`) that exits non-zero
    has its stderr appended there as `## Recipe Failure`, which is what the
    sweep's run record reads. The console output the child produced is
    discarded by the sweep, so this section is the only reason the period keeps.
    """
    shutil.copytree(
        PACKAGED / "recurring" / "blocker-reminders",
        seeded / "recurring" / "blocker-reminders",
    )
    shutil.copy(
        PACKAGED / "bootstrap" / "workflows" / "blocker-reminders" / "run.md",
        _mkdir(seeded / "workflows" / "blocker-reminders") / "run.md",
    )
    cfg = load_config(seeded)
    ref = create_named(cfg, "blocker-reminders").ref
    script = ref.task_dir / SCRIPT_ENTRY_POINT
    stock = "from coga_edge.blocker_reminders import main"
    source = script.read_text(encoding="utf-8")
    assert source.count(stock) == 1
    script.write_text(source.replace(stock,
        "import sys\n"
        "import coga_edge.blocker_reminders as job\n"
        "def fail(cfg, argv):\n"
        "    sys.stderr.write('[blockers] webhook refused the reminder\\n')\n"
        "    return 2\n"
        "job.run_blocker_reminders = fail\n" + stock,
    ), encoding="utf-8", newline="\n")

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
    # Package-backed: no local definition, only an explicit selection. The
    # first admitted run creates the repo carrier from the packaged seed.
    _mkdir(seeded / "recurring")
    (seeded / "recurring" / "jobs.toml").write_text(
        "[jobs]\nphone-home = true\n", encoding="utf-8"
    )
    assert not (seeded / "recurring/phone-home").exists()
    cfg = load_config(seeded)
    outcome = create_named(cfg, "phone-home")
    assert outcome.created
    parent = seeded / "recurring/phone-home/ticket.md"
    assert sorted(p.name for p in parent.parent.iterdir()) == ["ticket.md"]
    assert parent.read_text(encoding="utf-8").startswith("---\n{}\n---\n<!-- coga:recurring-state -->")
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
    shutil.copytree(PACKAGED / "recurring" / "phone-home", seeded / "recurring" / "phone-home")
    shutil.copytree(
        PACKAGED / "bootstrap" / "workflows" / "phone-home", seeded / "workflows" / "phone-home"
    )
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
