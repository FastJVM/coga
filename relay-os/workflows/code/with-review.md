---
name: code/with-review
description: Code change implemented by an agent, reviewed and merged by a human. Two steps — agent ships a PR, human merges.
steps:
  - name: implement
    skill: code/implement-and-pr
  - name: review
---

## review

Human reviews the open PR. Edit, request changes locally, or merge when
satisfied. After merging, run `relay step` to mark the task done.
