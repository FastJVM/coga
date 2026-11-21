---
name: docs/with-review
description: Docs/markdown change implemented by one agent, then peer-reviewed for prose, accuracy, and single-owner edits by the other agent before a PR is opened for the human's final review.
steps:
  - name: open-branch
    run: git/open-branch
    assignee: agent
    requires: branch
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

Run `git/open-branch` from the intended base and record the branch in the ticket.
See [coga/git](../../contexts/coga/git/SKILL.md).

## push-and-open-pr

Run `git/push-and-open-pr` after the implementation and review commits.
The script uses the preparation recorded under `## PR`.

## review

The owner reviews the PR and decides whether to merge. Run the final bump on
the branch, then commit and push the finished ticket and log before merging.
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

## open-pr

On a frozen ticket with this earlier step name, follow the `code/open-pr`
skill to run the current PR script.
