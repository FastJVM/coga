---
title: Normalize signal exits from read-only launch
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:ac9a902e-48a7-4b30-bca4-c93a99bf50bd
---

## Description

Peer review of PR #1233 (finding 6) found that `coga launch --read-only`
hands a signal-killed `ticket.py` child's negative return code straight to
the shell. A child killed by SIGINT returns `-2`, which the shell sees as 254
instead of the conventional 130. The owner deferred this finding from the
report-extraction PR on 2026-11-16 (source:
v1/microkernel/06-read-report-commands-as-ticket-workflows, Peer review).

Normalize the child's exit status where `ticket.py` is run, so every script
launch path follows the same `128 + signal` convention the other launch paths
already use. The owner chose to normalize once in the shared executor rather
than only on the read-only return, which covers ordinary script launches too.

Done means:

- a read-only launch whose `ticket.py` is killed by a signal exits `128 + N`
  (SIGINT gives 130), and so does an ordinary bootstrap or stateful script
  launch;
- the `script exited with code N` audit line and the `💥 script failed`
  notice report the normalized code;
- a test in `tests/test_launch_script.py` covers a child killed by a
  signal on the read-only path and on at least one ordinary script path;
- `coga/script-tickets` item 5 is updated in the same PR.

## Context

### Where the code is

- `launch_script.run_script_phase` runs the child with
  `subprocess.run([sys.executable, entry, *args], check=False)` and takes
  `exit_code = completed.returncode` as is. The `read_only` branch returns
  `ScriptPhaseResult(exit_code=...)` right after that. Normalize there, before
  the read-only early return, so the read-only return, `append_log`, the
  failure notice, and `launch._exit_failed_script` → `LaunchBail` all see the
  same value.
- `launch.launch` returns `LaunchResult(kind="script", exit_code=...)` for
  read-only. `commands/launch.py` exits through
  `oscompat.process_exit_status`, which only remaps Windows DWORD values
  (≥ 0x80000000). It passes POSIX codes, negative ones included, through
  unchanged, so Python's `SystemExit(-2)` shows up as 254.
- Code that already applies the convention: `repl_supervisor`
  (`128 + os.WTERMSIG(status)` and `128 + sig` for crashes),
  `recurring_runner` (`128 + signal.SIGTERM`), and `launch`'s own
  SIGINT/SIGTERM handler (`SystemExit(128 + signum)`). Reuse a shared helper
  if one fits. Otherwise a small private helper next to `run_script_phase` is
  fine; don't add a new core module for this.

### Constraints

- Map only negative POSIX return codes (`-N` → `128 + N`). Leave
  non-negative codes as they are: 75 (EX_TEMPFAIL retry semantics, also
  checked in `run_script_chain`) and Windows NTSTATUS values, where
  `returncode` is never negative, must keep their current meaning.
- Read-only must stay side-effect free. Don't add teardown, logging, or
  publication to the read-only branch while moving the normalization.
- No reusable helper exists: `repl_supervisor` works from a wait status, not
  a returncode. Write a small private helper.

### What the bug actually is

A terminal Ctrl-C also reaches the parent `coga`. It already exits 130
through `launch._on_signal`, or through KeyboardInterrupt on read-only. The
real defect is a signal that reaches **only the child**: a `kill`, or an OOM
SIGKILL, which should exit 137. Test that case, not a Ctrl-C through the
parent.

### Tests

The read-only fixtures live in `tests/test_launch_script.py` (the
`read_only_repo` fixture and the `test_read_only_*` tests). Have the child
signal itself, for example `os.kill(os.getpid(), signal.SIGTERM)`, and assert
143. SIGINT works too (an uncaught KeyboardInterrupt re-raises SIGINT, giving
-2), but SIGTERM is simpler. Skip on Windows. No existing test asserts a raw
negative script code. The `-SIGINT` in `tests/test_launch.py` is on a
`ReplOutcome` and is unrelated.

### Other consumers of the script exit code (check, none expected to break)

`retire/ticket.py` prints "exited {code}", recurring delegation failure
reporting is in `recurring_runner`, and `runner._escaping_exit_code`. All will
now see `128 + N` instead of a negative value.

### Docs (cited, not attached)

`coga/script-tickets`
(`src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md`),
item 5, says "launch exits with that code". Add that a signal-killed child
is reported as `128 + signal`. The `coga/launch` section "Read-only command
dispatch" already says "the usual process-status convention", so it needs no
edit.

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

branch: normalize-signal-exits-from-read-only-launch

## Handoff (implement)

- `launch_script._normalize_exit_code` (private, beside `run_script_phase`)
  maps a negative POSIX returncode `-N` to `128 + N`; non-negative codes
  (75, Windows NTSTATUS) pass through. Applied right after `subprocess.run`
  and before the `read_only` early return, so the read-only result,
  `append_log`, the `💥 script failed` notice and `_exit_failed_script`
  all see the same value. Read-only gained no new effects.
- Tests in `tests/test_launch_script.py`:
  `test_signal_killed_script_exits_128_plus_signal` (stateful launch via
  CliRunner: exit 143, log line, notice) and
  `test_read_only_signal_killed_script_exits_128_plus_signal` (real
  `python -m coga.cli launch --read-only` subprocess: shell sees 143). Both
  skip on Windows. Without the fix they fail with -15 and 241.
- `coga/script-tickets` item 5 now states the `128 + N` convention.
- Other consumers checked (retire/ticket.py, runner._escaping_exit_code,
  recurring delegation): they only report the integer; no change needed.
- Process note: no launch preparation was supplied, so the manual
  `coga/checkouts` flow was used; the code edit was made before the branch
  was claimed, then carried across the switch (branch claim published first).
- Local env: use `.venv/bin/python`; the PATH `python` lacks `tomlkit`.

## PR

```yaml
title: Normalize signal-killed ticket.py exits to 128 + signal
author: claude
author_evidence: >-
  Implement session ran as Claude Opus 5.5 (claude-opus-5-5) under megalaunch
  (coga-launch d902ba98-161a-48db-b625-a2216b97516e).
head: 1bf7a10ecea389e721d3ac86b6d6d45dd91ec88f
base: 89503cec07b530a8ae79b639df796d2e25a7b66f
depth: skim
rationale: >-
  One-line status mapping in the shared script executor plus two regression
  tests and a doc sentence; check that read-only stays effect-free and that
  non-negative codes (75) are untouched.
implementation: >-
  Adds a private _normalize_exit_code helper in launch_script and applies it
  to the ticket.py child's returncode before the read-only return, so every
  script launch path reports 128 + N for a signal-killed child.
deviations: None.
limitations: >-
  POSIX only by construction; Windows never yields negative returncodes and
  the new tests skip there. Windows/macOS not run (release-only tier).
files:
  src/coga/launch_script.py: >-
    Normalize the ticket.py child's negative returncode to 128 + signal
    before any consumer sees it.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: >-
    Item 5 documents that a signal-killed child is reported as 128 + N.
  tests/test_launch_script.py: >-
    Regression tests for a self-SIGTERM child on the stateful and read-only
    paths asserting 143 in exit status, audit line and notice.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    No code review yet; the workflow's peer-review step follows implement.
checks:
  - command: .venv/bin/python -m pytest -q tests/test_launch_script.py
    status: passed
    head: 1bf7a10ecea389e721d3ac86b6d6d45dd91ec88f
    base: 89503cec07b530a8ae79b639df796d2e25a7b66f
    detail: 92 passed on the committed, rebased head.
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 1bf7a10ecea389e721d3ac86b6d6d45dd91ec88f
    base: 89503cec07b530a8ae79b639df796d2e25a7b66f
    detail: >-
      4976 passed, 33 skipped. Ran on the uncommitted working tree before
      commit; the three diff paths are byte-identical in the commit, and the
      rebase only brought in this ticket's own state publication.
  - command: >-
      git stash -- src && .venv/bin/python -m pytest -q
      tests/test_launch_script.py -k signal_killed
    status: passed
    head: 1bf7a10ecea389e721d3ac86b6d6d45dd91ec88f
    base: 89503cec07b530a8ae79b639df796d2e25a7b66f
    detail: >-
      Regression check, fix removed: both new tests failed (-15 and 241), as
      expected; restored and they pass.
```
