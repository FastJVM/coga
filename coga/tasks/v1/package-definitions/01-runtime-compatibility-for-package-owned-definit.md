---
title: 01 Runtime compatibility for package-owned definitions
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
launch_generation: pending:6cb4cd49-aa69-4396-9773-a7c158e31722
---

## Description

Stage A of the package-owned definitions split (see the group README for
the goal and full design). Land runtime compatibility so `src/coga/resources/`
can become the single committed source of shipped definitions, while this
repo keeps every existing live definition. Stage B
(`v1/package-definitions/02-repo-cutover-to-package-owned-definitions`)
performs the removals and depends on this ticket being merged and in use.

### Stage A scope

**A — runtime compatibility and deletion-tolerant checks.** Land the catalog,
selection/carrier support, dependency fallbacks, init changes and reader/writer
updates first. Keep this repo's existing live definitions during this stage.
Move package seed refs as in README section 1 while keeping their live resolutions valid.
Update owning topics and links to their eventual package owners now. Commit
topic, skill and workflow changes that belong to A with its source before
any sweeping command, following the existing checkout contract.

**Pre-A publication boundary (evaluator P1 disposition):** keep this repo's
live recurring definitions and every definition sibling unchanged throughout
A, including scripts and runbooks. Ordinary mutable blackboard/worklist
updates remain ordinary published state. Committing a live recurring edit
does not protect it from the sweep. Author required instruction/link changes
only in the packaged recurring files during A; enumerate each resulting
legacy-definition difference, its old bytes and reason in A's transitional
checks. Phone-home's separate comparison must distinguish these reviewed
definition differences from its preserved complete mutable state. Do not
use a blanket recurring-directory exemption. B removes or converts these
legacy files only after A is merged and installed; it does not backport A's
new instructions into live parents before that boundary.

Update Dream's scans and hard-coded live-path consumers before deleting their
inputs. For any change inside a live recurring definition or attachment,
the packaged update takes effect after cutover; A's compatibility must still
support the unchanged live version. No source-root, provenance or publication
guard changes are part of this boundary.

A's packaging policy is deliberately transitional: package resources are
required; legacy counterparts are optional and, when present as definitions,
still checked for approved equality/divergence. Recognized state carriers are
validated as state. Remove the twin-count floor, mandatory canonical-context
existence, and phone-home's mandatory live-definition assertion; retain
required resources, seed-zero checks and the local-only audience prohibition.
Record the exact legacy removal inventory so this temporary allowance cannot
silently grow. Navigation resolves actual package paths and remains valid
with any removable counterpart absent. Tests/harnesses that open live skills,
workflows or parents must also tolerate removal. These checks must actually
be on control, not merely in the later branch.

### Acceptance criteria

- [ ] Shipped contexts, skills and their attachments, workflows, bootstrap
  tickets, recurring definitions/scripts/runbooks, and prompt resources each
  have one committed package owner, with only one packaged definition per
  logical ref. Required-resource checks prevent deleting both copies from
  becoming a vacuous pass. All `coga-dev/` files remain local-only. (Stage B
  enforces that this repo has no undeclared live counterparts.)
- [ ] Every removed live definition resolves through the installed package in
  both editable and fresh-wheel installations. Local overrides win by ref;
  malformed/unreadable overrides fail visibly without selecting stock text.
  Agent skill discovery and workflow freezing use the same effective refs.
- [ ] All nine currently bundled parents (`autoclose-merged`, `branch-sweep`,
  `blocker-reminders`, `dream`, `phone-home`, `skill-update`,
  `address-pr-comments`, `resolve-conflicts`, `trim-log`) work without local definition
  tickets. Listing/status, validation, due scans, clone scans and named launch
  agree on selection, definition source and dependencies.
- [ ] Package-backed recurring runs read/write only repo-owned parent state,
  worklists, period tasks and shared log, or clone-local ledgers/logs. Repeated
  and interleaved updates preserve unrelated blackboard keys, phone-home's
  complete `period_state`, snapshots, retirement records and CAS safeguards.
  A state-only local directory/file never shadows a package definition.
- [ ] Override boundaries include scripts and supporting files: no silent
  mixture of a local job body with a packaged `ticket.py`. Repo-specific jobs
  and attachments survive. Existing frozen workflows, period bodies,
  delegates and copied scripts are not regenerated during upgrade/migration;
  old state snapshots and legitimate unfinished periods remain usable.
- [ ] Existing repos with no new selection file retain local-only recurring
  activation. Deleted or `_name`-parked jobs do not reappear. Explicitly
  disabled jobs stay disabled under sweeps, `--force` and named recurring
  launch. Adding a bundled job in a package upgrade does not enable it in an
  existing repo. Fresh-init defaults follow the owner decision at review.
- [ ] Fresh init copies only approved scaffolds and real initial state. It
  creates no reusable shipped definitions in live roots. Clone setup and
  package upgrades never overwrite customization, reseed state, or recreate
  removed definitions. A documented operator migration and rollback runbook
  (rehearsed on this repo by stage B) preserves old seeds, customized
  overrides, parked jobs and saved state.
- [ ] Before compatibility merges, its ordinary handoff sweep leaves live
  recurring definitions and their supporting files unchanged on pre-A
  control while publishing ordinary ticket/state updates. Run pre-A
  control's own packaging, navigation and representative runtime checks;
  stage A's imports or relaxed checks cannot stand in for this evidence.
- [ ] Build the verification wheel from a pristine disposable clone and run
  installed-artifact smoke tests outside the editable source path. Cover all
  resource types and all nine parents with outward effects stubbed; compare
  package-resource bytes before/after and exercise read-only resources.
- [ ] The owning topics, `AGENTS.md`, indexes, shipped instructions and local
  development links describe the new ownership and navigation. Context-link
  validation reads the actual package tree. The relevant tests, seeded-repo
  validation and full suite pass after reconciliation with current main.
- [ ] This repo's live recurring definitions, their siblings and all other
  live counterparts remain present and valid on control after merge; the
  exact legacy removal inventory and every enumerated legacy-definition
  difference are recorded in the transitional checks for stage B.

## Context

### Read first

The shared design contract and verified source context live in
[the group README](README.md) (`coga/tasks/v1/package-definitions/README.md`):
"Shared design" sections 1–4 and 6, "Out of scope", and "Context". Read it
in full before planning; it is not composed into this prompt. Update the
README's design in the same PR when this stage changes the contract.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
