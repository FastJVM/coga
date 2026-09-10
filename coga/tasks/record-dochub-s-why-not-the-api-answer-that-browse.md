---
title: Record DocHub's why-not-the-API answer that browser api-first requires
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

`coga/contexts/browser/api-first/SKILL.md` requires every ticket that
automates a real SaaS UI to state whether the target exposes an API, which
endpoints it covers, and — when it does not — to "link or note the docs page
checked, so the next person doesn't redo the search".

DocHub is the repo's one committed real-site automation target (the chosen
e-sign target), yet `coga/skills/browser/dochub/SKILL.md` contains no occurrence
of "API" at all, and no ticket or context in the corpus records the DocHub API
check: grepping for "dochub" across `coga/tasks/`, `coga/contexts/` and
`coga/workflows/` returns only packaging-twin tickets, the Dream recurring
ticket, `coga/contexts/coga/codebase/SKILL.md`, and `browser/dom-backed`.

So the durable answer api-first exists to preserve was never written down for
the only site it actually governs, and every future DocHub ticket must redo the
search or silently skip the rule. This compounds the three "GAP — unavailable"
blocks already in that file, where per-site learning was lost to an external
memory store — the skill is the repo's designated home for exactly this.

## Context

Add a short "Why the browser, not the API" section at the top of
`coga/skills/browser/dochub/SKILL.md` — the same place the skill already tells
agents to write recovered knowledge back.

DocHub does publish an API, so the honest answer is likely "partial": name what
the API covers, what it does not, and link the docs page checked with the date.
Do the check rather than asserting a conclusion — an unverified "no API" note
would be worse than the current silence.

Check whether the skill has a packaged twin under
`src/coga/resources/templates/` before editing; if it does,
`tests/test_packaging.py` enforces byte-identity and both copies must change
together.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
