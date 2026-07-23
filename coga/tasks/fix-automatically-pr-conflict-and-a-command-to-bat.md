---
slug: fix-automatically-pr-conflict-and-a-command-to-bat
title: fix automatically PR conflict and a command to batch fix them
status: in_progress
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/codebase
- coga/principles
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
---

## Description

Ship a launchable command that resolves conflicts across the repo's open
PRs in one pass, and land the launch-side arg channel that lets it target a
single PR.

The command is authored as a **command ticket** under `coga/bootstrap/`
(the seam the `commands-as-tickets-open-pr-pilot` pilot landed — **merged to
main as PR #625, commit `9965e95e`**: local-first
`coga/bootstrap/<name>/ticket.md` resolution + `[aliases]`), so a ticket plus
one alias line mints a new `coga` verb with zero core-Python change. It is
launched in place each time, not instantiated per run.

Behavior:

- `coga resolve-conflicts` — enumerate every open PR (`gh pr list --state
  open`), and for each one that is conflicted against `main`, rebase it,
  resolve the conflicts with **full agent judgment** (read both sides,
  understand intent, re-apply the branch's change on top of main's), verify
  with `python -m pytest` when the diff touches `src/` or `tests/`, and
  `git push --force-with-lease`. This is deliberately more aggressive than
  the mechanical-only posture below it — the agent may resolve semantic
  conflicts, so verification before push is the safety net.
- `coga resolve-conflicts <PR>` — scope to a single PR. This requires the
  **arg channel for agent launches** (see below), which does not exist yet.

Because full agent judgment needs an agent (not a script), the command is an
**agent** launch. Today `coga launch` fails loud when an agent launch is
given trailing args (`launch_script.py` writes `COGA_ARG_1..N` for *script*
launches only; #625 explicitly deferred composing args into agent prompts
"until a second use case exists"). **This ticket is that second use case:**
extend `launch` to compose trailing args into the agent prompt so
`coga resolve-conflicts 631` works. This agent-prompt composition is the one
genuinely unbuilt piece — the bootstrap resolution and the script arg
channel are already live on main.

This **supersedes** the `rebase-stale-worktrees` recurring task. That task
already walks live branches and rebases them mechanically; the new command
is the PR-scoped, judgment-capable successor. Delete
`coga/recurring/rebase-stale-worktrees/` and **keep its weekly `0 8 * * 1`
schedule** by moving it onto the new command — a thin `coga/recurring/`
entry that launches `coga resolve-conflicts` weekly (or equivalent wiring;
implementer's choice). The command is **open-PRs-only**: it enumerates
`gh pr list --state open` and does *not* sweep stale branches that have no PR
yet. That is an **accepted, documented limitation** of the supersession — the
old task's pre-PR-branch coverage is intentionally dropped, not reimplemented.

The per-run summary goes to **stdout + Slack** (one line per PR, then a
`coga slack` roll-up). Nothing durable is written to disk — this fits the
stateless command-ticket model and avoids the new command writing other
tickets' files.

## Acceptance Criteria

- [ ] `coga/bootstrap/resolve-conflicts/ticket.md` exists as a stateless
  command ticket (no `status`/`workflow`; body documents the verb) and
  `coga resolve-conflicts` runs it via a default alias
  (`launch bootstrap/resolve-conflicts`).
- [ ] Running it with no args sweeps all open PRs: for each conflicted-vs-main
  PR it rebases, resolves conflicts with agent judgment, runs `pytest` when
  the diff touches `src/`/`tests/`, and `git push --force-with-lease`. A PR
  it cannot safely resolve is reported, never force-pushed.
- [ ] Verification gates the push: a rebase whose `pytest` fails is left
  unpushed and reported `verify-failed`, matching `rebase-stale-worktrees`'
  posture.
- [ ] `coga launch <agent-target> <ARG...>` composes trailing args into the
  agent prompt (the deferred half of the `commands-as-tickets` arg channel);
  `coga resolve-conflicts 631` scopes the run to PR 631. The `COGA_*` env
  reservation and the existing script-launch `COGA_ARG_*` behavior are
  untouched.
- [ ] Per-run summary prints one line per PR to stdout and posts a one-line
  roll-up via `coga slack`; nothing is written to any ticket blackboard.
- [ ] `coga/recurring/rebase-stale-worktrees/` is deleted and any reference
  to it (docs, cron config) is updated or removed.
- [ ] The weekly `0 8 * * 1` schedule is preserved on the new command (a
  `coga/recurring/` entry that launches `coga resolve-conflicts` weekly, or
  equivalent), so there is no window with neither task scheduled.
- [ ] Live + packaged copies stay in sync where touched (the arg-channel docs
  in `coga/architecture`, `coga/codebase`, and `docs/reference.md`; the new
  command ticket under both `coga/bootstrap/` and, if it should ship as a
  battery, `src/coga/resources/templates/coga/bootstrap/`).
- [ ] `python -m pytest` green; `coga validate` clean.

## Context

**Reuse the pilot's seam — don't rebuild it.** `commands-as-tickets-open-pr-pilot`
(**merged, PR #625, commit `9965e95e`**) landed: local-first
`coga/bootstrap/<name>/ticket.md` resolution (over the package resource), the
`COGA_ARG_1..N` + `COGA_ARGC` env channel for **script** launches, and
`open-pr` as the first shipped command ticket + default alias. All of this is
on `main` now — no coordination or waiting needed. Read that ticket's
blackboard and PR before starting — it is the template for authoring
`resolve-conflicts` and it documents exactly where the agent-arg channel was
deferred (`launch()` in `src/coga/commands/launch.py`; the script channel
lives in `src/coga/commands/launch_script.py`, and agent launch with trailing
args currently fails loud *before* the TTY gate). The only unbuilt piece this
ticket needs from that seam is composing args into the **agent** prompt.

**Sequence the work: seam → command → deletion.** The three deliverables are
separable and should land as distinct commits in that order: (1) the core
`launch` change that composes trailing args into an agent prompt, with its own
tests; (2) the `resolve-conflicts` command ticket that consumes it; (3)
deleting `rebase-stale-worktrees` and settling its cron. Deliverable (1) is a
generic kernel seam every future agent-arg use case inherits — treat it as the
load-bearing part, not an afterthought of the command.

**Supersession is NOT a strict superset — the gap is accepted, not closed.**
`rebase-stale-worktrees` enumerates from **live branches** (worktrees +
`branch:` under non-terminal tickets). The new command enumerates from **open
PRs** (`gh pr list`). A stale in-flight branch with **no PR yet** (a ticket
still before its `open-pr` step) was swept by the old task but is invisible to
the new one. **Owner decision (settled):** the command stays open-PRs-only and
this pre-PR coverage is intentionally dropped — do not add live-branch
enumeration to "restore" it. Document the limitation where the command is
described (its `coga/bootstrap/` ticket body).

**The behavior already half-exists.** `coga/recurring/rebase-stale-worktrees/ticket.md`
enumerates live branches (worktrees + `branch:` under non-terminal tickets),
`git fetch`es, tests staleness with `git merge-base --is-ancestor`, rebases
onto `origin/main`, resolves *trivial mechanical* conflicts only, verifies
(pytest when `src/`/`tests/` touched), and `git push --force-with-lease` for
branches with an upstream. Lift its run-order and its report vocabulary
(`rebased-pushed`, `up-to-date`, `conflict`, `skipped-dirty`,
`verify-failed`) into the new command — the two differences are: (a) the new
command enumerates from **open PRs** (`gh pr list`) not from live branches,
and (b) it may resolve **semantic** conflicts with agent judgment, not just
mechanical ones. Then delete `rebase-stale-worktrees`.

**Safety posture.** Force-pushing a PR branch is outward-facing and hard to
reverse. The chosen posture is full agent judgment *with* mandatory
verification before push and explicit per-PR reporting; a PR the agent
can't confidently resolve is aborted (`git rebase --abort`, worktree left as
found) and reported for a human, never force-pushed. There is no dry-run
flag in this scope — the verification gate and abort-on-doubt rule are the
safety net. (`--dry-run` was considered and set aside; revisit if the sweep
proves too eager in practice.)

**Workflow note.** Runs `code/with-review` (implement → peer-review →
open-pr → review). This ticket deletes a recurring task and changes core
`launch`; the owner chose to see the approach at PR time rather than gate a
separate design step. The peer-review step is the last judgment gate before
the PR.

## Out of Scope

- A `--dry-run` / plan-only mode (deferred; abort-on-doubt + verify-before-push
  is the safety mechanism instead).
- Writing conflict-resolution outcomes onto originating tickets' blackboards
  (rejected — the command stays stateless; summary is stdout + Slack only).
- Keeping `rebase-stale-worktrees` alongside the new command (rejected — the
  new command supersedes it; two things force-pushing the same branch is the
  hazard being removed).
- Composing trailing args into *script* prompts (already shipped by #625) —
  this ticket adds only the **agent**-launch arg composition.
- Re-litigating the `commands-as-tickets` seam (local-first resolution, the
  alias mechanism, the `requires: pr` gate) — reuse it as-is.
- Sweeping stale branches that have **no open PR yet** (accepted dropped
  coverage from `rebase-stale-worktrees` — the command is open-PRs-only).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/633
branch: resolve-conflicts-command
worktree: /tmp/coga-resolve-conflicts

## PR

Summary:
- Add the generic agent-launch argument block while preserving the script `COGA_ARG_*` channel.
- Ship `coga resolve-conflicts [PR]` as a stateless command ticket with complete open-PR discovery, actual-conflict selection, verification-before-push, explicit leases, and stdout/Slack reporting.
- Replace `rebase-stale-worktrees` with an agent-supervised weekly wrapper on the same schedule, intentionally retaining the documented open-PR-only scope.

Test plan: `python -m pytest` (1483 passed, 1 skipped) and `coga validate --task fix-automatically-pr-conflict-and-a-command-to-bat --json`.

## Implement plan

- Land the generic agent-launch trailing-argument prompt seam and focused tests first.
- Add the stateless `resolve-conflicts` command ticket and default alias, keeping live/package docs synchronized.
- Replace `rebase-stale-worktrees` with a weekly thin launcher for the new command, preserving `0 8 * * 1` while intentionally dropping pre-PR branch coverage.
- Verify the full suite and task validation, rebase onto current `origin/main`, and hand off as three commits.

## Implement progress

- `60823282` — generic agent-launch arg seam: scripts retain `COGA_ARG_*`; agents receive an appended `## Launch arguments` JSON array with argument boundaries preserved. Updated launch/architecture/codebase/CLI/reference docs.
- Regression-first verification: the new agent-argument test failed against the prior refusal, then passed after the change; `python -m pytest tests/test_launch.py tests/test_launch_script.py -q` → 115 passed.
- `4fe1db5d` — added byte-identical live + packaged `resolve-conflicts` stateless agent command tickets, the default alias, command/reference docs, and focused launch/alias tests. The ticket preserves the old rebase run order and result vocabulary while explicitly limiting discovery to open PRs.
- Found and closed two command-ticket seam gaps: `coga slack --task` previously resolved durable tasks only, and a stateless agent command had no lifecycle transition with which to release its supervisor. Bootstrap-target FYIs now use the generic resolver and, after a successful post, signal only that bootstrap session complete; durable-task FYIs remain non-terminal. Focused sentinel tests cover both paths. `python -m pytest tests/test_aliases.py tests/test_commands.py tests/test_launch.py -q` → 199 passed before the sentinel follow-up; focused follow-up tests pass.
- `78d5929e` — deleted the live + packaged `rebase-stale-worktrees` battery and replaced it with a thin live + packaged `resolve-conflicts` recurring wrapper. It preserves `0 8 * * 1`, delegates via `exec coga resolve-conflicts --queue-guidance`, documents the accepted open-PR-only limitation, and carries the live template's existing `2026-W29` high-water mark (packaged copy intentionally omits runtime state). Queue guidance now documents the bootstrap-command completion path so scheduled runs proceed and terminate without a nonexistent task transition.
- `python -m pytest tests/test_packaging.py tests/test_recurring.py -q` → 133 passed, 1 skipped. The new packaging regression asserts the wrapper schedule/dispatch and that the obsolete packaged directory is absent.

## Final verification

- Final branch: `resolve-conflicts-command` at `78d5929e`; three commits in the required seam → command → recurring-replacement order. Worktree is clean and `origin/main` (`2e6180ae`) is an ancestor after the final fetch/rebase check.
- `python -m pytest` on the final tree → 1483 passed, 1 skipped. The skip is the environment-gated wheel test (`hatchling` absent from the starting interpreter).
- Isolated `python -m pip wheel --no-deps .` then succeeded with build isolation. The wheel contains `bootstrap/resolve-conflicts/ticket.md` and `recurring/resolve-conflicts/ticket.md`; it contains no `rebase-stale-worktrees` resource.
- `coga validate --task fix-automatically-pr-conflict-and-a-command-to-bat --json` → exit 0 / `ok_count: 1`; only the expected clone-local `missing-user` warning. Repo-wide validation was also inspected and its nonzero result is entirely pre-existing unrelated draft/state drift (for example `op-service-account` and old `v2/*` drafts), with no issue for this task or the new command/recurring resources.
- CLI smoke: top-level help lists `resolve-conflicts → launch bootstrap/resolve-conflicts`; `launch --help` documents script env args versus the agent prompt block. Live + packaged command tickets are byte-identical, and both obsolete recurring directories are absent.
- Adjacent harness finding (not fixed here): two full-suite subprocess tests inherited this live launch's `COGA_TASK_BLACKBOARD` and appended fake `Dream Skill: validate-drift` reports to the control ticket. Those test artifacts were removed before handoff; a follow-up should scrub the remaining `COGA_TASK_*` metadata in the autouse environment guard.

## Peer review

- `codex review --base main` completed against `78d5929e`; focused review tests were `228 passed, 1 skipped`, and its full-suite run was `1483 passed, 1 skipped`.
- Must fix: the literal `origin/main` ancestry test treats Coga's own generated `coga/tasks/**` and `coga/log.md` commits as PR staleness, causing needless force-push churn. Select actual conflicts from refreshed PR mergeability instead.
- Must fix: the inline-script recurring wrapper is classified as headless script work, so its nested agent bypasses recurring's TTY admission and liveness supervisor. Make the recurring run agent-backed and keep its body a thin delegation to the command ticket.
- Must fix: `gh pr list` defaults to 30 results. Require paginated/adequately bounded enumeration so sweep mode covers every open PR.
- Applied: command discovery now uses `--limit 10000` with an explicit truncation/pagination fallback; every PR is refreshed and only `CONFLICTING` heads proceed, while `MERGEABLE` heads are left untouched and `UNKNOWN` fails safe after bounded retries.
- Applied: the weekly template is agent-backed (no `script:`), so recurring owns TTY admission, selected-agent override, queue posture, idle timeout, and max-session. Its agent delegates through the alias using its current agent type, then marks the period task done only after success.
- Verification after fixes: focused command/wrapper regressions `2 passed`; affected launch/command/packaging/recurring suite `358 passed, 1 skipped`; full suite `1483 passed, 1 skipped`.
- Peer-review fix commit rebased as `896e34c2`; branch is clean on fresh `origin/main` `591f7531`, which is an ancestor of HEAD. Post-rebase `python -m pytest` again passed `1483 passed, 1 skipped`.
- Final task validation after writing the PR handoff: `coga validate --task fix-automatically-pr-conflict-and-a-command-to-bat --json` → exit 0, `ok_count: 1`, no issues.
