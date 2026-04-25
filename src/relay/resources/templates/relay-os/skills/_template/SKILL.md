---
name: _template
description: Starter SKILL.md. Copy this directory to skills/<namespace>/<your-skill>/ and replace this content. Skills are process knowledge — how to do a thing — and attach to workflow steps.
---

# Replace with your skill title

This file follows the `SKILL.md` standard — the same format Claude Code
and OpenAI Codex use. A relay skill IS a Claude Code skill IS a Codex
skill. Zero proprietary extensions, so Anthropic's `skill-creator` (and
any other tool that speaks SKILL.md) can author and edit these files.

Skills are process knowledge. They attach to a workflow step and inline
into the agent's prompt at launch time when the task reaches that step.

Write what an agent picking up this step needs to know. Short and
declarative beats long and exhaustive.

## When to use this

Optional. Useful when the description alone is ambiguous.

## How to do it

- Bullet
- Bullet
- Bullet

## Bundled scripts

If this skill ships with scripts, drop them next to SKILL.md and describe
when each is called. The agent invokes them during interactive/auto
sessions; for `mode: script` tasks, `relay launch` runs the first
executable script with secrets injected as env vars.
