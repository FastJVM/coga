---
title: bump backward possible
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
  - relay/codebase
  - relay/architecture
skills: []
workflow: code/with-review
---

## Description

Make it possible to move a ticket *backward* through its workflow. Today
`relay bump` only advances (`next_step = current_idx + 1`) and refuses to
go past the last step; the only way to rewind is a human hand-editing the
`step:` field. We want a first-class, validated way to send a ticket back
to an earlier step — e.g. peer review finds the implementation needs a
fresh pass, so the ticket goes back to `implement` and runs "through
another layer" again.

Done looks like: `relay bump <id> --to <step>` moves the ticket to the
named or numbered target step, the move is validated and logged, it
broadcasts to Slack like a normal transition, and the base-prompt contract
is updated so this is a sanctioned move (not a panic) for both humans and
agents.

## Context

### Pinned design decisions (from the bootstrap interview)

- **Interface:** add a flag to the existing `relay bump` command rather
  than a separate `rewind` command. Primary form is
  `relay bump <id> --to <step>`, where `<step>` is a step **number** or
  **name** in the frozen workflow. (A bare `--backward` shorthand for
  "one step back" is acceptable if it falls out cleanly, but the
  number/name target is the required capability — decide during
  implement/peer-review, don't over-build.)
- **Target:** jump directly to any earlier step by number or name. This is
  the rewind capability. Whether `--to` is also allowed to skip *forward*
  is out of scope — keep the contract "you cannot skip ahead" intact and
  only relax the backward direction unless peer-review argues otherwise.
- **Who:** humans only. A rewind is the human's tool for acting on a
  panic (or their own judgment that a prior step was wrong). Agents still
  do **not** go backward — they `relay panic` and the human decides. The
  `--to` path must therefore *refuse* when invoked from inside a launched
  agent session: gate on `RELAY_SUPERVISED` (the env var set by
  `relay launch`) and bail with a message pointing the agent to `panic`.
  Decide the exact enforcement during implement/peer-review, but a
  supervised agent must not be able to rewind.

### Contract / prompt change

The base prompt's agent contract stays intact: agents still don't go
backward — they `relay panic` and the human decides. What changes is that
the human now has a CLI tool to *act* on that decision instead of
hand-editing `step:`. The base prompt at `src/relay/resources/prompt.md`
currently says **"Do not go backward. If a previous step was wrong and
needs rework, call `relay panic` with a clear reason. The human decides
whether to rewind."** Leave the agent-facing "don't go backward / panic"
rule as-is, but make the docs accurate where they describe the *human's*
options — i.e. "the human decides whether to rewind" can now point at
`relay bump <id> --to <step>` as the mechanism. Keep `relay bump --help`
and any `relay bump` guidance consistent with the new flag. Edit only
`src/relay/resources/prompt.md` — the matches under `.relay/`, `.venv/`,
and `templates/relay-os/.relay/` are installed-package/venv copies, not
separately-maintained sources; do not hand-edit those.

### Codebase pointers

- `src/relay/bump.py` — `advance_step()` writes `step:` and re-validates.
  The backward move should reuse this path (and its Slack/log machinery)
  rather than a parallel code path.
- `src/relay/commands/bump.py` — thin Typer entrypoint; add the `--to`
  option here, resolve the target step (number or name) against the frozen
  `workflow.steps`, and bail clearly on an unknown/out-of-range target.
- Reuse `resolve_step_assignee` so the target step's `assignee:` role token
  re-resolves on the way back (e.g. returning to `implement` flips the
  assignee back to the coder). Mind the `other-agent` flip in
  `code/with-review`.
- Slack/log wording: a forward bump says "advanced to step N". A backward
  move needs its own verb (e.g. "rewound to step N") so the audit trail and
  channel read honestly.
- Respect existing invariants from `relay/architecture`: `step:` is owned
  entirely by `relay bump`; only moves when `status: in_progress` (the
  `--to` path must keep that gate — don't bypass the status check); the
  `relay launch` supervisor re-chains on assignee changes. `step:` is
  stored as `"N (name)"` and step numbers are 1-based — mind the off-by-one
  against `step_index()` / `next_step - 1` arithmetic already in the file.
- **Re-chaining after a human rewind.** Since rewind is humans-only and
  refused under `RELAY_SUPERVISED`, it runs outside a launched agent
  session — so the `emit_done_marker` chain logic isn't on the rewind path.
  But a rewind still flips `assignee:` backward (e.g. peer-review →
  implement flips back to the coder), so the *next* `relay launch` must
  pick up the rewound step with the right assignee. Verify the rewound
  ticket validates and relaunches sanely.

### Tests & fixtures

- Add `pytest` coverage under `tests/` (see `tests/test_commands.py` /
  bump tests) for: backward by number, backward by name, unknown target,
  and assignee re-resolution on the way back.
- Update the `example/` seeded fixture if the workflow/bump semantics shift
  in a way the smoke path depends on (CLAUDE.md rule).
- Run `python -m pytest` and `relay validate --json` before opening the PR.

### Out of scope

- Forward step-skipping.
- Rewriting blackboard/log contents from prior steps (a rewind re-runs a
  step; it does not erase history).
