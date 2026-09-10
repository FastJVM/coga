---
name: marketing/positioning
description: Marketing-mode context for Coga launch/comms work. Loads Coga's positioning, audience, voice, proof points, and honest limits so an agent writing launch material stays on-message. Attach to any marketing/comms ticket. Product purpose comes from docs/vision.md and strategy from docs/market-thesis.md; dated owner message decisions are recorded here.
---

# Coga marketing positioning

Domain facts for writing Coga's outward comms — launch posts, landing
copy, READMEs, talks, social. This is *what's true about Coga's market
position and voice*; it is not a writing process — that is
`marketing/write-post`.
Product purpose comes from `docs/vision.md`; strategic reasoning comes from
`docs/market-thesis.md`. This file owns the current message direction and voice.
Resolve discrepancies by subject and dated owner decision; do not silently
promote older strategic prose above a newer message correction.

## Pitch direction — owner correction, 2026-09-08

Lead with Coga as a way to work with AI by managing what it works from: the
intent, instructions, relevant knowledge, and current working state. The human
and agent can shape those inputs together; readable files carry them into a
later session, and Coga composes the selected material into that session's
prompt. The interface includes conversation, planning, execution and correction.

Make the interaction concrete before introducing the company-OS category or
the parallel work queue. Ownership is present from the beginning: the material
being selected and corrected is visible and editable in the user's repo.
Explain one real task from rough intent through execution and a correction
that is available to later work.

Source: the owner correction and managed-prompt clarification in
[coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md](../../../tasks/redo-documentation-dir-and-merge-it-with-context-b.md).
The correction settles the direction, not final copy or historical uniqueness.
`marketing/plan/write-the-pitch-and-narrative` owns the reusable pitch and
narrative from the story/example decision ticket. Its owner review must
reconcile the message with the retained three-post briefs in `marketing/plan`.

## The spine: independence / ownership

Every piece of Coga comms hangs off one note: **own your machine,
depend on vendors less, the substrate is yours.** This is the *only*
taste an incumbent can't credibly voice — Anthropic already says "amplify
not replace / you're in control," but a business whose revenue scales
with your dependence can't mean "depend on us less" all the way down.
Make ownership concrete inside the opening interaction: the reader can inspect
and change the material the agent works from. "Human-in-the-loop" and
"amplify your thinking" need that mechanism to carry the claim.

- Supporting category line (vision.md): *"A company OS for small teams in the agentic
  era. Humanist tech for people who still want to understand their own
  machines."*
- The bet, in three words: **don't don't think.** The tool sharpens your
  judgment instead of removing it.
- Category: **operations-as-code** — version-controlled, legible,
  agent-executable markdown for operational work. Coga is an engineered
  *runtime* for that discipline, not a convention and not an agent
  framework.
- The metaphor: **compile your company** — Coga refuses to let you stay
  vague; it makes you externalize tacit operational knowledge into
  explicit, editable artifacts. Coga's "epics and sprints."

## Audience — a narrow tribe, owned completely

Coga is **classical in a romantic stampede**: every competitor sells
"think less" (Viktor "a hire," Symphony "manage work not agents," Cowork
"set it once"); Coga sells "think more clearly, own the result."

- The tribe: people who get **pleasure from rigor** — engineering taste
  applied to operations. Small builders/operators who want to understand
  and correct their own machines.
- This is **not a mass play.** Imposition narrows; the forcing function
  keeps the door narrow on purpose. Goal is "own a small tribe
  completely," never "win a mass category." Don't write copy that
  promises effortless mass appeal — it's off-brand and untrue.

## Voice

- Opinion-led and worldview-saturated — more so than Linear. We are not
  feature-listers. Sell the worldview, not a spec sheet.
- **But keep it sayable without the reading list.** The thesis leans on
  Pirsig / GEB / Lisp / homoiconicity; that's genuine taste but
  high-brow and may not travel. After the concrete opening interaction, use
  the explanation: *a frontier agent is brilliant but blank — it needs your
  grounding, and an ungrounded smart agent acts confidently wrong.*
  Coga is the apparatus that feeds it (contexts = facts, skills =
  procedures, blackboard = state), kept correct by a human-gated loop.
- Concrete over aspirational. Avoid transformation buzzwords ("rewired,"
  "co-contributors") — that's the generic-taste trap (Dust). Earned,
  felt, specific taste is the bar (Linear is the gold standard).

## Proof points — where the taste is *felt*

Coga owns no UI (it borrows the terminal, your editor, Slack), so don't
claim Linear-style pixel polish. The felt moments to dramatize instead:

- **The correction loop**: show the agent's mistake, the exact governing
  edit, and the later behavior the public record actually supports. Use the
  source's details without adding a duration or promising that a rerun works.
- **Steered-agent behavior**: the agent reliably does the right thing
  *because* the substrate directed it.
- **Calm Slack feed** over many parallel agents — ambient control.
- It's **your git**: fully inspectable state, no hosted backend, BYO
  agent (claude ↔ codex ↔ any CLI), free / rides your subscriptions.

## Honest limits — do not oversell

Comms must stay credible. State plainly where Coga is outclassed:

- **Fully-managed unattended autonomy is not Coga's default shape**. Coga keeps
  the local, file-backed loop and uses blockers, megalaunch, deterministic
  script tickets, and liveness watchdogs for unattended drain; Devin / Symphony /
  Claude Code win on fire-and-forget today.
- Workflow is a **linear state machine** — heavy parallel/dynamic
  orchestration → frameworks (LangGraph et al.).
- **Self-hosted, self-supported** — no managed reliability / SLA.
- Not zero-setup (that's `CLAUDE.md`).
- "Shipping the bug backlog *is* the strategy" — the felt layer is gated
  behind the maturity fixes (Slack drops, megalaunch/watchdog polish). Don't
  promise the felt experience the bugs are currently blocking.

## Competitive framing (for positioning, not attack copy)

- **Linear**: the taste gold standard, but *subtractive* (felt as speed);
  Coga is *impositional* (felt as clarity). "Jira→Linear" is the proof
  that taste, not tech, wins this category.
- **Claude Code / Codex**: **not rivals — the engines Coga drives** and
  rotates between. Frame as complement.
- **OpenAI Symphony**: same skeleton (board-as-FSM, stateless agents,
  one-per-ticket, respawn, spec-you-fork), inverted soul (their cloud,
  human-out, Codex-only, code-only). OpenAI open-sourcing it *proves* the
  mechanism is commodity — only taste differs.
- **CompanyOS (Feld)**: nearest framing-twin ("markdown that runs a
  company"), but skills-only, no loop. Owning markdown isn't the
  differentiator — the maintained, human-gated loop is.
- **Paperclip**: manages agents *as a workforce* (roles, budgets,
  approvals, dashboards); Coga manages *work as repo state*. Same orbit,
  opposite center of gravity — Paperclip owns the demo, Coga the substrate.
- **Devin**: the cautionary genre, not a rival — inflated launch claims,
  publicly debunked, never recovered with our tribe. Our anti-claim
  posture (pre-registered, recomputable, misses published) is priced
  against exactly this failure. Quote the claim *genre* ("fully
  autonomous," "+500%") in comms; never name-and-attack the brand.

## Headlines and evidence

- **"Agents do. Humans think." collides with Anthropic's "Keep
  thinking."** They own the megaphone, so in a feed *we* read as the
  echo. The line is keepable, but any headline placement must pair it
  with the note Anthropic can't sing — ownership/independence ("on a
  machine you own", "in your repo, not their cloud"). The humans-think
  note must never stand alone as the positioning.
- **Ground the message in public examples.** Human-minutes per shipped task
  remains an unmeasured historical proposal, not a headline requirement.
  The owner dropped the marketing token experiment on 2026-09-09. Use the
  specific public work, correction and later reuse that a source supports;
  no measured efficiency or productivity outcome is claimed by this series.

  Naming that metric as *defined and deliberately unmeasured* is not a
  violation to be scrubbed. `README.md` and `docs/velocity-report.md` both do
  exactly that today ("defined there but deliberately unmeasured", "until that
  run finishes"), and that disclosure is what keeps the absent number honest.
  What stays forbidden is quoting a figure, implying one exists, or resting a
  claim on it.

## The strategic fork (decided)

**Fork A is pinned** for the launch series — owner decision of 2026-08-19,
preserved here and in `marketing/plan`'s retained campaign. Write to fork A;
do not reopen
the question inside a marketing/comms ticket. Changing the fork is an owner
decision. `marketing/write-post` cites this paragraph at its entry condition
rather than restating the fork.

- **Fork A (pinned)** — internal OSS infrastructure / honest field report
  (taste as craft). Lower-key launch: recruiting, alignment, the small tribe.
- **Fork B (kept optionable)** — Coga-as-category (taste as brand): the
  Linear playbook (opinionated craft, a name, evangelism), narrow-tribe
  ceiling.

The fork sets the launch tone: a fork-B launch is a brand bet, a fork-A
launch is a field report. They read very differently.

## What this context does NOT cover

- Channel/account facts and audience scoring — `marketing/distribution`.
- How to write / the comms process and publication checks — `marketing/write-post`
  (the order of work and the gates), which hands the prose-craft pass to the
  imported `clarity` skill. What each post *says* and when it ships —
  `marketing/plan`.
- The full argument and competitor verification — `docs/market-thesis.md`.
- Product internals / how Coga works — `coga/architecture`,
  `coga/principles`.
