---
name: _template
description: Starter SKILL.md. Copy this directory to skills/<namespace>/<your-skill>/ and replace this content. Skills are process knowledge — how to do a thing — and attach to workflow steps.
---

# Replace with your skill title

This file follows the `SKILL.md` standard — the same format Claude Code
and OpenAI Codex use. A coga skill IS a Claude Code skill IS a Codex
skill: same file shape, same sections, no proprietary *structure*, so
Anthropic's `skill-creator` (and any other tool that speaks SKILL.md) can
author and edit these files.

There is exactly one place Coga extends the standard, and it is the `name:`
field. **Coga never reads it** — a skill's reference is derived from its
directory path, both for `skills:` refs and for the generated
`coga/.agent-skills` view (`agent_skills.py`). That leaves you a real choice,
with a real cost either way:

- `name: <namespace>/<your-skill>` — Coga's documented slash extension,
  matching the directory you copied this into. This is what most
  repo-authored skills here do, because the file then says what it is called.
  The cost is portability: slashes are outside the Agent Skills metadata
  grammar, so the vendored `anthropic/skill-creator` `quick_validate.py`
  rejects it as not kebab-case, and `skill-creator`'s validation/packaging
  flow will not run on it. For a repo-authored skill that rejection is
  expected, not a defect to fix.
- `name: <your-skill>` — the portable leaf form (lowercase letters, digits,
  and hyphens, no slash). Choose it whenever the skill has to satisfy the
  portable grammar or round-trip through `skill-creator`. Coga resolves it to
  the same namespaced ref from the path, so nothing about the skill's
  addressing changes. `browser/dochub` is the checked-in example, and
  vendored or installer-managed imports keep their upstream leaf `name:` for
  the same reason.

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
