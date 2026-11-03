---
title: 02 Repo cutover to package-owned definitions
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
launch_generation: pending:9a9e74e9-1618-4aeb-bea7-c0d8313889ef
---

## Description

Stage B of the package-owned definitions split (see the group README for
the goal and full design). Migrate this repo onto the package-owned
definitions that stage A
(`v1/package-definitions/01-runtime-compatibility-for-package-owned-definit`)
made resolvable, remove the live copies, and enforce strict single-source
ownership.

### Dependency

Do not start until
`v1/package-definitions/01-runtime-compatibility-for-package-owned-definit`
is merged to control and every participating checkout's CLI is A or newer. If it is not, `coga block` naming that exact
ref. Use A's recorded legacy removal inventory and transitional-check
allowances as the starting point; recompute the inventory on current main.

### Stage B scope

**B — repo migration, removal, and strict ownership.** Reconcile with merged A
and verify the CLI in every participating checkout uses A or newer. During a
short coordinated migration window, quiesce state writers/recurring sessions,
back up local definitions plus complete blackboards/attachments, and inventory
active, parked, deleted and customized jobs. Compare definitions and sibling
files separately from mutable blackboards, using a known prior seed/version
when needed. A changed file is not presumed disposable merely because its
name matches a bundled resource. Ambiguity retains an intentional local
override until the owner decides; record the reason, never silently delete it.

Publish selection before removing its dependent definitions (it changes
nothing while equivalent locals still exist). For each approved bundled
parent, replace the definition with a carrier preserving the entire saved
blackboard byte-for-byte and remove only its reviewed definition siblings.
Keep nontrivial state even for jobs with no declared `state_keys`; retain
worklists, the shared log, clone ledgers, frozen periods and custom jobs.
Read state from freshly reconciled control, never from the package's zero
seed. A parent with no useful state can have no local ticket until first use.
Do not leave a carrier plus orphaned definition siblings at an intermediate
publication: prepare that parent's conversion as one guarded state change.

Live-copy deletions/conversions are normal Coga state and may reach control
before B's source/test commit. Use the ordinary publication path and inspect
its receipt; do not exclude paths, suppress guards, or commit the packaged
side through a state command. `coga run publish-state` without path operands
can sweep deletions; named operands must be existing files, so verify removed
paths separately in the resulting control tree. Reconcile any publication
conflict without discarding newer state. Check control with A's runtime and
packaging tests after selection, after the first conversion/deletion, and
after the full removal, before enabling B's strict test policy.

B replaces temporary twin equality with an inverse check: fail on every
unapproved live counterpart, even byte-identical ones. Keep explicit reasons
for scaffolds/state carriers and any reviewed override, require those reasons
to describe real current files, and reject new accidental package/live copies.
Do not preserve phone-home's full definition merely for its counters. Land
B's final ownership tests/docs after the removals are safe; no intermediate
control commit may depend on unmerged B runtime support.

The operator migration lives with the shipped init/recurring contracts, with
a linked release-note entry. It must work on customized existing repos and
rehearse a rollback: keep writers quiesced, retain current state/ledgers,
restore definitions from verified backups if needed, and restore selection
without replaying periods. Require A-or-newer clients after migration; old
clients cannot interpret carriers. Drain or defer migration of a job whose
frozen custom instructions still require removed definition attachments;
never rewrite frozen workflows or discard an unfinished period just to finish
the migration. Retained custom attachments are documented overrides, not
silent exceptions. Automatic seed-recognition/migration tooling is not
required.

### Acceptance criteria

- [ ] This repo has no undeclared live counterparts of package resources;
  the inverse check fails on any unapproved live copy, even a byte-identical
  one, and on a deleted required fallback. All `coga-dev/` files remain
  local-only.
- [ ] The compatibility stage is merged and in use on control before any
  dependent removal is published. A regression exercises the first live-copy
  deletion/state conversion from a feature checkout against that control
  version; control's package, navigation and representative runtime checks
  stay green before the cutover PR merges.
- [ ] A separate final-state regression edits packaged content on a feature
  branch, both dirty and committed, then runs a mutating CLI exit sweep.
  Control's packaged bytes stay unchanged while ordinary local task,
  recurring-state and repo-context edits publish; control's packaging checks
  pass. No publication guard, root membership or provenance rule is weakened.
- [ ] The documented operator migration is rehearsed on this repo, including
  rollback. Old seeds, customized overrides, parked jobs, saved state
  (including phone-home's complete `period_state`), worklists, clone ledgers,
  frozen periods, and repo-only jobs (`usage-report`, `upstream-coga`) and
  attachments are preserved. The temporary `rollout/trim-log/coga/`
  definition copies and their staged-twin assertions are removed.
- [ ] Build the verification wheel from a pristine disposable clone and run
  installed-artifact smoke tests outside the editable source path. Cover all
  resource types and all nine parents with outward effects stubbed; compare
  package-resource bytes before/after and exercise read-only resources.
- [ ] The owning topics, `AGENTS.md`, indexes, shipped instructions and local
  development links describe the new ownership and navigation. Context-link
  validation reads the actual package tree. The relevant tests, seeded-repo
  validation and full suite pass after reconciliation with current main.

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
