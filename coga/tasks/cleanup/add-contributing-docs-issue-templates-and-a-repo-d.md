---
title: Add contributing docs, issue templates and a repo description
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
launch_generation: pending:c4a4cd02-28c5-432b-82c1-76bc1c6f7e2c
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

## Dev

branch: docs/contributing
worktree: /tmp/coga-contributing-docs

Separate linked feature checkout; the primary checkout owns task state and
runs workflow transitions.

## Implementation decisions

- Add a short `CONTRIBUTING.md` with setup, tests, and a pointer to the
  ticket convention in `coga/contexts/coga/principles/SKILL.md`; link to
  `docs/development.md` for the detailed development guide.
- Add minimal Markdown bug-report, feature-request, and PR templates, plus
  a contributor link from the README. Keep GitHub reports easy to file while
  making the Coga ticket the durable record for substantive implementation.
- Read-only GitHub check on 2026-09-17 confirmed the old description, empty
  homepage, and admin access. Apply the README tagline and the existing
  `project.urls.Homepage` from `pyproject.toml`
  (`https://github.com/FastJVM/coga`); no new community destination is implied.
- The code of conduct is conditional on the owner's preference, which is not
  supplied. Leave it unadopted; the requested docs/templates/settings can
  proceed without inventing an enforcement policy or reporting contact.
- `marketing/discord` still treats the community home as a draft campaign
  choice; this change does not select one.
- The primary checkout already had an unrelated edit to
  `coga/tasks/correct-the-v2-known-stale-surfaces-table-and-rout.md`; preserve it.

## Implemented

- `CONTRIBUTING.md` explains setup, testing, issue intake, the existing
  substantive-work ticket convention, and focused PRs. It links to the owning
  principle and the development guide rather than reproducing the full rules.
- `.github/ISSUE_TEMPLATE/bug_report.md` asks for observed/expected behavior,
  a reproduction, and environment; `feature_request.md` asks for a concrete
  problem and desired outcome. `.github/pull_request_template.md` asks for
  the change, ticket/issue references, and exact verification results.
- README links to the contributor guide. No runtime, workflow, fixture, or
  shipped Coga OS changes are needed.
- Applied and re-read GitHub settings successfully on 2026-09-17:
  `gh repo edit FastJVM/coga --description 'A company OS for small teams in the agentic era' --homepage 'https://github.com/FastJVM/coga'`.
  `gh repo view FastJVM/coga --json description,homepageUrl` returned those
  exact values. This external change is already live.

## Verification and handoff

- Created an isolated test environment in the feature checkout with
  `python -m venv .venv`; `.venv/bin/python -m pip install -e '.[test]'`
  succeeded after retrying outside the network-restricted sandbox.
- Parsed both issue templates with PyYAML and checked their nonempty
  `name`/`about` metadata and bodies. Checked all 16 local README/contributor
  links, including the ticket-principle heading anchor, and the PR template's
  expected path; all passed.
- `PYTHONPATH=/tmp/coga-contributing-docs/src .venv/bin/python -m pytest`
  passed: **2,654 passed in 178.52 seconds** on Python 3.12.12.
- `PYTHONPATH=/tmp/coga-contributing-docs/src .venv/bin/python -m coga.cli --version`
  returned `coga 0.3.2`; the same command with `--help` exited 0.
- `git diff --check` and `git diff --cached --check` passed.
- Committed as `a720e5d5` (`Add contributor guide and GitHub templates`).
  Feature checkout is clean. Post-commit `git fetch origin main` then
  `git rebase FETCH_HEAD` reported already up to date; `origin/main` is an
  ancestor and the feature branch has exactly one additional commit.
- No push or PR in this step. Ready for the frozen workflow's peer-review
  step. The optional code of conduct remains unadopted pending an explicit
  owner preference; there are no required implementation blockers.
