# relay-init-captures-name — design

## Dev
branch: init-captures-name-impl
worktree: /Users/zach2179/Desktop/relay-init-name-impl
pr:

## Implementation decisions (agent, 2026-06-17, implement step)

- **`relay setup` interaction:** `relay setup` calls `_do_init(via_setup=True)`
  then launches the `relay-setup` ticket. The empty/filled prune is therefore
  gated on `not via_setup` — otherwise setup would prune the very ticket it is
  about to launch. Name capture still happens under `via_setup` (so the
  "no double-prompt" criterion holds: `_ensure_user` finds `user` already set).
  Net: `relay setup` behaves exactly as before; only bare `relay init` evaluates
  the gate for pruning/next-steps.
- **Next-steps token stays `relay setup`** on the empty branch (the rename to
  `relay build` is `relay-build-command`'s job). Trimmed the "records your name"
  clause since init now captures it; `relay setup` will just echo the existing
  name and launch the interview.
- **Ignore-set for `_repo_is_empty`** = `{.git, .DS_Store, relay-os, CLAUDE.md,
  AGENTS.md, .claude, .codex, .gitignore}` — the set listed in the ticket's
  Proposed Shape. Pre-existing user-authored CLAUDE.md/AGENTS.md count as empty
  (relay-managed name), matching that decision.
- **Prompt fires early** in `_do_init` — after the `relay-os` refusal guard and
  the pristine empty-check, before the slow clone/venv — so a Ctrl-C at the
  prompt leaves nothing written and the user answers immediately.
- **Test approach:** autouse fixture stubs `init_cmd._prompt_user_name` → name
  so the existing CliRunner init tests don't block on stdin; the real validation
  loop is unit-tested via a module-level captured reference + patched
  `typer.prompt`. The fake clone now also ships `relay-build` (new-user, active)
  and `browser-automation` (new-user, draft) so the gate/stamp integration tests
  are representative of the real template set.

## Implementation results (agent, 2026-06-17, implement step)

- **Commit `7ff5b0fe`** on branch `init-captures-name-impl`. Files:
  `src/relay/commands/init.py` (new `_prompt_user_name`, `render_local_toml`,
  `_repo_is_empty`, `_prune_onboarding_tickets`,
  `_stamp_user_into_delivered_tickets`; rewired `_do_init`),
  `src/relay/commands/setup.py` (`_ensure_user` shares `_prompt_user_name`),
  `src/relay/resources/templates/.../browser-automation/ticket.md`
  (`zach` → `new-user`), `tests/test_init.py`.
- **Tests:** full suite `783 passed, 1 skipped` (pre-existing skip). New tests:
  name written to local.toml; no `new-user` survives in any delivered ticket;
  empty→onboarding seeded + `relay setup` coax; filled→onboarding pruned +
  `relay ticket` coax + skip notice; relay-managed files don't count as filled;
  unit tests for `_prompt_user_name` validation loop, `_repo_is_empty`,
  `_prune_onboarding_tickets` (both names), `_stamp_user_into_delivered_tickets`
  (leaves `replace-with-human-name` alone).
- **`relay validate` on the example fixture: clean** (`ok_count: 1`, no issues).
  validate-on-fresh-empty (a real network `git clone`) isn't unit-testable here,
  but the substantive guarantee is covered transitively: the only thing in the
  seeded tickets that would fail validate is the `new-user` placeholder, and a
  test asserts no `new-user` survives a fresh init.
- **Important test-harness fact for reviewers:** in pytest, `_do_init` copies the
  *real* worktree templates under `src/relay/resources/templates/relay-os`, NOT
  the fake-clone seed (the `fake_clone` fixture patches
  `update_cmd.packaged_template_root`, but `init` holds its own import binding).
  Tests therefore assert against the real shipped set, which on `main` is
  `relay-setup` + `browser-automation` (no `relay-build` yet — it lands with
  `relay-build-onboarding-flow`). The `_ONBOARDING_TICKET_DIRS` tuple +
  `_prune_onboarding_tickets` unit test cover the `relay-build` name for when it
  ships.

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
