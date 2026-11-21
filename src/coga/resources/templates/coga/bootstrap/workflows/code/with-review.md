---
name: code/with-review
description: Code change implemented by the main agent, then reviewed by its configured peer before a PR is opened for the human's final review.
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

## open-pr

On a frozen ticket with this earlier step name, follow the `code/open-pr`
skill to run the current PR script.

## implement

On a frozen snapshot without a step skill, follow `code/implement`.

## peer-review

On a frozen snapshot without a step skill, follow `code/peer-review`.

In the review receipt, record the actual reviewer and disclose any overlap with
the implementation session.
