---
title: Finish relay ticket greet-first (land PR 417)
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

The greet-first `relay ticket` discussion session — agent opens with a
launch-shape-tailored greeting instead of waiting silently — was specced in
`marketing/relay-ticket-creates` and implemented in PR #417, but that PR is
still open. Finish it: review and land PR #417 (or complete whatever remains) so
`relay ticket` greets first for both `claude` and `codex`.

## Context

Source ticket `marketing/relay-ticket-creates` (done) holds the validated design
and canonical implementer payload. PR #417 (`greet-first-ticket`, open) reduces
the earlier configurable-`discussion_kickoff` revision to a one-line `Begin`
append in `src/relay/commands/ticket.py` plus the shape-specific Step 1 of the
`bootstrap/ticket` SKILL.md — zero changes to shared core. See
https://github.com/FastJVM/relay/pull/417
