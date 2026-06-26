---
slug: cli-extension-model/rename-shim-to-alias
title: Rename "shim" to "alias" across Relay
status: draft
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- relay/extension-model
- relay/architecture
- relay/codebase
skills: []
workflow: null
secrets: null
---

## Description

Replace the term **shim** with **alias** everywhere in Relay — contexts, docs,
tickets, code, config, and skills — so the vocabulary is one word. A shim and an
alias are both thin routing-layers that point a command at a launch;
standardizing on "alias" removes the jargon. **Do this FIRST**, before the
command-move work, so that work uses the final terminology from the start.

## Context

Two distinct things are both called *shim* and both get renamed:
1. **Bootstrap shims** — `bootstrap/orient`, `bootstrap/ticket`: stateless
   launch-target `ticket.md` files.
2. **The tier-2 shim** — the `[shims.*]` config + the `cli.py` around-hook + the
   `Shim` dataclass / `run_shim`, introduced in PR #425.

Both become *alias*, qualified by tier: a **tier-1 alias** is pure argv sugar
(no logic); a **tier-2 alias** does the one thing a tier-1 can't — materialize a
ticket from a CLI argument.

Considerations:
- **Preserve the functional distinction.** Renaming the *word* must not merge
  the *concepts* — tier-1 (no logic) vs tier-2 (makes a draft from an arg) stay
  distinct; keep the tier qualifiers.
- **`extension-model` currently contrasts "alias" vs "shim"** (*"aliases are not
  a fourth home — they are argv sugar"*). That wording gets rewritten, not the
  distinction deleted.
- **Scope:** `relay-os/contexts/*`, `docs/*`, `src/relay/` (the `[shims.*]`
  config key, `commands/shim.py`, `cli.py`, the `Shim` dataclass + `run_shim`),
  task `ticket.md`/blackboards, skills, tests.
- **Coordinate with PR #425** — it introduces `[shims.*]` + `Shim` + `run_shim`.
  Either rename within #425 before it merges, or sweep right after it lands, so
  the new names don't immediately go stale.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
