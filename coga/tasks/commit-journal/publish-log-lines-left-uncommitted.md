---
title: Publish log lines that commands leave uncommitted
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
---

## Description

Some Coga log writes land in `coga/log.md` without being published by the
command that wrote them, so `main` can sit with a dirty log until a later
command's sweep picks it up, or indefinitely if none runs, and a dirty log
blocks fast-forwards and launches. Inventory every log write, classify each as
(a) published by its own command, (b) a documented deliberate deferral to a
later publish, or (c) stranded, and fix every stranded path so it publishes or
reports the failure.

Done when every log write either is published before its command exits,
prints a warning naming the retained line, or is a deferral documented in
`coga/state-publication`; each formerly stranded path has a test proving the
fix; and `python -m pytest` passes. Also decide, and record why, whether a
long-running attended session (`coga ticket`, `coga chat`) should publish its
start line immediately rather than leave it dirty for the whole session.

## Context

Split from `fix-the-commit-git-journal` (deleted); siblings
`commit-journal/coalesce-coga-state-commits` (which depends on this ticket's
inventory and lands after it) and `commit-journal/trim-the-audit-log`.

### The motivating case is a deferral, not proof of a bug

During this ticket's authoring on 2026-10-23, `git status` showed
`M coga/log.md` holding `[fix-the-commit-git-journal] [human:nicktoper] ticket
authoring launched`. `coga ticket` writes that line through
`spawn_agent_session` without `commit_log`, so nothing publishes it until a
later sync; here the first `coga create` run inside the session published it.
This is the attended-session question in the Description, not a confirmed
stranding.

### Prior work

The done ticket `surface-a-chat-end-log-line-that-was-written-but-n` fixed a
`coga chat` usage line written at session end on 2026-10-08 and never
published; it sat dirty for two weeks until `coga recurring --all` refused to
fast-forward over it. That fix covers chat teardown.

### Where to look

- Writers: `logfile.append_log` callers across about 15 modules (`bump`,
  `create`, `launch`, `launch_script`, `mark`, `recurring`,
  `recurring_runner`, `usage`, `commands/{init,owner,slack,unblock}`,
  `notification/slack`, `git`, `logfile`); search the whole `src/` tree.
- Publish paths: `git.sync_log` (log alone), `git.sync_task_state` (ticket
  plus log), and the CLI end-of-command sweep (`cli._should_sweep_coga_state`
  then `git.sync_coga_state`). Most commands sweep at exit, so likely
  stranding paths are the exceptions:
  - commands in `cli._NON_SWEEPING_COMMANDS` (`status`, `show`,
    `validate`, `usage`, `init`, `uninstall`) and the `run publish-state` /
    `prepare-checkout` exemptions;
  - every `git.state_sweep_withheld.set(True)` site (for example
    `commands/ticket` on `AuthoringError`, which leaves the launch line
    unpublished by design);
  - refused checkout returns.
- Failure records: `git.record_sync_failure` and the "sync refused" /
  "refresh failed" lines are written *because* a publish failed. They count
  as satisfied by the existing failure report; do not try to publish a
  failure record in a retry loop.

### Topic (cited, not attached; read first, update in the same PR)

`coga/state-publication` (`docs/contexts/coga/state-publication/SKILL.md`)
owns when each command publishes ("When Coga publishes") and how a stranded
log tail is recovered ("A stranded log tail blocking catch-up"). The
deliberate-deferral list this ticket produces belongs there.

Out of scope: `Read-only file system` sync failures inside agent sandboxes
(owned by `fix-coga-git-sync-failures-that-leave-main-diverge`).

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

<!-- coga:blackboard -->
## Dev

branch: coga/commit-journal-publish-log-lines-left-uncommitte-eee9dd

## Implement handoff (2026-10-26)

Commit 359aa7fbf on the branch, rebased onto origin/main 0b52bee2b, pushed. No PR yet.

### Inventory (every `append_log` writer under `src/`)

- (a) Published by the writing command: `create` (create sync), `bump` advance and
  every `mark_*` (lifecycle `sync_task_state`), `owner` (strict sync; on failure it
  retracts its line), `unblock`, `slack` (sweep), `recurring promote` (its own
  `git.publish` of task+template+log), `init` (initial commit), launch launch lines
  and `launch_script` "launched as a script" (`sync_log`), recurring delegated
  launch line (`sync_log`), usage record and the `coga ticket` line (teardown
  `sync_log`), autofix and retire creates (`sync_task_state`), recurring
  serviced/reused ledger lines (recurring publication or sweep), `launch_script`
  "script exited with code N" (checkout settlement or sweep).
- Failure records (the failure report covers them): `git.record_sync_failure`,
  "sync refused", "refresh failed", `recurring_runner._append_sync_failure`,
  phone-home "sync failed", Slack "post failed".
- (b) Deliberate retention: exit 75, `state_sweep_withheld`, `bump --to/--backward`.
  Before this change the only report was the generic "state sweep withheld" note.
- (c) Stranded, reproduced: a task `ticket.py` exiting 75 in a repo with Git enabled
  but no remote. The checkout boundary is exempt, so it never armed and nothing
  settled between phases. Launch exits 75 and the CLI skips the sweep, which left
  "script exited with code 75" dirty with no report.

### Decisions (approved by the human in session)

- Fix at the CLI boundary, not per site. `cli.main` records the log's size at
  entry. When the sweep does not run, `_warn_unpublished_log_lines` names each
  appended line control lacks (remote-tracking ref, else local control),
  prints at most 10, and gives the `coga run publish-state <log>` command.
  It reports rather than publishes, because publishing the log alone during a
  withheld exit would record transitions control lacks (`owner` retracts for
  the same reason). It stays silent when Git is disabled, a probe fails, or the
  entry offset is no longer on a line boundary (the checkout was switched).
- Attended sessions: `coga ticket` now passes `commit_log=True`, so its start
  line publishes before the session, matching `coga chat` (= `launch
  bootstrap/orient`, already immediate). Reason: a dirty log for the whole
  attended session blocks fast-forwards and confuses clean-checkout checks;
  the cost is one extra state commit per authoring session, which
  `commit-journal/coalesce-coga-state-commits` can fold.
- The deferral list lives in coga/state-publication under "Every log line has a
  publisher" (canonical and packaged twin, byte-identical).

### Notes for later steps

- A concurrent Dream session was editing `coga/tasks/recurring/dream/ticket.md` in
  this primary checkout. It was preserved through the rebase (autostash, byte-compared)
  and is not part of this branch.
- Megalaunch still writes its line at spawn (`record_launch_on_spawn`, which cannot be
  combined with `commit_log`); teardown `sync_log` publishes it. Left as is.

## PR

```yaml
title: Name unpublished log lines when the exit sweep is skipped
author: claude
author_evidence: Implement session ran as Claude Code on claude-opus-5-5 (attended, coga launch ac646fb4).
head: 359aa7fbffcd272262097e0c7eb4bd9b7ba2ba40
base: 0b52bee2b63315d3afc8375a2df74a8b1197729b
depth: deep
rationale: Changes CLI end-of-command publication reporting for every command and when `coga ticket` publishes; no review has run yet.
implementation: >-
  cli.main records the log size at entry. When the sweep is skipped (withheld,
  exit 75, rewind, non-sweeping subcommand), it names the appended log lines
  control lacks, with the publish-state recovery. `coga ticket` publishes its
  launch line at spawn. coga/state-publication documents each log writer's
  publisher and the deliberate deferrals.
deviations: None from the ticket. The approach (report, not publish) was chosen with the human in session.
limitations: >-
  Reports only, never publishes. Lines appended by a child process in the same
  window are attributed to "this command". The warning is skipped if a checkout
  switch moves the entry offset off a line boundary.
files:
  docs/contexts/coga/state-publication/SKILL.md: Skipped-sweep warning, coga ticket start publication, the log-writer and deferral list.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Byte-identical packaged twin of the topic.
  src/coga/cli.py: Log offset at entry; _warn_unpublished_log_lines and _control_log_lines; _sweep_coga_state reports whether it ran.
  src/coga/commands/ticket.py: Publish the authoring launch line before the session (commit_log=True).
  src/coga/launch.py: spawn_agent_session docstring notes coga ticket sets commit_log.
  tests/test_cli.py: Boundary tests covering exit-75/withheld naming, lines already on control, a completed sweep, and disabled Git.
  tests/test_launch_script.py: End-to-end regression for the stranded task ticket.py exit 75 without a remote.
  tests/test_ticket.py: coga ticket publishes its launch line before the agent spawns.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: The implement step does not review; code/self-qa and later review steps follow.
checks:
  - command: python -m pytest
    status: passed
    head: 359aa7fbffcd272262097e0c7eb4bd9b7ba2ba40
    base: 0b52bee2b63315d3afc8375a2df74a8b1197729b
    detail: 4055 passed, 10 skipped, run on the rebased commit (the only other dirt was the unrelated Dream ticket and this projected ticket).
  - command: python -m pytest tests/test_launch_script.py -k names_its_unpublished; python -m pytest tests/test_ticket.py -k publishes_its_launch_line
    status: passed
    detail: Both new regression tests fail with the fix reverted (cli.py at HEAD; ticket.py stashed) and pass with it, checked before commit.
    head: 359aa7fbffcd272262097e0c7eb4bd9b7ba2ba40
    base: 0b52bee2b63315d3afc8375a2df74a8b1197729b
  - command: coga validate --json
    status: not-run
    detail: No validation, task-layout or workflow behavior changed.
```
