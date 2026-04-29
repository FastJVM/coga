---
name: dev/with-self-review
description: Code change with an agent self-review pass before the human sees a PR. Four agent steps (implement, review, fix, pr) then human merge.
steps:
  - name: implement
    skill: code/implement
  - name: review
    skill: code/self-review
  - name: fix
    skill: code/apply-review
  - name: pr
    skill: code/open-pr
  - name: merge
---

## merge

Human reviews the open PR. Edit, request changes locally, or merge when
satisfied. After merging, run `relay bump` to mark the task done.
