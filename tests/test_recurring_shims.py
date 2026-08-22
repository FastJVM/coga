"""The five recurring templates' `ticket.py` deterministic halves.

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
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.launch_script import SCRIPT_ENTRY_POINT
from coga.recurring import create_named
from coga.runner import RECIPES
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
    ("digest", "digest"),
    ("skill-update", "skill-update"),
)


@pytest.mark.parametrize(("template", "recipe_name"), SHIMMED_TEMPLATES)
def test_shim_calls_the_registered_recipe_and_bumps_through_the_cli(
    template: str, recipe_name: str
) -> None:
    """Each shim imports core directly and completes its own step.

    Two things this pins. The import must resolve to the *same* function the
    `coga run` registry exposes — a typo would only surface on the next
    scheduled firing. And the step must be completed by subprocessing the CLI:
    calling the Typer command function in-process passes `OptionInfo`
    sentinels instead of real option defaults.
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

    assert imported.pop("load_config") == "coga.config"
    (symbol, module_name), = imported.items()
    module = importlib.import_module(module_name)
    assert getattr(module, symbol) is RECIPES[recipe_name]

    assert f"{symbol}(load_config(), [])" in source

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


def test_period_task_runs_its_shim_headlessly_and_closes_its_own_step(
    seeded: Path,
) -> None:
    """End-to-end: install a packaged template, create its period task, launch.

    `blocker-reminders` is the shim that can run for real in a fixture — no
    network, no `gh`, and a repo with nothing blocked is a clean no-op. The run
    proves the whole chain: `_create_at_slug` copies `ticket.py`, `coga launch`
    classifies the period task from that file, the recipe runs with no agent
    and no TTY (CliRunner supplies neither), and the shim's own `coga bump`
    finishes the one-step workflow.
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
    outcome = create_named(cfg, "blocker-reminders")
    ref = outcome.ref

    assert outcome.created is True
    assert (ref.task_dir / SCRIPT_ENTRY_POINT).is_file()
    # Only the reserved name travels; other template siblings stay put.
    assert sorted(path.name for path in ref.task_dir.iterdir()) == sorted(
        ("ticket.md", SCRIPT_ENTRY_POINT)
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert read_ticket(ref).status == "done"


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


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
