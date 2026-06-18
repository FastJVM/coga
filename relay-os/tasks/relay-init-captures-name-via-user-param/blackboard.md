The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (design step)

Investigated the live #391 branch (`init-captures-name-impl`, worktree
`/Users/zach2179/Desktop/relay-init-name-impl`) — the *current* worktree
(`feat/relay-init-captures-name`) does NOT contain #391's name-capture work, so
the spec is written against the impl branch.

What #391 does today (the thing we're revising):
- `_do_init` calls `_prompt_user_name()` up front (before the slow clone), then
  uses the name for two things: `render_local_toml(name)` and
  `_stamp_user_into_delivered_tickets(relay_os, name)`.
- `setup._ensure_user` shares the same `_prompt_user_name()` helper; on the fresh
  `relay setup` path it's a no-op echo because `_do_init` already set `user`.
- `new-user` placeholder ships in two tickets: `tasks/relay-setup/ticket.md` and
  `tasks/browser-automation/ticket.md` (owner + human lines).

The switch to `--user` is mechanical for direct `relay init`. The only real
ripple is the setup path (see Open Question 1).

## Decisions (resolved live with owner, 2026-06-18)

Re-oriented on `marketing/relay-build-command` (draft): name capture lives in
`relay init` ONLY; `relay setup` → `relay build` later, which requires an
already-init'd repo and does NOT capture the name. So `relay setup` is a dying
path and my ticket should stay a pure `relay init` change.

1. **`new-user` stamping on the `relay setup`-creates-a-fresh-repo path →
   Option A: don't handle it.** Leave `setup.py` / `_ensure_user` untouched; the
   `via_setup=True` branch in `_do_init` writes the empty template and does not
   stamp. Accepted: that transient path may leave `new-user` in onboarding
   tickets until `marketing/relay-build-command` redesigns onboarding. Only the
   direct `relay init --user` path stamps. (Owner picked A.)

2. **`--user` alongside `--update` → silently ignore.** `--update` stays exactly
   as-is; `--user` is simply not read/passed on that path. Default chosen to keep
   the "`--update` is unchanged" promise; low-stakes, override at review-design if
   desired.

3. **Error exit code → `sys.exit(2)`** for both missing-`--user` and
   invalid-`--user`, matching the existing `init` arg errors (`--all` misuse,
   `relay-os already exists`).

## Open Questions

None outstanding — all resolved above. (review-design: override any of the three
defaults if you disagree.)
