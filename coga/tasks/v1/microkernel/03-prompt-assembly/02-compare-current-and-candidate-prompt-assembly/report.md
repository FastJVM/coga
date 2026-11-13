# Prompt-assembly comparison: C1 vs current assembler — trial report

Status: **trial executed; behavioral verdicts and the decision are pending.**
The fresh blinded evaluation and the owner's decision are still open. This
report records what ran and what can be stated without breaking the blind.
Arm-labeled mechanical observations are in `controller-checks.json` and
`blind-key.json`. Do not open them before every row of `blind/verdicts.csv` is
filled.

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
  Analysis cases check this at the real subprocess seam. Their baseline
  builder also still renders exactly the frozen baseline.
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

## 3. Correctness gates (primary): PENDING the blinded verdict

The evaluation pack is `blind/`. Each item is one run under a shuffled X/Y
pair label in a random folder. An item holds:

- `facts.md`: the predeclared expectation, the mechanical outcome, the diff
  and the controller inputs;
- `trace.md`: the ordered tool calls with their outputs;
- `reveal-after-verdict/`: the agent's prose and the delivered prompt.

The workflow is: fill `blind/verdicts.csv`, then open the key, then complete
this section with per-case paired outcomes, gate violations, wrong actions,
omissions and corrections. Apply the protocol rule as written:

- any C1 gate violation disqualifies C1;
- so does any paired case losing a successful run.

The primary hypothesis needs one of the following:

- C1 succeeds in both authoring repetitions while baseline succeeds in at
  most one;
- or C1 gains at least two successful runs across the other cases, with no
  losses.

Controller observations the evaluator should weigh. These are stated for both
arms where they occurred in both, and they are visible in the traces.

- **owner-assist (both arms, both reps):** the agent inspected the result and
  wrote blackboard evidence on its first turn, before the scripted owner
  request arrived. In one run it also published state. No run advanced the
  step, changed the owner, merged or created a branch. The scripted lines were
  then sent as written.
- **author-paused:** where the agent ended with an unprompted summary rather
  than a confirmation question, the controller still sent the scripted
  `final_summary_confirmation` line. Agents in both arms ran
  `coga launch author-paused --prompt-report` inside their launched authoring
  session. The number of cold-evaluator sub-agent rollouts varies by run;
  the expectation is 1.
- **author-paused (publication):** whether the authoring edit was left
  unstaged or published differs between runs. Judge it against
  `forbidden: persisting authoring projection` and the lifecycle-command
  count.
- **autofix-problem:** body headings and the exact evidence wording
  (`exit 7`) vary by run. Judge them against `shallowest_heading: "###"` and
  `body_evidence`.

## 4. Inspectability (secondary): PENDING the blinded verdict

A probe answer is correct only when both parts are right, as listed in
`approved/protocol.md` § Inspectability probes. Count wrong sources, wrong
edit paths and corrections separately. Record more than four file reads as a
violation, judged from `trace.md`, since one call can read several files.

A gain needs at least two more fully correct answers out of six, with no
probe losing a correct answer.

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

## 8. Owner decision (after verdicts)

The choices are:

- disqualified;
- primary improvement demonstrated on this bounded pilot;
- behavioral tie with a named secondary improvement only;
- no useful improvement;
- inconclusive.

Payload is already settled as no gain, and no simplification is claimed. A
tie or mixed evidence does not select C1, and none of these choices
authorizes ticket 03.
