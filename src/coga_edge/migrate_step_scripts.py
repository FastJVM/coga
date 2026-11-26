"""One-time migration of in-flight branch tickets to `enter`/`exit` step scripts.

Branch workflows used to open their branch with an `open-branch` step (or the
closed `git: ticket-branch` launch mode) and carried ticket state on the
branch. They now declare `enter: git/ticket-enter` / `exit: git/ticket-exit`,
and ticket state lives on the base. A ticket's frozen workflow snapshot does
not follow its definition, so a ticket frozen earlier keeps the old shape.

Run from the repo, after upgrading coga::

    python -m coga_edge.migrate_step_scripts            # report only
    python -m coga_edge.migrate_step_scripts --apply    # publish one commit
    python -m coga_edge.migrate_step_scripts --path coga/tasks/<slug>.md

The default form reads every ticket on `<remote>/<base>` and reports what it
would rewrite; `--apply` pushes those rewrites as one commit built in a
temporary index, so local work and other branches are untouched. `--path`
rewrites one work-tree ticket in place: use it for a live copy that sits on a
checked-out branch.

For each ticket that is not done or canceled and whose snapshot still has an
`open-branch` step or `git: ticket-branch`, or whose workflow definition now
declares step scripts the snapshot lacks, the rewrite:

- adds the definition's `enter`/`exit` refs (the `git/ticket-*` pair when the
  definition declares none but the snapshot used a branch mode or step);
- drops `git: ticket-branch`;
- removes `open-branch` steps and renumbers `step`, so a ticket at
  `open-branch` resumes at the step after it.

Everything else in the ticket is kept. It never edits a branch: a branch that
still carries ticket state is named in the report for a person to clean.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coga.config import ConfigError, load_config
from coga.paths import resolve_workflow_path
from coga.ticket import Ticket, TicketError
from coga.workflow import Workflow, WorkflowError
from coga_edge.ticket_git import (
    TicketGitError,
    current_branch,
    git,
    is_ancestor,
    out,
    ref_tip,
    run_op,
)

PREFIX = "migrate-step-scripts"
BRANCH_STEP = "open-branch"
BRANCH_MODE = "ticket-branch"
DEFAULT_SCRIPTS = ("git/ticket-enter", "git/ticket-exit")
TERMINAL = {"done", "canceled"}


@dataclass(frozen=True)
class Rewrite:
    text: str
    notes: tuple[str, ...]


def _definition_scripts(cfg: Any, name: Any) -> tuple[str | None, str | None]:
    if not isinstance(name, str):
        return None, None
    try:
        definition = Workflow.load(resolve_workflow_path(cfg, name))
    except (OSError, WorkflowError):
        return None, None
    return definition.enter, definition.exit


def migrate_text(text: str, cfg: Any) -> Rewrite | None:
    """The migrated ticket text, or None when the ticket needs no change."""
    try:
        ticket = Ticket.parse(text)
    except TicketError:
        return None
    wf = ticket.workflow
    if ticket.status in TERMINAL or not isinstance(wf, dict):
        return None
    steps = wf.get("steps")
    if not isinstance(steps, list):
        return None

    branch_steps = [
        i for i, step in enumerate(steps, 1)
        if isinstance(step, dict) and step.get("name") == BRANCH_STEP
    ]
    mode = wf.get("git")
    enter, exit_ = _definition_scripts(cfg, wf.get("name"))
    if enter is None and exit_ is None and (branch_steps or mode == BRANCH_MODE):
        enter, exit_ = DEFAULT_SCRIPTS
    wants = {"enter": enter, "exit": exit_}
    missing = {k: v for k, v in wants.items() if v is not None and k not in wf}
    if not (branch_steps or mode == BRANCH_MODE or missing):
        return None
    if any(k in wf for k in wants) and missing:
        # A half-declared pair is someone's deliberate edit; leave it alone.
        return None

    notes: list[str] = []
    new_wf: dict[str, Any] = {"name": wf.get("name")}
    if mode is not None and mode != BRANCH_MODE:
        new_wf["git"] = mode
    elif mode == BRANCH_MODE:
        notes.append("dropped `git: ticket-branch`")
    for key in ("enter", "exit"):
        value = wf.get(key, wants[key])
        if value is not None:
            new_wf[key] = value
    if missing:
        notes.append("added " + ", ".join(f"`{k}: {v}`" for k, v in missing.items()))
    kept = [s for i, s in enumerate(steps, 1) if i not in branch_steps]
    new_wf["steps"] = kept
    for key, value in wf.items():
        if key not in new_wf and key not in ("git", "enter", "exit", "steps"):
            new_wf[key] = value
    ticket.frontmatter["workflow"] = new_wf

    index = ticket.step_index()
    if branch_steps and index is not None:
        new_index = index - sum(1 for i in branch_steps if i < index)
        if new_index > len(kept):
            return None  # nothing after `open-branch`; not a shape this migrates
        name = kept[new_index - 1].get("name")
        ticket.frontmatter["step"] = f"{new_index} ({name})"
        notes.append(
            f"removed `{BRANCH_STEP}`; step {ticket.step!r} was "
            f"{index} ({steps[index - 1].get('name')})"
        )
    return Rewrite(ticket.render(), tuple(notes))


# --- the base -------------------------------------------------------------------

def _ticket_entries(rev: str, tasks_rel: str) -> list[str]:
    listing = out("ls-tree", "-r", "-z", "--name-only", rev, "--", tasks_rel)
    return sorted(p for p in listing.split("\0") if p.endswith(".md"))


def plan_base(cfg: Any, rev: str, tasks_rel: str) -> dict[str, Rewrite]:
    plan: dict[str, Rewrite] = {}
    for rel in _ticket_entries(rev, tasks_rel):
        shown = git("show", f"{rev}:{rel}", check=False)
        if shown.returncode:
            continue
        rewrite = migrate_text(shown.stdout, cfg)
        if rewrite is not None and rewrite.text != shown.stdout:
            plan[rel] = rewrite
    return plan


def publish(plan: dict[str, Rewrite], *, remote: str, base: str, parent: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        out("read-tree", parent, env=env)
        for rel, rewrite in plan.items():
            blob = out("hash-object", "-w", "--stdin", input=rewrite.text)
            out("update-index", "--cacheinfo", f"100644,{blob},{rel}", env=env)
        tree = out("write-tree", env=env)
    commit = out(
        "commit-tree", tree, "-p", parent, "-m",
        f"Migrate {len(plan)} branch tickets to enter/exit step scripts",
    )
    run_op(f"git push {remote} {commit[:12]}:{base}", "push", "--quiet", remote,
           f"{commit}:refs/heads/{base}")
    out("update-ref", f"refs/remotes/{remote}/{base}", commit)
    return commit


def catch_up_local(base: str, commit: str) -> None:
    local = ref_tip(f"refs/heads/{base}")
    if local is None or not is_ancestor(local, commit):
        print(f"{PREFIX}: local `{base}` was left where it is; pull it", file=sys.stderr)
        return
    if current_branch() != base:
        out("update-ref", f"refs/heads/{base}", commit, local)
        return
    merged = git("merge", "--ff-only", "--quiet", commit, check=False)
    if merged.returncode:
        print(f"{PREFIX}: could not fast-forward local `{base}`: "
              f"{(merged.stderr or merged.stdout).strip()}; pull it", file=sys.stderr)


def report(plan: dict[str, Rewrite]) -> None:
    if not plan:
        print(f"{PREFIX}: no ticket needs migrating")
        return
    for rel, rewrite in plan.items():
        print(f"{rel}")
        for note in rewrite.notes:
            print(f"    {note}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coga_edge.migrate_step_scripts",
        description="Migrate in-flight branch tickets to enter/exit step scripts.",
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--base", default="main")
    parser.add_argument("--apply", action="store_true",
                        help="push the rewrites to <remote>/<base> as one commit")
    parser.add_argument("--path", type=Path,
                        help="rewrite this one work-tree ticket in place instead")
    args = parser.parse_args(argv)
    try:
        cfg = load_config(require_user=False)
        if args.path is not None:
            text = args.path.read_text(encoding="utf-8")
            rewrite = migrate_text(text, cfg)
            if rewrite is None or rewrite.text == text:
                print(f"{PREFIX}: {args.path} needs no change")
                return 0
            args.path.write_text(rewrite.text, encoding="utf-8")
            report({str(args.path): rewrite})
            return 0

        top = Path(out("-C", str(cfg.repo_root), "rev-parse", "--show-toplevel")).resolve()
        os.chdir(top)
        tasks_rel = (cfg.repo_root / "tasks").resolve().relative_to(top).as_posix()
        out("fetch", "--quiet", args.remote, args.base)
        parent = ref_tip(f"refs/remotes/{args.remote}/{args.base}")
        if parent is None:
            raise TicketGitError(f"`{args.remote}/{args.base}` does not exist after fetch")
        plan = plan_base(cfg, parent, tasks_rel)
        report(plan)
        if not plan or not args.apply:
            if plan:
                print(f"{PREFIX}: report only; rerun with --apply to publish")
            return 0
        commit = publish(plan, remote=args.remote, base=args.base, parent=parent)
        catch_up_local(args.base, commit)
        print(f"{PREFIX}: published {commit[:12]} to `{args.remote}/{args.base}`")
        return 0
    except TicketGitError as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 1
    except (OSError, ConfigError, ValueError, subprocess.SubprocessError) as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
