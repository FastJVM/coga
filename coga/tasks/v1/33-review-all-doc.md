---
title: review all doc
status: in_progress
owner: nicktoper
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
contexts:
- coga-dev/principles
step: 1 (implement)
agent: claude
launch_generation: 9141bf8e-f7aa-4bdc-8296-df1cc9fb1464
---

## Description
Finish the README and the user documentation needed for the first-user release.
Owner clarification, 2026-10-27: v1 must work on macOS and native Windows,
be easy to install, and have a completed README with matching documentation.
This ticket owns the final documentation acceptance pass; the numbered installer
and platform tickets own product fixes and live platform verification.

### Acceptance criteria

- The README gives a clear install and first-task path on macOS, native Windows,
  and Linux, with required tools, agent authentication, and optional dependencies
  distinguished. Existing-repo and new-repo instructions agree with actual behavior.
- Check every command and platform claim against the release candidate and the
  evidence from `v1/29-test-and-fix-install-on-macos-and-windows`,
  `v1/30-complete-the-authenticated-clean-install-audit`, and
  `v1/31-test-install-on-windows`. Installation or `--help` alone is not proof of
  a working authenticated first task.
- The install, init, first-task, launch, configuration, and uninstall topics agree
  with the README. Fix contradictions and broken navigation needed by those user
  paths, keeping canonical and packaged copies synchronized. Broader context
  restructuring remains deferred in `_v2/`.
- Coordinate with `v1/32-finish-the-readme-launch-checks-left-open-by-readm` so its
  link, example, and existing-demo checks have one owner. Verify the final README
  renders on GitHub and PyPI, including links and the wheel metadata description.
- Record the exact candidate commit, reviewed pages, command and link checks,
  remaining findings, and the owner's acceptance. Unresolved first-user blockers
  return to their existing tickets and prevent acceptance; cosmetic/context
  cleanup does not silently expand v1.

## Context

### Scope and required reading

Read [the numbered release queue](README.md) for sequencing. This is a
documentation change through `docs/with-review`: implementation, peer review,
PR, then `nicktoper`'s acceptance. Product fixes and fresh authenticated platform
walks stay with their existing tickets. Documentation work can proceed while
those receipts are pending, but final acceptance requires the evidence.

Review `README.md` and the following topics, cited rather than attached because
they are review and editing targets. Open their current files before editing;
check `docs/README.md` and inbound links when navigation changes.

| Ref and canonical path | Sections to read |
| --- | --- |
| `coga/install` — `docs/contexts/coga/install/SKILL.md` | Prerequisites; Install the CLI; Verify; Upgrading and removing |
| `coga/init` — `docs/contexts/coga/init/SKILL.md` | Fresh repo; Clone of a repo that already uses Coga; Instruction files and skill discovery; The operator's name |
| `coga/first-task` — `docs/contexts/coga/first-task/SKILL.md` | The complete first-task walk |
| `coga/launch` — `docs/contexts/coga/launch/SKILL.md` | Targets; Checkout boundary; Status is the signal; Phases and routing; The step chain; Options and exits |
| `coga/configuration` — `docs/contexts/coga/configuration/SKILL.md` | Shared/local configuration introduction; Allowlists; Unknown keys fail loud; `env:` indirection in config |
| `coga/uninstall` — `docs/contexts/coga/uninstall/SKILL.md` | What it removes; Safety rules; The global package |

`coga-dev/packaging` at `docs/contexts/coga-dev/packaging/SKILL.md` is cited
rather than attached; read "Canonical copies and twins" and "Wheel packaging".
Every edited user topic must stay byte-identical to its packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/<ref>/SKILL.md` in the
same PR. Coga-dev topics remain local-only. Run the relevant
`tests/test_packaging.py` checks and inspect a wheel built from the recorded
candidate; build from a pristine checkout when checking packaging behavior.

### Existing owners and evidence

- `v1/26-make-the-readme-install-section-the-only-install-p` owns making the
  README the single installation path and moving useful facts before retiring
  the separate install page. Review its final result: if `coga/install` has
  been removed, inspect the surviving owners and repaired links instead of
  requiring that page to remain. This ticket does not reverse that decision.
- `v1/32-finish-the-readme-launch-checks-left-open-by-readm` owns the README's
  absolute links, supported examples, first-steps comparison, and existing-demo
  verdict. Its PR [#1119](https://github.com/FastJVM/coga/pull/1119) merged on
  2026-10-28. Reuse its recorded checks and demo disposition, verifying that the
  final candidate includes them and that later edits introduce no regressions.
  A new demo or repeated historical investigation is outside this pass.
- `v1/29-test-and-fix-install-on-macos-and-windows` supplies the macOS human
  walk despite its older title. `v1/30-complete-the-authenticated-clean-install-audit`
  owns fresh Linux/macOS authenticated first-task evidence on Python 3.11 for
  PyPI and a main wheel. Its owner approved both Claude Code and Codex in each
  of those four combinations: eight required authenticated first-task completions.
  That scope approval is not a receipt; the October 28 access check records
  no completed run and still needs the owned Mac's SSH target.
  `v1/31-test-install-on-windows` owns the attended native Windows walk
  after `v1/14-interactive-coga-launch-on-native-windows`. Read their receipts,
  not just their statuses. A login blocker, install/init smoke, or patched
  artifact is not an authenticated first-task pass.

### Verification and acceptance record

Record the exact candidate commit, wheel version and hash, reviewed pages,
command and shell/platform checks, link and anchor results, and rendering
receipts on this ticket's blackboard. Map each platform claim to its source
receipt and tested artifact. If relevant behavior changed since that receipt,
request a rerun from its owning ticket; do not silently treat old evidence as
a pass for the new candidate. Classify remaining findings as first-user
blockers with an existing owner, or deferred cosmetic/context cleanup.

Before release, inspect the candidate README on GitHub and render the wheel's
description with a PyPI-compatible renderer. Check that `[project].readme` in
`pyproject.toml` still selects `README.md`, that the wheel's description matches
that candidate's README, and that its content type and links render correctly.
`v1/43-publish-coga-1-0-as-the-final-v1-step` owns publication and the repeat
check of the live PyPI description against the released artifact; this keeps
documentation acceptance from depending on a release it must precede.

At the owner-held review step, record `nicktoper`'s explicit acceptance of the
identified candidate and its evidence before merging/closing. Missing platform
proof or unresolved first-user blockers prevent acceptance. Hand the accepted
record to the release ticket; broader `_v2/` restructuring remains deferred.

Previous ref: `review-all-doc` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Dev

branch: codex/v1-33-doc-acceptance

## Implementation plan — 2026-10-28

Actual implementer: Codex. Manual checkout start: clean `main`, fetched and
fast-forward checked at `68b6cca1e`; no existing branch, PR, or dirty work.
Docs-only scope: review the README and six user topics against source and
receipts, correct first-user guidance, synchronize topic twins, check links
and candidate wheel metadata/rendering, then commit/push and hand off.
No product fixes, platform provisioning, or authenticated walks belong here.

Evidence correction: ticket 30 approves eight runs, but its latest access
check explicitly says none ran. The body now distinguishes required runs
from completed evidence. Ticket 14 is still at owner review-design, native
agent launch still refuses in source, and ticket 31 has no walk receipt.
Ticket 26 is still draft; do not silently treat its install-page removal as
landed. Documentation can proceed; final acceptance remains gated on these
owners and nicktoper's explicit acceptance of the eventual candidate.
