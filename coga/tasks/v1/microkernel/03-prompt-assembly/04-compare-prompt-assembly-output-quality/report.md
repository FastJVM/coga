# Output-quality comparison: C1′ vs current assembler — report

Status: **runs complete; awaiting the owner's blinded judgments.** Sections 3–5
are filled only after `blind/verdicts.csv` is complete and its hash is
recorded here, and only then are `blind-key.json` and `gates.json` opened.

## 1. What ran

| Item | Planned | Executed |
| --- | --- | --- |
| Paired sessions (4 cases × 2 arms × 2 reps) | 16 | 16, counterbalanced (see ticket blackboard "Frozen inputs"), each pair adjacent |
| Replaced (infrastructure) | — | 1: the first `code__baseline__r1` (F1, fixture left a tracked file untracked) |
| Infrastructure model calls (not trial sessions) | — | 1 no-op `codex exec` sandbox/model check (6,619 tokens) |

- **Agent and pins:** Codex `codex-cli 0.167.2` (exe sha256 `a9672d0f…f56b`),
  `gpt-6.1-sol`, reasoning `medium`. Ticket 02's permission profile, re-rooted
  to `/tmp/coga-quality-trial`. Production pin `abbe9ece3`.
- **Prompts:** frozen under `prompts/` before the first session (`prompts/SHA256SUMS`).
  C1′ is built by `c1prime.py`, which first reproduces ticket 02's C1 byte for byte.

### Invariants checked in every counted session

- **Prompt identity.** Production's prompt equalled the frozen baseline, and
  the delivered prompt equalled the frozen arm prompt apart from the launch
  marker.
- **Isolation.** The live repo's HEAD and status and the trial venv's
  site-packages were unchanged. The effective sandbox was as pinned.
- **Clean ending.** No session hit the 1,800 s limit.
- **Mechanical gates** (`gates.json`, sealed): no flags in any run.
  - Execute cases: exactly one bump to step 2. The code and docs cases also
    recorded and pushed a branch.
  - Authoring: the ticket stayed `draft` with no lifecycle transition, and a
    cold evaluator sub-agent ran in all 4 runs.
  - No merge commits, no CLI-owned frontmatter edits in execute cases, and no
    product files landing on `main`.

## 2. Design notes and limitations (fixed before judging)

- **Unattended conduct prepares no branch.** For code, design and docs,
  production `_launch` runs with megalaunch conduct, and production prepares a
  branch only for attended launches. Each agent therefore ran the manual
  `coga/checkouts` procedure itself, identically in both arms. The owner
  confirmed this conduct on 2026-11-14.
- **The measured step stops there.** The supervisor stopped after it because
  the peer CLI is deliberately absent. Agents noticed this, and some mention
  it in their output, in both arms.
- **Authoring used a fixed dialogue** (`dialogues.json`). Controller latency
  differed once: in author baseline r1 a Codex question form expired before
  the reply, so the same fixed line was sent as a plain-text turn. From
  author baseline r2 on, `autoanswer.sh` answered forms within seconds.
- **The fixture is one snapshot commit**, with no history and the trial
  packages stripped. The sandbox can still read the whole filesystem, as in
  ticket 02.
- **The sample is small:** one model and two repetitions. This is a pilot.
  Per the ticket, mixed results are recorded as inconclusive.

## 3. Owner's blinded judgments

_To fill after verdicts:_ the `verdicts.csv` sha256, then the per-pair
winners mapped to arms, ties, and the reasons.

## 4. Secondary (reported only)

_After unblinding: wall time, tokens, and correction needed, per arm, from `gates.json` and the verdict sheet._

## 5. Owner decision

_Positive selection / negative / inconclusive._ Only a positive selection
makes `03-implement-the-proven-prompt-assembly` eligible.
