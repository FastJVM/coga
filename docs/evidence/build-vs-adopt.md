# Coga: build or adopt — 2026-09-11

**Current usage assessment — 2026-09-12:** [the ten-tool follow-up](usage-comparison.md)
compares documented operator sequences and source protocols, including Pi
and the broader VS Code agent environment. Coga is moderately differentiated
overall; its standing-job operating model can be a substantial addition to
conversation-led work. CE remains the closest exercised alternative. GH-AW's
documented persistent queues and experimental correction-to-instruction-PR
pattern narrow the conceptual distinction further. Read that assessment
before treating the initial source gaps below as current missing capabilities.

**Subsequent hands-on update:** the owner authorized an [isolated replacement
trial](adoption-trial.md). CE plus 26 lines of queue instructions has now run
code and non-code plans, respected a human gate and resumed from an edited
task in a fresh session. Knowledge proposal/isolation and a separate fresh
preview of lesson reuse passed; actual human merge and accepted-knowledge
reuse remain pending. Read that evidence before
treating the source-only uncertainty below as a demonstrated product gap.

**Recommendation:** keep Coga while evaluating whether a replacement would
serve the work better. The CE trial now demonstrates a small standing queue,
handoffs and knowledge proposals with added conventions. It has not
established a better operating experience or lower upkeep. GitHub Agentic
Workflows remains a candidate for scheduled knowledge proposals. Useful
behavior and comparative benefit should decide a migration.

The marketing question is different: what distinctive way of working should
Coga stand for? The [pitch candidate](../contexts/marketing/positioning/SKILL.md)
centers on editable work definitions that agents execute and reviewed
lessons can improve. Recreating parts of that model constrains technical
exclusivity; it does not establish that the product design lacks value.

This evaluates the owner's clarified requirements, not a generic list of
agent features. The owner is willing to retire Coga if an existing setup
serves the work better. This assessment does not authorize a migration.

For the customer-facing direction, [why an existing tool user would adopt
Coga](why-switch-to-coga.md) covers each named product: current overlap, the
specific problem Coga could solve, switching costs and reasons to stay.
It distinguishes replacing a task process from adding Coga to an existing editor.

**Evidence:** primary documentation and source inspected on September 11,
an isolated Coga prompt-composition probe, seven existing isolated megalaunch
tests, and a [complete Dream-batch upkeep audit](upkeep-audit.md) of PRs
#763–775 and two local Dream session transcripts. Competitor features below
are documented capabilities, not hands-on reliability results. No competing
product had been installed or run for that initial assessment. The subsequent
CE trial above supplies actual functional evidence for one combination.
No comparative time, cost or output-quality measurement has been made;
other proposed combinations remain untested.

## Overall assessment

**Keep using Coga and validate its value with outside users.** The inspected
combination gives a coherent reason for it to exist, but neither comparative
superiority nor demand has been demonstrated. This is an analyst judgment
from the evidence below, not an owner-approved pitch or migration decision.

| Question | Judgment |
|---|---|
| Is the thesis coherent? | Yes. Agents help author and maintain the task/context files that govern execution; ticket workflows organize ongoing work; humans decide which generated knowledge becomes shared guidance. The maintenance mechanism has concrete internal history. |
| Is there meaningful differentiation? | Yes, in the integrated experience of authoring, running and revising independent work. The reviewed alternatives overlap substantially with individual parts; no complete replacement was demonstrated. |
| Is it fundamentally original or technically protected? | The ingredients have clear precedents. No strong technical moat is established by this research. Integration, defaults and daily usefulness must earn adoption. |
| Should we switch now? | There is insufficient evidence for a full migration. Keep the existing runtime while testing specific alternatives, and count all maintenance and integration costs. Competitors need to serve the useful behavior, not copy every Coga feature. |
| Is it ready to claim better outcomes or a market? | No comparative output/effort results or external retention evidence was gathered. A working mechanism does not prove that other people want to operate this way. |

The strongest value hypothesis is that maintaining clear work definitions
and reusable context reduces repeated explanation and supervision across
many tasks. Treating that as a requirement for humans to write and maintain
the whole document collection would misstate Coga. Ticket authoring,
summarization, context selection and knowledge maintenance are agent work;
the human can direct, correct and approve it. The history below shows this
division operating. Manual paperwork is therefore a substantially addressed
risk, rather than an unmitigated central weakness. The owner clarified that
setup, judgment and review also occur in the alternative workflow. They are
not incremental Coga costs merely because its files and gates expose them.
Compare total attention for equivalent work and quality, including repeated
explanation, supervision, rework and tool upkeep on both sides. Neither an
extra attention burden nor an attention saving has been established.
The observed prompt section omission remains a separate implementation
concern about delivering the authored instructions reliably.

The most plausible initial audience is a hypothesis: technical operators
already delegating recurring or multiple independent tasks, who repeatedly
explain the same context and are comfortable with files and Git. Someone
satisfied with occasional agent conversations has less reason to adopt the
structure. The useful external signal is whether a new user can complete
real work and chooses to return for another task, with less repeated
explanation or supervision. Demonstrating the full loop and observing that
behavior should precede expanding the product to win a feature comparison.
The existing Bookface/newsletter trial remains the channel plan; this
assessment does not add a new launch prerequisite or approve public claims.

## Agent-assisted upkeep: theory and recorded practice

The owner challenged the initial overhead assessment because much of this
material is AI-generated or summarized. Reviewing the contracts and local
history supports that correction. Human control of the files does not imply
human transcription or manual maintenance of every file.

**Mechanism.** The principles assign mechanizable work to agents and reserve
human attention for judgment. Guided ticket authoring writes the ticket,
selects relevant context, prepares a review summary and folds durable review
findings into the body. Retro compares completed work against existing
knowledge, drops duplicates and one-off details, patches or consolidates
contexts, and groups warranted edits into bounded, coherent PRs. Dream
finds stale knowledge and contract drift and produces proposals and a short
run summary. Human approval can therefore operate on prepared, reviewable
changes, with direct file editing available when useful.
[Principles](../contexts/coga/principles/SKILL.md),
[ticket authoring](../../src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md),
[Retro](../../src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md),
[Dream](../../coga/recurring/dream/ticket.md).

**Observed examples, not an authorship percentage.** The full September batch
contains 13 merged PRs (#763–775), verified through GitHub; the earlier local
`Dream:` subject search matched only 12 eventual commits. Inspection of
`d0f4cc14` (#773) shows context corrections against source,
Claude co-authorship, and follow-up fixes addressing three Codex review
findings. `a2028a7d` (#774) similarly records recurring-contract updates and
fixes for two review findings. `0cf17215` (#769) adds durable workflow and
launch rules to the architecture context. These demonstrate agent-assisted
knowledge upkeep and review in shipped history; commit counts do not measure
human time or prove that every line was machine-written. This attended
marketing session also demonstrates the authoring path directly: the owner
states intent and corrections while the agent maintains the evaluation,
contexts and ticket handoff.

The theory is consequently stronger than "the human maintains a wiki": the
same file interface permits AI to produce, compress and revise the operating
material, while the human retains authority. The remaining question is
whether the resulting decisions, corrections and exceptions stay manageable.
Summaries and peer review help with that too, but cannot guarantee faithful
intent or complete routing. The W36 extraction backlog records a past case
where 18 findings could not pass Retro's eligibility rules and needed a
durable follow-up; that historical count is not a claim that all 18 remain
unresolved today.
[Recorded routing failure](../../coga/tasks/dream-2026-w36-extract-backlog-18-findings-phase-4.md).

**Revised judgment:** the [complete batch audit](upkeep-audit.md) demonstrates
automated document production but only partial closure of the knowledge loop.
The apparent 22 human turns in the generation session were all machine task
notifications. Automated PR review raised 22 findings across 11 proposals;
all 13 proposals eventually merged. A warning accepted in #773 still failed
to prevent this marketing session's next-day `--prompt-report` incident.
Thus generation works, and routing accepted knowledge remains a concrete
weakness. Total human attention saving cannot be inferred from these event
counts; the owner was asked about review effort for this specific batch.

## The requirements we are comparing

The seven criteria express the owner's requested operating model, including
the subsequent request to examine megalaunch. They do not require another
product to copy Coga's commands or directory layout.

| Criterion | What a replacement must preserve |
|---|---|
| 1. Markdown is the source of truth | The task and reusable context are maintained files that govern work; a transcript or an app-only record must not become the sole authoritative definition. |
| 2. Control over the task prompt | Inspect and revise the work definition and relevant context; remove an obsolete instruction in place. Distinguish authored work instructions from additional harness instructions. |
| 3. Freedom of authoring tools | Chat, direct edits, copying and rewriting all work on the same material. Chat remains useful. Mandatory hand-writing is not a requirement. Lifecycle metadata may have dedicated commands, as it does in Coga. |
| 4. Reuse across work | Later tasks can use maintained instructions and knowledge without the human repeating the whole explanation. A fresh session must be able to work from the saved definition and needed written state. |
| 5. Proposed knowledge improvements | Agents can extract useful findings from work and propose updates to shared knowledge or procedures, including correcting stale or contradictory material. Include the effort of initiating or scheduling this work. |
| 6. Human merge of generated knowledge | A human can inspect, edit or reject proposed knowledge before it enters the shared source used by later work. Proposal work must not silently become the default input for other tasks. |
| 7. Operate a standing collection of tasks | Prepare independent tickets with their context, workflow and saved state; run ready work across them, return decisions to humans, and continue eligible work without reconstructing every task in a conversation. Demonstrate dependency handling and recovery boundaries. |
| Switching economics | Count migration, ongoing authoring/review, custom integration and upgrade maintenance against the Coga work actually removed. Similar capabilities alone do not establish a worthwhile switch. |

The owner's "desloping" means editing a current work definition to remove
ambiguity, repetition and superseded assumptions. That is supported by the
first three criteria. Neither Markdown nor a particular tool guarantees
clear reasoning or good output.

Local operation, the current Linux environment and existing agent choices
also affect migration. The comparison must cover both engineering and
non-code work. Ticket execution and human handoffs are part of the operating
model being evaluated; they cannot be treated as incidental extras. Exact
command names, ordering rules and every defensive implementation detail
need not carry over. Identify what the owner actually uses before choosing
a replacement scope.

## Comparison

"Needs integration" means a workflow or adapter remains to be supplied;
it does not mean the product makes the behavior impossible. "Not established"
means the reviewed sources do not demonstrate the complete requirement.
These are qualitative judgments against the criteria above, not scores.

| Option | Files and control of work | Knowledge loop and human merge | Switching assessment |
|---|---|---|---|
| **Coga, current baseline** | Authored ticket sections, explicit context refs, skills and blackboard are composed from files. Megalaunch operates a queue of independently maintained ticket workflows. | Dream/Retro propose shared knowledge changes through human-reviewed PRs. Knowledge must still be routed to the relevant later task. | Already integrates the desired combination. Seven isolated queue tests pass; real agent reliability is not established by those tests. Composition has a section-omission problem; no incremental authoring/review burden relative to alternatives has been established. |
| **Compound Engineering** | Accepts plan/spec file paths; editable plans and solution documents are operating inputs. Planning consults prior lessons and declared domain-rule packs. | Capture and maintenance are explicit skills. The actual trial isolates a generated correction in a worktree; human merge is pending. | **Tested with integration.** The [trial](adoption-trial.md) used 26 lines of queue instructions to run independent code/non-code plans, hold a human gate and resume a revised task from saved files. A fresh proposed-lesson consumer also passed. These go beyond the initial source-only comparison; accepted reuse and production coverage remain open. |
| **GitHub Agentic Workflows** | Markdown workflow bodies and explicit imports support authored prompts and reusable context. Normal execution is through GitHub Actions. | PR output is built in and can be the output of a knowledge-maintenance workflow. Default repo-memory auto-persistence does not provide the requested human merge gate. | **Strong candidate for the scheduled part.** Supply the extraction prompt, approved-source rules and human merge policy. A full switch also changes local attended work and task handoffs. |
| **GitHub Spec Kit** | Specifications, plans, tasks and a constitution are editable Markdown; execution reads those artifacts. Clarification and consistency checks support refining the definition. | A constitution-update procedure and extension hooks exist. A complete recurring extraction-to-human-merge loop was not established in the inspected core. | **Strong document-workflow overlap.** Consider with a knowledge-loop component if its planning workflow fits. Do not count it as a complete Dream replacement by itself. |
| **Kiro** | Specs include requirements, design and tasks files; Markdown steering supplies reusable context with selectable inclusion modes. Direct writing and conversational refinement are documented. | Web feedback can produce future guidance. The reviewed sources do not establish a required human-merged Markdown proposal for each learned change. | **Strong document-interface overlap.** Investigate only if adopting the Kiro environment is desirable; evaluate its knowledge gate separately from spec approval. |
| **Backlog.md** | Repo Markdown tasks, documents and decisions; tasks carry references, plans and notes. CLI/UI and editor authoring are documented. The usage guide explicitly recommends refining the task before a fresh-session rerun. | Agents read referenced docs and update relevant docs at completion. A full automatic extraction, maintenance and human-merge loop was not established. | **Potential ticket component.** The surrounding execution and knowledge-review process must be supplied or already exist. A better board alone does not justify replacing Coga. |
| **Superset** | Editable app/issue tasks become agent prompts through configurable templates. Agents can also work with repo files; the native task view is not established as a canonical Markdown ticket store. | Skills, scheduling, workspaces and PR review supply useful pieces. A Dream-equivalent knowledge policy must be supplied. | **Potential host for a replacement combination.** Keep Markdown authoritative explicitly. On this Linux environment, the desktop is experimental; the CLI supports Linux. |
| **Zed** | A file editor with project Markdown instructions and reusable skills; agent threads and worktrees organize execution. External agents retain their own instruction-loading behavior. | The reviewed sources do not establish a built-in completed-work-to-reviewed-knowledge loop. An appropriate agent skill could supply it. | **Useful interface or host.** Can be used with Coga as well as a replacement. Editor/session persistence is not by itself a substitute for the requested knowledge workflow. |
| **Agent Orchestrator (AO)** | Its documented center is a persistent project coordinator plus delegated agent workspaces and task context. A canonical Markdown task/context operating model was not established. | Feedback routing and supervision are documented; reviewed sources do not establish Dream-style human-merged knowledge extraction. | **Runtime candidate alongside Superset.** Compare coordination against megalaunch as well as file authority and the knowledge gate. The earlier lower priority based mainly on knowledge capture was too narrow. |

VS Code prompt files were initially checked as a narrower precedent: editable
Markdown prompts can be run in its Local agent; Agent Host users are directed
toward skills. The [September 12 follow-up](usage-comparison.md#vs-code)
also includes custom-agent handoffs, the Agents window and preview automation
and memory. The narrow feature comparison does not represent the full product.
[Prompt-file documentation](https://code.visualstudio.com/docs/agent-customization/prompt-files)

## What megalaunch adds to the comparison

The owner pointed to megalaunch after the initial evaluation. Inspection of
the engine confirms that reusable prompts and knowledge capture omit an
important part of Coga: the maintained files also define a collection of work
that the runtime can operate independently of the authoring conversation.

- The default sweep selects the operator's eligible active or in-progress
  tickets, optionally within a directory. Each ticket retains its own
  workflow, assignee, selected context and blackboard.
- Agent-owned steps run in fresh sessions. After a lifecycle transition,
  the runtime reads the ticket again and either launches the next eligible
  step or ends that task's chain at a human handoff, blocker or terminal state.
  The sweep can then service other tickets. Missing input becomes a recorded
  blocker rather than a question that holds the whole queue open.
- After the default sweep, a dependency pass can retry blocked tickets whose
  blocker names a finished task. It repeats until no more launches occur.
  This is exact-slug matching in blocker text, not a general dependency graph
  solver. Explicit selections stay within the selected work.
- Execution is sequential. Eligible in-progress work can resume, but an
  existing published launch claim requires explicit recovery; megalaunch
  does not automatically reclaim every interrupted session. Step and session
  limits also constrain a run.

[Engine](../../src/coga/megalaunch.py),
[queue conduct](../../src/coga/resources/prompt-megalaunch.md),
[workflow and launch contract](../contexts/coga/megalaunch/SKILL.md).

Compound Engineering also orchestrates work. Its `lfg` runs a hands-off
software shipping pipeline and explicitly supports invocation by schedulers,
loops and enclosing orchestrators. `ce-work` dispatches dependency layers
with fresh workers; its external execution controller records durable unit
state and recovery information. Consequently, neither autonomy, fresh
contexts nor recovery alone distinguishes Coga.
[LFG](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/lfg/SKILL.md),
[worker scheduling](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/execution-strategy.md),
[external execution contract](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/cross-model-execution.md).

The narrower difference supported by these sources is the operating unit:
Coga services independently authored tickets with their own persistent
workflows and human return points. The inspected CE execution contracts
organize a plan's implementation units and shipping stages; its feedback
sweep produces a rolling plan. They do not establish the same general ticket
queue by themselves. CE's separate knowledge-work route handles non-code
deliverables. **September 14 refresh:** the current `lfg` protocol also
routes non-code requests; the earlier software-only characterization of
that entry point is superseded. Use the
[current ladder assessment](pitch-evaluation.md#marketing-ladder-assessment--2026-09-14)
for the updated comparison.
[Feedback sweep](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-sweep/SKILL.md),
[knowledge work](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/non-code-execution.md).

For example, a code ticket can reach review while a research ticket follows
a different workflow. A human can revise the next task and its context using
chat or file edits, then run eligible work from that saved definition.
Separately, Dream/Retro can propose reusable changes for human merge;
subsequent launches can consume the accepted context. Megalaunch does not
itself invoke Dream, and finishing a task does not automatically prove a
knowledge improvement. Together these facilities support the intended
cycle: prepare work, run it, review decisions and knowledge, then reuse the
maintained material. A replacement evaluation must exercise that cycle.

## Evidence behind the switching judgments

**Compound Engineering:** `ce-work` takes plan/spec paths, and its knowledge-work
branch can produce non-code deliverables. It should not be dismissed as
incapable of this marketing/research work. `ce-compound` captures verified
lessons; planning searches relevant lessons, and `ce-compound-refresh`
maintains them. Experimental packs add reusable domain rules.
[Work entry](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/SKILL.md),
[non-code execution](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/non-code-execution.md),
[capture](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound/SKILL.md),
[planning](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-plan/references/research.md),
[maintenance](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound-refresh.md),
[packs](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/packs.md).

The knowledge-review gap is specific: capture completes after writing locally, and refresh
has several commit paths. Human-reviewed PRs are possible, but not a
universal capture requirement. Capture also handles one learning per run;
its research procedure uses the current session and optional session history.
We must test extraction from completed written tickets without relying on
the old conversation. A scheduler or retrospective pass and candidate
isolation remain integration work. Its `ce-sweep` scans configured feedback
sources into plans; that is not evidence of an equivalent whole-corpus Dream
knowledge scan.
[Capture completion](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound/references/report.md),
[refresh commits](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound-refresh/references/commit.md),
[capture research](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound/references/research.md),
[feedback sweep](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-sweep/SKILL.md).

**GitHub Agentic Workflows:** runtime imports can inject reusable Markdown
into an authored workflow prompt. A configured `create-pull-request` output
creates a branch and PR. A knowledge workflow can use those mechanisms with
human merge and later readers using approved repository content. This is a
plausible configuration, not an executed replacement. Repository memory
instead auto-commits/pushes qualifying changes, so using that feature as the
accepted knowledge source would miss the owner's gate.
[Workflow model](https://github.com/github/gh-aw),
[imports](https://github.github.com/gh-aw/reference/imports/),
[PR output](https://github.github.com/gh-aw/reference/safe-outputs-pull-requests/),
[repo-memory behavior](https://github.github.com/gh-aw/reference/repo-memory/).

**Spec Kit and Kiro:** both are substantial counterexamples to a claim that
only Coga operates from maintained task documents. Spec Kit's implementation
prompt requires reading tasks and plans; its constitution command maintains
a shared governance document. Its extensions also include non-software idea
assessment. Kiro executes `tasks.md` and supports Markdown steering files,
including manual inclusion and direct authoring. Kiro Web's learning from
owner PR feedback is a different documented flow from reviewing and merging
the resulting knowledge diff.
[Spec Kit execution](https://github.com/github/spec-kit/blob/main/templates/commands/implement.md),
[constitution](https://github.com/github/spec-kit/blob/main/templates/commands/constitution.md),
[Spec Kit scope](https://github.com/github/spec-kit),
[Kiro specs](https://kiro.dev/docs/specs/),
[Kiro steering and feedback](https://kiro.dev/docs/steering/).

**Backlog:** the source specifies Markdown tasks/documents/decisions,
reference reading, implementation notes and documentation updates. Its
agent-side editing restriction is a tooling difference; it does not mean
humans must use chat or cannot write their own descriptions. Coga also
protects lifecycle metadata from arbitrary editing.
[Agent workflow](https://github.com/MrLesk/Backlog.md/blob/main/src/guidelines/agent-guidelines.md),
[human workflow](https://github.com/MrLesk/Backlog.md#working-without-ai-agents).

**Superset, Zed and AO:** these can supply useful execution interfaces while
files and knowledge procedures remain elsewhere. Superset exposes task
prompt templates and agent skills; its CLI and desktop have different Linux
support. Zed documents Markdown instructions and skills, with loading rules
that vary for external agents. AO describes a persistent project coordinator
above individual tasks. None of those descriptions proves that their agents
cannot be taught the Coga methodology; none establishes the complete desired
loop without supplying that methodology.
[Superset tasks](https://docs.superset.sh/tasks),
[skills](https://docs.superset.sh/skills),
[platform support](https://docs.superset.sh/faq),
[Zed instructions](https://zed.dev/docs/ai/instructions),
[Zed skills](https://zed.dev/docs/ai/skills),
[AO](https://github.com/Untrivial-ai/agent-orchestrator).

## Coga must meet the same standard

Seven existing tests passed against this checkout's megalaunch source:
agent-step chaining, retention of a human gate under an agent override,
directory scoping, repeated dependency retries, explicit-selection scope,
eligible in-progress resume, and refusal to reclaim a published session claim.
These use temporary repositories and mocked agent launches. They verify
queue decisions, not live agent performance, terminal behavior or production
Git publication. The installed Coga environment lacked pytest; the tests
ran with the existing system Python and the checkout's `src` on `sys.path`.
[Existing tests](../../tests/test_megalaunch.py).

An isolated September 11 probe called `compose_prompt_report` directly
against temporary Markdown files and an in-memory configuration. It used
the current checkout's `src/coga/compose.py`, SHA-256
`2b179e53ea1febad37cb959cbc61f30a8e188151f870a1bf65210dcd7428f0ef`.
No agent, CLI launch, Git operation or network call ran in this probe.

| Observation | Result |
|---|---|
| Description, inline context, nested acceptance criteria and written blackboard | Delivered in the composed prompt. |
| Explicitly selected context | Delivered; an unselected context was absent. |
| Rewrite the task and selected context, then compose again | New text delivered; previous sentinel text absent. |
| Reference a missing context | Composition raised `ComposeError`. |
| Put a requirement under a sibling `## Extra requirements` heading | **Silently omitted**, despite being visible in the ticket file. |

The last result weakens the current implementation of direct prompt control.
Use the supported task sections today; this evaluation does not implement a
fix. The probe verifies input delivery, not whether an agent follows the
input, whether Dream extracts good lessons or whether later work improves.
[Composition source](../../src/coga/compose.py),
[composition contract](../contexts/coga/architecture/SKILL.md).

Dream's human merge requirement is an explicit operating contract backed by
isolated proposal work. It is not a claim that no agent can ever write an
unapproved local document. Fair comparisons should inspect candidate work
isolation and approved-source selection on both sides. Written state and
context selection also take upkeep; more documents do not guarantee more
useful context.
[Coga principles](../contexts/coga/principles/SKILL.md),
[Retro](../../src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md),
[Dream](../../coga/recurring/dream/ticket.md).

## The combinations worth considering

1. **Retain the Coga runtime and evaluate selected Compound Engineering
   procedures.** Test whether its planning, execution or knowledge-maintenance
   procedures improve our work enough to adopt. Keep the human merge rule
   for generated shared knowledge. This is a potential partial adoption;
   retiring Coga additionally needs a demonstrated replacement for the ticket
   queue and workflow handoffs. The evidence does not yet show that this
   remaining integration would be small.
2. **Local document-driven work + GitHub Agentic Workflows for retrospective
   knowledge proposals.** A credible partial replacement if moving scheduled
   work to Actions is acceptable. Reuse the extraction instructions and PR
   review discipline; assess runner setup and the split between local tasks
   and hosted jobs. This can replace one component without migrating every
   task at once.
3. **A task/document tool + an execution runtime + reviewed knowledge.**
   Backlog or Spec Kit could supply work artifacts; Superset or AO are
   candidates for execution. Demonstrate who owns the current task, how
   arbitrary workflows return to humans, and what happens after interruption
   before recommending a particular pairing. Format conversion and duplicated
   state may cost more than retaining Coga.
4. **Superset or Zed as the interface around retained Coga.** Choose based on
   execution and editing needs. This can improve the daily experience while
   keeping the current task and knowledge system; a host change alone does
   not establish a completed runtime or knowledge-loop migration.

These are candidate architectures, not installed integrations. Coga does not
need to be uniquely capable to be worth keeping, and an alternative does not
need to reproduce every Coga feature to be worth adopting.

## The test that decides whether switching is worth it

For a full-switch trial, first identify a candidate combination that claims
to cover the queue as well as authored prompts and reviewed knowledge. Run
it and Coga against the same bounded collection of engineering and non-code
tickets, with comparable agents and approved starting knowledge. Component
trials can cover less, but cannot establish a full replacement. This protocol
is the basis for the subsequent trial above. That trial runs a candidate on
a synthetic fixture; a new matched Coga run has not been performed.

| Exercise | Evidence needed |
|---|---|
| Edit through different tools | Create a task through chat, directly revise it, copy/reuse context, and confirm one maintained definition governs the next run. Record any conversion or duplicate state. |
| Clean the current definition | Remove a superseded instruction, start fresh and inspect the actual task/context supplied. Check supported headings and any extra harness layers. |
| Run a prepared collection | Use several saved tickets with different workflows: one ready, one awaiting a human, one dependent on another. Eligible work must progress without narrating the queue in chat, human gates must hold, and dependency handling must be visible. |
| Return and recover | End a worker session, revise a later task, and continue from saved state without duplicating completed work or bypassing ownership. Record manual recovery and any dependence on the previous coordinator's transcript. |
| Extract from completed work | Provide the finished ticket and evidence without its old chat. Show a proposed reusable lesson and a stale-rule correction, including why each is warranted. Record manual prompting or scheduling needed. |
| Reject an overgeneralization | Reject one plausible but wrong proposed rule. A later ordinary task must not consume that candidate as approved guidance. |
| Accept and reuse a lesson | Edit and merge another proposal. A different fresh task must find and use the accepted lesson without the human restating it. Inspect the resulting behavior, not just a citation to the document. |
| Account for the total work | Record authoring, review, reminders, missed context, repair work, tool/config maintenance and the Coga capabilities that can actually be removed. Keep setup cost separate from recurring effort. |

Switch when the candidate passes the required behaviors and the work it
removes outweighs migration and ongoing integration effort. If keeping the
gate and file authority requires rebuilding a comparable task runner and
retrospective system, retaining Coga is reasonable. If a few maintained
instructions and existing tools suffice, prefer adopting those and retiring
the redundant implementation. No numeric threshold or performance result
has been selected by the owner.

The next comparison should cover runtime behavior before recommending a
full-switch candidate; partial adoption of CE procedures or hosted knowledge
jobs can be evaluated independently. A complete switch is not yet supported
by observed comparative use. The value of the clarified operating model also
does not establish market demand; the marketing/user-adoption question
remains separate.
