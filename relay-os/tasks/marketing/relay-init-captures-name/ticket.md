---
title: relay init captures the user's name (kill the new-user placeholder)
status: done
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

`relay init` should ask the user for their name as a scripted prompt and write
it to `relay.local.toml` (`user`), so `current_user` is valid from the very
first moment after init. Today init ships `user = ""` and defers name capture to
`relay build` / `relay setup` — but relay machinery (ticket creation, `relay
chat`, launching) is usable right after init, before any name exists. Capture at
init, then stamp that name into the delivered onboarding ticket so the
`new-user` placeholder never ships as a live value — it should not survive this
relay-build work.

## Context

- One source of truth: everything stamps owner/human from `cfg.current_user`
  (the `user` line in `relay.local.toml`) — `create_task` does
  `owner = owner or cfg.current_user` (`src/relay/create.py:55`), the onboarding
  workflow's first step sets owner/human from it, and the launch gate
  (`src/relay/config.py`) refuses if it's unset. But init's `LOCAL_TOML_TEMPLATE`
  ships `user = ""` and init never prompts.
- The gap: bootstrap machinery is usable immediately after init (`relay chat` →
  bootstrap/orient, `relay ticket` → create_task) — before `relay build`
  captures the name. Anything created or launched in that window gets an empty or
  placeholder owner.
- `new-user` lives only in the onboarding ticket template
  (`tasks/relay-setup/ticket.md`; → `relay-build` in the new design):
  `owner: new-user`, `human: new-user`. Introduced in `ba6ca2a3` (#348, the
  relay-setup scaffold). It's currently overwritten by the agent at first launch
  (soft/fragile); a human-assigned step reached before that makes `relay launch`
  die with "Agent type 'new-user' is not defined" (same class as a human-name
  assignee).
- Scope (owner decision 2026-06-17 — go *wide*): (1) `relay init` asks for the
  name (scripted) and writes `user`; (2) stamp that name into delivered tickets so
  `new-user` never ships live; (3) the empty/filled gate + conditional seeding of
  the onboarding ticket — delegated here by `marketing/relay-build-onboarding-flow`
  (Out of Scope), which is at open-pr and does **not** implement it, so it lands
  here or nowhere. Once init captures the name, `_ensure_user` becomes a
  no-op/legacy fallback. The setup→build rename, `relay build` requiring init, and
  the next-steps command token live in `marketing/relay-build-command` (which
  subsumed `relay-build-requires-init`).
- Reverses the entry-mechanic call in `marketing/relay-build-onboarding-flow`
  ("name capture stays in the command, no prompt in init"); that bullet is
  updated. Reason: machinery usable pre-build needs a valid `current_user` at init.
- Not affected: the bootstrap items themselves (orient/project/ticket) ship
  `assignee: claude`, no owner/human, no placeholder. Leftover scrubbed here
  (owner decision 2026-06-17): `tasks/browser-automation/ticket.md` ships
  `owner: zach` hardcoded — switch it to the `new-user` placeholder so the same
  stamp fixes it. The `_template`/recurring `replace-with-human-name` placeholders
  are fine — `create_task`/recurring overwrite them from `current_user`.

## Acceptance Criteria

- [ ] A fresh `relay init` (not `--update`) prompts for the operator's name with a
  scripted prompt, validated as in `setup._ensure_user` (non-empty, no `"` or
  `\`), and writes it to `user` in `relay.local.toml`. A fresh init never leaves
  `user = ""`.
- [ ] `relay setup`/`relay build` (which call `_do_init`) do not double-prompt on a
  fresh repo: init captures the name and `_ensure_user` finds `user` already set.
- [ ] After a fresh init, no delivered ticket under `relay-os/tasks/` carries
  `owner: new-user`, `human: new-user`, or `assignee: new-user` — the captured
  name is stamped over the placeholder.
- [ ] `browser-automation`'s packaged template no longer hardcodes `owner: zach` /
  `human: zach`; it uses the `new-user` placeholder and is stamped to the captured
  name on init.
- [ ] Empty repo (contents are only `.git/`, `.DS_Store`, and relay-managed files):
  init keeps/seeds the onboarding ticket (`relay-build`, shipped `status: active`)
  and the printed next-steps point the user at the onboarding command.
- [ ] Filled repo (any other pre-existing file): init does **not** ship the
  onboarding ticket, and the printed next-steps coax the user toward `relay ticket`.
- [ ] The empty/filled decision is made against the repo's pristine contents,
  before init writes any of its own files.
- [ ] `relay init --update` is unchanged — it neither prompts for the name nor
  evaluates the gate.
- [ ] `relay validate` passes on a freshly-initialized empty repo (the seeded,
  stamped onboarding ticket validates).
- [ ] `tests/test_init.py` monkeypatches the name prompt and covers: name written
  to `relay.local.toml`; `new-user` stamped out of every delivered ticket; empty
  repo → onboarding seeded + onboarding-pointed next-steps; filled repo →
  onboarding absent + `relay ticket`-pointed next-steps.

## Proposed Shape

Rewire `_do_init` (`src/relay/commands/init.py`), pristine-contents check first:

1. Keep the `relay_os.exists()` refusal as the first guard — don't prompt only to
   error out.
2. `is_empty = _repo_is_empty(target)` — scan `target`'s current entries against an
   ignore-set of `{.git, .DS_Store}` plus relay-managed paths (`relay-os`,
   `CLAUDE.md`, `AGENTS.md`, `.claude`, `.codex`, host `.gitignore`); any other
   entry ⇒ filled. (Implement finalizes the exact ignore-set against real init
   output — see the blackboard open question.)
3. `name = _prompt_user_name()` — the validation loop lifted from
   `setup._ensure_user` (non-empty, no `"`/`\`). Always prompts, regardless of the
   gate (name capture is unconditional; the gate only affects seeding/next-steps).
4. `copy_fresh_templates(...)` as today, then:
   - If `not is_empty`: prune the delivered onboarding ticket dir(s) from the
     copied tree (`tasks/relay-build/`, plus `tasks/relay-setup/` while both still
     ship).
   - `_stamp_user_into_delivered_tickets(relay_os, name)` — regex-replace
     `^(owner|human|assignee):\s*new-user\s*$` → `\1: <name>` across
     `tasks/**/ticket.md`. Leaves `replace-with-human-name` (`_template`, `_rem`)
     untouched — different token, owned by `create_task`/recurring.
5. `local_toml.write_text(render_local_toml(name))` instead of writing the raw
   `user = ""` template; `render_local_toml` substitutes the name into
   `LOCAL_TOML_TEMPLATE`.
6. Branch the next-steps `steps` list on `is_empty`: empty → keep the onboarding
   coax (using the surviving `relay setup` token — see coordination); filled →
   replace it with a `relay ticket "<title>"` coax.

New helpers in `init.py`: `_prompt_user_name()`, `render_local_toml(name)`,
`_repo_is_empty(target)`, `_stamp_user_into_delivered_tickets(relay_os, name)`, and
the filled-repo prune (inline or `_prune_onboarding_tickets(relay_os)`).

`src/relay/commands/setup.py`: refactor `_ensure_user`'s inline prompt loop to call
`init_cmd._prompt_user_name()` so init and setup share one prompt + validation
(behavior unchanged; `_ensure_user` stays as the legacy `user`-empty fallback).

`src/relay/resources/templates/relay-os/tasks/browser-automation/ticket.md`:
`owner: zach` / `human: zach` → `new-user` / `new-user`.

Coordination with siblings:

- Next-steps command token: keep the survivor (`relay setup`) in the empty branch;
  `relay-build-command` renames it to `relay build` in the change that ships the
  command. Mirrors onboarding-flow's `relay create`→`relay ticket` deferral.
- Both onboarding tickets ship until `relay-build-command` deletes `relay-setup`;
  the gate + stamp treat the onboarding ticket(s) generically, so no rework lands
  when one is removed.

## Out of Scope

- The setup→build rename, `setup.py`→`build.py`, CLI registration, requiring an
  init'd repo, and the latent `launch()` arg-count bug → `marketing/relay-build-command`.
  This ticket leaves the onboarding command token as `relay setup`.
- The `build/onboarding` workflow content and the delivered `relay-build` ticket
  body → `marketing/relay-build-onboarding-flow`.
- The `relay ticket` creation primitive / retiring `relay draft` / `relay create`
  → `marketing/relay-ticket-creates`.
- Filled-repo onboarding and the bounded, opt-in scan with a token ceiling →
  deferred future ticket.
- Gating or removing `browser-automation` — it ships as before (now stamped, not
  `owner: zach`); the empty/filled gate covers only the onboarding ticket.
- `tests/test_setup.py` updates → land with the command rename.
