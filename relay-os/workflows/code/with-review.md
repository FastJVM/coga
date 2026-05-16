---
name: code/with-review
description: Code change implemented by an agent, PR opened by an agent, reviewed and merged by a human.
steps:
  - name: implement
    skills:
      - code/implement
  - name: open-pr
    skills:
      - code/open-pr
  - name: review
    assignee: owner
---

## review

Human reviews the open PR. Edit, request changes locally, or merge
when satisfied. After merging, run `relay bump` to mark the task
done.
