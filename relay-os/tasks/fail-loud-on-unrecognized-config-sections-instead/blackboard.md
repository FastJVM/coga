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
