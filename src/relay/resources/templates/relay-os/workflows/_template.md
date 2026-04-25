---
# `name` matches the file path under workflows/ (without the .md).
name: code/with-review
# `description` is what create-suggest matches against when picking a
# workflow for a new task. One sentence.
description: Standard code workflow with PR and approval gate.
# `steps` is the ordered sequence. Each step is either:
#   - has a `skill:` ref → full skill content inlined when this step runs
#   - has no skill → the agent reads the inline body section below with
#     a `## <step-name>` heading
steps:
  - name: implement
    skill: infra/testing-conventions
  - name: pr
  - name: approve
  - name: merge
---

<!--
Body sections below correspond 1:1 to steps without a `skill:` ref.
The heading must match the step name. Keep them short — one paragraph
each is plenty for inline instructions.
-->

## pr
Create a branch, push, open a PR. Title the PR after the task title.

## approve
Review the PR. If changes are needed, comment and wait. If approved, advance.

## merge
Merge the PR and clean up the branch.
