The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- branch: `docs/bootstrap-ticket-skills-rule`
- worktree: `/home/n/Code/claude/relay-bootstrap-ticket-skills-rule`
- pr: https://github.com/FastJVM/relay/pull/232

## Plan

Add an architecture-level rule to `relay-os/contexts/relay/architecture/SKILL.md`
that the `skills:` ticket frontmatter field must never carry
`bootstrap/ticket`. Rule lives inside the existing `**Skills**` Primitives
bullet (human-confirmed placement) — extends the line that already says skills
are "attached to workflow steps, not tickets" to also explain what the
ticket-level `skills:` field is for and why the authoring interview must not
sit in it.

Scope is doc-only — the architecture context. Not in scope: cleaning up the
six existing drafts that already carry `skills: [bootstrap/ticket]`; that is a
separate cleanup pass.

## Confirmed by human

- Extend the existing `**Skills**` bullet under Primitives, not a new
  paragraph under "Canonical ticket frontmatter".

## Verification

- `python -m pytest` (architecture SKILL.md is a doc file; tests should be
  unaffected, but run to confirm no regressions).
- `relay validate --json` against the example fixture is N/A — this change
  doesn't touch task layout, prompt composition, or workflow semantics.

## What changed

- Extended the `**Skills**` Primitives bullet in
  `relay-os/contexts/relay/architecture/SKILL.md` with two sentences:
  what the ticket-level `skills:` field is for, and that
  `bootstrap/ticket` must never appear there.
- Mirrored the change into the packaged source at
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`
  (force-add — `bootstrap/` is gitignored but the file is tracked, same
  pattern as the prior `a0f6738` resync commit). Downstream repos pick
  it up on the next `relay init --update`.
- The materialized `relay-os/bootstrap/contexts/...` copy in this repo
  is gitignored and regenerated on init; left as-is.
- Tests: 423 passed, 1 skipped (full suite) on a fresh 3.12 venv inside
  the worktree.

## Out of scope

- Cleaning up the six existing draft tickets that carry
  `skills: [bootstrap/ticket]`. That is a separate Dream/cleanup pass —
  the rule needs to be in the architecture context first so the cleanup
  has something to cite.

## Commit

- `cf94b68` on branch `docs/bootstrap-ticket-skills-rule` —
  "Document that bootstrap/ticket must not appear in ticket skills
  frontmatter". Two files changed, +10/-2. Pushed to origin and PR
  #232 opened against `main`.
