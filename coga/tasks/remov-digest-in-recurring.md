---
slug: remov-digest-in-recurring
title: Remove the daily digest
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
