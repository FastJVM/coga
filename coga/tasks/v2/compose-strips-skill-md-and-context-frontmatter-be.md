---
slug: v2/compose-strips-skill-md-and-context-frontmatter-be
title: Compose strips SKILL.md and context frontmatter before injection
status: draft
mode: llm
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: medium. Correctness/quality, touches every composed prompt.

The compose path injects skill and context files into the system prompt by
reading them raw — `_skill_layers` and `_step_layers` call `sp.read_text()`
(`compose.py:285`, `:315`) and contexts use `cp.read_text()` (`compose.py:196`).
`Skill.load` (`skill.py`) is never called from compose; `Skill` is not even
imported there. Consequence: every composed prompt embeds the literal YAML
frontmatter block (`---\nname: ...\ndescription: ...\n---`) inline into the
agent's system prompt. The `description` field is metadata meant for skill
*selection*, not for the agent to read mid-task — it is noise that burns tokens
and contradicts the "we adopt the Anthropic Skill format properly" claim.

Fix: use the existing frontmatter-aware parser (`skill.py`'s `Skill.load`) in
the compose path so only the body is injected, with frontmatter stripped. Apply
the same to contexts.

While here, fold in two smaller compose robustness gaps found in the same audit:
- Raw `read_text()` on rules/context/blackboard/skill (`compose.py:173, 184,
  196, 223, 285, 315`) raises bare `OSError`/`UnicodeDecodeError` on a
  permission issue or binary file, with no friendly message. Wrap with a clear
  error naming the offending file.
- `estimate_tokens` is the `chars/4` heuristic (`compose.py:101-105`) — fine as
  a rough gauge, but note it is misleading if ever used for budgeting (see the
  token-budget ticket).

Note (design decision, not a bug): Relay's compose eagerly inlines the full
skill body for the current step, which is the opposite of Anthropic's
progressive disclosure (metadata-then-body-on-demand). That is a legitimate
"deterministic prompt scope" choice — call it out in a context doc rather than
"fixing" it, but stripping frontmatter is still correct regardless.

Acceptance: composed prompts contain skill/context *bodies* only, no YAML
frontmatter; `test_compose.py` gains a case asserting frontmatter is absent;
raw file-read errors surface a clear message naming the file.

## Context

Code: `src/relay/compose.py` (`_skill_layers` ~279-296, `_step_layers`
~299-360, context loop 190-199), `src/relay/skill.py` (`Skill.load`,
unused by compose today), `tests/test_compose.py`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
