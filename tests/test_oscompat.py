"""Kernel-backed locks and descendant ownership on each native platform."""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from types import SimpleNamespace

import pytest

from coga import oscompat
from coga.git import state_lock


def test_nonblocking_lock_reports_contention_and_unlocks(tmp_path: Path) -> None:
    path = tmp_path / "lock"
    first = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    second = os.open(path, os.O_RDWR)
    try:
        oscompat.lock_fd(first, blocking=True)
        with pytest.raises(BlockingIOError):
            oscompat.lock_fd(second, blocking=False)
        oscompat.unlock_fd(first)
        oscompat.lock_fd(second, blocking=False)
        oscompat.unlock_fd(second)
    finally:
        os.close(second)
        os.close(first)


def test_state_lock_blocks_another_process_until_release(tmp_path: Path) -> None:
    script = """
import sys
from pathlib import Path
from types import SimpleNamespace
from coga.git import state_lock
print('waiting', flush=True)
with state_lock(SimpleNamespace(repo_root=Path(sys.argv[1]))):
    print('acquired', flush=True)
"""
    cfg = SimpleNamespace(repo_root=tmp_path)
    child = None
    with ThreadPoolExecutor(max_workers=1) as reader:
        try:
            with state_lock(cfg):
                with state_lock(cfg):  # same-thread reentrancy
                    child = subprocess.Popen(
                        [sys.executable, "-c", script, str(tmp_path)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    )
                    assert child.stdout.readline() == "waiting\n"
                    acquired = reader.submit(child.stdout.readline)
                    with pytest.raises(TimeoutError):
                        acquired.result(timeout=0.2)
            assert acquired.result(timeout=10) == "acquired\n"
            assert child.wait(timeout=10) == 0
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                child.wait()


def test_process_probe_does_not_terminate_a_live_owner() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert oscompat.process_is_running(child.pid)
        assert child.poll() is None
    finally:
        child.terminate()
        child.wait(timeout=10)
    assert not oscompat.process_is_running(child.pid)


def test_process_tree_stops_a_grandchild(tmp_path: Path) -> None:
    script = """
import subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
print(child.pid, flush=True)
time.sleep(60)
"""
    with oscompat.ProcessTree(
        [sys.executable, "-c", script], cwd=tmp_path,
        stdout=subprocess.PIPE, text=True,
    ) as tree:
        grandchild = int(tree.process.stdout.readline())
        assert oscompat.process_is_running(grandchild)
        assert tree.exists()
        tree.kill()
        tree.process.wait(timeout=10)
        # Querying a Windows process handle waits for termination without
        # sending a signal. POSIX may retain a zombie until init reaps it.
        if os.name == "nt":
            assert tree.wait_empty(timeout=10)
            assert not oscompat.process_is_running(grandchild)


def test_lock_directory_is_per_user() -> None:
    root = oscompat.lock_dir("coga-test-lock")
    assert root.parent == Path(__import__("tempfile").gettempdir())
    assert root.name.startswith("coga-test-lock-")
    assert "/" not in root.name and "\\" not in root.name
