---
slug: improve-prompt-for-relay-ticket
title: improve prompt for relay ticket
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
contexts: []
skills: []
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-coga
    skills: []
    assignee: agent
step: 3 (report-to-coga)
---

## Description

Investigate how Relay's ticket-creation interview (the `bootstrap/ticket`
skill that runs `relay ticket`) could be improved, and produce a concrete
**proposal** — not edits. The interview is suspected of asking too few or the
wrong questions, so tickets sometimes launch underspecified. Study the current
flow, let the investigation surface the real weak spots rather than assuming
them, and propose specific changes: better/different interview questions,
ordering or flow changes, and places the interview drops context it should
capture.

The deliverable is a written proposal (weak spots found, with examples from
real tickets; specific question/flow changes, ranked) on this ticket's
blackboard for the human to review. A separate follow-up ticket implements
whatever is accepted. **Do not edit the skill in this ticket.**

## Context

- The interview being studied:
  `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` — the live skill behind
  `relay ticket`. A packaged copy lives at
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`;
  note it for the future implementation ticket, but make no edits here.
- Prior art on ticket quality — read before proposing, so the work doesn't
  duplicate what already exists:
  `relay-os/bootstrap/skills/eval/ticket-diagnostic/SKILL.md` (a ticket
  diagnostic) and the step-6 evaluator review already baked into creation.
  Note the `ticket-diagnostic` skill is itself half-finished (it still
  contains a `<<YOU NEED TO BE MORE SPECIFIC HERE>>` placeholder) — treat it as
  a signal of intent, not polished prior art.
- Step 3 of the interview runs the autonomy triage in
  `relay-os/contexts/autonomy/triage/SKILL.md`. Any proposal touching the
  autonomy question must stay consistent with it.
- Keep it lean: the skill deliberately targets a short 4–6 question interview,
  and Relay is markdown-first and optimizes for human legibility and a tight
  correction loop (`docs/vision.md`,
  `relay-os/contexts/relay/principles/SKILL.md`). Heavier is not automatically
  better — adding questions has a real token/precision cost.
- Evidence: skim a handful of real filled tickets — they live in two layouts,
  flat `relay-os/tasks/<slug>.md` and nested
  `relay-os/tasks/<group>/<slug>/ticket.md` (so glob `relay-os/tasks/*.md` and
  `relay-os/tasks/**/ticket.md`, not `tasks/*/ticket.md`). Find where the
  current interview produced thin `## Description` / `## Context` sections and
  cite those as concrete motivation — but don't assume every thin ticket is the
  interview's fault; a thin answer or a skipped step can cause the same, and
  the proposal should distinguish them.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Human decision (2026-07-21)

Nick accepted the proposal below: all three P0 changes and all three P1
changes. P2 stands as written (no formal Acceptance Criteria section for now).
Follow-up implementation ticket created:
`implement-accepted-ticket-interview-improvements` (draft, `code/with-review`).
Two facts discovered while scoping it, corrections to the proposal's
implementation notes: `eval/ticket-diagnostic` was already deleted in PR #603
(its signal folded into ticket Step 6), and the packaged copy under `src/` is
the only source of the skill — there is no live `coga/skills/` override to
sync.

## Evaluator review

(Independent cold read of the filled ticket, step 6 of bootstrap/ticket. Two
items below were fixed in the body after this review: the broken
`tasks/*/ticket.md` evidence glob, and a caveat that ticket-diagnostic is
half-finished. The assignee/human ambiguity is left for the human to resolve.)

**Description — clear enough to start cold? Yes.**
- Cleanly states the task (investigate the `relay ticket` interview, produce a proposal), the deliverable (ranked weak-spots write-up on the blackboard), and the hard boundary (no edits, repeated three times). The "let the investigation surface real weak spots rather than assuming them" framing is good — it guards against the agent just rubber-stamping the stated suspicion. A future agent could begin without further questions.

**Workflow fit — `autonomy/assist-only` is a reasonable fit, mild semantic stretch.**
- The shape (agent drafts → human owns/decides → no irreversible step) maps onto the workflow's three steps (`agent-produces` / `human-owns-and-finishes` / `report-to-relay`). Good match for "investigate → proposal doc → human decides."
- Minor mismatch: assist-only's own text frames it for "quality, taste, or differentiating judgment, not feasibility." This task is more analytical/investigative than taste-driven. `autonomy/human-verify` would also fit. Not worth blocking on — assist-only's "call out assumptions/weak spots rather than hiding them" guidance actually suits a proposal doc well — but worth a glance at launch.

**File pointers — one broken glob, the rest accurate.**
- BROKEN: the Evidence bullet says skim "real filled tickets under `relay-os/tasks/*/ticket.md`." That glob matches exactly one file — `_template/ticket.md`. Real tickets live in two layouts: flat `relay-os/tasks/<slug>.md` (47 of them, including this very ticket) and nested `relay-os/tasks/<group>/<slug>/ticket.md` (9, two levels deep). An agent following the pointer literally would find essentially no evidence. Should read `relay-os/tasks/*.md` and/or `relay-os/tasks/**/ticket.md`.
- All other pointers verified present and on-point: `bootstrap/ticket/SKILL.md` (live + packaged copy), `eval/ticket-diagnostic/SKILL.md`, `contexts/autonomy/triage/SKILL.md`, `docs/vision.md`, `principles/SKILL.md`. The claim that a "step-6 evaluator review [is] baked into creation" is accurate (it's step 6 of the ticket skill — the review you are reading is that step).
- Worth flagging to the investigator (not a ticket defect, but material to the actual work): the `bootstrap/ticket` skill itself uses the same wrong `tasks/<slug>/ticket.md` shape throughout, and the `eval/ticket-diagnostic` prior-art skill is half-finished — it contains a literal `<<YOU NEED TO BE MORE SPECIFIC HERE>>` placeholder. The agent should not treat ticket-diagnostic as polished prior art.

**`contexts: []` — correct call.** The material the agent needs is the two skill files and the triage context, all of which are *process/skill* knowledge pointed at by path — exactly what the skill's selection contract says to do (skills aren't attached as contexts; pointers go in the body). `vision`/`principles` are cited for one narrow fact ("keep it lean"), which the contract explicitly says to inline-by-reference rather than attach. No context's full body genuinely needs inlining here. Don't add any.

**Scope — well bounded, single ticket.** Investigate + write proposal, with implementation explicitly deferred to a named follow-up ticket. The three analysis angles (questions / ordering / dropped context) are one cohesive study, not three tickets. Good.

**Assumptions to question before launch:**
- Assignee inconsistency: `owner: nick`, `human: nick`, but `assignee: zach`, `agent: claude`. `zach` is not an agent — relay.toml defines only `claude` and `codex` as agents; `zach` appears solely as a Slack-user mapping (i.e. a person). So it's unclear who the reviewing human is (nick per `human:`, or zach per `assignee:`) and why they differ. Resolve before launch.
- The evidence strategy assumes thin `## Description`/`## Context` sections in past tickets are caused by the *interview*. They could equally come from the human giving thin answers or the agent skipping interview steps. The proposal should not attribute every thin ticket to the questions themselves.
- Assumes a markdown/blackboard proposal is the right deliverable home; that's consistent with Relay conventions, so fine.

Net: solid ticket. One must-fix (the `tasks/*/ticket.md` evidence glob is broken) and one should-resolve (assignee vs human ambiguity). Everything else is in good shape.

## Proposal: improve the ticket interview

### Executive summary

The current `bootstrap/ticket` interview is mostly pointed in the right
direction, but it asks for the most important launch material too abstractly.
The weak pattern in real tickets is not "no workflow was chosen" as much as
"the future agent has to recover done criteria, source files, traps, and scope
from the title, blackboard, or live investigation." The fix should keep the
interview short and make each question carry more structure.

Recommended implementation: keep the 4-6 question budget, but rewrite the
substantive interview around three required outputs:

1. objective + why + definition of done,
2. handoff context with files, related tickets, constraints, traps, and tests,
3. autonomy/workflow/context choices grounded in the existing Coga corpus.

Also make the evaluator review use the existing diagnostic axes and require
gaps to be folded back into the ticket body before launch approval, not left as
durable guidance only on the blackboard.

### Evidence sampled

- Current interview text: `coga/bootstrap/skills/bootstrap/ticket/SKILL.md`
  still says the interview is short (4-6 questions), asks only "what should it
  do, and why?" for the new-title opener, then uses broad `Description` and
  `Context` prompts in Step 3. It also points examples at
  `coga/tasks/<slug>/ticket.md`, which misses the many bare `.md` tasks in this
  repo. The packaged copy has newer package-resource wording in Step 2, so the
  live and packaged copies need logical sync, not blind byte-copy.
- Prior art: `coga/bootstrap/skills/eval/ticket-diagnostic/SKILL.md` has the
  right evaluation axes (`Objective`, `Done`, `Scope`, `Knowledge`,
  `Workflow fit`, `Safety`), but its process is unfinished and still includes
  `<<YOU NEED TO BE MORE SPECIFIC HERE>>`. Treat it as a rubric source, not a
  workflow to invoke unchanged.
- Thin/failed authoring examples:
  - `coga/tasks/relay-ticket-doesn-t-ask-quesion-and-start-doing.md` is an
    empty draft with a title that directly names the authoring failure. This
    could be a raw draft or interrupted interview, so it is not proof by
    itself, but it is exactly the kind of state the interview should recover
    or explicitly leave as concept-capture.
  - `coga/tasks/remove-relay-migration-script.md` reached `done` with empty
    `## Description` and `## Context`; the real scope was recovered in
    blackboard implementation notes ("ticket body is empty beyond the title",
    target file, stale references, human-confirmed scope). That is recoverable
    but not a good launch artifact.
  - `coga/tasks/v2/acceptance-criteria.md` specifically asks for acceptance
    criteria / definition of done in tickets, and its own `## Context` is
    empty. This is both evidence of the need and a caution that a new section
    alone will not help unless the interview asks the right question.
- Strong examples:
  - `coga/tasks/branch-cleanup-as-recurring-tasks.md` is what "good context"
    looks like: it names the model to copy, concrete deletion gates, exact
    modules, packaged-copy sync, tests, history, and out-of-scope boundaries.
  - `coga/tasks/trim-blackboard-eval-once-processed.md` gives hook point,
    primitives, safety/no-op behavior, tests, and out-of-scope. Its evaluator
    review found real gaps that were then promoted into the body.
  - `coga/tasks/install/retest-ssh-https-and-init-reclone-on-fresh-machine/ticket.md`
    is a compact good ticket: description states the customer report and why
    now; context names prior tickets and code touchpoints.
- Related product pressure: `coga/tasks/stop-trimming-blackboard-but-refuse-to-launch-befo.md`
  exists because evaluator/authoring material can remain in the blackboard
  instead of being synthesized into the launch-ready body. The ticket
  interview should prevent that state rather than depending on first-launch
  refusal to catch it later.

### Ranked changes

**P0 — Add "done" to the first substantive question.**

Current prompt asks for what and why; it should ask for what, why, and done in
one breath. This stays within the question budget and aligns with
`eval/ticket-diagnostic`'s `Done` axis.

Proposed new new-title greeting:

> "Your `<slug>` ticket has been created (draft). What should it do, why now,
> and what would count as done? I'll turn your answer into the ticket."

Proposed Step 3 replacement for `Description`:

> **Objective / done** — capture what needs to happen, why it matters now, and
> the smallest observable result that means the ticket is done. This becomes
> `## Description`; if done criteria are not explicit, add one sentence rather
> than a new section unless the ticket already uses an Acceptance Criteria block.

Tradeoff: this slightly lengthens the opener. It is still cheaper than adding a
separate acceptance-criteria question or new field to every ticket.

**P0 — Make the context question concrete, not aspirational.**

The current "what's the agent going to wish they knew?" prompt is good taste
but too easy to answer with nothing. Replace it with a checklist-shaped single
question. The agent should not ask every sub-bullet separately; it should use
the bullets to pull missing details.

Proposed Step 3 `Context` prompt:

> **Handoff context** — ask for the future agent's starting map:
> files/modules/commands to inspect, related tickets or PRs, constraints and
> out-of-scope lines, known traps, verification commands, and any safety or
> rollback concern. This becomes `## Context`. If the human gives a thin answer,
> ask one targeted follow-up before writing an empty context.

For code tickets, the targeted follow-up should usually be:

> "What file or module should the implementer read first, and what trap should
> they avoid?"

For docs/proposal tickets:

> "What source docs or prior decisions should the writer treat as binding, and
> what is out of scope?"

Tradeoff: the question is denser. The payoff is high because it asks directly
for the fields that strong tickets already contain.

**P0 — Fold evaluator findings back into the ticket body before approval.**

Step 6 currently writes the evaluator review verbatim to the blackboard and
Step 7 asks the human to validate. That leaves a common failure mode: the
blackboard contains the actual launch guidance while the body stays thin. The
new first-launch refusal ticket will catch some of this, but authoring should
avoid creating the state.

Proposed flow change:

- Keep the independent evaluator.
- Change its rubric to the diagnostic axes: Objective, Done, Scope, Knowledge,
  Workflow fit, Safety.
- Ask it to mark findings as `must-fix before launch`, `nice-to-have`, or
  `question for human`.
- After the evaluator writes to the blackboard, the authoring agent must handle
  `must-fix` items before closing the authoring session: either edit
  `## Description` / `## Context` directly when the fix is mechanical, or ask
  the human one concrete question and then edit. The blackboard remains the
  audit trail; the body becomes the launch source of truth.

Tradeoff: authoring may take one extra exchange when the evaluator finds a
real gap. That is exactly when the extra exchange pays for itself.

**P1 — Add a "thin answer recovery" rule.**

The skill says "stop pulling once you have enough," but does not define "not
enough." Add a simple refusal-to-write-empty-body rule for guided authoring.

Proposed rule:

> If `## Description` would be blank, title-only, or generic, ask one follow-up.
> If `## Context` would be blank on a non-concept-capture ticket, ask one
> follow-up. If the human intentionally wants a placeholder idea, leave it as a
> workflow-less draft and write one sentence in the body saying it is
> concept-capture and not launch-ready.

This distinguishes real authoring failures from legitimate concept-capture
drafts. It also aligns with the current architecture: workflow-less drafts are
valid, but launchable work should not be empty.

Tradeoff: the interviewer becomes slightly less willing to accept a sparse
answer. That is acceptable because `coga create` already exists for quick raw
stubs.

**P1 — Update task-shape and resource-discovery guidance.**

Both the task body that launched this proposal and the live
`bootstrap/ticket` skill still carry path-shape assumptions from older Relay
layouts. The implementation ticket should update both live and packaged copies
for current Coga behavior.

Proposed guidance:

- For examples, sample real tasks in both supported ticket shapes:
  `coga/tasks/**/*.md` for bare single-file tasks and
  `coga/tasks/**/ticket.md` for directory tasks.
- Exclude support files such as `blackboard.md`, `log.md`, and `README.md`
  when sampling examples.
- For bundled workflows/contexts/skills, use the package bootstrap root in the
  packaged copy and local override roots in the live/project copy. The two
  copies may need equivalent wording rather than byte-identical text.

Tradeoff: this is mostly maintenance text, but stale example paths are a real
source of bad prior art for future authoring agents.

**P1 — Move "missing context/skill" into a conservative proposal path.**

Step 4 currently tells the authoring agent to create missing contexts/skills
inline. That is right for obvious prompt payload gaps, but too heavy for
speculative process gaps found during a short interview.

Proposed rule:

> Create a new context inline only when the future launched agent needs that
> exact body to do the ticket correctly and the human confirms the name. For a
> possible reusable process or broad pattern, write a `## Proposals` note on the
> ticket blackboard or a follow-up ticket suggestion; do not expand the current
> authoring session into framework work.

Tradeoff: fewer contexts/skills are created immediately. That preserves the
lean authoring loop and keeps context growth human-gated.

**P2 — Do not add a permanent `Acceptance Criteria` section yet.**

The evidence supports asking for done criteria; it does not yet prove every
ticket needs a new top-level section. Strong existing tickets encode done in
Description, Context, proposed shape, or checklists depending on task type.

Recommendation: first add "what counts as done?" to the interview and evaluator
rubric. Revisit a formal section later if ticket bodies still bury done
criteria after this change.

### Proposed Step 3 shape

The interview can stay at five human-facing prompts:

1. **Objective / done** — "What should this ticket do, why now, and what would
   count as done?"
2. **Handoff context** — "What should the future agent know before starting:
   files/modules, related tickets, constraints/out-of-scope, traps, tests, or
   safety/rollback?"
3. **Autonomy triage** — keep the existing three-question autonomy test and
   tier mapping; it is already consistent with `coga/contexts/autonomy/triage`.
4. **Workflow + contexts** — propose the lightest workflow and the narrow
   context list together, explaining any copied fact vs attached context.
5. **Assignee + extension fields** — keep current behavior.

Only ask a sixth question when the first two answers are too thin or the
evaluator finds a must-fix gap. That preserves the short-interview design while
making sparse launch artifacts less likely.

### Implementation ticket scope

Accepted changes should be implemented in a separate ticket. Suggested scope:

- Edit `bootstrap/ticket` Step 3, Step 6, and Step 7 in both source copies:
  live/project copy and packaged resource copy.
- Update task-shape/resource-discovery wording where it appears in
  `bootstrap/ticket` and `eval/ticket-diagnostic`.
- Add tests that assert the shipped skill template mentions definition of done,
  the concrete context buckets, current task shapes, and evaluator synthesis.
- Do not change `coga ticket` command behavior unless the text change exposes a
  real CLI mismatch.

### Assumptions and weak spots

- I sampled a handful of tickets, not the full corpus. The pattern is strong
  enough to propose prompt changes, but not enough to quantify failure rate.
- Empty `## Description` / `## Context` is not automatically the interview's
  fault. Some files are raw concept-capture drafts, old Relay-era tickets, or
  interrupted sessions.
- The repo is mid-rename from Relay to Coga in several artifacts. The follow-up
  should decide whether to keep "Relay" wording where it is product-history
  accurate or migrate the authoring skill text fully to Coga.
