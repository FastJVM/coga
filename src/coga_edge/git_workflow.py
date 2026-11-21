"""Plain Git utilities shared by the PR and merge workflow scripts."""

from __future__ import annotations

import subprocess


def git_output(*args: str, cwd: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).rstrip("\n")


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
