---
slug: install/quiet-managed-skill-failures-on-old-gh
title: Quiet managed skill failures on old gh
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 3 (open-pr)
---

## Description

With gh < 2.90 (no `gh skill` subcommand), `coga init` prints the full `gh`
usage screen **once per managed skill** — 7 skills × ~37 lines ≈ 260 lines of
noise burying the init summary. The per-skill warning line itself is good
("GitHub CLI 2.90.0+ with `gh skill` is required … Upgrade `gh`"); the raw
`unknown command "skill"` usage dump appended to each is not. Detect the
missing/old `gh skill` **once**, print one compact upgrade line, and skip the
remaining manifest entries instead of failing each identically. With current
gh the warnings are already compact — this is only the old-gh path.

## Context

Found in the 2026-07-08 fresh-container retest with gh 2.86 (a realistic
pre-2.90 machine); reproduces Greg's original "12 noisy failure dumps"
complaint at 7. Supersedes the noise half of
`marketing/quiet-relay-init-managed-skill-failures` (relay-era draft) — the
access half is fixed (public `google/agents-cli` manifest, optional,
warn-only, works unauthenticated). Touchpoints: `src/coga/managed_skills.py`
(failure detail capture), `src/coga/commands/init.py`
(`_print_managed_skill_summary`), `src/coga/skill_manager.py` (the gh-version
probe producing the message).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: quiet-old-gh-skill-noise
worktree: /home/n/Code/claude/coga/.coga/worktrees/coga-quiet-old-gh

## Plan (implement step)

Root cause traced: `ensure_gh_skill` (src/coga/skill_manager.py) appends the
full `(stderr or stdout)` of the failed `gh skill --help` probe to
`GH_SKILL_REQUIRED` — on gh < 2.90 that is the ~37-line usage screen — and the
probe runs once per manifest entry (7 github installs via `run_gh_skill`), so
`_print_managed_skill_summary` in init.py prints 7 identical dumps.

Fix, three layers:

1. `skill_manager.py`: new `GhSkillUnavailableError(SkillManagerError)`;
   `ensure_gh_skill` raises it and keeps only the FIRST line of the probe
   output (e.g. `unknown command "skill" for "gh"`), never the usage dump.
2. `managed_skills.py`: `install_managed_skills` / `reconcile_managed_skills`
   catch `GhSkillUnavailableError` once, mark that spec and every remaining
   spec `skipped-old-gh` (new status, message + remediation kept in details),
   and stop probing. A required spec still raises `ManagedSkillError`
   (fail-loud unchanged).
3. `commands/init.py` `_print_managed_skill_summary`: `skipped-old-gh` results
   collapse into ONE compact two-line warning (count + GH_SKILL_REQUIRED,
   then the skipped skill names); genuine `failed` results keep their
   per-skill warnings.

Decisions: status name `skipped-old-gh`; all affected entries get the same
status (uniform, so the counts line reads `skipped-old-gh=7`); first probe
line kept in the error message so direct `coga skill install` on old gh still
says why. reconcile_managed_skills has no CLI caller yet but shares
`_run_install`, so it gets the same short-circuit (otherwise the new exception
would escape it).

## Implement step — done

Committed as ad20f6d8 on `quiet-old-gh-skill-noise` (not pushed; open-pr step
does that). Files: src/coga/skill_manager.py, src/coga/managed_skills.py,
src/coga/commands/init.py, plus tests in test_skill_manager.py,
test_managed_skills.py, test_init.py.

New behavior on old gh (verified end-to-end with a fake gh runner and 7
manifest specs): exactly one `gh skill --help` probe, all 7 entries
`skipped-old-gh`, and init prints one two-line yellow warning
("Warning: skipped 7 optional managed skills — GitHub CLI 2.90.0+ …" +
"  Skipped: <refs>") instead of 7 usage dumps. Genuine non-gh failures keep
their per-skill warnings; required specs still raise ManagedSkillError
(init exit 2) whether gh dies on their own probe or was detected earlier.

Tests: `python3.12 -m pytest` in the feature worktree — 1153 passed,
1 skipped, 1 failed: test_launch_script.py::test_bootstrap_script_launch_is_stateless.
That failure is PRE-EXISTING and environmental, not from this change: it fails
identically on unmodified main (spawns a fresh interpreter that needs `coga`
pip-installed; this machine's python3.12 is PEP-668 externally managed and has
no coga install, and `pip install -e .` is refused). All three touched test
files pass (145 tests). Not blocking on it since it demonstrably predates the
branch; flagging here for the peer-review step.

## Peer review — complete

- Native `codex review --base main` found one must-fix P2: the cached old-gh
  short-circuit in `reconcile_managed_skills` runs before distinguishing the
  next entry's operation, so an existing URL-backed skill is skipped even
  though its update path does not use `gh skill`.
- Fix shape: retain the cached skip for missing installs (all install paths use
  `gh skill`) and existing GitHub-backed updates, while allowing existing
  URL-backed entries to reconcile normally. Add a mixed-sequence regression
  test proving a URL update still runs after an earlier GitHub entry detects
  old gh.
- The second native review found another P2: `ensure_gh_skill` classified every
  nonzero probe as old gh, including supported `gh` binaries with unreadable or
  malformed config. Narrow the dedicated exception to a missing binary or the
  recognized `unknown command "skill"` signature; preserve other probe failures
  as ordinary `SkillManagerError`s with their actual diagnostic.
- Applied both fixes in rebased commit `a6205a84`. The final native
  `codex review --base main` reported no findings.
- Rebased cleanly onto current `main` (`2c74a7f1`); branch is clean, contains
  `main`, and is two commits ahead.
- Verification after rebase: `PYTHONPATH="$PWD/src" python3.12 -m pytest -q`
  — 1156 passed, 1 skipped. The absolute `PYTHONPATH` lets the stateless
  script-launch subprocess import the worktree package without an editable
  install, so the previously reported environment-only failure is green.

## PR

Quiet old-GitHub-CLI managed-skill failures during `coga init`: detect a missing
or recognized pre-2.90 `gh skill` capability once, skip the remaining optional
managed installs, and print one compact upgrade warning instead of repeated
usage dumps. Required skills remain fail-loud, unrelated `gh` probe failures
retain their real diagnostics, and URL-backed reconciliation continues without
`gh skill` when possible.

Tests: `PYTHONPATH="$PWD/src" python3.12 -m pytest -q` — 1156 passed, 1 skipped.

## Usage

{"agent":"claude","cache_creation_input_tokens":273495,"cache_read_input_tokens":8436817,"cli":"claude","input_tokens":175,"model":"claude-fable-5","output_tokens":93845,"provider":"anthropic","schema":1,"session_id":"b67c3f98-3b68-4f6b-9792-defd26b0b210","slug":"install/quiet-managed-skill-failures-on-old-gh","step":"implement","title":"Quiet managed skill failures on old gh","ts":"2026-07-13T04:19:20.175108Z","usage_status":"ok"}
