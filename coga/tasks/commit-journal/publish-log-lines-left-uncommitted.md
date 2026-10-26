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
step: 3 (open-pr)
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
  `git.publish` of task+template+log), launch launch lines
  and `launch_script` "launched as a script" (`sync_log`), recurring delegated
  launch line (`sync_log`), usage record (teardown `sync_log`), the `coga ticket`
  start line (immediate `sync_log`), autofix and retire creates (`sync_task_state`), recurring
  serviced/reused ledger lines (recurring publication or sweep), `launch_script`
  "script exited with code N" (checkout settlement or sweep).
- Failure records (the failure report covers them): `git.record_sync_failure`,
  "sync refused", "refresh failed", `recurring_runner._append_sync_failure`,
  phone-home "sync failed", Slack "post failed".
- (b) Deliberate retention: exit 75, `state_sweep_withheld`, `bump --to/--backward`.
  Before this change the only report was the generic "state sweep withheld" note.
  Init commits its onboarding line locally and leaves the first push to the
  human, now explicitly listed in the publication topic.
- (c) Formerly stranded, reproduced: a task `ticket.py` exiting 75 in a repo with Git enabled
  but no remote. The checkout boundary is exempt, so it never armed and nothing
  settled between phases. Launch exits 75 and the CLI skips the sweep, which left
  "script exited with code 75" dirty with no report. Review also reproduced
  an ignored creation log after a successful sweep and a script exit line
  below the saved offset after switching to an older branch; both are fixed.

### Decisions (approved by the human in session)

- Fix at the CLI boundary, not per site. `cli.main` records the log's identity,
  timestamps, and bounded tail at entry. After every exit,
  `_warn_unpublished_log_lines` names retained lines control lacks
  (remote-tracking ref, else local control), prints at most 10, and gives the
  `coga run publish-state <log>` command.
  It reports rather than publishes, because publishing the log alone during a
  withheld exit would record transitions control lacks (`owner` retracts for
  the same reason). It stays silent when Git is disabled, a probe fails, or the
  log is unchanged. An ordinary append uses the tail; a rewrite falls back
  to the whole changed log, which may also name older retained lines.
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

## Peer review

Direct Codex review **completed** on final head
`ffdfb5e4efff4e3056da71676884064f7e769ebf`, base
`92d7e60ac0906cdb904bc56e15d1daea3d871121` (2026-10-26).
The original implementation was Claude's; Codex independently reviewed it,
then implemented the two fixes below with the attending human's explicit
approval. The final review includes self-review of those Codex fixes; it is
not an independent review of the entire final diff.

Both must-fix findings are resolved:

- A successful `coga create` with an ignored, untracked log silently excluded
  its creation line from both publication and the new warning. The warning
  now runs after every exit, including after a sweep.
- A task script switching to an older branch and exiting 75 left an
  unpublished exit line below the saved byte offset. The check now records
  file identity, timestamps, and a bounded tail; rewrites trigger a whole-log
  comparison. Its wording does not attribute older retained lines to the
  current command. Unchanged logs remain silent.

The new regression tests both failed against the pre-fix code and pass with
these fixes. The focused command
`PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest tests/test_cli.py tests/test_launch_script.py tests/test_ticket.py`
passed **143 tests** before the final rebase (fix tree committed as
`397694b1e01fff3b9c1e47ad92809b4646c14b82`, base `020e0d1577137c1f1f1f08797a1d725f49d7056a`).
A real PTY at 80x24 and 120x40 showed the retained creation line and recovery
command in readable yellow stderr; exit remained 0 and earlier ignored lines
were not attributed to either new command. No raw-terminal interaction changed.

Fetched main and rebased through the handoff checkpoint, preserving and
byte-comparing the projected ticket each time. This includes PR #1097's
Windows skill-link fix and CI configuration plus subsequent knowledge PRs. The final source review covers every diff path,
all `append_log` callers under `src/`, sweep skips, the explicit publishers,
and both state-publication twins. Init's human-owned first push is now an
explicit documented deferral. No remaining finding in this branch's changes.

The full command
`PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest`
completed on head `10460e26ad3dcd3a398d8dd299432ae9d6c36c51`, base
`33cb4c613012491b2fed36d9ee1e6f6c45778c52`, with **4058 passed, 10 skipped,
1 failed** (Python 3.12.12, Linux). The sole failure is
`test_live_and_packaged_copies_stay_identical`: the live
`coga/recurring/blocker-reminders/ticket.md` differs from its packaged twin.
Both files match main byte-for-byte; the live-only change entered main in
`e2d1c33620489db0aefcd2e1de276956322d2f0b` and belongs to the separate
`recurring-unblock-launch` work. Retrying that exact packaging test after the
human said "retry" produced the same failure (1 failed in 0.77s).

The final rebase adds only an unrelated completed-ticket deletion and a local
log-grammar topic note. `git diff 10460e26ad3dcd3a398d8dd299432ae9d6c36c51..HEAD -- src tests pyproject.toml`
is empty: the code, tests, packaged files, and build configuration match the
full-suite revision exactly. That full-suite receipt remains historical,
not restamped. The final focused command
`PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest tests/test_cli.py tests/test_launch.py tests/test_launch_script.py tests/test_publish_state.py tests/test_ticket.py`
passed **403 tests in 46.95s** on final head `ffdfb5e4efff4e3056da71676884064f7e769ebf`,
base `92d7e60ac0906cdb904bc56e15d1daea3d871121`.

The full suite exposed two test-harness assumptions, also corrected: the
shared non-Git fixture now stubs the new Git-reading diagnostic, and recovery
counts top-level sync diagnostics rather than echoed retained audit lines.
The recovery test still proves two failed publication attempts, one lifecycle
transition, and idempotent recovery. The tests themselves remain active in
real-Git fixtures.

The human explicitly selected **"Record failure and hand off"**, authorizing
the known unrelated full-suite failure with a `deep` recommendation. No
unrelated template was changed or test excluded. This approval remains the
handoff decision after the retry reproduced the same failure. Final head `ffdfb5e4efff4e3056da71676884064f7e769ebf` is committed and pushed
with `--force-with-lease`; it has three commits ahead of main. All review work
and PR preparation are complete. This projected ticket stays unstaged for the
single bump to publish and hand off to `open-pr`.

## PR

```yaml
title: Report unpublished log lines at command exit
author: claude/codex
author_evidence: >-
  Claude Code on claude-opus-5-5 implemented the original change (attended
  launch ac646fb4). Codex reviewed it and implemented the two human-approved
  review fixes in launch 0d0236f0-ef0f-4a25-b8ad-2715f074eac1.
head: ffdfb5e4efff4e3056da71676884064f7e769ebf
base: 92d7e60ac0906cdb904bc56e15d1daea3d871121
depth: deep
rationale: >-
  Shared CLI exit diagnostics and authoring publication timing change. Review
  fixes received self-review. The full suite has one unrelated packaging
  mismatch inherited from main; the human explicitly approved handing off
  with that failed receipt recorded.
implementation: >-
  CLI entry records log identity, timestamps, and a bounded tail. Every exit
  checks changed log lines against control, including after a sweep; a
  checkout rewrite triggers a whole-log comparison. Warnings name retained
  lines and the publish-state recovery without publishing withheld state.
  coga ticket publishes its launch line before spawning the authoring agent.
  The publication topic inventories the publishers and deliberate deferrals.
deviations: >-
  The human approved handing off despite the one pre-existing packaging
  failure instead of requiring an entirely green suite for this step. The
  reporting policy, immediate authoring-start publication, and both review
  fixes were also explicitly approved.
limitations: >-
  Read-only diagnostics do not fetch control or retry publication; failed
  probes remain nonfatal. A rewritten log can cause older retained lines to
  be named too. Warnings show ten lines plus an omitted count. Verification
  ran on Linux/Python 3.12.12; no local Windows or Python 3.11 run. The known
  blocker-reminders template mismatch is outside this branch's diff.
files:
  docs/contexts/coga/state-publication/SKILL.md: Exit diagnostics, authoring start publication, publishers, and deliberate deferrals including init's first push.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Byte-identical packaged twin of the publication topic.
  src/coga/cli.py: Snapshot changed logs and report lines control lacks after every exit, including ignored logs and checkout rewrites.
  src/coga/commands/ticket.py: Publish the authoring launch line before the session with commit_log=True.
  src/coga/launch.py: Document the authoring caller's immediate log publication.
  tests/test_cli.py: Cover withheld/exit-75 warnings, ignored logs after successful sweeps, published lines, unchanged logs, and disabled Git.
  tests/test_launch_script.py: Real CLI regression for exit 75 without a remote, including switching to a branch with a shorter log.
  tests/test_ticket.py: Prove the authoring launch line is published before the agent spawns.
  tests/conftest.py: Keep Git access stubbed in non-Git tests, including the new exit diagnostic; real-Git fixtures exercise it.
  tests/test_publish_state.py: Count actual sync failure reports separately from echoed audit lines and verify the retained transition is named.
review:
  reviewer: codex
  kind: self
  status: passed
  head: ffdfb5e4efff4e3056da71676884064f7e769ebf
  base: 92d7e60ac0906cdb904bc56e15d1daea3d871121
  detail: >-
    Direct review completed on the final rebased diff. Codex independently
    reviewed Claude's original implementation, found two gaps, and fixed them
    with human approval. Final review includes self-review of those fixes;
    no remaining finding in the changed code or contracts.
checks:
  - command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest
    status: failed
    head: 10460e26ad3dcd3a398d8dd299432ae9d6c36c51
    base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
    detail: >-
      4058 passed, 10 skipped, 1 failed in 359.28s. The sole failure is the
      pre-existing blocker-reminders live/packaged mismatch, unchanged by
      this branch. The human approved handoff with this failure recorded.
      Historical receipt before the final documentation-only rebase.
  - command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest tests/test_cli.py tests/test_launch.py tests/test_launch_script.py tests/test_publish_state.py tests/test_ticket.py
    status: passed
    head: ffdfb5e4efff4e3056da71676884064f7e769ebf
    base: 92d7e60ac0906cdb904bc56e15d1daea3d871121
    detail: 403 passed in 46.95s on the final rebased head.
  - command: git diff 10460e26ad3dcd3a398d8dd299432ae9d6c36c51..HEAD -- src tests pyproject.toml
    status: passed
    head: ffdfb5e4efff4e3056da71676884064f7e769ebf
    base: 92d7e60ac0906cdb904bc56e15d1daea3d871121
    detail: Empty; final code, tests, packaged files, and build configuration exactly match the full-suite revision.
  - command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest tests/test_packaging.py::test_live_and_packaged_copies_stay_identical -q
    status: failed
    head: 10460e26ad3dcd3a398d8dd299432ae9d6c36c51
    base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
    detail: User-requested retry reproduced the same unrelated mismatch; 1 failed in 0.77s.
  - command: coga validate --json
    status: not-run
    detail: No config, workflow, validation, or task-model behavior changed.
```
