---
title: Correct state-publication internals for pending-publication and the deferred
  done marker
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
    skills:
    - code/peer-review
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

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. Findings from the Phase 2 knowledge scan (shards ks-10, ks-28) and Phase 3 contract audit (ca-02), held as a draft because open PR #1199 (Hold dirty knowledge on feature checkouts until merge) is already editing both target files and does not carry these fixes; handle after #1199's review.

Targets: docs/contexts/coga-dev/internals/state-publication/SKILL.md and docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md.

1. stale (ks-10): the 'Scratch files and sandboxed publication' section says 'There is deliberately no deferred-publication state.' But src/coga/git.py keeps one since 22a1a4985: _PENDING_FILE = .coga/pending-publication.json, written by publish(..., remember=True) (used by sync_task_state with a fresh prepared ticket) on retryable failure (state: pending) or refusal (state: rejected), reused by the supervisor retry and sweep (_pending_expectations). coga-dev/internals/git-regressions already documents it. Narrow the sentence to what v1/06 decided.
2. stale (ks-10, dup ca-02): the publish leaf's quoted signatures omit publish(..., remember: bool = False) and sync_task_state(..., prepared: PreparedTicket | None = None). Add both and one sentence that a prepared lifecycle publish records its expectation for retry/sweep reuse, linking git-regressions.
3. stale (ks-28): the Guided-authoring finalization cancellation paragraph (~line 164) says commands.mark.canceled emits the done sentinel before the child CLI's exit sweep. Current src/coga/cli.py (~616-620) wraps dispatch and the end-of-command sweep in repl_supervisor.deferred_done_marker(), so the sentinel is written after _sweep_coga_state and _warn_unpublished_log_lines; <sentinel>.pending-<pid> keeps the backstop from tearing the session down. Related in-progress ticket: v1/coga-bump-on-feature-branch-leaves-stale-index-loc (introduced deferred_done_marker). Update the paragraph and its regression-fixture framing.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: correct-state-publication-internals-for-pending-pu

## Handoff (implement)

Docs-only change on the branch, commit 9e5e64d92 (pushed):

1. `state-publication/SKILL.md`, "Scratch files and sandboxed publication": the
   claim "no deferred-publication state" now says there is no replay *queue*.
   It names `.coga/pending-publication.json` as the one retained record, which
   only pins a prepared lifecycle publish's expectation, and links
   `coga-dev/internals/git-regressions`.
2. `state-publication/publish/SKILL.md`: the quoted signatures now include
   `remember=False` for `publish` and `prepared=None` for `sync_task_state`. A new
   sentence says a *fresh* `PreparedTicket` becomes `expect` and publishes with
   `remember=True`, which is what feeds the teardown retry and the sweep. This
   follows `git.sync_task_state`, which remembers only when `prepared.fresh`.
3. `state-publication/SKILL.md`, the cancellation paragraph: `mark canceled`
   requests the sentinel, but `cli.main` wraps dispatch and the
   end-of-command boundary in `repl_supervisor.deferred_done_marker`. The
   sentinel is therefore written after `_sweep_coga_state` and
   `_warn_unpublished_log_lines`, and `<sentinel>.pending-<pid>` holds off the
   backstop. The fixture framing now says the interrupted variant models an
   external kill by releasing the held marker early, matching the comment in
   `tests/fixtures/authoring_cancellation.py`.

Decision: PR #1199, which edits the same two files, was still OPEN at
implement time. The ticket asked to wait for its *review*. I went ahead
because the owner activated this ticket and the hunks are small; whichever PR
merges second rebases.

Adjacent pre-existing failure, not fixed here: `README.md` (the "ticket is an
ordinary Markdown file" paragraph) links
`coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md`, which
61388855a deleted. That breaks
`tests/test_packaging.py::test_context_navigation_has_no_broken_links`, and the
two `test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
cases fail because they run that test in a subprocess. README is identical on
origin/main, so the failure is on main as well. No follow-up ticket exists yet.

## PR

```yaml
title: Correct state-publication internals for remembered expectations and the deferred done marker
author: claude (Claude Code, claude-opus-5-5), manual megalaunch session
head: 9e5e64d927ff8561149fa749b0d943e44733b492
base: 9f2a2a8897f408fb9571604e3a2155aa82227227
review_depth: light — docs-only, two coga-dev (local-only) topics; each claim checked against git.publish, git.sync_task_state, cli.main, repl_supervisor.deferred_done_marker and the cancellation fixture
files:
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: items 1 and 3 (pending-publication record; deferred done marker ordering and fixture framing)
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: item 2 (remember/prepared signatures and the retry/sweep reuse sentence)
checks:
  - command: .venv/bin/python -m pytest -q
    tree: uncommitted working tree identical to the committed head 9e5e64d92 (only these two files were changed; committed right after)
    result: 4763 passed, 33 skipped, 3 failed in 723.71s
    failures: test_packaging::test_context_navigation_has_no_broken_links and 2x test_git::test_final_package_edits_never_escape_a_mutating_cli_sweep — the pre-existing README dead link above, unrelated to this diff
review: not run yet; peer-review is the next workflow step
```
