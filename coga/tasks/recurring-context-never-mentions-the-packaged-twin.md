---
slug: recurring-context-never-mentions-the-packaged-twin
title: Recurring context never mentions the packaged twin every template has
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
---

## Description

`coga/contexts/coga/recurring/SKILL.md` is what a recurring-template author reads, and
it never tells them the template they are editing has a packaged twin.

All seven templates under `coga/recurring/` have a counterpart under
`src/coga/resources/templates/coga/recurring/`, but grepping the recurring context for
`packaged`, `twin`, `mirror` or `resources/templates` returns nothing.

This matters more than an ordinary doc gap because **a recurring template body is
composed verbatim as the spawned task's `## Description`** — drift between the copies
changes the run prompt in every downstream repo after `coga init --update`.

Deliverable, two parts:

1. A twin-sync note in `coga/contexts/coga/recurring/SKILL.md` telling template authors
   the twin exists, where it is, and why drift is expensive.
2. A statement in `coga/contexts/coga/codebase/SKILL.md` of the principle governing
   **which** twins must be registered in `IDENTICAL_LIVE_PACKAGED_PAIRS` — that list
   currently covers only pairs someone remembered to add, and the context frames the
   hazard as rebase-specific.

Part 2 is the design judgment: deciding the registration rule (all twins? only those a
composed prompt depends on?) is what needs a human, and it determines whether this also
warrants extending the test.

## Context

Citations name symbols and files, not line numbers.

**Three tickets circle the same unenforced problem:**

- `coga/tasks/live-and-packaged-twin-pairs-are-edited-together-b.md` records that
  `IDENTICAL_LIVE_PACKAGED_PAIRS` enforces only a registered subset, and that two Dream
  Phase 6 PRs (#719, #721) each hit an unenforced pair in a single run.
- `coga/tasks/v2/document-recurring-template-live-vs-packaged-sync.md` asks specifically
  for a Gotchas bullet in the recurring context — this ticket supersedes it, and that
  draft should be folded in or canceled rather than worked separately.
- `coga/tasks/guard-the-browser-dochub-and-playwright-live-vs-pa.md` names one further
  unenforced pair.

**Verified on 2026-09-02:** `coga/recurring/` holds seven templates — `autoclose-merged`,
`blocker-reminders`, `branch-sweep`, `digest`, `dream`, `resolve-conflicts`,
`skill-update` — and each has a packaged twin under
`src/coga/resources/templates/coga/recurring/`. Of those, the enforced pair list
registers the five `ticket.py` files and `coga/recurring/dream/ticket.md`, but not the
other `ticket.md` bodies.

**Partial existing coverage:** `coga/contexts/coga/codebase/SKILL.md` carries a
rebase-hazard bullet that does state `IDENTICAL_LIVE_PACKAGED_PAIRS` "only covers pairs
someone remembered to register" — but it frames the hazard as rebase-specific and names
no rule for what must be registered.

Dream 2026-W36's own Phase 3 copy-divergence shard (`ca-06`) compared every registered
pair and the seven recurring template pairs and found **zero** divergence today, so this
is a preventive fix, not a repair.

`coga/contexts/coga/codebase/SKILL.md` is an enforced twin — edit both copies.
`coga/contexts/coga/recurring/SKILL.md` is 47 KB and has no packaged twin; check before
assuming.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-11`), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
