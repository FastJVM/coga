---
slug: cleanup/add-contributing-docs-issue-templates-and-a-repo-d
title: Add contributing docs, issue templates and a repo description
status: draft
owner: nicktoper
human: nick
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

Give arrivals from post 1 somewhere to land. `FastJVM/coga` has no
`CONTRIBUTING.md`, no code of conduct, and no issue or PR templates;
`.github/` holds only the release workflow. The GitHub repo description reads
"A blackboard for humans and agents", which is not the README tagline, and no
homepage URL is set.

## Context

**State at audit** (2026-09-02): public, AGPL-3.0, 3 stars, 0 forks,
0 open issues, 17 open PRs, one release (`v0.2.0`), Discussions disabled, no
homepage URL, description out of step with the README.

**Scope.**

- `CONTRIBUTING.md` — how to set up (`pip install -e ".[test]"`), run
  `python -m pytest`, and the repo's own convention that substantive work is a
  ticket. `docs/development.md` already carries most of this; the file can be
  short and point at it.
- A code of conduct, if the owner wants one. Standard Contributor Covenant is
  the boring choice.
- Issue and PR templates under `.github/`. Keep them minimal; a template that
  asks more than a reader will answer is worse than none.
- Repo description and homepage URL: align the description with the README
  tagline ("A company OS for small teams in the agentic era") and set the
  homepage. These are GitHub settings, so either the owner changes them or an
  agent runs `gh repo edit`.

**Not in scope.** The community home itself — Discussions versus Discord is
`marketing/discord`'s decision, and this ticket must not pre-empt it. The 17
open PRs are a separate triage question.

**Judgment.** The audit called this optional before post 1. The owner grouped
it with the cleanup work, so treat it as wanted but not release-blocking.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
