# V1 execution queue

Owner scope decision: 2026-10-27. This numbered queue owns the execution order;
each linked ticket owns its requirements and current workflow step. Numbers
are priority labels, not automatic dependencies or permission to skip owner gates.
Independent work may proceed in parallel. Run `coga status v1 --order-by slug`
for current status.

The release must work on macOS and native Windows, install easily, and have a
finished README with matching user documentation. Linux verification remains
in the existing clean-install matrix. Usage reporting and commit/log work
remain in v1. Since 2026-11-12 the [microkernel group](microkernel/README.md)
is also in v1, so Coga ships hackable. Its hackability demo, further context cleanup,
Dream fixes, and the other deferred work are in [`../_v2/`](../_v2/README.md).

## Execution order

Renumbered 2026-11-19 after the plain-Git decision. Only open tickets are
listed; done and canceled tickets keep their old numbers until deleted.

| # | Ticket |
| --- | --- |
| | **Urgent** |
| 01 | [Roll out the 04b edge shims on this repo's blocker-reminders period](01-urgent-roll-out-the-04b-edge-shims-on-this-repo-s-blocker.md): the recurring job fails with "unknown recipe" since PR #1272 |
| | **Security** |
| 02 | [webhook for slack is public](02-webhook-for-slack-is-public.md) |
| | **Architecture: plain Git and one executor model** |
| 03 | [Use Git like everyone: remove Coga's publication abstraction](03-use-git-like-everyone-remove-coga-s-publication-ab.md) |
| 04 | [Script or agent: one executor model and one launch loop](04-script-or-agent-one-executor-model-and-one-launch.md) (after 03) |
| 05 | [Launch on a stale feature branch leaves projected state](05-launch-on-a-stale-feature-branch-leaves-projected.md): likely moot under 03; re-check before work |
| — | [Microkernel group](microkernel/README.md): remaining placements 12–17, re-scoped against 03 |
| | **Agents and Windows** |
| 06 | [Handle gh not being installed by default](06-handle-gh-not-being-installed-by-default.md) |
| 07 | [Wire agent skills on Windows without symlink privilege](07-wire-agent-skills-on-windows-without-symlink-pr.md) |
| 08 | [Make coga's built-in commands agent-agnostic](08-make-coga-s-built-in-commands-agent-agnostic.md) |
| 09 | [Make adding a third agent one registry edit](09-make-adding-a-third-agent-one-registry-edit.md) |
| | **Install and release evidence** |
| 10 | [Test install on Windows](10-test-install-on-windows.md) |
| 11 | [Verify the macOS full-suite procedure on the EC2 Mac](11-verify-the-macos-full-suite-procedure-on-the-ec.md) |
| 12 | [Complete the authenticated clean-install audit](12-complete-the-authenticated-clean-install-audit.md) |
| 13 | [Verify PostHog telemetry with the live clean-wheel proof](13-verify-posthog-telemetry-with-the-live-clean-wheel.md) |
| | **Release** |
| 14 | [Publish coga 1.0 as the final V1 step](14-publish-coga-1-0-as-the-final-v1-step.md) |

## Dependencies and release evidence

- 03 precedes 04 and the remaining microkernel placements; 03's
  implementation PR also aligns the README and user topics with the
  2026-11-19 principles.
- The microkernel group must leave the `coga-dev/microkernel` "Open command
  placements" table empty before 14.
- 10, 11 and 12 supply the macOS/native Windows first-task and clean-install
  evidence; 13 supplies the live PostHog evidence.
- 14 is the final product-delivery step: completed v1 fixes, 03/04, the
  microkernel group, install evidence, README/docs acceptance and PostHog
  proof precede publication. Verify the public 1.0 artifact afterwards. The
  public launch is not a v1 step (parked in `_v2/marketing/build-the-launch-plan`).

## Renames and history

Ticket bodies record their previous refs; `coga/log.md` is unchanged. Lifecycle
statuses, workflow snapshots, owners, agents, PR records, and attachments were
preserved. Existing feature branches must reconcile the renamed control tickets
before further work; parked work needs an explicit owner pull-forward decision.
