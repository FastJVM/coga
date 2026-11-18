---
title: Restore sweep policy after read-only launch API calls
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 3 (open-pr)
agent: claude
launch_generation: pending:41372edd-6c62-4e6f-b403-3578b5d548c9
---

## Description

`coga.launch.launch(..., read_only=True)` sets `git.state_sweep_withheld` to
`True` and never resets it, so the policy leaks into the caller's context after
the call returns or bails. Peer review of PR #1233 (finding 7) found this; the
owner deferred it from the report-extraction PR on 2026-11-16. Today the
`coga recurring list` adapter covers for the leak by setting and resetting the
flag around its own call.

Limit the policy to the read-only invocation. When the call finishes, the
caller's previous value of `state_sweep_withheld` must be restored, whether the
call returns or bails. That covers a nested caller that already had it `True`,
and an ordinary writer command whose end-of-command sweep must still publish
afterwards. Then remove the adapter's workaround if it is redundant, or record
on the blackboard why it has to stay.

Done means: the read-only branch restores the caller's value on success and on
`LaunchBail`. Regression tests show that a caller's `False` and `True` both
survive a direct `launch(read_only=True)` call, and that an ordinary writer
command still runs its exit sweep after an in-process read-only call. A test
runs `coga recurring --force list` and shows no "withheld" warning. Decide
whether the CLI read-only test in `tests/test_cli.py` needs an API-level twin.
The adapter workaround is either removed with tests passing or kept with a
recorded reason. The same PR updates any topic text about this policy.

## Context

### Code facts (cite by symbol; line numbers drift)

- `git.state_sweep_withheld` is a `ContextVar[bool]`, default `False`. Its
  comment says `cli.main` scopes it to one invocation. The ordinary path in
  `cli.main` sets it to `False` with a token around `app()` and resets it in
  `finally`. The end-of-command `_sweep_coga_state` is skipped when the flag
  is set.
- The `cli.main` read-only argv path (`_read_only_launch_requested`) already
  sets the flag to `True` with a token and resets it. Only the **Python API**
  branch `launch.launch` (`if read_only:`) calls
  `git.state_sweep_withheld.set(True)` and drops the token, on both the
  `LaunchResult` return and the `_bail` paths.
- `commands/recurring.py` `list_recurring` (the compensating adapter) sets the
  flag to `False` with a token, calls
  `launch_target("bootstrap/recurring-list", ..., read_only=True)`, and resets
  in `finally`. Its comment says "recurring list already has no exit sweep".
  That is only partly true. `_should_sweep_coga_state` skips plain
  `recurring list`, but for `coga recurring --force list` (tested in
  `tests/test_recurring.py`) the subcommand starts with `-`, so the sweep
  runs. `_sweep_coga_state` also checks `state_sweep_withheld` before it checks
  argv, so a leaked `True` would print a false "state sweep withheld" warning.
  The adapter's reset therefore does real work today. It becomes redundant
  once the API restores the caller's value.
- Nothing inside the read-only call reads the flag:
  `launch_script.run_script_phase` doesn't consult it, and a subprocess doesn't
  inherit a ContextVar. Both fixes are valid: scope the `set(True)` with a
  token, or delete it. Choose one and record the reason on the blackboard. If
  you scope it, wrap the whole `if read_only:` branch in try/finally, because
  the option-combination `_bail` runs right after the set.
- Many other `state_sweep_withheld.set(True)` calls in `launch.py`,
  `publish_state.py`, `commands/launch.py`, `commands/ticket.py`, and
  `commands/skill.py` are deliberate writer-side retention signals (a refused
  checkout return keeps dirt, and the outer `cli.main` scope clears them).
  **They are out of scope**; do not convert them to tokens.
- Existing coverage: `tests/test_launch_script.py` calls
  `launch_module.launch("bootstrap/inspect", ..., read_only=True)`.
  `tests/test_recurring.py` and `tests/test_cli.py` cover the adapter and the
  CLI path.

### Policy contract (cited, not attached)

`coga/launch` (`src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md`)
is cited, not attached. Read its read-only launch section (`coga launch
--read-only`). The fact that matters here: read-only dispatch performs no
publication or CLI exit sweep "on success or refusal", and "ordinary launch
remains the default and retains its publication and completion boundaries".
This ticket makes the Python API honor the second clause for its caller.
Update that topic, and `coga-dev/microkernel` if it describes the flag, in the
same PR if wording changes.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: restore-sweep-policy-after-read-only-launch

## Handoff (implement)

Changed:
- `launch.launch` (`if read_only:` branch): the `state_sweep_withheld.set(True)`
  now keeps its token and the whole branch is wrapped in try/finally that
  resets it, covering the `LaunchResult` return and every `_bail`
  (option combination, target, config/secret errors).
- `commands/recurring.py` `list_recurring`: removed the set(False)/reset
  workaround; it is redundant now that the API restores the caller's value.
- `coga/launch` topic (read-only dispatch): added one sentence saying the
  withheld publication is scoped to the call and an in-process API caller keeps
  its own exit sweep. `coga-dev/microkernel` does not describe the flag, so it
  is unchanged.

Decisions:
- **Scope with a token rather than delete the set.** This keeps the flag true
  for any in-process code that runs during the read-only call (defense in
  depth for a refusal inside it), and the reset also discards any writer-side
  `set(True)` reached inside the call. Nothing reads the flag during the call
  today, so deleting it would also have worked. The token is the narrower
  change.
- **`recurring --force list` is refused by the recurring callback (exit 2)
  before the list adapter runs**, so it never reaches the read-only call. The
  ticket's premise there was slightly off. `coga recurring --interactive list`
  is the spelling that both sweeps at exit and reaches the adapter. The new
  test covers both. Only the `--interactive` case fails with the fix reverted
  and the workaround removed.
- **CLI/API twin:** `tests/test_cli.py::test_read_only_launch_finalization_restores_context`
  covers the argv path. The new
  `test_read_only_python_api_restores_caller_sweep_policy` is its API-level
  twin, so no further CLI test is needed.

Tests added:
- `tests/test_launch_script.py::test_read_only_python_api_restores_caller_sweep_policy`:
  caller False/True × {returns, option bail, target bail}. It also asserts the
  flag is True while the script spawns.
- `tests/test_launch_script.py::test_writer_command_sweeps_after_in_process_read_only_call`:
  `cli.main` writer argv whose app calls `launch(read_only=True)`. The sweep
  runs once with no withheld warning.
- `tests/test_recurring.py::test_recurring_option_before_list_sweeps_without_withheld_warning`:
  `--force list` (exit 2) and `--interactive list` (exit 0), each with one
  sweep and no "withheld" text on stderr.
- Without the launch.py fix, 4 of the 7 launch_script cases fail, and so does
  the `--interactive` recurring case.

Note: the shell's `python` lacks `tomlkit`; use `.venv/bin/python -m pytest`.

## Peer review

Independent direct Codex review of Claude's implementation completed on
head `4384e80416d19cfc354a7c21c1161fbae49b05f9` against base `3f206d29676ee19488097c7e26b842492631680d`.
No must-fix findings. The token reset covers normal return, early refusal, and
target resolution failure. The recurring adapter can rely on the restored
policy. The CLI argv test and direct API test cover their respective entry
points. `--force list` exits 2 before dispatching the adapter and
`--interactive list` reaches it. Both exercise the exit sweep without a
withheld warning. The diff changes no terminal rendering or input handling.

The full Linux suite passed with 4992 tests passed and 33 skipped.
Python 3.11 test dependencies were unavailable in the existing environment.
Native Windows and macOS verification is deferred to release.

## PR

```yaml
title: "Restore caller sweep policy after read-only launch API calls"
author: "claude"
author_evidence: "Implement session ran on Claude (Opus 5.5) in a megalaunch queue; commit adc5516d4 authored there."
head: "4384e80416d19cfc354a7c21c1161fbae49b05f9"
base: "3f206d29676ee19488097c7e26b842492631680d"
depth: "skim"
rationale: "The change is confined to one ContextVar scope and removal of its adapter workaround. Independent review\
  \ and the Linux suite passed. The recurring option cases exercise distinct dispatch paths."
implementation: "launch.launch's read_only branch keeps the state_sweep_withheld token and resets it in finally\
  \ on both the return and LaunchBail paths. The recurring list adapter's set/reset workaround is removed. coga/launch\
  \ notes that the withheld policy is scoped to the read-only call."
deviations: "The ticket expected `coga recurring --force list` to reach the adapter. The recurring callback refuses\
  \ it first (exit 2), so the test also covers `--interactive list`, which does reach the adapter and sweeps at\
  \ exit."
limitations: "Linux checks used Python 3.12.12. The Python 3.11 environment lacked test dependencies. Native Windows\
  \ and macOS verification is deferred to release."
files:
  src/coga/launch.py: "Scope the read-only branch's withheld policy with a token reset in finally."
  src/coga/commands/recurring.py: "Remove the now-redundant caller-policy set/reset around the read-only list call."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: "State that the read-only withheld\
    \ policy is scoped to the call."
  tests/test_launch_script.py: "Regression tests for caller False/True restoration on return and bail, and for a\
    \ writer's exit sweep after an in-process read-only call."
  tests/test_recurring.py: "Show that recurring --force list and --interactive list sweep without a withheld warning."
review:
  reviewer: "codex"
  kind: "independent"
  status: "passed"
  head: "4384e80416d19cfc354a7c21c1161fbae49b05f9"
  base: "3f206d29676ee19488097c7e26b842492631680d"
  detail: "Direct Codex peer review of Claude's implementation completed with no must-fix findings."
checks:
- command: "env PYTHONPATH=\"$PWD/src\" .venv/bin/python -m pytest -q"
  status: "passed"
  head: "4384e80416d19cfc354a7c21c1161fbae49b05f9"
  base: "3f206d29676ee19488097c7e26b842492631680d"
  detail: "Pop!_OS 24.04 LTS, Python 3.12.12. 4992 passed, 33 skipped in 854.82s."
- command: ".venv/bin/python -m pytest -q tests/test_launch_script.py tests/test_recurring.py tests/test_cli.py\
    \ -k 'restores_caller_sweep_policy or writer_command_sweeps or option_before_list or read_only_launch_finalization'"
  status: "passed"
  head: "4384e80416d19cfc354a7c21c1161fbae49b05f9"
  base: "3f206d29676ee19488097c7e26b842492631680d"
  detail: "Pop!_OS 24.04 LTS, Python 3.12.12. 10 passed, 669 deselected in 0.53s."
```
