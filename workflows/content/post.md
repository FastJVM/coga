---
name: content/post
description: Content creation with approval gate before publishing. Use for external posts — LinkedIn, newsletters, Reddit replies.
steps:
  - name: draft
  - name: approve
  - name: publish
---

## draft

Write the first draft in `blackboard.md` under Findings. Keep it in
the task directory until approved — do not publish drafts anywhere
external.

## approve

A human reviews the draft and either edits it on the blackboard or
calls `relay step` to advance.

## publish

Post the content using the skill bundled with this workflow's target
platform (e.g. `skills/content/linkedin/post.py`). Post a `relay feed`
with the URL of the published content.
