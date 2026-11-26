---
name: code/design-then-implement
description: A thin ticket is designed into a spec, cold-reviewed by another agent, approved by the owner, then implemented, code-reviewed by the other agent, and opened as a PR for final owner review.
enter: git/ticket-enter
exit: git/ticket-exit
steps:
  - name: design
    assignee: agent
    skills:
      - code/design
  - name: evaluate-design
    assignee: other-agent
    skills:
      - code/review-design
  - name: review-design
    assignee: owner
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
  - name: review
    assignee: owner
    skills:
      - code/address-pr-comments
---

## review-design

Owner reviews the spec the `design` step wrote into `ticket.md` —
`## Description` with its Acceptance criteria, Proposed shape, and Out of
scope `###` subsections (a separate `##` for any of them never composes) — and
answers
anything under `## Open Questions` on the blackboard. If an
`## Evaluator review` section is present, resolve every must-fix finding; record
a disposition when one is intentionally rejected. Edit the ticket directly to
correct scope or approach. When the spec is right, run `coga bump` to hand off
to `implement`. If the design is wrong enough to redo, rewind with
`coga bump <slug> --to 1` (`design` is step 1) instead of bumping; if the premise itself is
wrong, cancel and open a new ticket (`coga/lifecycle`).

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

## open-pr

On a frozen ticket with this earlier step name, follow the `code/open-pr`
skill to run the current PR script.

## implement

On a frozen snapshot without a step skill, follow `code/implement`.

## peer-review

On a frozen snapshot without a step skill, follow `code/peer-review`.
