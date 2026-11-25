"""Launch-boundary hook for `git: ticket-branch` workflows.

`enter` runs before launch reads the ticket. It finds or creates the ticket's
branch, switches to it and records the Git fields under `## Dev`. `exit` runs
when the launch ends on any path. It commits every non-ignored change, pushes
the branch and switches back to the starting branch. Both stop at the first
ambiguous state or Git failure and leave the checkout for a person to fix.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from coga.blackboard import read_dev_fields, set_dev_fields
from coga.taskfile import TaskFileError, read_blackboard, replace_blackboard, split_body
from coga.ticket import Ticket, TicketError
from coga_edge.git_workflow import branch_slug_part, changed_paths, fresh_branch_name

STATE_FILE = "git-ticket-branch.json"
PREFIX = "ticket-branch"


class HookError(Exception):
    """A refusal or failed Git operation; the message names it."""


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], text=True, capture_output=True, check=check)


def out(*args: str) -> str:
    try:
        return git(*args).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise HookError(f"`git {' '.join(args)}` failed: {exc.stderr.strip()}") from exc


def run_op(operation: str, *args: str) -> None:
    """Run one Git operation with its output visible; fail naming it."""
    completed = subprocess.run(["git", *args], text=True)
    if completed.returncode != 0:
        raise HookError(f"{operation} failed (exit {completed.returncode})")


def ref_tip(ref: str) -> str | None:
    completed = git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    return completed.stdout.strip() or None


def is_ancestor(a: str, b: str) -> bool:
    return git("merge-base", "--is-ancestor", a, b, check=False).returncode == 0


def state_path() -> Path:
    tmp = os.environ.get("TMPDIR")
    if not tmp:
        raise HookError("TMPDIR is not set; run this hook through `coga launch`")
    return Path(tmp) / STATE_FILE


def ticket_relpath(top: Path, ticket: Path) -> str:
    try:
        return ticket.resolve().relative_to(top).as_posix()
    except ValueError as exc:
        raise HookError(f"ticket {ticket} is outside the Git work tree {top}") from exc


def dev_fields_of_text(text: str) -> dict[str, str]:
    try:
        _, region = split_body(Ticket.parse(text).body)
    except (TicketError, TaskFileError):
        return {}
    return read_dev_fields(region or "")


def blob_text(ref: str, relpath: str) -> str | None:
    completed = git("show", f"{ref}:{relpath}", check=False)
    return completed.stdout if completed.returncode == 0 else None


def tracked_on(branch: str, relpath: str) -> bool:
    return git("cat-file", "-e", f"{branch}:{relpath}", check=False).returncode == 0


def warn_if_only_on_branch(start: str, relpath: str) -> None:
    if ref_tip(f"refs/heads/{start}") and not tracked_on(start, relpath):
        print(
            f"{PREFIX}: warning: ticket exists only on its branch; commit it on "
            f"`{start}` so later launches can find it ({relpath})",
            file=sys.stderr,
        )


def remotes() -> list[str]:
    return sorted(out("remote").splitlines(), key=len, reverse=True)


def candidates(slug: str, relpath: str) -> dict[str, dict[str, str]]:
    """Branches named for `slug` whose own ticket copy records that branch.

    Returns `{branch name: {"local"|<remote>: full ref}}`.
    """
    part = re.escape(branch_slug_part(slug))
    pattern = re.compile(rf"coga/{part}(?:-[0-9a-f]{{6}})?")
    names = remotes()
    found: dict[str, dict[str, str]] = {}
    for ref in out("for-each-ref", "--format=%(refname)", "refs/heads/coga/", "refs/remotes/").splitlines():
        if ref.startswith("refs/heads/"):
            name, where = ref.removeprefix("refs/heads/"), "local"
        else:
            rest = ref.removeprefix("refs/remotes/")
            remote = next((r for r in names if rest.startswith(f"{r}/")), None)
            if remote is None:
                continue
            name, where = rest.removeprefix(f"{remote}/"), remote
        if not pattern.fullmatch(name):
            continue
        text = blob_text(ref, relpath)
        if text is None or dev_fields_of_text(text).get("branch") != name:
            continue
        found.setdefault(name, {})[where] = ref
    return found


def refuse_diverged(name: str, refs: dict[str, str]) -> None:
    local = refs.get("local")
    if local is None:
        return
    local_tip = ref_tip(local)
    for where, ref in refs.items():
        if where == "local":
            continue
        tip = ref_tip(ref)
        if local_tip and tip and local_tip != tip and not (
            is_ancestor(local_tip, tip) or is_ancestor(tip, local_tip)
        ):
            raise HookError(
                f"local `{name}` and `{ref.removeprefix('refs/remotes/')}` have "
                "diverged; reconcile them by hand, then launch again"
            )


def refuse_dirty(start: str, target: str, top: Path) -> None:
    dirty = sorted(set(changed_paths(str(top))))
    if dirty:
        listing = "\n".join(f"  {path}" for path in dirty[:20])
        more = f"\n  ... and {len(dirty) - 20} more" if len(dirty) > 20 else ""
        raise HookError(
            f"cannot switch from `{start}` to `{target}` with uncommitted "
            f"changes:\n{listing}{more}\nRun `coga sync`, or commit or stash "
            "them, then launch again."
        )


def write_state(path: Path, **state: str) -> None:
    path.write_text(json.dumps(state), encoding="utf-8")


def enter() -> int:
    ticket = Path(os.environ["COGA_TASK_TICKET"])
    slug = os.environ["COGA_TASK_SLUG"]
    state_file = state_path()
    top = Path(out("rev-parse", "--show-toplevel")).resolve()
    relpath = ticket_relpath(top, ticket)
    start = out("branch", "--show-current")
    if not start:
        raise HookError("HEAD is detached; switch to a branch, then launch again")

    fields = read_dev_fields(read_blackboard(ticket)) if ticket.is_file() else {}
    recorded = fields.get("branch")
    create = False
    if recorded:
        missing = [key for key in ("base", "remote") if not fields.get(key)]
        if missing:
            raise HookError(
                f"`## Dev` records branch: {recorded} without "
                f"{' or '.join(f'{key}:' for key in missing)}; complete the "
                "record by hand, then launch again"
            )
        branch, base, remote = recorded, fields["base"], fields["remote"]
        refs = {
            where: ref
            for where, ref in (
                ("local", f"refs/heads/{branch}"),
                (remote, f"refs/remotes/{remote}/{branch}"),
            )
            if ref_tip(ref)
        }
        if not refs:
            raise HookError(
                f"the recorded branch `{branch}` exists neither locally nor as "
                f"`{remote}/{branch}`; fetch it or fix `## Dev`, then launch again"
            )
    else:
        found = candidates(slug, relpath)
        if len(found) > 1:
            raise HookError(
                "more than one branch records this ticket: "
                + ", ".join(f"`{name}`" for name in sorted(found))
                + "; keep one, then launch again"
            )
        if found:
            branch, refs = next(iter(found.items()))
            text = blob_text(refs.get("local") or next(iter(refs.values())), relpath) or ""
            branch_fields = dev_fields_of_text(text)
            missing = [key for key in ("base", "remote") if not branch_fields.get(key)]
            if missing:
                raise HookError(
                    f"`{branch}` records branch: {branch} without "
                    f"{' or '.join(f'{key}:' for key in missing)}; complete the "
                    "record on that branch, then launch again"
                )
            base, remote = branch_fields["base"], branch_fields["remote"]
        else:
            create = True
            base = start
            remote = out(
                "for-each-ref", "--format=%(upstream:remotename)", f"refs/heads/{start}"
            ) or "origin"
            name = f"coga/{branch_slug_part(slug)}"
            taken = ref_tip(f"refs/heads/{name}") or ref_tip(f"refs/remotes/{remote}/{name}")
            branch = fresh_branch_name(slug, remote, str(top)) if taken else name
            refs = {}

    if not create:
        refuse_diverged(branch, refs)
    switch = branch != start
    if switch:
        refuse_dirty(start, branch, top)

    # Written before any switch so an interrupt after it still lets exit
    # return to the starting branch.
    write_state(state_file, start=start, branch=branch, remote=remote, slug=slug, base=base)
    try:
        if create:
            run_op("git switch -c", "switch", "-c", branch)
        elif switch:
            if "local" in refs:
                run_op("git switch", "switch", branch)
            else:
                tracking = refs.get(remote) or next(iter(refs.values()))
                run_op(
                    "git switch", "switch", "-c", branch, "--track",
                    tracking.removeprefix("refs/remotes/"),
                )
    except HookError:
        if out("branch", "--show-current") == start:
            state_file.unlink(missing_ok=True)
        raise

    if create:
        region = read_blackboard(ticket)
        replace_blackboard(
            ticket, set_dev_fields(region, branch=branch, base=base, remote=remote)
        )
        print(f"{PREFIX}: created `{branch}` from `{start}`", file=sys.stderr)
    elif switch:
        print(f"{PREFIX}: switched to `{branch}`", file=sys.stderr)
    warn_if_only_on_branch(start if switch or create else base, relpath)
    return 0


def handoff_message(slug: str, ticket: Path) -> str:
    if not ticket.is_file():
        return f"{slug}: launch handoff (ticket removed)"
    try:
        parsed = Ticket.read(ticket)
        step = parsed.current_step()
    except (OSError, UnicodeError, TicketError):
        return f"{slug}: launch handoff (unreadable ticket)"
    if step is not None:
        return f"{slug}: launch handoff at {step['name']}"
    return f"{slug}: launch handoff ({parsed.status})"


def exit_() -> int:
    state_file = state_path()
    if not state_file.is_file():
        return 0  # enter never got as far as choosing a branch
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        start, branch, remote, slug = (
            state["start"], state["branch"], state["remote"], state["slug"]
        )
        base = state.get("base") or start
    except (OSError, ValueError, KeyError) as exc:
        raise HookError(f"cannot read the enter state {state_file}: {exc}") from exc
    ticket = Path(os.environ["COGA_TASK_TICKET"])
    top = Path(out("rev-parse", "--show-toplevel")).resolve()

    current = out("branch", "--show-current")
    if current != branch:
        raise HookError(
            f"HEAD is on `{current or 'a detached commit'}`, not the ticket "
            f"branch `{branch}`; nothing was committed or pushed"
        )
    removed = not ticket.is_file()
    run_op("git add -A", "add", "-A")
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        run_op("git commit", "commit", "-q", "-m", handoff_message(slug, ticket))
    run_op(f"git push {remote} {branch}", "push", "-u", remote, branch)
    if start != branch:
        run_op(f"git switch {start}", "switch", start)
        print(f"{PREFIX}: pushed `{branch}` and returned to `{start}`", file=sys.stderr)
    if not removed:
        warn_if_only_on_branch(start if start != branch else base, ticket_relpath(top, ticket))
    state_file.unlink(missing_ok=True)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in {"enter", "exit"}:
        print("usage: run.py enter|exit", file=sys.stderr)
        return 2
    try:
        return enter() if argv[0] == "enter" else exit_()
    except HookError as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError, TaskFileError) as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
