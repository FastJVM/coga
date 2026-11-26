---
name: code/agent-merge
description: Code change implemented by the main agent, reviewed by its configured peer, then published and merged by the main agent with no owner gate. The owner audits after the merge and can revert.
enter: git/ticket-enter
exit: git/ticket-exit
steps:
  - name: implement
    assignee: agent
    requires: branch
    skills:
      - code/implement
  - name: peer-review
    assignee: other-agent
    skills:
      - code/peer-review
  - name: push-and-open-pr
    run: git/push-and-open-pr
    assignee: agent
    requires: pr
  - name: merge
    assignee: agent
    run: code/merge-pr
---

## open-branch

On a frozen ticket with this earlier step, run `git/open-branch` from the
intended base and record the branch in the ticket. Current snapshots open the
branch in the `git/ticket-enter` step script instead. See
[coga/git](../../contexts/coga/git/SKILL.md).

## push-and-open-pr

Run `git/push-and-open-pr` after the implementation and review commits.
The script uses the preparation recorded under `## PR`.

## merge

The merge script verifies the peer-reviewed head and allows only ticket and
log commits after it. It records and pushes the final state, waits for checks
and merges the exact pushed head. The owner audits the merged PR.

## open-pr

On a frozen ticket with this earlier step name, follow the `code/open-pr`
skill to run the current PR script.

## implement

On a frozen snapshot without a step skill, follow `code/implement`.

## peer-review

On a frozen snapshot without a step skill, follow `code/peer-review`.

In the review receipt, record the actual reviewer and disclose any overlap with
the implementation session.
