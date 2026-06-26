---
slug: v2/write-prompt-file-second-resolution-timestamps-col
title: write_prompt_file second-resolution timestamps collide on same-second launches
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: low. Small, real, easy.

`write_prompt_file` (`compose.py:242-253`) names the dumped composed-prompt file
with a second-resolution timestamp. Two launches within the same second collide
and the second overwrites the first — losing the composed-prompt record for one
of them. Low stakes (these are debug/audit artifacts), but it defeats the
purpose of keeping the composed prompt for inspection when chaining/relaunch
fires rapidly.

Fix: add sub-second precision and/or the task slug + a short uniquifier
(e.g. include microseconds, or append a counter / short hash) so concurrent or
rapid-succession launches each get their own file.

Acceptance: two prompt dumps within the same second produce two distinct files;
covered by a test.

## Context

Code: `src/relay/compose.py:242-253` (`write_prompt_file`).

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
