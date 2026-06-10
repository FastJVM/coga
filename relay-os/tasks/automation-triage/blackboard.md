The blackboard is a notepad to be written to often as the human and agent works through a task.

## Notes for the implementer

The ticket is fully specced — read it; this is just orientation.

- **Source method:** the post cited in the ticket *is* the rubric. Don't re-derive.
- **This ticket = rubric + tiers only.** Ships the `autonomy/triage` context + the
  four `autonomy/` tier workflows (3 moved from `browser/`, 1 new `assist-only`),
  and repoints `build-automation`'s moved tier paths. It does **not** wire the
  test into any flow — that's the follow-up. So nothing consumes `autonomy/triage`
  yet; that's intended.
- **build-automation triage is a separate concern** — leave its logic untouched;
  only update the moved tier paths.
- **Move is path-safe** (verified at authoring): no `workflow:` field binds a
  moved tier, no tests reference tier names, `validate.py` has no tier whitelist.
  `name:` is display-only, not used for resolution.
- **Done check** is in the ticket: `relay validate --json`, grep for stale
  `browser/<tier>` refs, single-token assignees, follow-up filed as draft.

(Full bootstrap/eval history was trimmed once the ticket stabilized — it's in git
history if needed.)

## Dev

- Human override: commit/push this directly on `main` because the change is pure
  Relay OS markdown/state, not a feature-branch PR.
- Implemented on primary checkout with explicit path staging to avoid unrelated
  recurring/task-state churn already present in the working tree.

## Implementation notes

- Added `relay-os/contexts/autonomy/triage/SKILL.md` and the packaged mirror.
- Moved the three generic tier workflows from `browser/` to `autonomy/` in the
  live tree and packaged workflow templates, updating `name:` frontmatter.
- Added `autonomy/assist-only` in live and packaged workflow trees.
- Updated `browser/build-automation` only to point at the moved
  `autonomy/<tier>` workflow paths; its triage logic remains browser-specific
  and three-outcome.
- Filed draft follow-up:
  `wire-autonomy-triage-into-impl-ready-workflows`.

## Verification

- `python -m pytest` passed: 608 passed, 1 skipped.
- `relay validate --task automation-triage --json` passed.
- `relay validate --task wire-autonomy-triage-into-impl-ready-workflows --json`
  passed.
- Full `relay validate --json` is blocked by pre-existing unrelated ticket
  issues (`relay-additions-spec` and
  `split-context-to-doc-user-accessible-and-editable` missing `step:`).
- Stale `browser/<tier>` grep with `.relay` excluded only hits this ticket's
  own move-spec prose.

## Self-QA

- `codex review --commit f08b4b6 --title "Add autonomy triage tiers"` ran after
  sandbox retry; it found no correctness issues.
- Ran a simplify-equivalent Codex pass in `/tmp/relay-selfqa-simplify-4Ctcyg` to
  avoid unrelated primary-checkout churn. Applied its safe markdown cleanups:
  shorter frontmatter descriptions, wrapped dense workflow/context prose, and
  corrected `autonomy/triage` from "human-assigned steps" to `assignee:` choices
  because `autonomy/fully-automated` is all-agent.
- Re-verified live and packaged copies match byte-for-byte for the touched
  autonomy/build-automation files.
- `PYTHONPATH=/home/n/Code/relay/src /home/n/Code/relay/.venv/bin/python -m pytest`
  passed: 610 passed, 1 skipped.
- `relay validate --task automation-triage --json` and
  `relay validate --task wire-autonomy-triage-into-impl-ready-workflows --json`
  passed.
- Full `relay validate --json` still exits non-zero on unrelated backlog issues,
  including `relay-additions-spec` and
  `split-context-to-doc-user-accessible-and-editable` missing `step:`.
