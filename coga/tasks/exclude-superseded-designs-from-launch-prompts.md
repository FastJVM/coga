---
title: Exclude superseded designs from launch prompts
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
agent: claude
---

## Description

Keep archived ticket designs available to humans without automatically presenting their full text as current blackboard state on every launch. This addresses the surviving prompt-composition part of PR 755; its draft-synthesis-gate issue is already fixed.

This P2 follow-up comes from [the triage](triage-five-review-comments-that-merged-unanswered.md). An explicit megalaunch pick activated implementation on 2026-09-18. The implementation follows the recommended minimal scope below, retaining the existing archive placement.

### Evidence and source

Original [PR 755 comment](https://github.com/FastJVM/coga/pull/755#discussion_r3937900285); source ticket: [give-a-ticket-s-superseded-design-one-documented-h](give-a-ticket-s-superseded-design-one-documented-h.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

The partial fix `4e544d356a53b94a332c24e793ca8d6a1c833d51`, merged in `c4482fae9cb6e63e41c47dd156c08f66f2fee09c` (PR 755), excludes exact archive sections from synthesis checks and preserves them through activation. A 1,558-character archive passes that gate, unrelated scratch still fails, and all 60 abandoned-design markers still enter `compose_prompt`. Archive inclusion is verified; model confusion is a plausible consequence, not a measured incident.

### Behavior and scope

Retain the existing on-disk archive and its headings, but exclude exact top-level `## Superseded designs` sections from the automatically composed blackboard. Keep a short archive pointer for deliberate reading and keep current decisions and reasons in the live body/blackboard. This avoids moving every historical ticket. The original comment's alternative above-fence migration is outside this implementation's scope.

Inspect `src/coga/compose.py::compose_prompt_report`, `blackboard.prelaunch_blackboard_synthesis_reason_text`, and ticket section parsing. Share section recognition only where there are real common consumers; preserve unrelated blackboard content, `## Dev`, `## Blockers`, and following sections. Do not change stored history just to alter composition.

### Acceptance and focused verification

- Short and large conforming archives are absent from rendered prompts while archived bytes stay available and unchanged on disk.
- Live notes before and after the archive, machine-readable Dev/Blockers state, and current requirements still compose as intended.
- Heading boundaries are explicit: exact top-level archives are omitted, similar names or prose/code examples are not silently discarded. Cover nested historical headings and duplicate exact sections defensively.
- Draft validation and activation retain the shipped synthesis exemption and preserve the archive; unrelated authoring scratch remains subject to the existing gate.
- `--prompt-report` measures the actual composed blackboard. Test composition and draft activation in `tests/test_compose.py`, `tests/test_blackboard.py`, and `tests/test_mark.py`.
- Update the owning convention `coga/contexts/dev/code/SKILL.md`, the Layer-6 contract in `coga/contexts/coga/architecture/SKILL.md`, the PR 755 `coga/codebase` gotcha, and any affected authoring instructions. Keep each packaged twin under `src/coga/resources/templates/coga/bootstrap/` synchronized and run packaging checks.

Related [blackboard-bloat remedy](document-the-remedy-for-a-bloated-blackboard-sibli.md) offers manual archival guidance; it does not change this automatic inclusion rule and is not an equivalent fix. Coordinate shared context edits without changing that ticket's workflow.

Tradeoff: automatic launch loses historical alternatives unless the live summary preserves relevant rationale or the agent follows the archive pointer. Out of scope: bulk archive migration, deleting history, changing review ownership, or relitigating the already-fixed synthesis gate.

## Context

- `src/coga/compose.py::compose_prompt_report` originally passed the stored
  blackboard unchanged to Layer 6 and to the blocker preamble. Both consumers
  need the live projection so historical blocker examples cannot leak back in.
- `src/coga/blackboard.py::prelaunch_blackboard_synthesis_reason_text` already
  exempts archives from draft synthesis. Share its section recognition with
  prompt composition and `blackboard_size_warning`, retaining on-disk history.

<!-- coga:blackboard -->

## Dev

branch: codex/exclude-superseded-designs
worktree: /tmp/coga-exclude-superseded-designs

## Implementation plan

- The audit log records explicit megalaunch activation on 2026-09-18 at 17:31.
  This implementation follows the recommended minimal scope selected by that
  launch; the draft-era hold was superseded by activation. Keep archives
  on disk, omit their text from launch prompts, and add a deliberate-read pointer.
- Work in the separate feature checkout; keep task state and the final bump in
  the primary checkout. The pre-existing edit to
  `preserve-edits-during-released-claim-recovery.md` is unrelated and untouched.
- Share archive recognition between synthesis and composition. Add regression
  coverage before the fix, including code fences, nested headings, duplicate
  archives, surrounding live state, activation preservation, and report sizes.
- Update the owning contexts, affected authoring guidance, packaged twins, and
  example fixture. Run focused checks and the full suite, commit, freshen against
  `origin/main`, then bump once to peer review without pushing or opening a PR.

## Findings and decisions

- Re-read the original PR 755 comment through GitHub: its requested remedy was
  above-fence placement **or** exclusion from the launch blackboard. Keeping the
  existing archive on disk and filtering composition satisfies that alternative.
- New regressions reproduced prompt leakage for both file and directory tickets,
  short and large archives, duplicate sections, and historical blocker examples.
  The existing regex also treated fenced archive examples as real archives and
  fenced historical headings as live sections. The shared projection now tracks
  backtick/tilde fences and preserves all non-archive text verbatim.
- One pointer names the exact ticket file and archive heading. Filtering happens
  before the blocker preamble and report layers; the size warning measures that
  same projection. Draft synthesis uses the same archive boundaries without the
  generated pointer. No stored-history migration or lifecycle change.
- Test environment: ambient `python` lacks `tomlkit`; use the existing declared
  test environment `/tmp/coga-system-completion-venv/bin/python` with the feature
  checkout's absolute `PYTHONPATH`. The initial focused regression selection
  passes all 27 cases after the fix; broader and final checks follow.
- Shared-context coordination: the separate
  `document-the-remedy-for-a-bloated-blackboard-sibli` task remains at `open-pr`.
  Its manual attachment remedy still applies to large live notes. This change
  touches the adjacent Layer-6 contract and corrects the blackboard writer
  context's old claim that design archives always compose; retain both sets of
  guidance when rebasing. No edits or transitions were made to that ticket.

## Verification

- Focused pre-fix regressions: prompt leakage, fenced-heading misclassification,
  and archive-only size warnings reproduced. After the shared filter, the initial
  archive-focused selection passed **27 tests**.
- `PYTHONPATH=/tmp/coga-exclude-superseded-designs/src /tmp/coga-system-completion-venv/bin/python -m pytest -q tests/test_compose.py tests/test_blackboard.py tests/test_mark.py tests/test_validate.py tests/test_packaging.py tests/test_smoke.py tests/test_bootstrap_ticket_skill_template.py --tb=short`
  — **288 passed**, including wheel construction and twin synchronization.
- From the feature checkout's `example/coga/`:
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-exclude-superseded-designs/src /tmp/coga-system-completion-venv/bin/python -m coga.cli validate --json`
  — **4 tasks, no issues**. The fixture disables notifications; unset the inherited
  legacy bare webhook variable rather than editing config to satisfy its guard.
- From the primary checkout:
  `PYTHONPATH=/tmp/coga-exclude-superseded-designs/src /tmp/coga-system-completion-venv/bin/python -m coga.cli validate --task exclude-superseded-designs-from-launch-prompts --json`
  — **1 task, no issues**.
- `PYTHONPATH=/tmp/coga-exclude-superseded-designs/src /tmp/coga-system-completion-venv/bin/python -m pytest`
  — **2,689 passed in 192.82s**, including the final boundary regressions
  (empty archives, trailing whitespace, unclosed fences, mismatched fence
  markers/lengths, and archived Production-notes examples).
- Implementation committed and rebased cleanly onto fetched `origin/main`
  `6210db599296ed743e9a9f8acdd9fe3d541671f1`; final implementation commit is
  `9530336d`. The feature checkout is clean and the ancestor check passes.
  The same full-suite command passed again after rebase: **2,689 passed in
  198.58s**. `git diff --check origin/main...HEAD` is clean. No push or PR.

## Implement handoff

Ready for peer review on commit `9530336d` in the recorded feature checkout.
Four live/package context pairs are synchronized; the package-only authoring
skill, base prompt, human docs summary, and seeded example reflect the new
boundary. Source edits are committed; task notes remain in this primary copy
for the final `coga bump` transition. The adjacent blocker-reader finding below
is intentionally unresolved and does not change the archive composition scope.

## Adjacent finding — archive checkbox examples

`src/coga/blackboard.py::parse_blockers_text` and `open_blockers` scan the stored
region without section or code-fence awareness. A temporary conforming archive
containing a fenced `- [ ] [2026-09-18 12:00] [human:marc] id=old Historical example ask`
still returns blocker ID `old`; the new prompt projection omits that text.
`src/coga/megalaunch.py` and `src/coga/commands/launch.py` use `open_blockers` for
pre-composition gates, so such historical examples can affect launch eligibility.
This is pre-existing lifecycle parsing behavior, left unresolved in this
composition-only change. No matching follow-up was found in the task tree.
Peer review should keep this boundary visible; `retro/done-ticket` owns carrying
the finding forward rather than expanding this ticket into blocker lifecycle work.
