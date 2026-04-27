
# Relay

**A company OS for small teams in the agentic era. Humanist tech for people who still want to understand their own machines.**

---

We run FastJVM, a two-person deeptech startup making the JVM faster — a field dominated by Oracle and Google. Pre-revenue, post-reset. Relay is the methodology and tooling we built to run the company after the reset, and it's how we plan to keep running it.

This document describes what Relay is, why it works for us, and why it's hard to duplicate even though we're publishing it in full. Open source, MIT licensed: [github.com/relay-dev/relay](https://github.com/relay-dev/relay).

---

## What this is

Relay is not a product. It's how we run our company.

The substrate is markdown files in a git repo. The tooling is a six-command CLI. The methodology is how we use both — what we automate, what we don't, how we encode knowledge, how we divide work between us and the agents.

Pirsig drew a line in *Zen and the Art of Motorcycle Maintenance* between two ways of relating to a machine. The romantic mode: you use it, it works or it doesn't, the inside is someone else's problem. The classical mode: you understand it, you maintain it, the inside is legible to you and you to it. Pirsig's claim — which has aged better than most of the book — is that the romantic mode produces alienation from your own tools, and the classical mode produces Quality: not just better outcomes, but a different relationship to the work.

Most software today is romantic. SaaS tools are black boxes you rent access to. Agent platforms hide their prompts, their rules, their decisions. You don't understand the machine; when it misbehaves, you file a ticket. When your own operations depend on that machine, you've outsourced understanding along with execution.

Relay is classical. Every file the agent reads, you can read. Every rule the agent follows, you can edit. When it does something wrong, you open the context and fix it. You are in a maintenance relationship with your own operations — the same relationship Pirsig's narrator has with his motorcycle. That relationship is what produces Quality at a small company's scale. The alternative — outsourcing understanding to vendors — is what makes companies bloat, hire, and lose the thread of what they're actually doing.

This is the philosophical center of Relay, and it's load-bearing. Every design choice that follows — markdown over databases, CLIs over UIs, inline edits over PR cycles, discipline over enforcement — is downstream of the decision to stay in the classical mode. If you want romantic software that just works without asking you to understand it, this isn't for you. There are better romantic tools, well-funded and polished. Relay is for operators who want to keep their hands on the machine.

---

## The reset

Six months ago, our research took longer than expected and funding was running out. Two options: shut down, or rebuild around what was working. We chose rebuild. That meant letting engineers go — the hardest thing either of us has done as founders — and reconstituting the company around one senior engineer, the two of us, and whatever leverage we could extract from frontier agents.

Relay is what we built to make that reconstitution viable. Not a tool we adopted on top of an existing operation, but the operating substrate of the company from that point forward. Every recurring task, every workflow, every piece of institutional knowledge moved into it or got cut.

The methodology depends on this reset having happened. A company that didn't do the reset — that has existing SaaS tools, established processes, accumulated tribal knowledge — can't layer Relay on top and get the same leverage. The substrate has to be the operating substrate, not a parallel one. That's why this works for us and wouldn't work for most companies past a certain size or age.

---

## The thesis

A two-person technical team can produce the output of a ten-person team if three conditions hold:

**Frontier models are cheap and getting cheaper.** Inference cost per task has dropped by orders of magnitude and continues to fall. Tasks that weren't economically automatable two years ago are now automatable at rounding-error cost.

**Encoded expertise compounds.** The person who understands the domain is the person encoding it. No translation layer, no onboarding loss, no tribal knowledge lost to turnover. Context written once is reusable forever and updatable at minutes of latency when the world changes.

**The break-even point for automation has moved an order of magnitude.** Tasks that took 20 hours to automate and saved 4 hours a month used to have five-year payback. Now the same task takes 5 hours to automate and saves the same 4 hours a month — payback measured in weeks. A whole class of previously-not-worth-it work becomes worth automating.

Given those three conditions, the limiting factor is no longer "can we afford to automate this?" It's "do we have the substrate to capture the leverage?" Without a substrate, automations fragment across SaaS tools, scripts rot, context lives in people's heads, and the compounding breaks. With the right substrate, each automation reinforces the next.

Relay is our substrate.

---

## The substrate

Everything Relay operates on is markdown in a git repo. Tasks, contexts, skills, workflows, rules, the base prompt agents are launched with, the blackboards where agents write their in-progress state. One file type. One versioning system. No database, no server, no vendor platform.

The property we're reaching for is the one Lisp had: homoiconicity. Code and data in the same structure, so a running program can inspect and modify its own behavior using the same primitives it uses to operate. No metalanguage gap. Lisp achieved this at the code level and paid for it with a steep learning curve; the payoff was a language where macros, metaprogramming, and self-modification were first-class rather than bolted on.

Relay reaches for the same property at the operations level. The base prompt the agents start from, the rules they obey, the knowledge they draw on, the workflows they execute, and the workspace they operate in are all the same kind of file. Edited with the same tool. Versioned in the same history. Inspection and modification are the same action.

The consequence is concrete: when we notice an agent getting something wrong, we open the relevant file, edit it, commit. The next run uses the new version. No PR cycle, no deploy, no vendor feature request, no support ticket. End-to-end latency from "saw a mistake" to "fix is live" is roughly two minutes.

SaaS tools with editable rules still separate "the platform's behavior" from "your configuration" — you can tweak the exposed surface, not the underlying logic. Relay collapses that distinction. There is no underlying logic hidden from you; there is only the substrate, which you own end-to-end.

The tradeoff is the Lisp tradeoff: flexibility without structure means discipline substitutes for enforcement. Lisp codebases famously drift into dialects — every shop writes its own style, newcomers struggle to read other people's code, the substrate's power becomes the substrate's fragility. Relay has the same failure mode in waiting. At some team size, discipline breaks down and you need the structure you deliberately didn't build. We're far below that size and plan to stay there. For anyone past it, the tradeoff flips and Relay becomes the wrong tool.

---

## Where it runs

Relay runs on our machines by default. Not on a hosted service, not on a remote cluster, not in a vendor's cloud. The agent's session is on the same hardware one of us is sitting at. When it works, we're there. When it panics, we're there. When it finishes and posts to Slack, we're usually still at our desks.

This isn't about data sovereignty or infrastructure minimalism. It's about the correction loop. The loop only closes cheaply if the human and the agent are co-located in time and context. A cloud agent that runs overnight and reports in the morning has already broken the loop — by the time you see the mistake, you've lost the context of what the agent was trying to do and what you were doing. Reconstructing the situation before you can correct it is the cost that kills most automation programs. Co-location avoids that cost entirely. You're still *in* the context when the correction needs to happen.

Cloud execution has a legitimate place, but later. An automation that's been running for months, whose context is mature, whose panic thresholds are calibrated, whose failure modes are known and handled — that automation can graduate to cloud execution. The correction loop isn't firing often anyway; availability and reliability matter more than tight iteration latency. The weekly deliverability check, the monthly newsletter draft, the nightly Stripe reconciliation — stable automations don't need a human standing next to them.

What the automation can't afford to lose, at any stage, is legibility. Wherever it runs, we still have to be able to look inside it. Read the blackboard. Read the context it was given. Recover the prompt that was composed and sent. Trace what it decided and why. Cloud execution that preserves these properties is fine; cloud execution that hides internals breaks the classical-mode relationship with the machine and takes us back to renting understanding from a vendor.

In practice this means automations have a natural progression. Early on, everything runs local and attended — we're watching the agent work, editing context when it misfires, tuning thresholds. As the automation stabilizes, we attend less but it still runs on a machine we own. Eventually, mature automations can move to cloud execution, running on a schedule, results flowing into the same Slack channel that carries everything else. The default stance shifts from *watching* to *trusting* — but never to *opaque*. The cost of looking inside stays low at every stage.

**Slack is the coordination hub.** Not as a notification add-on, but as the ambient awareness layer that makes running multiple parallel agents tractable. Every state-changing command posts to a shared channel: task created, agent launched, step advanced, task done, agent panicked, script failed. FYI for routine events, @mention when a human needs to act. The channel is a scrollable record of everything happening across the company, across all projects, across all agents. We dip in when tagged, dip out otherwise.

The alternative — polling N dashboards, checking each tool's notification settings, context-switching between vendor UIs — is what small teams actually do before they build something like this, and it's the thing that caps how many parallel automations a founder can mentally track. One channel, one scroll, one place the whole company's activity lives. The feed is overshare-by-default on purpose. If it ever gets too noisy, that's a good problem — it means a lot is getting done.

---

## The correction loop

The mechanism underneath all of this is a loop with unusually short latency.

An agent does something wrong. A human notices — because they were at the machine, because Slack pinged them, because a panic fired. They open the relevant context file, tighten the wording or add the missing rule, commit. The next run of that task — and every future run of every task that references that context — uses the corrected version. Elapsed time from observed error to deployed fix: about two minutes.

That number is the engine. It isn't a convenience. It's the difference between automations that stay sharp and automations that rot.

The SaaS world runs on a different loop. Observe error → file ticket or open config UI → edit exposed surface → test in staging → deploy → wait for next run. Latency measured in days for the fast cases, weeks for the normal ones, never for the corrections the platform doesn't expose. That latency doesn't just make corrections slow. It raises the cost of each correction high enough that people stop making marginal ones. Which means automations drift. Which means trust erodes. Which means you stop automating things that would have been worth automating if the correction loop were cheaper.

Relay inverts this. Because corrections are cheap, we make them constantly, including the marginal ones. Because we make them constantly, the substrate gets better with use rather than worse. Because the substrate gets better with use, each new automation costs less than the last — it inherits a thicker library of corrected contexts, known-good patterns, calibrated thresholds. The system compounds.

This is what we mean when we say the methodology is a flywheel rather than a collection of tools. The substrate, the local execution, the Slack hub, and the classical-mode posture aren't independent design choices. They're the specific combination that collapses correction latency far enough that compounding becomes possible.

Two consequences worth naming:

**Context is the asset that appreciates.** Six months in, our context library is more valuable than the CLI, the scripts, the workflows, and the base prompt combined. Those are scaffolding. The contexts are the encoded operating knowledge of a compiler company at month six, and they're only that good because we've corrected them hundreds of times in the flow of work. A competitor forking Relay gets nothing that matters. A competitor somehow acquiring our contexts gets years of expertise they'd have otherwise had to live through. The flywheel spins up slowly and the output is specific to the company that spun it.

**Marginal automation becomes worth doing.** Tasks that took four hours a month and would have taken thirty hours to automate used to not pencil out. At today's correction loop cost, those same tasks take three to five hours to automate, the automation stays sharp because the correction loop keeps it sharp, and the payback is weeks instead of years. A whole category of "just do it manually forever" tasks becomes worth building. This is what actually lets two people run the operational surface of a larger company.

---

## The primitives

**Tasks** are directories in the repo. Each has a ticket (what to do, who's doing it, what workflow applies), a blackboard (the agent's workspace for in-progress state), and a log (append-only history of state changes). Tasks are how work gets tracked and how agents persist between sessions.

**Contexts** are reusable chunks of domain knowledge. "How email deliverability works," "how our JIT compiler handles inlining," "how our Stripe integration's retry logic behaves." Attached to tasks by name. Written once, used across tasks and agents. The artifact that appreciates over time — see the correction loop section above.

**Skills** are process knowledge attached to workflow steps. "How to run code review," "how to publish to LinkedIn," "how to reconcile the bank statement." Distinct from contexts: skills are how to do things, contexts are what's true about the world. A skill can include scripts; a context is pure knowledge.

**Workflows** are sequences of steps with optional skill references per step. Tasks snapshot a workflow at creation — in-flight work isn't disrupted by workflow edits.

**Blackboards** are per-task workspaces where agents write findings, plans, decisions, and blockers. The blackboard is how agents persist state between sessions — an agent that crashes mid-task is recoverable because the blackboard has its last known state. It's the pattern from 1970s AI research (Hearsay-II): independent processes coordinate through a shared mutable surface rather than direct message passing.

**Three modes** per task: interactive (human sits with the agent), auto (agent runs alone, panics to a human when stuck), script (no agent, a script runs with secrets injected). The mode is declared per-task. Most recurring operational work is script or auto. Most novel work is interactive. Choice is per-task, not a global setting.

**The base prompt** is a system prompt injected into every agent session. It teaches the agent how to operate within Relay — when to advance workflow steps, when to panic, how to use the blackboard, how to handle frontmatter. The base prompt lives as version-controlled markdown. Agents don't learn Relay through their own memory or config; they learn it fresh every session from a file we own.

---

## How we decide what to automate

Not every task should be automated. The three-question framework:

**Is the task publicly and extensively documented?** Frontier models are trained on the public corpus. If a competent outsider could learn the task from books, standards, or accredited courses, the model has likely internalized it. If the task requires tacit knowledge that isn't written down anywhere, the model will fail — sometimes confidently.

**Is competent-and-generic output enough?** LLMs produce competent-and-generic output by default. Tasks where that's sufficient (reconciliation, patent drafting, standard code refactors) are good candidates. Tasks requiring exceptional judgment, strong taste, or edge-case intuition (novel architecture decisions, sensitive customer communication, strategic writing) are not.

**Can we evaluate the result without raising the bar?** If we would review a contractor's output for this task with a certain rigor, we review the agent's with the same rigor. Not more, not less. If the evaluation requires expertise we don't have — if we can't tell whether the output is right — the task either needs redesign or shouldn't be automated.

If all three answer yes, the task goes into Relay as auto or script mode. If one answers no, we either redesign it (split into sub-tasks that each pass) or keep doing it ourselves. The worst outcome is confident automation of a task where we can't evaluate the result — that's how silent errors ship.

Most recurring operational work in a technical company passes all three questions once you decompose it finely enough. The decomposition is the work.

---

## Self-bootstrapping

The methodology describes itself using its own primitives. Two meta-skills make this possible.

**Dream** is a recurring task that scans the repo and proposes improvements. Gaps in context coverage, workflows that should exist but don't, skills referenced but not written, contexts that contradict recent blackboards. It writes proposals; we accept or reject. The contexts stay current not because we maintain them on a schedule, but because the system surfaces gaps in the flow of work.

**Create** is a skill that runs during task creation. Give it a title and description, it asks clarifying questions, proposes which contexts and workflows apply, and drafts the ticket. We review before confirming. Most of our task creation goes through this — it's how new work gets slotted into the existing substrate without us having to remember what's there.

Hofstadter spent *Gödel, Escher, Bach* arguing that strange loops — systems that contain representations of themselves and can reason about their own structure — are where interesting things happen. Relay isn't intelligent in any Hofstadter sense, but the pattern is similar at a workaday level: the system's rules are files, the files can be read by the same agents the rules govern, and the agents can propose changes to the rules they're about to follow. Dream is Relay reasoning about Relay, using Relay. Create-suggest is Relay extending Relay, from within Relay.

This is the reason the methodology doesn't rot. Without these meta-skills, Relay would be a task list with a documentation convention — useful but bound to drift. With them, the system is actively pushing us to maintain it, and the maintenance happens as a byproduct of using it, not as a separate activity. Quality, in Pirsig's sense, requires continuous attention to the machine. The strange loop is how we get that attention for free.

---

## The discipline we hold ourselves to

The methodology fails without sustained operating discipline. What we commit to:

When an agent gets something wrong, we update the relevant context before closing the task. Not later. Not in a backlog. The correction happens in the same session where the mistake was observed. The two-minute correction loop only works if we actually close it.

Panic thresholds get tuned per task, not set globally. An agent that never panics silently ships wrong answers. One that panics on every ambiguity is useless. Each auto-mode task gets its own calibration, revisited when we see failures.

Dream runs weekly, with a human reviewing every proposal. Not "eventually." Weekly. If we skip it, drift compounds and we notice three months later when the system starts failing in ways we don't understand.

Skills and contexts stay separate. Process knowledge in skills, domain knowledge in contexts. When a new piece of knowledge straddles the line, we split it. The distinction holds only because we enforce it in review.

Contexts get audited when they exceed a page. Long contexts signal conflation — multiple concepts that should be separate files. We split before the conflation becomes a correctness problem.

Scripts get owned, not orphaned. Every script in a skill has a specific author who remains on the hook for its behavior. An unowned script that breaks in production is a failure mode we've pre-committed to avoiding.

We ship first versions knowing they're wrong in small ways. This is the cultural commitment that makes the correction loop actually compound. In a SaaS world, the first version of any automation is expensive enough that "wrong in small ways" gets patched around with human workarounds, and the automation stays half-useful forever. With a two-minute correction loop, we ship early, fix what we see in the first week of use, and end up with something tight by week three. The tolerance for imperfect first versions is what separates teams that accumulate a library from teams that don't. Perfectionism on version one is a failure mode, not a virtue.

These aren't aspirational practices. They're the methodology. Relay without them is Notion with worse UI.

---

## What this replaces

Concrete substitutions, because abstractions don't convince anyone:

Instead of Notion or Linear for task tracking, a folder of markdown files in the repo. Instead of Zapier for recurring automation, skills with bundled scripts triggered by cron. Instead of an ops coordinator, auto-mode tasks that handle reconciliation, deliverability checks, reply triage, patent drafting. Instead of Slack-as-memory, a blackboard per task that survives sessions and is readable by whoever picks up the work. Instead of an internal wiki, contexts attached to tasks so knowledge is used where it's needed rather than filed where it'll be forgotten.

Each substitution has a tradeoff. Notion has a better UI. Linear has stronger collaboration features. Zapier has integrations we'd have to build ourselves. A real ops coordinator has judgment an agent can't replicate. We accept every one of those tradeoffs because the substrate matters more than any individual feature — one coherent system beats seven disconnected ones when the coherence is what lets knowledge compound.

---

## Why this is hard to duplicate

The methodology is published. The CLI is open source. Anyone can fork the repo. And yet:

**The reset is the first barrier.** Most companies can't rebuild around this without breaking things that work. Established process, existing SaaS subscriptions, tribal knowledge distributed across team members — these are assets at normal scale and liabilities when adopting a substrate like Relay. The window for adopting this closes as companies ossify. Founders at the right moment can; founders past it usually can't.

**The encoded expertise is the second barrier.** Our context library is years of work compressed into markdown. Forking Relay gets you the CLI, not the contexts. Another team building their own context library from scratch is doing the real work — the CLI is a tool in service of that work, not a substitute for it.

**The discipline is the third barrier.** Most teams adopt a methodology with enthusiasm and abandon it when maintenance friction compounds. The practices listed above look simple. Sustaining them for a year, then two, then five, while the company grows and priorities shift, is where most attempts fail. We haven't sustained them for five years yet — we've sustained them for six months. Ask us again in four years.

None of these is a feature-level moat. There's nothing in the code that a competitor can't replicate in a weekend. The moats are structural, operational, and temporal — properties of how the company and its founders operate, not of the software. That's why publishing costs us nothing. The description doesn't reduce the barriers.

That's also why we're publishing at all. Articulating the methodology keeps us aligned on how we operate. Future FastJVM hires will need this as the operating manual for joining the company. And the small set of teams for whom this is relevant — founder-operated technical companies at or near a reset moment — don't have good examples to learn from. Most writing about AI-native operations is vendor marketing or speculation. This is a report from a company that bet on a specific operating model and can tell you what's holding up at month six.

---

## Failure modes we watch for

**Silent wrong answers.** Auto-mode tasks that fail confidently, returning output that looks correct but isn't. The framework's third question — can we evaluate the result? — is meant to prevent this. When evaluation capacity is thin, the task moves from auto to interactive-with-approve, even if it's recurring.

**Context drift.** The world changes, contexts don't. Dream catches some of this, but not all. We schedule quarterly reviews of context accuracy against recent blackboards and recent company changes.

**Calibration rot.** Panic thresholds that were right six months ago become wrong as the task space shifts. Each auto-mode task's panic rate gets reviewed when it feels off. "Feels off" is imprecise, which is why this is a discipline issue rather than an automated check.

**Skills-contexts conflation.** The distinction that's conceptually clean but practically leaky. When we notice a skill containing domain facts or a context containing process instructions, we split. If we stop noticing, the methodology degrades.

**Scale ceiling.** One-task-one-worker, local locks, git as sync — these break around 10 people. We're at 2 and planning to stay small. If we ever scale past that, Relay's internals get rebuilt. The methodology survives; the infrastructure would need replacement.

**The market moving underneath us.** Editor vendors (Cursor, Windsurf) ship built-in task persistence and context scoping. Platform vendors (Linear) ship integrated agents. If the 80% of Relay's value gets absorbed into tools we're already using, the methodology remains but the bespoke tooling loses its justification. We monitor this; if it happens, we switch substrates and keep the methodology.

---

## What this is not

Not a product. We don't sell it, we don't support it, we don't maintain it as a dependency anyone should take on.

Not an agent. Relay doesn't generate code, make decisions, or run workflows autonomously. It's the substrate agents operate on.

Not a platform. No vendor lock-in, no API to integrate with, no hosted service. Your data is markdown files; your infrastructure is git.

Not a replacement for judgment. The three questions filter what to automate. What remains requires founder attention — and deserves it.

Not defensible by normal tech moats. No patents, no network effects, no switching costs, no data advantage. The methodology is defended by preconditions, not by code.

---

## Status

[FILL IN WITH REAL NUMBERS: months into running FastJVM on Relay, count of recurring automations, domains they span, team composition, concrete outcome like "haven't missed a deliverable since the reset" or similar. This is the credibility anchor — readers will discount everything above if this section is vague or absent.]

---

## On lineage

The ideas this document stands on aren't new. Pirsig's classical mode is 1974. McCarthy's homoiconic Lisp is 1958. Hofstadter's strange loops are 1979. The blackboard pattern comes out of CMU's Hearsay-II in the 1970s. Unix was already teaching that small sharp tools composed through files beat monolithic platforms when some of us were learning to code.

What's new is the economic condition that makes humanist tech a viable way to run a company rather than a hobbyist's preference. Frontier agents collapse the cost of automation by an order of magnitude. Founders who can encode their own expertise no longer need a team of ten to capture the leverage of a team of ten. The preconditions that used to force us toward romantic tools — we can't afford to understand everything, so we rent understanding from vendors — don't hold anymore for small technical teams willing to stay small.

So we built the thing the older tradition would have built if it had had frontier models to work with. Classical-mode software for operating a company. Legible, editable, owned. Published in case it's useful. Maintained for ourselves regardless.
