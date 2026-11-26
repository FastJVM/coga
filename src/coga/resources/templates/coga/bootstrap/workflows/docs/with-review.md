---
name: docs/with-review
description: Docs/markdown change implemented by one agent, then peer-reviewed for prose, accuracy, and single-owner edits by the other agent before a PR is opened for the human's final review.
enter: git/ticket-enter
exit: git/ticket-exit
steps:
  - name: implement
    assignee: agent
    requires: branch
  - name: peer-review
    assignee: other-agent
  - name: push-and-open-pr
    run: git/push-and-open-pr
    assignee: agent
    requires: pr
  - name: review
    assignee: owner
    skills:
      - code/address-pr-comments
---

## open-branch

A ticket frozen with this earlier step predates the step scripts: run
`python -m coga_edge.migrate_step_scripts --path <ticket>`, which drops the
step and adds `enter`/`exit`, then launch again. Current snapshots open the
branch in the `git/ticket-enter` step script. See
[coga/git](../../contexts/coga/git/SKILL.md#branch-step-scripts).

## push-and-open-pr

Run `git/push-and-open-pr` after the implementation and review commits.
The script uses the preparation recorded under `## PR`.

## review

The owner reviews the PR and decides whether to merge. The final bump runs
the `exit` step script, which publishes the finished ticket to the base; the
PR carries no ticket state, so merge it before or after.
The owner can launch an assist to handle requested changes.


## implement

Edit the requested documentation on the recorded branch. Review the relevant
canonical topics and update related links. Verify document accuracy and
reachability. Commit the documentation before the review step, and record
what you checked and what remains in the ticket before bumping.

## peer-review

Switch to the recorded branch if needed. Read the actual documentation diff
and check accuracy, scope, links, and definition ownership. Fix must-fix
findings, commit them, and record the head and evidence under `## Dev` and
`## PR`. Bump when the handoff is ready.

In the review receipt, record the actual reviewer and disclose any overlap with
the implementation session.

## open-pr

On a frozen ticket with this earlier step name, follow the `code/open-pr`
skill to run the current PR script.
