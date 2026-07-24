---
slug: overload-ticket-locally-easily
title: overload ticket locally easily
status: blocked
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/extension-model
- coga/architecture
skills: []
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Document the **zero-build way to override a bundled coga OS resource** — most
usefully, how to point `coga ticket` at your own interview instead of the
bundled `bootstrap/ticket`. This capability already exists via local-first
resolution; it is just not written down as a first-class how-to, so people
assume they need to build something.

Deliverable is docs only: a short note in the right coga context explaining
that dropping a repo file at `coga/<kind>/<ref>` overrides the bundled
`bootstrap/<kind>/<ref>` version wholesale, with the ticket-interview override
as the worked example. No code, no new mechanism.

This ticket started life as a proposal to build an *import/extend* directive
(inherit the base, write only the delta). That was **dropped**: the full-file
override already covers the real need, and an inherit-the-base mechanism is a
convenience-only win not worth building until copy-paste drift actually bites.
See "Out of scope" for the boundary. If drift ever becomes a real, felt
problem, reopen a fresh ticket for the directive.

## Context

**The fact to document (verified in source).**
- `src/coga/paths.py` resolves skills, contexts, and workflows **local-first,
  then bundled** (`resolve_skill_path` / `resolve_context_path` /
  `resolve_workflow_path`): a repo file at `coga/<kind>/<ref>` fully replaces
  the packaged `bootstrap/<kind>/<ref>` version; otherwise the bundled one is
  used. It is all-or-nothing per file — a full override, not a merge.
- Worked example for the note: `coga ticket` injects a **hardcoded** skill ref
  `AUTHORING_SKILL = "bootstrap/ticket"` (`src/coga/commands/ticket.py`). You
  cannot redirect it with an alias — `ticket` is a built-in and aliases can't
  shadow built-ins (`_validate_aliases`). But because that ref resolves
  local-first, dropping your own `coga/skills/bootstrap/ticket/SKILL.md` makes
  `coga ticket` inject **your** interview automatically. Zero build.
- Contrast to make in the note: `[aliases]` in `coga.toml` is command-name
  sugar (name → expanded coga command), **not** a content-override mechanism —
  a natural point of confusion this doc should clear up.

**Where to put it (writer's judgment — likely both, lightly).**
- `coga/extension-model` — the context on how coga's command surface / resources
  extend. The local-first override path fits its scope directly; this is the
  most likely primary home.
- `coga/architecture` — the composition/resolution mental model. A one-liner or
  pointer here may be warranted so the resolve-local-first behavior is
  discoverable from the architecture view. Keep it a pointer, not a duplicate.

**Constraints.**
- Shipped contexts are mirrored: keep the live repo copy under `coga/contexts/`
  and the packaged copy under `src/coga/resources/templates/coga/contexts/` in
  sync (per CLAUDE.md). The `docs/with-review` peer-review step checks this.
- Keep it short and legible — a paragraph or two per context, not a treatise.

**Out of scope (explicitly dropped, do not build).**
- The import/extend "inherit the base, write only the delta" directive. If you
  find yourself wanting to note *why* full-copy override is the recommendation,
  one sentence ("a full copy diverges from upstream over time; that tradeoff
  was accepted") is enough — do not spec the directive here.

<!-- coga:blackboard -->

## Production notes

2026-07-21 (ticket-edit session, nicktoper + claude): parked pending
`cli-extension-model/move-command-logic-to-tickets` (pass 2 execution).
Findings worth keeping from the discussion:

- Confirmed an alias cannot substitute for this doc: aliases can't shadow
  built-ins (`_validate_aliases`) and only rewrite argv — they can't redirect
  the hardcoded `AUTHORING_SKILL = "bootstrap/ticket"` ref. Local-first file
  override is the only zero-build path. That confusion arose naturally in this
  very session, which is evidence the note is needed.
- The command→ticket externalization makes the doc *more* relevant, not less:
  the collapsed `ticket` shape keeps the interview as a local-first-resolved
  ref, and pass 2 multiplies the refs that resolve this way. Post-move, the
  note's framing should shift from "obscure workaround" to "this is how you
  customize coga — commands are heads over refs, local files win".
- Blocked (not dropped) so it can be re-framed against the settled surface
  after the move executes, instead of documenting a moving target now.

---

## Blockers

- [ ] [2026-07-21 14:21] [agent:nicktoper] id=20260721T142144 Parked until cli-extension-model/move-command-logic-to-tickets (pass 2) executes — the note's framing depends on the post-move command surface (ticket collapsed to head + local-first refs); revisit and re-frame the doc then.
