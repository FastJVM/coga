# Output-quality comparison: C1′ vs current assembler — report

Status: **complete; owner decision: inconclusive (2026-11-15).**
Verdict-sheet hash was recorded before opening the key and gate details.

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

Verdict sheet sealed before unblinding (2026-11-15):
`c2013e9ccee9355793d57acae85151fddc922356bf1c3118ea8a9fa48262316f`.

All eight preferences supplied by the owner in attended chat. Pair 6601ad was a tie with no further reason supplied. Artifacts were presented in chat with varying abridgment; see ticket notes.

| Pair | Case | Verdict | Winning arm | Reason |
| --- | --- | --- | --- | --- |
| 1846ec | code | Y | candidate | The rationale section is important. |
| 283a63 | author | Y | baseline | Text can be very terse; prefer the terser output. |
| 367ff1 | design | X | candidate | More direct writing style. |
| 6601ad | design | tie | tie | No further reason supplied. |
| 732331 | author | Y | candidate | More precise. |
| 7d6512 | docs | X | baseline | More precise. |
| b030d4 | code | X | baseline | Clearer. |
| e2f466 | docs | Y | baseline | Clearer and more precise. |

Baseline wins 4, candidate C1′ wins 3, tie 1. Both arms passed all recorded mechanical gates. Results are mixed: no clear quality advantage for C1′. Judgments were made from chat presentations with varying abridgment, not uniformly from full raw artifacts; this limits the comparison, especially writing-style preferences.

## 4. Secondary (reported only)

| Arm | Runs | Wall time total (s) | Mean (s) | Total tokens incl. cached input | Cached input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 8 | 2821.3 | 352.7 | 13,668,031 | 13,100,032 | 52,033 |
| candidate | 8 | 2841.1 | 355.1 | 11,603,724 | 10,912,384 | 46,412 |

Token totals sum recorded rollouts, including authoring evaluator sub-agents. Cached input is included in total tokens; these are not cost estimates. No correction-needed ratings were supplied. Secondary measures do not determine selection.

## 5. Owner decision

Owner decision (2026-11-15, attended): **inconclusive**. Keep the current prompt assembly. The current baseline won four pairs, candidate C1′ three, with one tie; this does not establish a clear quality improvement. No additional rubric or trial is commissioned. `03-implement-the-proven-prompt-assembly` remains ineligible because there is no positive selection. No production prompt or launcher change follows from this trial.
