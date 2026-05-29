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

## review

Human reviews the open PR on GitHub. Edit, request changes, push fixes,
or merge when satisfied. The PR diff has already been through
`/code-review` and `/simplify`, so the agent QA is done — your job is
the human-judgment gate. After merging, `automerge` bumps the task to
`done` on your next `git pull` (or `relay status`).
