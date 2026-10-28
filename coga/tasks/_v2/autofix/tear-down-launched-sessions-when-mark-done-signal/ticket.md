---
title: Tear down launched sessions when mark done signal goes unobserved
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
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

### What broke

In the 2026-10-26 sweep, `recurring/dream` was reported as **timed-out**: "liveness watchdog tore the session down before it signalled done". Yet the ticket status after the run was `done`. The agent did finish its work and mark the task done. The supervisor never saw that done signal and kept the REPL open until the idle watchdog stopped it about 22 minutes later.

### Evidence

- Claude session transcript `~/.claude/projects/-home-n-Code-claude-coga-coga/c3d70c60-897e-473f-ad37-39f56468aef9.jsonl`:
  - At `18:14:35Z` the agent ran this from the Dream ops worktree `/home/n/Code/claude/.dream-retro-20261026T172253Z/dream-ops`:
    `env COGA_REPO_ROOT=$D COGA_COGA_OS_ROOT=$D/coga COGA_TASK_TICKET=… COGA_TASK_BLACKBOARD=… COGA_TASK_DIR=… COGA_EXPECTED_TASK=… coga mark done recurring/dream --message …`
  - At `18:14:42Z` the command printed `recurring/dream: done`, so it succeeded.
  - The agent's last message came at `18:14:55Z`. After that the session was idle.
- `coga/log.md` (commit 10039833e): the system usage record for `recurring/dream` shows `"exit_code":124,"exit_kind":"timeout","outcome_status":"timed_out"` and `ended_at 18:36:46Z`. The `task done` log line is at 11:14 local (18:14Z).
- Every earlier weekly Dream run in `coga/log.md` ended without a timeout. The visible difference this week is that Dream ran its closing commands from a separate ops worktree, with `COGA_*` variables repointed by `env`, because the primary checkout was occupied.

### Where it lives

- `src/coga/commands/mark.py:214`: `done` calls `emit_done_marker(session_id=ref.id_slug)`.
- `src/coga/repl_supervisor.py` `emit_done_marker` (~line 808): it returns silently if `COGA_DONE_SENTINEL` is unset, and it swallows any `OSError` from the atomic write. The sentinel file is the only channel, so either case quietly falls back to the idle/max-session backstop.
- `src/coga/repl_supervisor.py` `run_with_done_marker` (sentinel poll ~line 655) and `_sentinel_signals_done`: the content must equal `recurring/dream`.
- `src/coga/launch.py:3726`: the supervisor is scoped to `session_id=ref.id_slug`.
- `src/coga/recurring_runner.py` ~2640: `kind == "timeout"` is checked before terminal status. So a run that reached `done` is reported only as `timed-out`, and nothing records that the work had actually completed.

### What a fix must do

1. **Find out why the signal was missed.** Possible causes:
   - `COGA_DONE_SENTINEL` was missing from the agent's Bash environment.
   - The atomic write (temp file plus rename into the `coga-done-*` dir) failed and was swallowed.
   - The sentinel content did not match.

   Add a regression test for `mark done` run from a different worktree with repointed `COGA_*` variables.
2. **Stop failing silently.** If a session-ending command runs under a supervised launch (for example `COGA_EXPECTED_TASK` is set) and `emit_done_marker` cannot write the sentinel or finds no sentinel variable, it should warn on stderr. The agent and the human can then see that the REPL will not tear down.
3. **Add a backstop in the supervisor.** It could also treat the launched ticket's own terminal status as a done signal, polled cheaply. Then a completed run is torn down within seconds, not after the idle timeout.
4. **Report the outcome accurately.** When a liveness teardown finds the ticket already terminal, the recurring outcome should say so, for example `completed (late teardown: done signal not observed)`, instead of a bare `timed-out`. That keeps it separate from a real wedge.
5. Update `docs/contexts/coga/recurring/scheduling/inactivity/SKILL.md`, which owns the liveness contract, in the same PR.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

Previous ref: `autofix/tear-down-launched-sessions-when-mark-done-signal` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/1126
branch: fix/launched-session-terminal-backstop

## Investigation

- Verified the attached run log and historical Claude transcript. At 18:12:14Z Bash output included `COGA_DONE_SENTINEL=/tmp/coga-done-zpnnitkm/sentinel`; the 18:14:35Z closing command repointed task/repo variables without replacing the sentinel and printed `recurring/dream: done` at 18:14:42Z. The audit recorded completion before the later timeout.
- Repointing the checkout alone is not a reproducible signaling failure: slug scoping already landed in `7f222d934` (2026-07-04). The old writer swallowed all write errors and retained no sentinel-content diagnostic, so the precise historical failure remains unproven. This is an evidence limitation, not a claim that the incident is fixed already.

## Implement handoff

- Implemented and pushed `5d51138e458e6ad9cfe04e953d153947b8d5ce83`; reconciled with `origin/main` at `18e4da8484581688c50e10a0acf20fc2271fbb31`. Returned this checkout to clean, fast-forwarded `main` before writing this handoff. No PR opened; next step is self-qa.
- `repl_supervisor.emit_done_marker` now warns on missing supervised channels or failed writes. `launch._terminal_status_probe` supplies a cached exact-ticket backstop to `repl_supervisor.run_with_done_marker`, preserving sentinel observation separately from teardown. `recurring_runner._task_outcome` distinguishes completed late teardown from an unfinished timeout.
- The backstop reads published control state when publication is configured, protecting in-flight lifecycle publication and observing completion from linked worktrees. It excludes bootstrap and ticket-authoring sessions. The owning liveness topic and packaged twin document the contract and limits; the development spawn topic links there.
- Added the regressions before implementation (21 failed / 1 passed); fixed them, then passed the affected modules (403 passed). The initial broad run passed 4140 / skipped 10 while the final authoring/cache guards were being finished; the fresh full run below supersedes that preliminary evidence.
- Final full suite: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` -> **4141 passed, 10 skipped** in 377.10s, exit 0, Linux Python 3.12.12. This ran on the committed/reconciled head above, with a clean tree before and after. A final fetch/rebase left the tested head/base unchanged. `git diff --check origin/main...HEAD` passed.
- No config, task-model, workflow, prompt composition or validation behavior changed; no seeded fixture changes or separate `coga validate` run were needed. No unrelated bugs or new follow-up obligations identified. Python 3.11/native Windows and real vendor-agent sessions were not exercised; the suite includes POSIX PTY and real linked-worktree command regressions.
- Actual implementer: Codex (GPT-6), no model override; the ticket's configured Claude identity is not the implementer. No code review performed in implement; self-qa owns the next judgment and must refresh preparation after any fixes/rebase.

## Self-QA

- Reviewer: Claude (Opus 5.5) ran `/code-review` (default effort) against `origin/main...5d51138e4`. The review **returned** with 9 findings and nothing is still in flight. The code was authored by Codex, so this review is independent of the implementation. The fixes below were written by this same Claude session and have only been self-reviewed since.
- Applied (`49fafb066`):
  - The unset-sentinel warning gave false alarms in no-PTY launches and strict-assist ticket scripts. Both now export an explicit empty `COGA_DONE_SENTINEL`, which means "no channel" and stays quiet. Unset still warns when a supervised witness is present.
  - A terminal state the probe sees at its first observation is now ignored, so a stale published blob cannot tear down a fresh session.
  - The probe's git setup now resolves once. A ticket outside the git root, or a failed lookup, disables the probe instead of retrying a failing git call every second.
  - The duplicated warning text is now one helper.
- `/simplify` ran with reuse, simplification, efficiency and altitude agents; fixes in `e89dcb265`:
  - The probe now reuses `git._blob_oid`, `git._blob_bytes` and `git._parse_ticket`, and keeps its lazy source in one value.
  - The late-teardown outcome is folded into the terminal-status arm of `_task_outcome`.
  - Efficiency found nothing.
- Skipped, left for the human reviewer:
  - `/code-review` #3/#4: a human canceling the ticket from another terminal now ends the session within about 5 s, and a timeout that finds the ticket terminal reports `completed`, even when the session did not make the transition itself. The ticket asked for exactly this ("treat the ticket's terminal status as done").
  - `/code-review` #5: one `git rev-parse` per second inside the PTY loop. Accepted as cheap.
  - `/code-review` #8: `getattr(cfg, "git_enabled", False)` stays because many spawn tests pass `SimpleNamespace` configs.
  - Altitude: "fix the root cause instead of adding a probe", and "warn only on write failure". The investigation could not prove how the historical signal was lost, and the ticket explicitly requires both the backstop and the unset-variable warning.
- No raw-terminal or TUI surface changed visibly. The probe runs inside the PTY loop, but only through a callable that the PTY tests already exercise. No manual terminal sweep was needed.
- Tests at `e89dcb265`: full suite 4145 passed, 10 skipped. `git diff --check` is clean. Pushed; no rebase was needed because `origin/main` moved only by Coga state commits.

## PR

```yaml
title: Tear down terminal task sessions when completion signaling is lost
author: codex
author_evidence: The implement session ran as Codex (GPT-6) and wrote 5d51138e4. The self-qa fixes in 49fafb066 and e89dcb265 were written by Claude (Opus 5.5) in this self-qa session.
depth: deep
rationale: Changes process teardown and how recurring outcomes are classified. Claude's independent review applies to 5d51138e4 only; the self-qa fixes after it have been self-reviewed but not independently re-reviewed. The original swallowed-signal failure cannot be diagnosed conclusively.
implementation: Warn on stderr when a supervised session has no completion channel, or when the atomic sentinel write fails. An explicit empty sentinel marks launches where no supervisor polls. Poll the exact launched ticket once a second, from published control state when Git publication is configured, and release the REPL after five seconds of terminal state that first appeared during the session. This does not claim a sentinel was seen. When liveness fired first, report terminal tasks as completed with a late-teardown note. Bootstrap and authoring sessions stay sentinel-only.
deviations: The historical transcript confirms an inherited sentinel and a successful task transition, but does not record the final sentinel write or its content. Repointing task variables is not by itself a reproducible cause, so the new diagnostics cover the silent failure paths. A human canceling the ticket from another terminal also ends the session; this was left as intended and flagged in Self-QA.
limitations: Verified on Linux with Python 3.12.12. Not verified on Python 3.11, native Windows, or a live vendor-agent launch. The probe does not fetch, so completion from an independent clone is visible only after the launching repository's tracking ref updates. With a configured remote, unpublished completion is intentionally left to the sentinel and liveness channels. A ticket outside the git root gets no backstop.
files:
  src/coga/launch.py: Wire the stateful-session backstop. Resolve the git source once, throttle and cache exact-ticket state, require an open observation before a terminal one counts, keep recurring generation scope, and exclude stateless authoring.
  src/coga/launch_script.py: Export an explicit empty sentinel to ticket scripts so lifecycle calls in a strict assist do not warn falsely.
  src/coga/repl_supervisor.py: Release terminal sessions without claiming a sentinel was observed. Warn when a supervised completion channel is missing or the write fails. Export an empty sentinel on the no-PTY path.
  src/coga/recurring_runner.py: Distinguish completed late teardown from an unfinished watchdog timeout, keeping the explicit failure and template-damage overrides.
  tests/test_done_marker_emission.py: Exercise real linked-worktree completion with repointed COGA variables, working, missing and unwritable markers, and stale launching files.
  tests/test_launch.py: Cover terminal-state settling, terminal-at-launch rejection, the out-of-repo disable, generation and exact-ticket scope, invalid or missing state, stateless exclusions, publication safety and cached polling.
  tests/test_launch_script.py: Expect the explicit empty sentinel in the ticket-script environment.
  tests/test_repl_supervisor.py: Cover terminal-state teardown, stderr diagnostics, the quiet empty channel and the no-PTY empty export, while keeping sentinel observation and exit-classification coverage.
  tests/test_recurring_autofix.py: Cover done and canceled late teardown, and keep a missing ticket classified as a timeout.
  docs/contexts/coga/recurring/scheduling/inactivity/SKILL.md: Own the completion/liveness backstop, empty-channel and late-teardown reporting contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/inactivity/SKILL.md: Keep the packaged user-topic fallback byte-identical to its canonical owner.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Correct the shared spawn/supervisor map and link to the owning user contract.
review:
  reviewer: claude
  kind: independent
  status: failed
  head: 5d51138e458e6ad9cfe04e953d153947b8d5ce83
  base: 18e4da8484581688c50e10a0acf20fc2271fbb31
  detail: Claude /code-review (default effort) returned 9 findings on the Codex-authored head. Fixes are in 49fafb066 and e89dcb265, and /simplify ran on the branch. The applied fixes have only been self-reviewed by the same Claude session, not independently re-reviewed; the skipped findings and their reasons are in Self-QA.
head: e89dcb265293379c06543e06bc1a4046ed6349dc
base: 18e4da8484581688c50e10a0acf20fc2271fbb31
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: e89dcb265293379c06543e06bc1a4046ed6349dc
  base: 18e4da8484581688c50e10a0acf20fc2271fbb31
  detail: 4145 passed, 10 skipped in 335.01s on Linux, Python 3.12.12, on a clean committed tree.
- command: git diff --check origin/main...HEAD
  status: passed
  head: e89dcb265293379c06543e06bc1a4046ed6349dc
  base: 18e4da8484581688c50e10a0acf20fc2271fbb31
  detail: No whitespace errors.
- command: coga validate --json
  status: not-run
  detail: No config, task-model, workflow or validation behavior changed. The full suite includes the fixture smoke and packaging-twin checks.
```
