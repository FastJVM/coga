The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decision (2026-06-12, with nick)

Re-scoped from "pick option 1 or 2" to a coherence fix around one governing rule:

**A task ticket must carry a workflow everywhere EXCEPT while it is a `draft`.**
- `draft` = authoring grace period; workflow-less is valid there (concept-capture).
- `active`/`in_progress`/`done` require a workflow.
- Sole exception: machine-authored recurring (dream/cron) + retire tasks, which
  scaffold straight to `active` workflow-less and run their body as the prompt.

### The bug: validator is backwards
- Workflow-less `draft` → emits `missing-workflow` *warn* (validate.py:658-668).
  Nags the ALLOWED state forever (G3 noise — 43 hits on this repo now).
- Workflow-less `active` non-recurring/retire → emits NOTHING
  (validate.py:669 returns after draft-only check). The INVALID state (stuck,
  un-bumpable ticket) slips through silently.

Fix = flip it: stop warning on drafts; error on active workflow-less
(non-exception). Activation gate (mark.py:244) already enforces the boundary;
this just makes the validator agree.

## Comb map (from 3 Explore passes)

Validator: `_check_workflow_shape` validate.py ~L645-700.
  - missing-workflow warn: L658-668 (REMOVE)
  - bad-shape error (step set, wf null): L651-657 (KEEP)
  - missing-step error: L685-692 (KEEP)
Activation gate: mark_active mark.py:244 raises WorkflowMissing (KEEP, unchanged).
validate-drift classifier: run.py ~L232 missing-workflow→human-needed (REPLACE).
Sanctioned workflow-less-active (whitelist in new error):
  - recurring.py:603-623 — status=active, created_by=system, slug recurring-*
  - commands/retire.py:92-105 — status=active, created_by=retire, slug retire-*
Compose/automerge/ticket.current_step already null-safe — no change.

Docs/contexts asserting "workflow-less draft is valid" (KEEP, add symmetric half;
sync packaged copies under src/relay/resources/templates/):
  - relay/architecture SKILL.md ~L128, L136, L259
  - relay/cli SKILL.md ~L47-52, L70, L89, L114
  - bootstrap/ticket SKILL.md L23-26, L127-132 (reconcile internal contradiction)
  - README.md L279-283, L318, L409 (verify, not contexts but user-facing)

Drafts: 43 workflow-less drafts are VALID under the rule (drafts). No migration.
  Classification (informational only): 3 concept-capture, ~44 incomplete-real-work
  that *could* later get workflows (separate backlog hygiene), ~16 unclear/empty.
Sibling ticket document-workflow-less-concept-capture-drafts-as-s: premise now
  correct; fold its doc work into change (3) or close as covered.

## Decision (2026-06-12, with nick) — APPROACH CHANGE: give the exceptions a real workflow

Nick's call: instead of whitelisting recurring/retire as workflow-less-active
exceptions in the validator, **give them a real workflow too**. Then the rule
collapses to "everything past `draft` has a workflow, NO exceptions" — no
whitelist, no `created_by`-from-log signal (which isn't in frontmatter anyway),
no slug guessing (proven unreliable: `retire-standalone-...` is a human dev
ticket with a real workflow).

Key finding that forced this: `created_by` (system/retire) is written ONLY to
log.md's first line, never the ticket frontmatter. So the validator (which sees
only `(slug, Ticket)`) had no reliable signal to whitelist on. Nick's approach
sidesteps it entirely.

### Concrete plan (approved)
- **New workflow `direct/body`** — a *real* single-step workflow (nick: "a real
  one not a trivial one"), step `execute` → real skill `direct/body`. The skill
  is substantive (body-as-spec execution model, blackboard discipline, finish
  with `relay mark done`). Files: `relay-os/workflows/direct/body.md` +
  `relay-os/skills/direct/body/SKILL.md`, plus packaged copies under
  `src/relay/resources/templates/relay-os/`.
- **retire.py:95** — `workflow_name="direct/body"` (was None).
- **recurring.py:607** — `workflow_name=template.frontmatter.get("workflow") or
  "direct/body"` (defaults workflow-less templates like Dream). Digest etc. keep
  their own. Dream/retire bodies already end with "mark done" → no body edits.
- **validate.py `_check_workflow_shape`**:
  - REMOVE missing-workflow warn on drafts (L658-668).
  - ADD error when `status ∈ {active, in_progress}` and workflow is null. NO
    whitelist. (Leave `done` unflagged — harmless, avoids migrating historical
    `recurring-dream-2026-W24`.)
  - KEEP bad-shape + missing-step.
- **validate-drift run.py ~L232** — drop `missing-workflow→human-needed`; route
  new error kind to human-needed.
- **Docs/contexts** — state both halves of the rule; sync packaged copies.
- **Tests** — match existing suite.

Both validator+scaffold changes MUST ship together: scaffold runs the validator
(scaffold.py:174) and raises on errors, so erroring on workflow-less-active
would break recurring/retire scaffolding unless they already carry direct/body.

No live active/in_progress workflow-less tasks on disk → nothing newly errors.

## Dev
- branch: direct-body-workflow
- worktree: ../relay-direct-body-workflow
- pr: https://github.com/FastJVM/relay/pull/358
- ci: no checks configured on this repo (`gh pr checks` → "no checks reported").
  Local suite green: 719 passed, 1 skipped.

## Status
- Plan approved by nick. Building in worktree.

## Implementation progress (2026-06-12)
DONE (production code):
- `relay-os/workflows/direct/body.md` + `relay-os/skills/direct/body/SKILL.md`
  (real single-step workflow + substantive skill), packaged copies under
  `src/relay/resources/templates/relay-os/`.
- `retire.py`: workflow_name="direct/body".
- `recurring.py`: workflow_name = template workflow or "direct/body".
- `validate.py _check_workflow_shape`: removed draft warn; added
  `active-no-workflow` error for status in {active,in_progress,paused} + wf null.
  (done & draft exempt). Kept bad-shape + missing-step.
- packaged `validate-drift/run.py`: missing-workflow→active-no-workflow mapping
  (human-needed). NOTE: live `relay-os/bootstrap/` copy is gitignored/synced —
  re-sync propagates after merge.

DONE (tests, green): test_validate, test_recurring, test_retire. Added conftest
`seed_direct_body_workflow()` helper + seeded git_repo fixture's initial commit.

KEY CONSEQUENCE: `scaffold_task` self-validates and now RAISES on workflow-less
active/in_progress/paused. ~80 tests across 11 files created that (now-invalid)
shape as a shortcut → being updated to either carry a workflow (faithful: that's
what recurring/retire produce now) or construct on-disk when the test
specifically exercises the invalid shape. Production code unaffected.

DONE (docs): stated both halves of the rule + that recurring/retire are no
longer workflow-less exceptions, across:
- relay-os/contexts/relay/architecture/SKILL.md (+ packaged bootstrap copy)
- packaged relay/cli SKILL.md (--workflow optional in draft only; validator errors)
- packaged bootstrap/ticket SKILL.md (reconciled the "every ticket needs one"
  vs concept-capture contradiction: default to a workflow, but a deliberate
  workflow-less *draft* is valid and stays a draft until one is added)
- relay-os/contexts/relay/recurring/SKILL.md (direct/body for workflow-less templates)
- README.md (3 spots: mark-active gate, recurring scaffolding, retire)
Updated test_bootstrap_ticket_skill_template.py assertions to the reconciled prose.

SIBLING TICKET document-workflow-less-concept-capture-drafts-as-s: now COVERED
by these doc edits (both halves stated, concept-capture explicitly affirmed).
Recommend closing it as covered — flagging to nick, not touching its files here.

VERIFICATION: full suite `719 passed, 1 skipped`. Example fixture validates
clean (0 issues; no active-no-workflow). Example has no recurring/retire so
direct/body not needed there.

RE-SYNC REMINDER: the packaged validate-drift run.py + bootstrap contexts/skills
edits land in the gitignored live `relay-os/bootstrap/` copy only after a
template re-sync (post-merge). Live behavior in THIS repo's Dream runs picks
them up then.

STATUS: implement step complete — committing on branch `direct-body-workflow`,
then `relay bump`. (open-pr + self-qa are later steps.)

## Peer Review (2026-06-12, codex)

Ran `codex review --base main` from feature worktree
`../relay-direct-body-workflow`.

Finding:
- P1: `direct/body` is now required by recurring/retire, but existing repos
  updated via `relay init --update` would not receive
  `workflows/direct/body.md` or `skills/direct/body/SKILL.md`. Dream/recurring
  and retire would fail after upgrade until those files were manually copied.

Fix applied:
- Added `workflows/direct/body.md` to `VENDORED_WORKFLOW_TEMPLATES`.
- Added a narrow `VENDORED_SKILL_TEMPLATES` path for
  `skills/direct/body/SKILL.md` and refresh it during `init --update`.
- Extended init and packaging tests so fresh/update/package paths cover the
  new required workflow and skill.

Verification:
- `python -m pytest tests/test_init.py::test_init_update_refreshes_vendored_recurring_template tests/test_init.py::test_init_update_refreshes_cli_and_underscore_templates tests/test_packaging.py -q` →
  `4 passed, 1 skipped`.
- `python -m pytest -q` → `719 passed, 1 skipped`.
- `git diff --check` clean.
