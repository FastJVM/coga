# Market thesis — no moat, only taste

> **Scope.** This is the strategic companion to [`vision.md`](vision.md). Vision says *why Coga exists and how it works*. This doc says *what the market actually is, where value and durability live in it, and how to read competitors and ourselves against that.* It is opinion, argued from first principles and checked against shipping products as of mid-2026. Where it conflicts with reality, reality wins — update the doc.

---

## The thesis in one line

**In the layer Coga lives in — agent orchestration, knowledge management, ticketing — there is no defensible moat. There is only taste. Taste, once adopted by enough people, hardens into a metaphor and a brand, and *that* is the only durable thing in this category.**

Everything below is the argument for that sentence and its consequences.

> **TL;DR** (if you read nothing else):
> 1. **No moat in this layer — only taste** (legibility ⊥ defensibility; the mechanism is commodity, proven by OpenAI open-sourcing it as Symphony).
> 2. **Taste hardens into metaphor + brand** — the only durable thing (the Jira→Linear proof). Ours is *independence/ownership*, the one note an incumbent can't play credibly.
> 3. **We're fork A today** (internal infra), not fork B (a branded category) — fork B is available but needs adoption work we haven't started.
> 4. **The reliability substrate now exists** — checked Slack delivery,
> recurring tasks, supervised liveness limits, and atomic writes have shipped.
> The open strategic question is whether outsiders feel the correction loop,
> not whether those primitives exist. See [What's missing — the 80/20](#whats-missing--the-8020).

---

## The floor under all of it: agents are brilliant and blank

Before any of the market theory, the plain reason Coga exists: **a frontier agent is brilliant and blank.** The intelligence is solved; the *grounding* is not — and grounding is everything you know about your world that isn't in the model's weights: your conventions, your domain facts, last week's decision, how *your* team does the thing. A bigger model never closes that gap, because the facts were never in the weights to begin with — they live in the operator's head and the repo.

And "brilliant" is the dangerous half. An ungrounded capable agent doesn't sit there politely doing nothing — it **acts, confidently, wrongly**, improvising your conventions from priors. So feeding it context isn't optional hygiene; an unfed smart agent is a *liability*, not a no-op. Out of the box it cannot run your company; fed properly it can.

Coga is the apparatus that feeds it: **facts (contexts), procedures (skills), working state (blackboard)** — composed to the right step, and kept correct by a loop because the feed is never right the first time and drifts. That is the whole product. Everything below — the taste, the classical stance, the metaphor — is the argument for why *this shape* of feeding is the right one, and why it can't be bought from a vendor whose interest is the opposite.

**Be honest about what's original here: nothing about the *need*.** "A blank agent needs grounding" is the most obvious fact in the space — every tool is an answer to it (`CLAUDE.md`, modular/glob rules, RAG, on-demand skills, auto-captured memory, spec-driven PRDs). Coga's grounding *delivery* sits at one specific point on that well-mapped spectrum — **explicit, deterministic, author-controlled composition** (you can read the exact prompt; it fails loud on a missing ref), scoped by *process-position*, maintained by a *human-gated* loop — versus the field's center of gravity, which is *opaque, retrieval-driven, auto-captured*. That's a direction, not an invention. Which is the recurring result of this whole doc: dig any layer — orchestration, memory, grounding — and the mechanism is commodity; the only residue is the *direction* it points.

Two consequences worth stating up front, because they survive even the harshest skeptic:

- **The grounding gap is capability-proof.** "Models will get good enough that nobody needs the creating" is the obvious objection, and it's wrong: model quality doesn't touch grounding. A perfect model still doesn't know your payment-flow quirk or yesterday's call. The creating's value is *invariant to model capability* — arguably *rising* with it, since a smarter agent does more with good context and more damage without it.
- **Human-in-the-loop isn't (only) a value — it's a necessity.** The human is the *sole source* of the ground truth the agent lacks. "Externalize the tacit" isn't imposed rigor for its own sake; it is the only way the facts enter the system at all, because they exist nowhere else.

This is the legible, reading-list-free version of the whole thesis — the answer to this doc's own worry that the taste is "high-brow and may not travel."

---

## What kind of thing is Coga? (operations-as-code — a new discipline, not a new technology)

Try to place Coga on a *technology* map — "agent orchestrator," "company brain," "task manager," "agent memory" — and it fits nowhere, yet none of its parts are original. Those two facts are the **same fact**: Coga isn't a technology, it's a **discipline** — and disciplines are always unoriginal in mechanism (they use commodity tools) and invisible on a mechanism map (they aren't on it). TDD, IaC, docs-as-code: none invented a technology; each is a *way of working*.

The discipline is **operations-as-code**: treat operational work — knowledge, process, the work itself — as version-controlled, legible, reviewable, agent-executable markdown. It belongs to the old "X-as-code" family (IaC → GitOps → docs/policy-as-code), but it is a **genuinely new member**, and the reason it couldn't exist before is exact: every "X-as-code" is gated on an *executor that can run domain X*. IaC waited for cloud APIs. **Operations waited for an executor that tolerates ambiguity and natural language — an AI agent — which is ~2 years old**, plus an order-of-magnitude collapse in the cost of automating a task. You cannot write a Terraform plan for "handle this escalation well"; you can write a Coga context + skill and have an agent run it. So operations-as-code is new — *new for everyone*, opened by AI, not invented by Coga.

**The crux is the scope.** Coga's unit is *an operation*, and because the executor is domain-agnostic — with the **mode system** routing deterministic operations to plain-Python `script` mode and judgment-laden ones to agent mode — **one substrate spans the entire operational surface: `pytest` to payroll, dev-ops to back-office.** Deterministic ops (run the suite, create a report) crystallize to `script`; judgment ops (triage failures, draft the board update) use an agent; irreversible ops (payroll: compute by script, **gate by human** before money moves) use both, with the loop. It does **not replace** the test runner or the payroll system — it **orchestrates** them: the agent runs `pytest`, drives the payroll API through a skill, a human gates the irreversible step. Coga is the conductor, not the instruments. What's *shared* across all of it — and why one substrate works for unit-tests *and* payroll — is the universal meta-layer: the knowledge the op needs (contexts), the gate, the audit, the correction loop. Those concerns are identical across every domain. **That generality is what earns the "OS" in "company OS"** — not that it stores company data, but that it's the general-purpose runtime any operation executes on. No neighbor has this scope: CompanyOS is business-ops only, Symphony is code only, LangGraph is build-your-own-per-case.

That points at the structural position, which is an **empty quadrant**:

| | Operations-as-code (run your ops) | Agent framework (build an agent) |
|---|---|---|
| **Convention** (no runtime) | CompanyOS, agent-os, LLMunix | AGENTS.md / rules files |
| **Engineered runtime** | **Coga (≈ alone)** | LangGraph, CrewAI, Mastra, Agentuity |

The operations-as-code players ship **conventions, not tools** — CompanyOS proudly has "no application code, no `src/`." The real **runtimes serve a different genus** — LangGraph et al. are developer frameworks you write code against to *build* an agent, not operator runtimes to *run* an operation. Coga sits in the empty cell, and its **sub-bet within the discipline is contrarian**: that operations-as-code needs a *thin runtime* — the trust layer (fail-loud validation, supervised multi-step launches, vendor-neutral agent rotation, recurring automation, an audit log) — to graduate from a personal markdown hack (which CompanyOS is) into a substrate you can run an org on. The runtime keeps the state legible markdown; it makes the discipline *reliable* without hiding state. (Notice: that trust layer is exactly the 80/20 still being built.)

**So "what is it," resolved:** Coga is an early (≈sole) **engineered runtime for operations-as-code** — a discipline AI just opened, spanning the whole operational surface, occupying the quadrant the conventions and the developer-frameworks both leave empty. Its novelty is three-layered and honestly ranked: a *real but shared* category-novelty (the AI-opened discipline); a *real but copyable* structural position (the empty runtime quadrant — a head-start, not a moat); and the *only durable* layer, the **direction** (human-gated, amplify, legible, owned). At no level is the *mechanism* original — which is why, all the way down, the only defensible axis is taste. **Coga : CompanyOS :: Linear : Jira** — same discipline, opposite gate, claimed on direction.

---

## Why there is no moat in this layer

Four moves, each independently true, compounding:

**1. Legibility and defensibility are opposites.** A moat needs either opacity (they can't see how it works) or lock-in (they can't leave). Coga's whole thesis is the inverse — legible, ownable, no lock-in. Every property that would make the format or the workflow defensible is a property we deliberately removed. The non-defensibility is the design working as intended, not a gap.

**2. The mechanism is borrowed or trivial on purpose.** The skill/context format *is* Anthropic's SKILL.md, verbatim — adopting an open standard is the opposite of a moat; it's a dependency. The workflow primitive is a simple linear state machine, weaker than the parallel/dynamic orchestration competitors already ship — in fact the *least* original primitive in the system (Symphony open-sourced a near-identical board-as-FSM); see [*Locating the originality*](#locating-the-originality-it-isnt-the-workflow) for why the load-bearing primitive is elsewhere. Neither is worth defending, and both were engineered to be copyable.

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

A tool's taste lives in the **structure of thinking it forces**. Jira forces epics/sprints. Coga forces something deeper and more demanding: it **refuses to let you stay vague.** It makes you convert tacit, in-your-head, fuzzy operational knowledge into explicit, decomposed, classified, legible, editable artifacts — and treat every error as a defect in those artifacts. It imposes on *operations* the precision a programming language imposes on logic. Hence: **compile your company.**

Five moves it forces — not on every task, but on the ones whose stakes warrant the climb:

1. **Decompose to the evaluable unit** — break work down until each leaf is something you can actually *verify* (the three-question filter). You can't hand the agent a fog. "The decomposition is the work."
2. **Externalize the tacit** — if it matters, it becomes a file. Nothing important stays in your head or in chat. (Polanyi in reverse: it forces you to *tell* what you know.)
3. **Classify knowledge vs. process** — for everything you know: a *fact about the world* (context) or a *way of doing* (skill)? A forced ontology on your own expertise.
4. **Separate durable from ephemeral** — contexts (truth) vs. blackboard (working memory) vs. log (history). Constant sorting of "passing note or durable truth?"
5. **Correct systemically, not locally** — fix the *rule*, not the instance. Every mistake asks "what was missing from the substrate that let this happen?" — converting one-off fixes into compounding knowledge.

**But the rigor is amortized, not a per-task tax — and the onboarding is smooth.** You don't pay these five moves on every ticket. You pay them *once into the substrate* — contexts about your world, a skill, a workflow — and most tasks afterward are three lines, because they *inherit* that grounding for free (the relevant contexts compose into the prompt automatically). Same as a well-factored codebase: the upfront structure is exactly what makes each later change cheap. And the moves are mostly executed *by the agent*, not typed by you: `coga init` creates, `coga chat` / `coga ticket` run a guided authoring interview that drafts the contexts and workflow while you supply the spec and the judgment. So the floor is genuinely low — draft, launch, done — the ceiling is the full compile, and you climb only as far as a task is worth. The imposition lands on your *judgment* (decide, verify, correct), not your *labor*, and it is the dividend of prior investment, not a recurring toll. This is the "make rigor feel like flow" aim already partly shipping: keep the structure, subtract the friction of producing it. (The honest tail: if you three-lined *everything* and never built any substrate, you'd have plain Claude Code — ephemeral and ungrounded. The Coga value is the owned, correctable substrate your light tasks ride on.)

**Why the taste is *felt* as clarity.** The pleasure isn't snappiness — it's the clarity that comes from being made to think this way (the same satisfaction as well-factored code or a clean proof). The tool's taste is that it makes *you* more rigorous and your operation legible *to yourself*. That is the Lisp/homoiconicity lineage made operational: the constraint produces the pleasure.

**The cost is the same coin.** The forcing function is *demanding* — not in setup labor (the agent eats that) but in the *standing* requirement to stay in the judgment loop: decide, verify, fix the rule. Most people would rather stop thinking entirely (romantic tools exist to spare them that). So the tribe that loves Coga is the one that gets pleasure from rigor — engineering taste applied to operations. The forcing function is simultaneously the source of the taste *and* the reason the door is narrow.

This is the candidate metaphor — Coga's epics-and-sprints. Far more demanding than Jira's bureaucratic one ("think like a compiler engineer about your own company"), so it will never go mass, but it could own its tribe completely: once you think this way you can't unsee it, and no romantic tool can give it to you — *giving* it to you is forcing the rigor they're built to remove.

---

## Taste: imposition vs. subtraction (Coga vs. Linear)

Linear and Coga are both taste-led, but opposite *kinds* of taste.

- **Linear's craft is what it took away.** It looked at Jira's infinite configurability and *removed* it. Subtractive taste — fewer options, less ceremony, less friction. Its genius: you think about your *work*, never the *tool*. Felt as **speed**.
- **Coga's craft is what it makes you do.** It *adds* a forcing function (the five moves). Impositional taste. It makes you think harder, through the tool. Felt as **clarity**.

| | Linear | Coga |
|---|---|---|
| Forces you to | move fast, decide, ship | slow down, articulate, externalize |
| Felt as | speed / frictionlessness | clarity / rigor |
| Craft is in | what they removed | what they make you do |
| Felt where | the **surface** (owns the UI — immediate, seconds) | the **loop** (owns no surface — cognitive, felt when correction pays off) |
| Market consequence | subtraction removes work → **broad** | imposition adds work → **narrow tribe** |

**The lesson to steal:** the two aren't enemies. The best Coga applies *Linear-style subtraction to the act of being rigorous* — strip the friction out of complying with the forced structure so rigor feels like flow, not homework. The **2-minute correction loop is already this** (subtraction applied to "fix the rule"). The opportunity is to extend that frictionlessness to the other four moves. **"Make rigor feel like flow"** is the Coga-meets-Linear thesis: keep the imposed structure (that's the taste), subtract the friction of getting there (that's how it becomes *felt*).

---

## The landscape: absorption ↔ imposition

The deepest axis ordering the whole field is the vision's romantic↔classical, made concrete:

> Does the tool **absorb the work so you don't have to think** (romantic), or **force you to externalize and own your operational knowledge** (classical)?

`Viktor —— Notion —— Dust —— Symphony —— Codex / Claude Code ————————— Coga`
`(absorb everything) ··········(absorb the task)··················(impose ownership)`

*Competitor copy, funding, and feature claims below verified 2026-05-31; these rot fastest — re-verify quarterly.*

| Player (mid-2026) | Forced structure of thinking | Taste · where felt | vs. Coga |
|---|---|---|---|
| **Viktor** (Slack/Teams "AI coworker," $75M A) | "**A hire, not a tool.**" Delegate to a colleague and forget; it returns finished PDFs/apps/commits. | Pure subtraction of *your cognition* · felt as *relief*. Opaque by design. | The opposite pole. Viktor removes you from understanding; Coga forces you in. Romantic absolute. |
| **Notion** (Custom Agents) | "**Model your world as blocks/DBs; let agents write back into them.**" | Subtraction of structure (infinite malleability) · felt in the surface. Malleability *without* opinion → rots. | Notion supplies no discipline (you must); Coga imposes it. Notion hides state in nested pages; Coga forces legibility. |
| **Dust** | "**You're an AI Operator orchestrating multiplayer agents over company knowledge.**" | Aspirational/transformation taste · weakly felt (cloud console). | Platform thinking (configure in their cloud) vs. substrate thinking (externalize into your git). The Dust agent *gets smarter inside their console* — but you don't control that drift, can't inspect it, and pay rent for it: **lock-in and opaque drift in one.** Coga's substrate improves only through human-gated PRs you own and can read. |
| **OpenAI Symphony** | "**Manage work instead of supervising coding agents.**" Linear board as a finite state machine (Todo→In Progress→Review→Merging); one Codex agent per issue in an isolated workspace; respawn crashed/stalled agents. Shipped Apr 2026 as a `SPEC.md` + Elixir reference impl, not a product. | Imposes a pipeline but **subtracts the human from the loop** · felt as throughput (+500% merged PRs in 3 weeks, on OpenAI's own teams). | **The uncanny mirror — same skeleton, inverted soul** (below). |
| **Claude Code** | "**Converse with an agent that acts on your real files.**" Session-centric, ephemeral. | Subtraction of the gap between intent and change · *strongly felt* in the loop. | **Engine Coga drives, not a rival.** It forgets (session); Coga remembers (blackboard/contexts). |
| **Codex** | Same shape, OpenAI flavor: delegate coding tasks, parallel cloud sandboxes, "endurance." | Subtraction of toil · felt as fan-out. Ephemeral. | **Engine Coga drives** — Coga's `other-agent` peer reviewer. Codex executes; Coga orchestrates + persists. |
| **CompanyOS** (Brad Feld) | "**Markdown files that teach Claude Code how to run a company.**" Skills-only, ~2k lines of markdown in git, skills auto-trigger by intent. | Owned/local/legible · felt as *relief* (Claude runs ops for you). | **The nearest framing-twin** — same "company in owned markdown," but skills auto-fire (absorption), Claude-Code-only, and there's *no* state machine, workflow, fact/process ontology, or human-gated correction loop. Holds the substrate corner; not the gate or the forcing function. |
| **Backlog.md / task-master-ai** | "**Markdown tasks in git for AI agents.**" Spec-driven storage + Kanban, MCP-connected. | Subtraction of task-tracking friction · felt in the board. | **The nearest storage-cousin** — same markdown-tasks-in-git surface, but *no* custom workflows, no knowledge/process split, no correction loop, no orchestration. And the markdown is an *export*, not the authoring surface: Backlog.md recommends editing via its CLI "so field types and metadata stay consistent" — the tool is the source of truth. Coga inverts this: the markdown **is** the source of truth and hand-editing is the primary interface (the CLI owns only `status`/`step`/`log`). The filing cabinet, not the loop. |

**Contrast 1 — everyone sprints toward absorption; Coga is the lone imposition bet.** The taglines are a chorus of "think less": Viktor "a hire," Symphony "manage work *not* agents," Notion "works on your behalf 24/7," Codex "endurance." Coga sells the opposite — *think more clearly, own the result*. Not behind the field; the only classical tool in a romantic stampede. That's why its market is the small tribe who *wants* the imposition, and why no incumbent will build it (you can't sell "think harder" at scale).

**Contrast 2 — Symphony is Coga's doppelgänger: same mechanism, opposite values.** Verified against the [openai/symphony](https://github.com/openai/symphony) spec (open-sourced Apr 2026), the shared skeleton is five concrete bones: (1) the board *is* a finite state machine and the single source of truth; (2) agents are stateless between runs, reconstructed from the board on restart; (3) one agent per ticket in an isolated workspace; (4) a supervisor respawns crashed/stalled agents; (5) it ships as a spec you fork, not a product you buy. Describe those and you've described Coga's plumbing exactly. One bone even differs in *shape*: Symphony's state machine is a **single fixed pipeline** (Todo→In Progress→Review→Merging) baked into the spec; Coga's workflow is **author-defined per task type and frozen at creation** — you write your own ordered steps. That's the hackable/own-your-process axis Symphony doesn't have at all. But every bone that carries *meaning* inverts: Symphony = *"manage work instead of supervising coding agents"* (human out of the loop, throughput-first, state in Linear's **cloud**, **Codex-only**, **code→PR scope only**); Coga = the correction loop (human *in*, legibility-first, state in **your git**, vendor-neutral, whole-company scope, no ticket-level auto mode). **OpenAI open-sourcing the skeleton as a `SPEC.md` is the clearest possible proof the mechanism is commodity — they gave it away. The only thing left to differ on is taste/values, and Coga's are the contrarian ones.** The surface is now industry-standard; the divergence is entirely one layer down.

**Contrast 3 — same compounding, inverted gate (Dream vs the auto-memory field).** "Knowledge compounds in markdown" is now commodity too: Claude Code ships a [compounding knowledge loop](https://www.mindstudio.ai/blog/compounding-knowledge-loop-claude-code) — a `Stop` hook auto-extracts learnings into `CLAUDE.md`/`.claude/knowledge/`, *"no human gating,"* review optional and *after*. The broader agent-memory field is the same: accept/reject feedback auto-updates the agent's skills and knowledge. Coga's Dream is the **exact inverse gate**: it reads execution history, classifies drift, and *proposes a PR* — knowledge lands only when a human merges it, never automatically. Same compounding; opposite direction of the gate. This is principle #4 ("memory via PR, human-gated, never opaque") doing load-bearing work, and it is the one corner the searched field leaves empty — everyone auto-captures-then-maybe-reviews; nobody human-disposes-before-it-lands.

### The whole map: what each tool *is* to Coga

One reference table consolidating the field. The point of the last column: each tool isn't a generic "competitor" — it teaches one specific axis on which Coga inverts.

| Tool | What it is | Shares with Coga | Inverts / lacks | The axis it teaches |
|---|---|---|---|---|
| **Claude Code / Codex** | Session-centric coding agents | The actual engine | Ephemeral, single-vendor, forgets, no owned substrate | **Not rivals — the engines Coga drives**, persists, and rotates between |
| **OpenAI Symphony** | Tickets→agents orchestrator over Linear | All 5 skeleton bones (board-as-FSM, stateless agents, one-per-ticket, respawn, spec-you-fork) | State in *their cloud*, human-*out*, Codex-only, code-only, *fixed* pipeline (no author-defined workflow) | **Same skeleton, inverted soul** — mechanism is commodity (open-sourced) |
| **CompanyOS** (Feld) | "Markdown that teaches Claude to run a company" | The *framing* almost verbatim — owned, local, legible markdown | Skills auto-fire, Claude-only, *no* state machine, ontology, or gated loop | **Same framing, no loop** — owning markdown isn't the differentiator; the maintained loop is |
| **Backlog.md / task-master** | Markdown tasks-in-git for agents | The filing-cabinet surface | No custom workflow, no fact/process split, no loop; CLI-is-source (markdown is an *export*) | **Same files, inverted ownership** — Coga's markdown *is* the source of truth |
| **Dust** | Cloud "AI Operator" platform | Multi-agent over company knowledge | Cloud console, hidden state, agent drifts outside your control while you pay rent | **Lock-in + opaque drift** vs owned substrate + human-gated PRs |
| **Viktor / Notion / CoWork** | Absorption tools ("a hire," "works on your behalf") | Little structural | Delegate-and-forget; remove you from understanding | **The opposite pole** — absorb the work vs impose ownership |
| **Auto-memory loops** (Claude Code `Stop`-hook, agent-memory frameworks) | Knowledge auto-captured into markdown | Knowledge compounds in markdown | Auto-captured, ungated, review-optional-*after* | **Same compounding, inverted gate** |

Read down the last column and the thesis is self-evident: Coga is the only entry that holds *every* axis at once, because each is a consequence of the one root the others don't share.

### The capability matrix — who holds which axis

The map above is the *taste* cut (what each tool teaches). This is the *capability* cut: the concrete axes a buyer can check. Two distinctions matter and are easy to get wrong. **(1) Prose-as-code ≠ prose-as-context.** A `CLAUDE.md` is *context* — declarative, "here is how things are." Coga's tickets/workflows/skills are *instructions* — imperative, "do X, then Y, verify Z." The "code" is the imperative layer that tells the agent what to do; Coga keeps it separate from the context layer (the data it acts on), and `CLAUDE.md` has only the latter. **(2) Automation is not binary.** Coga's routing is granular — a task's execution substance (script vs agent) is deduced from its `script:` and workflow steps, and its workflow/assignees decide who acts at each step. The ticket carries neither a mode nor an autonomy flag; unattended drain is handled by blockers, megalaunch, script tasks, and the liveness watchdog.

| Tool | Programmed in | Owned & legible (your git) | Vendor-neutral (BYO-agent) | Batteries that *compound* | Human-gated loop | Domains | Autonomy | Cost |
|---|---|---|---|---|---|---|---|---|
| **CLAUDE.md** | context only (declarative) | partial (a flat file in your repo) | yes (any agent reads it) | **no — it bloats** | no | n/a | n/a | free |
| **Claude Code + ecosystem** (Skills/MCP/plugins/Cowork) | imperative chat + context | no (ephemeral; store/plugins) | no (Anthropic) | assembling (skills/MCP/plugins) — no workflow/ontology/git-substrate | auto-capture, review optional | dev-leaning | partial (background agents) | paid |
| **Devin** | chat / UI | no (their cloud) | no (bundled, opaque) | no (opaque knowledge) | out-of-loop (delegate) | code only | all-or-nothing autonomous | paid |
| **Frameworks** (LangGraph/CrewAI/ADK) | code | no (code, not legible prose-state) | model-neutral-ish | you *build* the batteries | you build it | you build it | you build it | OSS (you build everything) |
| **CompanyOS** (Feld) | prose, but context + skills (no program layer) | **yes** (owned git markdown) | Claude only | skills-only — no workflow/modes/pkg-mgr/loop | no (skills auto-fire) | business-ops | none | free |
| **OpenAI Symphony** | spec / code | no (state in Linear cloud) | Codex only | a spec you fork (board FSM) | out-of-loop, throughput | code only | async autonomous | OSS spec |
| **Coga** | **imperative instructions + separated context** | **yes — your git, fully inspectable** | **yes — claude↔codex↔any CLI** | **yes — composition→skills+pkg-mgr→workflow→modes→loop→gate, and it compounds** | **yes — PR-gated (Dream)** | **code + research + ops** | **granular: autonomous / hybrid / human per step** (fire-and-forget unblocks before release) | **free / open, rides your subscriptions** |

**Where Coga is the only option.** The combination *owned + legible + vendor-neutral + batteries-that-compound + human-gated + cross-domain + free* — nobody else holds it. `CLAUDE.md` is a strict subset (Coga = `CLAUDE.md` + the program layer + batteries + loop); CompanyOS is the only other "owned," but it is skills-only (no workflow, no loop); frameworks are code to *build* an agent, not prose to *run* work. For the buyer who wants to **own, understand, and correct** their agent substrate, across everything, for free — Coga is alone.

**Where Coga is outclassed (state it plainly).** Fully-managed unattended autonomy out of the box → **Devin / Symphony / Claude Code** (Coga keeps the local, file-backed loop and uses megalaunch + scripts for unattended drain). Heavy parallel/dynamic orchestration → **frameworks** (Coga's workflow is a linear state machine). Managed reliability / support / SLA → **paid products** (Coga is self-hosted, self-supported). Zero-setup → **CLAUDE.md** (one file, nothing to learn). Distribution / brand → anyone funded. And none of the axes Coga wins are a *moat* — the whole combination is copyable; the only durable layer is direction (see the conclusion).

**The fastest-closing threat is the Claude Code ecosystem** — it is assembling the batteries quickly. The cells it *structurally* will not close: owned-in-your-git, vendor-neutral, and the human-gated loop. That intersection — not "nobody does the parts" — is the defensible read.

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

And one uncomfortable finding, with an important qualifier: **Anthropic's "Keep thinking / amplify not replace / you're in control" is encroaching on the human-primacy taste we assumed only we could own — but only at the level of the *slogan*, not the *mechanism*.** Anthropic took the words; it has no correction loop, no human-gated knowledge compounding, no substrate the human edits between runs — nothing that puts the human *in* the loop as a working part. So the difference is authenticity *and* substance: Anthropic *says* "amplify, don't replace" while running a business that needs you maximally dependent on Claude. The one note in that chord they can't play *credibly at scale* is **independence/ownership** — "depend on vendors less, own your machine." Not because they can't say the words (Anthropic already ships open SKILL.md), but because a business whose revenue scales with your dependence can only sell independence as a wedge, never as the spine — the asymmetry isn't "can't say it," it's "can't mean it all the way down." That, not "human-in-the-loop" (whose *slogan* is now commoditized even though the *practice* isn't), is the only taste left that an incumbent can't honestly voice.

---

## The strategic fork for Coga

Two clean positions. They imply different work — but the choice can stay open, decided by a signal (below) rather than forced now:

**A. Internal OSS infrastructure (taste-as-craft).**
Coga is the substrate FastJVM runs on. No moat, and that's correct — defensibility is the wrong axis for a tool you don't sell. Publishing costs nothing; the payoffs are recruiting, alignment, and being an honest field report for the small tribe this fits. Taste here is craft for its own sake. The only live strategic input is a periodic **build-vs-adopt check**: when the incumbents absorb ~80% of what Coga does for us, migrate the methodology and retire the tool — a planned, graceful outcome, not a loss.

**B. Coga-as-category (taste-as-brand).**
A real, durable, model-proof moat *is* available — the metaphor + brand moat that Linear and Jira have. But it is **earned through adoption**, not owned through code: the Linear playbook (opinionated craft, a name people rally around, evangelism), not the "run it internally" path. The opening is real: the category is a taste vacuum, and our taste — *classical-mode, owner-operated, legible, neutral, depend-on-vendors-less* — is one the incumbents **can't credibly adopt** (Anthropic can't sell "depend on us less"; Dust can't sell "thin and legible") because their business models contradict it. That asymmetry is the one durable thing left, and it's a brand position, not a feature.

**But mind the ceiling.** This is *not* the full Linear move. Linear broadened because subtraction broadens; Coga's own thesis (above) says imposition *narrows*. So fork B is "own a small tribe **completely**," not "win a mass category" — the *playbook* is Linear's (craft, a name, evangelism), the *ceiling* is not. Don't let the word "category" import Linear-sized expectations; the demanding forcing function keeps the door narrow on purpose.

There is no third position where you get the moat without doing the adoption work.

### Why the fork can stay open: the incumbent is conflicted, and we're OSS

Two facts let the A/B decision wait without penalty.

**The incumbent can't build it.** Anthropic's ecosystem (Skills, MCP, plugins, Cowork) *needs* a grounding-and-coordination layer to exist — it makes agents useful and sells more Claude — so it will assemble the commodity batteries. But it builds them vendor-locked and cloud-favoring, never owned-and-neutral, because *owned + neutral + depend-on-vendors-less* attacks its own revenue. So the three cells it leaves to us — git-owned state, vendor-neutrality, the human-gated loop — aren't "won't close"; they're **"can't, without self-sabotage."** The best-placed player to kill Coga is structurally barred from the one axis Coga centers.

**And because Coga is OSS, the incumbent's best move is to *use* it, not fight it.** Coga drives Claude as a backend (it sells API usage), so an open, neutral Coga is a *complement* Anthropic benefits from — it can recommend or bundle it and collect the "you're in control" goodwill it can't manufacture itself. Pure upside for fork A: distribution and validation from the very player that can't compete on our axis.

The same openness is double-edged, and naming it keeps the doc honest: *use* also means *fork/absorb* — the code or the ideas can be taken, the neutrality stripped, a Claude-flavored version shipped; and incumbent adoption is the **graceful-retirement / influence win**, not independent-product capture. Openness maximizes diffusion and minimizes capture — the same fact, two signs (this doc's recurring shape).

This is *not* the "third position" rejected above — it buys no moat. It is **fork A as the default, with fork B kept *optionable***, because the OSS-complement stance compounds exactly the adoption fork B would later need, and the incumbent cannot force the choice. The pick is deferred until a signal forces it — and only one does: **a *neutral, non-conflicted* builder running the Linear play** (centering ownership). Anthropic never will; Dust can't. When that builder appears, fork B's window is closing and the choice must be made; until then, A-with-B-optionable is strictly correct. (Both triggers already live in "What to re-check.")

---

## Are *we* talking in taste or features? (self-judgment)

Honest read, because the thesis cuts both ways:

- **Our narrative (vision.md, README) is the most taste-saturated comms of anyone in the table** — a full worldview (Pirsig's classical mode, homoiconicity, the correction loop, "humanist tech for people who still want to understand their own machines"). On the *comms* axis we are not the feature-talkers; if anything we are *more* opinion-led than Linear.
- **But two real risks, both the inverse of the competitors' problem:**
  1. **Essay-taste is ahead of product-taste — but "product" here is not a UI.** Coga is *agent-mediated*: the human barely drives the CLI directly; the agent does. So judging it by Linear's yardstick (felt in keyboard/speed/pixels) is a category error — Coga deliberately owns *no* sensory surface. It borrows the terminal, your editor, and Slack. That's a direct consequence of the markdown-first / legibility principle: choosing not to own a UI means you can't *design* the felt layer the way Linear does. For an agent-mediated tool, felt taste lives somewhere else entirely (see below), and that's where the gap actually is.
  2. **Our taste is high-brow and may not travel.** Lisp, GEB, Hearsay-II, Pirsig is genuine taste but dense; Linear's taste is accessible ("you'll enjoy using"). High taste that only a tiny tribe can parse is craft, not yet a brand. If we ever pick fork B, the metaphor has to be sayable without the reading list.

- **Our differentiator narrowed to one word: independence.** Now that the *slogan* of "human-in-the-loop / amplify not replace / you're in control" is commoditized brand language (Anthropic's "Keep thinking" owns the words — though not the actual loop, which it doesn't build), our defensible taste is *not* human-primacy in general — it's **ownership/independence specifically**: own your machine, depend on vendors less, the substrate is yours. That's the one note in the chord an incumbent can't honestly play, and it should be the spine of any Coga comms.

**Where felt taste lives for an agent-mediated tool.** Not in pixels — in two moments the human *does* experience: (1) **the correction loop** — catching the agent doing something wrong, opening the context, fixing one line, re-running, and watching it do the right thing in two minutes; and (2) **the steered-agent behavior** — the agent reliably doing the right thing *because* the substrate (contexts, workflow, blackboard) directed it well. Plus the ambient layer: the Slack feed feeling like calm control over many parallel agents. Linear's "you'll just feel it" happens in seconds of UI; Coga's equivalent happens the first time the correction loop snaps shut cleanly. *That* is the sensory moment, and it's a real one.

**So "not felt yet" now splits in two:**
- **Operational calibration.** The substrate for unattended work has shipped;
  the remaining work is proving it repeatedly, tightening noisy or confusing
  moments, and making failures easy to correct.
- **Structural (permanent).** Coga will never have Linear-style pixel-craft
  because it owns no UI by design. Its felt taste must live in the correction
  loop and the agent's steered behavior.

**Verdict:** the reliability backlog is no longer the main strategic gate. The
real gaps are making the correction-loop payoff legible to outsiders, proving
the shipped unattended path under real use, and anchoring the story on
**independence/ownership** rather than a feature checklist.

---

## What's missing — the 80/20

The product is ~80% there, and the 80% is real: the classical substrate works
for attended and unattended local operation. Built and tested today are the
primitives, prompt composition, task state machine, schema validation,
supervised interactive REPL with done/block signaling and liveness limits,
script-backed recurring work, checked notifications, atomic writes,
git-backed state, cross-vendor chaining, and SKILL.md-format adoption.

The missing 20% is the move from shipped mechanism to trusted habit: proving
the system under repeated real runs, reducing operator confusion, and making
the correction loop obvious to someone who did not build it.

Three buckets, in priority order:

**Bucket A — make the loop felt.** Show the two-minute context correction and
the resulting changed agent behavior plainly; the checked notification path is
part of that experience, not an unimplemented prerequisite.

**Bucket B — earn unattended trust.** Recurring tasks, idle/max-session
watchdogs, and atomic writes have shipped. The remaining maturation work is
calibration, failure recovery, and evidence from sustained use.

**Bucket C — format bet not enforced / prompt hygiene (credibility polish).**
- **no SKILL.md conformance validation** — `coga validate` checks only that refs resolve, never that the files conform to the format we bet on. *(ticket: `validate-skill-md-frontmatter…`)*
- **raw frontmatter injected into prompts + no token budget.** *(tickets: `compose-strips-…-frontmatter`, `enforce-a-prompt-token-budget`)*
- ~~**drift**: `status.py` still side-effects automerge after the "move it out" change.~~ *(resolved: `status` is read-only; merged-ticket auto-close is now the sole job of the `autoclose-merged` recurring sweep.)*

**The one-line read of the 20%:** the substrate exists; what's missing is the **trust half** (unattended recurring with a watchdog, atomic writes, and working Slack/streaming so the loop is *felt*). That's why it feels like 80% — the classical *idea* is fully built and usable attended; the missing piece is everything that lets you *stop watching*, which is also everything that makes the taste land in the body instead of the head. Ship Buckets A and B and Coga crosses from "an excellent way to work with agents" to "the substrate that runs the company" — the thesis, delivered.

---

## Locating the originality: it isn't the workflow

A natural intuition — *the workflow is the deep original idea here* — is worth refuting head-on, because it points at exactly the wrong primitive. Ordered steps with handoffs is the **most-copied bone in the skeleton**: every CI system, Temporal, Airflow, and n8n have it, and Symphony open-sourced a near-identical board-as-FSM. If the originality lived in the workflow, the patent rejection would be instant.

What *is* distinctive about Coga's workflow is narrow and copyable: **author-defined and frozen at creation** (Symphony's pipeline is one fixed `Todo→…→Merging`; Coga's is your ordered steps, snapshotted so in-flight work is undisturbed), **per-step `assignee` resolving agent/human/owner interchangeably**, and **a fresh process per step** — one step, one session, the prompt scope deliberately reset between skills. That last point is a genuine, under-stated idea (context-window *hygiene* as a structural property of the process, not an accident), but it is still a weekend to copy. The name compounds the confusion: "workflow" imports the absorption-camp *runs-itself* connotation, which is the opposite of a human-gated handoff chain — it is being renamed **playbook** (ticket `rename-workflow-primitive-to-playbook`).

If you must locate originality in a *primitive* rather than the stance, the load-bearing one is the pair the workflow merely rides on: **statelessness + the blackboard.** The prompt is a pure function of the files on disk *now* — never a carried-over session — and the blackboard (the Hearsay-II pattern) is the durable surface that survives a crash. That pairing is what makes the two-minute correction loop **total and inspectable**: an edit between runs takes effect completely because there is no hidden session state to fight, and the agent is recoverable because its last state is on disk. The correction loop is the axiom made mechanical; statelessness+blackboard is the primitive that serves it most directly — and the workflow serves it least.

Two further ideas the rest of this doc under-weights, both consequences of the same root:

- **The step boundary as a deliberate context reset.** Treated above as a chaining detail, it is really a reliability thesis: you engineer an agent's correctness by structuring *where its context gets wiped*, the way you structure where a transaction commits. Nobody else frames workflow steps this way.
- **Status-as-signal instead of a mutex.** Refusing a hard lock — accepting that two divergent workers leave a *visible, git-recoverable* conflict rather than paying for stale-lockfile cleanup and `--force` flags — is a contrarian, fail-loud design choice, not an omission. It is a one-line consequence of the classical stance and deserves to be named as its own idea.

None of this changes the verdict below: the originality is still axiomatic, not featural, and all of it is copyable. The only correction is to the *ranking* of the featural candidates, which most people hold backwards — the workflow is the least original primitive, and the statelessness+blackboard engine is the most.

---

## Original and defenseless (the conclusion)

Is there something unique and original here? **Yes — but in the stance, not the parts.**

Nothing in the *mechanism* is original: tickets→agents, a state machine, respawn-on-crash, a blackboard, markdown skills, git-as-state, the correction loop — each is a known idea, and OpenAI open-sourced a near-identical skeleton (Symphony). Even the *framing* is no longer Coga's alone — Brad Feld's CompanyOS is "markdown files that teach Claude Code how to run a company," and the auto-memory field already compounds knowledge into markdown. A patent examiner rejects every claim.

And the residue is not a scattered list of features — it is **the closed-form consequence of a single axiom.** Coga computes every choice from one root (*"don't* don't *think — think better; own your machine"*); every competitor computes from the opposite root (*"don't think — the machine does it"*). Because the *domain* forces the same primitives on everyone — tickets, markdown, agents, a state machine — the surface coincides; because the *axioms* are opposite, the direction of every derived choice flips. That is why the pattern repeats corner for corner: same skeleton / inverted soul (Symphony), same compounding / inverted gate (Dream), same grounding problem / inverted delivery (legible-deterministic vs opaque-retrieval). The originality is **axiomatic, not featural** — not a feature nobody else has, but a fixed point nobody else's root can reach. The whole thing fits in one line: **same tech, same problem, inverted assumption about the human's role (irreducible, not residual) → an inverted product — light by default, rigorous on demand, empowering throughout, because the rigor is amortized into a substrate you own rather than taxed per task.** Two caveats keep this honest: the axiom itself is *borrowed* (Pirsig's classical mode, the Unix/Lisp legibility tradition) — what's original is *choosing it for agent-native operations while the field chose absorption*; and competitors are not *barred from building* any one corner (Backlog.md could add a correction loop tomorrow) — they are barred from *centering* it, because centering "think harder / depend on vendors less" contradicts their pitch and, for the model vendors, their business.

The original thing is the **conjunction and the direction**: Coga is the only coherent attempt to make agent-native company operations **classical** — *owned, legible, neutral, correction-looped, nothing hidden* — at the exact moment the entire field sprinted toward **absorption**. Everyone has the same Lego bricks; only Coga assembles them into *"you understand and own and correct your machine"* instead of *"the machine does it so you don't have to."*

The unique residue is the **full intersection**, because every competitor either lacks a corner or can't center it: Symphony (cloud, autonomy-first), Viktor (black-box hire), Notion/Dust (cloud platform, hidden state), CompanyOS (owned markdown — but skills auto-fire, Claude-only, no state machine, ontology, or gated correction loop), Backlog.md/task-master (storage, no loop), Claude Code/Codex (single-vendor, ephemeral, no owned substrate), Anthropic (cannot *center* "depend on vendors less"). Nobody holds *owned + legible + neutral + corrected + classical* at once — organized around the one value an incumbent can't voice: **independence/ownership** ("compile your company so *you* own and understand it").

And the honesty that ties the whole doc together: **this is original the way a philosophy implemented as a complete system is original — not the way a technology is.** It's taste made coherent and contrarian. A coherent contrarian point of view is genuinely scarce in practice (almost everyone copies the stampede), so it is real and rare — but it is a *stance*, which means it is original *and* freely copyable, for the identical reason. **Its originality and its non-defensibility are the same fact.** Original and defenseless.

Last caveat: right now the original thing lives more in the *conception* (vision, principles) than in the *product* (the loop is not fully felt yet). So: **original in stance, not yet original in experience** — and the bridge is the 80/20 above.

---

## Will it succeed? (success = influence or a fan base, not a unicorn)

"It's original, so will it succeed?" is a trap: the *kind* of originality here (a copyable stance) predicts non-defensibility, which is a headwind for *commercial* success, not a tailwind. The two axes are nearly anti-correlated. So the question only has a useful answer once you fix the metric — and the honest metric for a tool like this is **not commercial dominance but influence (the ideas spread and shape how people think about agent-ops) or a fan base (a small, intense tribe that loves it and evangelizes).**

By *that* bar, it is **likely to succeed** — because the very properties that doom commercial success are neutral or positive here:

- **The no-moat problem evaporates.** Influence *wants* ideas copied; a fan base doesn't leave because the design is copyable — it stays for the taste and the tribe. The thing that makes Coga commercially defenseless is exactly what makes it influence-shaped.
- **"Narrow door" becomes the definition, not the liability.** A small, intense, evangelizing tribe *is* a fan base; narrowness is the point, not a bug.
- **The comprehension-debt hinge softens.** Commercial success needed that bet felt *at scale*; influence/fan-base only needs it felt by a *minority* — far likelier — and the ideas travel regardless of whether the tool itself wins.
- Even the **graceful-retirement** outcome (incumbents absorb ~80%, the tool retires, the methodology lives on) *counts as influence-success* under this bar.

Two gates remain, and both are *executable*, not existential:

1. **Make the metaphor travel.** Influence and recruitment both need "compile your company" sayable *without* the Pirsig/Lisp/GEB reading list. High taste only a tiny set can parse is craft, not yet influence. A writing/comms problem — partly solved by leading with the plain version ("brilliant and blank; you must feed it").
2. **Ship the felt layer so admirers become fans.** A fan base forms around a *felt* experience, not an essay. Until the trust-half lands (recurring, watchdog, streaming, reliable Slack), you get *readers who admire the thinking* — influence — but not *users in love* — a fan base. The path from read-taste to felt-taste runs straight through the bug backlog.

**Verdict:** by the influence-or-fan-base metric, more likely than not — because that metric is the one this original, defenseless, contrarian tool is *built* to win. **Influence** is the near-term, lower-gate outcome (good thinking, made legible, made visible); a **fan base** is the higher-gate one (felt taste, shipped). The unicorn outcome was never the bet, and measuring against it was the only way to mistake this for a failure.

---

## What to re-check, and when

- **Build-vs-adopt** (fork A's only live input): when an incumbent substrate does ~80% of what Coga does *for us*, migrate the methodology and retire the tool.
- **Taste vacuum** (fork B's window): watch whether anyone runs the Linear move for agent-native ops. If a well-branded, opinionated, owner-operated competitor appears, the window for B is closing — and notably, it won't be Anthropic or Dust (they're conflicted out of our taste); it'll be another neutral, opinionated builder.
- **The model climbing into the substrate** (the only real risk to A): Skills + Cowork + Managed Agents are the first steps. The one place they won't climb is cross-vendor neutrality — the same asymmetry that anchors fork B.
- **Landscape table facts** (the fastest-rotting part of this doc): re-verify competitor hero copy, funding, and feature claims quarterly; last checked 2026-05-31.
