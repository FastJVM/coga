"""Open a Git branch for the current ticket and record its base and remote."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from coga.blackboard import read_dev_fields, set_dev_fields
from coga.taskfile import TaskFileError, read_blackboard, replace_blackboard
from coga_edge.git_workflow import fresh_branch_name


def output(*argv: str) -> str:
    return subprocess.check_output(argv, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--no-bump", action="store_true")
    args = parser.parse_args()
    try:
        path = Path(os.environ["COGA_TASK_TICKET"])
        slug = os.environ["COGA_TASK_SLUG"]
        fields = read_dev_fields(read_blackboard(path))
        branch = fields.get("branch")
        base = fields.get("base")
        if base and args.base and base != args.base:
            raise ValueError(f"--base {args.base!r} disagrees with the recorded base {base!r}")
        if not base:
            base = output("git", "branch", "--show-current") if not branch else None
            base = base or args.base
            if not base:
                info = json.loads(output("gh", "repo", "view", "--json", "defaultBranchRef"))
                base = (info.get("defaultBranchRef") or {}).get("name")
                if not base:
                    raise ValueError("Cannot determine the default branch. Supply --base.")
        remote = fields.get("remote")
        if not remote:
            remote = output("git", "for-each-ref", "--format=%(upstream:remotename)", f"refs/heads/{base}")
            remote = remote or "origin"
        if branch:
            subprocess.run(["git", "switch", "--", branch], check=True)
        else:
            branch = fresh_branch_name(slug, remote)
            subprocess.run(["git", "switch", "-c", branch], check=True)
        region = read_blackboard(path)
        additions = {
            key: value for key, value in {"branch": branch, "base": base, "remote": remote}.items()
            if key not in fields
        }
        live = read_dev_fields(region)
        for key, value in {"branch": branch, "base": base, "remote": remote}.items():
            if key in live and live[key] != value:
                raise ValueError(f"Live ticket's {key}: {live[key]} disagrees with {value}")
            if key not in live:
                additions[key] = value
        if additions:
            replace_blackboard(path, set_dev_fields(region, **additions))
        if not args.no_bump:
            subprocess.run([sys.executable, "-m", "coga.cli", "bump", slug], check=True)
    except subprocess.CalledProcessError as exc:
        return exc.returncode if exc.returncode > 0 else 1
    except (OSError, ValueError, KeyError, TaskFileError) as exc:
        print(f"open-branch: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
