---
slug: select-session-conduct-instead-of-appending-a-cont
title: Select session conduct instead of appending a contradiction
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/principles
- coga/architecture
- coga/codebase
- coga/launch-internals
- coga/recurring
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
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
secrets: null
step: 4 (open-pr)
---

## Description

Session conduct is currently authored as a contradiction. The base prompt
always composes `## Working with the human` (attended: ask the human and wait).
For a queue run, `coga megalaunch` or automatic `coga recurring` execution then
appends another block *after the task layers* that says the TTY is only
transport, the agent must continue after stating its plan, and unavailable
input must end in a terminal `coga block`. Every queue prompt therefore carries
both a rule and its inverse, and correctness depends on prose about which one
wins.

Replace precedence with selection. Prompt composition must receive the
ephemeral launch context and include exactly one session-conduct layer: an
attended contract for ordinary interactive work, or the appropriate queue
contract for megalaunch and automatic recurring work. This is launch
invocation state, not ticket state; no `mode:`, `autonomy:`, config switch, or
other durable selector belongs on the task.

The consequence matters in both directions. An attended agent that follows
queue conduct parks a ticket even though the human is present to answer. A
queued agent that follows attended conduct asks and waits until the liveness
watchdog tears down the session without the terminal transition that would
notify the owner and release the queue.

## Context

**Today there are three documents describing conduct, one contradicting the
other two:**

| document | when | size |
|---|---|---|
| `prompt.md` § Working with the human | always | attended default |
| `prompt-megalaunch.md` | appended for megalaunch | 33 lines |
| `prompt-queue.md` | appended for recurring | 29 lines |

The two appended files are ~80% the same content, differently worded — both
say TTY-is-transport, state-your-plan-and-continue, and block-terminally
rather than asking. They genuinely differ in about four lines each:
megalaunch carries the dependency-drain slug hint and the
blocker-resolution exception; recurring carries the stateless-bootstrap
`coga slack` completion signal.

The implementation has the same split. `compose_prompt()` /
`compose_prompt_report()` in `src/coga/compose.py` always load `prompt.md`.
`src/coga/megalaunch.py::_megalaunch_prompt_suffix()` and
`src/coga/commands/launch.py::_queue_prompt_suffix()` load the queue resources
later and pass them through `spawn_agent_session(prompt_suffix=...)`. As a
result, queue conduct is not a first-class reported composition layer, and the
initial compose preflight validates an attended prompt before the spawn path
constructs the queue prompt.

**What the contradiction costs.** The precedence machinery in the base prompt
exists only to manage it:

- "authoritative over any generic instruction elsewhere in this prompt, the
  workflow, or a step skill"
- "Only an execution directive appended *after* the task layers ... overrides it"
- "A workflow or step skill is composed later in this prompt and still does not"
- the companion rule in § Blocking and FYIs

plus six pinned assertions in `tests/test_compose.py`
(`test_compose_agent_prompt_attended_ask_and_wait`). Under selection, most of
that prose has nothing left to disambiguate, and the guards become the simpler
and stronger claim: *exactly one conduct block is composed, and it is the right
one.*

**This is not a revert to `mode_prompt`.** That layer was removed because its
selector was a **ticket field** (`autonomy:`, then `mode:`), and how a session
executes is not a property of the task — see #545. The selector here is
**launch context** (queued vs. attended), which is the honest axis. Same shape,
different and correct reason. It does partially undo the merge in
`475d4645`; that merge was right for the code as it stood, when conduct had one
unconditional value and nothing to select between.

## Acceptance Criteria

- [ ] `compose_prompt()` and `compose_prompt_report()` accept an explicit,
  typed launch-context selector whose default is attended. The supported
  contexts distinguish ordinary attended launches, megalaunch queue launches,
  and recurring queue launches without reading any ticket field or config
  option.
- [ ] Every ticket/bootstrap REPL prompt produced by the shared composer
  contains exactly one `session_conduct` `PromptLayer`, and `--prompt-report`
  identifies the selected resource. The base prompt and invocation suffix
  contain no second concrete conduct policy. The separate PTY-less recurring
  autofix analyst remains outside this composer and this ticket's scope.
- [ ] Ordinary `coga launch` (including a human-typed direct period-task
  launch), `coga chat`, guided `coga ticket` authoring, and every recurring
  invocation using its existing `--interactive` choice select attended
  conduct: ask the present human and wait, request confirmation before
  substantive code, and reserve blocking for an explicit request to park the
  ticket.
- [ ] `coga megalaunch` selects megalaunch queue conduct. Its prompt says that
  the TTY is transport, states a plan and continues, terminally blocks for
  unavailable input, preserves the exact dependency-slug hint, and preserves
  the selected blocked-task resolution exception.
- [ ] Non-interactive runner-owned recurring execution—the normal sweep,
  `--force`, named `recurring launch <name>`, ordinary period-task agent
  phases, and delegated stateless bootstrap sessions—selects recurring queue
  conduct. It preserves the stateless bootstrap `coga slack`
  completion/failure rule; the corresponding `--interactive` paths select
  attended conduct instead.
- [ ] Queue prompts do not contain the attended `ask and wait` / plan-approval
  directive, and attended prompts do not contain the queue directive to
  continue without approval and terminally block unavailable input. Tests
  assert both positive selection and absence of the opposite contract.
- [ ] Preflight, prompt reporting, every recompose, and final spawn use the
  same launch context. A missing selected conduct resource raises
  `ComposeError` before the launch publishes `in_progress` or spawns an agent,
  matching the existing required-layer preflight boundary without changing
  draft/paused auto-activation or recurring materialization semantics.
- [ ] Conduct is no longer carried in `prompt_suffix`; invocation-only inputs
  such as ordered launch arguments may remain suffixes. The obsolete queue
  suffix helpers and their resource preflights are removed.
- [ ] `prompt-blocker-resolution.md` remains an independent, state-derived
  preamble with its existing inclusion and ordering semantics. Script-only
  launches, TTY admission, liveness limits, lifecycle transitions, and queue
  completion sentinels retain their current behavior.
- [ ] The prompt-composition contract is updated in both
  `coga/contexts/coga/architecture/SKILL.md` and its packaged twin. The shipped
  CLI context and live recurring context no longer describe queue conduct as
  an appended override or advertise `--queue-guidance` if that internal flag
  is removed.
- [ ] Composition, launch, megalaunch, recurring, smoke, and packaging tests
  cover the selected resources and pass; `coga validate --task
  select-session-conduct-instead-of-appending-a-cont` succeeds.

## Proposed Shape

### Make launch context an explicit composition input

In `src/coga/compose.py`, define a narrow typed value such as
`LaunchContext = Literal["attended", "megalaunch", "recurring"]`. Add the
keyword-only `launch_context` argument, defaulting to `"attended"`, to
`compose_prompt()` and `compose_prompt_report()`. Immediately after the neutral
base layer, map that context to one package resource and append one
`PromptLayer` named `session_conduct`. Keep the selected filename in the
layer's `ref` so prompt reports make the choice legible.

The three values describe real caller contexts, not modes of a task:

- `attended` selects a new attended resource extracted from the current
  `prompt.md` `## Working with the human` section;
- `megalaunch` selects the complete megalaunch queue contract currently in
  `prompt-megalaunch.md`; and
- `recurring` selects the complete automatic-recurring queue contract currently
  in `prompt-queue.md`.

Keep the two queue resources complete rather than assembling a common queue
fragment plus caller-specific tails. Once selection ensures only one reaches
an agent, their repeated wording has no runtime token cost. The deliberate
maintenance duplication is preferable to splitting the highest-consequence
policy across multiple resources and reconstructing it in Python. Parameterized
tests should pin the common queue invariants in both files so their shared
meaning cannot drift silently.

### Make the base prompt neutral

Move all concrete attended behavior out of `src/coga/resources/prompt.md`.
Retain only neutral cross-references where the base loop and blocking section
need them: the selected `Session conduct` layer decides whether input is
available and how to escalate. Delete the override/precedence explanations,
including the claims about later task layers, because there will be no opposite
conduct block to rank.

Edit `prompt-megalaunch.md` and `prompt-queue.md` as selected conduct resources,
not suffixes. Remove wording that says they override an attended default, while
preserving all queue behavior and the caller-specific clauses listed in the
acceptance criteria. Add the new attended resource to the packaging manifest.

### Thread one value through every agent-spawn path

In `src/coga/commands/launch.py`, thread `launch_context` through the launch
preflight, prompt-report path, supervisor recomposition, and
`spawn_agent_session()`. Plain launch and authoring paths use the attended
default. Replace the recurring-only `queue_guidance` boolean plumbing with the
typed context: automatic recurring callers pass `"recurring"`, while
`--interactive` passes `"attended"`. This includes the delegated bootstrap
path through `launch_with_before_spawn()` so its pre-publication compose and
post-publication recompose cannot diverge.

In `src/coga/megalaunch.py`, pass `"megalaunch"` to both
`_preflight_agent_launch()` composition and `spawn_agent_session()`. Delete
`_megalaunch_prompt_suffix()`, `_queue_prompt_suffix()`, and now-unused package
resource imports. Leave `prompt_suffix` available only for genuinely appended
invocation input, notably `## Launch arguments`.

Update `src/coga/recurring_runner.py` and its tests at the same time as the
launch signatures. Derive the context once from the existing `interactive`
choice and carry that value through ordinary period launches, named launches,
forced sweeps, and delegated sessions. Do not add a public session-mode knob;
the entry point already knows whether it is attending one task or draining a
queue.

### Replace precedence tests with selection tests and update the contract

Refactor `tests/test_compose.py::test_compose_agent_prompt_attended_ask_and_wait`
and add parameterized coverage for all three launch contexts. Assert exactly
one `session_conduct` layer, its resource ref, its required positive clauses,
and absence of the opposite concrete policy. Extend prompt-report coverage so
the selected conduct is visible. Update launch/recomposition tests to capture
the typed context, megalaunch tests to stop inspecting a suffix, recurring
tests to distinguish automatic from `--interactive`, and
`tests/test_packaging.py` for the attended resource.

Rewrite the prompt-composition section in the live and packaged
`coga/architecture` contexts to list base prompt followed by selected session
conduct and to say explicitly that the selector is ephemeral launch context,
never ticket frontmatter. Update the packaged `coga/cli` queue section and the
live `coga/recurring` references to match the final internal spelling and
selection behavior.

## Out of Scope

- Reintroducing `mode:`, `autonomy:`, or any other ticket/config selector, or
  changing the `ticket.py`-based script-versus-agent deduction removed in
  #545.
- Changing which commands are attended versus queued, or adding a user-facing
  option that lets an ordinary launch impersonate queue execution.
- Redesigning blocker persistence, the selected-blocker resolution preamble,
  megalaunch dependency drain, recurring completion sentinels, liveness
  watchdogs, or TTY admission.
- Removing launch-argument suffixes or otherwise redesigning invocation input;
  this ticket removes only appended *conduct*.
- A general editorial rewrite or token-budget pass over the base prompt,
  workflow skills, or contexts beyond the neutral wording required to remove
  the contradiction.
- Factoring the two complete queue resources into shared fragments. Revisit
  only if maintaining the repeated queue invariants becomes a demonstrated
  problem.

## Origin

Found while trimming composed-prompt size in PR #726, which is where the
`mode_prompt` merge landed. Fourth in a run of fossils from two primitive
collapses (`autonomy` removal, and #427's three-files-to-one). Deliberately
kept out of #726 to keep that review scoped.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/729
branch: select-session-conduct
worktree: /home/n/Code/codex/coga-select-session-conduct

## Implementation Notes

- `compose.py` owns the selector: `LaunchContext` (`attended` | `megalaunch` |
  `recurring`) plus `SESSION_CONDUCT_RESOURCES`. `compose_prompt()` /
  `compose_prompt_report()` take keyword-only `launch_context="attended"` and
  append one `session_conduct` `PromptLayer` right after the base prompt. The
  layer is `raw=True` so each resource's own `## Session conduct — <context>`
  heading survives; `--prompt-report` shows the ref, verified live
  (`session_conduct  prompt-attended.md  1.1 KiB`).
- An unknown context raises `ComposeError` rather than composing no conduct,
  so a bad selector fails at the same pre-`in_progress` preflight as a missing
  resource.
- `prompt-attended.md` is new, extracted from the base prompt's old
  `## Working with the human`. `prompt.md` keeps only two neutral
  cross-references (loop step 4 and § Blocking and FYIs); all precedence prose
  is gone because there is no second conduct block left to rank.
- Removed the hidden `--queue-guidance` Typer option outright — recurring
  reaches launch through the in-process seams (`launch_recurring_period`,
  `launch_with_before_spawn`), never argv, so nothing passed it. The public
  `launch()` spelling now hardcodes `launch_context="attended"`, which also
  keeps an ordinary launch from impersonating a queue.
- `_queue_prompt_suffix()` and `_megalaunch_prompt_suffix()` deleted, with
  their now-unused `read_packaged_resource` imports. `prompt_suffix` carries
  only `_agent_args_prompt_suffix` (`## Launch arguments`).
- `spawn_agent_session()` gained `launch_context` and its two compose branches
  collapsed into one call passing both keywords.
- `recurring_runner._recurring_launch_context(interactive)` is the single
  mapping point (`attended` when `--interactive`, else `recurring`), consumed
  by `_launch_due_tasks` and `_launch_created`, and threaded into
  `_run_delegated_task` for delegated bootstrap sessions.

## Verification

- `python -m pytest`: **2120 passed** on the rebased branch, clean tree.
  Needs a venv with the `[test]` extra — the ambient `python3.12` lacks
  `hatchling`, and `test_wheel_includes_bootstrap_batteries` then fails as
  environment noise (it fails identically on unmodified `main`).
- That wheel test now also proves `prompt-attended.md` ships.
- `coga validate --task select-session-conduct-instead-of-appending-a-cont
  --json`: 1 ok, 0 issues.
- Re-diffed the live↔packaged pairs by hand after the rebase (architecture,
  codebase, resolve-conflicts, code/implement) — all identical.

## Gotchas

- **Ran `coga launch --prompt-report` from the feature worktree.** That is a
  state-changing command, so the CLI exit-boundary sweep committed the three
  live `coga/` doc edits as `d698cd03 "Sync coga state"` and pushed them to
  `origin/main` — exactly the hazard `coga/codebase` documents. Resolved with
  the owner's approval: soft-reset the branch past that commit so the doc
  files joined the feature commit, then `git revert d698cd03` on `main`
  (`b5cb36a0`, pushed). Verified `d698cd03` is no longer an ancestor of the
  feature branch, so merging re-adds the docs cleanly rather than hitting the
  revert-then-merge trap. **Use a scratch checkout, or the primary checkout,
  to run any prompt-report/launch verification.**
- Several tests faked `compose_prompt` as `lambda cfg, ref, ticket:`; the
  unified call passes keywords, so they needed `**kwargs`. Widening the fakes
  was right — the old branch existed only to avoid passing a keyword.

## Design Findings

- `compose_prompt()` always selects attended conduct indirectly through
  `prompt.md`; megalaunch and recurring add queue conduct later through
  `prompt_suffix`. That suffix is outside `PromptComposition.layers`, so the
  prompt report cannot prove the conduct selection today.
- The honest selector is caller-owned launch context. Direct launch and guided
  authoring are attended; megalaunch is its own queue context; recurring maps
  automatic runs to queue and `--interactive` to attended. No ticket data is
  needed.
- Keep `prompt-megalaunch.md` and `prompt-queue.md` as complete selected
  contracts. A shared queue file plus tails would save source words but split
  the policy the agent/reviewer needs to read as one unit.
- Added `coga/architecture`, `coga/codebase`, `coga/launch-internals`, and
  `coga/recurring` (plus principles) to the ticket because implementation
  changes the shared composer, `commands/launch.py`, and recurring launch
  plumbing. `coga/launch-internals` explicitly requires attachment for that
  path.

## Open Questions

None. The owner approved the three-value, caller-owned selector and keeping
`prompt-megalaunch.md` and `prompt-queue.md` as complete selected contracts.
The acceptance criteria now scope the composer away from the PTY-less autofix
analyst, distinguish non-interactive recurring execution from direct and
`--interactive` attended launches, and pin missing-resource failure to the
existing pre-`in_progress` / pre-spawn boundary.
