# Market thesis — no moat, only taste

> **Scope.** This is the strategic companion to [`vision.md`](vision.md). Vision says *why Relay exists and how it works*. This doc says *what the market actually is, where value and durability live in it, and how to read competitors and ourselves against that.* It is opinion, argued from first principles and checked against shipping products as of mid-2026. Where it conflicts with reality, reality wins — update the doc.

---

## The thesis in one line

**In the layer Relay lives in — agent orchestration, knowledge management, ticketing — there is no defensible moat. There is only taste. Taste, once adopted by enough people, hardens into a metaphor and a brand, and *that* is the only durable thing in this category.**

Everything below is the argument for that sentence and its consequences.

> **TL;DR** (if you read nothing else):
> 1. **No moat in this layer — only taste** (legibility ⊥ defensibility; the mechanism is commodity, proven by OpenAI open-sourcing it as Symphony).
> 2. **Taste hardens into metaphor + brand** — the only durable thing (the Jira→Linear proof). Ours is *independence/ownership*, the one note an incumbent can't play credibly.
> 3. **We're fork A today** (internal infra), not fork B (a branded category) — fork B is available but needs adoption work we haven't started.
> 4. **The taste is real but *read*, not yet *felt*** — and the felt layer is gated behind a handful of maturity bugs (Slack drops posts, auto-mode disabled, no watchdog). **Shipping the bug backlog *is* the strategy.** See [What's missing — the 80/20](#whats-missing--the-8020).

---

## Why there is no moat in this layer

Four moves, each independently true, compounding:

**1. Legibility and defensibility are opposites.** A moat needs either opacity (they can't see how it works) or lock-in (they can't leave). Relay's whole thesis is the inverse — legible, ownable, no lock-in. Every property that would make the format or the workflow defensible is a property we deliberately removed. The non-defensibility is the design working as intended, not a gap.

**2. The mechanism is borrowed or trivial on purpose.** The skill/context format *is* Anthropic's SKILL.md, verbatim — adopting an open standard is the opposite of a moat; it's a dependency. The workflow primitive is a simple linear state machine, weaker than the parallel/dynamic orchestration competitors already ship. Neither is worth defending, and both were engineered to be copyable.

**3. The model is eating its complements.** Orchestration is commoditized (everyone has a control plane — it's the contested battleground, not an open field). Integrations are commoditizing now: a frontier model + MCP + computer-use dissolves the connector-count moat, and app vendors shipping their own MCP servers disintermediates the aggregator entirely. Memory, RAG, tool-use, "skills" — each was a startup category, each is being absorbed into the model plus a thin open standard. The durable moats in the *whole stack* collapse to two: **the model itself** (capital/compute/talent) and **raw distribution/brand**. Everything in between trends to "feature the model absorbs."

**4. Therefore the only differentiation left in the middle layer is taste.** When the engine commoditizes, differentiation is forced up to the layer of *opinion about how the work should feel*. This is not a consolation prize. Taste is the **hardest** thing in the stack to replicate — harder than a model (which is capital) or integrations (which is labor) — because it can't be bought or brute-forced *fast*. It's slow to copy, not impossible (the Jira→Linear section below shows taste *does* get copied — every "Linear-for-X" — it just takes time). So the moat isn't "uncopyable"; it's **the lead, compounded into a brand before the copy lands.** "No moat, just taste" really means "no *cheap* moat — only the expensive, scarce, head-start one."

---

## How taste becomes durable: the Jira → Linear proof

The work-management category is the existence proof that **no tool here has ever had a technical moat.**

- **Jira** is architecturally unremarkable, widely disliked, trivially replicable — and one of the stickiest products in software. Its moat is not code. It is that Jira **colonized how a generation thinks about work**: epics, sprints, tickets, boards. You can't leave Jira because your org's brain is shaped like Jira. The metaphor *is* the lock-in. Plus incumbency and institutional process ossified around it.

- **Linear** beat an entrenched incumbent with **zero technical advantage**, purely on **taste** — a sharper metaphor, opinionated craft, and brand. Its own marketing says the quiet part out loud: *"the quality of a product is driven by the taste of its makers"*, *"issue tracking you'll enjoy using."* Linear is literally "Jira, with taste," and that was enough to win a category everyone thought was locked.

The chain, generalized:

> **taste → (adopted at scale) → metaphor + institutional embedding + brand → durability.**

Taste is the input. Metaphor and brand are the durable outputs. The model commoditizing the engine doesn't threaten this — it *forces* it, exactly as commodity databases forced the work-tracking fight up to the Linear-vs-Jira taste layer.

The critical caveat: **a metaphor only you use is not a moat — it's a convention.** Jira's metaphor is a moat because millions of brains are shaped like it. Linear's brand is a moat because they did the brand work. You cannot have the metaphor/brand moat without *distributing* the metaphor. Taste you keep to yourself is craft, not a moat.

---

## The metaphor: compile your company

A tool's taste lives in the **structure of thinking it forces**. Jira forces epics/sprints. Relay forces something deeper and more demanding: it **refuses to let you stay vague.** It makes you convert tacit, in-your-head, fuzzy operational knowledge into explicit, decomposed, classified, legible, editable artifacts — and treat every error as a defect in those artifacts. It imposes on *operations* the precision a programming language imposes on logic. Hence: **compile your company.**

Five moves it forces, none skippable:

1. **Decompose to the evaluable unit** — break work down until each leaf is something you can actually *verify* (the three-question filter). You can't hand the agent a fog. "The decomposition is the work."
2. **Externalize the tacit** — if it matters, it becomes a file. Nothing important stays in your head or in chat. (Polanyi in reverse: it forces you to *tell* what you know.)
3. **Classify knowledge vs. process** — for everything you know: a *fact about the world* (context) or a *way of doing* (skill)? A forced ontology on your own expertise.
4. **Separate durable from ephemeral** — contexts (truth) vs. blackboard (working memory) vs. log (history). Constant sorting of "passing note or durable truth?"
5. **Correct systemically, not locally** — fix the *rule*, not the instance. Every mistake asks "what was missing from the substrate that let this happen?" — converting one-off fixes into compounding knowledge.

**Why the taste is *felt* as clarity.** The pleasure isn't snappiness — it's the clarity that comes from being made to think this way (the same satisfaction as well-factored code or a clean proof). The tool's taste is that it makes *you* more rigorous and your operation legible *to yourself*. That is the Lisp/homoiconicity lineage made operational: the constraint produces the pleasure.

**The cost is the same coin.** The forcing function is *demanding*; most people don't want to be made to externalize and decompose (romantic tools exist to spare them that). So the tribe that loves Relay is the one that gets pleasure from rigor — engineering taste applied to operations. The forcing function is simultaneously the source of the taste *and* the reason the door is narrow.

This is the candidate metaphor — Relay's epics-and-sprints. Far more demanding than Jira's bureaucratic one ("think like a compiler engineer about your own company"), so it will never go mass, but it could own its tribe completely: once you think this way you can't unsee it, and no romantic tool can give it to you — *giving* it to you is forcing the rigor they're built to remove.

---

## Taste: imposition vs. subtraction (Relay vs. Linear)

Linear and Relay are both taste-led, but opposite *kinds* of taste.

- **Linear's craft is what it took away.** It looked at Jira's infinite configurability and *removed* it. Subtractive taste — fewer options, less ceremony, less friction. Its genius: you think about your *work*, never the *tool*. Felt as **speed**.
- **Relay's craft is what it makes you do.** It *adds* a forcing function (the five moves). Impositional taste. It makes you think harder, through the tool. Felt as **clarity**.

| | Linear | Relay |
|---|---|---|
| Forces you to | move fast, decide, ship | slow down, articulate, externalize |
| Felt as | speed / frictionlessness | clarity / rigor |
| Craft is in | what they removed | what they make you do |
| Felt where | the **surface** (owns the UI — immediate, seconds) | the **loop** (owns no surface — cognitive, felt when correction pays off) |
| Market consequence | subtraction removes work → **broad** | imposition adds work → **narrow tribe** |

**The lesson to steal:** the two aren't enemies. The best Relay applies *Linear-style subtraction to the act of being rigorous* — strip the friction out of complying with the forced structure so rigor feels like flow, not homework. The **2-minute correction loop is already this** (subtraction applied to "fix the rule"). The opportunity is to extend that frictionlessness to the other four moves. **"Make rigor feel like flow"** is the Relay-meets-Linear thesis: keep the imposed structure (that's the taste), subtract the friction of getting there (that's how it becomes *felt*).

---

## The landscape: absorption ↔ imposition

The deepest axis ordering the whole field is the vision's romantic↔classical, made concrete:

> Does the tool **absorb the work so you don't have to think** (romantic), or **force you to externalize and own your operational knowledge** (classical)?

`Viktor —— Notion —— Dust —— Symphony —— Codex / Claude Code ————————— Relay`
`(absorb everything) ··········(absorb the task)··················(impose ownership)`

*Competitor copy, funding, and feature claims below verified 2026-05-31; these rot fastest — re-verify quarterly.*

| Player (mid-2026) | Forced structure of thinking | Taste · where felt | vs. Relay |
|---|---|---|---|
| **Viktor** (Slack/Teams "AI coworker," $75M A) | "**A hire, not a tool.**" Delegate to a colleague and forget; it returns finished PDFs/apps/commits. | Pure subtraction of *your cognition* · felt as *relief*. Opaque by design. | The opposite pole. Viktor removes you from understanding; Relay forces you in. Romantic absolute. |
| **Notion** (Custom Agents) | "**Model your world as blocks/DBs; let agents write back into them.**" | Subtraction of structure (infinite malleability) · felt in the surface. Malleability *without* opinion → rots. | Notion supplies no discipline (you must); Relay imposes it. Notion hides state in nested pages; Relay forces legibility. |
| **Dust** | "**You're an AI Operator orchestrating multiplayer agents over company knowledge.**" | Aspirational/transformation taste · weakly felt (cloud console). | Platform thinking (configure in their cloud) vs. substrate thinking (externalize into your git). |
| **OpenAI Symphony** | "**Manage work, not agents.**" Tickets-as-state-machine, one autonomous agent per ticket, respawn on crash. | Imposes a pipeline but **subtracts the human from the loop** · felt as throughput (6× PRs). | **The uncanny mirror — same skeleton, inverted soul** (below). |
| **Claude Code** | "**Converse with an agent that acts on your real files.**" Session-centric, ephemeral. | Subtraction of the gap between intent and change · *strongly felt* in the loop. | **Engine Relay drives, not a rival.** It forgets (session); Relay remembers (blackboard/contexts). |
| **Codex** | Same shape, OpenAI flavor: delegate coding tasks, parallel cloud sandboxes, "endurance." | Subtraction of toil · felt as fan-out. Ephemeral. | **Engine Relay drives** — Relay's `other-agent` peer reviewer. Codex executes; Relay orchestrates + persists. |

**Contrast 1 — everyone sprints toward absorption; Relay is the lone imposition bet.** The taglines are a chorus of "think less": Viktor "a hire," Symphony "manage work *not* agents," Notion "works on your behalf 24/7," Codex "endurance." Relay sells the opposite — *think more clearly, own the result*. Not behind the field; the only classical tool in a romantic stampede. That's why its market is the small tribe who *wants* the imposition, and why no incumbent will build it (you can't sell "think harder" at scale).

**Contrast 2 — Symphony is Relay's doppelgänger: same mechanism, opposite values.** Describe Symphony's plumbing (tickets as units, board as state machine, one agent per ticket, respawn crashed agents, model-agnostic-ish) and you've described Relay's. But: Symphony = *"manage work instead of supervising agents"* (human out of the loop, throughput-first, state in Linear's cloud); Relay = the correction loop (human *in*, legibility-first, state in your git, auto-mode deliberately disabled). **OpenAI open-sourced the mechanism — proof the mechanism is commodity. The only thing left to differ on is taste/values, and Relay's are the contrarian ones.**

---

## Judging competitors on the taste axis

The naïve question — "do they sell taste or a feature list?" — turns out to be the wrong cut, because **almost everyone serious already sells taste.** The homepage copy (checked mid-2026) is overwhelmingly worldview-and-feeling, not spec sheets. So the real axis is one level up: **the *quality* of the taste — specific, felt, and earned (you sense it in the product) vs. generic, aspirational, and buzzword (transformation language anyone could write).**

| Player | Quality of taste | Actual hero copy (mid-2026) | Read |
|---|---|---|---|
| **Linear** | **Specific + felt** (the gold standard) | "A new species of product tool." "Purpose-built… designed for the AI era." Customer line they chose to feature: *"You just have to use it and you will just feel it."* Zero feature bullets in the hero. | The model. Taste so specific it's a sensory claim, and it's *true in the product*. Won a locked category on this alone. |
| **Dust** | **Generic / transformation taste** | "Multiplayer AI for human-agent collaboration." "Work doesn't just get done – it gets rewired." The "AI Operator" identity. | Not a feature-lister — but the taste is buzzword-aspirational ("rewired," "co-contributors"), the kind anyone could write. Identity invented (AI Operator), not felt. Taste as *positioning*, not as *craft*. |
| **Anthropic — Cowork** | **Warm + outcome taste** | "Delegate to Claude, delight in the result." "Set it once, skip the ask." Brand line: *"Keep thinking"* / "amplify your thinking rather than replace it." | Real taste, and *adjacent to ours* — "amplify not replace," "you're in control" gestures at the human-primacy territory we thought was ours. But it's brand veneer over a dependency business (the whole point is you keep using Claude). |
| **Jira** | **Features + incumbency** (the lone holdout) | Capability + administration; no opinionated craft. | The foil. Durable by embedding, not taste — and therefore beatable *on taste*, which Linear proved. |
| **Cursor** | Felt taste for devs, diffusing | Craft/speed for developers, sliding toward a capability list (models, background agents, computer use) as it scales. | Real taste at the core, eroding into features under growth pressure — the cautionary tale. |

**Corrected pattern (this is the important update):** the agent-native category is **not a taste vacuum — it's a taste *crowd*.** Everyone has learned to sell worldview. The vacuum is narrower and harder: **specific, felt, *earned* taste — taste you experience in the product, not just read on the landing page.** Only Linear clears that bar today; Dust and Anthropic sell *aspirational* taste (well-written positioning) without the felt-in-use craft that makes Linear's a moat.

And one uncomfortable finding: **Anthropic's "Keep thinking / amplify not replace / you're in control" is encroaching on the exact human-primacy taste we assumed only we could own.** The difference is authenticity, not territory: Anthropic *says* "amplify, don't replace" while running a business that needs you maximally dependent on Claude. The one note they can't play *credibly at scale* is **independence/ownership** — "depend on vendors less, own your machine." Not because they can't say the words (Anthropic already ships open SKILL.md), but because a business whose revenue scales with your dependence can only sell independence as a wedge, never as the spine — the asymmetry isn't "can't say it," it's "can't mean it all the way down." That, not "human-in-the-loop" (now commoditized as a brand line), is the only taste left that an incumbent can't honestly voice.

---

## The strategic fork for Relay

Two clean positions; we must pick, because they imply different work:

**A. Internal OSS infrastructure (taste-as-craft).**
Relay is the substrate FastJVM runs on. No moat, and that's correct — defensibility is the wrong axis for a tool you don't sell. Publishing costs nothing; the payoffs are recruiting, alignment, and being an honest field report for the small tribe this fits. Taste here is craft for its own sake. The only live strategic input is a periodic **build-vs-adopt check**: when the incumbents absorb ~80% of what Relay does for us, migrate the methodology and retire the tool — a planned, graceful outcome, not a loss.

**B. Relay-as-category (taste-as-brand).**
A real, durable, model-proof moat *is* available — the metaphor + brand moat that Linear and Jira have. But it is **earned through adoption**, not owned through code: the Linear playbook (opinionated craft, a name people rally around, evangelism), not the "run it internally" path. The opening is real: the category is a taste vacuum, and our taste — *classical-mode, owner-operated, legible, neutral, depend-on-vendors-less* — is one the incumbents **can't credibly adopt** (Anthropic can't sell "depend on us less"; Dust can't sell "thin and legible") because their business models contradict it. That asymmetry is the one durable thing left, and it's a brand position, not a feature.

**But mind the ceiling.** This is *not* the full Linear move. Linear broadened because subtraction broadens; Relay's own thesis (above) says imposition *narrows*. So fork B is "own a small tribe **completely**," not "win a mass category" — the *playbook* is Linear's (craft, a name, evangelism), the *ceiling* is not. Don't let the word "category" import Linear-sized expectations; the demanding forcing function keeps the door narrow on purpose.

There is no third position where you get the moat without doing the adoption work.

---

## Are *we* talking in taste or features? (self-judgment)

Honest read, because the thesis cuts both ways:

- **Our narrative (vision.md, README) is the most taste-saturated comms of anyone in the table** — a full worldview (Pirsig's classical mode, homoiconicity, the correction loop, "humanist tech for people who still want to understand their own machines"). On the *comms* axis we are not the feature-talkers; if anything we are *more* opinion-led than Linear.
- **But two real risks, both the inverse of the competitors' problem:**
  1. **Essay-taste is ahead of product-taste — but "product" here is not a UI.** Relay is *agent-mediated*: the human barely drives the CLI directly; the agent does. So judging it by Linear's yardstick (felt in keyboard/speed/pixels) is a category error — Relay deliberately owns *no* sensory surface. It borrows the terminal, your editor, and Slack. That's a direct consequence of the markdown-first / legibility principle: choosing not to own a UI means you can't *design* the felt layer the way Linear does. For an agent-mediated tool, felt taste lives somewhere else entirely (see below), and that's where the gap actually is.
  2. **Our taste is high-brow and may not travel.** Lisp, GEB, Hearsay-II, Pirsig is genuine taste but dense; Linear's taste is accessible ("you'll enjoy using"). High taste that only a tiny tribe can parse is craft, not yet a brand. If we ever pick fork B, the metaphor has to be sayable without the reading list.

- **Our differentiator narrowed to one word: independence.** Now that "human-in-the-loop / amplify not replace / you're in control" is commoditized brand language (Anthropic's "Keep thinking" already owns it), our defensible taste is *not* human-primacy in general — it's **ownership/independence specifically**: own your machine, depend on vendors less, the substrate is yours. That's the one note in the chord an incumbent can't honestly play, and it should be the spine of any Relay comms.

**Where felt taste lives for an agent-mediated tool.** Not in pixels — in two moments the human *does* experience: (1) **the correction loop** — catching the agent doing something wrong, opening the context, fixing one line, re-running, and watching it do the right thing in two minutes; and (2) **the steered-agent behavior** — the agent reliably doing the right thing *because* the substrate (contexts, workflow, blackboard) directed it well. Plus the ambient layer: the Slack feed feeling like calm control over many parallel agents. Linear's "you'll just feel it" happens in seconds of UI; Relay's equivalent happens the first time the correction loop snaps shut cleanly. *That* is the sensory moment, and it's a real one.

**So "not felt yet" splits in two:**
- **Mostly: not there yet (maturity).** The surfaces that carry the felt experience are exactly the ones currently broken or disabled — Slack silently dropping posts (ambient awareness dead), auto-mode disabled so you can't *watch* the agent work, no liveness watchdog so an unattended run can stall. The felt layer is gated behind the very bugs in the backlog. Fix those and the correction-loop moment comes online. This is the dominant cause and it's fixable.
- **Partly: structural (permanent).** Relay will never have Linear-style pixel-craft because it owns no UI by design. Its felt taste *must* live in the loop and the agent's steered behavior, not in a surface it controls. That's a constraint to embrace, not fix — and it means the felt-taste playbook for agent-mediated tools is unwritten (nobody's nailed it yet), so it's a real but *unproven* moat surface.

**Verdict:** we are *not* drifting into feature-talk — that was never the risk; if anything we out-taste everyone on conviction. The real gaps: (a) the felt layer is *gated by maturity bugs* (the correction loop can't be felt while Slack drops and auto-mode won't stream) — so shipping the backlog *is* the taste work; (b) make the metaphor *legible to outsiders* without the Pirsig/Lisp/GEB reading list; (c) anchor on **independence/ownership**, the one taste an incumbent can't copy. Until (a) lands we are fork A: high-craft internal infra with an unusually good essay — taste that's *read*, not yet taste that's *felt* — and the path from read to felt runs straight through the bug backlog, not through a design system.

---

## What's missing — the 80/20

The product is ~80% there, and the 80% is real: the **classical substrate works for attended, single-operator use.** Built and tested today — the primitives (tasks / contexts / skills / workflows / blackboard), prompt composition, the task state machine, a real schema validator, the supervised interactive REPL with done/panic detection, git-backed everything, cross-vendor chaining (claude ↔ codex), and genuine SKILL.md-format adoption. That is the original stance *built*: you can run real work through Relay, watch it, correct it, and own every artifact.

The missing 20% is not evenly spread — it clusters in one place, and it is exactly the part that turns the stance from *stated* into *lived*. **It is the transition from "watch it" to "trust it."** Relay nails *watch it* (attended interactive). It does not yet do *trust it* (unattended, recurring, reliable) — which is the half that converts Relay from "a way I work with agents" into "the substrate that runs my company," i.e. the actual thesis.

Three buckets, in priority order:

**Bucket A — the loop isn't *felt* (the felt-taste gap).** The correction loop is the sensory payoff, and it's currently broken by maturity bugs, not design:
- **Slack silently drops posts** (`slack.py:97` ignores the HTTP response) → the ambient-awareness layer is dead. *(ticket: `slack-post-ignores-http-response…`, HIGH)*
- **auto-mode disabled** (`launch.py:202`) → you can't *watch* the agent work or feel it being steered. *(ticket: `stream-agent-progress…`)*
- Fixing these is the difference between taste-that's-read and taste-that's-felt.

**Bucket B — can't be *trusted unattended* yet (the maturation arc).** The vision's whole arc is attended → trusted-automation → cloud. The graduation is blocked:
- **recurring** not landed (lands ~next week, now that autobump works) — without it there is no real automation story.
- **no liveness watchdog** → a wedged task stalls the sequential sweep forever. *(ticket: `supervisor-liveness-watchdog…`)*
- **non-atomic writes** → a 3am crash corrupts the ticket the next sweep reads. *(ticket: `atomic-writes…`, low — git is the backstop)*
- This bucket is the 20% that matters most: it's the entire right half of the spectrum (`watch it → trust it`).

**Bucket C — format bet not enforced / prompt hygiene (credibility polish).**
- **no SKILL.md conformance validation** — `relay validate` checks only that refs resolve, never that the files conform to the format we bet on. *(ticket: `validate-skill-md-frontmatter…`)*
- **raw frontmatter injected into prompts + no token budget.** *(tickets: `compose-strips-…-frontmatter`, `enforce-a-prompt-token-budget`)*
- **drift**: `status.py:79` still side-effects automerge after the "move it out" change. *(ticket: `drift-status-still-calls-auto-bump…`)*

**The one-line read of the 20%:** the substrate exists; what's missing is the **trust half** (unattended recurring with a watchdog, atomic writes, and working Slack/streaming so the loop is *felt*). That's why it feels like 80% — the classical *idea* is fully built and usable attended; the missing piece is everything that lets you *stop watching*, which is also everything that makes the taste land in the body instead of the head. Ship Buckets A and B and Relay crosses from "an excellent way to work with agents" to "the substrate that runs the company" — the thesis, delivered.

---

## Original and defenseless (the conclusion)

Is there something unique and original here? **Yes — but in the stance, not the parts.**

Nothing in the *mechanism* is original: tickets→agents, a state machine, respawn-on-crash, a blackboard, markdown skills, git-as-state, the correction loop — each is a known idea, and OpenAI open-sourced a near-identical skeleton (Symphony). A patent examiner rejects every claim.

The original thing is the **conjunction and the direction**: Relay is the only coherent attempt to make agent-native company operations **classical** — *owned, legible, neutral, correction-looped, nothing hidden* — at the exact moment the entire field sprinted toward **absorption**. Everyone has the same Lego bricks; only Relay assembles them into *"you understand and own and correct your machine"* instead of *"the machine does it so you don't have to."*

The unique residue is the **full intersection**, because every competitor is structurally barred from at least one corner: Symphony (cloud, autonomy-first), Viktor (black-box hire), Notion/Dust (cloud platform, hidden state), Claude Code/Codex (single-vendor, ephemeral, no owned substrate), Anthropic (cannot say "depend on vendors less"). Nobody holds *owned + legible + neutral + corrected + classical* at once — organized around the one value an incumbent can't voice: **independence/ownership** ("compile your company so *you* own and understand it").

And the honesty that ties the whole doc together: **this is original the way a philosophy implemented as a complete system is original — not the way a technology is.** It's taste made coherent and contrarian. A coherent contrarian point of view is genuinely scarce in practice (almost everyone copies the stampede), so it is real and rare — but it is a *stance*, which means it is original *and* freely copyable, for the identical reason. **Its originality and its non-defensibility are the same fact.** Original and defenseless.

Last caveat: right now the original thing lives more in the *conception* (vision, principles) than in the *product* (the loop isn't felt, auto-mode is off). So: **original in stance, not yet original in experience** — and the bridge is the 80/20 above.

---

## What to re-check, and when

- **Build-vs-adopt** (fork A's only live input): when an incumbent substrate does ~80% of what Relay does *for us*, migrate the methodology and retire the tool.
- **Taste vacuum** (fork B's window): watch whether anyone runs the Linear move for agent-native ops. If a well-branded, opinionated, owner-operated competitor appears, the window for B is closing — and notably, it won't be Anthropic or Dust (they're conflicted out of our taste); it'll be another neutral, opinionated builder.
- **The model climbing into the substrate** (the only real risk to A): Skills + Cowork + Managed Agents are the first steps. The one place they won't climb is cross-vendor neutrality — the same asymmetry that anchors fork B.
- **Landscape table facts** (the fastest-rotting part of this doc): re-verify competitor hero copy, funding, and feature claims quarterly; last checked 2026-05-31.
