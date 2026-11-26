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

The default form reads the base tickets and checks their branches for newer
state. `--apply` publishes the rewrites on the base and removes legacy ticket
state from affected code branches in the same atomic push. `--path` rewrites
one work-tree ticket in place.

For each ticket that is not done or canceled and whose snapshot still has an
`open-branch` step or `git: ticket-branch`, or whose workflow definition now
declares step scripts the snapshot lacks, the rewrite:

- adds the definition's `enter`/`exit` refs (the `git/ticket-*` pair when the
  definition declares none but the snapshot used a branch mode or step);
- drops `git: ticket-branch`;
- removes `open-branch` steps and renumbers `step`, so a ticket at
  `open-branch` resumes at the step after it.

The branch's copy wins when the base still matches the branch point.
Reconcile conflicts, unpublished branch work, or a different recorded base
before applying the migration.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from coga.blackboard import read_dev_fields
from coga.config import Config, ConfigError, load_config
from coga.lifecycle import TERMINAL_STATUSES
from coga.paths import resolve_workflow_path
from coga.taskfile import TaskFileError, split_body
from coga.ticket import Ticket, TicketError
from coga.workflow import Workflow, WorkflowError
from coga_edge.ticket_git import (
    TicketGitError,
    current_branch,
    git,
    is_ancestor,
    merged_log,
    out,
    ref_tip,
    run_op,
)

PREFIX = "migrate-step-scripts"
BRANCH_STEP = "open-branch"
BRANCH_MODE = "ticket-branch"
DEFAULT_SCRIPTS = ("git/ticket-enter", "git/ticket-exit")


@dataclass(frozen=True)
class Rewrite:
    text: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class BranchUpdate:
    name: str
    tip: str
    ancestor: str


@dataclass(frozen=True)
class TreeEntry:
    mode: str
    oid: str


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
    if ticket.status in TERMINAL_STATUSES or not isinstance(wf, dict):
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


def _show_text(rev: str, rel: str) -> str | None:
    shown = git("show", f"{rev}:{rel}", check=False)
    return shown.stdout if shown.returncode == 0 else None


def _branch_fields(ticket: Ticket) -> dict[str, str]:
    _, blackboard = split_body(ticket.body, blackboard_required=False)
    return read_dev_fields(blackboard or "")


def _tree_entry(rev: str, rel: str) -> TreeEntry | None:
    row = out("ls-tree", "-z", "--full-tree", rev, "--", rel)
    if not row:
        return None
    mode, _, oid = row.partition("\t")[0].split()
    return TreeEntry(mode, oid)


def _attachments(
    rel: str, changed: list[str], branch: str, ancestor: str,
) -> list[str]:
    if PurePosixPath(rel).name != "ticket.md":
        return []
    root = PurePosixPath(rel).parent
    result = []
    for path in changed:
        if path == rel or not path.startswith(f"{root}/"):
            continue
        if any(
            _tree_entry(rev, str(parent / "ticket.md")) is not None
            for parent in PurePosixPath(path).parents if root in parent.parents
            for rev in (branch, ancestor)
        ):
            continue
        result.append(path)
    return result


def plan_branches(
    cfg: Config,
    plan: dict[str, Rewrite],
    *,
    parent: str,
    tasks_rel: str,
    log_rel: str,
    remote: str,
    base: str,
) -> tuple[list[BranchUpdate], dict[str, TreeEntry | None], str, list[str]]:
    """Use branch-only state when it can move to the base without ambiguity."""
    remote_prefix = f"refs/remotes/{remote}/"
    local_prefix = "refs/heads/"
    refs = out("for-each-ref", "--format=%(refname)", remote_prefix, local_prefix).splitlines()
    branches: list[BranchUpdate] = []
    attachments: dict[str, TreeEntry | None] = {}
    log = _show_text(parent, log_rel) or ""
    blockers = []
    seen: set[str] = set()
    for ref in refs:
        local = ref.startswith(local_prefix)
        name = ref.removeprefix(local_prefix if local else remote_prefix)
        if name in {base, "HEAD"}:
            continue
        tracking = ref_tip(remote_prefix + name)
        tip = out("rev-parse", ref)
        if local and tracking and is_ancestor(tip, tracking):
            continue
        common = git("merge-base", parent, tip, check=False)
        if common.returncode != 0:
            continue
        ancestor = common.stdout.strip()
        changed = out(
            "diff", "--no-renames", "--name-only", "-z", ancestor, tip, "--", tasks_rel,
        ).rstrip("\0").split("\0")
        for rel in changed:
            if not rel.endswith(".md"):
                continue
            text = _show_text(tip, rel)
            if text is None:
                continue
            try:
                ticket = Ticket.parse(text)
                fields = _branch_fields(ticket)
            except (TicketError, TaskFileError):
                continue
            if fields.get("branch") != name or fields.get("remote") != remote:
                continue
            rewrite = migrate_text(text, cfg)
            if rewrite is None and rel not in plan:
                continue
            label = f"{rel} on {name}"
            if rewrite is None:
                if ticket.status in TERMINAL_STATUSES or (
                    isinstance(ticket.workflow, dict)
                    and any(key in ticket.workflow for key in ("enter", "exit"))
                ):
                    rewrite = Rewrite(text, ())
                else:
                    blockers.append(f"{label}: the branch workflow could not be migrated")
                    continue
            if local:
                blockers.append(f"{label}: reconcile the local branch with {remote} first")
                continue
            if fields.get("base") != base:
                recorded = fields.get("base")
                blockers.append(
                    f"{label} ({ticket.status}, {ticket.step}): "
                    f"recorded base {recorded!r} differs from {base!r}"
                )
                continue
            at_base = _show_text(parent, rel)
            if at_base is not None:
                try:
                    if Ticket.parse(at_base).status in TERMINAL_STATUSES:
                        continue
                except TicketError:
                    blockers.append(f"{label}: the base copy cannot be read as a ticket")
                    continue
            own_attachments = _attachments(rel, changed, tip, ancestor)
            if rel in seen or any(
                _tree_entry(parent, path) not in {
                    _tree_entry(ancestor, path), _tree_entry(tip, path),
                }
                for path in (rel, *own_attachments)
            ):
                blockers.append(f"{label}: both the base and branch changed ticket state")
                continue
            plan[rel] = Rewrite(rewrite.text, (f"used live state from {name}", *rewrite.notes))
            seen.add(rel)
            for attachment in own_attachments:
                attachments[attachment] = _tree_entry(tip, attachment)
            log = merged_log(log, _show_text(tip, log_rel) or "", ticket_slug(rel, tasks_rel))
            update = BranchUpdate(name, tip, ancestor)
            if update not in branches:
                branches.append(update)
    return branches, attachments, log, blockers


def ticket_slug(rel: str, tasks_rel: str) -> str:
    path = PurePosixPath(rel).relative_to(tasks_rel)
    return path.parent.as_posix() if path.name == "ticket.md" else path.with_suffix("").as_posix()


def _base_commit(
    plan: dict[str, Rewrite],
    attachments: dict[str, TreeEntry | None],
    log: str,
    *,
    log_rel: str,
    parent: str,
) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        out("read-tree", parent, env=env)
        for rel, rewrite in plan.items():
            blob = out("hash-object", "-w", "--stdin", input=rewrite.text)
            out("update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=env)
        for rel, entry in attachments.items():
            if entry is None:
                out("update-index", "--force-remove", "--", rel, env=env)
            else:
                out("update-index", "--add", "--cacheinfo",
                    f"{entry.mode},{entry.oid},{rel}", env=env)
        if log != (_show_text(parent, log_rel) or ""):
            blob = out("hash-object", "-w", "--stdin", input=log)
            out("update-index", "--add", "--cacheinfo", f"100644,{blob},{log_rel}", env=env)
        tree = out("write-tree", env=env)
    return out(
        "commit-tree", tree, "-p", parent, "-m",
        f"Migrate {len(plan)} branch tickets to enter/exit step scripts",
    )


def _branch_commit(update: BranchUpdate, tasks_rel: str, log_rel: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        out("read-tree", update.tip, env=env)
        out("reset", "--quiet", update.ancestor, "--", tasks_rel, log_rel, env=env)
        tree = out("write-tree", env=env)
    return out(
        "commit-tree", tree, "-p", update.tip, "-m",
        "Keep migrated ticket state off the code branch",
    )


def catch_up_local(base: str, commit: str) -> None:
    local = ref_tip(f"refs/heads/{base}")
    if local is None:
        return
    if not is_ancestor(local, commit):
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
        log_rel = (cfg.repo_root / "log.md").resolve().relative_to(top).as_posix()
        out("fetch", "--quiet", "--prune", args.remote)
        parent = ref_tip(f"refs/remotes/{args.remote}/{args.base}")
        if parent is None:
            raise TicketGitError(f"`{args.remote}/{args.base}` does not exist after fetch")
        plan = plan_base(cfg, parent, tasks_rel)
        branches, attachments, log, blockers = plan_branches(
            cfg, plan, parent=parent, tasks_rel=tasks_rel, log_rel=log_rel,
            remote=args.remote, base=args.base,
        )
        report(plan)
        for update in branches:
            print(f"{update.name}: remove legacy ticket state from the code branch")
        if blockers:
            for blocker in blockers:
                print(f"{PREFIX}: {blocker}", file=sys.stderr)
            print(f"{PREFIX}: reconcile the listed branches before applying", file=sys.stderr)
            return 1
        if not plan or not args.apply:
            if plan:
                print(f"{PREFIX}: report only; rerun with --apply to publish")
            return 0
        commit = _base_commit(plan, attachments, log, log_rel=log_rel, parent=parent)
        updates = {args.base: commit}
        for update in branches:
            updates[update.name] = _branch_commit(update, tasks_rel, log_rel)
        run_op(
            f"git push {args.remote} (migration)",
            "push", *(["--atomic"] if branches else []), "--quiet", args.remote,
            *(f"{oid}:refs/heads/{name}" for name, oid in updates.items()),
        )
        for name, oid in updates.items():
            out("update-ref", f"refs/remotes/{args.remote}/{name}", oid)
            catch_up_local(name, oid)
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
