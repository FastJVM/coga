"""Seed a feature checkout's ignored local config without exposing its contents."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tomllib

_REEXEC_ENV = 'COGA_SEED_LOCAL_CONFIG_REEXEC'


def _reexec_under_coga_interpreter() -> int:
    """Re-run this script with the interpreter that owns the `coga` command.

    Under `uv tool install coga` or pipx the package lives in an isolated
    environment, so the ambient `python` this attachment is invoked with
    cannot import it. The installed console script's shebang names that
    environment's interpreter; run there instead of failing on import.
    """
    if os.environ.get(_REEXEC_ENV):
        print('Local config setup failed: the `coga` command\'s interpreter '
              'cannot import coga either.', file=sys.stderr)
        return 2
    console = shutil.which('coga')
    if console is None:
        print('Local config setup failed: coga is not importable and no `coga` '
              'command is on PATH.', file=sys.stderr)
        return 2
    with open(console, 'rb') as script:
        shebang = script.readline().decode('utf-8', 'replace').strip()
    if not shebang.startswith('#!'):
        print('Local config setup failed: coga is not importable and the `coga` '
              'command has no interpreter shebang.', file=sys.stderr)
        return 2
    interpreter = shebang[2:].split()
    env = dict(os.environ, **{_REEXEC_ENV: '1'})
    return subprocess.run([*interpreter, __file__, *sys.argv[1:]], env=env).returncode


try:
    from coga.config import load_config
except ImportError:
    if __name__ == '__main__':
        raise SystemExit(_reexec_under_coga_interpreter())
    raise


class SeedError(Exception):
    """A safe-to-print checkout setup failure."""


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', '-C', str(root), *args], capture_output=True, text=True,
    )
    if result.returncode:
        raise SeedError('Cannot verify checkout or ignored local config.')
    return result.stdout.strip()


def read_local(path: Path) -> tuple[bytes, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise SeedError('Local config must be an ordinary, unlinked file.')
    try:
        data = path.read_bytes()
        user = tomllib.loads(data.decode('utf-8')).get('user')
        if not isinstance(user, str) or not user.strip():
            raise ValueError('missing actor')
        load_config(path.parent)
    except Exception:
        # Config/parser exceptions may embed credential values. Never relay them.
        raise SeedError('Invalid local config; repair it in its owning checkout.') from None
    return data, user


def seed_local_config(source_workspace: Path, destination_checkout: Path) -> None:
    source_workspace = source_workspace.resolve()
    source_root = Path(git(source_workspace, 'rev-parse', '--show-toplevel')).resolve()
    destination_root = destination_checkout.resolve()
    if Path(git(destination_root, 'rev-parse', '--show-toplevel')).resolve() != destination_root:
        raise SeedError('Destination must be a Git checkout root.')
    relative = (source_workspace / 'coga.local.toml').relative_to(source_root)
    source = source_root / relative
    destination = destination_root / relative
    if destination.parent.resolve() != destination.parent:
        raise SeedError('Destination config directory must not be symlinked.')
    for root in (source_root, destination_root):
        if git(root, 'ls-files', '--', relative.as_posix()):
            raise SeedError('Local config must not be tracked or staged.')
        git(root, 'check-ignore', '--', relative.as_posix())
    data, actor = read_local(source)
    if destination.exists() or destination.is_symlink():
        _, existing_actor = read_local(destination)
        if existing_actor != actor:
            raise SeedError('Destination actor differs from primary checkout; refusing to overwrite.')
        destination.chmod(0o600)
    else:
        # Exclusive creation protects an existing file; restrict before writing.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, 'wb') as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(data)
            read_local(destination)
        except Exception:
            destination.unlink()
            raise
    if stat.S_IMODE(destination.stat().st_mode) != 0o600:
        raise SeedError('Cannot restrict local config permissions to 0600.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_workspace', type=Path, help='Primary directory containing coga.toml')
    parser.add_argument('destination_checkout', type=Path, help='Feature Git checkout root')
    args = parser.parse_args()
    try:
        seed_local_config(args.source_workspace, args.destination_checkout)
    except SeedError as exc:
        print(f'Local config setup failed: {exc}', file=sys.stderr)
        return 2
    except Exception:
        print('Local config setup failed: cannot read, copy, or restrict config permissions.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
