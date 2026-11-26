---
name: code/with-self-review
description: Code change with an agent self-QA pass (direct review, fixes committed in place) before the PR is opened, so the human reviewer sees one clean diff. Three agent steps then human PR review.
git: ticket-branch
steps:
  - name: open-branch
    run: git/open-branch
    assignee: agent
    requires: branch
  - name: implement
    assignee: agent
    requires: branch
    skills:
      - code/implement
  - name: self-qa
    assignee: agent
    skills:
      - code/self-qa
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

Run `git/open-branch` from the intended base and record the branch in the ticket.
See [coga/git](../../contexts/coga/git/SKILL.md).

## push-and-open-pr

Run `git/push-and-open-pr` after the implementation and review commits.
The script uses the preparation recorded under `## PR`.

## review

The owner reviews the PR and decides whether to merge. Run the final bump on
the branch, then commit and push the finished ticket and log before merging.
The owner can launch an assist to handle requested changes.

## pr

On a frozen ticket with this earlier step name, follow the `code/open-pr`
skill to run the current PR script.

## implement

On a frozen snapshot without a step skill, follow `code/implement`.

## No other-agent code review

This workflow is for teams using one agent. The implementer runs self-review
and the owner reviews the PR before merging.
