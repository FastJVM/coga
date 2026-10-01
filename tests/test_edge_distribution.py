from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_phone_home_is_a_forkable_edge_module():
    import coga_edge.phone_home as phone_home

    tree = ast.parse(Path(phone_home.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert (node.module or '').split('.')[0] in sys.stdlib_module_names | {'coga'}
        elif isinstance(node, ast.Import):
            assert all(alias.name.split('.')[0] in sys.stdlib_module_names | {'coga'} for alias in node.names)
    assert callable(phone_home.main)
    assert callable(phone_home._worker_main)


def test_kernel_does_not_load_edge_implementations():
    # Resource shims belong to the edge; production core must never select them.
    for source in (ROOT / 'src/coga').rglob('*.py'):
        if 'resources' in source.relative_to(ROOT / 'src/coga').parts:
            continue
        assert 'coga_edge' not in source.read_text(), source


# Build two actual artifacts once. The report wording changes while metadata
# stays identical: a version-string assertion cannot accidentally prove this.
@pytest.fixture(scope="module")
def edge_wheels(tmp_path_factory):
    root = tmp_path_factory.mktemp("edge-wheels")
    wheels = {}
    for label in ("A", "B"):
        source = root / label
        source.mkdir()
        for name in ("pyproject.toml", "README.md"):
            shutil.copyfile(ROOT / name, source / name)
        shutil.copytree(ROOT / "src", source / "src", ignore=shutil.ignore_patterns(
            "__pycache__", ".venv", ".coga", ".agent-skills", ".claude", ".codex",
        ))
        module = source / "src/coga_edge/phone_home.py"
        module.write_text(module.read_text().replace("## Phone home\\n", f"## Phone home {label}\\n"))
        result = subprocess.run([
            sys.executable, "-m", "pip", "wheel", "--no-build-isolation", "--no-deps",
            str(source), "-w", str(source / "dist"),
        ], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        [wheels[label]] = (source / "dist").glob("*.whl")
    return wheels


def _install(wheel, installed):
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "--no-deps", "--upgrade",
        "--target", str(installed), str(wheel),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def _run(root, env, *args):
    result = subprocess.run([sys.executable, *args], cwd=root, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def _initialized_repo(tmp_path, wheel):
    installed = tmp_path / "installed"
    _install(wheel, installed)
    root = tmp_path / "company"
    root.mkdir()
    guard = tmp_path / "transport-guard"
    guard.mkdir()
    # Also guard fresh worker/CLI processes without changing admission. Any
    # network attempt leaves evidence even if worker error handling catches it.
    (guard / "sitecustomize.py").write_text(
        "import http.client\nfrom pathlib import Path\n"
        "def forbidden(*a, **kw):\n"
        f"    Path({str(guard / 'called')!r}).touch()\n"
        "    raise AssertionError('production transport called')\n"
        "http.client.HTTPSConnection = forbidden\n"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(installed), str(guard))), "CI": "true"}
    _run(root, env, "-c", '''
import subprocess
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner
from coga.cli import app
from coga.config import load_config
from coga.recurring import create_named
subprocess.run(["git", "init", "-b", "main"], check=True, capture_output=True)
subprocess.run(["git", "config", "user.name", "Test"], check=True)
subprocess.run(["git", "config", "user.email", "test@example.test"], check=True)
with patch("coga.commands.init._check_external_dependencies"):
    result = CliRunner().invoke(app, ["init", ".", "--user", "tester"])
assert result.exit_code == 0, result.output
local = Path("coga/coga.local.toml")
local.write_text(local.read_text() + "\\n[git]\\nenabled = false\\n")
result = create_named(load_config(Path("coga")), "phone-home")
assert result.created
assert (result.ref.task_dir / "ticket.py").read_bytes() == Path("coga/recurring/phone-home/ticket.py").read_bytes()
''')
    return root, installed, env, guard


@pytest.mark.parametrize("fork", ["none", "template", "period"])
def test_installed_wheel_upgrade_preserves_shims_and_full_forks(tmp_path, edge_wheels, fork):
    root, installed, env, guard = _initialized_repo(tmp_path, edge_wheels["A"])
    template = root / "coga/recurring/phone-home/ticket.py"
    period = root / "coga/tasks/recurring/phone-home/ticket.py"
    if fork != "none":
        source = (installed / "coga_edge/phone_home.py").read_text()
        destination = template if fork == "template" else period
        destination.write_text(source.replace("## Phone home A\\n", "## Phone home FORK\\n"))
        if fork == "template":
            # Recreate only before B, proving real recurring creation copies
            # the fork. The resulting period must survive the wheel upgrade.
            shutil.rmtree(period.parent)
            _run(root, env, "-c", '''
from pathlib import Path
from coga.config import load_config
from coga.recurring import create_named
assert create_named(load_config(Path("coga")), "phone-home").created
''')
            assert period.read_bytes() == template.read_bytes()
    before = {p: p.read_bytes() for p in (template, period)}
    for script in (template, period):
        expected = "FORK" if fork == "template" or (fork == "period" and script == period) else "A"
        output = _run(root, env, str(script))
        assert f"## Phone home {expected}" in output
        assert "capture suppressed; receipt suppressed" in output
    # Installation itself must not touch any repo file, including state.
    snapshot = {p: p.read_bytes() for p in (root / "coga").rglob("*") if p.is_file()}
    _install(edge_wheels["B"], installed)
    assert snapshot == {p: p.read_bytes() for p in (root / "coga").rglob("*") if p.is_file()}
    for script in (template, period):
        expected = "FORK" if fork == "template" or (fork == "period" and script == period) else "B"
        assert f"## Phone home {expected}" in _run(root, env, str(script))
        assert script.read_bytes() == before[script]
    # Selection comes from the period's file; it never consults the template.
    template.unlink()
    expected = "B" if fork == "none" else "FORK"
    assert f"## Phone home {expected}" in _run(root, env, str(period))
    assert period.read_bytes() == before[period]
    _run(root / "coga", env, "-m", "coga.cli", "launch", "recurring/phone-home")
    from coga.ticket import Ticket
    assert Ticket.read(period.with_suffix(".md")).status == "done"
    assert f"## Phone home {expected}" in period.with_suffix(".md").read_text()
    assert period.read_bytes() == before[period]
    assert not template.exists()
    assert not (guard / "called").exists()
    # Both the installed implementation and the copied fork carry their own
    # private entry, which independently preserves production suppression.
    worker = period if fork != "none" else installed / "coga_edge/phone_home.py"
    assert _run(root, env, str(worker), "--worker", "capture", str(root / "coga")).strip() == "suppressed"


@pytest.mark.parametrize("missing", [False, True])
def test_installed_shim_launch_completes_or_fails_without_agent(tmp_path, edge_wheels, missing):
    root, installed, env, guard = _initialized_repo(tmp_path, edge_wheels["B"])
    if missing:
        shutil.rmtree(installed / "coga_edge")
        # The developer interpreter may have an editable source path. Block
        # fallback imports too, to model a genuinely missing wheel module.
        with (guard / "sitecustomize.py").open("a") as stream:
            stream.write(
                "import sys\n"
                "class MissingEdge:\n"
                "    def find_spec(self, fullname, path=None, target=None):\n"
                "        if fullname == 'coga_edge':\n"
                "            raise ModuleNotFoundError('No module named coga_edge')\n"
                "sys.meta_path.insert(0, MissingEdge())\n"
            )
    # No TTY and no executable agent. The actual CLI must finish or return
    # the script's failure, never fall through to an agent success.
    (installed / "bin/git").symlink_to(shutil.which("git"))
    env["PATH"] = str(installed / "bin")
    result = subprocess.run([
        sys.executable, "-m", "coga.cli", "launch", "recurring/phone-home",
    ], cwd=root / "coga", env=env, capture_output=True, text=True, timeout=30)
    period = root / "coga/tasks/recurring/phone-home/ticket.md"
    from coga.ticket import Ticket
    ticket = Ticket.read(period)
    log = (root / "coga/log.md").read_text()
    if missing:
        assert result.returncode != 0
        assert "ModuleNotFoundError" in result.stdout + result.stderr
        assert "script exited with code 1" in log
        assert ticket.status == "in_progress"
        assert "task done" not in log
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert ticket.status == "done"
        assert log.count("task done") == 1
        assert "[system] task done" in log
        assert "## Phone home B" in period.read_text()
    assert "launched as a script" in log
    assert not (guard / "called").exists()


FIXTURES = ROOT / "tests/fixtures/edge-migration"
RUNBOOK = ROOT / "docs/contexts/coga/packaging/edge-code-upgrades.md"


def _operator_command(name, root, env, *, success=True):
    import re
    document = RUNBOOK.read_text()
    match = re.search(rf"<!-- migration:{name} -->\n```sh\n(.*?)\n```", document, re.S)
    assert match, name
    result = subprocess.run(["bash", "-c", match[1]], cwd=root, env=env,
                            capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    return result.stdout


@pytest.mark.parametrize("layout", ["user", "tool-link"])
def test_documented_interpreter_uses_console_script_shebang(tmp_path, layout):
    scripts = tmp_path / "bin"
    scripts.mkdir()
    # A separate venv proves that resolving the Python symlink would lose
    # the environment even though the base interpreter remains executable.
    venv = tmp_path / "tool"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    interpreter = venv / "bin/python"
    launcher = scripts / "coga" if layout == "user" else venv / "bin/coga"
    launcher.write_text(f"#!{interpreter}\nraise AssertionError('do not run coga')\n")
    launcher.chmod(0o755)
    if layout == "tool-link":
        (scripts / "coga").symlink_to(launcher)
    assert not (scripts / "python").exists()
    env = {**os.environ, "PATH": str(scripts) + os.pathsep + os.environ["PATH"]}
    assert _operator_command("interpreter", tmp_path, env).strip() == str(interpreter)


@pytest.mark.parametrize("shebang", ["#!/bin/sh", "#!/usr/bin/env python3", "#!/missing/python3"])
def test_documented_interpreter_refuses_unknown_launcher(tmp_path, shebang):
    launcher = tmp_path / "coga"
    launcher.write_text(f"{shebang}\nexit 0\n")
    launcher.chmod(0o755)
    env = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]}
    _operator_command("interpreter", tmp_path, env, success=False)


def test_documented_legacy_adoption_preserves_state_and_reconciles_callers(tmp_path, edge_wheels):
    root, installed, env, guard = _initialized_repo(tmp_path, edge_wheels["A"])
    env["PATH"] = str(installed / "bin") + os.pathsep + env["PATH"]
    env["COGA_PY"] = _operator_command("interpreter", root, env).strip()
    template = root / "coga/recurring/phone-home/ticket.py"
    period = root / "coga/tasks/recurring/phone-home/ticket.py"
    parked = root / "coga/tasks/_parked/phone-home/ticket.py"
    edited = root / "coga/recurring/_custom-phone-home/ticket.py"
    legacy = (FIXTURES / "phone-home-old.py").read_bytes()
    for path in (template, period, parked, edited):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(legacy)
    parked.with_suffix(".md").write_text(period.with_suffix(".md").read_text().replace("status: active", "status: paused"))
    period.with_suffix(".md").write_text(period.with_suffix(".md").read_text().replace("status: active", "status: blocked"))
    edited.write_bytes(legacy + b"\n# Committed local customization\n")
    edited_before = edited.read_bytes()
    unrelated = period.parent / "notes.txt"
    unrelated.write_bytes(b"unrelated attachment\r\n")
    # Nonzero parent telemetry state and cursor, plus frozen period workflow,
    # generation and blackboard, must survive the migration, not be reseeded.
    parent = template.with_suffix(".md")
    parent.write_text(parent.read_text().replace('"run":0', '"run":41').replace(
        '"repo_id":null', '"repo_id":"dd2433c0-7277-4a63-8640-c73089700480"'))
    with period.with_suffix(".md").open("a") as stream:
        stream.write("\nExisting findings remain.\n")
    dream_paths = [root / f"coga/{path}/dream/ticket.md" for path in (
        "recurring", "tasks/recurring", "tasks/_parked",
    )]
    dream_old = (FIXTURES / "dream-old.md").read_bytes()
    for path in dream_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(dream_old)
    # Other init batteries are inventoried too: no slug-based ownership guess.
    expected = sorted(str(p.relative_to(root)) for base in (root / "coga/recurring", root / "coga/tasks")
                      for p in base.rglob("*.py"))
    assert _operator_command("inventory", root, env).splitlines() == expected
    assert {str(p.relative_to(root)) for p in (template, period, parked, edited)} <= set(expected)
    callers = _operator_command("callers", root, env).splitlines()
    assert len(callers) == 9
    for path in dream_paths:
        entries = [line for line in callers if line.startswith(str(path.relative_to(root)) + ":")]
        assert len(entries) == 3
        assert all(any(name in line for line in entries) for name in (
            "coga run validate-drift", "coga run cleanup-orphan-markers", "coga run delete-task"))
    # Git cleanliness is deliberately irrelevant: even a committed fork is
    # compared against the old artifact's bytes.
    subprocess.run(["git", "add", "coga"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "legacy fixture"], cwd=root, check=True, capture_output=True)
    env["OLD_SOURCE"] = str(FIXTURES / "phone-home-old.py")
    for path in (template, period, parked, edited):
        env["CANDIDATE"] = str(path)
        label = "review" if path == edited else "stock"
        assert _operator_command("compare", root, env) == f"{label}: {path}\n"
    env["OLD_SOURCE"] = str(tmp_path / "unknown-baseline")
    assert _operator_command("compare", root, env).startswith("review:")
    env["OLD_SOURCE"] = str(FIXTURES / "phone-home-old.py")
    # No installation or executable replacement may alter markdown/state.
    preserved = {p: p.read_bytes() for p in (root / "coga").rglob("*") if p.is_file() and p.suffix != ".py"}
    _install(edge_wheels["B"], installed)
    implementation, shim = _operator_command("locate", root, env).splitlines()
    assert Path(implementation) == installed / "coga_edge/phone_home.py"
    env["NEW_SHIM"] = shim
    for path in (template, period, parked):
        env["CANDIDATE"] = str(path)
        _operator_command("replace", root, env)
        assert path.read_bytes() == Path(shim).read_bytes()
    env["CANDIDATE"] = str(edited)
    _operator_command("replace", root, env, success=False)
    assert edited.read_bytes() == edited_before
    assert all(p.read_bytes() == raw for p, raw in preserved.items())
    # Representative, explicitly selected replacement passages; no Dream
    # implementation or production command is introduced by this fixture.
    for path in dream_paths:
        before = path.read_bytes()
        after = before
        for number, name in enumerate(("validate-drift", "cleanup-orphan-markers", "delete-task")):
            old = f"coga run {name}".encode()
            new = f"python /fixture-only/{name}.py".encode()
            old_file = tmp_path / f"old-{number}.txt"
            new_file = tmp_path / f"new-{number}.txt"
            old_file.write_bytes(old)
            new_file.write_bytes(new)
            env.update(CANDIDATE=str(path), OLD_PASSAGE=str(old_file), NEW_PASSAGE=str(new_file))
            _operator_command("reconcile", root, env)
            after = after.replace(old, new, 1)
        assert path.read_bytes() == after
        assert path.read_bytes().split(b"<!-- coga:blackboard -->")[1] == before.split(b"<!-- coga:blackboard -->")[1]
        assert path.read_bytes().split(b"---", 2)[1] == before.split(b"---", 2)[1]
    _operator_command("callers", root, env, success=False)
    # A stale passage never silently overwrites custom text.
    _operator_command("reconcile", root, env, success=False)
    for path in (template, period, parked):
        assert "## Phone home B" in _run(root, env, str(path))
    assert edited.read_bytes() == edited_before
    assert unrelated.read_bytes() == b"unrelated attachment\r\n"
    assert not (guard / "called").exists()
