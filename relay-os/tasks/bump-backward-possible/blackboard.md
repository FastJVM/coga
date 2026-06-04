The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes

Interview pinned the design (2026-05-29, nick):
- Interface: flag on `relay bump`, primary form `relay bump <id> --to <step>`
  (step = number or name). `--backward` shorthand optional if clean.
- Target: jump to any earlier step by number/name. Forward-skip stays out of scope.
- Who: HUMANS ONLY (revised 2026-05-29 after evaluator flag). Agents still
  panic; rewind is the human's tool to act on that. Enforcement: `--to`
  refuses under `RELAY_SUPERVISED` (i.e. inside a launched agent session).
  Base-prompt agent contract stays as-is; only the "human decides whether to
  rewind" wording points at the new `relay bump --to` mechanism.
- Workflow: code/with-review.
- Contexts: relay/codebase, relay/architecture.

Post-evaluator edits folded into ticket: quoted the full "human decides whether
to rewind" sentence (the thing being changed); pinned src/relay/resources/prompt.md
as the single edit target (other matches are venv/package copies); added the
1-based step-index off-by-one note and the supervised-backward-assignee-flip
caveat for peer-review.

## Evaluator review

The `tests/test_commands.py` bump test references in the ticket are valid and the test patterns exist (including `test_other_agent_resolves_to_the_peer_on_bump`, directly relevant to the assignee re-resolution coverage the ticket asks for).

I have enough to assess. Here is my evaluation.

---

## Evaluation: `bump-backward-possible` ticket

**1. Is the Description clear enough to start cold?**
Yes — strongly so. The Description states the current behavior accurately (`next_step = current_idx + 1`, refuses past last step, hand-edit is the only rewind today — all confirmed in `src/relay/commands/bump.py:87-94`), names the motivating scenario, and gives a concrete "done looks like" with the exact CLI shape (`relay bump <id> --to <step>`). An agent with no prior context could start immediately.

**2. Does `code/with-review` fit?**
Yes. This is a self-contained Python code change (CLI flag + reuse of `advance_step`) plus a prompt/docs edit and tests — exactly the shape `code/with-review` is built for (implement → peer-review → open-pr → review). No mismatch. The ticket even anticipates peer-review as the place to decide the `--backward` shorthand and forward-skip question, which fits the workflow's intent.

**3. Are attached contexts relevant? Anything missing?**
`relay/codebase` and `relay/architecture` are both on-target and necessary — this edits `src/relay/` and turns on workflow/step invariants. Nothing critical is missing. One could argue `relay/principles` (the "why markdown-first / legible correction loop" non-negotiables) is relevant given this changes the panic-vs-rewind contract, but the ticket's `## Context` already carries the operative facts, so it's not required.

**4. Any context broad enough that the fact should've been copied into `## Context`?**
This is handled well — the ticket already inlines the load-bearing specifics (the `advance_step`/`resolve_step_assignee` reuse path, the `other-agent` flip, the `step:`-owned-by-bump invariant) rather than leaning on the agent to rediscover them. Two notes:
- The architecture SKILL.md actually lists assignee role tokens as only `owner | human | agent` (line 35) and **omits `other-agent`** — so an agent relying on the context alone would miss it. The ticket correctly copies the `other-agent` fact into `## Context`, which is exactly the right call. Good.
- The prompt.md quote in the ticket ("Do not go backward... call `relay panic`") is accurate (prompt.md:70-71), but the ticket truncates the real second sentence: **"The human decides whether to rewind."** Since the whole point is to let agents rewind too, that exact sentence is the one most needing revision and should have been quoted in full. Minor, but worth flagging to the implementer.

**5. Is the scope reasonable?**
Reasonable and well-bounded — single capability (backward `--to`), with an explicit `## Out of scope` (forward-skipping, history rewriting) and a "decide during implement/peer-review, don't over-build" note on the `--backward` shorthand. It is one ticket's worth of work, not several. The prompt-contract change is intrinsic to the feature (agents must be told this is now sanctioned), not a separate ticket.

**6. Assumptions to question before launch:**
- **Sole `prompt.md` location.** The ticket says "if a packaged/relay-os copy exists, keep them in sync." There is effectively **one** real source: `src/relay/resources/prompt.md`. The many other hits (`.relay/.venv/...`, `templates/relay-os/.relay/...`) are installed-package and venv copies, not separately-maintained sources — the implementer should not hand-edit those. Worth making explicit so the agent doesn't chase phantom duplicates.
- **`relay bump` reads current step via `step_index()` and only acts when `status == in_progress`** (bump.py:57, 87). A backward `--to` must respect the same `in_progress` gate; the ticket says "respect existing invariants" but doesn't call this out by name. Reusing the existing entrypoint flow covers it, but the implementer should confirm the `--to` path doesn't bypass the status check.
- **`step:` format is `"N (name)"`** (bump.py:93). Resolving `--to` by *name* means parsing/matching against `wf["steps"][i]["name"]`; resolving by *number* is 1-based. The ticket implies this but doesn't pin the 1-based indexing — a small off-by-one trap given `step_index()` vs `next_step - 1` arithmetic already in the file.
- **Supervised re-chaining on a backward move.** The ticket says "don't break the supervisor handoff," but a rewind can flip the assignee *backward* (e.g. peer → coder). The existing `emit_done_marker` / `RELAY_SUPERVISED` chain logic (bump.py:136-154) assumes forward motion; the implementer should verify a backward assignee flip chains/stops sanely rather than assuming it's free. This is the most likely place for a latent bug and deserves a peer-review eye.

**Bottom line:** A genuinely strong, launch-ready ticket — accurate codebase pointers (all verified), correct workflow, contexts that compensate for a real gap in the architecture SKILL.md, and a clean scope fence. The only substantive gaps are (a) the truncated "human decides whether to rewind" sentence that is itself the thing being changed, and (b) under-specified handling of the supervised backward-assignee-flip, which should be flagged for the implement/peer-review steps.

## Dev

branch: bump-backward-step
worktree: /home/n/Code/relay-bump-backward-step
commit: bcdbb87 Allow relay bump to rewind workflow steps
pr: https://github.com/FastJVM/relay/pull/251

Implementation decision from interactive session:
- `relay bump <id> --to <step>` resolves numeric 1-based step targets only,
  not names.
- Add a decrement-only shorthand for one step backward. Bare `relay bump <id>`
  remains the normal one-step forward increment.

Implementation notes:
- Added `relay bump <id> --to <step-number>` for human-only rewinds to an
  earlier step.
- Added `relay bump <id> --backward` for a one-step rewind.
- Rewinds refuse under `RELAY_SUPERVISED` and tell agents to use `relay panic`.
- Rewinds reuse the normal bump write/validate/log/Slack path, but log/broadcast
  as `rewound` and resolve the target step's assignee token.
- Updated only `src/relay/resources/prompt.md` for the base prompt contract.

Verification:
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest tests/test_commands.py -q -p no:cacheprovider` -> 52 passed.
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest -q -p no:cacheprovider` -> 478 passed, 1 skipped.
- `PYTHONPATH=/home/n/Code/relay-bump-backward-step/src /home/n/Code/relay/.venv/bin/python -m relay.cli validate --json` from primary checkout -> exit 0 with existing warnings.
- `git diff --check` -> clean.

Note: running validation directly inside the feature worktree failed because its
machine-local `relay-os/relay.local.toml` does not set `user`; I did not edit
local config.

## Peer review

Started Codex peer review from `/home/n/Code/relay-bump-backward-step` on branch
`bump-backward-step` against `main`.

Findings so far:
- Must-fix: `relay bump --backward` crashed with `IndexError` when the current
  `step:` pointed outside the frozen workflow (for example `99 (bogus)`). I
  patched `src/relay/commands/bump.py` to bail clearly before indexing and
  added focused coverage in `tests/test_commands.py`.
- Must-fix: maintained bump guidance still described `relay bump` as
  advance-only. I updated README/design/context wording, including the packaged
  bootstrap context copies where present.

Applied in feature worktree and committed:
- `58bff08 peer-review: guard rewind edge cases`

Verification after peer-review fixes:
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest tests/test_commands.py -q -p no:cacheprovider` -> 53 passed.
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest -q -p no:cacheprovider` -> 479 passed, 1 skipped.
- `PYTHONPATH=/home/n/Code/relay-bump-backward-step/src /home/n/Code/relay/.venv/bin/python -m relay.cli validate --json` from primary checkout -> exit 0 with existing warnings.
- `PYTHONPATH=/home/n/Code/relay-bump-backward-step/src /home/n/Code/relay/.venv/bin/python -m relay.cli bump --help` from primary checkout -> exit 0 and shows `--to` / `--backward`.
- `git diff --check` -> clean.
- Manual reproduction for invalid `step: 99 (bogus)` plus `--backward` now exits 2 with a clear invalid-step error.

Feature worktree is clean after the peer-review commit.

## PR / open-pr step

- PR #251 opened: https://github.com/FastJVM/relay/pull/251 (base `main`, head `bump-backward-step`), links the ticket via `Closes ticket: bump-backward-possible`.
- CI: repo has no GitHub checks configured (`gh pr checks 251` -> "no checks reported"), so there is nothing to be green; local `pytest` (479 passed, 1 skipped) and `relay validate --json` (exit 0) stand as the verification (see Dev/Peer review above).

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: relay/architecture — add other-agent assignee role token
