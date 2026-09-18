---
title: Attribute headless recurring completions to system
status: in_progress
owner: nicktoper
contexts:
- coga/architecture
- coga/codebase
- coga/launch-internals
- dev/code
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
agent: claude
launch_generation: 0c2099a2-09cf-4b7b-a174-3c52c05f0a29
---

## Description

Make deterministic recurring completion identify the system in audit records and outcome wording. A successful `ticket.py` currently invokes child `coga bump`, which records a human actor and names the configured agent as finisher although no agent ran.

This P2 fix scope comes from [the triage](triage-five-review-comments-that-merged-unanswered.md) and is now selected for implementation.

### Evidence and source

Original [PR 705 comment](https://github.com/FastJVM/coga/pull/705#discussion_r3834701954); source ticket: [migrate-recurring-templates-to-ticket-py-shims-and](migrate-recurring-templates-to-ticket-py-shims-and.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

An isolated `launch_script.run_script_phase` probe executed a real script and real child CLI using the shipped shim's bump argv. The child had no `COGA_SUPERVISED`; its log said `[human:marc] task done` and its outcome said `claude finished`. The live append-only log still contains this attribution for `recurring/autoclose-merged` on 2026-09-18 08:33 (also 09-10/11). PR 786 removed the original digest template, but the other four bundled shims remain affected; PR 827's recipe-reporting change did not fix completion identity.

### Expected behavior and scope

Trace `src/coga/launch_script.py::run_script_phase`, `task_env.apply_task_env`, `commands/bump.py::bump` (terminal and intermediate-step paths), `commands/common.py::current_operator`, and lifecycle outcome writers. The launcher already audits script start as system; the missing link is deterministic child completion.

Provide a narrowly scoped system completion identity through the actual script-to-CLI subprocess boundary for `autoclose-merged`, `blocker-reminders`, `branch-sweep`, and `skill-update`. Reuse lifecycle validation/publication rather than writing status or log entries directly. An attribution marker must not grant owner-gate, assist, rewind, or launch authority, and it must not let a script signal an outer agent's done sentinel.

### Acceptance and focused verification

- Run a deterministic fixture through the real launcher/script/child-bump chain with recipes stubbed or otherwise isolated. Assert system actor and system finisher wording, not only the shim's command text.
- Check terminal completion and an intermediate step; lifecycle transitions still occur exactly once.
- Preserve human CLI attribution and real agent/recorded-assist behavior. A task or configured agent name alone must not imply that an agent actually ran.
- Failures and owner handoffs retain existing behavior; no new caller-controlled shortcut around lifecycle gates.
- Extend `tests/test_launch_script.py`, `tests/test_recurring_shims.py`, and relevant bump/notification tests. Do not execute production maintenance recipes.
- Update the script/lifecycle attribution contract in `coga/contexts/coga/architecture/SKILL.md` (and the narrower launch contract if affected), plus the PR 705 `coga/codebase` gotcha and packaged twins. If shims change, update both live `coga/recurring/<name>/ticket.py` and packaged equivalents.

Tradeoff: an explicit identity must cross a subprocess without becoming a privilege grant. Do not restore digest or rewrite historical `coga/log.md` records. General audit-identity redesign, GitHub replies and merge-policy changes are outside this ticket.

## Context

- `src/coga/launch_script.py` plus `run_script_phase` owns the real deterministic
  subprocess boundary. It already audits script start as system, but previously
  cleared only supervised ownership witnesses, leaving the done sentinel inherited.
- `src/coga/commands/common.py` plus `current_operator` resolves the assigned
  workflow operator, not evidence that an agent ran. Completion attribution belongs
  in the new shared `completion_identity` used by `commands.bump.bump` and
  `commands.mark.done`, after their existing assist publication validation.

<!-- coga:blackboard -->

## Dev
branch: fix/headless-completion-system
worktree: /tmp/coga-system-completion

## Implementation plan

The live ticket is already admitted to implement; the draft-only sentence above
is stale triage history. Implement the explicitly launched scope.

Trace the actual script/child CLI boundary, add failing regression coverage, then
carry a task-scoped system attribution marker through normal lifecycle writers.
Attribution must not mint supervised ownership or assist publication authority.
Keep owner handoffs, completion gates, and publication validation intact; clear
an inherited agent sentinel at the deterministic subprocess boundary. Update the
owning contexts and packaged twins, run the suite, commit and freshen, then bump
from this primary checkout. No production maintenance recipes, push, or PR.

## Implementation findings

- Regressions reproduced the original human audit/Claude finisher mismatch through
  the real launcher, all four copied recurring shims (recipes stubbed), and child
  CLI bumps. Initial run: 23 failed, 1 passed on the attribution expectations.
- Added `COGA_SCRIPT_TASK`, scoped by absolute target path, to the task-env
  namespace. Launch re-mints it only for scripts and clears the outer sentinel;
  agent task-env setup clears the marker. It supplies identity only, never assist
  or ownership witnesses. Script rewinds are refused; completion gates stay intact.
- Bump step/final paths and mark done share completion attribution: script = system;
  validated recorded assist = its agent; matching supervised session = its derived
  agent; ordinary CLI = current human. Assigned agent/task metadata alone is not
  execution evidence. No shim or production recipe changes were needed.
- Updated architecture, launch-internals, and the PR 705 codebase gotcha, with
  byte-identical packaged twins. Focused suite: 290 passed in 19.99s. Six strict-assist
  attribution/publication regressions also passed. The final full suite passed:
  2,684 tests in 182.97s.
- Test interpreter: `/tmp/coga-system-completion-venv/bin/python`; installed declared
  `.[test]` dependencies after sandbox DNS blocked the initial install. Always run
  with `PYTHONPATH=/tmp/coga-system-completion/src` to exercise the feature source.

## Implement handoff

Committed as `047c353e` (`Attribute deterministic completions to system`) on the
recorded branch. The feature checkout is clean. Final `git fetch origin main`
and `git rebase FETCH_HEAD` reported up to date; `git rev-list --count
HEAD..origin/main` returned 0. No push or PR in this step.

Verification commands (from the feature checkout):

```sh
PYTHONPATH=/tmp/coga-system-completion/src /tmp/coga-system-completion-venv/bin/python -m pytest -q
git diff --cached --check
git fetch origin main
git rebase FETCH_HEAD
git status --short
git rev-list --count HEAD..origin/main
git diff --check
```

Full-suite result: **2,684 passed**. The seeded example copy exercises each
packaged recurring shim with its recipe stubbed; task layout, prompt composition,
and workflow shape required no fixture changes. The new tests verify local audit
and outcome identity through real subprocesses, single terminal/intermediate
transitions, outer-sentinel isolation, human/supervised/assist behavior, and
unchanged gate/publication refusals. The adjacent publication finding below is
explicitly outside this change and remains for follow-up.

## Adjacent finding — strict-assist audit publication

While extending `tests/test_launch.py`'s recorded-assist fixtures, a lifecycle
transition appeared in the feature checkout's committed `coga/log.md`, while the
bare remote's `main:coga/log.md` retained only the creation entry. Ticket state
still published successfully. This is outside this identity fix and remains
unresolved: `src/coga/git.py` plus `sync_task_state`/`_dispatch_branch_sync` owns
publication; `src/coga/pr_assist.py` plus `assist_publication_from_env` supplies
the verified lease.

Reproduction: `_seed_single_checkout_human_review`, then a real CLI bump or mark
done with the valid task-scoped assist environment; compare the local audit and
`git show main:coga/log.md` in the fixture's bare remote. Confirmed independently
with untouched primary source at `c6fcfcb1` using the three
`test_recorded_assist_completion_keeps_agent_identity` cases (all passed with
local audit/notification assertions). Baseline artifacts are under
`/tmp/coga-completion-baseline/pytest/`. No matching active follow-up was found;
the older `remov-digest-in-recurring` blackboard discusses related audit landing.
Retro should carry this finding into its durable owning context/follow-up before
deleting this ticket. Current tests assert local attribution and preserve the
existing checks that task state reaches both refs; no publication changes here.
