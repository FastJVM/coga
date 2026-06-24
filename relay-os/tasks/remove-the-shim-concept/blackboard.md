# remove-the-shim-concept — design notes

## Design-session decisions (2026-06-24, with zach)

1. **"No worse Typer" guardrail → keep substance, drop the name.** The
   guardrail and the "tier-2 shim" name protect different things: the *name*
   labels a mechanism we're deleting; the *guardrail* protects against a
   `relay.toml` config DSL, a live risk for the extraction program. So we keep
   the guardrail's teeth and remove only the label. Reworded text is in
   `ticket.md` → Proposed Shape → Model-contract rewordings.
2. **Install-symlink identifiers left untouched.** `init.py`
   `_try_install_shim`/`_relay_shim`, `uninstall.py` `shim` vars, and their
   tests are the `~/.local/bin/relay` OS symlink — a different sense, carved
   out by the ticket. Behavior-neutral; renaming reaches into the install path
   for no model-clarity benefit. Decided: leave.
3. **Naming locked:** prose "shim" → **bootstrap ticket** / **stateless launch
   target**; code `DISCUSSION_BOOTSTRAP_SHIMS` → `DISCUSSION_BOOTSTRAP_TICKETS`,
   `shim_ticket` → `bootstrap_ticket`.

## Open Questions

None unresolved. `review-design` ask for Nico = **approve the reworded
model-contract passages** (ticket.md → Proposed Shape → Model-contract
rewordings) and the rename inventory. The two judgment calls above were settled
live with zach; the rest is mechanical.

## Findings (for the implement step)

- **Three-tree sync, with existing drift.** `architecture` has 3 copies
  (top-level live, gitignored live bootstrap, packaged template) and they've
  already drifted ("creates" vs "scaffolds"). `cli` is bootstrap-battery-only —
  2 copies (live bootstrap + packaged), **no top-level copy** — and those two
  have drifted too. The sweep must harmonize each to identical shim-free text.
- `extension-model`, `codebase`, `project-stage` are project-local (1 copy
  each).
- `.relay/` holds a vendored copy of the CLI (`launch.py` etc.) — gitignored,
  init-managed, excluded from the sweep.
- A stale `__pycache__/shim.cpython-312.pyc` lingers from the
  already-deleted `shim.py` command — harmless, gitignored, out of scope.
- The `cli` context's Aliases section still lists only `chat` + `dream` —
  pre-existing doc drift unrelated to "shim"; flagged as a separate follow-up.
