---
title: 01 Define prompt candidates and trial protocol
status: draft
owner: nicktoper
contexts:
  - coga-dev/microkernel/objectives
workflow: draft-for-human
---

## Description

Define complete candidate prompts and the comparison protocol that will test whether a new general assembler is better than the current one. The common model is a ticket carrying deterministic code or agent work; an agent prompt assembles a minimal base, requested skills, context blocks, relevant workflow material, and the ticket's intent and working state. This ticket produces reviewable candidates and an owner-approved protocol, without changing the production assembler or running the trials. It is done when the owner has approved the complete examples, applicability contract, measures, trial budget and decision rule, and the approved package is ready for ticket 02.

### Deliverable

Put complete baseline and candidate prompts beside this ticket, with the input fixtures and a manifest mapping each rendered block to its source and the explicit invocation fact that selected it. Record full source revisions. Compare the current form with one or more minimal-base alternatives; do not select the winner before trials. Keep the deliverable self-contained: later steps must not need the old launch-decomposition ticket or a chat transcript.

Inventory every production prompt builder and its transport. Include ordinary workflow steps, stateless agent procedures, guided authoring, megalaunch, recurring sessions, and the noninteractive `recurring_autofix.build_prompt` / `recurring_autofix.analyze_record` path. These last two are explicitly in scope. Shared assembly does not require routing noninteractive analysis through an interactive supervisor.

### Fair comparison

Define paired trials with the same task, initial repository state, semantic inputs, agent/version/model settings and budget for baseline and candidate. Hold attached context selection fixed within a pair so context trimming is not mistaken for an assembly gain. Specify bounded repetitions and order handling, expected and forbidden actions, the observations to collect, and how ambiguous results will be reported. Use representative cases rather than a full cross-product.

Cover the confirmed authoring conflict (execute/bump versus edit without advancing), stateless completion, ordinary workflow completion, attended versus queued conduct, an owner assist, script-to-agent handoff, skilled versus inline workflow instructions, and noninteractive autofix's structured-result contract. Combine cases where useful. A deterministic-only `ticket.py` path is a control: it must execute without composing a prompt or requiring an agent.

Any regression in completion, checkout, authority, required input or deterministic execution disqualifies a candidate. Among candidates that satisfy those gates, require a demonstrated improvement in instruction correctness, inspectability or size, with explicit tradeoffs and no unsupported performance claim. Agree what counts as an improvement before ticket 02 runs. A smaller prompt alone cannot compensate for lost required behavior. Permit the outcome that no candidate is better.

### What counts as demonstrated gain

For each case, write the expected observable result before executing either
form. For example, editing an existing paused ticket must change the requested
body while preserving its status and step and making no lifecycle advance;
noninteractive autofix must return its structured analysis without mutations
or interactive completion. Check fixture state and command traces against
those expectations rather than grading the agent's own claim of success.

Use a separate result for each dimension, not one weighted score:

| Dimension | Paired evidence |
| --- | --- |
| Correct behavior | Successful runs per case, forbidden actions, omissions and corrections needed; a fresh evaluator checks outcomes with candidate labels hidden where practical |
| Inspectability | A bounded task asking the agent to identify the effective source and the file to edit for a requested customization; compare against known ownership and count wrong answers or corrections |
| Prompt payload | Actual rendered bytes and estimated tokens for the same semantic inputs, with required blocks accounted for |
| Implementation simplicity | Named special cases, duplicate assembly paths and dependency paths removed in the prototype; confirm actual production reduction separately in ticket 03 |

Use fresh sessions and initial fixture state for each run. Fix repetitions,
order handling, the primary improvement sought and the minimum useful effect
with the owner before trials. Do not choose the winning dimension or threshold
after seeing results. Time and agent usage can be supplementary observations,
with their variance reported; they do not override correctness gates.

If both forms behave correctly, report that behavioral tie. A payload saving
then supports a payload claim, not a claim that the agent reasons better.
Likewise, a simpler prototype is not yet a production-code reduction. A small
pilot yields bounded evidence on these tasks; weak, mixed or ambiguous results
remain inconclusive rather than becoming a general performance claim.

### Minimal mechanism

Applicability is selected from explicit invocation facts with visible provenance. Do not infer procedure from command or skill names, workflow names or text equality. Specify which instructions remain shared base, which additions are invocation data, and which belong to ticket/skill/workflow files. Decide how a skilled step's workflow fragment and skill fit together without composing redundant or conflicting text.

No production changes, lifecycle redesign, new configuration language, generic plugin registry or permanent benchmark service belongs here.

## Context

Execution order and ownership are indexed in the sibling README. This is preparation for `v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly`; it does not prove that a candidate is better.

Read `src/coga/compose.py` (`compose_prompt_report`, `_step_layers`), `src/coga/commands/ticket.py` (`_authoring_ticket`, `_run_authoring_session`), `src/coga/launch.py` (`spawn_agent_session`) and `src/coga/recurring_autofix.py` (`build_prompt`, `analyze_record`, `build_analyze_command`). Current authoring removes the target step but still composes `prompt-ticket.md` for a TaskRef; this is a concrete contradictory-instruction baseline.

Cited rather than attached: `coga/prompt-composition`, at `src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md`, sections "Layer order", "What each layer reads", and "Blocker preamble versus authoring". Skills and contexts currently resolve local-first and compose whole; `_step_layers` currently selects skills OR inline instructions. Read the actual resolved files for each candidate, rather than assuming links load them.

Also cite rather than attach `coga/recurring/autofix` at
`src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md`,
"The loop". Its analyst is a one-shot, text-only call with no lifecycle and
no mutation authority. Unparseable replies surface as problems; analyst
failure must not change the sweep's exit code. Include these in the comparison
without giving the analyst interactive task-completion instructions.

Use the read-only `compose.compose_prompt_report` API for baseline measurement; do not use a launch that could prepare a checkout or publish state merely to inspect a prompt. Measure both the real authoring projection and normal workflow inputs. Trial prompts are examples, not instructions to this authoring session; keep them as attachments rather than operative text in this ticket's Description.

Workflow `draft-for-human` fits the protocol and prompt specimens as support material: agent prepares, owner makes the judgment, agent records the accepted result. Do not deliver a production runner or reusable harness here; if one proves necessary, scope its code and review explicitly before adding it.

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
