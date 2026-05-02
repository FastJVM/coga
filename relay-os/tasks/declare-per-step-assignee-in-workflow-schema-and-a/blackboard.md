# Implementation notes

## Final design (decided with nick during the session)

- Tickets gain two new role fields: `human:` and `agent:` (in addition to
  the existing `owner:` and `assignee:`).
- Workflow steps gain optional `assignee:` taking only **role tokens**
  (`owner` | `human` | `agent`). Literal nicknames are rejected by the
  workflow loader. Steps without `assignee:` leave the ticket assignee
  unchanged on bump (back-compat).
- On bump, the role token resolves against the ticket's matching role
  field; bump rewrites `assignee:` to that nickname. If the field is
  missing, **fail loud** (exit 2 with a clear message).
- Scaffold auto-populates `human:` ← `owner` and `agent:` ← (explicit
  `assignee` arg if it's a known agent nick) → (owner's lone configured
  agent). Initial `assignee:` is computed from workflow step 1's role
  token if present.
- Retrofit lives in `src/relay/retrofit.py:backfill_role_fields()` and
  is called from `relay init --update`. Same heuristic as scaffold for
  the agent inference.
- No `--assignee` override flag (per nick's call).
- One special token only: `owner` / `human` / `agent`. No `agent`-vs-
  literal hybrid.

## Files touched

- `src/relay/workflow.py` — `WorkflowStep.assignee`, role-token validation,
  `freeze()` propagates the field, `VALID_ASSIGNEE_ROLES` exported.
- `src/relay/ticket.py` — added `human` and `agent` properties.
- `src/relay/bump.py` — `resolve_step_assignee()`, `AssigneeResolutionError`,
  `advance_step(new_assignee=...)`.
- `src/relay/commands/bump.py` — resolves the step's role token, threads
  the resolved nickname through, appends `→ assigned to <name>` to
  log/slack/echo only when the assignee actually changes.
- `src/relay/scaffold.py` — `human` / `agent` params, `_default_agent_for`
  helper, initial-assignee resolution from step 1.
- `src/relay/retrofit.py` (new) — `backfill_role_fields()` for `init --update`.
- `src/relay/commands/init.py` — calls retrofit from `_do_update`,
  prints summary.
- `docs/spec.md` — workflow schema doc, ticket frontmatter table,
  full ticket example.
- `relay-os/contexts/relay/architecture/SKILL.md` — one-liner under
  workflows primitive.
- `src/relay/resources/templates/relay-os/workflows/_template.md` and
  `relay-os/workflows/_template.md` — demo the new field.
- `src/relay/resources/templates/relay-os/tasks/_template/ticket.md` —
  added `human:` / `agent:`.
- `example/relay-os/workflows/code/with-review.md` — demo the new field.
- Tests: `tests/test_commands.py`, `tests/test_create.py`,
  `tests/test_primitives.py` (190 pass).

## Out of scope (deferred to other tickets)

- Removing manual "edit assignee" instructions from existing skills →
  `rewire-code-with-review-...` ticket owns this.
- Updating the user's own `relay-os/workflows/code/with-review.md` and
  `dev/with-self-review.md` to declare role tokens — same rewire ticket.
- Validating that resolved nicknames exist in `relay.toml` (already
  partially covered by `relay validate`'s `unknown-assignee` check).

## Manual smoke-test

Verified end-to-end against a tmpdir relay repo:
- Scaffold with workflow whose step 1 declares `assignee: agent` →
  initial `assignee:` resolves to `claude1`.
- Bump into step 2 (`assignee: human`) → `assignee:` rewrites to
  `alice`, log/slack/echo include `→ assigned to alice`.
- Bump into step 3 (`assignee: owner`) when owner == current assignee →
  no `→ assigned to` suffix (no real handoff).
- Hand-delete `human:` from a ticket whose next step needs it → bump
  exits 2 with a clear "add `human: <nickname>` to ticket frontmatter"
  message.
