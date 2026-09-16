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
step: 3 (open-pr)
launch_generation: 0e8f2078-4f08-421c-942c-52bc4e952acc
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

pr: https://github.com/FastJVM/coga/pull/822
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

## Peer review

2026-09-16: `codex review --base main` **returned** with no actionable
findings; its focused packaging run passed all 11 tests. The reviewer could
not independently check DocHub's external claims because its network was
unavailable. Parent review separately fetched the public help-center sources
and checked the current pricing, integrations, and comparison pages.

**Evidence correction (supersedes Implement's categorical conclusion).** The
2024-04-11 support reply exists in the help center's public thread record:
`https://support-backend.usrsprt.com/support/dochub/community-forum/question/c91a6950-fa12-401f-93e5-cbc88a6db133`.
However, today's `/search?q=API&per_page=15&page=1` at the same support base
returns two knowledge-base topics, two questions, and the support answer;
the draft's "only API hit" / "no articles" claims were false. The other
hits concern Google APIs and SSO, not the e-sign workflow. An old reply plus
unsuccessful documentation searches also cannot prove that no API exists.
Both skill copies now say **no usable public API found for this workflow**,
link the checked sources, acknowledge the conflicting comparison-page claim,
and drop the unsupported assertions about every integration or hand-off.
The browser route and local AcroForm pre-fill remain; future tickets attach
`browser/api-first`, cite this check, and re-check for changed scope, new API
evidence/access, or age beyond a year.

**Surface review.** This diff only changes instructional markdown; no
interactive terminal or rendered UI behavior changed. Browser control tools
were unavailable; the external evidence was verified through public HTTP
reads instead.

**Verification.** `git fetch origin main` followed by `git rebase FETCH_HEAD`
ran before review and again after committing the corrections. Both rebases
succeeded without conflicts; the final refresh added only audit-log commit
`6a60239a`. `git diff --check origin/main...HEAD` and
`cmp coga/skills/browser/dochub/SKILL.md src/coga/resources/templates/coga/bootstrap/skills/browser/dochub/SKILL.md`
passed after the corrections. Final post-rebase command:
`PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest -q -o cache_dir=/tmp/coga-dochub-peer-review-pytest-cache`
→ **2561 passed in 176.43s**, with no warnings. The cache directory avoids
the harmless read-only-cache warning from the earlier full passing run.

**Committed handoff.** Review fix: `824ae147` (`peer-review: qualify DocHub API
evidence`); rebased implementation: `6c50e678`. `dochub-api-answer` is clean,
two commits ahead of fetched `origin/main`. No feature push or PR in this step.

## PR

DocHub's automation skill lacked the API check required by `browser/api-first`.
Add a dated, source-linked answer for document preparation and e-signing:
no usable public API was found for this workflow. Distinguish the older
support answer from current comparison-page claims, keep local AcroForm
pre-fill plus the browser workflow, and explain when to re-check. Update the
packaged skill twin identically; no runtime or fixture changes.

Test plan: `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest -q -o cache_dir=/tmp/coga-dochub-peer-review-pytest-cache`
— 2561 passed; skill twins are byte-identical and
`git diff --check origin/main...HEAD` passed.
