---
title: relay build requires an already-initialized repo
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

`relay build` currently creates the repo itself by calling `relay init` when
none exists — leftover from the `relay setup` command it was renamed from. Drop
that: `relay build` should require an already-initialized relay repo and do
onboarding only. Run where relay isn't initialized, it should fail with a clear
"run `relay init` first" message instead of silently initializing.

## Context

- The init-if-needed lives in `src/relay/commands/build.py`: on `find_repo_root`
  failure it calls `init_cmd._do_init(target, via_setup=True)`. This is verbatim
  heritage from `relay setup` (init-if-needed + name capture + launch onboarding)
  and was not reconsidered during the rename to `relay build`.
- Target flow: `relay init` first (creates the repo + seeds onboarding), then
  `relay build` runs onboarding against the already-init'd repo. Build is
  onboarding-only, not repo creation.
- Companion: `marketing/remove-relay-setup-command` (the rename) still carries
  this `_do_init(..., via_setup=True)` call. The `via_setup` flag in `init.py`
  (it suppresses the "run relay build" next-step) can be revisited once build no
  longer calls init.
- Related, still in discussion (not yet decided): the empty-repo-only direction
  for `marketing/relay-build-onboarding-flow` — whether `relay init` seeds the
  `relay-build` ticket only for empty repos, and how filled repos are handled.
