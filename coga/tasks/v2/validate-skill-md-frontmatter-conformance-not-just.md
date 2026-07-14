---
slug: v2/validate-skill-md-frontmatter-conformance-not-just
title: Validate SKILL.md frontmatter conformance not just ref existence
status: draft
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: medium. Closes a credibility gap relative to the project's
central bet ("a relay skill IS a Claude Code skill IS a Codex skill").

`relay validate` checks only that skill/context refs **resolve to a file**
(`validate.py:533-592`) and that the `skills:`/`contexts:` ticket fields are
string lists. It never validates SKILL.md *content*. A skill with no frontmatter,
no `description`, a malformed YAML block, or a 10k-line body passes `relay
validate` clean — it only blows up later when `Skill.load` runs (e.g. in
`skill_manager._skill_ref_for_dir`, which swallows the error anyway,
`skill_manager.py:882-886`). For a system whose entire thesis is "we ARE the
Anthropic Skill format," shipping zero conformance checking on that format is the
biggest single gap relative to the stated bet.

Add a conformance check (in `relay validate`, and/or a `relay skill lint`):
- SKILL.md parses (valid frontmatter delimiters + YAML)
- required fields present and non-empty (`name` — or documented dir-name
  fallback — and `description`)
- `description` within a sane length (selection metadata, not an essay)
- optionally warn on oversized bodies (token bloat; ties into the token-budget
  ticket — note only the blackboard size is checked today, `validate.py:266-276`,
  not skills/contexts)
- flag the proprietary `script:` field explicitly so the "zero proprietary
  extensions" claim has a known, enumerated exception rather than a silent one.

Acceptance: a malformed/incomplete SKILL.md is reported by `relay validate` (or
`relay skill lint`) with a clear, file-named error; tests cover missing
frontmatter, missing `description`, and malformed YAML.

## Context

Code: `src/relay/validate.py` (`_check_refs` 533-592, only existence today),
`src/relay/skill.py` (`Skill.load`, the parser to reuse),
`src/relay/skill_manager.py:882-886` (error currently swallowed). Bet stated in
`relay-os/skills/_template/SKILL.md`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
