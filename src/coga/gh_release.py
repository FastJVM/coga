"""Install `gh` from its official GitHub release, for `coga init`.

`coga init` offers `gh` through the machine's package manager first. When no
usable manager exists, or its install fails, init falls back to this route:
download the pinned release archive for this platform and architecture,
verify it against a SHA-256 digest shipped in this module, and copy the one
`gh` binary into a user-writable directory on PATH. No package manager, no
sudo, no installer.

This module is the co-versioned part of `init`'s contract, imported only by
`coga.commands.init`. The digest table is the integrity anchor *because* it
ships in Coga's own release: a checksums file fetched from the same GitHub
release would prove only transport integrity. Nothing resolves "latest".

Pin maintenance: bump `GH_VERSION` by hand at each Coga release, and sooner
for a `gh` security release. Re-verify all six digests against
`https://github.com/cli/cli/releases/download/v<version>/gh_<version>_checksums.txt`
when doing so. Init installs `gh` only when it is missing and never upgrades
it; `gh` announces its own new releases.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import errno
import hashlib
import http.client
import io
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

GH_VERSION = "2.103.3"
RELEASE_BASE_URL = "https://github.com/cli/cli/releases/download"

# SHA-256 of each pinned release archive, keyed by (gh os name, gh arch name),
# copied from gh_<GH_VERSION>_checksums.txt in the same release.
GH_ASSET_SHA256: dict[tuple[str, str], str] = {
    ("macOS", "amd64"): "a2f86418f4350ae6e9ec60d5000bdf7665728436946a97fc27fe50e6ae752682",
    ("macOS", "arm64"): "d700207eae9ae98fe2b89535c2c087c07823d4628c56364695a5a07ef311c062",
    ("linux", "amd64"): "4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d",
    ("linux", "arm64"): "ee32df2323c8847f5fac6cb6b4b69ca75828e9329a8f22f677021f7b3306ce63",
    ("windows", "amd64"): "98d0cfa794721665d7973dd728c78aff7bd836d58f10f6d7a03568eccb0a22e0",
    ("windows", "arm64"): "197211c98687d7770ac331fe8a3b6c198c389108c1536cdbedf659fe4703e484",
}

# `sys.platform` -> (gh os name, archive extension). Always the archive, never
# the .pkg/.msi/.deb/.rpm installers, which need elevation.
_PLATFORMS: dict[str, tuple[str, str]] = {
    "darwin": ("macOS", "zip"),
    "win32": ("windows", "zip"),
    "linux": ("linux", "tar.gz"),
}
# Lowercased `platform.machine()` -> gh arch name. Anything else (i386,
# armv6/7) has no supported asset.
_ARCHES: dict[str, str] = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
}

DOWNLOAD_TIMEOUT_SECONDS = 60
# The real archives are well under 20 MB; refuse anything far larger.
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024


class ReleaseError(Exception):
    """The downloaded archive is unusable: wrong digest or bad contents."""


@dataclass(frozen=True)
class ReleaseAsset:
    """One pinned `gh` release archive and the binary inside it."""

    name: str
    url: str
    sha256: str
    binary: str


@dataclass(frozen=True)
class InstallPlan:
    """Where the binary would go; nothing is created until it is published."""

    directory: Path
    expected_on_path: bool


def release_asset(platform_name: str, machine: str) -> ReleaseAsset | None:
    """The pinned asset for `sys.platform`-style `platform_name` and `machine`."""
    os_arch = _PLATFORMS.get(platform_name)
    arch = _ARCHES.get(machine.lower())
    if os_arch is None or arch is None:
        return None
    os_name, extension = os_arch
    sha256 = GH_ASSET_SHA256.get((os_name, arch))
    if sha256 is None:
        return None
    name = f"gh_{GH_VERSION}_{os_name}_{arch}.{extension}"
    return ReleaseAsset(
        name=name,
        url=f"{RELEASE_BASE_URL}/v{GH_VERSION}/{name}",
        sha256=sha256,
        binary="gh.exe" if os_name == "windows" else "gh",
    )


def host_asset() -> ReleaseAsset | None:
    """The pinned asset for the running interpreter's platform and machine."""
    return release_asset(sys.platform, platform.machine())


def download(url: str) -> bytes:
    """Fetch `url` with a timeout and a size cap. The tests' network seam."""
    request = urllib.request.Request(url, headers={"User-Agent": "coga-init"})
    chunks: list[bytes] = []
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise OSError(
                        f"download exceeded {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB"
                    )
                chunks.append(chunk)
    except http.client.HTTPException as exc:
        raise OSError(f"download interrupted: {exc!r}") from exc
    return b"".join(chunks)


def verify(data: bytes, asset: ReleaseAsset) -> None:
    """Raise `ReleaseError` unless `data` hashes to the pinned digest."""
    actual = hashlib.sha256(data).hexdigest()
    if actual != asset.sha256:
        raise ReleaseError(
            f"checksum mismatch for {asset.name}: expected {asset.sha256}, got {actual}"
        )


def _is_binary_member(name: str, binary: str) -> bool:
    return PurePosixPath(name.replace("\\", "/")).parts[-2:] == ("bin", binary)


def extract_binary(archive: bytes, asset: ReleaseAsset) -> bytes:
    """Read the single `.../bin/<binary>` member; never extract anything else.

    The macOS and Linux archives wrap everything in `gh_<v>_<os>_<arch>/`,
    the Windows zip does not, so the member is matched by its trailing
    `bin/<binary>` rather than its full path.
    """
    try:
        if asset.name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(archive)) as zf:
                zip_matches = [
                    info
                    for info in zf.infolist()
                    if not info.is_dir() and _is_binary_member(info.filename, asset.binary)
                ]
                _require_one(len(zip_matches), asset)
                return zf.read(zip_matches[0])
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
            tar_matches = [
                member
                for member in tf.getmembers()
                if member.isreg() and _is_binary_member(member.name, asset.binary)
            ]
            _require_one(len(tar_matches), asset)
            extracted = tf.extractfile(tar_matches[0])
            if extracted is None:  # pragma: no cover - isreg() members always read
                raise ReleaseError(f"could not read bin/{asset.binary} in {asset.name}")
            return extracted.read()
    except (zipfile.BadZipFile, tarfile.TarError, EOFError) as exc:
        raise ReleaseError(f"{asset.name} is not a readable archive: {exc}") from exc


def _require_one(count: int, asset: ReleaseAsset) -> None:
    if count == 0:
        raise ReleaseError(f"bin/{asset.binary} is missing from {asset.name}")
    if count > 1:
        raise ReleaseError(f"bin/{asset.binary} appears {count} times in {asset.name}")


def on_path(directory: Path) -> bool:
    """True when `directory` is an entry of the current process's PATH."""
    resolved = directory.resolve() if directory.exists() else directory
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).resolve() == resolved:
                return True
        except OSError:
            continue
    return False


def _inside_home(directory: Path) -> bool:
    """True for a directory strictly inside the user's home.

    Everything else counts as a system directory (`/usr/local/bin`,
    `/opt/homebrew/bin`, `Program Files`, `WindowsApps`) and is never chosen,
    even when the coga shim lives there.
    """
    try:
        home = Path.home().resolve()
        resolved = directory.resolve()
    except (OSError, RuntimeError):
        return False
    return resolved != home and resolved.is_relative_to(home)


def _writable_target(directory: Path) -> bool:
    """An existing writable directory, or creatable under a writable one."""
    if os.path.lexists(directory):
        return directory.is_dir() and os.access(directory, os.W_OK)
    for ancestor in directory.parents:
        if os.path.lexists(ancestor):
            return ancestor.is_dir() and os.access(ancestor, os.W_OK)
    return False


def _in_virtualenv_prefix(directory: Path) -> bool:
    if sys.prefix == sys.base_prefix:
        return False
    try:
        return directory.resolve().is_relative_to(Path(sys.prefix).resolve())
    except OSError:
        return False


def plan_install_dir() -> InstallPlan | None:
    """Choose where `gh` would be installed, without creating anything.

    Candidates, first eligible wins: the directory the `coga` shim runs from
    (unless coga runs from a virtualenv and the shim is inside it, so a
    project `.venv/bin` never receives `gh`), `~/.local/bin`, then `~/bin` on
    POSIX. Eligible means on PATH, inside the home directory, and writable or
    creatable. With none eligible the plan is `~/.local/bin`, marked as
    expected off PATH, when it is writable or creatable; otherwise None.
    """
    home = Path.home()
    candidates: list[Path] = []
    coga = shutil.which("coga")
    if coga is not None:
        shim_dir = Path(coga).parent
        if not _in_virtualenv_prefix(shim_dir):
            candidates.append(shim_dir)
    local_bin = home / ".local" / "bin"
    candidates.append(local_bin)
    if os.name != "nt":
        candidates.append(home / "bin")
    for candidate in candidates:
        if on_path(candidate) and _inside_home(candidate) and _writable_target(candidate):
            return InstallPlan(candidate, expected_on_path=True)
    if _inside_home(local_bin) and _writable_target(local_bin):
        return InstallPlan(local_bin, expected_on_path=False)
    return None


def publish_binary(directory: Path, name: str, data: bytes) -> Path:
    """Write `data` to `directory/name` atomically, never replacing anything.

    Creates `directory` (only now, after consent and verification), writes a
    temp file beside the destination, then publishes it with an operation
    that fails when the destination exists: `os.link` on POSIX, `os.rename`
    on Windows. Never `os.replace`. A destination that exists in any form,
    including a dangling symlink, raises `FileExistsError` and is left
    untouched. The temp file is removed on every path.
    """
    dest = directory / name
    if os.path.lexists(dest):
        raise FileExistsError(errno.EEXIST, "already exists", str(dest))
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "nt":
            os.rename(tmp, dest)
        else:
            os.chmod(tmp, 0o755)
            os.link(tmp, dest)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
    return dest
