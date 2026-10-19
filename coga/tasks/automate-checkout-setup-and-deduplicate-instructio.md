---
title: Automate checkout setup and deduplicate instructions
status: draft
owner: nicktoper
contexts:
  - coga/knowledge
  - coga/extension-model
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
---

## Description

Move repeated checkout mechanics into shared code used by ticket launch and ad-hoc chat, and remove the duplicated Git recipes in the same change. Keep a complete explanation for humans and agents in the owning checkout documentation.

The current implementation already prepares current control and safely returns ordinary launches and direct chat to control. The remaining branch setup, record publication, and agent handoff instructions are repeated across the base prompt, checkout contexts, implementation/review skills, and code/docs workflows. Implement the missing automation and then shorten those instructions.

### Agreed direction

- Use the ticket's existing workflow and current step to select checkout behavior. Do not introduce another ticket field that merely repeats the current phase. For the shipped code/docs flows: design stays on control, implementation creates or reuses the recorded branch, code review/fixes use that branch, and PR publication operates from control. Distinguish design review from code/PR review, including owner assists; a generic step name alone does not establish semantics.
- Share the deterministic branch-preparation implementation between launch and a callable operation for an agent already inside coga chat. Reuse a recorded branch without resetting its unique work. For a new ticket branch, record and publish the linkage on control before switching. Keep workflow-specific selection separate from shared Git mechanics.
- Chat begins without a task or workflow and may remain discussion-only. When the human requests edits, the agent invokes the same preparation operation for an ad-hoc branch. Do not require creating a ticket or inventing a workflow transition. The existing launcher owns safe checkout return at session exit, not after each conversation turn.
- Preserve one complete, coherent explanation of the lifecycle in the owning checkout topic and its focused exception/recovery references. Humans and agents use the same documentation. Normal prompts describe the actual prepared branch and who handles return; chat has a short instruction to read the procedure and invoke preparation before editing.
- Leave implementation choices, selecting changes to commit, meaningful conflict resolution, tests, review, and handoff content to the agent. Automation checks preconditions and reports actionable failures while preserving unfinished work.

### Acceptance criteria

- [ ] Fresh implementation prepares a branch and publishes its ticket linkage before the agent edits code. A resumed implementation reuses the recorded branch; repeated preparation does not allocate extra branches or lose commits.
- [ ] The shipped workflow/step cases above select the correct checkout. Selection uses the current authoritative ticket, including after a chained step; no duplicate phase field, reinterpretation of requires as an entry policy, or arbitrary step-name heuristic is introduced. Define safe behavior for existing frozen tickets, repo-overridden workflows, unsupported/custom workflows, and already-satisfied work.
- [ ] Ad-hoc chat can move from discussion to requested edits through the shared preparation operation, with no ticket requirement. Repeated requests within the same session reuse the intended branch; ambiguous or occupied work is surfaced rather than taken over.
- [ ] Preserve the existing clean-entry, publication, safe-return, recorded-assist, sandbox-clone, configured-remote/control, and Git-disabled/non-Git/remote-less contracts where applicable. Account explicitly for script phases, recurring/delegated launches, megalaunch, and prompt-report rather than broadening dispatch accidentally.
- [ ] Dirty or unpublished work, stale state, conflicting linkage, and unavailable Git access produce specific diagnostics. Failure or interruption preserves unique work and never fabricates completion, replays a transition, or silently discards edits to get back to control.
- [ ] Runtime prompt information matches what preparation actually did. The agent no longer needs to reconstruct the automated startup and return procedure from conditional prose. Manual/API operation and chat still have an explicit way to find the complete guidance.
- [ ] Update the owning checkout, launch, workflow, composition, and extension topics as needed, plus applicable packaged twins. Remove obsolete procedural copies from the base prompt, dev/code overview, code skills, code/docs workflows, and orientation guidance in the same PR. Preserve required instructions in skilled and inline workflow steps.
- [ ] Add meaningful real-Git coverage for fresh/resumed work, step selection and chaining, chat discussion-to-edit, repeated calls, interruption, and dirty/publication failures. Update seeded launch fixtures where behavior changes. Run relevant Git/launch/compose/workflow/packaging tests, the required implementation checks, and coga validate --json.
- [ ] Compare representative prompts through the read-only compose API. Verify required guidance still arrives and repeated checkout recipes have disappeared; do not use a real launch or its sweeping prompt-report option just to measure.

### Design deliverable

Specify the branch-selection and publication sequence, the workflow-to-checkout mapping and its owning surface, and the smallest callable interface for in-session chat. Explain how an ad-hoc branch is identified and reused without ticket metadata, how failed/partial preparation is retried, and how the agent receives the authoritative ticket for its handoff after branch switching. Resolve the placement under coga/extension-model; this work should reuse the existing launch boundary, not introduce a general execution/plugin framework. The operation's spelling and API are design decisions, not existing capabilities.

### Scope boundary

Deliver automation, documentation, and removal of obsolete instructions together. Preserve the existing checkout model and human workflow gates. Worktree isolation, branch deletion policy, automatic implementation commits, and a general lifecycle/publication redesign are separate work.

## Context

The attached knowledge and extension-model topics govern where the explanation
and the shared implementation belong. The behavior topics below are cited
rather than attached; read the named sections before designing or changing
their behavior, and update their owners and packaged twins with implementation.

- `dev/checkouts` (`docs/contexts/dev/checkouts/SKILL.md`): read "Start, work,
  end", "Publish pre-branch ticket edits", and "Which checkout you invoke
  Coga from". `src/coga/git.py` plus `sync_coga_state` publishes Coga state;
  branch switching alone does not publish the ticket linkage. Its
  `prepare_control_checkout` provides the existing safe control preparation.
- `dev/checkouts/launch-boundary`
  (`docs/contexts/dev/checkouts/launch-boundary/SKILL.md`): read "Preparation
  and return" and "Checkout recovery", including exemptions.
  `src/coga/launch.py` plus `_CheckoutBoundary.enter` and `.settle` already
  wrap ordinary launches and direct orientation in state publication and
  control preparation; `_checkout_exemption` preserves recorded checkouts.
- `coga/launch` (`docs/contexts/coga/launch/SKILL.md`): read "Checkout boundary"
  and "Phases and routing". `src/coga/launch.py` plus `_LaunchInvocation`
  coordinates dispatch, and `_supervise_steps` rereads the ticket for each
  step. Branch preparation must fit that order without composing from stale
  feature-branch ticket state or interfering with script phases.
- `coga/workflows` (`docs/contexts/coga/workflows/SKILL.md`): read step format,
  freezing, and "Step completion gates". `src/coga/ticket.py` plus
  `Ticket.current_step` resolves the existing frozen step; `src/coga/workflow.py`
  plus `Workflow.load` reads workflow definitions. Completion gates do not
  currently describe entry behavior. Define the checkout mapping without
  assuming arbitrary custom step names have shipped-workflow semantics.
- `coga/prompt-composition`
  (`docs/contexts/coga/prompt-composition/SKILL.md`): read "Layer order" and
  "What each layer reads". `src/coga/compose.py` plus
  `compose_prompt_report` measures a prompt without a launch; `_step_layers`
  selects either step skills or the live inline step body. A skill-backed
  step does not receive its workflow's inline prose. Links do not load topics.
- `coga/testing` and `coga/packaging`
  (`docs/contexts/coga/testing/SKILL.md` and
  `docs/contexts/coga/packaging/SKILL.md`): read the verification and twin
  requirements before implementation. `src/coga/paths.py` plus
  `resolve_context_path` and `resolve_skill_path` select local or packaged
  resources, rather than composing both copies.

The audit found repeated entry/return instructions in `dev/code`,
`dev/checkouts`, `coga/skills/code/{implement,self-qa,open-pr,address-pr-comments}/SKILL.md`,
and packaged `bootstrap/workflows/{code,docs}/` definitions. The implementation
skill also repeats them within its introduction, procedure, and acceptance
checklist. Its resumed-branch guidance has no equivalent in the copied docs
implementation startup procedure. Use these as starting points for the
cross-surface audit, not a closed list.

Direct chat is `bootstrap/orient`; its packaged `ticket.md` deliberately has
no task lifecycle. The base prompt is `src/coga/resources/prompt.md`.
Tests already covering return include `tests/test_launch.py` plus
`test_launch_returns_a_feature_branch_handoff_before_the_next_step` and
`test_launch_returns_the_checkout_after_a_failed_session`; extend the
existing real-Git test approach rather than mocking away checkout behavior.

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
implementation and evidence, never placeholders; coga/internals/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Authoring handoff

The owner approved the direction in an attended orientation discussion:
automate shared mechanics, use the existing workflow/current step, retain
complete documentation, and support edits requested during ad-hoc chat.
This draft captures that agreement; design and implementation have not started.

The next launch starts the design step. Settle the workflow mapping's owning
surface and the callable chat interface at design review. Preserve the
distinction between agreed behavior and those still-open implementation choices.
