The blackboard is a notepad to be written to often as the human and agent works through a task.

## Tier-2 shim design (2026-06-23, zach + claude) — restating Nico's ticket spec

The "committed design" the Done= asks for. This ELABORATES Nico's sketch in the
ticket body; it does not change it. Scope here is the GENERIC `arg → create-draft
→ launch` mechanism only. Greet-first / the spawn-consolidation is a separate,
nick-owned ticket (see "Relationship" below), not part of this design.

### 1. The shim's declarative schema (Nico's sketch, verbatim)
```toml
[shims.ticket]
launch = "bootstrap/ticket"
draft_if_missing = true
validate_after = true
sync = ["tasks", "contexts", "skills"]
require_tty = true
```
Each field = one tested `ticket.py` behavior the shim must express:
- `launch` — the authoring entry to launch.
- `draft_if_missing` — `create_draft(arg)` when arg isn't an existing ticket.
- `validate_after` — post-session `validate_task_dir` + the draft-must-have-a-workflow gate.
- `sync` — snapshot/diff/git-sync of tasks/contexts/skills.
- `require_tty` — the interactive-TTY check.

### 2. Dispatch — the cli.py around-hook
`cli.py main()` rewrites argv BEFORE Typer today — there is no after-hook. The
shim needs a real **around-hook**: for a shim-name command, resolve arg →
(draft_if_missing) → launch → validate_after + sync. This is the ONE new
mechanism Pass 2 builds.

### 3. Which commands migrate
`ticket`, then `project`, then `retire` — the three fused heads whose shape is
`arg → create-draft → launch`.

### 4. What stays bespoke (OPEN — enumerate before building)
The shim expresses only the fixed `arg → draft → launch` shape. Anything beyond
that stays as shared-runner Python or a tier-3 skill:
- `project`'s multi-ticket decomposition and `retire`'s retro are agent/skill
  work (tier-3 skills the shim launches), not declarative.
- Edge behaviors of `ticket.py` to place: the caution-status heads-up (editing
  an in_progress/done ticket), the workflow gate, the create-or-edit resolve.
- TODO: walk `ticket.py` / `project.py` / `retire.py` and tag each behavior as
  field | shared-runner-Python | tier-3-skill.

### 5. Order (Nico's)
- **First (no new mechanism needed):** reads → stateless script shims
  (status / show / recurring list / skill status); `recurring` scan → Dream-shaped task.
- **Last (gated on the shim):** the fused heads — `ticket`, then `project` / `retire`.

### Guardrails (from relay/extension-model)
- **No inversion** — relocate the tested Python UNCHANGED into the shim runner /
  script steps; never rewrite a deterministic check as agent judgment.
- **No worse Typer** — keep the single fixed shape `arg → draft → launch`; no
  conditionals / computed args / validation in `relay.toml`.

### Relationship to greet-first / the launch mechanism
Greet-first (the `Begin` kickoff + the shape-specific greeting) is NOT part of this
generic shim. It lives in `finish-relay-ticket-greet-first-land-pr-417`
("Consolidate agent-triggering into one launch mechanism, greet-first as an
option"), which **supersedes PR #417** and fixes a deeper issue: `ticket.py` /
`project.py` hand-roll their OWN copy of the `relay launch` spawn sequence instead
of routing through it.

Ownership + sequencing: zach took over BOTH greet-first tickets
(`finish-...-417` and `marketing/relay-ticket-creates`) from nick on 2026-06-23
(nick hadn't started). **This shim is built FIRST** — it provides the structure
the greet-first work builds on; greet-first then layers the kickoff/greeting as an
option on the consolidated launch path. So: shim first -> greet-first second, both
zach-owned. (The shim's `launch` step should route through that one consolidated
path, not re-fork the spawn.)
