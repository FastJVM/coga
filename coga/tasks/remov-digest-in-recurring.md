---
slug: remov-digest-in-recurring
title: Remove the daily digest
status: in_progress
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 3 (open-pr)
---

## Description

Remove the daily digest from Coga entirely: the `coga/recurring/digest/`
job, the `coga digest` command and its `runner.RECIPES` entry, the spool
producer/consumer machinery, the `digest/post` workflow and `coga/digest/flush`
skill, and the packaged twins that seed all of it into fresh repos.

Done / Canceled / recurring-error outcomes stop being spooled for a once-a-day
post and instead **post live to Slack as they happen**. That is the path
`notification.notify` already takes today when no digest ticket is installed,
so for outcomes the change is "make the fallback the only path".

**Owner decision:** the digest's other job — scanning `origin/main` and
posting an "Also merged (no ticket)" section for commits no Done ticket
claimed — is dropped with no replacement. Unattributed merges stop appearing
in Slack; `git log` / GitHub remain the record. This is intentional, not a
regression to rediscover.

Why: the digest is the one recurring job that owns a second write-contended
`merge=union` file (`spool.md`), a legacy-migration shim, a git high-water mark
in a ticket blackboard, and a Typer command whose home in core is already an
open question (see `CLAUDE.md`, microkernel rule). It has generated a
disproportionate share of autofix tickets (spool drain leaks, clobbered
serviced periods, log-sync commit filtering). Live posting is simpler and the
volume is low enough that a daily rollup isn't earning its machinery.

Done looks like: no reference to the digest *feature* remains in `src/`,
`coga/` (excluding `coga/log.md` and historical `coga/tasks/`), `docs/`, or
`tests/`. A `grep -ri digest` will still hit SHA-256 `hexdigest` / skill-tree
`*_digest` checksums and the unrelated `marketing/digest-sweep` fixture slug
in `tests/test_{tasks,views,status,validate}.py` — leave those alone. The
test suite is green; `coga validate --json` is clean; `coga mark done` on a
ticket posts a live Slack message.

## Context

**What to delete (live + packaged twin — `tests/test_packaging.py` enforces
byte-identity, so delete both sides of every pair):**

- `coga/recurring/digest/` (`ticket.md`, `ticket.py`, `spool.md`) and
  `src/coga/resources/templates/coga/recurring/digest/`.
- `coga/workflows/digest/post.md` and the bundled
  `bootstrap/workflows/digest/post.md`.
- `coga/skills/coga/digest/flush/SKILL.md` and the bundled
  `bootstrap/skills/coga/digest/flush/SKILL.md`. `coga/.agent-skills/coga/digest`
  is a generated install of that skill — remove it too, but it's not a twin.
- `coga/tasks/recurring/digest/` — the materialized current-period task
  (`status: done`). It's a normal task, so `coga delete` is the right
  removal, not `rm -rf`. Note this is a task-state mutation and lands on the
  control branch from the primary checkout, **outside** the feature branch /
  PR (see `stop-syncing-task-state-onto-the-feature-branch`).
- `src/coga/commands/digest.py`, `tests/test_digest.py`.
- `src/coga/spool.py` — its only consumers are `commands/digest.py` and
  `notification/__init__.py`; once `notify` no longer spools, it has none.
  `tests/test_notification_messages.py` and `tests/test_recurring.py` import
  it for fixtures and will need reworking. Other tests that seed a spool or
  assert the digest exists: `tests/test_mark.py:1096–1107`,
  `tests/test_launch.py:5778–5790` (strict-outcome publication),
  `tests/test_runner.py:16,64,119` (`digest` in `RECIPES`),
  `tests/test_recurring_shims.py:36` (parametrized over `digest`),
  `tests/test_period_state.py:164`, and a comment at `tests/conftest.py:369`.

**Core wiring to unwind:**

- `src/coga/cli.py:91` `app.command("digest")`, and `"digest"` in the
  sweeping-commands frozenset near `cli.py:128`.
- `src/coga/runner.py:29` `"digest": run_digest_recipe` in `RECIPES`.
- `src/coga/aliases.py:28` `"digest"` in the reserved built-in names set.
- `src/coga/notification/__init__.py`: the whole `# --- digest (outcome) path`
  block — `digest_spool_path`, `digest_spool_target_path`,
  `digest_state_path`, `_migrate_legacy_digest_spool`, `render_digest`,
  `DIGEST_RECURRING_NAME`, `DIGEST_EVENT_KINDS`, `_DIGEST_SPOOL_SEED` — and
  the `__all__` exports. `notify` itself should survive as the outcome-post
  entry point (callers: `mark.py` ×3, `recurring_runner.py` ×2) but collapse
  to the live `post` branch. Keep the `DIGEST_EVENT_KINDS` gate if it's still
  wanted as "only outcomes go through notify"; rename it if kept.
- Callers importing the spool helpers: `autoclose.py:47`, `mark.py:33` (and
  `_prepare_outcome_spool` at `mark.py:114–135`, plus the strict-outcome
  snapshot logic at `:234`, `:426`), `commands/bump.py:20,211–224`,
  `commands/mark.py:36,448,505`, `recurring_runner.py:84,2366`. The
  `digest_detail=` keyword threads through `src/coga/bump.py:173` (not
  `commands/bump.py`), `mark.py`, `autoclose.py:433`,
  `recurring_runner.py:2874,4462` — it becomes the live-post detail line, so
  rename rather than drop.
- Git sync: `git.py` treats `spool.md` as an explicitly owned
  `merge=union` sibling alongside `log.md` (see comments at `git.py:763`,
  `:1523–1592`) — every `spool` mention in `git.py` is a docstring or
  comment; `_union_merge_paths` (`git.py:~3430`) reads `git check-attr`, so
  no code change there. `coga/.gitattributes:2` `**/spool.md merge=union`
  and its packaged twin `src/coga/resources/templates/coga/.gitattributes`
  can both go once no spool exists. Read `coga/contexts/coga/sync/SKILL.md`
  before touching this — it documents the union-landing contract.

**Docs and contexts that describe the digest and must be updated (live +
packaged twin where both exist):** `coga/contexts/coga/{architecture,
codebase, extension-model, important, launch-internals, patterns, recurring,
sync, usage}/SKILL.md`, bundled `bootstrap/contexts/coga/cli/SKILL.md`,
`docs/{README,reference,operations,vision,cli-extension-audit,
cli-extension-external-surface}.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`
(the microkernel paragraph names `coga digest` as an open placement question —
that sentence is now moot), and the comment block in `coga/coga.toml` +
`src/coga/resources/templates/coga/coga.toml` (~line 44 / 55). Also
`coga/recurring/{autoclose-merged,skill-update}/ticket.md` and
`coga/skills/coga/autoclose/sweep/SKILL.md` mention the digest as where their
outcomes land.

**Boundary note:** the base prompt says agents don't edit `coga.toml`. The
only digest reference there is a *comment*; the owner authorizes editing that
comment as part of this ticket. No `[aliases]` or `[recurring]` entry needs
removing.

**Do not touch:** `coga/log.md` (append-only audit trail), any historical
ticket under `coga/tasks/` (autofix run-logs, done tickets, `v2/` drafts),
and the false-positive `digest` hits — `hashlib...hexdigest()` in
`authoring.py`, `blocker_reminders.py`, `git.py:205`, `skill_manager.py`; and
`source_digest` / `*_tree_digest` / `installed_digest` throughout
`skill_manager.py`. Those are checksums, not the feature.

**Related tickets (context, not scope):** `digest-can-clobber-recurring-last-serviced-period`,
`autofix/stop-the-digest-spool-drain-leaking-a-blank-line-e`,
`autofix/filter-coga-s-own-log-sync-commits-out-of-the-dige`,
`v2/cleanup-core-commands/` (parked design that was going to decide `coga
digest`'s CLI spelling — this ticket moots that half of it; leave a note in
its README rather than editing the drafts).

**Ordering hint (from review):** go producer-first, consumer-second.
Collapse `notify` to live post, delete `spool.py`, the strict-outcome arming
sites, the `.gitattributes` rules, and `patterns/SKILL.md`'s spool section
first — `run_digest` already short-circuits on "no spool installed"
(`commands/digest.py:119–124`) — then delete the dead consumer, job, workflow,
skill, materialized task, and docs. Consumer-first would leave a spool being
written that nothing drains mid-branch. Note `autoclose.py:539–542` gates its
live Done post on `digest_spool_path(cfg) is None`, so this PR changes how its
own merge is announced; expect a live post on close.

**Out of scope:** changing what `post` does or which channel outcomes go to;
touching `dream`, `autoclose-merged`, `blocker-reminders`, `branch-sweep`, or
`skill-update` beyond fixing their prose references; any replacement rollup
for outcomes or merged commits.

<!-- coga:blackboard -->

## Dev

branch: remove-digest
worktree: /home/n/Code/claude/coga-remove-digest

## Decisions

- Owner approved dropping `digest_detail=` and `notify(detail=)` rather than
  renaming them: each duplicated `slack_text`, and the live path never read
  the extra detail. `notify(ticket=)` is also gone; the rendered message
  already carries the task identity.
- `notify` remains the outcome entry point, gated by `OUTCOME_EVENT_KINDS`:
  Done / Canceled go to flow, recurring errors go to important. Message
  formatting, destinations, and delivery-failure policy are unchanged.
- The unattributed-merge scan has no replacement. `coga/sync` now states the
  policy directly: commits without a Done ticket are absent from Slack;
  `git log` and GitHub are the record.
- `mark_done` retains the former live-path sync behavior. Cancellation must
  union-land its audit log immediately, including recorded assists, because
  an abandoned feature branch may never merge.

## Implementation

Three committed changes on the feature branch, based on `7127b7a5`:

1. `922abfaa` — remove the producer/consumer machinery, command, registered
   recipe, recurring job, workflow, skill, packaged twins, and spool union
   attributes; route every outcome through the existing live post path.
2. `6f05c5a1` — update contexts, docs, configuration comments, templates,
   fixtures, and the parked command-cleanup README.
3. `dfe67e66` — peer-review fix for strict cancellation audit publication,
   its CLI regression test, and removal of the remaining historical feature
   descriptions from active docs/contexts (including packaged twins).

Control-branch cleanup was completed during implement: `coga delete
recurring/digest` landed as `0445c9af`; the generated
`coga/.agent-skills/coga/digest` installation was removed. These state/local
changes are outside the feature PR.

## Peer review

`codex review --base main` **returned**, exit 0, on 2026-09-10. It found one
P2 must-fix: strict recorded-assist cancellation no longer union-landed its
required reason in `coga/log.md` onto control after spool removal. The canceled
ticket was published, but the audit remained stranded on the feature branch.

Fixed in `dfe67e66` by preserving `land_union_files_to_control=True` for the
strict cancellation transaction. The new
`tests/test_launch.py::test_recorded_assist_cancellation_lands_reason_on_control`
failed on the missing remote audit reason before the fix and passed afterward.
It verifies canceled status on both remote refs, preservation of a concurrent
log append, one live notification, no product-code leakage onto control, and
a clean worktree. Updated the live and packaged sync contract. No unresolved
review findings or design decisions remain.

`git fetch origin main && git rebase FETCH_HEAD` completed cleanly in the
feature worktree, onto `7127b7a5`, before the fix and final test run.

## Verification

The feature worktree was tested using
`source /tmp/coga-remove-digest-review-venv/bin/activate`. This isolated
environment includes pip, Hatchling, and the feature package installed editable;
the previously excluded wheel-build test now runs.

- `python -m pytest` — **2345 passed**, no skips or deselections, in 183.57s.
  One warning: the sandbox could not write pytest's optional cache. Includes
  wheel contents/twin parity and CLI live Slack-dispatch tests (mocked webhook).
  Full output: `/tmp/coga-remove-digest-pytest.log`.
- `coga validate --json` — exit 1 solely for the same four pre-existing
  `unsynthesized-draft-blackboard` errors as primary `main`: the parked
  `v2/autotrigger-ticket-type`,
  `v2/measure-relay-prompt-scope-and-agent-precision`,
  `v2/split-context-to-doc-user-accessible-and-editable`, and
  `v2/use-worktree-when-starting-a-dev-task` tickets. Error kind, task, and
  message tuples match exactly. Historical tickets remain untouched.
- `coga --help` — passes; the removed command is absent.
- `git diff --check` — clean.
- Reference audit across `src/ coga/ docs/ tests/ README.md AGENTS.md CLAUDE.md`
  (excluding `coga/log.md` and historical `coga/tasks/`) finds only checksum
  terminology, unrelated fixture slugs, third-party news examples, and the
  `ProcessPoolExecutor` substring. Active documentation no longer recounts
  the removed feature. Audit: `/tmp/coga-remove-digest-reference-audit.txt`.

## Adjacent state

The primary checkout retains pre-existing dirty launch-claim edits on four
other tickets (`add-an-agent-picker-for-recurring`, `agent-usage-report`,
`detect-stranded-ticket-writes-across-checkouts`, and
`document-the-ticket-blackboard-writer-s-contract`), plus runtime log/template
state. They were not edited or staged by this review. Catch-all sweeps can
report the previously noted `sync refused` messages for those tickets.

## PR

Remove the daily digest and post Done, Canceled, and recurring-error outcomes
live through the existing Slack routing. Delete the command and registered
recipe, queue machinery, recurring job, workflow, skill, and packaged copies;
update the contexts, docs, and fixtures. Commits merged without a Done ticket
are intentionally no longer announced; git and GitHub remain their record.

Preserve cancellation audit publication on the control branch, including
recorded-assist cancellations, so the required reason survives an abandoned PR.

Test plan: `python -m pytest` (2345 passed, including wheel packaging and live
notification dispatch); `coga validate --json` (only the four pre-existing
parked-draft errors, identical to main); `coga --help`; `git diff --check`.
