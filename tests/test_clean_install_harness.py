from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from textwrap import dedent

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/clean-install/container.sh"


def _executable(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())
    path.chmod(0o755)


def _checksum_stub(bin_dir: Path) -> None:
    # The harness runs on Linux; its tests must not need host GNU coreutils.
    _executable(bin_dir / "sha256sum", f"""
        #!{sys.executable}
        import hashlib
        from pathlib import Path
        import sys

        filename = sys.argv[1]
        print(hashlib.sha256(Path(filename).read_bytes()).hexdigest(), "", filename)
    """)


@pytest.fixture
def install_env(tmp_path: Path, monkeypatch) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _checksum_stub(bin_dir)
    # Keep the host's installed coga out of PATH; only installation exposes it.
    for name in ("bash", "git", "mkdir", "tee"):
        (bin_dir / name).symlink_to(shutil.which(name))
    (bin_dir / "python").symlink_to(sys.executable)
    _executable(bin_dir / "id", "#!/bin/sh\nprintf '1000\\n'\n")
    stub = tmp_path / "coga-stub"
    _executable(stub, """
        #!/bin/sh
        if [ "$1" = "${COGA_TEST_FAIL:-}" ]; then
            echo 'synthetic installed-artifact failure' >&2
            exit 17
        fi
        if [ "$1" = ticket ]; then
            [ -t 0 ] && [ -t 1 ] || exit 19
        fi
        printf 'coga stub: %s\\n' "$*"
    """)
    _executable(bin_dir / "uv", """
        #!/bin/sh
        if [ "$1" = tool ] && [ "$2" = install ]; then
            [ "${COGA_TEST_FAIL:-}" != install ] || exit 17
            /bin/ln -s "$COGA_TEST_STUB" "$COGA_TEST_BIN/coga"
        fi
        printf 'uv stub: %s\\n' "$*"
    """)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("COGA_TEST_STUB", str(stub))
    monkeypatch.setenv("COGA_TEST_BIN", str(bin_dir))
    return dict(os.environ)


def _run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("mode", ["pypi", "wheel"])
def test_clean_install_reaches_init_from_selected_artifact(
    tmp_path: Path, install_env: dict[str, str], mode: str,
) -> None:
    args = [mode, "first-user"]
    if mode == "wheel":
        wheel = tmp_path / "wheel dir" / "coga-1.0-py3-none-any.whl"
        wheel.parent.mkdir()
        wheel.write_bytes(b"artifact")
        args.append(str(wheel))
    result = _run(install_env, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    steps = (evidence / "steps.txt").read_text()
    assert "PASS\tcoga init --user first-user" in steps
    assert "PASS\tcoga --version" in steps
    assert steps.splitlines()[-1] == "PASS\tcoga validate --json "
    assert ("uv tool install coga " in steps) == (mode == "pypi")
    if mode == "wheel":
        assert "coga-1.0-py3-none-any.whl" in steps
        assert "sha256sum" in steps
    assert "attended coga ticket has not run" in (evidence / "init-passed.txt").read_text()
    assert not (evidence / "ticket.txt").exists()


@pytest.mark.parametrize("failed_command", ["install", "--version", "init", "validate"])
def test_clean_install_preserves_failure_and_stops(
    install_env: dict[str, str], failed_command: str,
) -> None:
    install_env["COGA_TEST_FAIL"] = failed_command
    result = _run(install_env, "pypi", "first-user")
    assert result.returncode == 17
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    steps = (evidence / "steps.txt").read_text()
    assert "FAIL (exit 17)" in steps
    assert failed_command in steps.splitlines()[-1]
    assert not (evidence / "init-passed.txt").exists()


def test_clean_install_refuses_reuse(install_env: dict[str, str]) -> None:
    assert _run(install_env, "pypi", "first-user").returncode == 0
    result = _run(install_env, "pypi", "first-user")
    assert result.returncode == 2
    assert "start a new container" in result.stderr


def test_clean_install_ticket_keeps_terminal_stdio(install_env: dict[str, str]) -> None:
    assert _run(install_env, "pypi", "first-user").returncode == 0
    master, slave = os.openpty()
    try:
        result = subprocess.run(
            ["bash", str(SCRIPT), "ticket", "First task", "--agent", "claude"],
            env=install_env, stdin=slave, stdout=slave, stderr=slave,
        )
    finally:
        os.close(slave)
        os.close(master)
    assert result.returncode == 0
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    assert "ticket_exit_code=0" in (evidence / "ticket.txt").read_text()


def test_clean_install_main_builds_fetched_commit_not_working_tree(
    git_repo, tmp_path: Path, monkeypatch,
) -> None:
    script = git_repo.root / "scripts/clean-install/run.sh"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/clean-install/run.sh", script)
    source = git_repo.root / "package.txt"
    source.write_text("committed main\n")
    git_repo.git("add", "package.txt")
    git_repo.git("commit", "-m", "Package on main")
    git_repo.git("push", "origin", "main")
    main_sha = git_repo.git("rev-parse", "HEAD").strip()
    git_repo.checkout_branch("feature")
    source.write_text("uncommitted feature\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _checksum_stub(bin_dir)
    _executable(bin_dir / "docker", """
        #!/bin/sh
        [ "$1 $2" != 'container inspect' ] || exit 1
        printf 'docker stub: %s\\n' "$*"
    """)
    _executable(bin_dir / "uv", """
        #!/bin/sh
        # uv build --wheel --no-sources --out-dir OUTPUT SOURCE
        mkdir -p "$5"
        cp "$6/package.txt" "$5/coga-1.0-py3-none-any.whl"
    """)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("COGA_CLEAN_INSTALL_NETWORK", "host")
    result = subprocess.run(
        ["bash", str(script), "main", "clean-main"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = git_repo.root / ".coga/clean-install/clean-main"
    assert (evidence / "source.txt").read_text() == f"origin/main={main_sha}\n"
    wheel = evidence / "wheels/coga-1.0-py3-none-any.whl"
    assert wheel.read_text() == "committed main\n"
    assert source.read_text() == "uncommitted feature\n"
    assert "docker build --pull --network host -t coga-clean-install:py311" in result.stdout
    assert "docker create --network host --name clean-main" in result.stdout
    assert "network=host" in (evidence / "result.txt").read_text()
    assert git_repo.git("branch", "--show-current").strip() == "feature"
