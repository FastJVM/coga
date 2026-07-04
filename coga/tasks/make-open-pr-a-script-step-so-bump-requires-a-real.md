---
slug: make-open-pr-a-script-step-so-bump-requires-a-real
title: Make open-pr a script step so bump requires a real PR
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- coga/architecture
- coga/principles
- coga/codebase
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

**Problem.** `coga bump` moves the workflow `step:` as a free-floating counter
with no coupling to the artifact the step represents. Reproduced
deterministically: a `code/with-review` ticket set `in_progress` at step 1,
bumped 3× with *no branch, no commit, no PR*, reaches `step 4 (review)` — the
`open-pr` step "completes" without opening a PR. This is the mechanism behind
the cross-worktree divergence incident: on `main` the step marched through
open-pr/review while the code sat unmerged on a separate worktree branch, and
nothing tied the two together.

The current `code/open-pr` skill is an **agent-run checklist** (find worktree →
push → `gh pr create` → record `pr:` on the blackboard → `coga bump`) whose
steps carry no judgment — so an agent can skip a step, reorder them, or bump
without ever opening the PR.

**Change.** Convert `code/open-pr` from an agent skill into a **script step**,
so the step's substance *is* creating + recording the PR. A script step cannot
"complete" without producing its output, which closes the hole by construction
and fails loud on the incident's mis-branch case (no diff → `gh pr create`
errors → the step fails instead of silently advancing). This is principle 2 —
"agents do, humans think; crystallize the deterministic part to a script."

Keep judgment where it belongs: the agent writes the PR title/summary/test-plan
into the blackboard `## Dev` section during implement/peer-review; the open-pr
**script** consumes that + pushes + `gh pr create` + writes `pr: <url>` back +
bumps.

**Deterministic recipe the script owns:**
1. Read `branch:` / `worktree:` and the PR body fields from `## Dev`.
2. Confirm the worktree is on that branch, clean, with commits ahead of base.
3. `git push` the branch.
4. `gh pr create` (or `gh pr ready <#>` if a draft exists). Title = ticket
   title; body from `## Dev` + `Closes ticket: <slug>`.
5. Write `pr: <url>` under `## Dev` in the primary checkout.
6. `coga bump` to advance.

**Fail-loud requirements (the whole point):**
- No branch recorded / no commits ahead of base / nothing to PR → non-zero
  exit, step does **not** advance, error is actionable (points at the missing
  `## Dev` fields or `coga block`).
- Push / `gh` auth failure → fail loud with the setup hint (mirror
  `github_preflight`), never a bare traceback.

**Design decisions to settle in-ticket:**
- PR body source + fallback when no prior step authored a summary (fall back to
  `## Description`, or fail loud asking for one?).
- draft-vs-ready, base branch, multi-PR — script covers the common case from
  `## Dev` fields; document the escape hatch (a flag, or keep an agent variant).
- **Replace** `code/open-pr` outright (preferred — no reason it should be
  hand-run) vs ship a scripted variant + a `code/with-review` variant. Frozen
  workflows mean in-flight tickets are unaffected either way.

**Out of scope (separate tickets):**
- The `review` step reading the *bound* PR; gating earlier steps on PR presence.
- The worktree-teardown ("rip") problem — un-pushed commits lost on
  launch-worktree teardown.
- `coga automerge` already gates `done` on the PR being merged — don't duplicate.

## Acceptance

- `code/open-pr` runs as a script step; push + open PR + record `pr:` + bump are
  one deterministic unit that cannot complete without a real PR URL.
- **Reproduce-and-verify** (the sandbox from this investigation): a
  `code/with-review` ticket's open-pr step **fails loud and does not advance**
  when there is no branch/commit; and with a real branch it opens an actual PR,
  records `pr: <url>` under `## Dev`, then bumps.
- Tests cover both paths. Both `SKILL.md` copies (live `coga/skills/...` +
  packaged `src/coga/resources/templates/...`) stay in sync. `coga/architecture`
  / `dev/code` updated if the `## Dev` contract changes.

## Context

- **Reproduction** (no agent needed): `coga bump` × 3 on an `in_progress`
  `code/with-review` ticket with nothing built advances `implement →
  peer-review → open-pr → review`. The open-pr bump printed `step 3 → step 4`
  with no PR. That is the failure to close.
- **Current skill:** `coga/skills/code/open-pr/SKILL.md` (+ packaged copy under
  `src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/`). Keep both
  copies in sync (CLAUDE.md rule).
- **Script-step machinery** and env vars (`COGA_TASK_SLUG`, `COGA_TASK_DIR`,
  `COGA_TASK_BLACKBOARD`, `COGA_SKILL_DIR`, …) and examples to mirror:
  `coga/skills/coga/digest/flush`, `coga/skills/coga/autoclose/sweep`, the dream
  workers. Script-step semantics are in `coga/architecture` ("Mode and
  execution"); a step runs as a script when its single skill declares a
  `script:` entry.
- The `## Dev` blackboard convention (`branch:` / `worktree:` / `pr:`) is
  defined in the `dev/code` context.

<!-- coga:blackboard -->

## Dev
branch: open-pr-script
worktree: /home/n/Code/claude/coga-open-pr-script
pr:

## Investigation findings (implement step)

**Key discovery — the ticket's premise assumes machinery that doesn't exist yet.**
The ticket (and `coga/architecture`) say "a step runs as a script when its single
skill declares a `script:` entry." The script *resolution* half is real
(`launch_script._resolve_script` already handles "current step's single skill
declares script:"), **but the dispatch half is not**:

- `is_script_launch(cfg, ticket)` == `ticket.mode == "script"` — a *whole-ticket*
  flag. There is **no per-step** script detection anywhere
  (`grep` confirms `is_script_launch` is the only gate; it's only ever
  `ticket.mode == "script"`).
- The agent supervisor loop in `commands/launch.py` (`while True:`, ~L392–520)
  **always spawns an agent** for each step. It never checks whether the current
  step is a script step.
- Every existing script workflow (autoclose, digest, dream children,
  blocker-reminders) is a *wholly* `mode: script` ticket. No ticket today mixes
  agent steps and script steps.

`code/with-review` is `mode: agent`, so **every** step — including `open-pr` —
runs as an agent today. Simply adding `script: run.py` to the `open-pr` SKILL.md
would do nothing: the supervisor would still spawn an agent whose composed
prompt just contains the (now thin) SKILL body.

**Therefore the real change has two parts:**

1. **Launcher (core):** teach the agent supervisor to dispatch a *script step*
   inside an otherwise agent-mode workflow. Add `current_step_is_script(cfg,
   ticket)`; in the supervisor loop, when the current step is a script step, run
   `run_script_mode(cfg, ref, ticket)` (which pushes the work + auto-advances on
   exit 0, and on non-zero exit posts "script failed" and **leaves the step
   put** — exactly the fail-loud guarantee we want), then re-read + use
   `_harness_stop_reason` to stop at the human `review` step.
2. **Skill:** rewrite `code/open-pr/SKILL.md` to `script: run.py` + add `run.py`
   implementing the deterministic recipe (read `## Dev` branch/worktree/body →
   verify branch/clean/commits-ahead → `git push` → `gh pr create`/`gh pr ready`
   → write `pr: <url>` to `## Dev` → let the launcher bump). Both live +
   packaged copies.

**Why this closes the hole by construction:** the launcher only bumps a script
step on exit 0. No branch / no commits ahead / `gh` failure → non-zero exit →
step does NOT advance → fail loud. The agent can no longer bump past open-pr
without a real PR because the agent isn't the one bumping — the script's exit
code is.

**Worktree note:** under `[launch].worktree`, implement→peer-review→open-pr all
run in one launch worktree; the feature worktree path is absolute in `## Dev`,
so the open-pr script targets it with `git -C <feature_worktree>` regardless of
the script's own cwd. `_advance_after_script`'s bump/sync runs in-worktree just
like an agent step's bump.

**Design decisions surfaced to human before writing core launcher code (see FYI).**

## Implement step — complete (commit 584ebe34 on `open-pr-script`)

Settled decisions (confirmed with human):
- **Per-step dispatch:** added to the supervisor (the core change). ✅
- **Replace outright:** `code/open-pr` is now the script; no agent variant kept.
- **PR body fallback:** `## PR` section → else `## Description` → else title.

What landed:
- `src/coga/open_pr.py` — importable `open_pr()` recipe (`OpenPrError` on every
  fail-loud path); `run.py` (live + packaged) is a thin wrapper (mirrors
  autoclose/digest).
- `src/coga/commands/launch_script.py` — `current_step_is_script(cfg, ticket)`.
- `src/coga/commands/launch.py` — supervisor loop dispatches a script step via
  `run_script_mode` (advances only on exit 0; non-zero → fail-loud, no advance).
- `src/coga/autoclose.py` — `parse_worktree_path` (shared `## Dev` parser).
- `code/open-pr/SKILL.md` declares `script: run.py`; `code/with-review`,
  `code/with-self-review`, `code/design-then-implement` workflow docs updated;
  `coga/architecture` + `dev/code` contexts document the new shape. Both
  live + packaged copies in sync (enforced by a test).

Tests (all green — full suite 1080 passed, 1 skipped):
- `tests/test_open_pr.py` — opens+records PR, `## Description` fallback, readies
  a draft, and the fail-loud paths (no commits ahead = the incident case, no
  branch, no worktree, dirty tree); `set_dev_pr` units; live/packaged sync.
- `tests/test_launch.py` — `current_step_is_script` detection + supervisor runs
  the scripted step as a script, never spawning an agent.
- Wheel builds clean on a symlink-free export and ships the new files.
- `coga validate` shows no new errors (only pre-existing unrelated dogfood drift).

Scope notes: the packaged `coga/architecture` context was already ~118 lines
divergent from the live copy on `main` (unrelated topics); I applied **only** my
subsection to each, preserving that pre-existing drift rather than reconciling it
here. `coga/bootstrap/**` mirrors are vestigial (runtime never reads them; the
codebase context says leave them) — untouched.

Note this ticket's OWN open-pr step will still run the old agent way: launch
worktrees fork from `main`, so the new behavior only applies once this merges.

## Usage

{"agent":"claude","cache_creation_input_tokens":622914,"cache_read_input_tokens":40111304,"cli":"claude","input_tokens":54600,"model":"claude-opus-4-8","output_tokens":308492,"provider":"anthropic","schema":1,"session_id":"337eb95f-f254-4f3f-a564-6adc2e26b5b0","slug":"make-open-pr-a-script-step-so-bump-requires-a-real","step":"implement","title":"Make open-pr a script step so bump requires a real PR","ts":"2026-07-04T17:52:03.583746Z","usage_status":"ok"}
