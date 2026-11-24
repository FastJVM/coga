---
name: coga-dev/testing/agent-trials
description: How to run a paired, blinded agent-behavior trial of a Coga prompt or composition change — predeclaration, frozen arms, fixture isolation, Codex pins, counterbalanced runs, blinding, scale, harness pitfalls, and evidence handling — learned from the 2026-11 prompt-assembly pilots.
---

# Agent-behavior trials

Use a paired trial when a prompt or composition change claims agents behave or
write better; unit tests and payload size cannot show that. Two bounded pilots
(2026-11, prompt assembly: rule compliance, then output quality) settled the
method. Their rulings live in
[coga/prompt-composition](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md#assembler-ruling).
The general test tiers are in [testing](../SKILL.md).

- **Predeclare before any model session**, with owner approval: cases with
  expected observable outcomes and forbidden actions (checked against fixture
  files, git/ticket state and command traces, never the agent's claim), hard
  gates (completion, checkout, authority, required input, deterministic
  execution), the primary measure and its minimum effect, repetitions, order,
  budget and stop rules. Report each dimension separately, with no weighted
  score. A payload saving is not a reasoning gain. Mixed or small-n results are
  `inconclusive`, never a default win. Change no criterion after seeing
  results, and never mix candidate revisions within one series.
- **Freeze both arms.** Render the baseline through the real path
  (`compose_prompt_report`, or capture at `spawn_agent_session`), build the
  candidate mechanically from it (first check that the builder reproduces any
  prior candidate byte for byte), and hash both. At run time, abort if
  production's prompt drifted from the frozen baseline, then inject the arm via
  `spawn_agent_session(composed_prompt=...)`. Never run a nested `coga launch`.
  Autofix goes through `analyze_record` with only its prompt bytes substituted.
  A `ticket.py` control runs real dispatch with spies that fail on composition.
- **Isolate.** Fixture = `git archive <pin>` under `/tmp` with a local bare
  origin and the trial's own task files stripped. Force-add the pin's exact
  tracked set and assert equality: `git add -A` drops tracked-but-ignored files
  such as `src/coga/resources/templates/coga/skills/_template/SKILL.md`, and
  packaging tests then fail on the fixture's unchanged `main`. Use a
  non-editable venv at the pin and hash its site-packages before and after each
  run. Put `user` in the fixture's `coga.local.toml` (shared config rejects
  it). Run both the harness and the agent under an environment allowlist (an
  ambient `SLACK_WEBHOOK_URL` broke config load). Turn notifications and
  telemetry off.
- **Codex pins.** Pass `-m` and `-c model_reasoning_effort` explicitly (the
  local config default differs). There is no seed flag. Pre-trust the fixture
  path. Grant fixture `.git` writes with a permission profile, because
  `workspace-write` makes `.git` read-only and every bump fails. Set
  `/etc/codex/requirements.toml` aside and restore it afterwards: it overrides
  `-c` pins (see
  [coga/sandboxes](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md)).
  Verify `turn_context.sandbox_policy` per run and keep only rollouts whose cwd
  is the fixture. Whole-filesystem reads stay possible, so record live-repo
  listings and check that no trial task file was opened. Token ceilings are
  unenforceable (the turn-one baseline is about 22–46k tokens and is re-billed
  per tool call), so bind on wall clock and record tokens.
- **Run.** Use a fresh session and a reset fixture per arm. Counterbalance:
  alternate the arm order per case and reverse it in repetition 2, keeping
  pairs adjacent. An infrastructure refusal before the model starts may use
  one replacement from a fixed reserve, kept under `runs/_replaced/`; once the
  model starts, any failure counts. The controller sends only fixed dialogue
  lines, records unanticipated questions without answering them, and answers
  Codex question forms within seconds (they expire). Per-run invariants:
  delivered prompt equals the frozen arm apart from the launch marker; live
  repo HEAD and status unchanged; sandbox as pinned; no limit hit.
- **Blind.** Build a pack with neutral X/Y labels and random pair ids, and seal
  the key and the arm-labeled gate/controller files. Hash the verdict sheet
  before unblinding. Show judges full artifacts uniformly; abridged chat
  excerpts weakened the 2026-11 quality verdicts.
- **Scale and cost.** 11 cases × 2 arms × 2 repetitions (44 sessions plus 12
  probes) and 4 × 2 × 2 (16 sessions, 8 pairs) were enough to show a gate
  failure or a tie, not a reliability claim; one run in two decided the gate.
  Code-change cases ran about 14 minutes and roughly 1–4 M tokens each.
- **Harness pitfalls.** Restore every monkeypatched function (an unrestored
  `subprocess.run` spy recorded the wrong call). Do not pass a frozen prompt as
  `developer_instructions` to an inspectability probe: its output contract
  overrides the question.
- **Evidence.** Each trial produced about 35–40 MB. Codex rollouts carry
  account/user IDs and encrypted reasoning. Decide with the owner what
  may be committed or shared before the first run. The harness is disposable and lives beside its ticket, never
  in `src/coga/`. Reuse the reference harness from its commit permalinks:
  the rule-compliance
  [protocol](https://github.com/FastJVM/coga/blob/7a40b520f248e715fb78c03e9124e48d11b5e098/coga/tasks/v1/microkernel/03-prompt-assembly/01-define-prompt-candidates-and-trial-protocol/protocol.md),
  its [adapter](https://github.com/FastJVM/coga/blob/7a40b520f248e715fb78c03e9124e48d11b5e098/coga/tasks/v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly/adapter.py)
  and [blind-pack builder](https://github.com/FastJVM/coga/blob/7a40b520f248e715fb78c03e9124e48d11b5e098/coga/tasks/v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly/blind.py),
  and the output-quality
  [adapter](https://github.com/FastJVM/coga/blob/7a40b520f248e715fb78c03e9124e48d11b5e098/coga/tasks/v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality/adapter.py)
  with its [controller scripts](https://github.com/FastJVM/coga/blob/7a40b520f248e715fb78c03e9124e48d11b5e098/coga/tasks/v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality/ctl.sh).
