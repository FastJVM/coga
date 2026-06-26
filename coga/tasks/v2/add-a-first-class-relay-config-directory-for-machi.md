---
slug: v2/add-a-first-class-relay-config-directory-for-machi
title: Add a first-class relay config directory for machine-local config and secret
  files
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Relay has no first-class home for machine-local **config and secret
*files*** that bootstrap skills need at runtime. Today the only local-config
surface is `relay.local.toml` (key/value, gitignored, `env:VAR`
indirection). That covers scalars and secret *references*, but not actual
files a skill must read — e.g. a Google service-account JSON key.

This surfaced wiring up the bundled `relay/google-calendar` skill: it reads
`[calendar].service_account_file` (a path) from `relay.local.toml`, but the
key file itself has no sanctioned location. We ended up dropping it in an
ad-hoc gitignored holding dir (`<repo>/.secrets/`) because the repo's
`.gitignore` only protects `/relay.local.toml` — a raw key at repo root
would be committable. That's a footgun the product should remove.

Propose and implement a **first-class relay config directory**: one
sanctioned, git-safe place for per-machine config/secret files, materialized
and gitignore-protected by `relay init`, discoverable by skills via a stable
env var (à la the existing `RELAY_*` launch vars), so a bootstrap skill can
resolve a credential file without each repo reinventing a hiding spot.

Open questions for whoever picks this up:

- **Location & name** — `relay-os/.config/`? `relay-os/config.local/`? A
  user-level `~/.config/relay/<repo>/`? Repo-local keeps it grep-able and
  co-located; user-level keeps secrets out of the repo tree entirely.
- **gitignore guarantee** — `relay init` must ensure the dir is ignored
  (the way `/relay.local.toml` is today) so a dropped key can never be
  committed. Fail loud if the ignore rule is missing.
- **Skill discovery** — expose the path as e.g. `RELAY_CONFIG_DIR` in the
  composed prompt and the `mode: script` env var set, alongside
  `RELAY_RELAY_OS_ROOT` etc.
- **Relationship to `relay.local.toml`** — does `service_account_file`
  become a name resolved *relative to* the config dir, or stay an absolute
  path? Keep `env:VAR` indirection working either way.
- **Legibility** — must not violate "markdown-first, legible, no hidden
  state." A directory of plainly-named files a human can `ls` is fine; an
  opaque blob store is not.

Out of scope: rotating/managing the credentials themselves; any
cloud-specific auth logic (that lives in the consuming skill).

## Context

- Triggering work: the `relay/google-calendar` skill (relay PR #249,
  merged) + the patents consumer wiring (FastJVM/patents PR #57). The
  patents `relay.local.toml` still needs a `[calendar].service_account_file`
  pointing at the SA key — deferred until this config-directory shape is
  decided.
- Interim state today: the SA JSON key lives at `<this-repo>/.secrets/relay-calendar-sa.json`
  (gitignored via a new `/.secrets/` rule, `chmod 600`). That `.secrets/`
  dir is a placeholder, not the proposed design — replace it.
- Precedent to mirror: `relay.local.toml` (gitignored local config) and the
  `RELAY_*` env vars injected for `mode: script` launches (see
  `relay/architecture`, "Dream's known-skill contract" env list).
- Relevant principle: "Markdown-first, git-backed, legible" and "Fail loud"
  (the gitignore guarantee) — see `relay/principles`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
