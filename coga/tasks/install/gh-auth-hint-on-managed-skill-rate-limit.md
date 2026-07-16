---
slug: install/gh-auth-hint-on-managed-skill-rate-limit
title: gh auth hint on managed skill rate limit
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
script: null
step: 2 (peer-review)
---

## Description

Unauthenticated `gh skill install` runs against GitHub's anonymous API quota
(60 req/hr per IP); repeated inits — or one init behind office NAT — 403 all
managed-skill installs with a raw rate-limit dump. The failures are warn-only
(init proceeds), but the remediation hint suggests re-running
`coga skill install …`, which hits the same limit. When the failure is a
rate-limit 403, the remediation should say `gh auth login` (authenticated
requests get a much higher quota), and the raw GitHub ToS/request-ID blob
should be trimmed to the one actionable line.

## Context

Found in the 2026-07-08 fresh-container retest (third init from one IP,
gh 2.96 unauthenticated). Touchpoints: `src/coga/managed_skills.py` /
`src/coga/skill_manager.py` (failure classification + remediation text).

<!-- coga:blackboard -->

## Dev
branch: gh-rate-limit-hint
worktree: /home/n/Code/claude/coga-gh-rate-limit-hint

## Plan (implement step)

Failure path today: a rate-limit 403 from `gh skill install` raises
`SkillManagerError` with the raw stderr blob; `_github_access_denial_reason`
(src/coga/managed_skills.py) doesn't match it, so it lands in
`_failure_result` → status `failed`, message = full blob, remediation =
`coga skill install …` (the command that hits the same limit). Only
`coga init` renders these summaries (`_print_managed_skill_summary` in
src/coga/commands/init.py); `reconcile_managed_skills` has no CLI caller yet.

Changes:
- managed_skills.py: add `_github_rate_limit_reason(output)` (line-scan like
  the access-denial classifier; markers: "api rate limit exceeded",
  "secondary rate limit", "rate limit exceeded"; returns the one matching
  line → trims the ToS/request-ID blob). Check it *before* the access-denial
  classifier in `_run_install` (gh's rate-limit text can mention
  `gh auth login`, which would misclassify as no-access). New status
  `skipped-rate-limited` with `remediation: gh auth login`; per-source cache
  extended to carry (kind, reason) so later skills from the same source skip
  without re-hitting the exhausted quota (mirrors the no-access cache).
  Required skills fail loud with `Remediation: gh auth login`.
- init.py: consolidated one-note-per-source rendering for
  `skipped-rate-limited`, mirroring `_print_no_access_skill_notes`.
- Tests mirroring existing style in tests/test_managed_skills.py and
  tests/test_init.py.

Noted, out of scope: the reconcile/update path (`reconcile_managed_skills`
line ~243) still reports raw blobs on rate-limited `gh skill update`; no CLI
caller today, follow-up ticket material if one appears.

## Implemented (commit 942c7eb0 on gh-rate-limit-hint)

- `src/coga/managed_skills.py`: `_github_rate_limit_reason()` scans stderr
  lines for "api rate limit exceeded" / "secondary rate limit" / "rate limit
  exceeded" and returns just that line (trims the ToS/request-ID blob).
  Checked before the access-denial classifier in `_run_install`. New result
  status `skipped-rate-limited` with `remediation: gh auth login`
  (`GH_AUTH_REMEDIATION`). Per-source failure cache now stores
  `(kind, reason)` tuples ("no-access" | "rate-limit") so later skills from
  the same source skip without another API call. Required skills fail loud
  with `Remediation: gh auth login`.
- `src/coga/commands/init.py`: `_print_rate_limited_skill_notes()` — one
  consolidated yellow note per source, mirroring the no-access notes, naming
  `gh auth login` and a `coga skill install <source> <skill>` retry example.
- `src/coga/resources/managed-skills.toml`: header comment documents the
  rate-limit skip behavior.
- Tests: 2 new in tests/test_managed_skills.py (skip + trim + remediation;
  required fails loud), 1 new in tests/test_init.py (consolidated note).

Verification: full suite `python -m pytest` → 1210 passed, 1 skipped, in a
python3.12 venv with the worktree installed editable. (Bare python3.12
without the editable install fails test_launch_script.py's stateless test
identically on main — environment setup, not this change.)

## Usage

{"agent":"claude","cache_creation_input_tokens":276155,"cache_read_input_tokens":7661107,"cli":"claude","input_tokens":162,"model":"claude-fable-5","output_tokens":91674,"provider":"anthropic","schema":1,"session_id":"18dcba7c-4b8a-40be-bae4-ac12c400542c","slug":"install/gh-auth-hint-on-managed-skill-rate-limit","step":"implement","title":"gh auth hint on managed skill rate limit","ts":"2026-07-16T00:22:29.976871Z","usage_status":"ok"}
