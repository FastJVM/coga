"""Finish the ticket and merge exactly its peer-reviewed change and state commits."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from coga.repl_supervisor import SENTINEL_ENV, deferred_done_marker, emit_done_marker
from coga.blackboard import read_dev_fields
from coga.taskfile import TaskFileError, read_blackboard
from coga.ticket import Ticket, TicketError
from coga_edge.git_workflow import changed_paths, commit_state, git_output


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


def pr_view(cwd: str, url: str) -> dict:
    return json.loads(subprocess.check_output(
        ["gh", "pr", "view", url, "--json", "state,isDraft,baseRefName,headRefOid,statusCheckRollup"],
        cwd=cwd, text=True,
    ))


def run() -> int:
    try:
        path = Path(os.environ["COGA_TASK_TICKET"]).resolve()
        coga_root = Path(os.environ["COGA_COGA_OS_ROOT"]).resolve()
        slug = os.environ["COGA_TASK_SLUG"]
        cwd = git_output("rev-parse", "--show-toplevel", cwd=str(path.parent))
        paths = tuple(p.relative_to(cwd).as_posix() for p in (path, coga_root / "log.md"))
        fields = read_dev_fields(read_blackboard(path))
        for key in ("reviewed", "branch", "base", "remote", "pr"):
            if key not in fields:
                raise ValueError(f"Missing {key}: under ## Dev")
        branch = git_output("branch", "--show-current", cwd=cwd)
        if fields["branch"] != branch:
            raise ValueError(f"Current branch {branch!r} disagrees with recorded branch {fields['branch']!r}")
        dirty = set(changed_paths(cwd)) - set(paths)
        if dirty:
            raise ValueError("Commit your work first: " + ", ".join(sorted(dirty)))
        verify_reviewed_tree(cwd, fields["reviewed"], git_output("rev-parse", "HEAD", cwd=cwd), paths)
        ticket = Ticket.read(path)
        if ticket.status != "done":
            workflow = ticket.workflow
            if not isinstance(workflow, dict) or ticket.step_index() != len(workflow["steps"]):
                raise ValueError("The merge step must be the final workflow step")
            subprocess.run(
                [sys.executable, "-m", "coga.cli", "bump", slug],
                cwd=cwd, env={**os.environ, SENTINEL_ENV: ""}, check=True,
            )
        commit_state(cwd, paths)
        subprocess.run(["git", "push", "--", fields["remote"], "HEAD"], cwd=cwd, check=True)
        head = git_output("rev-parse", "HEAD", cwd=cwd)
        verify_reviewed_tree(cwd, fields["reviewed"], head, paths)
        url = fields["pr"]
        pr = pr_view(cwd, url)
        if pr.get("state") != "OPEN" or pr.get("isDraft") or pr.get("baseRefName") != fields["base"] or pr.get("headRefOid") != head:
            raise ValueError(f"PR {url} does not match open, ready head {head} on {fields['base']}")
        if pr.get("statusCheckRollup") != []:
            subprocess.run(["gh", "pr", "checks", url, "--watch", "--fail-fast"], cwd=cwd, check=True)
        subprocess.run(
            ["gh", "pr", "merge", url, "--squash", "--match-head-commit", head],
            cwd=cwd, check=True,
        )
    except subprocess.CalledProcessError as exc:
        return exc.returncode if exc.returncode > 0 else 1
    except (OSError, ValueError, KeyError, TaskFileError, TicketError) as exc:
        print(f"merge-pr: {exc}", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    with deferred_done_marker():
        result = run()
        if result == 0:
            emit_done_marker(session_id=os.environ["COGA_TASK_SLUG"])
        return result


if __name__ == "__main__":
    raise SystemExit(main())
