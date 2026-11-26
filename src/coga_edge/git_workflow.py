"""Plain Git utilities shared by the branch, PR and merge workflow scripts."""

from __future__ import annotations

import re
import secrets
import subprocess


def git_output(*args: str, cwd: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).rstrip("\n")


def branch_slug_part(slug: str) -> str:
    """The branch-safe slug segment used in `coga/<slug-part>[-<hex6>]`."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-.")[:48] or "task"


def fresh_branch_name(slug: str, remote: str, cwd: str = ".") -> str:
    """A `coga/<slug-part>-<hex6>` name free locally and on `remote`."""
    refs = set(git_output("for-each-ref", "--format=%(refname)", cwd=cwd).splitlines())
    prefix = f"coga/{branch_slug_part(slug)}"
    for _ in range(8):
        name = f"{prefix}-{secrets.token_hex(3)}"
        if f"refs/heads/{name}" not in refs and f"refs/remotes/{remote}/{name}" not in refs:
            return name
    raise ValueError(f"No free branch name under {prefix}")


def _dirty_paths(porcelain_z: str) -> list[str]:
    """Paths named by NUL-delimited `git status --porcelain -z` output.

    Mirrors `git._changed_paths_under`: a rename or copy entry carries its
    source path in the following NUL field, and both endpoints are returned so
    a ticket renamed away from its committed path is still recognized.
    """
    fields = porcelain_z.split("\x00")
    paths: list[str] = []
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        if path:
            paths.append(path)
        if status[0] in ("R", "C") and i < len(fields):
            source = fields[i]
            i += 1
            if source:
                paths.append(source)
    return paths


def changed_paths(cwd: str, paths: tuple[str, ...] = ()) -> list[str]:
    return _dirty_paths(git_output(
        "--literal-pathspecs", "status", "--porcelain", "-z",
        "--untracked-files=all", "--", *paths, cwd=cwd,
    ))


def commit_state(cwd: str, paths: tuple[str, ...]) -> None:
    changed = sorted(set(changed_paths(cwd, paths)))
    if not changed:
        return
    subprocess.run(["git", "--literal-pathspecs", "add", "--", *changed], cwd=cwd, check=True)
    subprocess.run(
        ["git", "--literal-pathspecs", "commit", "--only", "-m", "Update Coga ticket state", "--", *changed],
        cwd=cwd, check=True,
    )


def verify_reviewed_tree(cwd: str, reviewed: str, head: str, paths: tuple[str, ...]) -> None:
    if not re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", reviewed):
        raise ValueError(f"reviewed: must be a full commit OID, got {reviewed!r}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", reviewed, head], cwd=cwd).returncode:
        raise ValueError(f"Reviewed commit {reviewed} is not an ancestor of {head}")
    for oid in git_output("rev-list", f"{reviewed}..{head}", cwd=cwd).splitlines():
        changes = git_output(
            "diff-tree", "-r", "-m", "--no-commit-id", "--name-only", "--no-renames", "-z",
            oid, cwd=cwd,
        )
        unexpected = set(changes.split("\0")) - {"", *paths}
        if unexpected:
            raise ValueError(f"Commit {oid} after review changed {', '.join(sorted(unexpected))}")
