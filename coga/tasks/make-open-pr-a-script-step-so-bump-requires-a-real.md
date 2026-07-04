---
slug: make-open-pr-a-script-step-so-bump-requires-a-real
title: Make open-pr a script step so bump requires a real PR
status: active
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
