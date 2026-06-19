"""Helpers for recognizing GitHub repository references."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def github_owner_repo(source: str) -> str | None:
    """Return ``owner/repo`` for common GitHub source forms.

    Accepts GitHub's shorthand (``owner/repo``), HTTPS URLs, SCP-style SSH
    URLs, and pip-style ``git+`` URL prefixes. The caller keeps the original
    source string for git/gh commands; this helper is only for comparison and
    user-facing GitHub API paths.
    """
    value = source.strip()
    if not value:
        return None
    value = git_clone_source(value)

    if "://" not in value:
        if value.startswith("git@github.com:"):
            return _owner_repo_from_path(value[len("git@github.com:") :])
        if ":" not in value and value.count("/") == 1:
            return _owner_repo_from_path(value)
        return None

    parsed = urlparse(value)
    if (parsed.hostname or "").lower() != "github.com":
        return None
    return _owner_repo_from_path(parsed.path)


def same_github_repo(left: str, right: str) -> bool:
    """True when two source strings point at the same GitHub owner/repo."""
    left_repo = github_owner_repo(left)
    right_repo = github_owner_repo(right)
    return bool(left_repo and right_repo and left_repo.lower() == right_repo.lower())


def is_ssh_git_source(source: str) -> bool:
    """True when ``source`` names an SSH-style git source."""
    value = git_clone_source(source)
    if value.startswith("git@"):
        return True
    if "://" not in value:
        return False
    return urlparse(value).scheme == "ssh"


def pip_git_source(source: str) -> str:
    """Return a pip-compatible git requirement source for ``source``."""
    value = source.strip()
    if value.startswith("git+"):
        return value
    if value.startswith("git@github.com:"):
        return "git+ssh://git@github.com/" + value[len("git@github.com:") :]
    return "git+" + value


def git_clone_source(source: str) -> str:
    """Return a source string suitable for `git clone`."""
    value = source.strip()
    if value.startswith("git+"):
        return value[len("git+") :]
    return value


def redacted_git_source(source: str) -> str:
    """Return ``source`` without credential-bearing URL userinfo."""
    value = git_clone_source(source)
    if "://" not in value:
        return value
    parsed = urlparse(value)
    if not parsed.hostname:
        return value
    strip_user = parsed.scheme in {"http", "https"} and parsed.username is not None
    strip_password = parsed.password is not None
    if not strip_user and not strip_password:
        return value

    host = parsed.hostname
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    userinfo = ""
    if strip_password and not strip_user and parsed.username is not None:
        userinfo = f"{parsed.username}@"
    return urlunparse(parsed._replace(netloc=f"{userinfo}{host}"))


def _owner_repo_from_path(path: str) -> str | None:
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not owner or not repo:
        return None
    return f"{owner}/{repo}"
