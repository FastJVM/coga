---
name: _template
description: Starter SKILL.md. Copy this directory to skills/<namespace>/<your-skill>/ and replace this content. Skills are process knowledge — how to do a thing — and attach to workflow steps.
---

# Replace with your skill title

This file follows the `SKILL.md` standard — the same format Claude Code
and OpenAI Codex use. A coga skill IS a Claude Code skill IS a Codex
skill. Zero proprietary extensions, so Anthropic's `skill-creator` (and
any other tool that speaks SKILL.md) can author and edit these files.
Coga derives a skill's reference from the directory path either way. A
repo-authored skill normally declares that namespaced ref as its `name:` —
`name: <namespace>/<your-skill>`, matching the directory you copied this into.
Reserve the standards-valid leaf form (lowercase letters, digits, and hyphens,
no slash) for a skill that also has to satisfy the portable Agent Skills
metadata grammar; `browser/dochub` is the checked-in example, and vendored or
installer-managed imports keep their upstream leaf `name:` for the same reason.
The vendored `anthropic/skill-creator` `quick_validate.py` enforces that
portable grammar, so it rejects a namespaced `name:` as not kebab-case. For a
repo-authored skill that rejection is expected, not a defect to fix.

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
when each is called. The agent invokes them during its session; describe how
to run one rather than expecting `coga launch` to execute it. Deterministic
headless behavior belongs at one of the two sanctioned edges instead: the
reserved sibling `ticket.py` beside a ticket, which `coga launch` subprocesses
before any agent phase, or a registered `coga run` recipe when the behavior
needs a repository-independent argv/stdout/exit contract.
