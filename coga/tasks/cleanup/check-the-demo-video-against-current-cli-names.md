---
slug: cleanup/check-the-demo-video-against-current-cli-names
title: Check the demo video against current CLI names
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: human
  - name: verify-read-only
    skills: []
    assignee: agent
secrets: null
step: 1 (brief-and-hand-off)
---

## Description

The README links a 95-second demo recorded 2026-07-18. One CLI name has been
removed since: `coga project`. Watch the video, confirm whether it shows or
says that command, and re-record or annotate if it does. Everything else in
the video's era still resolves today.

## Context

**Already checked, read-only (2026-09-03).** The video has no captions and
no description, so its content cannot be verified without watching it. What
was verified instead:

| Fact | Value |
|---|---|
| URL | https://www.youtube.com/watch?v=iwnewxJvRPc |
| Title | Coga Asynchronous Agentic Programming |
| Channel | ntoper |
| Uploaded | 2026-07-18 |
| Length | 95 seconds (matches the README's "95-second demo") |
| Captions | none |
| Description | empty |

**The CLI surface diff, upload date versus today.** Comparing registered
commands at commit `0c8eb75e` (2026-07-18 14:49, the last commit before
upload) against `main`:

- **`coga project` — removed** (commit `8394d3b3`, "remove-coga-build-and-project",
  PR #691). It ran a four-question interview and created an ordered set of
  draft tickets. Nothing replaced the spelling. **This is the only command in
  the video's era that no longer exists.** No mention of it survives in
  `README.md`, `docs/`, or the contexts, so the video is the last place it
  could still appear.
- `coga build` was removed in the same commit and restored by `ef721d2f`
  (PR #701), so it is fine.
- `coga open-pr` stopped being a built-in Typer command and became a default
  alias for the registered `coga run open-pr` recipe. The spelling on screen
  is unchanged, so a demo showing it is still correct.
- Added since: `coga run <recipe>`, `coga mark canceled`, and the
  `resolve-conflicts` alias. New surface never invalidates an old recording.

**What remains for the human.** 95 seconds of watching, looking and listening
for `coga project`. If it does not appear, close this ticket: the video is
accurate. If it does, decide between re-recording, a pinned comment, or a
README note next to the link.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
