---
name: marketing/positioning
description: Approved V1 instrument positioning, concrete behavior, proof and public-claim limits.
---

# Coga positioning

**Owner decision, 2026-09-21:** Coga is an instrument for the human using
agents. Its purpose is to strengthen human direction and judgment, not to
make agent autonomy the objective.

## Opening and immediate behavior

> Everyone is building infrastructure for agents. Coga is building an
> instrument for the human using them.

The opening is the owner's rhetorical contrast, not a verified claim about
every competitor. Qualify its universal wording where factual precision
requires it. Coga orchestrates work itself; the distinction is where direction,
judgment and the ability to change the system live.

> You set direction. Agents carry the work forward. When something needs
> your judgment, they leave it for you and move on to other work. Your
> corrections become part of how the system works next time.

The queue can move on to other eligible tasks; the task awaiting judgment
stays at its human gate or blocker. Corrections become durable through edits
to the files future runs use, with the existing human review boundaries.
This is not a claim of automatic learning or permission to bypass a gate.

## Proof

Show megalaunch carrying work forward while preserving human decisions,
plus one concrete correction to governing guidance that changes later work.
Support observed behavior with a public demonstration or public Coga record.
A prompt receiving a context alone does not demonstrate the correction's
later effect. The [idea-piece ticket](../../../../coga/tasks/marketing/idea-piece.md)
owns selecting and presenting the example; no separate story pipeline is needed.

Product purpose remains in [vision](../../product/vision/SKILL.md), behavior in
Coga's contracts, and the longer strategic argument in
[strategy](../strategy/SKILL.md). Earlier positioning is
[historical reference](../../../archive/launch-programs/positioning-before-reset.md).

## Root premise — owner follow-up, 2026-10-13

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

## Refinement — owner review session, 2026-10-13

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
  cite the dated [agent memory landscape](../../../evidence/agent-memory-landscape-2026-10-13.md).
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
  the agent or a second agent steps in, and an agent can write them; shared
  rule changes arrive as pull requests. Plan mode is a useful anchor: here the
  plan is a file, reviewed cold by a second agent, approved as a step and still
  there at implementation.
- **Reading guidance.** The human chooses how closely to read; the
  preparing agent's advisory review depth on each pull request
  ([pr-publication](../../coga/internals/pr-publication/SKILL.md)) is a
  suggestion, not a requirement.
- **Audience by posture.** Write for readers who already separate what they
  know from what they are still discovering; teams that plan unknown work as
  if it were known will feel overhead. Targeting itself belongs to the
  first-users ICP context; this is README voice only.
- **Vocabulary.** The product term is "context". Describe contexts as stating
  facts and contracts; avoid "documentation", which readers distrust.

## Source and claim limits

- **Owner follow-up, 2026-10-13.** Never position Coga as an audit,
  governance or compliance tool, and do not use those words. No novelty or
  priority words ("first", "only", "new", "unique"): individual features have
  close prior art (see the dated
  [landscape](../../../evidence/agent-memory-landscape-2026-10-13.md)). Avoid
  category words that file Coga under shared AI knowledge: "knowledge
  compounds", "learn once", "multiplayer", "company brain". Do not say
  "human at the center", "human-centered", "human-in-the-loop" or
  "progressive disclosure". Reading is chosen per pull request; never imply
  the human reads everything or that Coga forces a review. Code is "cheap
  enough to throw away", never free.

- Use public support for claims about actual Coga work: dated tickets, log
  entries, contexts, diffs, PRs or a newly recorded public demonstration.
- Authored examples are allowed. Identify them as illustrations or proposed
  walkthroughs, and do not present invented events or results as observed.
- A context included in a prompt proves delivery. A claim about successful
  reuse also needs the later work that demonstrates it.
- All private-repo narrative quotations from the audit are excluded from
  writing sources. The attachment that held them
  (`coga/tasks/marketing/phase-0-audit/narrative-candidates.md`) was deleted
  from the tree; do not recover it from history or re-collect the material.
- No "first", "only" or priority claim for managing the prompt: close
  precedents exist (see the dated claim check in
  [market landscape](../../../archive/market-landscape.md)).
- No measured productivity multiplier or unsupported token/time saving.
  Vision's output ratio is a product bet, not evidence of an achieved result.
  The marketing token experiment remains dropped.
- Keep concrete product limitations in view: setup and self-support,
  inspectable local files, explicit human judgment, and the actual workflow
  and execution behavior. Do not turn illustrative copy into a promise of
  managed autonomy or universal results.
- Do not say Coga forces the reader to read a ticket: `coga launch` activates
  a draft. Say instead that what you read is what the agent gets.
- Admin and patent use may be cited through
  [usage comparison](../../../evidence/usage-comparison.md#core-flexibility-across-administrative-and-patent-work);
  do not describe the operator beyond what the public record states.
- Statements about what other tools do not do are dated observations ("at the
  2026-10-13 check"), never "nobody else".
