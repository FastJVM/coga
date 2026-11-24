---
name: coga/git
description: Work with tickets on ordinary Git branches and carry their state through the PR.
---

# Working with Git

Coga writes the ticket and the audit log in the current checkout. You can run
Coga in a directory without Git. Code workflows can explicitly run a Git script
to open a branch or PR. Use ordinary `git pull`, `git push`, and `gh` to share
work, and `git branch -d` or GitHub to clean up merged branches.

## Ticket Git record

Use one line per field in the blackboard's `## Dev` section. Each workflow step
updates its own fields and preserves other lines.

```text
branch: <name>
base: <branch>
remote: <name>
reviewed: <full commit OID>
pr: <full /pull/ URL>
```

`git/open-branch` records branch, base and remote. `code/peer-review` records
the final reviewed head. `git/push-and-open-pr` records the PR URL. Workflow
gates read branch and PR from this record. If a needed field is missing or
disagrees with Git or GitHub, stop and resolve the discrepancy.

## Branch to merge

Start from the intended base. The branch script switches to the recorded
branch or creates one from the current HEAD. Once it exists, the ticket on
that branch is the live copy. For older tickets, the recorded branch may need
its base and remote backfilled before the PR step.

On a code step, commit implementation and review changes. The PR script commits
the ticket and log before opening the PR, then records the URL, advances the
step, and pushes the handoff. A launch audit line can land locally after that
push. After the PR opens, whoever changes the ticket commits and pushes that
state on the branch. The owner runs the final bump before merging, then commits
and pushes `status: done` with the log so the merge carries the finished ticket
to the base. The agent-merge workflow does that in its merge script.

Before handing off code, fetch the base and rebase as appropriate. Inspect
staged, unstaged and committed work separately. Preserve unique changes on both
sides. If Git reports a conflict, a failed push, or unexpected dirt, keep local
state, report the failure, and resolve it before retrying.

## Shared audit log

Lifecycle commands append to `coga/log.md`. The scaffold sets `merge=union`
so both sides of an append conflict survive. Log compaction snapshots the log
and preserves bytes appended before its final read. An append between that
read and the atomic replacement can still be lost. Keep compaction and routine
writes apart when possible.
