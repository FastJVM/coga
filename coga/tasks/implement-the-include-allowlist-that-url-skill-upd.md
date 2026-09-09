---
slug: implement-the-include-allowlist-that-url-skill-upd
title: Implement the include allowlist that url skill updates already promise
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

`coga skill install-url` records an `include` allowlist in `.coga-source.json`,
and both `coga/contexts/coga/codebase/SKILL.md` and the `recurring/skill-update`
template described that allowlist as re-applied on every update. It is not.
**`include` is never read anywhere in `src/coga/skill_manager.py`** (zero
occurrences). PR #773's review caught the docs; this ticket is the code half.

What `_update_url_skill_dir` actually does is compare two digests — the fresh
download's `source_tree_digest` against the recorded one, and
`hash_skill_tree(skill_dir)` against `installed_tree_digest` — and then either
report `skipped-local-adaptation` / `conflict`, or call `_replace_skill_tree`
with the complete upstream tree. A pruned install therefore has only two
outcomes on update, and both are wrong:

- Record the digests honestly and the pruned copy reads as locally adapted
  forever: `skipped-local-adaptation` while upstream is quiet, `conflict` when
  it moves, parked under the follow-up heading on **every** run.
- Record the pruned tree's digest as `source_tree_digest` and the upstream
  comparison can never match, so every run silently un-prunes the skill and
  reports it as an ordinary `updated`.

This is not cosmetic, which is why it is worth its own ticket. When a follow-up
is the only outcome and no PR opened, `run_skill_update_recipe` returns 1, so
`coga/recurring/skill-update/ticket.py` exits before reaching `coga bump`. The
recurring runner treats a non-zero `ticket.py` as sweep-ending
(`recurring_runner.py`, the `except SystemExit` branch), so **every template
ordered after `skill-update` is skipped for that period**. A single
permanently-pruned skill quietly disables the rest of the recurring schedule,
week after week. `coga/skills/clarity/` is the live instance.

Implement the allowlist so pruning is reproducible:

- Read `include` in the URL install and update path and materialize only the
  listed paths.
- Keep `source_tree_digest` the true digest of the fetched upstream tree, so
  the upstream-changed comparison stays meaningful.
- Re-record `installed_tree_digest` from the pruned result, so a clean pruned
  install reads as unmodified rather than as a local adaptation.
- An edit the operator made *beyond* the allowlist must still surface as
  `conflict` — the allowlist reproduces pruning, it does not suppress real
  adaptation detection.

## Context

- `src/coga/skill_manager.py` — `_update_url_skill_dir`, `_replace_skill_tree`,
  `hash_skill_tree`, `_url_metadata`.
- `src/coga/skill_update.py` — `run_skill_update_recipe`'s `return 1` on
  follow-ups with no PR.
- `coga/skills/clarity/.coga-source.json` — the live pruned install, with the
  allowlist and the `local_adaptation_notes` describing it.
- `tests/test_skill_manager.py` — existing url install/update coverage to
  extend.
- Related: `autofix/stop-one-failing-ticket-py-from-starving-the-rest` covers
  the sweep-starvation half. Fixing either one alone leaves the other real;
  this ticket removes the standing follow-up, that one stops a single failing
  template from starving the sweep.
- Docs already corrected to describe today's behavior in PRs #773 and #775 —
  when this lands, both need updating back to describe the allowlist as real.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
