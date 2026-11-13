---
title: 01 Define prompt candidates and trial protocol
status: in_progress
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 3 (report-to-coga)
agent: claude
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

### Review package

The draft support package is indexed in [README.md](README.md), with [protocol](protocol.md), [applicability](applicability.md), [production inventory](inventory.md), complete prompts and fixtures, block/source manifests and [rendered measurements](measurements.md). The specimens are attachments, not operative instructions for this session. The owner decision record is still unapproved; ticket 02 must not run until the owner approves the complete package and execution pins.

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

## Draft package

Prepared README.md, protocol.md, applicability.md, inventory.md, measurements.md,
22 complete baseline/C1 prompts for eleven agent cases, twelve case fixtures
including a no-prompt deterministic control, resolved source snapshots,
manifest.json and sources.json. No production assembler changes or trials.

Source baseline: c3a86e7f0402d571da02df9d6f91b36b0844905a (full pins/blobs
and attachment SHA-256 hashes in sources.json). Actual compose_prompt_report
and actual _authoring_ticket projection generated ordinary/authoring baselines;
recurring_autofix.build_prompt generated analyst baselines. One-off rendering
and auditing code stayed in /tmp; no reusable harness was delivered.

The human authorized drafting one candidate, two repetitions and instruction
correctness as primary. Complete owner approval is recorded below.
Approved limits, counterbalanced order, predeclared outcomes, hard gates,
separate dimensions and negative/inconclusive decisions are in protocol.md.
Candidate retains whole selected contexts/skills and current skill-OR-inline
selection. Autofix retains a noninteractive, structured, read-only call.

Render-only evidence: baseline 111,859 bytes; C1 108,052 bytes (3.40% smaller,
below the proposed 15% payload threshold). Analysis cases grow. No behavioral,
reasoning or production-simplicity gain is established; no winner selected.

## Verification

All 22 hashes and block byte maps checked; every baseline independently
reproduced with read-only production APIs. Resolved source snapshots checked.
Linux suite receipt: production base c3a86e7f0402d571da02df9d6f91b36b0844905a,
working tree changed only this ticket and its review attachments; Pop!_OS 24.04
LTS, Linux 7.2.15-76070215-generic, Python 3.12.12. Exact command:
`env TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest --basetemp=/home/n/Code/coga-prompt-protocol-pytest-667707cc -q`
-> 4853 passed, 33 skipped in 828.16s (exit 0). Native Windows and Python 3.11
floor verification were not run; this is no release receipt.

Scoped read-only validation:
`env TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.validate --json --task v1/microkernel/03-prompt-assembly/01-define-prompt-candidates-and-trial-protocol`
-> ok_count 1, no issues. `git diff --check` passed.

Reviewed attachment-tree SHA-256:
`f5ee59e2cd8ebf2d88f17f5ea9623b4699bee2cad3b1fa5a6cc34cec5e10dbbc`.
Its exact counting/hash method and per-file digests are in sources.json.
This excludes the live ticket and sources.json itself, so lifecycle publication
can change this ticket without changing the reviewed specimen package.

## Owner handoff

Owner approved the existing complete review package and its 60-session ceiling,
and explicitly authorized advancing this owner-held step. Acceptance includes
the complete examples, applicability contract, cases and expected outcomes,
paired controls/order, session limits and reserve, primary/secondary thresholds,
hard gates, stop rules and separate-dimension reporting in protocol.md.
Accepted attachment-tree SHA-256:
`f5ee59e2cd8ebf2d88f17f5ea9623b4699bee2cad3b1fa5a6cc34cec5e10dbbc`.
All 79 attachment hashes and that tree hash were reverified on control revision
`130bb1c2c7c28f819289c89c8f0ce3f917f5d55a`; the specimen package is unchanged.

Owner clarification: keep two repetitions per arm/case; no
expanded reliability study is needed at this stage. The owner will judge the
results at the end. Report the observed outcomes and their limits without
claiming broader reliability. Correctness gates remain in force.

Owner selected Codex, Sol, medium reasoning for both forms. Local model-cache
resolution: `gpt-6.1-sol`, with `medium` listed as supported. Observed CLI:
`codex-cli 0.167.2`; resolved executable:
`/home/n/.codex/packages/standalone/releases/0.167.2-x86_64-unknown-linux-musl/bin/codex`;
SHA-256: `a9672d0fa0dd8fcf8cad136fa0d056b914bc046f5ac3d78f4a5cf390655af56b`.
No model session was started. Recheck these pins before trials; the local
model identifier does not establish an immutable provider model version.

For report-to-coga: carry this explicit approval into the package decision
record, preserve the accepted specimens, and record any resulting metadata-only
hash changes separately. Capture remaining execution-environment/transport pins
before ticket 02 starts, under the approved model, settings and limits. Approval
does not select C1 or authorize production migration. No trials ran here.
No branch or PR exists: this step only edits routine ticket state on main,
under launch's return ownership. Attachment hashes and git diff --check passed;
the scoped read-only validation command above returned ok_count 1, no issues.
the full Linux receipt above remains the preparation receipt, not a new run.
