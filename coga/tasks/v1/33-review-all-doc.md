---
title: review all doc
status: draft
owner: nicktoper
workflow: null
contexts:
  - coga-dev/principles
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

Read [the numbered release queue](README.md), `coga/install`, `coga/init`,
`coga/first-task`, `coga/launch`, and `coga-dev/packaging` for the affected
contracts. This former title-only draft now has the owner's scope; its workflow
is still unset and must be selected by the owner before launch.

Previous ref: `review-all-doc` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
