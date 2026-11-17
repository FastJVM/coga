---
name: coga/prompt-composition
description: How `coga launch` builds an agent prompt — the exact layer order, how the one session-conduct resource is selected, what each layer reads (including repo overrides of the fixed text resources), the three-region ticket extract, the blocker preamble and authoring projection, failure on missing refs, what never composes, `--prompt-report`, and the ruling that retains the current assembler.
---

# Prompt composition

When an agent phase remains after any `ticket.py` phase
([coga/script-tickets](../script-tickets/SKILL.md)), launch builds one prompt.
The prompt is a pure function of the files on disk at that moment: nothing
carries over from an earlier session, so a corrected file takes full effect
on the next launch. There is no follow-up loading.

## Layer order

1. **Header**: task ref, title, exact task directory, status.
2. **Base prompt** (resource `prompt.md`): the rules every session needs —
   checkout start, ticket-file editing rules, boundaries; neutral on conduct.
   Its shared reconciliation checkpoint directs agents to
   [coga/checkouts/reconciliation](../checkouts/reconciliation/SKILL.md).
   **Ticket loop** (resource `prompt-ticket.md`) follows it for a task ticket
   only: the blackboard, `bump`, and `block` loop. A stateless
   `bootstrap/<name>` target omits it, since it has no lifecycle; its own
   ticket says how it finishes. A repo whose older `resources/prompt.md`
   override still carries those sections composes them twice until it drops
   them.
3. **Session conduct**: exactly one resource chosen by launch context
   ([below](#session-conduct)).
4. **Blocker preamble** (`prompt-blocker-resolution.md`), only when the
   filtered blackboard has open `## Blockers` asks; see below.
5. **Repo context**: `<coga root>/context.md`, if present.
6. **Ticket contexts**: each `contexts:` ref, in list order.
7. **Skills**: each ticket-level `skills:` ref, then the current step's
   skills, or, for a skill-less step, its inline section from the live
   workflow definition ([coga/workflows](../workflows/SKILL.md)).
8. **The ticket**, contiguous in on-disk order: `## Description`, then
   `## Context`, then the live blackboard.
9. **Checkout notice** (`## Checkout (runtime)`): generated, never a
   resource. It states the branch launch observed, any ticket it projected,
   who returns the checkout, and for a direct chat the exact
   `coga run prepare-checkout` invocation. Without one (megalaunch,
   recurring) it states that no preparation was supplied and points to
   [coga/checkouts](../checkouts/SKILL.md). Being generated, it stays true
   under a repo's older `resources/prompt.md` override.

After the task layers, launch appends a `## Launch arguments` JSON block only
when positional launch arguments were given ([coga/launch](../launch/SKILL.md)).
The last line of every spawned prompt is a unique `coga-launch: <uuid>`
marker; it is not a layer and the report never shows it.

## Session conduct

How a session executes is a property of the **invocation**, not of the task.
Exactly one conduct resource sits immediately after the base prompt (and
the ticket loop, when composed); it is selected, never stacked or appended
after task layers, and both those layers defer to it for every instruction
to ask or to block. What each posture
requires is the resource text itself.

| Launch context | Resource | Chosen by |
| --- | --- | --- |
| `attended` | `prompt-attended.md` | ordinary `coga launch` (including a human-typed direct period-task launch), `coga chat`, guided `coga ticket`, any recurring spelling with `--interactive`; also the default |
| `megalaunch` | `prompt-megalaunch.md` | `coga megalaunch` |
| `recurring` | `prompt-queue.md` | runner-owned recurring runs: bare sweep, `--force`, `coga run recurring-scan`, `recurring launch <name>`, a period task's agent phase, a delegated stateless bootstrap session |

It is never ticket frontmatter, config, or a user flag on an ordinary launch.
An unknown context or missing resource refuses the launch like any missing
layer. A repo may replace any of the three resources by name (below);
selection is unchanged, and an override replaces only its own context's text.
The blocker preamble and `## Launch arguments` are task state and invocation
input, not conduct, and never change which resource is selected.

## What each layer reads

- The fixed text layers read top-level resources, repo override first:
  `<coga root>/resources/<name>` (`coga/resources/` by default) wholly
  replaces the packaged copy. The overridable names are `prompt.md`,
  `prompt-ticket.md`, the three conduct resources, `prompt-blocker-resolution.md`, and three
  non-prompt resources rendered by other commands: `blackboard.md` (the stock
  placeholder `coga create` writes; [coga/blackboard](../blackboard/SKILL.md)),
  `ticket.md` (the ordinary `coga create` body; one literal `{description}`
  is replaced) and `retire.md` (the `coga retire` task body, where a literal
  brace is doubled). Bootstrap launches use the same overrides. Override is
  **replace-only**: there is no append or patch mode, so an overridden file
  stops receiving upstream edits until someone merges them by hand.
  `templates/` is not part of this rule
  ([coga/context-layout](../context-layout/SKILL.md)). An override that
  exists but cannot be read or rendered refuses, naming the repo file, never
  a silent fallback; `coga validate` flags an unreadable override and a file
  in `resources/` that matches no name.
- Contexts and skills resolve local-first, then the package bootstrap copy.
- Every layer except the generated header and checkout notice is
  **normalized** before it composes: a leading YAML frontmatter block of a
  whole file (resource, `context.md`, context, skill) and whole-line HTML
  comment blocks are dropped; a resource's, context's or skill's leading
  document title is dropped when it is the body's one shallowest heading,
  since the `##` layer heading names the layer; and the remaining ATX
  headings are demoted so the shallowest sits at `###`. Only one `#`
  heading (the task header) and one `##` per layer remain. Lines inside code
  fences are never touched, an unterminated `<!--` stays as text, inline
  comments within a prose line stay, and setext headings are not rewritten.
  The session-conduct layer takes its heading from the resource's leading
  heading, so it names the selected context (`## Session conduct —
  attended`), falling back to `Session conduct`.
- Markdown links inside a context or skill are not followed; only attached
  refs compose ([coga/knowledge](../knowledge/SKILL.md)).
- A missing context, skill, or packaged resource refuses the launch, naming
  the paths checked, before it publishes `in_progress` or spawns. A deleted
  workflow definition composes a placeholder and is reported by
  `coga validate` instead; an existing but malformed or unreadable one
  refuses.

## The ticket is a three-region extract

Composition first drops complete HTML comment blocks from the body above
the fence, so a comment holding `##` lines (such as the ticket guide) neither
ends nor starts a section; the file and every other parser are unchanged. It
then takes each `##` section (heading case-insensitive, fence-aware,
so a `##` line inside a code fence does not end it) and carries only
`## Description`, `## Context`, and the blackboard region. Every other `##`
section above the fence is uncomposed: it reaches no layer, but launch and
`--prompt-report` print an `uncomposed-section` warning naming it, as
`coga validate` does. Where that material belongs is owned by
[coga/tickets](../tickets/SKILL.md) (Body regions). The exact
`## Superseded designs` content is replaced by a short pointer to the ticket
file and archive heading; the stored ticket is unchanged. The stock
blackboard placeholder (packaged `blackboard.md`, the repo override, or that
override rendered with the ticket title) is dropped wherever it stands as a
block of whole lines outside a fence, before the archive pointer is added. A
blackboard region left empty composes as `*No state recorded yet.*`.

## Blocker preamble versus authoring

The preamble is derived from state, not a flag: it appears while unresolved
asks exist and disappears once `coga unblock` records an answer, so it
survives a session that dies mid-discussion. It lists open asks verbatim and
makes resolve-or-re-block the session's first job. Open asks compose once:
while the preamble lists them, the blackboard layer replaces exactly those
entries with one pointer line and keeps resolved entries with their
`resolved:` lines. An unchecked entry followed by a `resolved:` line counts
as resolved, as in the blocker parser.

Guided `coga ticket` authoring composes an ephemeral projection: `skills:`
becomes only `bootstrap/ticket`, `step:` is removed so no step layer
composes, and the blocker preamble is off. Blocker text, open asks included,
still appears in the blackboard layer, so authoring a blocked ticket neither runs its step,
resolves its asks, nor reactivates it. The stored ticket keeps its workflow
position. Authoring composes through the same normalization, so the ticket
guide comment is absent from its prompt; `bootstrap/ticket` directs the agent
to read the guide in the ticket file, which it must read to edit anyway.

## What never composes

- `coga/log.md`: repo-global, never a layer; [retention](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/ticket.md) bounds eligible old history. Only the blackboard carries state forward.
- Ticket attachments and superseded-design text (pointer only).
- HTML comment blocks and file frontmatter, from any layer.
- The stock blackboard placeholder.
- Unattached contexts, docs pages, and anything reached by a link.

## Measuring

`coga launch <ref> --prompt-report` prints one line per layer (layer id, ref,
bytes, `approx_tokens` = ceil(chars/4)) and the total, all measured on the
normalized text; the `session_conduct`
line names the selected resource, the ticket's regions stay separate lines so
an oversized blackboard is visible, and layers read from a repo override are
listed under `Repo resource overrides:`. It works on drafts and skips the
end-of-command state sweep
([coga/launch](../launch/SKILL.md#options-and-exits)). A prompt too large for
one argv argument is delivered as a pointer to the prompt file;
such a size usually means context bloat.

The CLI diagnostic refreshes the ignored `.agent-skills/` view. For a
write-free report, call `compose.compose_prompt_report` directly. The flag
stays with launch because it reports the launch-selected composition and
provenance, rather than an independent ticket report.

## Assembler ruling

The production assembler — `compose.compose_prompt_report`, the authoring
projection above, and the recurring-autofix prompt builder — is retained.
The owner ruled on 2026-11-13 that candidate C1, which separated orientation
from invocation authority and omitted the execution loop from guided
authoring, was **disqualified**:

- In an owner-assist run, C1 merged `origin/main` into the prepared branch
  without a request: a checkout-gate violation, and a lost successful run in
  that case. The predeclared protocol makes either disqualifying.
- Its authoring advantage (2/2 against 1/2) does not override the gate and
  did not come from the predicted execute/bump conflict: the baseline failure
  was a missing cold evaluator, and no baseline authoring run advanced the
  ticket.
- Secondary measures showed no gain (inspectability +1/6 against a +2
  threshold; payload −3.40% against 15%), and no simplification was claimed.
  The implementation follow-up stays unlaunched.

Reopening needs a materially revised candidate with a new owner-approved
protocol and a new paired comparison; this evidence does not carry over. A
revision should keep authoring free of execution-loop text without weakening
the owner-assist and [reconciliation](../checkouts/reconciliation/SKILL.md)
guidance that keeps a read-only assist from merging into a prepared branch.
Evidence: the
[trial report](https://github.com/FastJVM/coga/blob/main/coga/tasks/v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly/report.md)
(§3, §4, §8) and its
[blind verdicts](https://github.com/FastJVM/coga/blob/main/coga/tasks/v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly/blind/verdicts.csv).

That trial measured rule compliance only. A follow-up measured output quality
against C1′, which is C1 with the baseline checkout and reconciliation guidance
restored. In eight blinded pairs the baseline won 4, C1′ won 3 and one was a
tie, and both arms passed every mechanical gate. The owner ruled the result
**inconclusive** on 2026-11-15, so the current assembler stays. The trial was
a pilot: one model, two repetitions, and judgments made from chat
presentations with varying abridgment. Evidence: the
[quality report](https://github.com/FastJVM/coga/blob/main/coga/tasks/v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality/report.md)
(§3, §5).

Implementation detail (prompt files, the launch marker's cache rationale,
error classes, argv delivery) is in
[coga-dev/internals/compose](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/compose/SKILL.md).
