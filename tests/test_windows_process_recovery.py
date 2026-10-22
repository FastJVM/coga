"""Native Job Object ownership survives inspection, cancellation and crashes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from coga import oscompat, recurring_runner as runner


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows Job Object recovery")


def _owned_checkout(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    parent = Path(tempfile.mkdtemp(prefix=f"{runner._CONTROL_WORKTREE_PREFIX}{root.name}-"))
    checkout = parent / "checkout"
    workspace = checkout / "coga"
    workspace.mkdir(parents=True)
    durable = root / "coga"
    durable.mkdir()
    log = workspace / ".coga/recurring-runs/run.md"
    log.parent.mkdir(parents=True)
    log.write_text("# Café — retained transcript\n", encoding="utf-8", newline="\n")
    return root, parent, checkout, durable


def test_windows_stale_recovery_retains_live_tree_then_preserves_transcript(tmp_path):
    root, parent, checkout, durable = _owned_checkout(tmp_path)
    owner = subprocess.Popen([sys.executable, "-c", "pass"])
    owner.wait(timeout=10)
    with oscompat.ProcessTree([sys.executable, "-c", "import time; time.sleep(60)"]) as tree:
        runner._write_control_worktree_owner(
            parent, root, "main", Path("coga"), pid=owner.pid,
            inner_state="running", inner_pgid=tree.identity,
        )
        assert runner._stale_owned_control_worktree(root, "main", checkout) is None
        assert tree.process.poll() is None
        tree.kill()
        tree.process.wait(timeout=10)
        assert tree.wait_empty(timeout=10)
        assert runner._stale_owned_control_worktree(root, "main", checkout) is not None
    runner._cleanup_control_worktree(root, "main", checkout, Path("coga"), durable)
    assert not parent.exists()
    assert (durable / ".coga/recurring-runs/run.md").read_text(encoding="utf-8") == "# Café — retained transcript\n"


def test_windows_interrupted_child_is_stopped_before_checkout_cleanup(tmp_path, monkeypatch):
    root, parent, checkout, durable = _owned_checkout(tmp_path)
    runner._write_control_worktree_owner(parent, root, "main", Path("coga"))
    tree = oscompat.ProcessTree([sys.executable, "-c", "import time; time.sleep(60)"])
    wait = tree.process.wait
    interrupted = False

    def interrupt_once(*args, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt()
        return wait(*args, **kwargs)

    monkeypatch.setattr(tree.process, "wait", interrupt_once)
    monkeypatch.setattr(runner, "_start_repo_recurring_process", lambda *args: tree)
    with pytest.raises(KeyboardInterrupt):
        runner._run_repo_recurring(
            checkout / "coga", force=False, interactive=False, agent_override=None,
            control_worktree=True, control_worktree_parent=parent,
        )
    assert tree.process.poll() is not None
    assert not oscompat.process_tree_is_running(tree.identity)
    runner._cleanup_control_worktree(root, "main", checkout, Path("coga"), durable)
    assert not parent.exists()
    assert (durable / ".coga/recurring-runs/run.md").is_file()


def test_windows_supervisor_death_terminates_grandchild_and_recovers(tmp_path):
    root, parent, checkout, durable = _owned_checkout(tmp_path)
    script = """
import json, sys, time
from pathlib import Path
from coga import oscompat, recurring_runner as runner
child_code = 'import subprocess, sys, time; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); print(p.pid,flush=True); time.sleep(60)'
with oscompat.ProcessTree([sys.executable, '-c', child_code], stdout=-1, text=True) as tree:
    runner._write_control_worktree_owner(Path(sys.argv[1]), Path(sys.argv[2]), 'main', Path('coga'), inner_state='running', inner_pgid=tree.identity)
    print(json.dumps({'grandchild':int(tree.process.stdout.readline()), 'tree':tree.identity}),flush=True)
    time.sleep(60)
"""
    supervisor = subprocess.Popen(
        [sys.executable, "-c", script, str(parent), str(root)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
    )
    try:
        evidence = json.loads(supervisor.stdout.readline())
        assert runner._stale_owned_control_worktree(root, "main", checkout) is None
        assert supervisor.poll() is None  # inspection must not kill the owner
        supervisor.kill()
        supervisor.wait(timeout=10)
        # Acquiring a process handle is non-destructive, and completion of
        # job cleanup is observed with a bounded wait before the assertion.
        import time

        deadline = time.monotonic() + 10
        while oscompat.process_is_running(evidence["grandchild"]) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not oscompat.process_is_running(evidence["grandchild"])
        assert runner._stale_owned_control_worktree(root, "main", checkout) is not None
        runner._cleanup_control_worktree(root, "main", checkout, Path("coga"), durable)
        assert not parent.exists()
        assert (durable / ".coga/recurring-runs/run.md").is_file()
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait(timeout=10)
