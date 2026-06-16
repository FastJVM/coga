# remove-relay-setup-command → "Replace relay setup with relay build"

## 2026-06-16 — reframed as part of the relay-build onboarding epic

This ticket started as "remove the `relay setup` command, keep `relay init`
scaffolding the relay-setup interview." During the design step Zach reframed the
whole onboarding direction into **`relay build`** — one scripted question ("what
do you want to build?") + agent-led chat → spec → first batch of launchable
tickets.

**Why the premise changed:** removing the command orphaned its name capture.
`relay launch` calls `load_config`, which fails loud if `user` is unset
(`src/relay/config.py:216`), so the interview ticket can't capture its own name
— nothing runs before launch except `relay init`. The clean answer is to
**rename** `setup` → `build` rather than remove it: name capture stays in the
command, and `relay init` stays a pure scaffold (no prompt). So the old design
exploration (move `_ensure_user` into init, isatty guard, init next-steps note)
is moot.

**Parked, not done.** This ticket is the command rename only. Its design depends
on the onboarding flow design in `marketing/relay-build-onboarding-flow` (it
fixes the target names: `relay-build` ticket, `build` workflow). **Design the
keystone first, then return here.** Not bumped on purpose — no spec is written
under the new premise yet.

**Slug:** still `remove-relay-setup-command`; rename to `relay-build-command`
when convenient (deferred — it's mid-launch).

## Epic map (all in `marketing/`)

- `relay-build-onboarding-flow` (was `shorten-relay-setup-interview-flow`) — the flow design. **Keystone.**
- `remove-relay-setup-command` (this) — the `relay build` command + retire `relay setup`.
- `onboarding-plan` — parent strategy; target flow + interview stance updated.
- `relay-ticket-creates` — the ticket-creation primitive the generate step rides.
- `init-questions` — design/validation record of the approach being replaced (keep; don't rename).
- `validate-relay-build-onboarding` — new; tests empty / filled / ±CLAUDE.md.
