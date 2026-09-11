---
title: Document how packaged contexts reach a repo, and settle the packaged-only cli
  context
status: draft
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

Two related packaging facts that no context records, one of which has already
shipped a defect.

**1. The two packaged-context trees are consumed by different mechanisms.**
`coga/contexts/coga/codebase/SKILL.md` documents packaged contexts only as a
byte-identity twin rule over two path mappings (`templates/coga/<path>` and
`templates/coga/bootstrap/{contexts,skills,workflows}/<path>`). Nothing records
that `paths.resolve_context_path` falls back to `bootstrap/contexts/` **only**,
while `templates/coga/contexts/**` is init-seeded into a new repo by
`commands/update.py::copy_fresh_templates` and is never a runtime fallback.
Verified in-tree: `src/coga/resources/templates/coga/bootstrap/contexts/` holds
only `coga/` and `dev/`, whereas `browser/api-first` and `browser/dom-backed`
exist only under `src/coga/resources/templates/coga/contexts/browser/`.

That undocumented distinction has already shipped a defect:
`src/coga/resources/templates/coga/bootstrap/browser-automation/ticket.md`
attaches `browser/api-first`, and `bootstrap/skills/browser/build-automation/SKILL.md`
tells the agent to apply it — so that bootstrap ticket cannot compose from
bundled resources alone. Both the design agent and the independent evaluator on
`redo-documentation-dir-and-merge-it-with-context-b` had to rediscover this by
probing the package.

**2. `coga/cli` is the one shipped context with no live copy.** Of the eleven
bootstrap contexts under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`,
ten have a live counterpart under `coga/contexts/coga/`; `coga/cli` does not.
Because `tests/test_packaging.py` derives twins from the packaged tree and a
packaged file with no live counterpart is simply not a pair, that context sits
outside byte-parity enforcement entirely and is invisible to anyone treating
`coga/contexts/` as the canonical tree — yet three live contexts route readers
to it (`launch-internals`, `architecture`, `extension-model`) and tickets edit
it (`migrate-recurring-templates-to-ticket-py-shims-and` records correcting
"active stale launch text in the packaged `coga/cli` context"). The done ticket
`packaged-repos-ship-recurring-templates-without-th` flagged this exact case as
an adjacent finding — "worth deciding whether that packaged-only context is
intentional" — and the decision was never made or written down.

## Context

Part 1 wants a short "how packaged contexts reach a repo" section in
`coga/contexts/coga/codebase/SKILL.md` (and its enforced twin) naming the three
states — init-seeded, bootstrap-fallback, local-only — and stating the rule an
author needs: an attachment in a bundled bootstrap ticket must resolve from
`bootstrap/contexts/`. Fixing the shipped `browser-automation` defect is a
separate, smaller change; decide whether it rides along.

Part 2 is a decision, not a documentation task: either state in the twin-rule
paragraph that a packaged-only context is a deliberate unenforced shape, name
`coga/cli` as the only current instance and why, and say where its edits are
reviewed — or give it a live copy so the derived parity test covers it.

Verify each claim against `src/coga/paths.py` and `src/coga/commands/update.py`
before writing; this Dream run read them but did not re-verify every path.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
