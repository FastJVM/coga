"""Merge exactly the ticket's peer-reviewed change, then finish the ticket."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from coga.repl_supervisor import SENTINEL_ENV, deferred_done_marker, emit_done_marker
from coga.blackboard import read_dev_fields
from coga.taskfile import TaskFileError, read_blackboard
from coga.ticket import Ticket, TicketError
from coga_edge.git_workflow import changed_paths, git_output, verify_reviewed_tree


def pr_view(cwd: str, url: str) -> dict:
    return json.loads(subprocess.check_output(
        ["gh", "pr", "view", url, "--json", "state,isDraft,baseRefName,headRefOid,statusCheckRollup"],
        cwd=cwd, text=True,
    ))


def merge_method(cwd: str, url: str) -> str:
    repo = url.rsplit("/pull/", 1)[0]
    settings = json.loads(subprocess.check_output(
        [
            "gh", "repo", "view", repo, "--json",
            "viewerDefaultMergeMethod,mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed",
        ],
        cwd=cwd, text=True,
    ))
    method = settings.get("viewerDefaultMergeMethod")
    allowed = {"MERGE": "mergeCommitAllowed", "REBASE": "rebaseMergeAllowed",
               "SQUASH": "squashMergeAllowed"}
    if isinstance(method, str) and method.upper() in allowed:
        method = method.upper()
        if settings.get(allowed[method]) is True:
            return "--" + method.lower()
    enabled = [name for name, key in allowed.items() if settings.get(key) is True]
    if len(enabled) == 1:
        return "--" + enabled[0].lower()
    raise ValueError(f"Cannot determine an enabled merge method for {repo}")


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
        tasks_prefix = (coga_root / "tasks").relative_to(cwd).as_posix() + "/"
        dirty = {
            p for p in set(changed_paths(cwd)) - set(paths)
            if not p.startswith(tasks_prefix)
        }
        if dirty:
            raise ValueError("Commit your work first: " + ", ".join(sorted(dirty)))
        verify_reviewed_tree(cwd, fields["reviewed"], git_output("rev-parse", "HEAD", cwd=cwd), paths)
        ticket = Ticket.read(path)
        if ticket.status != "done":
            workflow = ticket.workflow
            if not isinstance(workflow, dict) or ticket.step_index() != len(workflow["steps"]):
                raise ValueError("The merge step must be the final workflow step")
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
            ["gh", "pr", "merge", url, merge_method(cwd, url), "--match-head-commit", head],
            cwd=cwd, check=True,
        )
        # Last action: the final bump marks the ticket done and runs the
        # workflow's `exit` script, which publishes it on the base.
        if ticket.status != "done":
            subprocess.run(
                [sys.executable, "-m", "coga.cli", "bump", slug],
                cwd=cwd, env={**os.environ, SENTINEL_ENV: ""}, check=True,
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
