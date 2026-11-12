---
title: Make packaged behavior discoverable and editable
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
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
step: 1 (design)
contexts:
  - coga-dev/microkernel/objectives
  - coga-dev/principles
---

## Description

Provide one discoverable route from a command to the files that define its
behavior, and to a complete editable repository copy of the selected behavior.
This fills the accessibility gap in the original microkernel group: local-first
resolution exists, but users must still know package paths and follow Python
shims manually. New draft proposed by the refresh; owner scope review precedes
implementation.

### Objectives advanced

Hackability: users and their agents can find and change shipped behavior even
with a read-only installation. Ticket ownership: the path reaches the actual
script or composed instructions. Simplification: one resolver-based inspection
and copy path replaces separate package-location/copy recipes per capability.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12).

1. The gap exists: bundled workflows/skills/contexts/command tickets and
   recurring definitions are package-owned, while this source repo has no
   live mirror of them for a contributor to discover by browsing `coga/`.
2. `paths.resolve_workflow_path`, `resolve_skill_path`, `resolve_context_path`,
   resource override helpers, `tasks.resolve_bootstrap`, and the recurring
   catalog supply the existing selection rules. `show` displays tickets;
   it is not a unified source/fork command. `skill status` is skill-specific.
3. The objective and first acceptance case are attached. The wheel's current
   fork/upgrade rules are owned by `coga/edge-code`; no missing retired task
   is needed to recover them.
4. Wheel-owned edge delivery shipped in `bc46823c4` and package-aware recurring
   selection in `d0f4e2c6f`. `phone-home` and `trim-log` use shims importing
   `coga_edge`. Keep that distribution support; add access to the effective
   definition and its real implementation.

### Proposed user path

Prefer a stateless script command ticket exposed by an alias, with an inspect
operation and an explicit copy operation. The design step chooses the spelling;
it does not require a new permanent Typer head or plugin registry.

Inspection accepts a command/alias or a typed definition reference, resolves
through the same helpers execution uses, and reports the selected local or
package source, relevant workflow/skill/script references and the local
override destination. Show which parts of a live ticket are frozen versus
resolved from current definitions. Inspect without running jobs, importing
arbitrary user implementations, invoking an agent, requiring a TTY or publishing
dirty state. A non-ticket kernel primitive should be identified honestly rather
than reported as an editable ticket.

Copying is explicit and bounded to the selected definition plus the necessary
siblings/references identified for that customization. Preserve an existing
local override; report conflicts instead of merging or overwriting it. Reuse
configured roots and the existing whole-directory rules for bootstrap tickets,
skills and recurring definitions. Preserve recurring parent state carriers and
their blackboards when making a complete definition fork; never leave only a
script beside a state-only carrier.

When a selected script is only an import shim, make the owning implementation
available as a full local fork, with the shared-core compatibility it requires.
Start with the shipped, inspectable edge shapes; if a dependency cannot be
copied completely, name it and refuse to claim a complete fork. Do not execute
a job or recursively load plugins to discover its source.

Package defaults continue to have one committed owner. A local fork is an
intentional user-owned override and stops following that default's updates.
Explain how to identify that state and return to the stock definition. This
ticket does not introduce automatic merging of customized code, rewrite running
periods, or copy the entire package into every repository at init.

### Acceptance and reduction evidence

- [ ] From a pristine installed wheel outside the source checkout, a user can
      find and copy the peer-review workflow/instructions, customize it for one
      agent and run it with the checkout-policy ticket's explicit declaration.
- [ ] With the installation directory read-only, fork a shipped script-backed
      behavior and change its actual implementation in repo-local files; prove
      resolution uses it and the installed bytes remain unchanged.
- [ ] Cover local precedence, broken overrides, custom contexts roots, aliases,
      referenced skills, complete bootstrap/recurring siblings and state carriers.
- [ ] Inspection/help are read-only and preserve streams/exits. Copy refuses
      conflicting local files and never overwrites running/frozen task state.
- [ ] Updates affect package defaults while retaining intentional forks;
      verify the documented return-to-default procedure in fixtures.
- [ ] Reuse existing resolution code and replace redundant lookup/copy
      instructions; report the code added versus the paths actually removed.
- [ ] Update package-owned user customization guidance and packaging tests,
      including read-only wheel and native Windows receipts. Never recreate
      unapproved live definition mirrors in Coga's own source repo.

## Context

Read `coga-dev/microkernel/objectives`, `coga-dev/packaging` and
`coga-dev/testing`. User owners under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/` are
`context-layout`, `extension-model`, `edge-code` (including its upgrade
procedure), `workflows`, `script-tickets` and `recurring/templates`.

The launch sibling owns the generic stateless read/write dispatch distinction.
The checkout-policy sibling owns workflow declaration; the end-to-end peer-review
case joins these two capabilities. Recipe moves consume this forkability
requirement but own their job implementations and upgrade caller reconciliation.

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
