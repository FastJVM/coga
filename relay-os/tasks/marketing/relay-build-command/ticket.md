---
title: Add the relay build command (replaces relay setup)
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
---

## Description

Add the `relay build` command by renaming `relay setup` → `relay build`, and
retire `relay setup`. After `relay init`, the user runs `relay build`, which
launches the new `relay-build` onboarding ticket (one question → agent-led chat
→ spec → flat ticket batch). Two deliberate departures from the old `relay
setup`: `relay build` **requires an already-initialized repo** (it does NOT run
`relay init` itself — fail with "run `relay init` first" when there's no repo),
and it **does not capture the user's name** (that moved to `relay init`). "relay
setup" disappears from the command, the source file, and the next-steps text.

## Context

- Fresh replacement for `marketing/remove-relay-setup-command` (being closed):
  that ticket was scoped as a straight rename that *carried over* `relay setup`'s
  init-if-needed + name-capture, both of which this session reversed — so a clean
  rewrite is clearer than patching it.
- **Folds in `marketing/relay-build-requires-init`** — "no init-if-needed,
  require an already-init'd repo" is part of defining the renamed command. Retire
  that ticket as subsumed.
- Name capture is **out of scope here** — it lives in `relay init` now
  (`marketing/relay-init-captures-name`); `relay build` just relies on `user`
  being set before launch.
- Files: `src/relay/commands/setup.py` → `build.py`; the command registration +
  `_BUILTIN_COMMANDS` entry in `src/relay/cli.py`; `relay init`'s next-steps text
  repointed at `relay build`; the packaged `relay-setup` ticket template →
  `relay-build`, and the `init/setup` workflow → `build/onboarding` (keep the live
  and packaged copies in sync). The onboarding flow content is designed in
  `marketing/relay-build-onboarding-flow`.
- Carry the latent-bug fix forward: `setup.py`'s `launch_cmd.launch(...)` call
  passes only 6 of `launch()`'s 8 params, omitting `max_session` and
  `return_timeout` (added to `launch` after `setup.py` was written). Because
  `launch` is a Typer command, the unpassed params keep their `typer.Option(...)`
  defaults (`OptionInfo` objects), so the call crashes at launch
  (`repl_supervisor.py`: "'>=' not supported between instances of 'float' and
  'OptionInfo'"). The renamed command must pass all of `launch()`'s params — or,
  better, call a non-Typer helper so new options can't silently become sentinels.
- Companions: `marketing/relay-build-onboarding-flow` (the flow this launches),
  `marketing/relay-init-captures-name` (the init-side name capture this relies on).
