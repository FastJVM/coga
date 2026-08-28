---
slug: select-session-conduct-instead-of-appending-a-cont
title: Select session conduct instead of appending a contradiction
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
step: 2 (review-design)
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
- [ ] Every agent prompt contains exactly one `session_conduct`
  `PromptLayer`, and `--prompt-report` identifies the selected resource. The
  base prompt and invocation suffix contain no second concrete conduct policy.
- [ ] Ordinary `coga launch`, `coga chat`, guided `coga ticket` authoring, and
  `coga recurring --interactive` select attended conduct: ask the present human
  and wait, request confirmation before substantive code, and reserve blocking
  for an explicit request to park the ticket.
- [ ] `coga megalaunch` selects megalaunch queue conduct. Its prompt says that
  the TTY is transport, states a plan and continues, terminally blocks for
  unavailable input, preserves the exact dependency-slug hint, and preserves
  the selected blocked-task resolution exception.
- [ ] Automatic recurring execution—the normal sweep, `--force`, named
  `recurring launch <name>`, ordinary period-task agent phases, and delegated
  stateless bootstrap sessions—selects recurring queue conduct. It preserves
  the stateless bootstrap `coga slack` completion/failure rule.
- [ ] Queue prompts do not contain the attended `ask and wait` / plan-approval
  directive, and attended prompts do not contain the queue directive to
  continue without approval and terminally block unavailable input. Tests
  assert both positive selection and absence of the opposite contract.
- [ ] Preflight, prompt reporting, every recompose, and final spawn use the
  same launch context. A missing selected conduct resource raises
  `ComposeError` before lifecycle mutation or agent spawn, like any other
  required prompt layer.
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

None after tracing the current call sites. The owner review should explicitly
approve the choice to keep two complete queue resources rather than factoring
shared prose before implementation begins.
