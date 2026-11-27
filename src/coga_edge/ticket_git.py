"""Shared Git plumbing for the `git/ticket-enter` and `git/ticket-exit` scripts.

Ticket state (`<coga root>/tasks/**` and `<coga root>/log.md`) never lands on
a code branch: it lives on the base, and each step change publishes only the
current ticket and its log lines there. The checkout carries the live ticket
files and log across each branch switch, including attachment additions and
deletions.

Every helper stops at the first failure with Git's message and leaves local
state intact; nothing retries.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from coga.blackboard import read_dev_fields
from coga.taskfile import TaskFileError, split_body
from coga.ticket import Ticket, TicketError


class TicketGitError(Exception):
    """A refusal or failed Git operation; the message names it."""


def git(*args: str, check: bool = True, env: dict[str, str] | None = None,
        input: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], text=True, capture_output=True, check=check, env=env,
        input=input,
    )


def out(*args: str, env: dict[str, str] | None = None, input: str | None = None) -> str:
    try:
        return git(*args, env=env, input=input).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise TicketGitError(
            f"`git {' '.join(args)}` failed: {(exc.stderr or exc.stdout).strip()}"
        ) from exc


def run_op(operation: str, *args: str) -> None:
    """Run one Git operation with its output visible; fail naming it."""
    completed = subprocess.run(["git", *args], text=True)
    if completed.returncode != 0:
        raise TicketGitError(f"{operation} failed (exit {completed.returncode})")


def ref_tip(ref: str) -> str | None:
    completed = git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    return completed.stdout.strip() or None


def is_ancestor(a: str, b: str) -> bool:
    return git("merge-base", "--is-ancestor", a, b, check=False).returncode == 0


def current_branch() -> str:
    return out("branch", "--show-current")


# --- the ticket's place in the work tree ----------------------------------------


@dataclass(frozen=True)
class TicketPaths:
    """Work-tree-relative POSIX paths of the ticket state for one launch."""

    top: Path
    ticket: Path            # absolute ticket file
    ticket_rel: str         # the ticket file
    task_rel: str           # the task: the ticket file, or its directory
    task_is_dir: bool
    tasks_rel: str          # <coga root>/tasks
    log_rel: str            # <coga root>/log.md

    @property
    def carried(self) -> tuple[str, ...]:
        """Ticket state whose working copy crosses a branch switch."""
        attachments = _task_files(self, with_head=True) if self.task_is_dir else []
        return tuple(dict.fromkeys((self.ticket_rel, self.log_rel, *attachments)))


def ticket_paths() -> TicketPaths:
    top = Path(out("rev-parse", "--show-toplevel")).resolve()
    ticket = Path(os.environ["COGA_TASK_TICKET"]).resolve()
    task_dir = Path(os.environ["COGA_TASK_DIR"]).resolve()
    coga_root = Path(os.environ["COGA_COGA_OS_ROOT"]).resolve()

    def rel(path: Path) -> str:
        try:
            return path.relative_to(top).as_posix()
        except ValueError as exc:
            raise TicketGitError(f"{path} is outside the Git work tree {top}") from exc

    task_is_dir = ticket.name == "ticket.md" and ticket.parent == task_dir
    return TicketPaths(
        top=top,
        ticket=ticket,
        ticket_rel=rel(ticket),
        task_rel=rel(task_dir if task_is_dir else ticket),
        task_is_dir=task_is_dir,
        tasks_rel=rel(coga_root / "tasks"),
        log_rel=rel(coga_root / "log.md"),
    )


def dev_record(ticket: Path) -> dict[str, str]:
    try:
        _, region = split_body(Ticket.read(ticket).body)
    except (OSError, TicketError, TaskFileError):
        return {}
    return read_dev_fields(region or "")


def tracked_in_head(rel: str) -> bool:
    return git("cat-file", "-e", f"HEAD:{rel}", check=False).returncode == 0


def require_unstaged_carried_paths(paths: TicketPaths) -> None:
    pathspecs = [f":(top,literal){rel}" for rel in paths.carried]
    staged = out("diff", "--cached", "--name-only", "-z", "--", *pathspecs)
    if staged:
        raise TicketGitError(
            "Unstage the carried ticket or log before continuing: "
            + ", ".join(staged.rstrip("\0").split("\0"))
        )


# --- carrying live state across a switch -----------------------------------------


def switch_carrying(paths: TicketPaths, target: str, *switch_args: str) -> None:
    """Switch branches with the live ticket, attachments and audit log."""
    require_unstaged_carried_paths(paths)
    with tempfile.TemporaryDirectory() as temporary:
        backup = Path(temporary)
        carried = save_carried_files(paths, backup)
        switched = False
        try:
            clear_carried_changes(paths, carried)
            run_op(f"git switch {target}", "switch", "--no-overwrite-ignore", *switch_args)
            switched = True
        finally:
            restore_carried_files(paths, backup, carried, switched=switched)


def save_carried_files(paths: TicketPaths, backup: Path) -> tuple[str, ...]:
    carried = paths.carried
    for rel in carried:
        source = paths.top / rel
        if source.is_symlink() or source.is_file():
            destination = backup / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=False)
    return carried


def clear_carried_changes(paths: TicketPaths, carried: tuple[str, ...]) -> None:
    tracked = []
    for rel in carried:
        file = paths.top / rel
        if tracked_in_head(rel):
            tracked.append(rel)
        elif file.is_symlink() or file.is_file():
            file.unlink()
    if tracked:
        out("restore", "--source=HEAD", "--worktree", "--",
            *(f":(top,literal){rel}" for rel in tracked))


def restore_carried_files(
    paths: TicketPaths, backup: Path, carried: tuple[str, ...], *, switched: bool,
) -> None:
    # Include attachments present only on the destination. The live copy's
    # absence of those attachments is a deletion, including across a rebase.
    candidates = set(carried)
    if switched:
        candidates.update(paths.carried)
    for rel in sorted(candidates):
        file = paths.top / rel
        if file.is_symlink() or file.is_file():
            file.unlink()
    for rel in carried:
        source = backup / rel
        if source.is_symlink() or source.is_file():
            file = paths.top / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, file, follow_symlinks=False)


# --- publishing the ticket to the base ---------------------------------------------


_LOG_REF_RE = re.compile(r"^\S+ \S+ v1 \[([^\]]+)\] ")


def log_lines_for(text: str, slug: str) -> list[str]:
    return [
        line for line in text.splitlines(keepends=True)
        if (m := _LOG_REF_RE.match(line)) and m.group(1) == slug
    ]


def merged_log(base_text: str, local_text: str, slug: str) -> str:
    """The base's log plus this ticket's local lines it does not have yet."""
    present = set(base_text.splitlines(keepends=True))
    missing = [line for line in log_lines_for(local_text, slug) if line not in present]
    if not missing:
        return base_text
    if base_text and not base_text.endswith("\n"):
        base_text += "\n"
    return base_text + "".join(
        line if line.endswith("\n") else line + "\n" for line in missing
    )


def _task_files(
    paths: TicketPaths, env: dict[str, str] | None = None, *, with_head: bool = False,
) -> list[str]:
    """Select tracked and non-ignored ticket paths using the publication index."""
    if not paths.task_is_dir:
        return [paths.ticket_rel] if paths.ticket.is_file() else []
    entries = set(out(
        "ls-files", "--cached", "--others", "--exclude-standard", "--full-name",
        *(["--with-tree=HEAD"] if with_head else []),
        "-z", "--", f":(top,literal){paths.task_rel}/", env=env,
    ).split("\0"))
    root = Path(paths.task_rel)
    nested = {
        Path(entry).parent for entry in entries
        if entry.endswith("/ticket.md") and entry != paths.ticket_rel
    }
    selection = []
    for entry in sorted(entries):
        if not entry or entry.endswith("/"):
            continue
        parents = Path(entry).parents
        if any(
            parent in nested or (paths.top / parent / "ticket.md").is_file()
            for parent in parents if root in parent.parents
        ):
            continue
        selection.append(entry)
    return selection


def publish_ticket(paths: TicketPaths, *, slug: str, remote: str, base: str) -> str | None:
    """Push one commit onto `<remote>/<base>` with only this ticket's state.

    Returns the new commit, or None when the base already matches. The commit
    is built in a temporary index from `<remote>/<base>`; other tickets' files
    and unpushed local base commits are never published.
    """
    out("fetch", "--quiet", remote, base)
    remote_ref = f"refs/remotes/{remote}/{base}"
    parent = ref_tip(remote_ref)
    if parent is None:
        raise TicketGitError(f"`{remote}/{base}` does not exist after fetch")

    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        out("read-tree", parent, env=env)
        selected = _task_files(paths, env)
        if selected:
            out("add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul", env=env,
                input="".join(f":(top,literal){rel}\0" for rel in selected))

        base_log = git("show", f"{parent}:{paths.log_rel}", check=False)
        base_log_text = base_log.stdout if base_log.returncode == 0 else ""
        log_file = paths.top / paths.log_rel
        local_log = log_file.read_text(encoding="utf-8") if log_file.is_file() else ""
        log_text = merged_log(base_log_text, local_log, slug)
        if log_text != base_log_text:
            blob = out("hash-object", "-w", "--stdin", input=log_text)
            out("update-index", "--add", "--cacheinfo", f"100644,{blob},{paths.log_rel}", env=env)

        tree = out("write-tree", env=env)
    if tree == out("rev-parse", f"{parent}^{{tree}}"):
        return None
    commit = out("commit-tree", tree, "-p", parent, "-m", f"{slug}: ticket state")
    run_op(f"git push {remote} {commit[:12]}:{base}", "push", "--quiet", remote,
           f"{commit}:refs/heads/{base}")
    out("update-ref", remote_ref, commit)
    return commit


def fast_forward_base(paths: TicketPaths, base: str, commit: str) -> bool:
    """Move the checked-out local base to `commit` when it is an ancestor.

    Keep the working ticket and carry forward only pending audit appends.
    """
    local = ref_tip(f"refs/heads/{base}")
    if local is None or not is_ancestor(local, commit):
        print(
            f"ticket-exit: local `{base}` has commits not on the published "
            f"base; left it where it is",
            file=sys.stderr,
        )
        return False
    if current_branch() != base:
        out("update-ref", f"refs/heads/{base}", commit, local)
        return True
    try:
        require_unstaged_carried_paths(paths)
    except TicketGitError as exc:
        print(f"ticket-exit: published, but left local `{base}` where it is: {exc}",
              file=sys.stderr)
        return False
    before = git("show", f"{local}:{paths.log_rel}", check=False).stdout
    log = paths.top / paths.log_rel
    working = log.read_text(encoding="utf-8") if log.is_file() else ""
    if not working.startswith(before):
        print(f"ticket-exit: published, but local `{base}` has edits to existing audit "
              f"lines in {paths.log_rel}; reconcile them before fast-forwarding",
              file=sys.stderr)
        return False
    with tempfile.TemporaryDirectory() as temporary:
        backup = Path(temporary)
        carried = save_carried_files(paths, backup)
        merged = None
        try:
            clear_carried_changes(paths, carried)
            merged = git("merge", "--ff-only", "--quiet", commit, check=False)
            if merged.returncode == 0 and log.is_file():
                published = log.read_text(encoding="utf-8")
                present = set(published.splitlines())
                pending = [line for line in working[len(before):].splitlines()
                           if line and line not in present]
                if pending and published and not published.endswith("\n"):
                    published += "\n"
                saved_log = backup / paths.log_rel
                saved_log.parent.mkdir(parents=True, exist_ok=True)
                saved_log.write_text(published + "".join(f"{line}\n" for line in pending),
                                     encoding="utf-8")
        finally:
            restore_carried_files(paths, backup, carried,
                                  switched=merged is not None and merged.returncode == 0)
    if merged.returncode != 0:
        # The publish already landed; only the local catch-up failed.
        print(
            f"ticket-exit: published, but could not fast-forward local "
            f"`{base}`: {(merged.stderr or merged.stdout).strip()}",
            file=sys.stderr,
        )
        return False
    return True


__all__ = [
    "TicketGitError",
    "TicketPaths",
    "clear_carried_changes",
    "current_branch",
    "dev_record",
    "fast_forward_base",
    "git",
    "is_ancestor",
    "log_lines_for",
    "merged_log",
    "out",
    "publish_ticket",
    "ref_tip",
    "require_unstaged_carried_paths",
    "restore_carried_files",
    "run_op",
    "save_carried_files",
    "switch_carrying",
    "ticket_paths",
]
