---
name: bootstrap/project
description: Interview the human about a project (outcome, prior art, constraints, dependencies), propose an ordered set of tickets for them to prune, then scaffold the surviving set as draft tickets — one launchable step each. You plan the project; you do not start the work.
---

# Plan a project into tickets

Your job is to turn a project the human has in their head into an **ordered set
of `draft` tickets**, one per step, that they can review and launch. You plan;
you do **not** do the work itself, and you do **not** activate or launch any of
the tickets you create — they're left as drafts for the human.

The human is at the keyboard (`mode: interactive`). Ask, don't guess. Keep the
interview short — four questions, one at a time — and let the decomposition be
your job, not theirs. The human supplies only what you genuinely can't infer.

## Ticket format — read this first

The canonical ticket shape is `relay-os/tasks/_template/ticket.md`. **Read it
once before you scaffold anything** — Description is the *what + why* (2–4
sentences), Context is task-specific knowledge. Every generated ticket matches
that shape. Don't invent frontmatter fields the template doesn't define.

## Step 1 — Interview (four questions, one at a time, recorded verbatim)

Ask these in order, one per turn. Record each answer before asking the next.
Don't interrogate — if an answer is vague, note the gap and move on; the
review step (Step 3) catches it more cheaply than a follow-up question would.

1. **Outcome (always first, never skipped).** "When this project is done, what
   exists that doesn't today? How would you demo it?" This is the definition of
   done and the final ticket's review bar. Ask it even if a doc exists —
   confirming the concrete done-state is cheap, and getting it wrong breaks the
   whole decomposition.

2. **Prior art (gap-filler).** "Is there anything I should build on — a doc
   (vision, spec, notes), or existing work like a workflow, script, or code?
   Point me to it." If they name something, **read it** before continuing and
   use it to skip later gaps it genuinely fills (tech, deadlines, sequence).
   The prior art is often a workflow/script/code file, not a prose doc — take
   whatever they point at. This never lets you skip Q1.

3. **Constraints.** "What's already fixed — deadlines, tech you've committed
   to, anything that mustn't change?" Fixed decisions become ticket Context;
   deadlines shape how much you decompose.

4. **Dependencies & sign-off.** "What has to happen before what? Include
   anything you're blocked on from outside (access, accounts, another team),
   who has to approve or hand off, and any order the agent couldn't guess from
   the goal." This is the part only the human can supply: external blockers and
   hidden ordering are edges in the dependency graph, and sign-off owners
   become `human`-assigned steps.

If the session was seeded (a `## Project seed` block at the end of your prompt,
or a doc path given on the command line), treat it as the answer-in-progress to
Q1/Q2 — read it, then confirm or fill the gaps rather than asking from scratch.

## Step 2 — Decompose

From the four answers, draft an **ordered** list of tickets. Sizing rule: one
ticket = one launchable unit of work with a single reviewable output. Not so
coarse that a ticket hides three deliverables; not so fine that a ticket is a
single trivial command.

- Order by the dependency graph from Q4. A prerequisite that must exist before
  later work (a test account, a built artifact the rest depends on) comes
  first. Nothing that produces an output is scheduled before the thing it
  operates on exists.
- Don't fabricate. If a step needs a fact neither the answers nor the prior art
  provide, draft the ticket anyway and record the gap in its Context as an open
  question rather than inventing a value.
- The final ticket's acceptance bar is Q1's demo answer. Intermediate tickets
  get acceptance criteria you draft; the human corrects them in Step 3.

## Step 3 — Review before scaffold (do not skip)

Present the proposed list to the human as **titles + one-liners + the
dependency edges**, before creating anything on disk. Ask plainly:

> "Anything here that shouldn't be a ticket, and anything missing? Does the
> order look right?"

This is the real scope and granularity gate — the human bounds scope by
reacting to a concrete list, which is far cheaper than predicting boundaries up
front or deleting wrong tickets afterward. Fold their edits in: drop tickets
they cut, split ones they flag as too big, add ones they name, reorder as
directed. Loop until they're satisfied. **Create nothing until they approve the
list.**

## Step 4 — Scaffold the ordered drafts

For each surviving ticket, in order, run:

```
relay create "<title>"
```

Then edit the new draft's `ticket.md` directly:

- **Description** — the what + why (2–4 sentences), drawn from the interview.
- **Context** — task-specific facts from the answers and prior art. Record
  cross-ticket ordering here in prose, e.g. `Depends on: <predecessor-slug>`
  (there is no dependency frontmatter field yet — keep it in the body so it
  survives until one exists). Note any open questions you couldn't resolve.
- Leave `workflow: null` unless the human chose a workflow for that step — a
  workflow-less draft is a valid authoring state; the human activates and wires
  each ticket when they're ready. Don't run `relay mark active` or
  `relay launch` on anything.

Slugs are leaf-name based, so the human can reference each ticket regardless of
order. After scaffolding, list the created slugs in dependency order and stop —
the human owns what happens next.

## What you must not do

- Don't start the actual project work — you produce drafts, not deliverables.
- Don't activate or launch the tickets you create.
- Don't skip the interview's Q1 or the Step 3 review, even when a doc exists.
- Don't over-generate. When unsure whether something is one ticket or three,
  propose your best guess in Step 3 and let the human reshape it.
