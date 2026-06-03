The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: autobimp-smoke
worktree: /home/n/Code/relay-autobimp-smoke
pr: (pending — opened in the `pr` step)

## Implement step (done)

Added `tests/test_autobimp_smoke.py` — three deterministic `slugify`
assertions not already covered by `test_primitives.py`:
- empty string → `"task"` fallback
- separator-run collapsing (`"Hello,   World!!!"` → `"hello-world"`)
- surrounding-whitespace trimming

No source change. Chose `slugify` because it's a pure, env-independent
function — nothing timing/CI-flaky to muddy the relaunch signal.
Verified in the worktree: new test 3 passed; full suite 517 passed,
1 skipped. Committed on `autobimp-smoke` (56140e6), worktree clean.
No push / no PR yet — that's the `pr` step. Bumping → `self-qa`.

## Self-QA step (done)

Ran `/code-review` and `/simplify` against `autobimp-smoke` vs `main`.
**No actionable findings; no edits, no new commit.**

- `/code-review`: verified all three assertions against `src/relay/slugify.py`.
  All correct (`""`→`task`; `"Hello,   World!!!"`→`hello-world`;
  whitespace trimmed). No correctness/reuse/simplification/efficiency/altitude
  findings on the 23-line test.
- `/simplify`: one minor reuse overlap noted — `test_primitives.py`
  already exercises the `or "task"` fallback via `slugify("!!!")`, and the
  new `test_slugify_empty_string_falls_back_to_task` re-hits it via `""`.
  **Skipped:** `""` vs `"!!!"` are distinct boundary inputs sharing the
  fallback line; trimming adds no value for an intentionally self-contained
  smoke artifact, and the human reviewer is one step away. The other two
  assertions are genuinely uncovered.

Env note: this shell's default `python` is miniconda 3.9 without the
editable `relay` install — `pytest` there fails at collection
(`ModuleNotFoundError: No module named 'relay'`). Use the project venv:
`/home/n/Code/relay/.venv/bin/python -m pytest`. Re-ran the full suite in
the worktree that way: **517 passed, 1 skipped** (matches implement step).
Working tree clean. Bumping → `pr`.

## Bootstrap notes

Synthetic test ticket. Purpose: confirm `relay launch`'s auto-relaunch
supervisor chains through the `dev/with-self-review` workflow.

Setup decisions:
- **Workflow:** `dev/with-self-review` (human's choice) — first three steps
  are agent (`claude`) steps, so it auto-relaunches twice then stops at the
  human `review` gate.
- **`implement` task:** add one small, self-contained *passing* test under
  `tests/` so the chain has a real diff. No source change. Pick a stable
  assertion (not timing/env-dependent) so CI doesn't flake and muddy the
  relaunch signal.
- **assignee:** set to `claude` (not the seeded `nick`). `relay launch` uses
  the ticket-level `assignee` for the first step, and step `assignee: agent`
  resolves via the ticket's `agent:` field.
- **contexts:** `dev/code` only — the load-bearing fact (record branch/PR
  under `## Dev`) is also paraphrased in `## Context`.

Expected boundaries (the prediction under test):
- `implement → self-qa` (claude → claude): auto-relaunch
- `self-qa → pr` (claude → claude): auto-relaunch
- `pr → review` (claude → owner): stop at human gate

A stop where auto-relaunch was expected is the finding — note it here.

## Evaluator review

## Evaluation: test-autobimp ticket

**Clarity for a cold-start agent: Good.** The Description plainly states what the first agent step must do — add one small, self-contained, passing test under `tests/`, no source change, keep it green. An agent picking up the `implement` step would know exactly what to produce. The success criterion ("a real diff to carry through self-QA and PR") is unambiguous.

**Workflow fit (dev/with-self-review): Correct, and deliberately so.** The whole point of this ticket is to exercise the auto-relaunch chain across three consecutive agent steps (`implement → self-qa → pr`) terminating at a human gate (`review`). That is exactly the shape `dev/with-self-review` provides: three `assignee: agent` steps followed by one `assignee: owner` step. The ticket's predicted boundaries (auto-relaunch twice, stop once) match the workflow frontmatter precisely. No mismatch.

**Contexts (dev/code): Relevant and sufficient.** The workflow produces a branch and PR, so `dev/code` is the right attachment, and the ticket correctly instructs recording branch/PR under a `## Dev` blackboard section per that context. Nothing important is missing for a test of this scope. `skills: []` is fine — skills come from the workflow steps (`code/implement`, `code/self-qa`, `code/open-pr`).

**Context over-breadth: Minor, acceptable.** `dev/code` is a fairly broad conventions doc (checkout boundary, worktree discipline, multi-ticket PRs, frontmatter-vs-blackboard rationale). The one fact the agent actually needs — "write `branch:`/`worktree:`/`pr:` under `## Dev`" — is the canonical block, and the ticket already paraphrases it inline ("Record the branch and PR under a `## Dev` section"). So the load-bearing fact is effectively copied into `## Context`; the rest of `dev/code` is reference. For a real ticket I might flag the broadness, but for a test it's fine.

**Scope: Appropriately tiny.** One trivial passing test, no source change. This is well under one ticket's worth of work — correct for a supervisor smoke test. It does not bundle anything.

**Assumptions worth questioning before launch:**
- *"Both agent→agent transitions auto-relaunch."* This is the hypothesis under test, not a guarantee — which the ticket correctly frames (a stop where relaunch was expected is "the finding"). Good: it's falsifiable and the failure mode is documented.
- *Worktree/checkout discipline vs. a throwaff test.* `dev/code` pushes feature work into a separate worktree outside the primary checkout. For a real PR that matters; for a throwaway test it adds ceremony. Not wrong, just heavier than the task needs — the agent should not get stuck if worktree setup is fiddly.
- *"Keep it green so the PR is mergeable."* Adding a test that asserts "trivial existing behavior" is safe, but the agent should pick something genuinely stable (not timing/environment-dependent) so CI doesn't flake and muddy the relaunch signal.
- *Mode is `interactive`* — reasonable for a supervised test where a human is watching the relaunch behavior, but worth confirming that's intended rather than `autonomous`, since the test is fundamentally about unattended chaining.

Bottom line: well-formed test ticket. Workflow and context choices are correct for its stated purpose, scope is right-sized, and the prediction it's testing is clearly stated and falsifiable.
