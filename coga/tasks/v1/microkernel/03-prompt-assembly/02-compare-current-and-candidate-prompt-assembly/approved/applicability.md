# C1 applicability contract (proposed)

This is a specimen contract, not new config or production API. The future
prototype may use ordinary typed arguments; no persistent invocation metadata
is added to ticket frontmatter. Names below describe observed facts, not CLI,
workflow or skill-name heuristics.

## Selection and provenance

The caller supplies operation (`execute`, `author`, or `analyze`), execution
kind (`agent` or `script`), target kind (`task`, `stateless`, or `record`),
conduct (attended, megalaunch queue, recurring queue, or one-shot), actual
completion authority, any owner-assist scope, and its observed checkout result.
Sources are the actual dispatch call, resolved target type, frozen current step
and resolved role, script-phase result and invocation arguments. Never derive
these facts from a spelling such as `review`, a workflow's name, a skill's
name, text equality with shipped instructions, or the presence of a TTY.

| Observed invocation facts | Included instructions and completion |
| --- | --- |
| `execute + agent + task` | Shared base; interactive boundaries; task-editing rules; existing ticket loop; exactly one conduct resource; blocker preamble if enabled and live asks remain; repo context; attached contexts; ticket skills; current step; intent/context/blackboard; observed checkout; arguments and marker |
| Same, owner-held step with explicit assist | Same layers; visible owner-assist scope in invocation block. No lifecycle transition without the human's explicit request; an agent override changes neither owner nor workflow role |
| `author + agent + task`, attended | Shared base; interactive boundaries; task-editing rules; authoring authority; attended conduct; repo/attached contexts; actual authoring projection's skill; intent/context/blackboard; checkout; marker. No execution loop, current-step instructions, blocker resolution or task-secret injection. Kickoff is a separate first user turn |
| `author + agent + stateless`, attended | Same authoring operation without a task blackboard or task lifecycle; requested authoring skill still owns the interview and explicit editing exceptions |
| `execute + agent + stateless` | Shared base; interactive boundaries; selected conduct; repo/attached contexts; requested skills/procedure and intent; checkout/arguments/marker. No task lifecycle or task-editing block. Procedure owns completion; the recurring stateless fixture's final successful `coga slack` releases its session |
| `analyze + agent + record + one-shot` | Shared base; read-only analysis authority; full analysis procedure/result schema; run record and open findings. No interactive conduct, checkout preparation, ticket loop, task edits, lifecycle, marker or interactive supervisor |
| `execute + script`, deterministic completion | No prompt, composition, agent lookup or refresh. Existing script machinery runs `ticket.py`, reloads state and classifies its result |
| Script succeeds, leaves same task step `in_progress` | Only then compose an agent prompt using fresh ticket/config/target and observed handoff, clearing script identity. Never compose from the pre-script ticket |

Unknown operations, incompatible target/conduct combinations, missing authority,
or contradictory caller facts refuse before spawn and publication. `author`
and `analyze` cannot be queue task-execution modes. A missing/invalid skill,
context or required resource remains a visible refusal, not a dropped block.
An absent checkout witness renders the existing unsupplied notice; it grants
no prepared-branch claim. The assembler does not itself do Git or expand
assist capability. Executor checkout/admission/publication behavior stays as
it is; this proposal does not replace its current policy classifier.

## Ownership and ordering

`candidate/base.md` is shared orientation only. Caller facts are data in the
visible invocation block and manifest: exact target, operation, conduct,
completion, assist, checkout and post-script result. They select instructions
but are not an instruction-writing DSL. `interactive.md` owns interactive
checkout/reconciliation and nesting/config boundaries. `task-editing.md` owns
ordinary ticket editing limits; an attached authoring skill may supply its
existing explicit exception. `author.md` and `analysis.md` state operation
authority. Existing ticket-loop and conduct files retain their text.

Repo context and selected contexts/skills resolve local-first, package fallback
only on absence, and compose whole including frontmatter. Links do not load
content. Preserve order and duplicates explicitly requested by separate refs;
do not use text similarity to deduplicate or trim. A trial cannot change
attached context selection between forms or repetitions.

A skilled current step receives a short **metadata** workflow fragment:
current step/index, resolved assignee, requires gate and ordered skill refs,
then each full resolved skill. No inline prose from that workflow is composed.
A step without skills receives the same metadata and its matching live inline
section once. Thus workflows supply sequence/role/gate and choose the procedure;
skills supply the procedure. This preserves `_step_layers`'s existing OR rule.
A human intending additional instructions for a skilled step must edit its
skill or attach another skill; silently concatenating dormant inline prose is
not part of this candidate. Fixture workflows deliberately carry dormant
inline text on skilled steps to make this selection observable. Missing live
workflow behavior and malformed/unreadable refusals stay at the existing
contract; no new fallback is proposed.

An authoring prompt retains the target's stored status and frozen workflow on
disk. Its projection removes only the execution step and replaces skills with
the actual requested authoring skill, matching the baseline projection; the
caller fact `author` removes the loop. Analysis procedure text is the current
`build_prompt` text, preserved whole as the control for this independent
builder; C1 adds orientation/authority/provenance without interactive rules.
This may increase analysis payload. It does not require an interactive spawn.

Manifest entries record source snapshot/revision/hash and the invocation or
ticket field that selected every rendered block, including generated header,
metadata, checkout, arguments and transport marker. Provenance overhead counts
in delivered bytes. Prototype simplicity claims must count validation of
caller facts and the analysis adapter as well as any removed branches.
