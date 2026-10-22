from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from conftest import windows_skip, write_executable

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / 'src/coga/resources/templates/coga/bootstrap/skills/code/implement/seed_local_config.py'
SECRET = 'sentinel-credential-do-not-print'


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding="utf-8", stderr=subprocess.PIPE)


@pytest.fixture
def checkouts(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / 'primary'
    source.mkdir()
    git(source, 'init', '-b', 'main')
    git(source, 'config', 'user.email', 'test@example.com')
    git(source, 'config', 'user.name', 'Test')
    (source / 'coga').mkdir()
    (source / '.gitignore').write_text('coga.local.toml\n', encoding="utf-8", newline="\n")
    (source / 'coga/coga.toml').write_text('version = 1\n', encoding="utf-8", newline="\n")
    git(source, 'add', '.')
    git(source, 'commit', '-m', 'fixture')
    destination = tmp_path / 'feature'
    git(source, 'worktree', 'add', '-b', 'feature', str(destination))
    (source / 'coga/coga.local.toml').write_text(f'user = "test"\n[notification.slack]\nwebhook = "{SECRET}"\n', encoding="utf-8", newline="\n")
    return source, destination


def run_seed(source: Path, destination: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT / 'src'))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(source / 'coga'), str(destination)],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert SECRET not in result.stdout + result.stderr
    return result


@pytest.mark.parametrize('clone', [False, True])
def test_seed_fresh_checkout(checkouts: tuple[Path, Path], clone: bool) -> None:
    source, destination = checkouts
    if clone:
        destination = source.parent / 'clone'
        git(source, 'clone', '--no-hardlinks', str(source), str(destination))
    assert run_seed(source, destination).returncode == 0
    copied = destination / 'coga/coga.local.toml'
    assert copied.read_bytes() == (source / 'coga/coga.local.toml').read_bytes()
    if os.name == 'posix':
        assert copied.stat().st_mode & 0o777 == 0o600
    else:
        assert os.access(copied, os.W_OK)
    assert not copied.is_symlink()
    git(destination, 'add', '.')
    assert git(destination, 'diff', '--cached', '--name-only') == ''
    assert 'coga.local.toml' not in git(destination, 'ls-files')
    assert SECRET not in git(destination, 'show', 'HEAD')
    (destination / 'coga/coga.toml').write_text('version = 1\n# snapshot change\n', encoding="utf-8", newline="\n")
    snapshot = git(destination, 'stash', 'create').strip()
    assert snapshot
    assert 'coga.local.toml' not in git(destination, 'ls-tree', '-r', '--name-only', snapshot)
    assert SECRET not in git(destination, 'show', snapshot)


@pytest.mark.parametrize('mode', [0o600, 0o644, 0o666])
def test_seed_resume_preserves_contents(checkouts: tuple[Path, Path], mode: int) -> None:
    source, destination = checkouts
    local = destination / 'coga/coga.local.toml'
    contents = f'user = "test"\n# destination {SECRET}\n'
    local.write_text(contents, encoding="utf-8", newline="\n")
    local.chmod(mode)
    assert run_seed(source, destination).returncode == 0
    assert local.read_text(encoding="utf-8") == contents
    if os.name == 'posix':
        assert local.stat().st_mode & 0o777 == 0o600
    else:
        assert os.access(local, os.W_OK)


@pytest.mark.parametrize('contents', [None, 'user = [', 'user = ""', 'user = 4', f'user = "test"\n[notification]\nchannels = ["{SECRET}"]'])
def test_seed_rejects_invalid_source(checkouts: tuple[Path, Path], contents: str | None) -> None:
    source, destination = checkouts
    local = source / 'coga/coga.local.toml'
    if contents is None:
        local.unlink()
    else:
        local.write_text(contents, encoding="utf-8", newline="\n")
    assert run_seed(source, destination).returncode == 2
    assert not (destination / 'coga/coga.local.toml').exists()


@pytest.mark.parametrize('contents', ['user = "other"', 'user = ['])
def test_seed_rejects_destination_without_overwriting(checkouts: tuple[Path, Path], contents: str) -> None:
    source, destination = checkouts
    local = destination / 'coga/coga.local.toml'
    local.write_text(contents, encoding="utf-8", newline="\n")
    original = (source / 'coga/coga.local.toml').read_bytes()
    assert run_seed(source, destination).returncode == 2
    assert local.read_text(encoding="utf-8") == contents
    assert (source / 'coga/coga.local.toml').read_bytes() == original


def test_seed_rejects_symlink(checkouts: tuple[Path, Path]) -> None:
    source, destination = checkouts
    (destination / 'coga/coga.local.toml').symlink_to(source / 'coga/coga.local.toml')
    assert run_seed(source, destination).returncode == 2



@windows_skip("POSIX local-config permission restriction")
def test_seed_permission_failure_is_fatal(checkouts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy

    source, destination = checkouts
    local = destination / 'coga/coga.local.toml'
    local.write_text('user = "test"\n', encoding="utf-8", newline="\n")
    local.chmod(0o644)
    helper = runpy.run_path(str(SCRIPT))

    def refuse_chmod(self: Path, mode: int) -> None:
        raise PermissionError('permission denied')

    monkeypatch.setattr(Path, 'chmod', refuse_chmod)
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), str(source / 'coga'), str(destination)])
    assert helper['main']() == 2
    assert local.read_text(encoding="utf-8") == 'user = "test"\n'
    assert local.stat().st_mode & 0o777 == 0o644


@pytest.mark.parametrize('tracked', [False, True])
def test_seed_refuses_unignored_or_tracked_config(checkouts: tuple[Path, Path], tracked: bool) -> None:
    source, destination = checkouts
    if tracked:
        local = destination / 'coga/coga.local.toml'
        local.write_text('user = "test"\n', encoding="utf-8", newline="\n")
        git(destination, 'add', '-f', 'coga/coga.local.toml')
    else:
        (destination / '.gitignore').write_text('', encoding="utf-8", newline="\n")
    assert run_seed(source, destination).returncode == 2


def test_checkout_guidance_invokes_helper_for_creation_and_resume() -> None:
    bootstrap = REPO_ROOT / 'src/coga/resources/templates/coga/bootstrap'
    for relative in ['skills/code/implement/SKILL.md', 'workflows/docs/with-review.md']:
        text = (bootstrap / relative).read_text(encoding="utf-8")
        assert 'seed_local_config.py /primary/repo/coga /feature/repo' in text
        assert 'sandbox clone fallback' in text
        assert 'resume' in text


def _isolated_env(tmp_path: Path, *, with_console: bool) -> dict[str, str]:
    """An environment whose ambient python cannot import coga.

    Mirrors `uv tool install` / pipx: the package is importable only through
    the interpreter named by the `coga` console script's shebang.
    """
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    env['PATH'] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    if with_console:
        if os.name == 'nt':
            # The helper reads the wheel launcher's embedded shebang, without
            # executing the console entrypoint itself.
            (bin_dir / 'coga.exe').write_bytes(
                b'MZ launcher stub\x00' + f'#!"{sys.executable}"\n'.encode('utf-8')
                + b'PK\x03\x04zip payload stub'
            )
        else:
            interpreter = write_executable(bin_dir / 'coga-python', f'''
                import os, sys
                os.environ['PYTHONPATH'] = {str(REPO_ROOT / 'src')!r}
                os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
            ''')
            console = bin_dir / 'coga'
            console.write_text(f'#!{interpreter}\nraise SystemExit("not the real cli")\n', encoding="utf-8", newline="\n")
            console.chmod(0o755)
    return env


def test_seed_reexecs_under_the_coga_console_interpreter(
    checkouts: tuple[Path, Path], tmp_path: Path,
) -> None:
    source, destination = checkouts
    env = _isolated_env(tmp_path, with_console=True)
    # `-S` skips site-packages, so the editable test install is invisible to
    # the ambient interpreter exactly as under an isolated tool install.
    result = subprocess.run(
        [sys.executable, '-S', str(SCRIPT), str(source / 'coga'), str(destination)],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert SECRET not in result.stdout + result.stderr
    assert result.returncode == 0, result.stderr
    copied = destination / 'coga/coga.local.toml'
    assert copied.read_bytes() == (source / 'coga/coga.local.toml').read_bytes()
    if os.name == 'posix':
        assert copied.stat().st_mode & 0o777 == 0o600
    else:
        assert os.access(copied, os.W_OK)


def test_seed_fails_loud_without_coga_or_its_console_script(
    checkouts: tuple[Path, Path], tmp_path: Path,
) -> None:
    source, destination = checkouts
    env = _isolated_env(tmp_path, with_console=False)
    env['PATH'] = str(tmp_path / 'bin')
    result = subprocess.run(
        [sys.executable, '-S', str(SCRIPT), str(source / 'coga'), str(destination)],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert result.returncode == 2
    assert 'Local config setup failed: coga is not importable' in result.stderr
    assert not (destination / 'coga/coga.local.toml').exists()
