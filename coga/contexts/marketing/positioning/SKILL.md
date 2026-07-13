---
name: marketing/positioning
description: Marketing-mode context for Coga launch/comms work. Loads Coga's positioning, audience, voice, proof points, and honest limits so an agent writing launch material stays on-message. Attach to any marketing/comms ticket. Source of truth is docs/market-thesis.md and docs/vision.md — when this drifts from them, they win.
---

# Coga marketing positioning

Domain facts for writing Coga's outward comms — launch posts, landing
copy, READMEs, talks, social. This is *what's true about Coga's market
position and voice*; it is not a writing process (that would be a skill).
Distilled from `docs/market-thesis.md` and `docs/vision.md` — read those
for the full argument. When they conflict with this file, they win.

## The spine: independence / ownership

Every piece of Coga comms hangs off one note: **own your machine,
depend on vendors less, the substrate is yours.** This is the *only*
taste an incumbent can't credibly voice — Anthropic already says "amplify
not replace / you're in control," but a business whose revenue scales
with your dependence can't mean "depend on us less" all the way down.
So do **not** lead with "human-in-the-loop" or "amplify your thinking" —
those slogans are commoditized now. Lead with ownership/independence.

- One-liner (vision.md): *"A company OS for small teams in the agentic
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
  high-brow and may not travel. For launch comms, lead with the legible
  version: *a frontier agent is brilliant but blank — it needs your
  grounding, and an ungrounded smart agent acts confidently wrong.*
  Coga is the apparatus that feeds it (contexts = facts, skills =
  procedures, blackboard = state), kept correct by a human-gated loop.
- Concrete over aspirational. Avoid transformation buzzwords ("rewired,"
  "co-contributors") — that's the generic-taste trap (Dust). Earned,
  felt, specific taste is the bar (Linear is the gold standard).

## Proof points — where the taste is *felt*

Coga owns no UI (it borrows the terminal, your editor, Slack), so don't
claim Linear-style pixel polish. The felt moments to dramatize instead:

- **The 2-minute correction loop**: catch the agent doing something
  wrong → open the context → fix one line → re-run → it does the right
  thing. This is the sensory moment; show it.
- **Steered-agent behavior**: the agent reliably does the right thing
  *because* the substrate directed it.
- **Calm Slack feed** over many parallel agents — ambient control.
- It's **your git**: fully inspectable state, no hosted backend, BYO
  agent (claude ↔ codex ↔ any CLI), free / rides your subscriptions.

## Honest limits — do not oversell

Comms must stay credible. State plainly where Coga is outclassed:

- **Fully-managed unattended autonomy is not Coga's default shape**. Coga keeps
  the local, file-backed loop and uses blockers, megalaunch, script tasks, and
  liveness watchdogs for unattended drain; Devin / Symphony / Claude Code win
  on fire-and-forget today.
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

## Open strategic question for the launch

The fork is **not yet decided** — flag it, don't assume:

- **Fork A** — internal OSS infrastructure / honest field report (taste
  as craft). Lower-key launch: recruiting, alignment, the small tribe.
- **Fork B** — Coga-as-category (taste as brand): the Linear playbook
  (opinionated craft, a name, evangelism), narrow-tribe ceiling.

Default is **A with B kept optionable.** Pin the fork with the human
before committing to a launch tone — a fork-B launch is a brand bet, a
fork-A launch is a field report. They read very differently.

## What this context does NOT cover

- How to write / the comms process, templates, channel mechanics — that's
  a skill, not this context.
- The full argument and competitor verification — `docs/market-thesis.md`.
- Product internals / how Coga works — `coga/architecture`,
  `coga/principles`.
