---
slug: fail-loud-on-unrecognized-config-sections-instead
title: Fail loud on unrecognized config sections instead of silently treating webhook
  as absent
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
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
  - name: review
    skills: []
    assignee: owner
---

## Description

Relay's config loader (`load_config` in `src/relay/config.py`) reads a fixed
set of known top-level sections by name with `.get(...)`. A misspelled or
stray section — `[notifcation]`, `[Slack]`, `[notification.slak]` — is
silently ignored: `.get()` returns `None` and the loader treats that config as
absent. The most visible symptom is Slack notifications silently going dark
because the webhook section never matched the expected name (hence the title).

This contradicts Relay's fail-loud / legible contract. The loader already
rejects unknown keys inside *some* tables (`[ticket.fields.*]`, local
`[agents.*]` overrides) but the enforcement is half-applied — top-level section
names are never checked, and several known tables silently ignore unknown
sub-keys. Generalize the existing behavior: make `load_config` raise
`ConfigError` for **any unrecognized key, at any level of a fixed-schema
table**, in **either** `relay.toml` or `relay.local.toml`, naming the offending
key and listing the valid ones. Free-form maps (see below) stay open.

## Context

Decisions already made (don't relitigate):

- **Hard error at load time.** Raise `ConfigError` from `load_config` — not a
  warning, and not validate-only. Matches how unknown keys in `[ticket.fields]`
  / local `[agents.*]` already fail.
- **Both files enforced.** Shared `relay.toml` *and* `relay.local.toml`.
- **Full recursive enforcement, not just top-level sections.** Every table with
  a *fixed* set of expected keys must reject unknowns. This is the deliberate
  wider scope — a top-level allowlist alone would miss `[notification.slak]`,
  the likeliest real cause of the webhook silently going dark (the title
  symptom). Validating one level into `[notification]` is the whole point.
- **Retire `extra_local`.** The `extra_local` field on `Config`
  (`config.py:132`, populated at `:275`) is written but **never read** —
  confirmed no `cfg.extra_local` access in `src/` or `tests/`. Once unknown
  local sections are rejected it can only ever be `{}`. Remove the field and
  its population.

### What to validate — fixed-schema tables (reject unknown keys)

Verify each against the loader before finalizing; this is the loader's current
consumption, not a guess:

- Top-level **shared** sections: `version`, `default_status`, `agents`,
  `notification`, `slack`, `git`, `launch`, `ticket`, `aliases`. Plus
  `assignees` as a **known-but-rejected** key — it has a dedicated deprecation
  error (`config.py:234`), so it is *not* simply "unknown". Don't copy this
  list verbatim into an `allowed` set and run the generic check first, or
  `assignees` loses its tailored message; see the special-case note below.
- Top-level **local** keys: `user`, `secrets`, `agents`, `notification`,
  `slack`, `git`. (Note `version`/`default_status`/`launch` are only read from
  *shared* — they're silently ignored in local today, which is itself the
  footgun. Rejecting them in local is the consistent choice.)
- `[agents.<name>]` (shared): `cli`, `auto`, `file`, `mode`, `name_flag`,
  `discussion`. **Currently does NOT reject other unknown keys** (`_parse_agents`
  only checks required-present + local-only-absent) — so `[agents.claude].clii`
  is silently dropped today. Add the rejection here too.
- `[notification]`: `channels`, `slack`.
- `[notification.slack]` and legacy `[slack]`: `webhook`, `enabled`, `gifs`,
  `users`.
- `[git]`: `enabled`, `remote`, `control_branch`.
- `[launch]`: `idle_timeout`, `max_session`.
- `[ticket]`: `fields`.
- `[ticket.fields.<name>]`: `description`, `values`, `default`, `required` —
  **already enforced** (`_ALLOWED_TICKET_FIELD_KEYS`); leave as-is or fold into
  the shared helper.
- local `[agents.<name>]` partial override: `skip_permissions`,
  `skip_permissions_argv` — **already enforced** (`_parse_local_skip_policy`);
  same.

### What stays open — free-form maps (do NOT reject keys)

These map arbitrary user-chosen names to values; their *keys* are data:

- `[aliases]` (name → command)
- `[secrets]` (key → reference)
- `[notification.slack.gifs]` / legacy `[slack.gifs]` (event-kind → URL list)
- `[notification.slack.users]` / legacy `[slack.users]` (name → member ID)

### Implementation notes

- Add a small shared helper, e.g. `_reject_unknown_keys(table, allowed,
  label)`, and call it from each parsing helper so error wording is uniform.
  Match the existing `ConfigError` style (see `_parse_agents` `unknown_local`
  and the `[ticket.fields]` unsupported-keys errors): name the unknown key,
  list the valid ones. Note `version`/`default_status` are scalar keys, not
  tables — word the message so it reads sensibly for those too.
- **Known-but-rejected keys — run their dedicated errors BEFORE the generic
  unknown-key check**, or their tailored migration guidance is lost. There are
  two such cases, both already in the loader:
  - `[assignees]` at top level (`config.py:234`) — "no longer supported, remove
    it" message.
  - `skip_permissions` / `skip_permissions_argv` inside a **shared**
    `[agents.<name>]` table (`config.py:326-332`) — "this is machine-local
    policy, move it to relay.local.toml" message. The generic agent-key
    allowlist (`cli`/`auto`/`file`/`mode`/`name_flag`/`discussion`) must not
    swallow these with a generic error.
  Treat both as a specially-handled reject set checked ahead of the generic
  pass (or keep the existing dedicated raises and run the generic check only on
  what survives them).
- `[slack]` is deprecated but **still supported** — keep it valid.
- **Blast radius is wide** — a too-tight allowlist hard-fails *every* relay
  command on startup. Grep `example/relay-os/`, all seeded fixtures, any
  `relay.toml`/`relay.local.toml` template under `src/relay/resources/`, and
  nick's own `relay.local.toml`, and make them clean before merging. Update
  `tests/test_config.py` with both accept (every known key) and reject (a typo
  at each level) cases. Run `python -m pytest` and `relay validate --json`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (nick + claude, 2026-06-19)

Filled the ticket from a bare scaffold. Decisions locked in the interview:

- Unknown top-level config section → **hard `ConfigError` at load time** (not
  warn, not validate-only).
- Enforce **both** `relay.toml` and `relay.local.toml`.
- `extra_local` field is dead (written, never read) → retire it as part of the
  change.

Workflow: `code/with-review`. Assignee: `claude`. No contexts attached (change
is self-contained in `src/relay/config.py`; specifics live in the ticket body).

### RESOLVED: scope widened to full recursive enforcement

Evaluator flagged that a top-level-only allowlist would miss `[notification.slak]`
— the likeliest real cause of the webhook silently going dark (the title
symptom). Nick chose **"widen to all known tables"**: reject unknown keys at
*every* level of fixed-schema tables, in both files. Free-form maps (aliases,
secrets, gifs, users) stay open. Ticket body now enumerates the per-table
known-key sets and the free-form exceptions. This generalizes the enforcement
that `[ticket.fields.*]` and local `[agents.*]` already have. Note: `_parse_agents`
currently does NOT reject unknown shared agent keys either — same footgun, now
in scope.

Second evaluator flag (already noted in ticket): rejecting `version` /
`default_status` / `[launch]` in `relay.local.toml` is a genuine behavior
change, not just the named footgun — those are silently ignored there today.
Implementer must grep `example/` + seeded fixtures + nick's own
`relay.local.toml` so nothing real hard-fails on the next command.

### Second eval pass (widened ticket) — two fixes applied

A fresh cold-read eval verified 8/10 per-table key lists exactly against the
loader, the free-form/fixed split, and all three behavioral claims. It found
two real gaps, both "known-but-special-cased-rejected" keys whose dedicated
error must fire BEFORE a generic unknown-key check:

1. Shared top-level list could be misread as the literal `allowed` set, dropping
   `assignees`' tailored deprecation message (`config.py:234`).
2. The ticket forgot the shared-agent `skip_permissions` /
   `skip_permissions_argv` special-case (`config.py:326-332`) — same class as
   `assignees`, needs its "move to relay.local.toml" message preserved.

Both fixed in the ticket body (shared-section bullet now flags `assignees` as
known-but-rejected; the special-case note now covers both cases explicitly).
Eval otherwise: launch-ready, one coherent ticket, scope correct.

## Evaluator review

I have everything I need to ground the critique. The grep confirms `extra_local` is only written (lines 132, 275, 291), never read anywhere in `src/` or `tests/` (the `example/.../.venv/` hits are a vendored copy of this same file, not a consumer).

---

## Evaluation: `fail-loud-on-unrecognized-config-sections-instead`

**Description clarity — strong.** An agent with no prior context could start. The problem (`.get()` silently swallows misspelled sections → Slack goes dark), the contract violation (fail-loud), and the fix (section-name allowlist raising `ConfigError`) are all stated concretely with realistic examples. The "Decisions already made" block correctly pre-empts the obvious relitigations (warn vs. error, validate-only, local leniency).

**Workflow `code/with-review` — fits.** This is a small, surgical loader change with real footgun-reversal risk (a too-tight allowlist breaks every command on startup for legit repos). Code + review is the right shape; nothing here suggests it needs more (e.g. a discussion/design step) or less.

**Implementation-notes accuracy — verified against the loader:**

(a) **Shared allowlist.** The ticket lists `version, default_status, agents, notification, slack, git, launch, ticket, aliases`. The actual `shared.get(...)` set in `load_config` (lines 228–263) plus the dedicated `if "assignees" in shared` check (234) is exactly: `version, default_status, agents, notification, slack, git, launch, ticket, aliases` — and `assignees` handled separately. **The shared allowlist is correct and complete.** Note the nested helpers also read `gifs`/`users` (lines 815, 847) but those are *sub-keys* of slack tables, not top-level sections — correctly excluded.

(b) **Local keys.** Ticket says `user, secrets` plus override tables `agents, notification, slack, git`. Loader reads from `local`: `agents` (233), `notification` (242, 254), `slack` (244, 256), `git` (260), `user` (266), `secrets` (273). **Correct and complete.** Worth noting: `notification` and `slack` are passed to the channel/slack resolvers *but those resolvers only consume the `slack` sub-table and `channels`/`webhook`/`enabled` keys* — still, the top-level local section name read is `notification`/`slack`, so the allowlist entry is right.

(c) **`[assignees]` dedicated error.** Confirmed at lines 234–239. Ticket's instruction to run it before the generic check (or fold into a special set) is sound — its migration message is materially friendlier.

(d) **`extra_local` never read.** Confirmed: only written (132/275/291), zero `cfg.extra_local` / `.extra_local` reads in `src/` or `tests/`. The `example/.../.venv/` hits are a vendored install of this exact file, not a real consumer. The "retire it" decision is safe and correct.

**Allowlist flag:** No section is missed or wrongly included in either list. One subtlety the implementer should not trip on: `version`/`default_status`/`launch` are *bare top-level keys* (scalars/tables), not all `[table]` sections — a section-name allowlist that iterates `shared.keys()` naturally covers them, but the error message wording ("unknown section") is slightly off for scalar keys like `version`. Minor; worth a phrasing choice, not a blocker.

**Scope — reasonable, single ticket.** Three tightly coupled changes: add the allowlist check, reject in both files, retire the now-dead `extra_local`. The `extra_local` removal is a direct consequence of the allowlist (the field can only ever be `{}` afterward), so bundling it is correct, not scope-creep. No multi-ticket bloat.

**Assumptions / edge cases to question before launch:**

1. **Local-only rejection of `version`/`default_status`/`launch` is a real behavior change, not just the named footgun.** Today a repo could harmlessly carry `[launch]` or `version` in `relay.local.toml` and it's silently ignored. The ticket flags this honestly ("edge case to decide") and lands on fail-loud — defensible — but if any real `relay.local.toml` in the wild has stray copies of these, they'll now hard-fail on *every* command. The implementer must grep `example/` and any seeded fixtures (the ticket already says to) and should also sanity-check the user's own `relay.local.toml` isn't carrying one.

2. **`channels` and other notification sub-keys.** The allowlist operates on top-level section names only — it won't catch a misspelled *sub-key* like `[notification].chanels` or `[notification.slak]`. That's out of scope (the ticket scopes to top-level sections), but worth stating explicitly so reviewers don't expect the nested case to be fixed here. The original Slack-goes-dark symptom in the title could actually stem from a nested misspelling (`[notification.slak]`), which this change would *not* catch — only a top-level `[Slack]`/`[notifcation]` would. Mild title/scope tension worth a sentence in the PR.

3. **Packaged-template sync.** Per CLAUDE.md, loader changes don't touch `relay-os/` contexts, but the implementer should confirm no shipped `relay.toml`/`relay.local.toml` template under `src/relay/resources/` trips the new check.

**Bottom line:** Ticket is launch-ready. Description and decisions are clear, the allowlist contents are accurate and complete against the loader, the `extra_local` retirement is verified-safe, and scope is one coherent unit. The only things to surface to the reviewer are (1) the genuine behavior change for local `version`/`default_status`/`launch`, and (2) that top-level-only matching won't catch the nested-section misspelling the title alludes to.

## Dev

branch: config-fail-loud-unknown-sections
worktree: /home/n/Code/relay-config-fail-loud
pr: https://github.com/FastJVM/relay/pull/418

### Implementation plan (claude, 2026-06-19)

Single helper `_reject_unknown_keys(table, allowed, label)` raising ConfigError
naming the unknown key(s) + listing allowed. Called per fixed-schema table:

- Top-level **shared** (in load_config, AFTER the dedicated `assignees` raise so
  its tailored message wins): allowed = version, default_status, agents,
  notification, slack, git, launch, ticket, aliases.
- Top-level **local** (in load_config): allowed = user, secrets, agents,
  notification, slack, git.
- `[agents.<name>]` shared (in `_parse_agents`, AFTER the dedicated
  skip_permissions/_argv raise so that message wins): allowed = cli, auto, file,
  mode, name_flag, discussion.
- `[notification]` shared+local: allowed = channels, slack.
- `[notification.slack]` + legacy `[slack]`, shared+local: webhook, enabled,
  gifs, users.
- `[git]` shared+local: enabled, remote, control_branch.
- `[launch]` shared (in `_parse_launch`): idle_timeout, max_session.
- `[ticket]` shared (in `_parse_ticket_fields`): fields.

Helper is a no-op on non-dicts so existing "must be a table" type errors still
fire from their dedicated spots. Free-form maps (aliases, secrets, gifs values,
users values) keep their keys open.

Retire dead `extra_local` field (written 132/275/291, never read).

Verified: relay-os/, example/relay-os/, and both templates use only allowed
keys → nothing hard-fails on next command.

### Implemented + tested (claude, 2026-06-19)

Done on branch `config-fail-loud-unknown-sections`, commit 2671fc4.

What changed in `src/relay/config.py`:
- Added `_reject_unknown_keys(table, allowed, label)` (no-op on non-dicts so the
  existing "must be a table" type errors still fire) + per-table allowed-key
  frozensets.
- `_reject_unknown_sections(shared, local)` validates top-level keys of both
  files plus the cross-file `[notification]` / `[notification.slack]` / legacy
  `[slack]` / `[git]` tables. Called from load_config AFTER the dedicated
  `[assignees]` raise.
- `_parse_agents` rejects unknown shared agent keys AFTER the dedicated
  skip_permissions* raise (both tailored messages preserved).
- `_parse_launch` / `_parse_ticket_fields` reject `[launch]` / `[ticket]` keys.
- Removed dead `extra_local` field + its population.

Tests: added 15 cases in tests/test_config.py — one accept-all-known-keys case,
reject cases at every level (incl. the `[notification.slak]` footgun, local-only
`default_status`, cross-file local `[git]`), free-form-maps-stay-open,
assignees-message-beats-generic, and extra_local-retired.

Verification (python3.12 — repo needs 3.11+, default python is 3.9):
- `python -m pytest` → 837 passed, 1 skipped.
- `relay validate --json` in example/relay-os → ok_count 1, no issues.
- Loaded nick's live relay-os config under new code → loads, user=nick,
  extra_local attr gone.

No push / no PR (that's code/open-pr). Worktree clean.

### Peer review (codex, 2026-06-20)

Native review:
- `codex review --base main` first failed inside the sandbox with the known
  read-only app-server initialization error, then succeeded when rerun with
  escalation.
- Finding: local `[git].remote` / `[git].control_branch` were accepted by the
  new allowlist but still ignored by `load_config` (`_parse_git` only reads
  shared `[git]`). This preserved a silent local-config misconfiguration path.

Fix applied in feature worktree `/home/n/Code/relay-config-fail-loud`:
- Split git allowlists: shared `[git]` accepts `enabled`, `remote`,
  `control_branch`; local `[git]` accepts only `enabled`.
- Added regression coverage that local `[git].remote` and
  `[git].control_branch` now fail loud.
- Committed as `3b3821c` (`peer-review: apply review findings`).

Verification:
- `python -m pytest tests/test_config.py -q` -> 71 passed (pytest cache warning
  only: feature worktree `.pytest_cache` is read-only).
- `python -m pytest` -> 839 passed, 1 skipped (same pytest cache warning).
- `PYTHONPATH=/home/n/Code/relay-config-fail-loud/src python -m relay.cli validate --json --task fail-loud-on-unrecognized-config-sections-instead`
  from the primary checkout -> ok_count 1, no issues.
- Repo-wide `relay validate --json` with the same `PYTHONPATH` still fails on
  unrelated existing task-state drift (missing-step errors on other tasks and
  unknown-assignee warnings); this ticket validates cleanly.
- `relay bump ... --message "Peer review fix committed: 3b3821c; tests passed."`
  advanced the ticket to step 3 (`open-pr`) assigned to `claude`, then exited
  non-zero because Slack DNS failed in the sandbox before git sync/done-marker
  cleanup. The auto-written Slack failure log line contained the webhook URL;
  it was redacted before committing task state.

### Open PR (claude, 2026-06-19)

- Auth probed: `gh auth status` ok (nicktoper), remote = FastJVM/relay (https).
- Pushed `config-fail-loud-unknown-sections`; opened PR #418
  (https://github.com/FastJVM/relay/pull/418). No prior draft existed.
- CI: `gh pr checks 418` → "no checks reported" (repo has no CI workflows on
  this branch) — nothing to wait on. Bumping to human review.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: 'New coga/architecture detail: config loader fails loud on unknown keys'
