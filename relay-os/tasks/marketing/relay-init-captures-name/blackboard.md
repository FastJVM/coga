# relay-init-captures-name — design

## Decisions (owner, 2026-06-17, interactive design step)

- **Scope = WIDE.** This ticket includes (1) name capture at `relay init`,
  (2) stamping `new-user` → captured name in delivered tickets, AND (3) the
  empty/filled-repo gate + conditional seeding of the onboarding ticket.
  Rationale: `relay-build-onboarding-flow` delegated the gate here (its Out of
  Scope) and is at open-pr without implementing it; `relay-build-command`
  doesn't claim it either — so the gate lands here or is orphaned. It's also all
  one code region (`_do_init`), so doing it here avoids a later PR re-touching
  the same function.
- **browser-automation = switch to placeholder + stamp.** Change its packaged
  template from `owner/human: zach` to the `new-user` placeholder so the single
  stamp path fixes it alongside the onboarding tickets. (Owner declined "leave
  it" and "stop shipping it".)

## Key facts found during investigation

- The name-prompt + validation already exists in `setup._ensure_user`
  (`src/relay/commands/setup.py:66`) — moving capture to init is mostly relocating
  it. Plan: extract `_prompt_user_name()` into `init.py`, call from both.
- Only three *delivered, launchable* tickets ship a bad owner:
  `tasks/relay-setup/ticket.md` and `tasks/relay-build/ticket.md` (`new-user`,
  active), and `tasks/browser-automation/ticket.md` (`zach`, draft). Both
  onboarding tickets ship today (rename to a single `relay-build` is
  `relay-build-command`'s job).
- `_template` / `_rem` use the `replace-with-human-name` token, overwritten by
  `create_task`/recurring — leave them alone. The stamp must match `new-user`
  only, not that token.
- `relay-build-requires-init` ticket dir does not exist — folded into
  `relay-build-command` per that ticket's Context. Fixed the stale reference in
  this ticket's Context.

## Open Questions (for review-design)

1. **Non-interactive init.** A fresh `relay init` now blocks on a name prompt
   (same as `relay setup` today). Do we also want a non-interactive escape —
   a `--user NAME` flag or `RELAY_USER` env — for scripted/CI init? Default if
   unanswered: interactive-only, matching current `relay setup`.
2. **Exact empty/filled ignore-set.** onboarding-flow says "empty = nothing but
   `.git/`, `.DS_Store`, and relay's own files." At gate time (before init writes
   anything) relay's own files don't exist yet, so the only real question is
   whether a *pre-existing, user-authored* `CLAUDE.md` / `AGENTS.md` counts as
   "empty" (relay-managed name) or "filled" (a real project signal). Proposed
   default: ignore `{.git, .DS_Store}` and dirs/files init itself manages; treat
   any other pre-existing file — including a hand-written `CLAUDE.md` — as filled.
   Confirm the membership.
3. **browser-automation on filled repos.** It's not gated (gate covers only the
   onboarding ticket), so a filled repo still receives the browser-automation
   *draft* (now stamped). Fine, or should it be omitted on filled repos too?
