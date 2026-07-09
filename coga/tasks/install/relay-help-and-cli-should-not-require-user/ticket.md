---
title: relay CLI should not require user to be set (default to $USER)
status: draft
mode: agent
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

The `user` config requirement surfaces constantly during onboarding — a new user
can't even run `relay --help` without it, and sometimes the command then reports
it's ignoring the requirement anyway. Relax it: read-only / help commands should
not need `user` at all, and where a name is genuinely needed, default to `$USER`
when there is no local config override rather than hard-failing.

## Context

Reported by Greg as the single most pervasive friction. The name-*capture*
mechanism (`relay init --user`) already landed
(`relay-init-captures-name-via-user-param`, done); this is the complementary
*strictness* problem — the requirement is enforced far too broadly. Config
loading and `current_user` live in `src/relay/config.py`.

**Retest 2026-07-08 (fresh-container):** released 0.2.0 is fixed — `--help`
works everywhere, blank `user` tolerated. But unreleased main REGRESSES this:
`load_config` hard-fails on missing/empty `user` for every command including
`--help` (`src/coga/config.py` ~304, `src/coga/cli.py` `main()`), and since
`coga.local.toml` is gitignored, every teammate who clones a coga repo hits
it before they can run anything. Scope this ticket to main's behavior:
read-only/help commands must not need `user`, and document (or automate) the
teammate step that creates `coga.local.toml`.
