---
name: dev/with-self-review
description: Code change with an agent self-QA pass (/code-review + /simplify, fixes committed in place) before the PR is opened, so the human reviewer sees one clean diff. Three agent steps then human PR review.
steps:
  - name: implement
    assignee: agent
    skills:
      - code/implement
  - name: self-qa
    assignee: agent
    skills:
      - code/self-qa
  - name: pr
    assignee: agent
    skills:
      - code/open-pr
  - name: review
    assignee: owner
---

## pr

Follow the `code/open-pr` skill to push and open the PR. In addition to
the blackboard `## Dev` entry, **update the ticket**: write the PR link
into `ticket.md` so the source of truth records where the change landed.
Add a `## PR` section to the ticket body (or update it if present) with
the PR URL before you `relay bump`.

After the PR is open, **resolve any merge conflicts with the base branch
before the handoff**: check that the PR is mergeable (e.g. `gh pr view
<PR#> --json mergeable,mergeStateStatus`), and if it conflicts with
`main`, merge/rebase `main` into the feature branch, resolve the
conflicts, re-run `python -m pytest`, and push so the human reviewer
receives a clean, mergeable PR. Only then `relay bump` to hand off to the
owner. If a conflict needs a judgment call you can't make, write it to
the blackboard and `relay panic` instead of bumping.

## review

Human reviews the open PR on GitHub. The PR diff has already been through
`/code-review` and `/simplify`, so the agent QA is done — your job is
the human-judgment gate.

This is an owner-controlled gate. If an agent is launched or asked to
assist during this step, it may inspect the PR, run verification, prepare
or push explicitly requested fixes, and report a recommendation. It must
not merge the PR, delete the branch, run `relay automerge`, run
`relay mark done`, or otherwise advance/close the task unless the human
explicitly says to do that for this PR.

The human owner decides whether to edit, request changes, push fixes, or
merge. After the human merges, run `relay automerge` explicitly (or rely
on a later `relay launch` freshness check) to mark the task `done`.
