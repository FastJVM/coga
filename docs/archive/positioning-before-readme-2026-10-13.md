# Positioning before the README reset

> **History, archived 2026-10-13.** Sections removed from `marketing/positioning`, `marketing/strategy`, `product/vision`, `marketing/distribution` and `coga/current-direction` when the owner made [README.md](../../README.md) the source of truth for concepts and positioning. They are not instructions; current positioning is the README and [`marketing/positioning`](../contexts/marketing/positioning/SKILL.md).

## marketing/positioning — Proof

Show megalaunch carrying work forward while preserving human decisions,
plus one concrete correction to governing guidance that changes later work.
Support observed behavior with a public demonstration or public Coga record.
A prompt receiving a context alone does not demonstrate the correction's
later effect. The [idea-piece ticket](../../coga/tasks/marketing/idea-piece.md)
owns selecting and presenting the example; no separate story pipeline is needed.

## marketing/positioning — Root premise — owner follow-up, 2026-10-13

Coga is built for work you discover by doing: you start from a rough idea,
understand it as you go, and backtrack when a premise breaks. Code is now cheap
enough to throw away; what is expensive is the right idea, a clear spec and
proof that it works. So what has to last is what you learned, kept in files
the human can read, change and redo from. The human-ownership principle and
the features (task-scoped prompts, one owner per fact, per-kind workflows,
Dream) follow from this premise; individual features have close prior art, so
never present a feature as the original part.

The first 2026-10-13 rewrite below folded the original "Built for work you
discover by doing" idea into the knowledge lifecycle. The README follow-up on
PR #1000 restores it as the root: the problem section names the gap between
vibe coding and spec-first tools, and the key ideas open by deriving from the
premise.

## marketing/positioning — Refinement — owner review session, 2026-10-13

Revised the same day from the owner's PR #1000 review comments.

Keeps the 2026-09-21 opening and the instrument framing above. Adds what the
README's concrete behavior leads with and how it is worded.

- **Core.** Coga keeps in the repo what the team knows and the model does not
  (decisions, domain facts, experiment results, decisions not to act) as
  contexts scoped to the task, one owner per fact, checked against the code.
  Without them a capable agent falls back on its defaults, which are everyone's
  defaults.
- **Collaboration, defined.** The human brings what the model would not think
  of; agents bring execution and breadth, including research and review; Coga
  makes sure the human's part reaches every later launch. Use this definition
  rather than the bare words "collaboration" or "human in the loop".
- **README opening.** After the quote, say what Coga runs (Claude Code and
  Codex out of the box, any CLI agent with a few lines of config) and lead
  with the payoff: fix the file once and every later run starts from the fix.
  Do not open with "never from chat history" or the collaboration definition;
  the owner judged both unclear to a first-time reader. Then say Coga does not
  replace Claude Code or Codex; it handles the part they cannot do for you.
- **Entry pain.** Lead with the growing `CLAUDE.md`/`AGENTS.md`, instructions
  repeated in chat, and fresh sessions opened only to make an agent forget.
  Then say why size is not the whole problem: the same fact in diverging
  copies, and no way to tell which copies are still true.
- **Scoping.** Contexts are scoped by what the task is, not by where the code
  is, and the agent can still look up the rest. Comparisons with other tools
  cite the dated [agent memory landscape](../evidence/agent-memory-landscape-2026-10-13.md).
- **The unit is the task, not the session.** Lead the key ideas with this,
  in plain words rather than "one owner per fact" vocabulary: a ticket holds
  the goal, contexts, step and working notes, and every launch rebuilds from
  it, so sessions and agents are interchangeable.
- **Knowledge moves into files you correct.** Frame contexts as the feedback
  loop: decisions and knowledge move from code, chat and heads into contexts
  and tickets, and a fix to the owning file reaches the next launch. Tickets
  are disposable; what they teach is not: the usual move when a premise turns
  out wrong is to close the ticket with its reason, update the owning context
  and open a new one. Rewind exists but is the exception; do not lead with it.
- **Hackable and automated.** Answer the "write everything up front" fear:
  every file is editable, but in practice an agent writes it after a quick
  chat (`coga build` drafts a vision and starter tickets; `coga ticket`
  drafts a ticket and its contexts), and the human edits, rewrites or chats
  again. Do not say "you specify more up front".
- **Built on Claude Code and Codex.** Coga builds on capable agents rather
  than replacing them; it does the part they leave to the human. Say it in the
  opening, qualitatively: no percentage.
- **The process is yours.** Workflows set, per kind of work, where the human,
  the agent or a second agent steps in, and an agent can write them. Edits to
  shared rules publish as visible Git commits; Dream's proposals arrive as
  pull requests ([publication contract](../contexts/coga/internals/state-publication/SKILL.md)).
  Do not say every rule change arrives as a pull request. Plan mode is a
  useful anchor: here the
  plan is a file, reviewed cold by a second agent, approved as a step and still
  there at implementation.
- **Reading guidance.** The human chooses how closely to read; the
  preparing agent's advisory review depth on each pull request
  ([pr-publication](../contexts/coga/internals/pr-publication/SKILL.md)) is a
  suggestion, not a requirement.
- **Audience by posture.** Write for readers who already separate what they
  know from what they are still discovering; teams that plan unknown work as
  if it were known will feel overhead. Targeting itself belongs to the
  first-users ICP context; this is README voice only.
- **Vocabulary.** The product term is "context". Describe contexts as stating
  facts and contracts; avoid "documentation", which readers distrust.

## marketing/positioning — Source and claim limits (duplicate bullet)

- No "first", "only" or priority claim for managing the prompt: close
  precedents exist (see the dated claim check in
  [market landscape](market-landscape.md)).

## marketing/strategy — What kind of thing Coga is

Coga is better read as a discipline than a technology: operations-as-code,
treating knowledge, process and the work itself as versioned, legible,
agent-executable files. Earlier "X-as-code" disciplines waited for an executor
for their domain; operations waited for an executor that tolerates natural
language. The executor is domain-agnostic, so one substrate spans deterministic
steps (a ticket's `ticket.py`), judgment steps (an agent) and irreversible ones
(script plus human gate). Coga orchestrates existing systems; it does not
replace them. Its contrarian sub-bet is that the discipline needs a thin
runtime — validation, supervised launches, vendor-neutral agents, recurring
work, an audit log — without hiding state.

## marketing/strategy — The imposed metaphor: compile your company

Coga's taste is impositional where Linear's is subtractive. It asks the
operator to decompose work to evaluable units, externalize tacit knowledge,
classify facts versus procedures, separate durable truth from working state,
and correct the rule rather than the instance. The rigor is paid into the
substrate once and inherited by later light tasks, and agents do much of the
drafting. The cost is a standing demand for judgment, which narrows the
audience to people who enjoy rigor. The lesson from Linear is to subtract
friction from being rigorous, not to remove the rigor.

For an agent-mediated tool without its own UI, felt taste lives in the
correction loop snapping shut and in reliably steered agent behavior.

## marketing/strategy — Strategic posture (first paragraph)

Two positions were analyzed: A, internal open-source infrastructure published as
a field report; B, a branded category earned through adoption (the Linear
playbook with a small-tribe ceiling). A was the default with B left optional;
openness makes Coga a complement an incumbent can use as well as copy. The
earlier pinned fork is reference, not a live decision: current campaign choices
are in [plan](../contexts/marketing/plan/SKILL.md) and message in [positioning](../contexts/marketing/positioning/SKILL.md).

## product/vision — The bet

A two-person technical team can produce the output of a ten-person team when
agents do the mechanizable work and the humans concentrate on specification,
evaluation and correction. **This is a thesis, not a measured result.** It rests
on three conditions:

- model inference keeps getting cheaper per task;
- expertise encoded by the person who holds it compounds, because corrections
  accumulate in reusable files instead of in people's heads;
- the break-even point for automating a task has moved far enough that
  previously marginal work becomes worth automating.

Given those conditions, the limit is whether there is a substrate that captures
the leverage. The dated operating observations
([velocity evidence](../evidence/velocity.md)) count agent-operated
workstreams; they do not measure productivity, and the human-minutes experiment
is shelved.

Choose what to automate with three questions: is the task publicly and
extensively documented; is competent-and-generic output enough; can the result
be evaluated with the rigor you would apply to a contractor? If any answer is
no, decompose the task until each part passes, or keep doing it yourself.
Confident automation of work nobody can evaluate is the failure to avoid.

## product/vision — Three kinds of work

The three questions above sort tasks by whether they can be automated. A
second sort, by how much of the task is known before it starts, decides which
Coga mechanism carries it:

- **Routine**: repeatable upkeep such as fixing merge conflicts or bumping
  dependencies. It runs as recurring templates
  ([`coga/recurring`](../contexts/coga/recurring/SKILL.md)), a ticket's `ticket.py`
  sibling ([`coga/script-tickets`](../contexts/coga/script-tickets/SKILL.md)), or a
  fixed `coga run` recipe (`runner.RECIPES`).
- **Understood**: work you can fully specify before doing it, like a support
  request or a planned feature. It becomes a ticket created with a workflow
  whose steps are frozen ([`coga/workflows`](../contexts/coga/workflows/SKILL.md)),
  and it can be queued through
  [`coga/megalaunch`](../contexts/coga/megalaunch/SKILL.md).
- **Unknown**: work you discover by doing. There is a known cone of what you
  have already done, and beyond it everything is blurred. For this work there
  is `coga chat` (the bootstrap orient ticket), the
  [blackboard](../contexts/coga/blackboard/SKILL.md) as working memory, a human
  rewind that moves the step back and keeps everything learned
  ([`coga/lifecycle`](../contexts/coga/lifecycle/SKILL.md)), `## Superseded
  designs` kept on disk but out of the prompt
  ([`coga/blackboard`](../contexts/coga/blackboard/SKILL.md),
  [`coga/prompt-composition`](../contexts/coga/prompt-composition/SKILL.md)),
  `coga ticket` re-authoring at
  any status ([`coga/tickets`](../contexts/coga/tickets/SKILL.md)), and
  [Dream](../contexts/coga/dream/SKILL.md) for the maintenance that follows.
  A wrong premise is usually cancelled and restarted rather than rewound
  ([`coga/lifecycle`](../contexts/coga/lifecycle/SKILL.md) owns the rule).

Coga handles all three kinds, but it is **built for unknown work**. Routine
and understood work are where the human's thinking has already been captured.
Unknown work is where it still happens, and the correction loop in `## Purpose`
exists to serve it. How these pieces run day to day is in `## Operating model`.

## product/vision — Operating limitations (market absorption)

- **The market may absorb it.** If editors, platforms or model vendors ship
  most of this value, keep the method and retire the tool; see
  [`marketing/strategy`](../contexts/marketing/strategy/SKILL.md).

## marketing/distribution — Recorded surfaces and outstanding facts

Extracted from the audit on 2026-09-09. Public observations were recorded on
**2026-09-02/03**; no live account or website was rechecked for the September
10 inventory. Recheck applicable facts, rules and links when selecting a
channel and again before submission. Sources:
[audit evidence](launch-programs/phase-0-audit/step-1-findings.md),
[audit history](launch-programs/phase-0-audit/audit-history.md), and
[the earlier campaign research](launch-programs/campaign-ticket-briefs.md).

| Surface | Recorded observation | Input if the new plan uses it |
|---|---|---|
| [Blog](https://deviantabstraction.com) | WordPress/Jetpack; email signup present; most recent post then was 2026-06-02. No Coga mention found in that audit. | Subscriber count, trailing-30-day views, working subscribe flow and a current reader-path check. |
| [HN account](https://hacker-news.firebaseio.com/v0/user/top256.json) | `top256`, joined 2016; karma 213 as confirmed September 3. Audited history: 26 stories, four scores of 30+ points (87, 52, 47, 32), six Show HN submissions at 1–6 points. | Founder availability, current submission rules, format and supported title. Scores are not observed front-page placement or proof that a title caused a result. |
| [Lobsters account](https://lobste.rs/u/ntoper) | `ntoper`, created 2025-06-05; karma 55. A self-authored submission scored 26 points / 19 comments. | Current community fit, tags, rules and account standing. Previous `vibecoding` / `practices` advice is dated. |
| [Reddit account](https://www.reddit.com/user/Let047/) | Owner reported 7,781 karma, 2,609 contributions, six years and 56 followers; unauthenticated fetches were blocked. | Joined communities and current self-promotion rules. The owner report is not a fresh account check. |
| Bookface / YC | Login-gated; owner standing and feasibility remain unreported. Earlier proposals included a friendly read, Launch YC and YC amplification. | Owner confirms access and decides whether and how to use those surfaces. Prior Bookface-before-HN and second-run timing are archived choices. |
| [fastjvm.com](https://fastjvm.com) | Audit found a JVM research index without a natural Coga link slot; the owner previously chose a one-time announcement. | Reconsider the purpose and placement in the new campaign. |
| Community | Audit found Discussions disabled and no Discord link. | No community setup is required for V1; the earlier proposal is archived. |
| X and personal share asks | Options in the earlier runbook, without an audited account baseline here. | Decide their fit, workload and timing if selected. |

## coga/current-direction — In force (control and data planes)

- **Control and data planes stay split.** `coga launch` owns
  `active` → `in_progress`; `coga bump` owns `step:`; a human rewind is
  recovery for understood work and a normal move for unknown work. Contract:
  [`coga/lifecycle`](../contexts/coga/lifecycle/SKILL.md).
