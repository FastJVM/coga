# Blackboard — virtual-employee

The blackboard is a notepad to be written to often as the human and
agent work through a task. This file currently carries two things the
future implementer should read before starting:

1. `## Conversation digest` — the design conversation between nick
   and claude that produced the current ticket framing. Read this
   first; the ticket body assumes you know the reasoning that's
   captured here.
2. `## Evaluator review` — verbatim critique from an independent
   reviewer who read the ticket cold. Treat as inputs for the human
   reviewer (nick) to act on before activating the ticket.

---

## Conversation digest

A long interactive bootstrap-ticket session collapsed the title
"virtual employee" from "design a new primitive" down to "name an
abstraction Relay declines, and ship that rejection across three
surfaces." The key moves, in order:

**1. Initial framing — advisor that loads context.**
First read: a "virtual employee" is an advisor persona (e.g. a CMO)
that loads domain context to help write tickets and shape direction.
Pushback: in Relay terms that's *just* a context file attached via
`contexts:`. The interesting part — what would make it an *employee*
rather than an *advisor* — was being skipped.

**2. Decomposition — runtime vs. organizational layer.**
The standard Anthropic-style definition of an *agent* is
LLM + context + tools + (memory). That's the **runtime layer**.
What makes something an *employee* on top of that is the
**organizational layer**: stable named identity, addressable inbox,
scope of ownership, accountability. Relay's existing primitives
cover the runtime; the organizational layer is what's underspecified.

**3. Framing A — persona as attached context.**
Cheap, works today, but the persona has no continuity. It's a
consultant re-hired per ticket, not an employee.

**4. Framing B-strong — persona with persistent memory outside
markdown.**
Rejected on principle. State outside markdown fights `legibility
over cleverness` and the markdown-first thesis. Should be argued
*against* explicitly.

**5. Framing C — repo = employee.**
Elegant for one beat: a `relay-os/`-enabled repo already has
identity, inbox (`tasks/`), continuity (git + blackboards), Slack
channel. **Killed by the FE/BE counter-example**: a monorepo with
frontend and backend teams is one repo, two genuinely-distinct
employees. The abstraction doesn't survive intra-repo specialization.

**6. Framing B-weak — detached identity.**
Free-floating employee identity (name, attached contexts, Slack
handle, routing field) that attaches to tickets independent of where
the code lives. Most promising candidate for a while. Then collapsed
by the next question.

**7. The "is it needed?" audit.**
What a named bundle would bring: vocabulary, consistency,
discoverability, future sugar optionality. What it would cost:
premature abstraction (zero real callers), lock-in, indirection
layer. None of the trigger conditions for "yes" (5+ tickets in a
domain wanting the same bundle, real need for `@cmo` pings,
onboarding pain) are present today. The vocabulary win is free in
speech anyway — saying "CMO ticket" in conversation doesn't require
any file to exist.

**8. The "is it the right abstraction?" audit.**
Even granting the bundle, "virtual employee" is the *trendy*
framing — Devin / Sierra / Decagon / Lindy. Specific reasons it's
wrong-shaped for Relay:
- Imports baggage from human employment (tenure, agency, continuity)
  that doesn't transfer to stateless LLM sessions.
- Centers identity over work; Relay is task-centric.
- Category mistake — LLM sessions are stateless function calls, not
  beings with continuity.
- Tempts feature creep (AI OKRs, AI 1:1s, AI promotion ladders).
- Re-bundles primitives Relay deliberately keeps decomposed
  (contexts ≠ skills ≠ assignees ≠ Slack handles).

**9. The "is Relay contrarian, and right?" turn.**
Yes, and yes — but structural, not aesthetic. Every contrarian
choice traces to a specific principle in `relay/principles`:
- Markdown-first vs. SaaS hidden state.
- Legibility over cleverness vs. opaque agent abstractions.
- Short human correction loop vs. autonomous fire-and-forget.
- Fail loud vs. confidently-helpful agents that swallow errors.
- Classical mode (Pirsig) vs. layer-on-layer abstraction.
- No premature abstraction vs. anticipatory architecture.

`no premature abstraction` is the kill shot for virtual-employee
specifically: zero real callers, the principle literally says
"extract only when the third real caller appears." Supporting
precedent in `current-direction`: the "assignees flattened out"
decision *removed* an indirection layer that earned nothing. Relay
actively deletes abstractions that don't justify themselves.

**10. The "shouldn't this be a context / README?" turn.**
Checked `docs/vision.md` and the README. Discovery: vision.md
already does most of the contrarian-stance work (classical-vs-
romantic frame, "What this is not," "Why this is hard to duplicate").
What's missing is naming the **agent-as-employee framing
specifically** as one of the trendy abstractions Relay declines —
and making that posture loadable into agent prompts so agents
inherit the stance, not just humans (vision.md is explicitly scoped
as human-facing).

**11. Converged deliverable.**
Three-surface PR via `dev/with-self-review`:
- Clause in `docs/vision.md`'s "What this is not" section naming
  agent-as-employee as a declined abstraction.
- New `relay-os/contexts/relay/non-goals/SKILL.md` cataloging
  declined trendy abstractions. Initial (and only) entry:
  agent-as-employee. Structured so future entries extend the same
  shape.
- Extension to `relay-os/contexts/relay/principles/SKILL.md` adding
  "Contrarian bets" articulation tying each principle to the trendy
  alternative it's betting against (one line per bet, not
  paragraphs).

Naming choice: `non-goals` over `stance` (engineering-standard, more
scoped). Open to pushback in evaluator review.

---

## Evaluator review

**1. Description clarity for a cold-start agent.** The Description
is unusually strong for a cold-start. Lines 20–27 do three useful
things in 100 words: name the deliverable shape ("declined-
abstractions catalog"), tell the agent this is *not* a design ticket
(so don't re-derive the framing), and explicitly point at the
blackboard for the reasoning. The "see blackboard for the full
reasoning" parenthetical on line 24 is the right signal. The Context
section's first bullet (lines 46–51) doubles down with "Read the
blackboard first" in bold and tells the agent what shape to expect
there (`## Conversation digest`). That's the right framing — but
it's load-bearing on the blackboard actually containing that
section. If the blackboard hasn't been seeded with a
`## Conversation digest`, the ticket misleads the implementer.
Worth verifying before launch.

**2. Workflow fit.** `dev/with-self-review` is fine but slightly
oversized for a three-file doc PR. The `code/implement` and
`code/self-qa` skill names imply *code* — an agent picking up the
skill will read it through a code-review lens (probably `/simplify`
on prose, which is the wrong instinct). A `docs/with-self-review`
variant, or just `code/with-review` (skipping self-QA), would fit
better. That said, the self-QA step *is* genuinely useful here —
line 115's "catch sloppy wording before the human reviewer sees it"
is a real concern for a doc PR that's going to be visible on the
public-facing vision.md. So: not a mismatch worth blocking on, but
flag for the implementer that "self-qa on prose" means re-read for
wording, not run `/simplify`.

**3. Attached contexts.** `principles` and `current-direction` are
clearly load-bearing — the ticket body directly cites the
assignees-flattening precedent (lines 69–74) and quotes principles
by name (lines 56–68). `project-stage` is also load-bearing: "bias
toward deletion" and "no premature generality" are the exact stance
this ticket is making canonical. `architecture` is the weakest
attach — the ticket doesn't touch primitives or planes, and an
implementer doing a doc PR doesn't need 265 lines of Dream worker
contract and frontmatter mechanics. Consider dropping `architecture`
or replacing it with a one-line quote in the Context section.
Missing: nothing major, though `codebase/SKILL.md` could help the
implementer find the `_template/SKILL.md` referenced on line 81 —
currently they'd have to grep for it.

**4. Scope.** Three surfaces in one PR is the right call here, *not*
three tickets. The whole point of the ticket is the rejection being
legible across all three; splitting it would let the surfaces drift
(vision.md ships, principles extension stalls, non-goals context
never gets written). The size discipline section (lines 95–101)
caps each surface tightly enough that the combined diff stays
small. Keep as one ticket.

**5. Name `non-goals`.** Agree with the ticket's call on line 90.
`non-goals` is the engineering-standard term (Go, Kubernetes SIGs,
RFC culture). `stance` is vague and overlaps with `project-stage`.
`declined-abstractions` is more accurate but unwieldy as a directory
name; the Description's own phrase "declined-abstractions catalog"
(line 22) is a fine *body* framing inside a `non-goals/` directory.
`not-this` is cute but loses search hits. Ship as `non-goals`.

**6. Assumptions worth questioning.** Two. First, the ticket assumes
a `relay/non-goals` context warrants its own SKILL.md directory
rather than a section inside `relay/principles`. With one entry,
that's borderline — `project-stage` is one file with multiple H2s
and works fine. A counter-proposal: extend `relay/principles` with
a "Declined abstractions" H2 instead of a new context. The ticket
should at least name why it chose new-context over new-section
(probably: principles are timeless, declined abstractions are a
growing catalog). Second, the "Contrarian bets" addition to
`principles/SKILL.md` (lines 39–42, 84–89) risks bloating a
deliberately-scannable file — the principles context warns it's the
Pirsig filter, not a marketing doc. One line per bet, sure, but six
principles × one line each plus framing is ~10 lines added to a
70-line file. Worth doing, but the implementer should resist the
temptation to make each "vs." line clever.

**7. Other implementer-friction notes.** The "around line 230"
pointer on line 77 is helpful — verified, "What this is not" is at
line 230. Good. The `_template/SKILL.md` reference on line 81 isn't
given an absolute path; implementer will grep. The README pointer
(lines 109–112) is appropriately soft. One real gap: the ticket
doesn't say where the new context file's `description:` should land
tonally — terse like `architecture`'s, or narrative like
`vision.md`. Given the audience (agent prompts, not humans), terse
is right; worth one sentence saying so.

Overall: solid ticket. Tighten the contexts list (drop or quote
`architecture`), question the new-context-vs-section decision once
in the PR, and verify the blackboard digest actually exists before
launch.
