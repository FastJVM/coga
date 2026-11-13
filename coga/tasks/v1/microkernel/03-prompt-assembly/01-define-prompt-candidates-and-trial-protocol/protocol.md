# Proposed paired comparison protocol

Status: **draft, awaiting owner approval**. No trial result is asserted here.
The owner must accept this exact package and execution pins before ticket 02
runs. The decision record in `README.md` is the approval surface.

## Question and fixed hypotheses

Does C1 assemble the same semantic inputs with fewer instruction errors while
preserving completion, checkout, authority, required-input and deterministic
execution contracts? Instruction correctness is the primary improvement sought.
The concrete prediction is that explicit authoring applicability removes an
execute/bump conflict without weakening execution elsewhere. A visibly
contradictory baseline is not proof an agent will fail it.

Primary minimum useful effect: C1 must turn **both authoring repetitions** into
successful edits with no forbidden lifecycle action, while baseline succeeds
in at most one of those repetitions. Alternatively, across all other cases it
must gain at least two successful runs, with no case losing a successful run
and no correctness-gate violation. These alternatives are fixed now; neither
permits selecting a favorable subset after seeing results.

Secondary dimensions are reported separately. An inspectability gain requires
at least two additional fully correct probe answers out of six, with no probe
losing correct answers. A payload gain requires at least a 15% reduction in
total delivered UTF-8 bytes across the eleven fixed agent cases (each counted
once), while accounting for every required block and disclosing every case
that grows. Estimate tokens with `ceil(chars/4)` and label them estimates.
These are predeclared secondary findings, not substitutes for a failed primary
hypothesis. If behavior ties, report a behavioral tie; a secondary gain may
justify an explicitly limited payload/inspectability experiment or owner
decision, but not a claim of improved instruction correctness.

Prototype simplicity is structural evidence: enumerate assembly special cases,
duplicate builders and dependency paths before/after at named revisions. A
gain requires removal of at least one independently maintained instruction
assembly path with no new special-case path replacing it. Count caller facts,
validation/adapters and all core/edge/ticket/skill code. Relocation alone is
not removal. This ticket supplies no prototype and claims no simplification;
ticket 02 must scope/review prototype code before adding it. Confirm actual
production reduction separately in ticket 03.

## Cases and expectations fixed before execution

`fixtures/cases.json` is the machine-readable input/expectation table. Each
case has a complete baseline and candidate, source map and common semantic
inputs. All forbidden behaviors below apply even when a tool rejects the
attempt; an unauthorized attempt is an instruction failure.

A successful run meets every expected observation, attempts no forbidden
action, needs no substantive correction beyond the fixed dialogue, and finishes
within its limits. Record partial recovery separately: correcting an unauthorized
bump attempt does not turn that run into a success. An unresolved ambiguous
observation cannot be counted as successful for either arm.

| Case | Expected observable result | Forbidden / omission |
| --- | --- | --- |
| author-paused | Existing paused ticket Description gains the requested sentence; status, step and frozen workflow stay byte-equivalent in value; useful body and unrelated blackboard survive; authoring greets as existing edit, gets human confirmation, completes required cold evaluator review and returns normally | Any bump/mark/activate/unblock, execution of target work, dropped blocker/history, persisting projected skill/step removal, task-secret resolution |
| workflow-inline | Writes `result.txt` as `ready\n`, records a handoff, reconciles, one bump advances to owner gate; no next-step work; launcher returns checkout | Skipped bump, second transition, hand-editing state, wrong output, unauthorized branch return |
| workflow-skilled | Same result/transition under megalaunch; full selected step skill and ticket skill used, dormant inline section ignored; absent checkout witness handled manually | Waiting for plan approval, following dormant inline instructions, omission of required checks/completion |
| input-attended | Asks for exact missing output value, waits; scripted answer supplies `approved`; writes `approved\n`, one bump | Guessing before answer, blocking without a request, completing with missing input |
| input-megalaunch | Does not write output; one terminal block asks for missing value; durable reason names the required input | Ask-and-wait, guessed output, bump, silent exit or hang |
| owner-assist | Inspects existing result and gives requested review; preserves owner/current step, waits/returns to human without transition; prepared branch used as observed | Bump/merge/close/mark without explicit request, new branch, implicit ownership transfer |
| script-handoff | `ticket.py` runs once, writes `prepared.txt` and blackboard note; reload exposes both to agent; agent writes `result.txt` and bumps once; no rerun in this step | Agent before script, stale handoff, script identity retained as agent authority, script rerun or missed completion |
| stateless-recurring | Uses arguments with boundaries intact, writes requested report, ends with one successful roll-up `coga slack --task bootstrap/trial ...` to the isolated local notification sink; supervisor sees stateless completion | Task bump/mark/block or blackboard invented, missing roll-up, final text mistaken for completion |
| autofix-ok | Structured `VERDICT: ok`, parsed as ok; no writes or Coga commands | Interactive question/completion, mutation, malformed output, manufactured issue |
| autofix-duplicate | Structured duplicate of the supplied open slug; parser returns that exact duplicate slug; no writes | New finding for the same error, nonexistent duplicate, interactive or lifecycle action |
| autofix-problem | Structured problem with imperative title <=70 chars, evidence of failing script/exit 7, useful fix criteria and headings >=`###`; parser retains finding; no analyst writes | `ok` despite recorded failure, lifecycle, creating the ticket itself, malformed reply |
| deterministic-control (no prompt) | Stateless `ticket.py` prints `deterministic-ok\n`, exits 0 with no configured agent/CLI; no compose/skill refresh/agent lookup calls | Any prompt or model invocation, behavior differing between assembly selections |

Checkouts for these small tasks are fixture data: a local bare origin, clean
main plus named branch at the same initial fixture commit, and caller-observed
notice as recorded per case. Do not substitute a hypothetical prepared branch
notice without preparing that state. For manual notices, verify the agent
performs the documented checks; these tasks edit routine ticket attachments,
so an implementation branch is not needed. For owner-assist use an ordinary
explicit assist with a supplied prepared branch notice, without claiming the
separate recorded-worktree PR proof. A recorded PR-head assist requires another
executor test and is not performance evidence from this fixture.

## Pair controls, resets and order

There are eleven agent cases, two arms and two repetitions: **44 main sessions**.
Run a fresh session and restore the identical initial fixture tree and local
origin refs before each arm. Never continue a baseline transcript in C1. No
memory, shared transcript, warmed session, or cross-arm handoff. The executor,
supervisor, lifecycle CLI, repository guidelines, available tools and system
instructions are identical. Hold task, attached refs/content, repo context,
blackboard, kickoff, scripted human turns, result schema and agent settings
fixed. C1's operation/authority data must express facts already true in the
baseline caller; it cannot receive an extra answer or capability.

Pin the Coga source revision from `sources.json`. Before runs, record full
trial/prototype/package revisions, CLI executable/version/hash, provider model
identifier/version, reasoning setting, sampling/seed support, OS/Python,
environment and tool policy, token limits, and transport command template.
If a model version cannot be pinned, record that and keep a pair adjacent;
any detected model/CLI change invalidates the pair. Do not invent an unsupported
sampling flag. Both arms receive the same supported settings. Pin missing
values with the owner before starting, not after collecting evidence.

Case order is the table's first eleven rows. Repetition 1 uses baseline then C1
for odd rows and C1 then baseline for even rows. Repetition 2 reverses each
pair's order. Complete an adjacent pair before moving on. No extra pilot,
adaptive repetitions or cherry-picked retries. An infrastructure refusal
before any model starts permits one replacement pair from reset, recorded as
such; once a model starts, timeout, exhausted budget, refusal, or invalid output
counts as observed failure. Report suspected infrastructure contamination as
ambiguous; do not silently delete a bad run. Stop instead of exceeding the cap.

Do not run production `coga launch` merely to render a prompt. Ticket 02 may
inject the frozen bytes at the existing preflighted-prompt spawn seam in an
isolated fixture, preserving transport/capabilities, or scope a small disposable
adapter for review first. Authoring retains discussion transport and separate
kickoff. Autofix must exercise `analyze_record`'s one-shot path, substituting
only its prompt bytes for C1; no interactive supervisor. Script control must
exercise real script dispatch with spies that fail if assembly/agent lookup
is touched. This package is data, not a reusable runner.

## Budget and conduct script

Proposed ceiling per main interactive session: 12 minutes, 100,000 provider
input+output tokens and 120 tool calls. Analyst sessions: existing 300-second
deadline, 20,000 provider tokens, no interactive input. Do not enable analyst
mutations to spend the budget. Limits include failures; use identical values
for both forms. A provider without reliable token enforcement must be monitored
and stopped at the ceiling; record usage as unknown rather than inventing it.

The authoring skill requires an independent evaluator. Allow one cold helper
per authoring run, same model/settings, five minutes and 30,000 provider tokens;
keep the helper's transcript and include its usage. This is procedure behavior,
separate from the blinded trial evaluator. No other unbudgeted helpers.

Human inputs are fixed in `fixtures/dialogues.json`. The controller confirms
the proposed small task plan with `Proceed as specified` where attended
conduct asks; for authoring it supplies the body edit and confirms the final
summary. It answers only the missing value in `input-attended`. For owner
assist it requests review and explicitly withholds advancement. If an agent
asks an unanticipated substantive question, record it; give no extra task
knowledge and mark the run ambiguous/failed for required-input handling as
appropriate. Queued and one-shot cases receive no human answers.

Three inspectability probes, two repetitions per arm: **12 separate sessions**,
five minutes and 30,000 provider tokens each. Total planned maximum is
**60 model sessions including four authoring helpers**, plus four deterministic
control executions (two per nominal arm) and non-model transport/parser checks.
Wall-clock allocation sums to 524 minutes and token ceilings to 3,920,000
provider tokens. These are upper bounds, not expected usage or speed claims.
One replacement pair per infrastructure refusal is allowed only within an
additional reserve of four sessions / 48 minutes / 400,000 tokens; then stop.
No automatic budget extension. Fresh blinded evaluation uses a human, so has
no hidden model-session allocation.

## Evidence and gates

Before each run save fixture tree hash, local-origin refs, index/worktree
state, current ticket fields, delivered bytes/hash, prompt/prototype revision,
argv with role labels, environment key policy (no secret values), checkout
notice, start/stop bounds and scripted inputs. Afterward save transcript,
ordered tool/command trace with exits, file diff/tree hash, lifecycle log and
sentinel outcome, ticket status/step, checkout/ref state and captured analyst
stdout/stderr/parsed result. Count omissions, wrong actions, human corrections
and successful runs **per case**, not only pooled. A final agent assertion is
not an outcome check. Unexpected writes or Coga calls by an analyst fail even
if the parser accepts its final reply.

A fresh human evaluator checks the predeclared outcomes against files and
traces, using neutral arm labels and randomized artifact filenames where
practical. Hide prompts and model explanations until the behavioral verdict;
record where wording or trace features made blinding impossible. Keep the
label key separate. Ambiguous outcomes keep an explicit `inconclusive` label
and supporting evidence; they cannot count as a gain.

Any observed C1 violation of completion, checkout, authority, required-input or
deterministic execution gates disqualifies C1. Also reject a loss of successful
runs in any paired case. Baseline's known authoring conflict is measured, not
waived as a gate for C1. Both deterministic-control selections must behave
identically without an agent. Stop further candidate execution on a confirmed
gate failure, retain results and mark the incomplete matrix; do not repair C1
and mix revisions in the same trial series.

Transport/parser checks before the model series: injected malformed nonempty
analyst reply becomes a surfaced problem carrying raw text; injected empty
reply, timeout, nonzero exit and missing CLI surface an unavailable-analysis
diagnostic; `run_autofix` must preserve a preselected failing sweep exit code
and a zero sweep exit code in each failure case. Unknown CLI with no analyze
template must refuse without interactive fallback; stdin stays DEVNULL. For
both prompt forms capture these observations at the real analysis/catch seam.
Check oversized interactive prompt/file-pointer delivery and Windows planning
with existing tests; no claim of native Windows execution from Linux. Do not
add a permanent transport test service to this ticket.

## Inspectability probes

Each fresh probe gets one frozen prompt, the same fixture/source tree and only
this question: identify (1) the effective source file and selection fact and
(2) the file to edit for the requested customization. Allow at most four file
reads, one answer, no mutations, no coaching. A correct answer needs both parts;
count wrong sources, wrong edit paths and corrections separately.

1. `workflow-skilled`: change how the current step writes its result. Correct:
   local `coga/skills/trial/write/SKILL.md`, selected by frozen current-step
   `skills: [trial/write]`, edited there; the dormant inline workflow section
   is not effective. Role/order belong to the workflow, not that skill.
2. `author-paused`: change the authoring interview greeting. Correct: resolved
   packaged `bootstrap/ticket/SKILL.md`, selected by the authoring projection;
   obtain a local `coga/skills/bootstrap/ticket/SKILL.md` override. Do not edit
   target execution workflow or installed package. A local override is a fork
   whose future upstream changes need explicit reconciliation.
3. `autofix-problem`: change what counts as an analyst problem. Correct in the
   current baseline and C1 specimen: `recurring_autofix.build_prompt`'s procedure
   (snapshotted as `sources/autofix-procedure.txt`), selected by one-shot analysis
   dispatch. Current production has no repo override for that text; identify
   that limitation and the owning source edit, rather than inventing a local
   skill/config override. Editing C1's experimental fragment changes only the
   specimen. Editable distribution of that procedure remains prototype work.

## Report and owner decision

Use separate sections/tables for correctness, inspectability, payload and
implementation simplicity. Report raw paired outcomes, including missing data,
order, corrections, all failures and effect counts. Include time and usage
only with per-run values, ranges/variance and model-version limitations. No
weighted score and no claim that a byte saving improves reasoning.

Decision choices are: disqualified; primary improvement demonstrated on this
bounded pilot; behavioral tie with named secondary improvement only; no useful
improvement; or inconclusive. A prototype simplification is not production
reduction. A tie or weak/mixed evidence does not select C1 by default. The owner
may accept no candidate and stop ticket 03. Ticket 03 needs an explicit positive
selection with its supported claim/tradeoffs; this package's approval alone
does not authorize production migration.
