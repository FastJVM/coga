# V1 execution queue

Owner scope decision: 2026-10-27. This numbered queue owns the execution order;
each linked ticket owns its requirements and current workflow step. Numbers
are priority labels, not automatic dependencies or permission to skip owner gates.
Independent work may proceed in parallel. Run `coga status v1 --order-by slug`
for current status.

The release must work on macOS and native Windows, install easily, and have a
finished README with matching user documentation. Linux verification remains
in the existing clean-install matrix. Usage reporting and commit/log work
remain in v1. Microkernel work, its hackability demo, further context cleanup,
Dream fixes, and the other deferred work are in [`../_v2/`](../_v2/README.md).

## Execution order

| # | Ticket |
| --- | --- |
| | **Security and state reliability** |
| 01 | [webhook for slack is public](01-webhook-for-slack-is-public.md) |
| 02 | [Reconcile the coga notifications leaked-webhook response with the append-only log](02-reconcile-the-coga-notifications-leaked-webhook-re.md) |
| 03 | [State sync published unmerged recurring templates from a feature branch](03-state-sync-published-unmerged-recurring-templates.md) |
| 04 | [Stop the contexts-root sweep from publishing canonical topics without their packaged twins](04-stop-the-contexts-root-sweep-from-publishing-canon.md) |
| 05 | [Chat ticket edits strand the checkout on a chat branch](05-chat-ticket-edits-strand-the-checkout-on-a-chat-br.md) |
| 06 | [Fix coga git sync failures that leave main diverged from origin](06-fix-coga-git-sync-failures-that-leave-main-diverge.md) |
| 07 | [Lifecycle writes read control's ticket before modifying it](07-lifecycle-writes-read-control-s-ticket-before-modi.md) |
| 08 | [Fail the branch sweep when local branch enumeration fails](08-fail-the-branch-sweep-when-local-branch-enumeratio.md) |
| 09 | [Guard foreign linked worktree branch cleanup](09-guard-foreign-linked-worktree-branch-cleanup.md) |
| 10 | [Preflight dirty tracked files before skill-update PR checkout](10-preflight-dirty-tracked-files-before-skill-update.md) |
| 11 | [Skill update rebuilds its PR branch every period and silently discards hand-pushed commits](11-skill-update-rebuilds-its-branch-and-discards-hand-pushed-commits.md) |
| | **Release tests and Windows** |
| 12 | [Fix release_env fixture interpreter symlink in fresh venvs](12-fix-release-env-fixture-interpreter-symlink-in-fre.md) |
| 13 | [Repair CI and resume with release-focused triggers](13-repair-ci-and-resume-with-release-focused-triggers.md) |
| 14 | [Interactive coga launch on native Windows](14-interactive-coga-launch-on-native-windows.md) |
| 15 | [Uninstall recovery hints use POSIX env syntax on Windows](15-uninstall-recovery-hints-use-posix-env-syntax-on-w.md) |
| | **Installation and onboarding** |
| 16 | [Find out what macOS actually ships](16-find-out-what-macos-actually-ships.md) |
| 17 | [Separate installing coga from installing its dependencies](17-separate-installing-coga-from-installing-its-depen.md) |
| 18 | [Handle gh not being installed by default](18-handle-gh-not-being-installed-by-default.md) |
| 19 | [Install link for Claude Code yields the desktop app not the CLI](19-install-link-for-claude-code-yields-the-desktop-ap.md) |
| 20 | [Ask which agents to enable during coga init](20-ask-which-agents-to-enable-during-coga-init.md) |
| 21 | [Show which agents are available on the machine during coga init](21-show-which-agents-are-available-on-the-machine-dur.md) |
| 22 | [Init sends the user to edit a toml nothing can open](22-init-sends-the-user-to-edit-a-toml-nothing-can-ope.md) |
| 23 | [Scan for an existing repo during install](23-scan-for-an-existing-repo-during-install.md) |
| 24 | [Mention coga build in the install flow](24-mention-coga-build-in-the-install-flow.md) |
| 25 | [Position op as optional](25-position-op-as-optional.md) |
| 26 | [Make the README install section the only install path](26-make-the-readme-install-section-the-only-install-p.md) |
| 27 | [Link uninstall from the README](27-link-uninstall-from-the-readme.md) |
| 28 | [Affordable macOS testing on owned Macs and per-minute CI](28-affordable-macos-testing-on-owned-macs-and-per-min.md) |
| 29 | [Test and fix install on macOS and Windows](29-test-and-fix-install-on-macos-and-windows/ticket.md) |
| 30 | [Complete the authenticated clean-install audit](30-complete-the-authenticated-clean-install-audit.md) |
| 31 | [test-install-on-windows](31-test-install-on-windows.md) |
| 32 | [Finish the README launch checks left open by readme-top](32-finish-the-readme-launch-checks-left-open-by-readm.md) |
| 33 | [review all doc](33-review-all-doc.md) |
| | **Usage reports and commit/log work** |
| 34 | [Prevent duplicate session usage records from inflating totals](34-prevent-duplicate-session-usage-records-from-infla.md) |
| 35 | [Recheck Codex usage completeness after the session matching fix](35-recheck-codex-usage-completeness-after-the-session.md) |
| 36 | [Usage report: name the human, split per agent, show cache reads separately](36-usage-report-name-the-human-split-per-agent-show-c.md) |
| 37 | [Fix the usage-report cost-proxy parenthetical and delivery-miss comment after PR 1102](37-fix-the-usage-report-cost-proxy-parenthetical-and.md) |
| 38 | [Coalesce Coga state commits to one per lifecycle event](38-coalesce-coga-state-commits.md) |
| 39 | [Trim coga/log.md to a configurable age with a weekly recurring job](39-trim-the-audit-log.md) |
| | **Telemetry proof and public release** |
| 40 | [State the hatchling prerequisite in the clean-wheel proof](40-state-the-hatchling-prerequisite-in-the-clean-whee.md) |
| 41 | [Verify PostHog telemetry with the live clean-wheel proof](41-verify-posthog-telemetry-with-the-live-clean-wheel.md) |
| 42 | [Publish the argument for Coga as a human instrument](42-idea-piece.md) |
| 43 | [Publish coga 1.0 as the final V1 step](43-publish-coga-1-0-as-the-final-v1-step.md) |
| 44 | [Execute the V1 launch](44-build-the-launch-plan.md) |

## Dependencies and release evidence

- 03 and 04 address publication defects; coordinate 13 with their final behavior
  before resuming the hosted test workflow.
- 14 must land before 31 can verify the complete native Windows first-task path.
- 28 provides Mac access for 30. The installer fixes feed 29, 30, and 31;
  an install/init smoke does not prove a completed authenticated task.
- 32 and 33 finish the README and user documentation against the tested
  macOS, Windows, and Linux paths. Their final acceptance uses the install evidence.
- 34 and 35 establish trustworthy usage data for 36. Coordinate 37 with that report.
- 38 and 39 must preserve the audit consumers documented in their designs;
  finish usage accounting before accepting log retention.
- 40 fixes the proof prerequisites; 41 supplies the live PostHog evidence.
- 42 can proceed alongside engineering and precedes the public launch.
- 43 is the final product-delivery step: completed v1 fixes, macOS/native Windows
  first-task evidence, README/docs acceptance, release tests, and PostHog proof
  precede publication. Verify the public 1.0 artifact afterwards. 44 follows
  those verified release links and the idea piece.

## Renames and history

Ticket bodies record their previous refs; `coga/log.md` is unchanged. Lifecycle
statuses, workflow snapshots, owners, agents, PR records, and attachments were
preserved. Existing feature branches must reconcile the renamed control tickets
before further work; parked work needs an explicit owner pull-forward decision.
