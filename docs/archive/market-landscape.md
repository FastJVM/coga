# Market landscape (dated research)

> **History, archived 2026-09-22.** Competitor research extracted from
> `docs/market-thesis.md` (written 2026-05-30; competitor copy, funding and
> feature claims verified **2026-05-31**) plus the prompt-as-interface claim
> check of **2026-09-08**. These facts rot fastest: re-verify any of them
> before reusing it in a current public claim. Descriptions of Coga below are
> as of those dates and may be stale (for example references to open tickets
> or unshipped features); the shipped contracts are the `coga/*` contexts. The
> current strategic argument is in
> [`marketing/strategy`](../contexts/marketing/strategy/SKILL.md), approved
> public claims in
> [`marketing/positioning`](../contexts/marketing/positioning/SKILL.md), and
> later dated comparisons in [`docs/evidence/`](../evidence/).

## Prompt-as-interface claim check — 2026-09-08

The owner asked whether explicitly managing the prompt, instead of organizing
work around chat, supports calling Coga radically new. This was a focused
comparison, not an exhaustive prior-art review.

Implementation evidence at that date: `src/coga/compose.py`
`compose_prompt_report` reads the repo context, attached contexts, selected
skills/step, Description, inline Context and blackboard, with the base and
conduct layers; `PromptComposition` exposes the assembled text and layer
metadata. The composer does not reconstruct those inputs from a chat
transcript. The agent still has its own session history, tools and provider
instructions, so Coga does not control every token of the agent's context;
durable corrections must reach the relevant files to affect a later launch.

| Source | Overlap and claim limit |
| --- | --- |
| [PromptChainer, CHI 2022](https://arxiv.org/abs/2203.06566) | Visual authoring and debugging of LLM prompt chains. Non-chat prompt interfaces predate Coga; not equivalent to Coga's operating loop. |
| [GitHub Spec Kit, 2025-09-02](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/) and [project docs](https://github.com/github/spec-kit/blob/main/docs/index.md) | Specifications guide implementation, are revised as understanding changes, and give Markdown context to later phases, across processes and agents. Close overlap. |
| [Kiro specs](https://kiro.dev/docs/specs/) | Requirements, design and task files drive planning and execution with tracked progress. Close overlap. |
| [OpenAI prompting guidance](https://developers.openai.com/api/docs/guides/prompting) | Manage prompts in versioned code reviewed through Git/PRs. Prompt management itself is established. |
| [Anthropic context engineering, 2025-09-29](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) and [Claude Code memory](https://code.claude.com/docs/en/memory) | Maintained context, external notes and persistent editable instructions across sessions. Continuity outside a transcript is not exclusive to Coga. |

**Assessment:** the contrast with chat is supported as a design explanation;
"first", "unprecedented" or "only Coga" is not. The thesis is the explicit
combination of managed prompt composition, ongoing work and state,
operator-owned files and correction across sessions. Its uniqueness and any
task-performance benefit are unproven.

## Structural position — 2026-05

| | Operations-as-code (run your ops) | Agent framework (build an agent) |
|---|---|---|
| **Convention** (no runtime) | CompanyOS, agent-os, LLMunix | AGENTS.md / rules files |
| **Engineered runtime** | Coga | LangGraph, CrewAI, Mastra, Agentuity |

The 2026-05 reading: operations-as-code players shipped conventions without a
runtime; the runtimes were developer frameworks for building agents. The
position was described as a head start, not a moat.

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

**Contrast 2 — Symphony is Coga's doppelgänger: same mechanism, opposite values.** Verified against the [openai/symphony](https://github.com/openai/symphony) spec (open-sourced Apr 2026), the shared skeleton is five concrete bones: (1) the board *is* a finite state machine and the single source of truth; (2) agents are stateless between runs, reconstructed from the board on restart; (3) one agent per ticket in an isolated workspace; (4) a supervisor respawns crashed/stalled agents; (5) it ships as a spec you fork, not a product you buy. Describe those and you've described Coga's plumbing exactly. One bone even differs in *shape*: Symphony's state machine is a **single fixed pipeline** (Todo→In Progress→Review→Merging) baked into the spec; Coga's workflow is **author-defined per task type and frozen at task creation or draft activation** — you write your own ordered steps. That's the hackable/own-your-process axis Symphony doesn't have at all. But every bone that carries *meaning* inverts: Symphony = *"manage work instead of supervising coding agents"* (human out of the loop, throughput-first, state in Linear's **cloud**, **Codex-only**, **code→PR scope only**); Coga = the correction loop (human *in*, legibility-first, state in **your git**, vendor-neutral, whole-company scope, no ticket-level auto mode). **OpenAI open-sourcing the skeleton as a `SPEC.md` is the clearest possible proof the mechanism is commodity — they gave it away. The only thing left to differ on is taste/values, and Coga's are the contrarian ones.** The surface is now industry-standard; the divergence is entirely one layer down.

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

The map above is the *taste* cut (what each tool teaches). This is the *capability* cut: the concrete axes a buyer can check. Two distinctions matter and are easy to get wrong. **(1) Prose-as-code ≠ prose-as-context.** A `CLAUDE.md` is *context* — declarative, "here is how things are." Coga's tickets/workflows/skills are *instructions* — imperative, "do X, then Y, verify Z." The "code" is the imperative layer that tells the agent what to do; Coga keeps it separate from the context layer (the data it acts on), and `CLAUDE.md` has only the latter. **(2) Automation is not binary.** Coga's workflow and assignees decide who acts at each step, while deterministic work runs as a `ticket.py` beside the ticket (which may call the explicit `coga run` recipe registry). The ticket carries neither a mode nor an autonomy flag — the presence of that one file is the whole declaration; unattended drain is handled by script tickets, blockers, megalaunch, and the liveness watchdog.

| Tool | Programmed in | Owned & legible (your git) | Vendor-neutral (BYO-agent) | Batteries that *compound* | Human-gated loop | Domains | Autonomy | Cost |
|---|---|---|---|---|---|---|---|---|
| **CLAUDE.md** | context only (declarative) | partial (a flat file in your repo) | yes (any agent reads it) | **no — it bloats** | no | n/a | n/a | free |
| **Claude Code + ecosystem** (Skills/MCP/plugins/Cowork) | imperative chat + context | no (ephemeral; store/plugins) | no (Anthropic) | assembling (skills/MCP/plugins) — no workflow/ontology/git-substrate | auto-capture, review optional | dev-leaning | partial (background agents) | paid |
| **Devin** | chat / UI | no (their cloud) | no (bundled, opaque) | no (opaque knowledge) | out-of-loop (delegate) | code only | all-or-nothing autonomous | paid |
| **Frameworks** (LangGraph/CrewAI/ADK) | code | no (code, not legible prose-state) | model-neutral-ish | you *build* the batteries | you build it | you build it | you build it | OSS (you build everything) |
| **CompanyOS** (Feld) | prose, but context + skills (no program layer) | **yes** (owned git markdown) | Claude only | skills-only — no workflow/pkg-mgr/loop | no (skills auto-fire) | business-ops | none | free |
| **OpenAI Symphony** | spec / code | no (state in Linear cloud) | Codex only | a spec you fork (board FSM) | out-of-loop, throughput | code only | async autonomous | OSS spec |
| **Coga** | **imperative instructions + separated context** | **yes — your git, fully inspectable** | **yes — claude↔codex↔any CLI** | **yes — composition→skills+pkg-mgr→workflow→loop→gate, and it compounds** | **yes — PR-gated (Dream)** | **code + research + ops** | **granular: per-step `assignee` role (`owner`/`agent`/`other-agent`), derived not stored, plus a deterministic phase when a `ticket.py` sits beside the ticket — it runs headlessly first and the agent still picks up whatever judgment the step leaves open — no mode or autonomy flag** (fire-and-forget unblocks before release) | **free / open, rides your subscriptions** |

**Where Coga is the only option.** The combination *owned + legible + vendor-neutral + batteries-that-compound + human-gated + cross-domain + free* — nobody else holds it. `CLAUDE.md` is a strict subset (Coga = `CLAUDE.md` + the program layer + batteries + loop); CompanyOS is the only other "owned," but it is skills-only (no workflow, no loop); frameworks are code to *build* an agent, not prose to *run* work. For the buyer who wants to **own, understand, and correct** their agent substrate, across everything, for free — Coga is alone.

**Where Coga is outclassed (state it plainly).** Fully-managed unattended autonomy out of the box → **Devin / Symphony / Claude Code** (Coga keeps the local, file-backed loop and uses megalaunch + script tickets for unattended drain). Heavy parallel/dynamic orchestration → **frameworks** (Coga's workflow is a linear state machine). Managed reliability / support / SLA → **paid products** (Coga is self-hosted, self-supported). Zero-setup → **CLAUDE.md** (one file, nothing to learn). Distribution / brand → anyone funded. And none of the axes Coga wins are a *moat* — the whole combination is copyable; the only durable layer is direction (see the conclusion).

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
