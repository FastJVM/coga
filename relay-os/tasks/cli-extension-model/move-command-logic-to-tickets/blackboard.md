The blackboard is a notepad to be written to often as the human and agent works through a task.

## Tier-2 shim design — working draft (2026-06-23, zach + claude orientation session)

**Goal:** collapse the `arg → draft → launch` heads of `ticket`/`project`/`retire`
onto one declarative tier-2 shim, retiring bespoke `commands/ticket.py` (~320 lines).
Per `relay/extension-model` this is Pass 2's one new mechanism.

**The shim (example: `relay ticket`):**
```toml
[shims.ticket]
launch = "bootstrap/ticket"              # authoring entry/skill to run
                                         # (rename to bootstrap/ticket-authoring = separate deferred follow-up)
draft_if_missing = true                  # arg not an existing ticket? create_draft from it
validate_after = true                    # re-validate the ticket after the session
sync = ["tasks", "contexts", "skills"]   # git-commit changed files
require_tty = true
kickoff = "Begin"                        # first-turn token -> agent greets first
```

**Three shapes, distinguished from FILE STATE (no transient param):**
- no arg -> bare (compose the shim itself).
- arg = existing slug -> existing (compose that ticket; body already filled).
- arg != slug -> new (create_draft, compose it; body empty).
The greeting reads "which ticket am I on + is the body empty" — all files-on-disk.

**ticket.py -> new home:** resolve/draft/validate/sync Python -> the shim runner
(moved UNCHANGED — no-inversion); `cmd.append("Begin")` -> `kickoff` field;
shape-specific greeting -> the authoring skill (composed on every authoring launch).

**Constraints (from extension-model):** fixed shape only (no `relay.toml`
conditionals/computed args — no-worse-Typer); params only if materialized into
files (shape is READ from files, never stamped as a transient launch param);
shim leans on kernel `create` + `launch` (both certified kernel by Pass 1).

**The one new mechanism to build:** a `[shims.*]` config schema + a dispatch
**around-hook** in `cli.py` (today `main()` only rewrites argv *before* Typer —
there is no after-hook; the shim adds one). Everything else is moving existing
tested Python into it.

**Migration order:** `ticket` first (= PR 417 greet-first, delivered cleanly +
deletes `ticket.py`) -> then `project`, `retire`. Plus the no-mechanism moves
(reads -> script shims; `recurring` -> Dream-task) per the ticket body.

### Open questions
1. **Greeting home — confirm with Nico.** The mechanics put the shape-specific
   greeting in the authoring SKILL (composed on every authoring launch), not the
   shim's `ticket.md` — because for new/existing the launch target is the *user's*
   ticket, so the shim body isn't composed. Does this match his "in the ticket.md"
   framing?
2. **Milestone.** Stop at this committed design (ticket "done" per its own
   "Done = a committed design"), or green-light building the shim + migrating
   `ticket` (which delivers greet-first / PR 417)?
