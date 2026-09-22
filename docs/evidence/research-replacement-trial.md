# Reproducing the research workflow with CE or Kortix

**September 16, 2026.** CE plus a small coordinator instruction file reproduced
the tested research handoff: discover a failed premise, preserve a human
decision, continue independent work, and resume from revised files in a fresh
session. Kortix supplies concrete primitives for the same coordination, but
was not run live. Neither result establishes a better replacement for Coga.
It does rule out treating this working relationship as exclusive to Coga.

This extends the [research-work comparison](research-work-comparison.md).
Only invented research data were used in the new execution test. Private
research material was not sent to either competitor or copied into this
document.

## What was actually run with CE

The test used CE 3.26.3 at commit
`082c83e0537c803ac1d927daafc2e6eb6962dedf`, Claude Code 2.1.273, and a
**35-line, 347-word operator file**. The operator supplied queue selection,
dependency eligibility, human-decision handling, output ownership and restart
rules. It called the unmodified `ce-work` procedure in `mode:return-to-caller`
using CE's supplied knowledge-work route. Those are real extension points,
not modifications to CE.
[Worker contract](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-work/SKILL.md),
[knowledge-work route](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-work/references/non-code-execution.md).

The invented Cedar Drying Lab queue contained an A/B analysis, an independent
inventory report, and a deliberately undefined future study. The accepted
question assumed equal temperature. Joining the observation and chamber
tables revealed that A always ran at 50 degrees Celsius and B at 70 degrees.
The obstacle was in the evidence; the analysis task did not start blocked.
An unaccepted earlier proposal falsely claimed an isolated benefit for B.

| Test condition | Observed result |
|---|---|
| Discover a contradiction in a settled research premise | The report identified method/temperature/chamber confounding and withheld a causal method recommendation. |
| Preserve the human's decision without stopping all work | Analysis became `awaiting-human`; the independent inventory completed with the correct total of 9 across 3 items. |
| Avoid inventing the unknown future programme | The undefined study remained `draft`, unchanged. |
| Keep evidence and accepted knowledge separate | Raw data, accepted context and the unaccepted proposal remained byte-identical during the run. The proposal was explicitly rejected as unsupported. |
| Continue after the owner changes direction | Between invocations, the harness staged a clearly labelled fixture-owner decision and reopened the same task for protocol design. A fresh session read those revised files and produced the new deliverable. |
| Respect the new bounded delegation | The draft specified four batches, two per method, at 60 degrees in one chamber, with airflow 3, calibration and blinded scoring. It did not execute an experiment. |
| Preserve prior work after the change | The first analysis, completed inventory, inventory plan, raw data and future draft remained byte-identical. The earlier working-state bullets were retained. |

Both invocations exited successfully. The second had no previous conversation
and did not need a person to dispatch work during execution. Actual file
contents, hashes and tool calls were checked; this conclusion does not rely
only on the model's completion messages. The compact
[receipt and operator text](ce-research-replacement-2026-09-16.json)
record the checks and source version.

There are important limits to that result:

- This was **one invented scenario across two invocations**, not repeated
  reliability testing, a comparison of human attention, or a full research
  programme migration.
- CE's source instructions were explicitly loaded in a restricted Claude
  session. This was not a marketplace-install test. No Coga runtime was
  used, and the subprocess wrapper only launched and recorded the sessions;
  the model performed the queue coordination.
- The operator is our integration. CE did not already ship this particular
  cross-investigation queue. The test also does not isolate CE's contribution
  from the model or show whether a plain agent would perform as well.
- The fixture-owner decision was staged test input, **not a real human
  acceptance or merge**. The separate human-merge stage of the
  [earlier adoption trial](adoption-trial.md) remains pending.
- Independent scientific review, experiment execution, concurrent writers,
  crash recovery and post-merge knowledge reuse were not tested here.
- Coordination success is not scientific validation. For example, the draft
  describes temperature control throughout drying but permits only three
  readings per batch; those readings cannot establish the condition over the
  whole period. It still needs substantive review.

An initial sandboxed launch could not reach the model and was interrupted;
the successful run used approved network access. The restrictive harness
denied one shell verification command in each successful invocation. The
agent completed the checks using available file tools and arithmetic. These
are recorded harness conditions, not evidence of CE queue failures.

## How I would carry the whole method over to CE

Keep the research corpus, experiment runner and accepted context. Represent
each currently useful investigation as a plan with its stage, dependencies,
accepted inputs and evidence paths. Later speculative work stays ineligible.
The owner can author the files directly or use CE's planning methods.

Use the tested operator as the outer loop. Within an investigation, encode
preparation, independent critique, owner decision, execution and
interpretation as explicit stages. The existing scientific method belongs
in reusable project instructions. A critique should run in a separate
context and inspect the protocol and evidence, rather than merely approving
the worker's summary. The experimental runner should accept only the
owner-approved protocol and input versions; generic permission to run a
shell is not acceptance of a particular experiment.

Keep three kinds of state distinct: **working evidence, pending decisions,
and accepted knowledge**. An agent may update the first two. Learned changes
go into a proposal branch or isolated directory. Shared context changes only
after human acceptance, and future runs deliberately read that accepted
version. That supplies the human-reviewed compounding policy around CE.

The new test demonstrates the outer loop and changed-direction restart. The
remaining stages above are a concrete integration design, not additional
test results. Coga already supplies a maintained lifecycle and scheduler;
the CE alternative makes more of that policy our instruction convention.
The existence of that convention does not, by itself, prove extra human
effort. Conversely, 35 lines and one successful case do not prove equivalent
operating reliability or lower maintenance.

## How I would implement the same method with Kortix

Use a coordinator session and a project-owned research skill. Store the
task queue, stage definitions, decision records and evidence references as
project files. Start with one coordinator writing queue state, so separate
workers cannot overwrite each other's scheduling decisions.

The supplied CLI provides the necessary operations:

| Coordinator action | Verified Kortix mechanism |
|---|---|
| Start an isolated worker with explicit inputs | `sessions new --json --wait --with-file ... --prompt ...` creates the session and uploads named files before delivering its prompt. |
| Detect a worker needing a person | `sessions wait-for` returns 3 for a pending question or permission, 0 for settled/idle, and 124 for timeout. |
| Retrieve results without a person relaying messages | `sessions cp` copies artifacts between sessions or a local machine; `sessions log --json` reads progress without prompting the worker. |
| Preserve work across an idle period | Stopped sandboxes retain files and conversation; the session commands can wake them. |
| Accept a shared correction | Change requests provide a diff and merge surface; configure knowledge merges to require the human. |

[CLI instructions](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-system/references/kortix/kortix-cli.md),
[actual wait implementation](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/cli/src/commands/sessions-wait.ts),
[merge implementation](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/projects/routes/r9.ts#L42).

The resulting coordinator policy would be:

1. Read current task definitions and accepted context. Select an eligible
   stage and record its attempt ID and input versions before dispatch.
2. Start a worker with those inputs and instructions to return evidence,
   outstanding decisions and its claimed outcome.
3. On a pending ask, save the session ID and exact decision on the task,
   mark it waiting for the person, and select another eligible task.
   Do not answer a reserved decision on the person's behalf.
4. On idle, retrieve and inspect the artifacts. **Idle is not proof of task
   success.** A worker can also finish by reporting a research blocker; the
   result must therefore be classified before advancing the stage.
5. On timeout, preserve the running session ID and resume monitoring later;
   do not dispatch a duplicate or call the task complete. Record transport
   failures separately from research decisions.
6. After the owner edits a decision or changes the question, reread current
   files and dispatch the appropriate next stage. Supersede stale attempts
   explicitly; do not silently answer an old permission request with a new
   task definition.

Keep unreviewed working state on the coordinator's working branch or durable
checkpoint, separate from accepted shared knowledge. **Do not require a
human merge for every intermediate queue update.** That would unnecessarily
make the person a dispatcher. Workers' artifacts can be copied and reviewed
before shared knowledge is accepted. The exact checkpoint/recovery policy
and this research-stage dispatcher would be our integration; they were not
deployed or reliability-tested here.

Existing local research hardware can remain local through Kortix's
experimental computer connector. The project must define which checkout is
authoritative and how evidence returns to the coordinator. Permission to
use the paired computer remains separate from approval of a specific run.
[Computer connector](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-computer/SKILL.md).

This is a feasible composition of inspected mechanisms, **not a live Kortix
result**. It is nevertheless enough to reject the blanket claim that
Kortix inherently requires a person to sit in front of its sessions.

## Public traction

GitHub figures below were read from the repository API on September 16,
2026. They measure public developer interest, not active users or revenue.

| Product | Repository interest | Additional public adoption evidence |
|---|---|---|
| Compound Engineering | **25,112 stars; 2,055 forks.** [Repository](https://github.com/EveryInc/compound-engineering-plugin). | Skills.sh displays about **2.8K installs of `ce-work`**, one skill through one route, not the plugin's whole user base. The retrieved registry page was cached roughly three weeks earlier. [Registry](https://www.skills.sh/everyinc/compound-engineering-plugin/ce-work). |
| Kortix / Suna | **20,212 stars; 3,436 forks.** [Repository](https://github.com/kortix-ai/suna). | Former founding COO Domenico Gagliardi reports **roughly 500,000 Suna users and a $4M seed round**. These are self-reported historical figures; active usage, retention and paid-team counts are unspecified. [First-party account](https://www.domenicogagliardi.com/). |

Every reports use of CE in its own product development and by individual
engineers at Google and Amazon, and distributes the method through its
publication and camps. That supports real adoption and an established
distribution channel; it is not evidence of company-wide deployments or a
measured CE active-user count.
[Every's account](https://every.to/source-code/compound-engineering-camp-every-step-from-scratch).

Kortix also appears on the portfolio job boards of
[Freestyle](https://jobs.freestyle.vc/companies/kortix-2) and
[Entrepreneurs First](https://portfolio.joinef.com/companies/kortix-2),
corroborating investor backing, though not the reported round size. Suna's
historical reach should not be presented as 500,000 current customers for
Kortix's present company platform. No verified current MAU, paid customer
count or product-specific revenue was found for either alternative.

Both are credible competitors with public reach. The figures do not support
ranking their retained user bases against each other. CE currently has more
GitHub stars; Kortix has the larger reported general-product audience and
reported venture funding. Those are different measures.

## The documented project flows

These are the products' supplied flows, distinct from the custom research
coordinators proposed above.

| Stage | Kortix | Compound Engineering |
|---|---|---|
| Establish the workspace | Create a Git-backed agent project with configuration, skills, permissions and memory. Current project docs recommend keeping this repository small and pointing it at the codebases it operates on. | Install CE in the existing agent environment and configure it in the working repository. Plans, project rules and learned documents remain files. |
| Define useful work | Start a session with a request, or have a configured trigger/channel start one. The agent uses the project's instructions and reads relevant memory. | Bring a brief or plan directly, or use Brainstorm to clarify scope and Plan to define decisions, units, evidence and verification. The plan is editable by the person. |
| Execute | A session gets its own sandbox and branch. The agent works there; questions or permission requests can pause that session. | Work executes an eligible plan and verifies the result. Code work has a shipping path; explicitly marked knowledge work produces the saved deliverable without code-shipping machinery. |
| Accept changes | The agent commits, pushes and opens a change request. The documented normal contract leaves review and merge to the person. Requesting changes can wake the originating session. | Review checks the work. The code path normally ends in commits and a PR; the person retains merge authority unless they delegated it. Knowledge-work review needs the relevant document/domain method. |
| Carry knowledge forward | Shared memory and instruction edits use the same CR process. A new session starts from the updated default branch after merge; an existing session retains its own filesystem and conversation. | Compound records qualifying reasoning in the solutions directory; subsequent planning retrieves relevant lessons. Capture is conditional, not mandatory paperwork for every task. |
| Delegate a longer run | Triggers and session orchestration can automate repeated work. A research queue still needs the explicit dispatch policy described above. | LFG chains a request through the relevant skills. It stops on a blocker or invalidated settled decision; our operator supplied the separate policy for continuing other investigations. |

[Kortix project](https://kortix.com/docs/project),
[sessions](https://kortix.com/docs/work/sessions),
[change requests](https://kortix.com/docs/work/change-requests),
[CE flow](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/README.md),
[CE knowledge-work behavior](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-work/references/non-code-execution.md).

**Clarification about Kortix's supplied knowledge loop:** human-reviewed
memory is already its documented normal procedure, not just something its
permissions could be configured to allow. Its current starter includes a
disabled-by-default `harness-reflector` cron that examines recent activity
and proposes changes to prompts, skills and memory through a CR. This is
substantial overlap with Dream. The website still illustrates the older,
narrower `memory-reflector`; the inspected starter uses `harness-reflector`.
This does not override the earlier finding that the implementation can grant
merge capabilities to an authorized reviewer agent, or establish a security
boundary against all out-of-band Git operations.
[Memory procedure](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-memory/SKILL.md),
[starter manifest](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/base/kortix.yaml),
[public explanation](https://kortix.com/company-as-code).

### What differs in the ticket-to-PR flow

The broad sequence of defining work, executing it and reviewing a proposed
change is shared. **Owner clarification: workflows are user-defined per
project.** A project owns reusable workflow definitions; tickets select and
carry instances of those methods. The bundled workflows are starting points,
not a fixed method every project must adopt. Coga makes the selected workflow
and current ticket step explicit runtime state. Its shipped
`code/design-then-implement` workflow assigns
design to the main agent, design evaluation to another agent, design approval
to the owner, implementation and PR creation to the agent, and final review
to the owner. The launcher chains agent steps as fresh processes and stops
at a human handoff; the same ticket carries the definition and working record.
The PR is an artifact of this particular workflow, not the universal unit of
all Coga work.
[Shipped workflow](../../src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md),
[launcher](../../src/coga/commands/launch.py),
[workflow contract](../contexts/coga/architecture/SKILL.md).

CE's plan defines the requested work while its editable skill procedures
direct execution. Kortix's project configures agents and its sessions and
change requests carry execution and integration. Both can host an additional
ticket/workflow policy. Our 35-line CE experiment tested a queue handoff and
restart from revised files; it did not reproduce Coga's complete workflow
model, role routing or transition gates. Calling the broad lifecycle shared
therefore does not establish equivalent orchestration or user experience.

## What this changes for Coga

CE is a credible small replacement experiment: the tested coordination can
be carried over without rebuilding Coga in Python. Kortix is a credible
platform replacement when shared remote operation, permissions, connectors
and its review interface are useful. Neither demonstrated a productivity,
attention or reliability advantage for the existing research programme.

The defensible Coga claim is that it **supplies this way of working directly,
through a small local tool and an editable task/context/workflow model**.
The method is portable. A competitor implementing it after we supply our
operator is different from already shipping it as the default experience,
but that distinction is a packaging and operating-quality claim, not an
exclusive capability.

Ownership and AGI language will not distinguish Coga from Kortix: Kortix's
current pitch already centres ownership and a company represented by files
in Git. Coga needs to demonstrate its specific working rhythm and simplicity
in practice. [Kortix's current positioning](https://kortix.com/about).

### Principles, supplied behavior and compatibility

The replacement result does not establish identical product philosophies.
The test transplanted part of Coga's coordination policy into CE. Successful
execution establishes compatibility with that policy; it does not establish
that CE already supplies the whole method as its default experience.

Several principles are nevertheless already supported without that addition.
CE explicitly centres planning and review, keeps its methods in editable
files, and provides both interactive work and delegated execution. Its LFG
workflow captures learning in the proposed change and leaves merging to the
person unless authorized. Standalone Compound writes learned documents into
the working tree; a universal rule preventing reuse before human acceptance
would need the project's own policy. Human judgment is therefore substantial
common ground, rather than a Coga-only value.
[CE overview](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/README.md),
[LFG](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/lfg/SKILL.md),
[Compound write boundary](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-compound/SKILL.md#write-boundary).

Kortix likewise supports owned Git files, permissions and reviewed changes.
Its stated direction is shifting autonomy from humans to agents within a
platform. Coga's stated root is improving human judgment while keeping the
system directly understandable and changeable. That is a difference in
declared priorities, not proof that Kortix prevents human-led work.
[Kortix's principles](https://kortix.com/about),
[Coga's canonical principles](../contexts/coga/principles/SKILL.md).

Coga's principles also constrain implementation: a small local substrate,
directly editable operational instructions, agent-operable mechanisms,
durable tickets and human-accepted shared knowledge. The supplied sweep makes
one pending decision compatible with progress elsewhere. This combined
contract is a valid product identity. Its rules are behavioral and
architectural commitments, not a claim that an unrestricted agent cannot
violate them. Capability overlap does not erase that identity, and identity
alone does not prove a switching advantage. The remaining comparison is how
well each product delivers the relationship its intended users want.
