The blackboard is a notepad to be written to often as the human and agent works through a task.

## Origin

Split out from `move-automerge-out-of-relay-status` on 2026-05-08
during an orient session. The sibling ticket covers the broad
recurring sweep; this one is the targeted check at the moment of
launch.

Nick explicitly called this half out as the one he most wants —
the moment a stale-ticket bug actually hurts (agent spins up
against a merged PR's ticket).

## Implementation note

This depends on the `auto_bump_merged(cfg, ...)` helper extracted
in `auto-bump-tickets-when-their-pr-merges`. Before starting
implementation, check whether that helper already accepts a
single-slug scope; if not, add an `auto_bump_one(cfg, slug)`
sibling that shares the bump path.

## Decisions (resolved during impl)

- **`gh` missing → warn-and-continue.** Fail-loud is satisfied by a
  visible yellow warning to stderr that names the failure and points
  at `gh auth login`. Hard-fail would be hostile to contributors who
  haven't set up `gh`.
- **`--no-verify` flag.** Yes, opt-out exists for the offline /
  known-stale-but-I-want-to-edit-anyway case.
- **Bootstrap shims.** Skipped explicitly via the
  `isinstance(ref, TaskRef)` guard. They have no status / PR link, so
  the candidate filter would no-op anyway, but the explicit skip
  keeps intent legible.

## Implementation

Done out-of-band from this ticket (worked on it directly from an
orient session rather than relaunching, since the orient base prompt
forbids `relay launch` from inside an orient session).

### Changes

- `src/relay/automerge.py`
  - Extracted `_try_bump_one(cfg, ref, *, quiet)` from
    `auto_bump_merged`. Single source of truth for the
    "candidate? → gh → mark_done" flow. Always raises `GhError`;
    callers decide whether to swallow.
  - `auto_bump_merged` now loops over `_try_bump_one`, preserving
    the existing "first GhError short-circuits the sweep when
    quiet=True" behavior.
  - New `auto_bump_one(cfg, ref, *, quiet=False) -> bool` — the
    targeted single-ticket helper. Always raises GhError.
- `src/relay/commands/launch.py`
  - New `--no-verify` flag.
  - After factory mode, before `read_ticket(ref)`, calls
    `auto_bump_one(cfg, ref)`. If True (bumped to done): print a
    clear "auto-bumped to done before launch" line and `return`
    cleanly (no lock, no agent spawn, exit 0). If GhError: print a
    yellow warning + `gh auth login` hint, continue launch.
  - Skipped on bootstrap shims, prompt-report, and `--no-verify`.

### Tests

- `tests/test_automerge.py` — 7 new tests covering `auto_bump_one`:
  bumps on merged final-step, bumps on no-workflow merged,
  skips non-final, skips open PR, skips no-PR-link, skips already-done,
  always-raises-on-gh-error.
- `tests/test_launch.py` — 5 new tests covering the launch path:
  bumps + skips agent spawn, no-op when PR open, warn-and-continue
  on GhError, `--no-verify` skips entirely, no-op without PR link.
- Full suite: 283 passed (was 272).

### Branching note for the human

The work happened on `codex/dream-workers-skills-only` because that
was the active branch when the orient session started, but the
changes are unrelated to that branch's Dream-workers scope. Before
opening a PR, the human should rebase / cherry-pick this onto a
fresh branch (suggested name:
`verify-ticket-freshness-on-relay-launch`).

## Follow-up

Sibling ticket `move-automerge-out-of-relay-status` is still open —
the recurring sweep half hasn't been touched.
