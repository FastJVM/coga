---
title: Finish the README launch checks left open by readme-top
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
step: 1 (implement)
agent: claude
contexts:
  - coga-dev/principles
launch_generation: 64b54f34-0ccc-44cd-97e9-52bb3fb1cf42
---

## Description

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-08 gap). marketing/readme-top is done (and retired by this Dream run) but its blackboard 'Still open for this ticket' listed unowned obligations that open tickets still route to it:
- README relative links 404 on PyPI (pyproject readme = README.md; README.md lines ~20-21, 53-67): make them PyPI-safe absolute links (marketing/publish-coga-1-0-as-the-final-v1-step finding 3 routes this to readme-top).
- Check README ## First steps against the marketing/fix-installer final matrix.
- Watch and give a verdict on the 95-second demo video the README links (~line 120).
- Show the megalaunch carry-forward proof in the README Example.
Also repoint the routing references in marketing/publish-coga-1-0-as-the-final-v1-step (~L128), marketing/build-the-launch-plan (~L46) and marketing/fix-installer/complete-the-authenticated-clean-install-audit (~L45) to this ticket. Retro's earlier attempt (PR #1059) closed unmerged.

## Context

Read `coga/install`, `coga/init`, `coga/first-task`, and `coga/megalaunch`
under `docs/contexts/coga/` for the current commands and platform boundaries;
these are cited rather than attached. The authenticated final install matrix
is owned by `marketing/fix-installer/complete-the-authenticated-clean-install-audit`.
An install/init smoke or source comparison does not replace that matrix.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

branch: codex/readme-launch-checks

## Implement handoff — 2026-10-26

Actual implementer: Codex (the configured ticket agent is Claude).
Commit `6b7cc3e04a7331016742ddfc32873e08cf9cb5b3` is pushed to
`origin/codex/readme-launch-checks`, based on current control
`01a1751fb7c99dc54aca31002d4846c4c139c582`. The final fetch found no further
movement. Manual checkout procedure completed: this checkout returned to
clean, fast-forwarded main before writing this handoff. No PR was opened.

All four README checks have a disposition below. The installer comparison
checks the completed audit's actual final matrix and later available
receipts; it does not require or invent a new install run. Authenticated
completion remains explicitly owned by the existing audit and release work.
The three requested routing references, the cleanup index, and the
idea-piece's matching claim were updated as control-branch ticket state.
PR #1059 was checked closed/unmerged; it did not complete this work.

Next: peer-review the two-file feature diff and refresh the preparation
record with the actual reviewer. Keep the authenticated-install limitation
visible in release readiness. No unowned follow-up was introduced.

## Implementation findings

- README links now use absolute GitHub URLs (tree URLs for directories).
  Historical examples pin commit IDs so ticket retirement cannot break them.
- The Example now shows an observed megalaunch handoff: on 2026-10-22 the
  Windows CI ticket blocked at 11:50, the next ticket launched at 11:51,
  and that next ticket reached peer review at 12:10. Source: `coga/log.md`
  at `3b57a4d0d4eaf3e2fabb4d30fca9adfcba7ff8d5`, entries 9111–9127.
  This proves other work continuing, not completion of the blocked ticket.
- Public thinkpick main was `a980f5822c876776361b9709b9f6b2ad4b57e9bc`.
  Its research/decision tickets are drafts, with no completed classifier
  report in that tree. The corrected vision and candidate-scoring brief
  do show the owner's correction becoming instructions. README now states
  that narrower evidence instead of claiming a completed research decision.
  The idea-piece brief carries the same correction on control.
- `coga-dev/current-direction` records why the existing demo link is removed
  and no longer says these checks have no owner. It is local-only: no
  packaged twin is permitted for this namespace.

## First-steps reconciliation

The predecessor's final audit was read from Git history, not docs/archive:
`598104e10^:coga/tasks/marketing/fix-installer/run-clean-installs-and-file-issues.md`.
It closed on October 2 with authentication recorded as a blocker in all four
October 1 artifact runs; none completed a first-task workflow.

| Evidence | Result and README consequence |
| --- | --- |
| Linux + macOS, PyPI 0.2.0, Python 3.11.16 | Init first needed gh, then failed with the resource-namespace TypeError; patched-package continuation was not an unmodified pass. A later 0.4.0 install/init smoke superseded the release gap, not the missing first task. |
| Linux + macOS, main wheel 0.3.2 | Install/init/validate passed after prerequisites; authentication stopped the first-task walk. Keep login before either agent-led entry route. |
| Fresh Mac prerequisite probe | Git's CLT stub failed headlessly. README now points to installing CLT before the sequence. |
| October 17 macOS human walk | The proposed five-line route reached coga build; it did not establish a done first task. PR #1043 is closed unmerged, so its install rewrite was not silently imported. |
| Current source/contracts | `src/coga/commands/init.py` `_repo_is_empty`, `_prune_onboarding_tickets`, and `_offer_agent_cli`, plus `coga/init` and `coga/first-task`, support build after empty-repo init, ticket for an existing project, and agent authentication before either route. README links the owning first-task guide for completion. |

Verdict: the README entry sequence agrees with the available matrix's
prerequisite/order findings and current contracts. It does not claim an
end-to-end install pass. The required fresh Linux/macOS × PyPI/main,
both-agents authenticated completion evidence remains owned by
`marketing/fix-installer/complete-the-authenticated-clean-install-audit`,
which is blocked on `marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min`.
No environments, credentials, or new install runs were substituted for it.
Current PyPI JSON reports 0.4.1, uploaded October 21; that metadata lookup is
not an install receipt. Final release validation stays with the release ticket.

## Demo verdict

Inspected the public 95-second July 18 video (`iwnewxJvRPc`): 32 frames at
three-second intervals across the clip, plus native-resolution assignment
and checkout scenes. FFmpeg's full audio check found silence throughout at
-50 dB; metadata lists no captions or description. This was a visual frame
audit, not a caption-based summary or continuous playback.

- Around 33–39 seconds, the agent offers to edit top-level `assignee` fields
  and then carries out the chosen agent reassignment. Current tickets derive
  assignee from the frozen workflow step; that old surface is gone.
- Around 41 seconds, the composed prompt directs replacement of registered
  worktree metadata under /tmp. Current `coga/checkouts` forbids ordinary
  ticket worktrees and has a different sandbox refusal recovery.
- The queue, human-gate, review and handoff ideas remain recognizable, but
  the generic “some command names may have changed” note does not cover those
  concrete differences. Removed the link from README onboarding, with the
  durable rationale in `coga-dev/current-direction`. No YouTube edit or new
  recording is required or claimed.

Local evidence: `.coga/readme-launch-checks/` (frame sheets, native-resolution
scenes, metadata summary, HTML and link receipts); downloaded video remains
`/tmp/coga-readme-demo.mp4`. Video SHA256:
`7c07651d8169e5b575ac4b4efe6da9c093ec43f03b4ff6e8d3ff7423f0dda05d`.
No docs/archive content was read; its pre-existing README link was checked
by Git path metadata and HTTP HEAD only.

## PR

```yaml
title: Make README links PyPI-safe and substantiate launch examples
author: codex
author_evidence: This implement session ran as Codex, although the ticket is configured for
  Claude. Exact model ID and reasoning override were not exposed by this session; no identity
  is inferred from the ticket assignment.
head: 6b7cc3e04a7331016742ddfc32873e08cf9cb5b3
base: 01a1751fb7c99dc54aca31002d4846c4c139c582
depth: deep
rationale: Documentation changes have passing final-head checks, but peer review has not run.
  Review the narrowed thinkpick claim, recorded queue evidence and demo removal. Authenticated
  clean-install completion remains a separate open release gate; it is not claimed here.
implementation: Makes every README link absolute, pins historical examples, shows a recorded
  megalaunch blocker followed by another ticket reaching review, corrects the unsupported
  completed-thinkpick-decision claim, clarifies login/Mac/platform prerequisites, and removes
  the obsolete July demo from onboarding. Current-direction retains the demo decision and
  recognizes follow-up ownership.
deviations: The public thinkpick records showed draft research/decision tickets, so the example
  was narrowed to the documented correction. Related ticket routing and the idea-piece copy
  were reconciled as control-branch state, not included in the feature diff.
limitations: 'Linux Python 3.12.12 suite only; no new Python 3.11, macOS or native Windows
  platform run. No authenticated first-task install rerun: the completed October audit stopped
  at login, and its successor remains blocked on owned-Mac access. Demo review used frames
  across the clip and a full silent-audio check, not continuous playback. Markdown was rendered
  and links checked, but no browser visual QA or live PyPI publication was performed.'
files:
  README.md: PyPI-safe links, evidence-backed Example and onboarding summary, and removal
    of the obsolete demo link.
  docs/contexts/coga-dev/current-direction/SKILL.md: Own the demo removal rationale and replace
    the obsolete assertion that README checks are unowned. Local-only Coga-dev context; no
    packaged twin.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step only. The next frozen step is peer-review; no independent or self-review
    receipt is claimed. Actual implementer is Codex, so a later Codex review must be classified
    honestly under the preparation rubric.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest > /tmp/coga-readme-final-pytest.log
    2>&1
  status: passed
  head: 6b7cc3e04a7331016742ddfc32873e08cf9cb5b3
  base: 01a1751fb7c99dc54aca31002d4846c4c139c582
  detail: 4121 passed, 10 skipped in 344.30s; Linux, Python 3.12.12, pytest 9.1.1. Full run
    began after commit and rebase on a clean tree. Log retained in .coga/readme-launch-checks/final-pytest.log.
    No runtime/fixture change required new tests.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pip wheel --no-deps --no-build-isolation
    --wheel-dir /tmp/coga-readme-dist .
  status: passed
  head: 6b7cc3e04a7331016742ddfc32873e08cf9cb5b3
  base: 01a1751fb7c99dc54aca31002d4846c4c139c582
  detail: Built coga-0.4.1-py3-none-any.whl. SHA256 0370c510ea61a7bd2d1ca969926d6651187c12cf71df4e7645b23faf7e12057f.
    Local verification artifact only; no upload.
- command: .venv/bin/python .coga/readme-launch-checks/check_readme.py
  status: passed
  head: 6b7cc3e04a7331016742ddfc32873e08cf9cb5b3
  base: 01a1751fb7c99dc54aca31002d4846c4c139c582
  detail: 27 Markdown link occurrences, all HTTPS; 17 current-repo links resolve in Git; 25
    distinct URLs return HTTP 200 via HEAD. Wheel description is text/markdown and byte-identical
    to README.md. README SHA256 c1c5fd62aca6a2d7e4be1bcd85952f98f9eccb055b137f6a5c1987a19a8afb08.
    HTML and JSON receipt retained beside the local checker; archive link checked without
    reading archive contents.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task finish-the-readme-launch-checks-left-open-by-readm
    --json
  status: passed
  head: 6b7cc3e04a7331016742ddfc32873e08cf9cb5b3
  base: 01a1751fb7c99dc54aca31002d4846c4c139c582
  detail: 1 ok, no issues. Runtime/config/workflow semantics did not change; fixture validation
    was not required.
- command: git diff --check 01a1751fb7c99dc54aca31002d4846c4c139c582...codex/readme-launch-checks
  status: passed
  head: 6b7cc3e04a7331016742ddfc32873e08cf9cb5b3
  base: 01a1751fb7c99dc54aca31002d4846c4c139c582
  detail: Passed on the committed feature diff after push and return to main.
```
