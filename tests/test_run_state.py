"""Managed run state: layout, tmp scope, sweep, attribution and temp routing."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import windows_skip

from coga import oscompat, run_state
from coga.compose import write_prompt_file
from coga.config import load_config
from coga.tasks import BootstrapRef, TaskRef
from coga.validate import emit_report, run as validate_run, validate_task

_SRC = Path(__file__).resolve().parents[1] / "src"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


def _ticket(path: Path, status: str = "active") -> None:
    _write(
        path,
        f"""
        ---
        title: {path.stem}
        status: {status}
        owner: marc
        contexts: []
        ---

        ## Description

        Something to do.

        <!-- coga:blackboard -->
        """,
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "repo" / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification]
        channels = []
        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(coga_os)
    return coga_os


def _ref(repo: Path, slug: str) -> TaskRef:
    directory, _, leaf = slug.rpartition("/")
    return TaskRef(leaf, repo / "tasks" / f"{slug}.md", directory or None, file_form=True)


def _age(path: Path, seconds: float) -> None:
    past = time.time() - seconds
    os.utime(path, (past, past))


# --- scope --------------------------------------------------------------------


def test_scope_redirects_temp_keeps_system_tmp_and_purges(repo: Path) -> None:
    cfg = load_config(repo)
    system = tempfile.gettempdir()
    with run_state.launch_tmp_scope(cfg) as scope:
        assert scope.path.parent == (repo / ".coga" / "tmp").resolve()
        assert len(scope.path.name) == 8
        assert (scope.path.parent / f"{scope.path.name}.lock").is_file()
        for name in run_state.TMP_ENV_NAMES:
            assert scope.env_overrides[name] == str(scope.path)
        assert scope.env_overrides["COGA_SYSTEM_TMPDIR"] == system
        (scope.path / "junk").write_text("x")
    assert not scope.path.exists()
    assert list((repo / ".coga" / "tmp").iterdir()) == []


def test_scope_preserves_an_inherited_system_tmpdir(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("COGA_SYSTEM_TMPDIR", str(tmp_path / "outer-system"))
    with run_state.launch_tmp_scope(load_config(repo)) as scope:
        assert scope.env_overrides["COGA_SYSTEM_TMPDIR"] == str(tmp_path / "outer-system")


@pytest.mark.parametrize("error", [RuntimeError, KeyboardInterrupt])
def test_scope_purges_on_exception(repo: Path, error: type[BaseException]) -> None:
    with pytest.raises(error):
        with run_state.launch_tmp_scope(load_config(repo)) as scope:
            (scope.path / "f").write_text("x")
            raise error()
    assert list((repo / ".coga" / "tmp").iterdir()) == []


def test_nested_scope_never_removes_the_parent(repo: Path) -> None:
    cfg = load_config(repo)
    with run_state.launch_tmp_scope(cfg) as outer:
        (outer.path / "keep").write_text("x")
        with run_state.launch_tmp_scope(cfg) as inner:
            assert inner.path != outer.path
            assert (outer.path / "keep").is_file()
        assert not inner.path.exists()
        assert (outer.path / "keep").is_file()


@windows_skip("Windows cannot unlink an open lock; nested-scope tests cover its lock lifetime.")
def test_launch_retries_if_sweep_retires_new_lock_before_acquisition(
    repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    tokens = iter(("aaaaaaaa", "bbbbbbbb"))
    monkeypatch.setattr(run_state.secrets, "token_hex", lambda _: next(tokens))
    real_lock = run_state.lock_fd

    def preempt(fd: int, *, blocking: bool) -> None:
        monkeypatch.setattr(run_state, "lock_fd", real_lock)
        assert [item.token for item in run_state.sweep_orphans(cfg).removed] == ["aaaaaaaa"]
        real_lock(fd, blocking=blocking)

    monkeypatch.setattr(run_state, "lock_fd", preempt)
    with run_state.launch_tmp_scope(cfg) as scope:
        assert scope.path.name == "bbbbbbbb"
        assert scope.path.with_suffix(".lock").is_file()
        assert not run_state.sweep_orphans(cfg).removed


def test_launch_keeps_directory_when_mkdir_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    path = run_state.tmp_root(cfg) / "aaaaaaaa"
    real_mkdir = Path.mkdir

    def already_created(directory: Path, *args, **kwargs) -> None:
        if directory == path:
            real_mkdir(path)
            (path / "keep").write_text("someone else's file")
        real_mkdir(directory, *args, **kwargs)

    monkeypatch.setattr(run_state.secrets, "token_hex", lambda _: "aaaaaaaa")
    monkeypatch.setattr(Path, "mkdir", already_created)
    with pytest.raises(FileExistsError):
        with run_state.launch_tmp_scope(cfg):
            pytest.fail("launch should not have started")
    assert (path / "keep").is_file()
    assert not path.with_suffix(".lock").exists()


@pytest.mark.parametrize("limit, warns", [(8, True), (4096, False)])
def test_scope_warns_about_long_socket_paths(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
    limit: int, warns: bool,
) -> None:
    monkeypatch.setattr(run_state, "SOCKET_WARN_BYTES", limit)
    with run_state.launch_tmp_scope(load_config(repo)) as scope:
        assert scope.path.is_dir()  # the long path is still used
    err = capsys.readouterr().err
    assert ("Unix socket paths" in err and str(scope.path) in err) is warns


def _read_only_tree(base: Path) -> Path:
    """A tree a tool left read-only, like a copytree of an installed package."""
    nested = base / "pkg" / "sub"
    nested.mkdir(parents=True)
    (nested / "file.py").write_text("x")
    (base / "pkg" / "top.txt").write_text("x")
    for path in (nested / "file.py", base / "pkg" / "top.txt", nested, base / "pkg"):
        path.chmod(0o444 if path.is_file() else 0o555)
    return base / "pkg"


def test_launch_purge_removes_read_only_trees(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with run_state.launch_tmp_scope(load_config(repo)) as scope:
        _read_only_tree(scope.path)
    assert "could not" not in capsys.readouterr().err
    assert not scope.path.exists()


def test_sweep_removes_read_only_orphans_without_touching_link_targets(
    repo: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "kept").write_text("x")
    outside.chmod(0o555)
    root = repo / ".coga" / "tmp"
    orphan = _orphan(root, "aaaaaaaa")
    pkg = _read_only_tree(orphan)
    pkg.chmod(0o755)
    (pkg / "link").symlink_to(outside, target_is_directory=True)
    pkg.chmod(0o555)
    try:
        result = run_state.sweep_orphans(load_config(repo))
        assert not result.failures
        assert [o.token for o in result.removed] == ["aaaaaaaa"]
        assert not orphan.exists()
        assert (outside / "kept").is_file()
        assert outside.stat().st_mode & 0o777 == 0o555
    finally:
        outside.chmod(0o755)


def test_validate_fix_removes_read_only_orphans(repo: Path) -> None:
    cfg = load_config(repo)
    orphan = _orphan(repo / ".coga" / "tmp", "aaaaaaaa")
    _read_only_tree(orphan)
    fixed = validate_run(cfg, fix=True)
    assert [f.path for f in fixed.fixes if f.kind == "orphan-tmp"] == [str(orphan)]
    assert not any(i.kind == "orphan-tmp" for i in fixed.issues)
    assert not orphan.exists()


def test_unremovable_orphan_reports_one_failure_per_area(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repo / ".coga" / "tmp"
    _orphan(root, "aaaaaaaa")
    _orphan(root, "bbbbbbbb")
    monkeypatch.setattr(
        run_state, "_remove_tree",
        lambda path: [f"{path}/{name}: denied" for name in ("a", "b", "c")],
    )
    failures = run_state.sweep_orphans(load_config(repo)).failures
    assert len(failures) == 2
    for token, failure in zip(("aaaaaaaa", "bbbbbbbb"), sorted(failures)):
        assert failure == (
            f"could not remove orphan tmp {root / token}: "
            f"{root / token}/a: denied (and 2 more)"
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX inode permissions")
def test_purge_keeps_modes_of_hard_linked_files_outside_the_area(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    outside.chmod(0o444)
    with run_state.launch_tmp_scope(load_config(repo)) as scope:
        pkg = _read_only_tree(scope.path)
        pkg.chmod(0o755)
        os.link(outside, pkg / "linked.txt")
        pkg.chmod(0o555)
    assert "could not" not in capsys.readouterr().err
    assert not scope.path.exists()
    assert outside.stat().st_mode & 0o777 == 0o444


def test_failed_purge_warns_and_leaves_the_rest_for_the_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_state, "_remove_tree", lambda path: [f"{path}/busy: in use"])
    with run_state.launch_tmp_scope(load_config(repo)) as scope:
        pass
    assert "could not fully remove launch tmp" in capsys.readouterr().err
    assert scope.path.is_dir()
    assert not (scope.path.parent / f"{scope.path.name}.lock").exists()


# --- sweep --------------------------------------------------------------------


def _orphan(root: Path, token: str, *, lock: bool = True, age: float = 0) -> Path:
    path = root / token
    path.mkdir(parents=True)
    (path / "left").write_text("orphan")
    if lock:
        (root / f"{token}.lock").write_text("")
    if age:
        _age(path, age)
    return path


def test_sweep_removes_unlocked_orphans_and_spares_live_and_young(repo: Path) -> None:
    cfg = load_config(repo)
    root = repo / ".coga" / "tmp"
    unlocked = _orphan(root, "aaaaaaaa")
    lockless_old = _orphan(root, "bbbbbbbb", lock=False, age=3600)
    lockless_young = _orphan(root, "cccccccc", lock=False)
    (root / "dddddddd.lock").write_text("")  # creation interrupted before mkdir
    (root / "not-a-token").mkdir()
    live = _orphan(root, "eeeeeeee")
    fd = os.open(root / "eeeeeeee.lock", os.O_RDWR)
    oscompat.lock_fd(fd, blocking=False)
    try:
        assert {o.token for o in run_state.find_orphans(cfg)} == {
            "aaaaaaaa", "bbbbbbbb", "dddddddd",
        }
        # Reporting removes and creates nothing.
        assert unlocked.is_dir() and (root / "dddddddd.lock").is_file()
        assert not (root / "bbbbbbbb.lock").exists()

        result = run_state.sweep_orphans(cfg)
    finally:
        os.close(fd)
    assert {o.token for o in result.removed} == {"aaaaaaaa", "bbbbbbbb", "dddddddd"}
    assert not result.failures
    assert not unlocked.exists() and not (root / "aaaaaaaa.lock").exists()
    assert not lockless_old.exists()
    assert not (root / "dddddddd.lock").exists()
    assert lockless_young.is_dir()
    assert live.is_dir() and (root / "eeeeeeee.lock").is_file()
    assert (root / "not-a-token").is_dir()


def test_launch_scope_sweeps_crashed_siblings(repo: Path) -> None:
    root = repo / ".coga" / "tmp"
    crashed = _orphan(root, "aaaaaaaa")
    with run_state.launch_tmp_scope(load_config(repo)):
        assert not crashed.exists()


def test_sweep_claims_old_lockless_directory_through_removal(
    repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    orphan = _orphan(run_state.tmp_root(cfg), "aaaaaaaa", lock=False, age=3600)
    real_remove = run_state._remove_tree

    def check_exclusive(path: Path) -> list[str]:
        assert path.with_suffix(".lock").is_file()
        assert not run_state.sweep_orphans(cfg).removed
        return real_remove(path)

    monkeypatch.setattr(run_state, "_remove_tree", check_exclusive)
    assert [item.path for item in run_state.sweep_orphans(cfg).removed] == [orphan]
    assert not orphan.exists()
    assert not orphan.with_suffix(".lock").exists()


def test_validate_reports_evidence_with_corrupt_owner_record(repo: Path) -> None:
    cfg = load_config(repo)
    path = run_state.data_root(cfg) / "tasks" / "broken"
    path.mkdir(parents=True)
    (path / run_state.OWNER_FILE).write_bytes(b"\xff")
    (path / "evidence").write_bytes(b"abc")

    report = validate_run(cfg)
    assert report.state is not None
    assert [(entry.owner, entry.bytes) for entry in report.state.entries] == [
        ("(unattributed)", 3),
    ]


def test_read_only_scope_never_sweeps(repo: Path) -> None:
    root = repo / ".coga" / "tmp"
    crashed = _orphan(root, "aaaaaaaa")
    with run_state.launch_tmp_scope(load_config(repo), sweep=False):
        pass
    assert crashed.is_dir()
    assert not (repo / ".coga" / "data").exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX lock retirement order")
def test_sweeper_holding_a_retired_lock_inode_does_not_delete(repo: Path) -> None:
    root = repo / ".coga" / "tmp"
    _orphan(root, "aaaaaaaa")
    # A sweeper opened the old lock inode, then the owner retired it and a new
    # lock file appeared at the path: the stale handle must not count.
    stale = os.open(root / "aaaaaaaa.lock", os.O_RDWR)
    (root / "aaaaaaaa.lock").unlink()
    fresh = os.open(root / "aaaaaaaa.lock", os.O_RDWR | os.O_CREAT, 0o600)
    oscompat.lock_fd(fresh, blocking=False)
    try:
        os.close(stale)
        assert run_state.find_orphans(load_config(repo)) == []
    finally:
        os.close(fresh)


# --- attribution and usage ----------------------------------------------------


def test_data_dirs_are_collision_free_and_attributed(repo: Path) -> None:
    cfg = load_config(repo)
    _ticket(repo / "tasks" / "foo.md")
    _ticket(repo / "tasks" / "foo" / "bar.md")
    _ticket(repo / "tasks" / "bootstrap" / "status.md")
    foo, bar, task_status = (_ref(repo, s) for s in ("foo", "foo/bar", "bootstrap/status"))
    boot_status = BootstrapRef("status", repo / "bootstrap" / "status")
    dirs = {run_state.task_data_dir(cfg, r) for r in (foo, bar, task_status, boot_status)}
    assert len(dirs) == 4

    for ref, payload in ((foo, "12345"), (bar, "1"), (task_status, "22"), (boot_status, "333")):
        path = run_state.ensure_task_data_dir(cfg, ref)
        (path / "f").write_text(payload)
    shared = repo / ".coga" / "data" / "_shared"
    shared.mkdir()
    (shared / "key").write_text("k")
    stray = repo / ".coga" / "data" / "stray" / "deep"
    stray.mkdir(parents=True)
    (stray / "x").write_text("xx")
    (repo / ".coga" / "data" / "tasks" / "loose").write_text("l")

    report = run_state.usage(cfg)
    by_path = {Path(e.path): e for e in report.entries}
    data = repo / ".coga" / "data"
    assert by_path[data / "tasks" / "foo"].owner == "foo"
    assert by_path[data / "tasks" / "foo"].bytes == 5  # excludes nested bar/
    assert by_path[data / "tasks" / "foo" / "bar"].owner == "foo/bar"
    assert by_path[data / "tasks" / "bootstrap" / "status"].owner == "bootstrap/status"
    assert by_path[data / "tasks" / "bootstrap" / "status"].target == "task"
    assert by_path[data / "bootstrap" / "status"].target == "bootstrap"
    assert by_path[shared].owner == "(shared)"
    assert by_path[data / "stray"].owner == "(unattributed)"
    assert by_path[data / "tasks" / "loose"].owner == "(unattributed)"
    assert report.total_bytes == 5 + 1 + 2 + 3 + 1 + 2 + 1

    only = run_state.usage(cfg, ref=bar)
    assert [Path(e.path) for e in only.entries] == [data / "tasks" / "foo" / "bar"]


def test_usage_never_follows_symlinks(repo: Path, tmp_path: Path) -> None:
    cfg = load_config(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big").write_bytes(b"x" * 10_000)
    shared = repo / ".coga" / "data" / "_shared"
    shared.mkdir(parents=True)
    (shared / "link").symlink_to(outside, target_is_directory=True)
    report = run_state.usage(cfg)
    assert report.total_bytes < 10_000


def test_linked_worktree_data_lives_in_the_primary_checkout(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    _write(primary / "coga" / "coga.toml", "version = 1\n[notification]\nchannels = []\n")
    _write(primary / "coga" / "coga.local.toml", 'user = "marc"\n')

    def git(*args: str, cwd: Path = primary) -> None:
        subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)

    git("init", "-b", "main")
    git("add", "coga/coga.toml")
    git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-m", "seed")
    linked = tmp_path / "linked"
    git("worktree", "add", str(linked), "-b", "side")
    _write(linked / "coga" / "coga.local.toml", 'user = "marc"\n')

    cfg = load_config(linked / "coga")
    assert run_state.data_root(cfg) == (primary / "coga" / ".coga" / "data").resolve()
    assert run_state.tmp_root(cfg) == linked / "coga" / ".coga" / "tmp"


# --- validate -----------------------------------------------------------------


def test_validate_reports_state_stale_data_and_fixes_orphans_repo_wide(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = load_config(repo)
    _ticket(repo / "tasks" / "live.md")
    _ticket(repo / "tasks" / "finished.md", status="done")
    for slug in ("live", "finished", "deleted"):
        ref = _ref(repo, slug)
        (run_state.ensure_task_data_dir(cfg, ref) / "evidence").write_text(slug)
    orphan = _orphan(repo / ".coga" / "tmp", "aaaaaaaa")

    report = validate_run(cfg)
    emit_report(report, json_output=True)
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    assert state["root"] == str(repo / ".coga")
    owners = {(e["owner"], e["kind"]) for e in state["entries"]}
    assert {("live", "data"), ("finished", "data"), ("deleted", "data"),
            ("(tmp)", "tmp-orphan")} <= owners
    assert state["total_bytes"] == sum(e["bytes"] for e in state["entries"])
    kinds = {(i["kind"], i["task"]) for i in payload["issues"]}
    assert ("stale-state", "finished") in kinds
    assert ("stale-state", "deleted") in kinds
    assert ("stale-state", "live") not in kinds
    assert ("orphan-tmp", "(state)") in kinds
    assert orphan.is_dir()

    # A scoped repair never sweeps tmp it does not report.
    scoped = validate_task(cfg, "live", fix=True)
    assert orphan.is_dir()
    assert [e.owner for e in scoped.state.entries] == ["live"]
    assert not any(i.kind == "orphan-tmp" for i in scoped.issues)

    fixed = validate_run(cfg, fix=True)
    assert not orphan.exists()
    assert any(f.kind == "orphan-tmp" for f in fixed.fixes)
    assert not any(i.kind == "orphan-tmp" for i in fixed.issues)
    # Durable state is never removed automatically.
    assert (repo / ".coga" / "data" / "tasks" / "finished" / "evidence").is_file()


def test_validate_text_prints_state_and_still_all_good(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = load_config(repo)
    _ticket(repo / "tasks" / "live.md")
    ref = _ref(repo, "live")
    (run_state.ensure_task_data_dir(cfg, ref) / "keep").write_text("abc")
    report = validate_run(cfg)
    assert not (repo / ".coga" / "tmp").exists()  # validate creates nothing
    emit_report(report, json_output=False)
    out = capsys.readouterr().out
    assert f"State: {repo / '.coga'} 3 B" in out
    assert "  live  data  3 B  1 files" in out


# --- Coga's own temp users ----------------------------------------------------


def test_coga_temp_users_resolve_to_system_tmpdir(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    managed = tmp_path / "managed"
    system = tmp_path / "system"
    managed.mkdir()
    system.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", None)
    monkeypatch.setenv("TMPDIR", str(managed))
    monkeypatch.setenv("COGA_SYSTEM_TMPDIR", str(system))
    assert oscompat.system_tmpdir() == str(system)
    assert oscompat.lock_dir("coga-test").parent == system
    ref = _ref(repo, "x")
    prompt = write_prompt_file("hi", ref)
    try:
        assert prompt.parent == system
    finally:
        prompt.unlink()

    monkeypatch.delenv("COGA_SYSTEM_TMPDIR")
    assert oscompat.system_tmpdir() == tempfile.gettempdir()


_ROUTED_TEMP_USERS = {
    "coga/repl_supervisor.py": 1,
    "coga/repl_supervisor_nt.py": 1,
    "coga/skill_manager.py": 3,
    "coga_edge/skill_update_pr.py": 1,
    "coga/compose.py": 1,
}


@pytest.mark.parametrize("module", sorted(_ROUTED_TEMP_USERS))
def test_every_coga_temp_call_names_the_system_tmpdir(module: str) -> None:
    """Coga's own temp files must pass `dir=` from `system_tmpdir()`."""
    tree = ast.parse((_SRC / module).read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "tempfile"
        and node.func.attr in {"mkdtemp", "mkstemp", "TemporaryDirectory", "NamedTemporaryFile"}
    ]
    assert len(calls) == _ROUTED_TEMP_USERS[module]
    for call in calls:
        dirs = [k.value for k in call.keywords if k.arg == "dir"]
        assert dirs, f"{module}:{call.lineno} has no dir="
        assert "system_tmpdir" in ast.unparse(dirs[0]), f"{module}:{call.lineno}"


def test_windows_prompt_placeholder_uses_system_tmpdir() -> None:
    source = (_SRC / "coga" / "launch.py").read_text(encoding="utf-8")
    assert "placeholder = Path(oscompat.system_tmpdir())" in source
    assert "tempfile.gettempdir" not in source
