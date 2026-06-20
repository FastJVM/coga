---
title: Fail loud on unrecognized config sections instead of silently treating webhook
  as absent
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
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
