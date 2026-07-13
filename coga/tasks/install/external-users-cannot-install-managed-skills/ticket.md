---
slug: install/external-users-cannot-install-managed-skills
title: External users can't install managed skills (relay-skills access)
status: in_progress
mode: agent
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

On `relay init --update`, the ~12 optional managed skills all failed to install
for Greg because he has no access to the `relay-skills` repo — which is the
default state for any outside / onboarding user. The managed-skill install path
should either not require private-repo access, degrade cleanly to a working
install without them, or clearly state that these skills are optional and how to
obtain access.

## Context

Reported by Greg (external user). The *noise* of these failures (12 full `gh`
usage dumps burying the success lines) is already owned by
`marketing/quiet-relay-init-managed-skill-failures` (draft); this ticket is the
orthogonal *access/availability* problem for non-team users. Skill install
delegates to `gh skill` (see the `relay/cli` context, `relay skill`) and
`src/relay/skill_manager.py`.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/535
branch: managed-skills-no-access
worktree: /home/n/Code/claude/coga/.coga/worktrees/coga-managed-skills-no-access

## Findings (implement step)

- The ticket's "relay" names map onto this repo: `relay init --update` ≈ `coga init`,
  `src/relay/skill_manager.py` = `src/coga/skill_manager.py`. The managed-skill
  install path is `src/coga/managed_skills.py` (`install_managed_skills`), called
  only from `coga init` (`src/coga/commands/init.py:_install_managed_skills_or_exit`).
- Manifest: `src/coga/resources/managed-skills.toml` — 7 optional github-sourced
  skills, all from one source repo. Each spec runs its own `gh skill install`,
  so a user without access to the source repo gets one failure per skill
  (the "12 failures" Greg saw), each surfaced as status=failed + warning.
- Root cause: no preflight on source-repo accessibility; `gh skill install` is
  attempted per skill and fails per skill for users outside the org.

## Implemented (commit a024cf80 on managed-skills-no-access)

- `src/coga/managed_skills.py`: new `_github_source_unavailable_reason` /
  `_probe_github_source` / `_no_access_result`. Before any github-sourced
  managed-skill install, each unique source is probed once per run with
  `gh repo view <owner/repo> --json name` (cache dict threaded through
  `install_managed_skills` / `reconcile_managed_skills` into `_run_install`).
  Unreachable source (private repo, no gh auth, or gh missing entirely →
  FileNotFoundError caught) ⇒ optional skills get status `skipped-no-access`
  with reason + remediation in details, and **no** `gh skill install` runs at
  all; required skills still raise ManagedSkillError (fail-loud unchanged).
  Probe only runs on the real install path — an injected `github_installer`
  test seam bypasses it, preserving existing tests.
- `src/coga/commands/init.py`: `_print_no_access_skill_notes` — one
  consolidated yellow note per unreachable source ("skipped N optional managed
  skills from <source> … Coga works without them … get access or `gh auth
  login`, then `coga skill install …`") instead of a warning per skill.
- `src/coga/resources/managed-skills.toml`: comment documents the new
  degrade behavior.
- Tests: 4 new in tests/test_managed_skills.py (single probe per shared
  source + no install attempts, gh-missing skip, required fail-loud on
  no-access, accessible source proceeds to install) and 1 new in
  tests/test_init.py (consolidated note, no per-skill warnings). Style
  mirrors existing runner/seam-based tests.

## Verification

- `python3.12 -m pytest tests/test_managed_skills.py tests/test_init.py -q` → 105 passed.
- Full suite in a scratch venv with `pip install -e .`: 1147 passed, 1 skipped.
- Note: bare `python3.12 -m pytest` (no editable install) fails
  `tests/test_launch_script.py::test_bootstrap_script_launch_is_stateless`
  with ModuleNotFoundError — pre-existing on the base commit too (subprocess
  needs coga installed); unrelated to this change, green once installed.

## Notes for review

- Ticket's "12 failures": live manifest has 7 entries, all one source repo —
  count differs from the report but the mechanism (one failing `gh skill
  install` per optional skill for a no-access user) is what's fixed. With the
  preflight, the noisy gh usage dumps never run for no-access users, which
  also de-fangs (but doesn't close) the separate noise ticket
  `marketing/quiet-relay-init-managed-skill-failures`.
- Chose "degrade cleanly + clearly state optional/how to get access" over
  "don't require private-repo access" (moving skills to a public source is a
  publishing decision, not a CLI change).

## Peer review

- Native `codex review --base main` found and fixed three correctness edges:
  transient GitHub failures were initially misclassified as access denial;
  missing `gh` guidance was not actionable; and SAML-protected organizations
  need their specific access-denial response recognized.
- A final review found the preflight design itself would block anonymous
  installs from public repositories because `gh repo view` requires auth while
  `gh skill install` supports anonymous access. Replaced the preflight with
  failure-driven caching: the first real install runs; only an explicit
  auth/not-found/SAML failure is cached, and later optional skills from that
  source are skipped. Required skills remain fail-loud.
- Final native review: no findings. Branch rebased cleanly onto `main`, clean,
  and 5 commits ahead.
- Verification: focused managed-skill/init suite `108 passed`; full suite in an
  isolated editable-install venv `1150 passed, 1 skipped`.

## PR

Consolidate managed-skill access failures during `coga init`: after the first
explicit auth, not-found, or SAML denial from a GitHub source, Coga skips the
remaining optional skills from that source and prints one clear note that Coga
works without them plus actionable install/auth guidance. Anonymous installs
from public repositories still proceed, missing `gh` gets an install-first
hint, and required managed skills remain fail-loud.

Tests: `/tmp/coga-managed-skills-review-venv/bin/python -m pytest -q` — 1150
passed, 1 skipped.

## Usage

{"agent":"claude","cache_creation_input_tokens":255785,"cache_read_input_tokens":8398095,"cli":"claude","input_tokens":194,"model":"claude-fable-5","output_tokens":75281,"provider":"anthropic","schema":1,"session_id":"7ac00306-fdf1-45d7-89ea-78a362599c5f","slug":"install/external-users-cannot-install-managed-skills","step":"implement","title":"External users can't install managed skills (relay-skills access)","ts":"2026-07-11T01:48:08.284853Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":13059840,"cli":"codex","input_tokens":644595,"model":"gpt-5.6-sol","output_tokens":19952,"provider":"openai","schema":1,"session_id":"019f4edc-53ce-7dc0-a7ea-6b444323a298","slug":"install/external-users-cannot-install-managed-skills","step":"peer-review","title":"External users can't install managed skills (relay-skills access)","ts":"2026-07-13T00:50:19.909563Z","usage_status":"ok"}
