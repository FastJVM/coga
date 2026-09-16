---
title: Record DocHub's why-not-the-API answer that browser api-first requires
status: in_progress
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
step: 2 (peer-review)
launch_generation: 7c642513-1187-4cf6-8cba-08d54aee6dfd
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

## Dev

branch: dochub-api-answer
worktree: /home/n/Code/claude/coga-dochub-api-answer

## Implement (2026-09-16)

**Finding that overrides the ticket's guess.** The `## Context` assumed the
answer was "likely partial" because "DocHub does publish an API". It does not.
Evidence, all checked 2026-09-16:

- DocHub Support's own community answer (help.dochub.com, thread
  "Automatically Filling Forms via API", uuid
  `c91a6950-fa12-401f-93e5-cbc88a6db133`, 2024-04-11): "Currently, we are
  working on DocHub API… As of now, you can only use DocHub directly from your
  browser." Only API hit in the entire help-center knowledge base + community
  (searched: API, webhook, zapier, developer, sdk, "rest api").
- `dochub.com/compare/dochub-vs-pandadocs-api-pricing` is the sole dochub.com
  page describing a "docHub API" (lowercase-d mail-merge; sandbox plan,
  Developer Dashboard, "Open API Specification"). Zero outbound links to any
  reference/spec/dashboard. `dochub.com/developers`, `/developers/api`,
  `/api-docs`, `/api` → 404; `api./docs./developers.dochub.com` don't resolve.
- `dochub.com/pricing`, `dochub.com/en/integrations`: no API/developer tier.
  `zapier.com/apps/dochub/integrations` → 404. apitracker.io profile is empty.
- `https://dochub.com/api/` is the web app's private XHR backend (visible in
  help-center page config as `DOCHUB_API_URL`); undocumented, unsupported.

So the recorded answer is **No** (not partial), with the pypdf AcroForm
pre-fill named as the hybrid api-first asks for. Section explicitly says
which page not to cite as evidence and when to re-check.

**Changes.** `coga/skills/browser/dochub/SKILL.md` — new "Why the browser, not
the API" section directly under the intro (before the AcroForm pre-fill
section). Packaged twin
`src/coga/resources/templates/coga/bootstrap/skills/browser/dochub/SKILL.md`
copied byte-for-byte (it existed and was identical before the change).

**Verification.** In the worktree, using the primary checkout's `.venv`:
`PYTHONPATH=src python -m pytest -q tests/test_packaging.py` → 11 passed;
full `python -m pytest -q` → 2561 passed (171s). Rebased onto fresh
`origin/main` (already at tip). One commit `a6aeda1f`, tree clean. No push,
no PR.

**Not done / out of scope.** Did not add `browser/api-first` to the skill's
substrate list at the top; the new section names the context inline, which
seemed enough. No fixture change — no task layout, prompt composition, or
workflow semantics affected.
