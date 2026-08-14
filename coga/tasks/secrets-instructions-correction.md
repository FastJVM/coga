---
slug: secrets-instructions-correction
title: secrets-instructions-correction
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

A credential is declared per ticket, in `secrets:` frontmatter, as an `op://`
pointer that `coga launch` resolves and injects. **It is a list of single-key
entries, not a mapping** — `coga validate` rejects a dict with `bad-shape —
ticket 'secrets:' must be null or a list of 'NAME: <ref>' entries`, and a launch
fails validation *after* already marking the task active:

```yaml
secrets:
  NASA_FIRMS_MAP_KEY: op://weather-events/nasa-firm/credential    # wrong (mapping)
  - NASA_FIRMS_MAP_KEY: op://weather-events/nasa-firm/credential  # correct (list)
```

## Context

Original report was a raw paste; the Description above is the same content with
its line-number prefix, duplicated half-sentence, and unclosed fence cleaned up.

**The ticket's premise does not reproduce in this repo.** Every instruction here
already documents the correct list form:

- `coga/tasks/_template/ticket.md:12` — "one `- NAME: <ref>` list entry per secret"
- `docs/operations.md:183` — "Each entry is a single-key map", list example
- `coga/contexts/coga/architecture/SKILL.md:156` — "a list of single-key maps `- NAME: <ref>`"
- `coga/contexts/coga/secrets/SKILL.md:28` — list example
- `src/coga/config.py:1094` — the validator error quoted in the Description

A repo-wide grep for a mapping-form `secrets:` example returned nothing outside
this ticket's own body. So the instruction that produced the mistake is not in
this repo, and there is no target here to correct.

Three candidate scopes, unresolved:

1. **Wrong instruction lives elsewhere** — e.g. the `weather-events` repo's own
   docs, or something an agent wrote there. Fix is over there, or hoist the rule
   somewhere agents actually read.
2. **Docs are fine; the real defect is the failure mode** — the reported "launch
   fails validation after already marking the task active" is a `coga launch`
   ordering bug: the active transition happens before `secrets:` is validated, so
   a typo strands the ticket in a state that needs hand-repair. That is a code
   ticket in `src/coga/`.
3. **Both**, as one ticket or split into two.

Scope 2 is worth a look regardless of how 1 resolves — it is the part that costs
manual cleanup every time. The `design` step's first job is to settle which
scope this ticket actually is, using Zach's answer.

Out of scope until that is settled: changing `secrets:` parsing to *accept* the
mapping form. The list shape is deliberate (`src/coga/config.py:1094`), and
`coga/contexts/coga/architecture/SKILL.md:156` explains why a bare-string entry
and a raw literal are both rejected.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.


---

## Blockers

- [x] [2026-08-13 22:21] [agent:claude] id=20260813T222158 Zach to confirm the ticket's scope before design starts. The premise does not reproduce in this repo: every instruction here already documents the correct '- NAME: <ref>' list form (coga/tasks/_template/ticket.md:12, docs/operations.md:183, coga/contexts/coga/architecture/SKILL.md:156, coga/contexts/coga/secrets/SKILL.md:28, src/coga/config.py:1094), and a repo-wide grep finds no mapping-form example outside this ticket's own body — so there is no instruction here to correct. Which did you actually hit: (a) the wrong instruction lives in another repo (weather-events?) — name the file; (b) the real defect is that coga launch marks the task active BEFORE validating secrets:, so a typo strands the ticket and needs hand-repair — a code fix in src/coga/; or (c) both, as one ticket or split. Contexts are still unset pending that answer.
  resolved: [2026-08-13 22:54] [human:nicktoper] Scoped to (b) on reproduced evidence, since (a) has no target in this repo. Re-verified: no mapping-form 'secrets:' example exists anywhere here outside this ticket's own Description, so there is no instruction in this repo to correct; if the bad instruction lives in weather-events, that fix belongs in that repo and needs a filename only Zach can supply — carried forward as an Open Question for the owner at review-design rather than blocking a second time. (b) does reproduce and is precise: src/coga/commands/launch.py:542 calls _auto_activate (a durable write — status draft/paused to active, freezes the workflow snapshot, seeds step, appends the log, git-syncs) BEFORE the fail-loud preflight gauntlet at 544-591 (human-handoff refusal, TTY check, agent-type resolution, CLI-binary check, compose preflight, and the secrets preflight at 591 that raises SecretError). So a malformed 'secrets:' on a draft ticket strands it in 'active' with a frozen workflow and a spurious activation log entry. Two internal precedents show the intended shape: the blocked-resume path already defers _auto_activate to line 666, after every preflight, and the assist path already composes an in-memory prospective activation via _prospective_assist_ticket/prepare_active without writing. mark.py:445 prepare_active is documented as exactly this 'pure preparation boundary'. Fix is to make the normal draft/paused path do what those two already do. Existing coverage masks the bug: test_launch_fails_loud_on_op_read_error starts from an already-active task and asserts only that it stays active.
