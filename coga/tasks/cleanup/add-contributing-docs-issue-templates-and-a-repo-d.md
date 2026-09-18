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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/832
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

## Peer review

- `codex review --base main` from `/tmp/coga-contributing-docs` on
  `docs/contributing` **returned successfully (exit 0)** with no actionable
  findings. It initially failed to
  initialize its app-server client in the read-only sandbox, then started
  successfully with the approved `codex review` escalation. Review transcript:
  `/tmp/coga-contributing-peer-review.log`.
- The reviewer also ran
  `PYTHONPATH="$PWD/src" .venv/bin/python -m pytest tests/test_cli.py -q`:
  **15 passed**. No must-fix changes or additional implementation commit were
  needed.
- Manually checked the five-file Markdown diff against the development guide
  and the canonical ticketed-work principle. The templates keep issue intake
  short and point substantive implementation to a Coga ticket.
- Rechecked issue-template YAML metadata and bodies, the PR template's path
  and sections, and all 16 local README/contributor links (including the one
  heading anchor); all passed.
- `gh repo view FastJVM/coga --json description,homepageUrl` confirmed the
  requested description and homepage remain live on 2026-09-17.
- Ran `git fetch origin main` and then `git rebase FETCH_HEAD`
  unconditionally. Rebase succeeded without conflicts onto `d88dcb4d`;
  implementation commit is now `8fb06fc5`. `git range-diff` confirmed the
  reviewed patch is unchanged; upstream changes were only this ticket and
  `coga/log.md`.
- After the rebase,
  `PYTHONPATH=/tmp/coga-contributing-docs/src .venv/bin/python -m pytest`
  **returned successfully: 2,654 passed in 171.35 seconds**. Test transcript:
  `/tmp/coga-contributing-peer-review-pytest.log`.
- `git diff --check origin/main...HEAD` and `git diff --check` passed.
  The feature checkout is clean, and `git rev-list --left-right --count
  origin/main...HEAD` returned `0 1`: one committed change ahead of fetched
  main. The unrelated primary-checkout task edit remains untouched.
- Peer review is complete with no required changes or blockers. The PR body
  below is ready for the next workflow step.

## Open PR

- Confirmed the peer review returned successfully with no actionable findings.
  Both checkouts were clean at the start of this step.
- The first `coga open-pr` attempt refused the stale feature branch before
  publishing. Ran `git fetch origin main` and `git rebase FETCH_HEAD` in
  `/tmp/coga-contributing-docs`; the rebase completed without conflicts onto
  `611acffa`. Implementation commit is now `8214f1cb`.
- `git range-diff d88dcb4d..8fb06fc5 origin/main..HEAD` confirmed the reviewed
  patch is unchanged. `git diff --check origin/main...HEAD` passed; the feature
  checkout is clean and one commit ahead of fetched main (`0 1`).
- The required post-rebase full test run returned successfully:
  `PYTHONPATH=/tmp/coga-contributing-docs/src .venv/bin/python -m pytest`
  (**2,655 passed in 216.55 seconds**).
  Transcript: `/tmp/coga-contributing-open-pr-pytest.log`.
- `gh repo view FastJVM/coga --json description,homepageUrl` confirmed the
  requested description and homepage remain live on 2026-09-18.
- Retried `coga open-pr cleanup/add-contributing-docs-issue-templates-and-a-repo-d`
  successfully. It pushed the branch, opened
  https://github.com/FastJVM/coga/pull/832, and recorded the URL under `## Dev`.
- `gh pr view 832 --repo FastJVM/coga` confirmed an open, non-draft, mergeable
  PR from `docs/contributing` to `main`, with the prepared title and body.
  Both checkouts are clean. Publication is complete and ready for owner review.

## PR

New contributors had no contributor guide or GitHub issue/PR templates. Adds a
short guide linked from the README, plus minimal bug-report, feature-request,
and pull-request templates. The guide explains setup and testing, links to the
development guide, and routes substantive changes through the existing Coga
ticket convention.

The GitHub repository description now matches the README tagline, and its
homepage uses the existing package homepage URL, `https://github.com/FastJVM/coga`.
Those settings were applied and verified separately from this diff. The optional
code of conduct remains unadopted pending an owner preference.

Test plan: `PYTHONPATH=/tmp/coga-contributing-docs/src .venv/bin/python -m pytest`
(2,655 passed after the publishing rebase); issue-template metadata, all 16 local README/contributor links,
and `git diff --check origin/main...HEAD` passed. `codex review --base main`
returned with no actionable findings.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `cleanup/add-contributing-docs-issue-templates-and-a-repo-d`
Recorded: 2026-09-18T19:26:51+00:00

    Branch 'docs/contributing' is not safe to publish. current branch does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase FETCH_HEAD`. Reconcile it and relaunch, or `coga block --task cleanup/add-contributing-docs-issue-templates-and-a-repo-d`.
