# Coga, Compound Engineering and Kortix for open-ended research

**2026-09-16. Recommendation: keep Coga for the existing research programme;
consider CE methods as additions. Kortix becomes attractive when a shared,
remotely operated platform is itself a requirement.** Neither alternative
has demonstrated a better replacement for this programme. Both can support
human-led research, and several purported Coga exclusives are already supplied
elsewhere.

This follows the [human-schedule comparison](human-centered-comparison.md).
It compares the working method, rather than counting agent features. The
private research records were inspected locally; their details are excluded
from this public-facing document. The sequence below is an illustrative
research pattern. A subsequent [live CE replacement test and traction check](research-replacement-trial.md)
used invented data to test part of that pattern; it did not execute the
private research programme or a live Kortix instance.

## The work being compared

The person does not know the entire future task list. They know a useful
question and the next investigation that could change their decision:

1. Define a question and competing explanations.
2. Prepare a bounded experiment and obtain an independent critique.
3. Have the owner accept its exact scope and inputs.
4. Execute the agreed experiment and preserve the observations.
5. Audit the interpretation, including conflicting and negative evidence.
6. Let the person retain, change or abandon the question.
7. Record accepted conclusions and define the next useful work from them.

Other eligible work should advance while one item awaits that decision.
Restarting should recover the current accepted question, pending decisions
and evidence from files. This is the meaningful unknown-work requirement:
**the method can be reusable while the next research task remains unknown.**

All three need the operator's domain expertise: hypotheses, experimental
controls, evidence standards and acceptance criteria. Giving Coga credit for
those user-authored rules while counting them as competitor integration
would be an unfair comparison.

## What each actually supplies

| Requirement | Coga | Compound Engineering | Kortix |
|---|---|---|---|
| Directly edit the work and reusable instructions | Tasks, contexts and workflows are explicit primitives. | Editable plan files, skills, project instructions and learned documents. | Git-backed project instructions, skills, memory and manifest. |
| Investigate before deciding | The operator attaches the investigation method to a task. | Brainstorm, POV and Bake-off explicitly support exploration and judgment; Optimize supports measured experiments. | Deep Research supports investigations with sources and notes on disk; experimental methodology still needs a project skill. |
| Separate preparation, critique, human decision and execution | Ordered workflow roles and owner handoffs are read by the runtime. | Supplied skills have their own gates and return contracts. The equivalent programme needs an outer workflow convention. | Sessions, review surfaces, permissions and change requests exist. The equivalent scientific stages need a project workflow convention. |
| Park one item and advance other eligible work | Megalaunch supplies the sweep, human-role gates and dependency drain. | A new two-invocation test with a 35-line operator discovered a research-premise conflict, parked it, completed independent work and resumed from revised files. This is our integration, not a supplied CE queue. | The CLI exposes session dispatch, artifact transfer and a distinct pending-question return. An explicit research dispatcher can compose these; that whole sweep was not run live. |
| Change the research question without rewriting old evidence | Editable tasks/context plus a new experiment identity in the domain method. | Can revise the plan and retain prior evidence. Plan explicitly surfaces invalidated settled decisions to its caller. | Can commit revised project files through a change request and start subsequent sessions from them. |
| Accept shared knowledge under human control | Dream proposes substantive changes for human merge. | Compound writes learned documents; review isolation and acceptance conventions must be supplied around it. | Memory changes use change requests. Agent merge permissions and self-merge checks support a human-controlled acceptance policy. |
| Run on existing research hardware | Invokes the existing local runner. | Can use the same local runner through the current agent host. | The experimental computer tunnel can invoke the runner on a paired machine. The default session runtime is a cloud sandbox. |

Coga's runtime findings are detailed in the
[implementation comparison](human-centered-comparison.md#what-coga-actually-does-after-delegation).
The competitor mechanisms and their limits are grounded below.

## CE: a credible substitute that would need the programme layer

CE's current non-software brainstorming method is explicitly a thinking
partnership. Its planning and POV methods preserve decisions and uncertainty;
pipeline planning must return `settled-decision-invalidated` when evidence
undermines an earlier decision. Bake-off develops independent alternatives
and obtains an independent assessment, while leaving adoption with the
caller. These are supplied behaviors, not hypothetical extensions.
[Universal brainstorming](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-brainstorm/references/universal-brainstorming.md),
[planning](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-plan/SKILL.md),
[POV](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-pov/references/method.md),
[Bake-off](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-bakeoff/SKILL.md).

Optimize is an especially relevant counterexample. It freezes a spec once
derived work exists, requires explicit approval before experiments, records
results on disk, and has stopping criteria. Its objective is improving a
measured target. A confirmatory research experiment must instead preserve its
registered protocol, including results that do not improve the metric. Use
the research project's runner for that work. One concrete default difference:
Optimize's log deliberately does not record approval, so a fresh resume
without witnessed approval asks again. A reusable authorization bound to
specific experimental inputs would need an explicit integration.
[Optimize procedure](https://github.com/EveryInc/compound-engineering-plugin/blob/082c83e0537c803ac1d927daafc2e6eb6962dedf/skills/ce-optimize/SKILL.md).

A concrete CE replacement would keep the research files and runner, use
plans for bounded investigations, call an independent audit at the relevant
stages, and record human decisions and eligibility in a maintained queue.
The next task is authored after the decision; later speculative tasks stay
ineligible. Shared corrections would be proposed in a separate branch and
accepted before ordinary tasks retrieve them. This is feasible integration,
not a stock CE programme demonstrated here.

The [earlier live adoption trial](adoption-trial.md) is useful evidence:
unmodified CE plus a 26-line operator instruction file ran code and non-code
work, held a declared human gate, and restarted from an edited plan. It also
proposed and previewed a knowledge correction. Actual human merge and reuse
after that merge remain pending. That trial did not test a newly discovered
scientific blocker or a changed research premise.

The [September 16 research trial](research-replacement-trial.md) now tests
those two conditions with invented data. CE plus a 35-line operator
identified an unexpected confound, preserved the owner's decision and
finished unrelated work. After a staged fixture-owner revision, a fresh
session produced the newly requested protocol while preserving the earlier
evidence. This establishes that the tested coordination is portable with a
small instruction layer. It does not establish a scientifically approved
protocol, a full programme replacement, or comparative reliability.

**Switch judgment:** CE can replace much of the method and offers useful
reasoning procedures. It has not shown a better way to operate this standing
programme than Coga's existing task lifecycle and sweep. Removing Coga would
trade its maintained runtime for our own coordination conventions. Those
conventions can be AI-authored; their existence alone does not establish
extra human effort. CE skills are also candidates for use within Coga, so
adopting useful methods need not require replacing the coordinator.

## Kortix: the closest platform alternative

Kortix's Deep Research skill keeps a plan, source index, notes and report on
disk and resumes prior research. Its supplied procedure mainly gathers and
synthesizes source evidence; it does not supply the project's experimental
protocol. That protocol can remain in project files and an added research
skill, just as it does in a Coga project.
[Deep Research](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/marketplace/.kortix/opencode/skills/deep-research/SKILL.md).

The human review overlap is stronger than a comparison of slogans suggests.
Memory is ordinary Markdown in the project branch. Shared changes reach
the base through a change request. The merge route checks human-side merge
capability, calls the agent-scope check, and refuses the originating session's
self-merge. The refinement instructions allow a human or an authorized
reviewer agent. Thus a human-only knowledge acceptance policy is a supported
configuration choice; it is not a missing capability unique to Coga.
[Memory protocol](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-memory/SKILL.md),
[actual merge route](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/projects/routes/r9.ts#L42),
[refinement policy](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-harness-refinement/SKILL.md).

A concrete replacement would retain the research corpus, introduce a
research-stage skill and durable task/decision records, and use separate
sessions for preparation and critique. Human decisions would authorize the
next stage; accepted conclusions would merge through CRs. A coordinator
would need explicit instructions to park unresolved questions and dispatch
other eligible investigations. Triggers can restart work later, and session
queues have retry handling; neither fact alone proves that whole-programme
dispatch policy.
[Scheduling instructions](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-system/references/scheduling.md),
[trigger implementation](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/projects/lib/triggers.ts).

The [concrete replacement design](research-replacement-trial.md#how-i-would-implement-the-same-method-with-kortix)
uses `sessions new`, `wait-for` and `cp`. Inspection of the actual wait
implementation confirms a separate return for pending questions or
permissions. A coordinator can record that blocked item and dispatch another;
it must still inspect artifacts because an idle session is not proof of
successful research. Intermediate working state must remain distinct from
human-accepted knowledge so that every queue update does not require a merge.

Keeping existing research hardware is possible: the experimental computer
connector provides permissioned file and shell access to a paired machine.
That leaves a choice about which checkout owns task state and accepted
knowledge, and how the remote coordinator retrieves local evidence. Moving
the measurements into an ordinary cloud sandbox is a different experimental
environment and requires protocol validation. Self-hosting Kortix's control
plane still includes frontend, API, gateway and Supabase, with agent sessions
on a separate sandbox provider. Managed platform skills are refreshed by
Kortix; project extensions have their own names.
[Computer tunnel](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-computer/SKILL.md),
[self-hosting](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/self-host/README.md),
[managed skill handling](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/runtime-assets/managed-skills.ts).

**Switch judgment:** Kortix is credible when shared remote operation,
permission controls, connectors and a review UI solve an actual problem.
For the current local research programme, no observed benefit justifies
replacing the small coordinator with that platform. This is a fit judgment,
not a measured maintenance-cost comparison or a claim that Kortix needs a
human to operate every session.

## What remains differentiated

Coga makes a standing programme of tasks, human handoffs and reusable
methods directly operable through files and a small local runtime. A useful
research deliverable can be evidence for the owner's next decision. The
runtime can then work elsewhere until that decision is made. That is a
substantive working-method difference from merely managing parallel chats.

The serious competitors can reproduce this relationship. Editable prompts,
human review, knowledge accumulation and handling unknown work are not
exclusive. Coga's case is the supplied combination and how directly it fits
this work, rather than a capability nobody else possesses. A demonstration
should show the person revising the question, the next task changing, and
other work continuing through the handoff. Do not claim that every competitor
makes the person follow the machine's schedule.

## Evidence boundary

This combines source inspection, existing research records, the earlier CE
trial and a subsequent two-invocation CE test on invented research data.
It is not a matched competitor experiment. No Kortix instance was deployed,
no real research experiment was executed, and no comparative attention or
reliability result was measured. The [new trial report](research-replacement-trial.md)
separates observed execution from proposed integration and records current
public traction for both alternatives.

Sources: Coga `ffb0e361ae0ed8b77cbe5eaaea39c7d1e7bc5e1f`;
CE 3.26.3 `082c83e0537c803ac1d927daafc2e6eb6962dedf` for current source,
3.24.0 for the earlier live trial; Kortix
`05c2901f6d510da70500fc5c3ef207bfc233d8cc`. The previous comparison records
18 passing Coga mechanism checks and a prompt-composition gap: some separate
level-two ticket sections require the agent to reread the full ticket.
That limits a claim that every authored section is automatically injected;
it does not establish that the task content is unavailable.
