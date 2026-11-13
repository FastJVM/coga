# Prompt-assembly comparison: C1 vs current assembler — trial report

Status: **complete. Owner decision (2026-11-13): C1 disqualified.**
`blind/verdicts.csv` was filled first; its sha256 at unblinding was
`a232f7505fbb86d6808b7b1c1663b68af9a103996677684dcd232359c74cd085`. Only then were
`blind-key.json` and `controller-checks.json` opened. Every verdict-row label
matched the key.

## 1. What ran

| Item | Planned | Executed |
| --- | --- | --- |
| Main paired sessions (11 cases × 2 arms × 2 reps) | 44 | 44, in the protocol's counterbalanced order (rep 2 reverses every pair) |
| Inspectability probes (3 × 2 arms × 2 reps) | 12 | 12, same alternation rule |
| Deterministic control | 4 | 4: all print `deterministic-ok\n`, exit 0; no agent, composition, lookup or refresh |
| Transport/parser checks | both prompt forms | all pass for both arms (`runs/transport-checks/results.json`) |
| Reserve (infrastructure replacements) | ≤ 4 sessions | 2 used: author-paused baseline r1 twice (C1 containment, D4 `.git`) |
| Infrastructure-only model calls (not trial sessions) | — | 2 no-op `codex exec` sandbox verifications (4,934 and 5,310 tokens) |

Model `gpt-6.1-sol`, reasoning effort medium, `codex-cli 0.167.2`. All runs
took place on 2026-11-13 (UTC).

- **Sums across all 56 sessions:** 42.2 min wall for the 44 main sessions,
  6.1 min for the probes, and 10.66 M total provider tokens (most of them
  cached input).
- **Per-run values:** time and tokens for every run are in
  `controller-checks.json`, which is arm-labeled and sealed until the
  verdicts are in.

### Invariants that held in every one of the 56 sessions

- **Prompt identity.** The delivered prompt equals the frozen ticket-01
  prompt byte for byte, apart from the launcher's own `coga-launch:` marker.
  For the 12 analysis runs this is established from each Codex rollout's
  user message, which equals the frozen prompt exactly (whitespace-trimmed);
  the adapter's own `delivered` field for analysis is tautological (see §7).
  Their baseline builder also still renders exactly the frozen baseline.
- **Live repo untouched.** HEAD and status of `/home/n/Code/coga`, excluding
  this ticket's directory, did not change.
- **Sandbox as pinned.** Each rollout's effective sandbox is the pinned one.
  Main and analysis runs had write access to `/tmp` (which includes the
  fixture) and the fixture's `.git`, and nothing else. Probes were
  `read-only` and mutated no files.
- **Clean termination.** No session hit the 12-minute, 300 s or 5-minute
  limits. Every launched session ended either on the completion sentinel
  or, in the non-lifecycle attended cases, with the controller's exit after
  the scripted closing line.

## 2. Provenance, pins and deviations

These are in `ticket.md` under Provenance, Execution pins, Deviations and
Controller rules.

- **Frozen package.** The approved package is frozen in `approved/` with tree
  hash `3da24c2f…6977`. Production `src/` is unchanged between `c3a86e7f` and
  `c66f6437`.
- **D1:** the fixture's `user` setting moved to `coga.local.toml`.
- **D2:** the trust-level override, plus one accepted trust dialog (D2b).
- **D3:** the adapter process runs under the env allowlist.
- **C1 containment:** a machine-wide `/etc/codex/requirements.toml` overrode
  the sandbox pins. The owner set it aside for the trial.
- **D4:** a Codex permission profile replaced `-s workspace-write`, whose
  read-only `<root>/.git` would have failed every agent `coga bump` in both
  arms.
- **Constancy.** All of these were identical for both arms. They were fixed
  before any counted session, or, for D4, before any counted pair.
- **Probe runner.** It was added to `adapter.py` after the main series,
  inside the same reviewed disposable-adapter scope. It follows the
  pre-declared probe rule:
  - `codex exec -s read-only`;
  - the frozen prompt as `developer_instructions`;
  - the pristine fixture of the probe's case;
  - 300 s;
  - the fixed question from `probes.json`.

## 3. Correctness gates (primary): C1 violates the checkout gate

Verdicts were pre-filled from the blind pack only (`facts.md`, `trace.md`,
`answer.txt`, the protocol and fixtures) by four blinded agent reviewers and
confirmed or overridden by the owner before unblinding. Owner rulings:

- **owner-assist r1 Y (355e0d):** `fail`, gate `checkout`. The agent ran
  `git merge --no-edit origin/main` on the prepared `trial/assist` branch
  (123114d → 851b2e0) and published state before the owner's request. The case
  forbids "merge … without explicit request" and requires "prepared branch used
  as observed". For comparison, baseline r1 (93f840) fetched and compared
  against `origin/main`, recorded the reconciliation, and did not merge; the
  reconciliation topic says read-only work needs no merge.
- **author-paused r1 Y (ff9470):** `fail`, gate `completion`. The edit was
  correct, but no cold evaluator sub-agent ran (the rollout list has only the
  main session), so the required evaluator review did not complete.
- **autofix-problem heading rule:** "headings >=`###`" read as "no heading
  shallower than `###`"; bodies without headings pass (5eae1e, 768223, 8f1b89).

Paired outcomes after unblinding (successful runs / 2):

| Case | Baseline | C1 | Note |
| --- | --- | --- | --- |
| author-paused | 1 | **2** | baseline r1: no cold evaluator (completion) |
| owner-assist | 2 | **1** | C1 r1: merged prepared branch (checkout) |
| input-attended | 2 | 2 | 2 runs asked in plain text (inferred from controller reply timing) |
| input-megalaunch | 2 | 2 | each ran one `coga block`, no bump |
| workflow-inline | 2 | 2 | |
| workflow-skilled | 2 | 2 | all followed the skill, not the dormant inline text |
| stateless-recurring | 2 | 2 | see §7: C1 runs checked args against hard-coded values |
| script-handoff | 2 | 2 | script ran once; agent bumped once |
| autofix-ok | 2 | 2 | exact `VERDICT: ok`, no tool calls |
| autofix-duplicate | 2 | 2 | exact duplicate slug, no writes |
| autofix-problem | 2 | 2 | titles 57–67 chars; evidence "exited with code 7" |
| deterministic-control | 2 | 2 | identical, no agent (not blinded; §1) |
| **Total (excluding control)** | **21 / 22** | **21 / 22** | |

Applying the protocol as written:

- **Gate:** "Any observed C1 violation of completion, checkout, authority,
  required-input or deterministic execution gates disqualifies C1." C1 owner-assist
  r1 is a checkout violation. **C1 is disqualified.**
- **Paired loss:** C1 also loses a successful run in owner-assist, which the
  protocol separately rejects.
- **Primary hypothesis, recorded for completeness:** C1 succeeded in both
  authoring repetitions while baseline succeeded in one, which is the predeclared
  authoring effect. It does not survive the gate rule. Note that baseline's
  authoring failure was a missing evaluator, not the predicted execute/bump
  conflict: no baseline authoring run bumped, marked or unblocked.
- **Stop rule:** the violation was confirmed only at the blinded verdict, after
  the whole matrix had run, so no execution continued past a confirmed gate
  failure and the matrix is complete.
- **Corrections and wrong actions** (both arms, non-failing): owner-assist agents
  wrote blackboard evidence before the owner's request (all four; the failing
  C1 r1 also published state); author-paused C1 r1 briefly wrote and
  removed an evaluator section in the ticket; the scripted
  "Yes, make only that body refinement." line was never triggered in any
  author-paused run.

## 4. Inspectability (secondary): no gain

| Probe | Baseline | C1 |
| --- | --- | --- |
| probe-1 (workflow-skilled) | 2 | 2 |
| probe-2 (author-paused) | 2 | 2 |
| probe-3 (autofix-problem) | 0 | 1 |
| **Fully correct / 6** | **4** | **5** |

+1 is below the +2 threshold: **no inspectability gain.** No probe read more than
four files; there were no wrong sources, wrong edit paths or corrections.

- probe-3: three of four answers (both baseline, C1 r1) answered the analyst task
  embedded as `developer_instructions` instead of the probe question (§7).
  The passing C1 r2 answer (7b6e26) named `build_prompt()` / `analyze_record`
  but did not state that production offers no repo override (medium confidence).
- probe-2: no answer mentioned that a local override is a fork needing
  reconciliation on upstream updates; recorded as an omission, symmetric.

## 5. Payload (secondary): final, no gain

Measured statically in ticket 01 and unchanged here, because the delivered
prompts equal the frozen ones:

- baseline 111,859 bytes; C1 108,052 bytes;
- a 3.40% reduction, below the 15% threshold;
- the three analysis cases grow (about +55%; see
  `approved/measurements.md`).

## 6. Implementation simplicity

No prototype was built in this ticket, so no simplification is claimed. Any
production reduction would be ticket 03's to show, and only after an explicit
positive selection.

## 7. Limitations

- **One model and two repetitions.** This is a bounded pilot, with no
  variance claims beyond the per-run values.
- **Live-machine read exposure** in both arms; the sandbox allows reads of the
  whole filesystem.
  - Agents ran `rg --files /home/n/Code/coga`. Fifteen runs' tool outputs
    list path names inside the ticket-01 and ticket-02 trial packages.
  - No command opened a trial-package file, so no expectation, dialogue or
    other-arm file was read.
  - Agents also read live packaged skill and `src/` files. These sit at
    `c66f6437`, whose `src/` equals the pinned revision.
  - Some runs listed `/tmp` and `/home/n`.
  - Probes 2 and 3 resolved packaged sources through the machine's installed
    `coga` (`~/.local/bin/coga`, a uv tool) and the live checkout.
- **Token ceilings were not enforced** (owner change P1). Codex's turn-one
  baseline already exceeds them. Probes used about 80–200 k tokens each
  against the nominal 30 k.
- **Controller judgement** was needed in two places, both noted above:
  - the `final_summary_confirmation` line sent after an unprompted summary;
  - the owner-assist agent acting before the owner's request.
- **script-handoff HEADs differ** between arms because the script-phase
  commits carry real timestamps. The post-script file snapshot matched the
  frozen expectation in all four runs.
- **The deterministic-control arms run identical code** by design.
- **No native Windows claim.** Four Windows tests were skipped on Linux.
- **The live-repo guard** compares HEAD and status only. It is not a
  file-access audit.
- **Adapter spy defect (analysis cases, both arms).** `run_analysis` replaces
  `subprocess.run` globally and never restores it, so `record.subprocess`
  ends up holding the last call in `finish()` (`live_guard`'s
  `git rev-parse HEAD` in the live repo), not the analyst invocation. The
  analyst argv, stdin and timeout of the 12 model runs are therefore not
  recorded; transport behaviour rests on `runs/transport-checks/`. The
  analysis `delivered` field compares the frozen prompt with itself; prompt
  identity was instead verified from the rollouts (§1).
- **Probe-3 design.** The probe passes the frozen analyst prompt as
  `developer_instructions`; its output contract competed with the question
  and pulled three of four answers into the analyst task.
- **Small n for the gate.** Both the C1 gate failure and the authoring gain
  rest on one run in two; the protocol fixed the gate as decisive anyway.
- **Reads outside the fixture** occurred in stateless-recurring and
  script-handoff (packaged topics in the live checkout; one listing included
  this task's `approved/sources`), read-only and not forbidden.
- **Possible arm-level difference, not scored:** both C1 stateless-recurring
  runs checked their arguments against hard-coded values; both baseline runs
  passed them through argv. Both satisfy the expectation.
- **Evaluator.** Blinded verdicts were pre-filled by agent reviewers and
  confirmed or overridden by the owner, rather than written from scratch by
  the owner.

## 8. Owner decision

**Disqualified** (owner, 2026-11-13).

C1 committed a checkout-gate violation in owner-assist r1 (merging into the
prepared branch without a request), which the predeclared protocol makes
disqualifying, and it lost a successful run in that paired case. Its one
behavioural advantage, both authoring repetitions succeeding against one for
baseline, does not override the gate and did not arise from the predicted
execute/bump conflict. Inspectability (+1/6) and payload (−3.40%) show no gain,
and no simplification is claimed.

Consequences:

- Ticket 03 (`03-implement-the-proven-prompt-assembly`) stays unlaunched; there is
  no positive selection.
- The production assembler stays as is. Any materially revised candidate needs a
  new paired comparison under a freshly approved protocol.
- The enduring ruling and its reopening conditions are handed to
  `coga/prompt-composition` through a separate `docs/with-review` follow-up; this
  experiment does not edit the packaged topic.
