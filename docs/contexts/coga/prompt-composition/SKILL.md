---
name: coga/prompt-composition
description: How `coga launch` builds an agent prompt — the exact layer order, how the one session-conduct resource is selected, what each layer reads (including repo overrides of the fixed text resources), the three-region ticket extract, the blocker preamble and authoring projection, failure on missing refs, what never composes, and `--prompt-report`.
---

# Prompt composition

When an agent phase remains after any `ticket.py` phase
([coga/script-tickets](../script-tickets/SKILL.md)), launch builds one prompt.
The prompt is a pure function of the files on disk at that moment: nothing
carries over from an earlier session, so a corrected file takes full effect
on the next launch. There is no follow-up loading.

## Layer order

1. **Header**: task ref, title, exact task directory, status.
2. **Base prompt** (resource `prompt.md`): the operating loop; neutral on
   conduct. Its shared reconciliation checkpoint directs agents to
   [coga/checkouts/reconciliation](../checkouts/reconciliation/SKILL.md).
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
Exactly one conduct resource sits immediately after the base prompt; it is
selected, never stacked or appended after task layers, and the base prompt
defers to it for every instruction to ask or to block. What each posture
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
  replaces the packaged copy. The overridable names are `prompt.md`, the
  three conduct resources, `prompt-blocker-resolution.md`, and three
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
- Contexts and skills resolve local-first, then the package bootstrap copy,
  and are read **whole**: `SKILL.md` frontmatter (`name`, `description`) is
  included in the prompt.
- Markdown links inside a context or skill are not followed; only attached
  refs compose ([coga/knowledge](../knowledge/SKILL.md)).
- A missing context, skill, or packaged resource refuses the launch, naming
  the paths checked, before it publishes `in_progress` or spawns. A deleted
  workflow definition composes a placeholder and is reported by
  `coga validate` instead; an existing but malformed or unreadable one
  refuses.

## The ticket is a three-region extract

Composition takes each `##` section (heading case-insensitive, fence-aware,
so a `##` line inside a code fence does not end it) and carries only
`## Description`, `## Context`, and the blackboard region. Every other `##`
section above the fence is uncomposed: it reaches no layer, but launch and
`--prompt-report` print an `uncomposed-section` warning naming it, as
`coga validate` does. Where that material belongs is owned by
[coga/tickets](../tickets/SKILL.md) (Body regions). The exact
`## Superseded designs` content is replaced by a short pointer to the ticket
file and archive heading; the stored ticket is unchanged.

## Blocker preamble versus authoring

The preamble is derived from state, not a flag: it appears while unresolved
asks exist and disappears once `coga unblock` records an answer, so it
survives a session that dies mid-discussion. It lists open asks verbatim and
makes resolve-or-re-block the session's first job.

Guided `coga ticket` authoring composes an ephemeral projection: `skills:`
becomes only `bootstrap/ticket`, `step:` is removed so no step layer
composes, and the blocker preamble is off. Blocker text still appears in the
blackboard layer, so authoring a blocked ticket neither runs its step,
resolves its asks, nor reactivates it. The stored ticket keeps its workflow
position.

## What never composes

- `coga/log.md`: repo-global, append-only, never a layer, so it can grow
  without bound. Only the blackboard carries state forward.
- Ticket attachments and superseded-design text (pointer only).
- Unattached contexts, docs pages, and anything reached by a link.

## Measuring

`coga launch <ref> --prompt-report` prints one line per layer (layer id, ref,
bytes, `approx_tokens` = ceil(chars/4)) and the total; the `session_conduct`
line names the selected resource, the ticket's regions stay separate lines so
an oversized blackboard is visible, and layers read from a repo override are
listed under `Repo resource overrides:`. It works on drafts but runs the
normal state sweep ([coga/checkouts](../checkouts/SKILL.md)). A prompt too
large for one argv argument is delivered as a pointer to the prompt file;
such a size usually means context bloat.

Implementation detail (prompt files, the launch marker's cache rationale,
error classes, argv delivery) is in
[coga-dev/internals/compose](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/compose/SKILL.md).
