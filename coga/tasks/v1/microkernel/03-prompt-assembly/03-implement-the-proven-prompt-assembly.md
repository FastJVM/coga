---
title: 03 Implement the proven prompt assembly
status: blocked
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga-dev/codebase/gotchas
- coga-dev/testing
- coga-dev/microkernel
- coga-dev/project-stage
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 1 (design)
agent: claude
---

## Description

Implement the general prompt assembly form only after the owner accepts paired evidence that it improves on the current form. The ticket is the common unit of deterministic code and agent work. Agent prompts assemble the selected minimal base, requested skills, relevant context blocks and workflow material, ticket intent/state and explicit invocation additions through one inspectable composition mechanism. Done means every in-scope production prompt builder uses the selected contract, its behavior and provenance match the demonstrated form, real duplicate or command-specific assembly paths have been removed, and the required regressions, documentation and review receipts are complete.

### Positive experimental gate

Do not activate or begin this ticket until `v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly` has an owner-recorded positive selection, not merely status `done`. A negative or inconclusive comparison leaves this draft unlaunched. During design, copy the selected complete prompts, comparison result, applicability contract, required base additions and limitations into this ticket or its attachments. Do not depend on predecessor tickets remaining live. A material change to the selected form requires renewed comparison and owner review before replacement.

### Scope and boundary

Migrate ordinary workflow prompts, stateless agent procedures, guided authoring, megalaunch, recurring sessions AND noninteractive `recurring_autofix.build_prompt` / `recurring_autofix.analyze_record`. Preserve the latter's structured-output/parse, transport, secret and failure contracts; sharing composition does not require an interactive supervisor. Migrate real callers together with the shared assembly seam. Do not introduce a second public launch API, forwarding re-exports or a command-name allowlist.

The assembler receives explicit invocation facts and resolves declared file references. It must not guess procedure from command/skill/workflow names or compare instruction text to shipped copies. Make each composed block's effective source and selection reason inspectable. Preserve local-first resolution and refusal of required missing or unreadable inputs. Consume the approved skilled/inline workflow rule; do not blindly compose both.

Authoring must not instruct execution or advancement of the target ticket. Stateless agent work must not acquire a task lifecycle. Stateful work must retain its applicable completion and checkout guarantees. Deterministic-only `ticket.py` execution remains code, with no prompt or configured-agent requirement; exit zero still never advances a stateful step. Invocation conduct and runtime checkout notices must remain truthful.

### Verification and simplification

Exercise every migrated production caller through composition and integration regressions, including noninteractive analysis. Preserve environment isolation, secrets/redaction, command representability, completion authority, publication order, checkout returns, assist receipts, recurring leases and released launch claims wherever the changed boundary touches them. Report the whole-system production-code and dependency-path delta at named revisions, separating relocation from deletion/deduplication and tests/docs from production code.

Update `coga/prompt-composition`, changed prompt resources and instruction owners, affected launch/script/checkout/publication contracts, autofix's owning procedure, and the local source map in the same implementation PR. An extraction earns its place through the selected contract and real migrated consumers. The separate launch-decomposition ticket owns the stateless invocation/publication and shared execution contracts; consume them without bundling their full refactor into this ticket.

## Context

This draft implements evidence selected in the numbered group's ticket 02; it does not choose the winning prompt form. The owner reviews its design before code through `code/design-then-implement`. Leave the draft workflow as a reference until activation; do not copy the old launch ticket's paused workflow position into this new scope.

Implementation sources: `src/coga/compose.py` (`compose_prompt_report`, `_step_layers`), `src/coga/commands/ticket.py` (`_authoring_ticket`, `_run_authoring_session`), `src/coga/launch.py` (`spawn_agent_session`, `_LaunchInvocation`), both megalaunch modules, `src/coga/recurring_runner.py`, and `src/coga/recurring_autofix.py` (`build_prompt`, `analyze_record`, `build_analyze_command`). Inventory actual callers again at implementation time.

Editing targets are cited rather than attached. Read `src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md` ("Layer order", "What each layer reads", "Blocker preamble versus authoring"); `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md` ("Order inside one call", "Per-caller parameters", "Large prompts", "The supervisor"); and `docs/contexts/coga-dev/internals/state-publication/SKILL.md` ("Invariants", "The end-of-command sweep", "Guided-authoring finalization") plus "Ordinary managed startup" in its `publish/SKILL.md` leaf. `launch._LaunchInvocation._publish_startup` groups ordinary startup before checkout entry; `authoring.finalize_authored` validates and publishes the required authored set together.

User contract owners resolve under `src/coga/resources/templates/coga/bootstrap/contexts/`: `coga/launch` ("Phases and routing", "Agent preflight order", "The step chain"), `coga/script-tickets` ("One deterministic phase", "Chaining", "COGA_TASK_* contract"), `coga/checkouts` ("Start, work, end"), and `coga/state-publication` ("When Coga publishes", "Prepared ticket transactions"). The source map is `docs/contexts/coga-dev/codebase/SKILL.md`, "Source map". Read and update those owners where the actual change affects their contract.

The autofix owner is also cited rather than attached:
`src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md`,
"The loop". Preserve its one-shot, text-only, non-mutating analyst contract,
surfacing of unparseable replies and independence from the sweep's exit code.
The shared assembly must not inject an interactive lifecycle into that path.

The checkout-policy declaration sibling owns checkout selection and compatibility; this ticket owns no competing policy table. The paused launch-decomposition ticket remains a distinct delivery scope, not an umbrella. Decide any narrower invocation/session interface with that ticket's owner before depending on it, without making exploratory prompt trials depend on unfinished runtime work.

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

## Gate status (2026-11-13, design session)

- Launched without a positive selection: ticket 02 ended with C1 disqualified (owner, 2026-11-13). No spec written.
- Owner clarified that "better" means better output (PRs, documents); 02 measured rule compliance only, never output quality.
- New prerequisite drafted: `v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality` (`draft-for-human`, owner's blinded judgment as primary measure, 02's gates kept hard).
- PR #1234's ruling should state that 02 did not measure output quality; owner to comment there and run an assist on that ticket.
- Parked by owner request until 04 records a positive selection.

---

## Blockers

- [ ] [2026-11-13 23:26] [agent:claude] id=20261113T232634 Parked at owner request: no positive selection. Waiting on v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality to record a positive output-quality selection before design can start.
