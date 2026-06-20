# remove-relay-draft — blackboard

## Plan (approved 2026-06-20, full-sweep scope)

Remove the `relay draft` command. `create` survives as the quick-stub path;
`ticket` is the create-or-edit authoring entry. Human chose the **full sweep**:
code + tests + the complete doc/context surface.

### Code (production)
- `src/relay/cli.py` — drop `app.command("draft")(create_cmd.draft)` and
  `"draft"` from `_BUILTIN_COMMANDS`. Leave `create` + the `_LEGACY_ALIASES`
  `create → launch bootstrap/ticket` entry alone.
- `src/relay/commands/create.py` — delete the `draft()` function; rewrite the
  module docstring (now "for `relay create`") and the `create()` docstring
  (no longer "compatibility spelling for `relay draft`" — it's the primary).

### Functional dependency the ticket missed
- `bootstrap/project` skill instructs agents to run `relay draft "<title>"`
  to scaffold each ticket (`.../skills/bootstrap/project/SKILL.md:95`, plus
  `commands/project.py` docstrings). Switch these to `relay create` or the
  project flow breaks at runtime. (live + packaged template copies)

### Tests
- `tests/test_create.py` — `["draft", ...]` invocations + section header →
  `create`; keep coverage equivalent (drop the now-redundant draft/create
  duplication sensibly, but keep the workflow-less + sync assertions).
- `tests/test_git.py` (7×), `tests/test_init.py` — `["draft", ...]` → `["create", ...]`.
- `tests/test_bootstrap_ticket_skill_template.py` — assertion pins the
  "Raw draft" wording; update to match the rewritten skill line.

### Docs / contexts (full sweep — both live `relay-os/` and `relay-os/bootstrap/`
### template trees, kept in sync per CLAUDE.md)
- `README.md` — status-diagram bullet (L179-181), compat-spelling note
  (L199-201), the `### relay draft "<title>"` section (L263-278).
- `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` (+ packaged copy,
  currently identical) — Step 1 "Raw draft" + L43 empty-interview line.
- `relay-os/contexts/relay/cli/SKILL.md` ... actually CLI ref lives only under
  `relay-os/bootstrap/contexts/relay/cli/SKILL.md` — the whole `## relay draft`
  section (L65-87), L120 project scaffold mention, L591 quick-ref.
- `relay-os/contexts/relay/architecture/SKILL.md` + bootstrap copy (L131, L147).
- `relay-os/contexts/relay/sync/SKILL.md` + bootstrap copy (L57-58, L289-290).
- `relay-os/contexts/relay/current-direction/SKILL.md` (L179-180, L213).
- `relay-os/bootstrap/orient/ticket.md` (L33), `relay-os/bootstrap/ticket/ticket.md` (L13,16).
- `relay-os/recurring/digest/ticket.md` + packaged copy (L20 lifecycle-chatter list).

NOT touched: historical `relay-os/tasks/**` tickets/blackboards (records);
`.relay/` and `.venv/` vendored copies; `relay.toml` `default_status = "draft"`
(that's the ticket *status* value, unrelated to the command).

### Verify
- `python -m pytest`
- `relay validate --json` against example fixture if validation behavior shifts
  (it shouldn't — no schema change).
- Confirm `relay draft` now errors as unknown; `relay create` still works.

## Dev
branch: remove-relay-draft
worktree: /Users/zach2179/Desktop/relay-remove-draft

## What changed (implement step — committed, not pushed)

Full sweep done. 26 files. `relay draft` command removed; `relay create` is
now the sole raw-create command. Key points:

- **Code:** unregistered `draft` in `cli.py` (+ dropped from
  `_BUILTIN_COMMANDS`), deleted `draft()` in `commands/create.py`, rewrote its
  module + `create()` docstrings.
- **Functional fix the ticket missed:** `bootstrap/project` skill scaffolds
  each ticket by running the command (`.../skills/bootstrap/project/SKILL.md`)
  and `project.py` docstrings described it — both now point at `relay create`,
  so `relay project` keeps working.
- **Docs/contexts swept** (live `relay-os/` + packaged `src/.../templates/`):
  README, docs/design, docs/vision, relay/{cli,architecture,sync,
  current-direction} contexts, base prompt, orient + ticket shims, `_template`
  ticket, digest ticket. Preserved existing "scaffolds" wording (per the
  avoid-"scaffolding"-in-new-prose preference, don't rename old mentions).
- **Tests:** swapped `["draft", ...]` → `["create", ...]` in test_git/test_init;
  deleted the two redundant draft-specific tests in test_create (their `create`
  twins already exist); fixed the skill-template + project-comment assertions.

### Verification
- `python -m pytest` → **820 passed, 1 skipped** (pre-existing skip). Ran with
  `PYTHONPATH=<worktree>/src` so pytest exercises the worktree, not the
  editable install pinned to the primary checkout.
- Typer surface: `relay --help` shows no `draft` row; `relay draft x` exits 2
  (unknown command); `relay create --help` exits 0.

### Adjacent finding (NOT fixed here — candidate follow-up)
Pre-existing doc drift on whether the raw-create command posts `✨`:
`relay/sync` context lists it under "no notification post" (silent), while
`relay/cli` + `relay/current-direction` say it posts `✨` when a channel is
selected. `create_draft()` itself only calls `git.sync_task_state`. I kept the
existing per-file wording (rename only) rather than resolve the contradiction —
out of scope for this removal.

### Note for reviewer
The materialized `relay-os/bootstrap/` tree is gitignored (rebuilt by
`relay init --update`), so its draft references were edited in the packaged
`src/relay/resources/templates/...` source of truth, not the live copies.

## Peer review (codex, 2026-06-20)

Ran `codex review --base main` from `/Users/zach2179/Desktop/relay-remove-draft`.
The review reported two findings:

- P2: `relay-os/contexts/relay/current-direction/SKILL.md` says raw create
  posts `✨`, while implementation/tests/sync context currently describe raw
  create as silent. Human clarified during review: **`relay create` does post
  to Slack**. I did not apply the review's proposed contract change to call it
  silent; treat the underlying doc/test/code mismatch as pre-existing drift /
  follow-up outside this removal.
- P3: packaged `_template/ticket.md` was updated, but the live
  `relay-os/tasks/_template/ticket.md` still mentioned `relay draft`. Fixed.

Additional review sweep found live `relay-os/tasks/marketing/README.md` still
using `relay draft` in current instructions for moving new marketing tickets.
Fixed that to `relay create`.

### Peer-review verification

- Applied fixes in feature worktree and committed:
  `755111ad peer-review: apply review findings`.
- `python -m pytest` from `/Users/zach2179/Desktop/relay-remove-draft` →
  **820 passed, 1 skipped**.
