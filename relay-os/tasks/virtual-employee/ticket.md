---
title: virtual employee
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/principles
- relay/current-direction
- relay/project-stage
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: self-qa
    skills:
    - code/self-qa
  - name: pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
---

## Description

Name the **agent-as-employee** framing as an abstraction Relay does
*not* adopt, and ship that rejection as the inaugural entry in a
declined-abstractions catalog. This is not a design ticket for a new
primitive — the design conversation that led here concluded the
primitive isn't needed (zero real callers, principle violations, see
blackboard for the full reasoning). The ticket's purpose is to make
the rejection legible across three surfaces so future contributors
don't re-litigate.

Ship as a small doc PR via `dev/with-self-review`. Three deliverables:

1. **`docs/vision.md`** — add a clause to the "What this is not"
   section naming the agent-as-employee framing as a declined
   abstraction, with a one-line why. Link to the new
   `relay/non-goals` context.
2. **`relay-os/contexts/relay/non-goals/SKILL.md`** — new context
   under one page, cataloging trendy abstractions Relay declines.
   Initial entry: agent-as-employee. Structured so future entries
   extend the same shape.
3. **`relay-os/contexts/relay/principles/SKILL.md`** — add a
   "Contrarian bets" articulation tying each principle to the trendy
   alternative it's betting against (one line per bet, not
   paragraphs).

## Context

- **Read the blackboard first.** The `## Conversation digest` section
  there summarizes the design conversation that produced this framing
  — the runtime-vs-organizational-layer decomposition, the FE/BE
  counter-example that killed "repo = employee", the principle-by-
  principle audit. Without that context the ticket reads as a
  surprising "no"; with it the rejection is obvious.
- **Why agent-as-employee fails Relay's principles** (the implementer
  should use these as the source for the vision.md and non-goals
  wording, not paraphrase from memory):
  - `no premature abstraction` — zero real callers. No CMO ticket, no
    marketing ticket, no FE/BE specialist pattern. Just speculation
    about a future shape. Principle says: don't extract until the
    third real caller appears.
  - `legibility over cleverness` — the "employee" bundle aggregates
    contexts, skills, assignees, Slack handles, and identity into one
    indivisible thing. That re-bundles primitives Relay deliberately
    keeps decomposed. You lose the composability that makes Relay
    good.
  - `classical mode (Pirsig)` — the abstraction's purpose is hard to
    explain in one sentence beyond the metaphor. The metaphor
    over-promises: LLM sessions are stateless function calls; they
    don't have tenure, agency, or continuity. Calling them
    "employees" papers over the actual machinery.
- **Supporting precedent in `current-direction`** — see the "Recent
  decisions (assignees flattened out)" entry: the
  `[assignees.<user>]` indirection was *removed* because it earned
  nothing. Relay actively deletes abstractions that don't justify
  themselves. The declined-abstractions catalog generalizes this
  pattern.
- **Precision of the rejection — primitive, not metaphor.** The
  non-goal is specific: don't make `virtual-employee` a primitive in
  Relay's substrate (a `[employees.*]` table, a memory-bearing role
  abstraction, an identity-bearing agent entry). The framing remains
  useful as **UX positioning** for `relay chat` and similar
  interactive surfaces — an agent that's loaded the repo's contexts
  genuinely feels like a teammate who's been onboarded into the
  company, and "talking to your virtual employee" is an accurate
  description of that user experience even though the substrate is
  just stateless invocation + composed prompt. The `non-goals` entry
  should reject the *primitive* precisely without banning the
  *metaphor*. Future tickets are expected to use "virtual employee"
  as positioning language for `relay chat`-style surfaces; that's
  not a contradiction with this rejection, it's the same line drawn
  from both sides.
- **Concrete file targets:**
  - `docs/vision.md` — the "What this is not" section, around line
    230. The existing clauses ("Not a product. … Not an agent. …
    Not a platform.") are the right shape and length to mimic.
  - `relay-os/contexts/relay/non-goals/SKILL.md` — new file. Use
    `relay-os/contexts/_template/SKILL.md` for shape. Frontmatter
    `name: relay/non-goals`, a one-sentence `description:`. Body is
    the catalog (one H2 per declined abstraction; agent-as-employee
    is the first and only entry shipped here).
  - `relay-os/contexts/relay/principles/SKILL.md` — extend the
    existing file. The current structure is one H2 per principle.
    Either add a "Contrarian bets" H2 at the bottom summarizing each
    principle's "vs." line, or weave a one-line "vs." into each
    existing principle. Implementer's call; keep the file scannable
    (~70 lines today, don't double it).
- **Naming choice — `non-goals` over `stance`** — engineering-standard
  (Go non-goals, K8s SIG non-goals docs), scoped, less vague.
  Implementer may push back if a stronger alternative emerges
  (`declined-abstractions`? `not-this`?), but should justify the
  change in the PR description.
- **New context vs. new H2 inside `principles`** — chosen: a new
  separate context. Principles are timeless non-negotiables; declined
  abstractions are a growing catalog that will gain entries over time
  as new trendy framings come up. Different lifecycle, different
  audience, different shape. Worth naming this choice in the PR
  description so the reviewer sees it called out.
- **Size discipline:**
  - The `non-goals` context: under one page. One entry now;
    don't pad.
  - The `principles` extension: one line per bet, not paragraphs.
    Principles file stays scannable.
  - The `vision.md` clause: one short paragraph matching the
    existing "Not a / Not an" cadence.
- **Out of scope:**
  - Writing additional `non-goals` entries beyond agent-as-employee.
    Future trendy framings get their own tickets that extend the
    same surface.
  - Building any persona/employee primitive in code.
  - Touching `[agents.*]` in `relay.toml` or anything under
    `src/relay/`.
  - README changes are optional — README already points at
    `vision.md` for the why. Add a one-line pointer to
    `relay/non-goals` from README's "For the working mental model"
    sentence only if it reads naturally; skip if it's awkward.
- **PR shape** — one PR touching three files (vision.md, the new
  non-goals context, the principles extension). The `self-qa` step
  exists to catch sloppy wording before the human reviewer sees it;
  use it. **Caveat**: `code/self-qa` is a code-shaped skill (it
  expects `/review` + `/simplify` on a code diff). For this doc PR,
  treat "self-qa" as a re-read pass for wording, structure, and
  tone — not a `/simplify` run on prose, which would mangle it.
- **New context file `description:` tone** — terse, like
  `relay/architecture` or `relay/principles` (one sentence, what it
  is + when to load). The audience is agent prompts, not human
  readers. Save the narrative voice for `vision.md`.
