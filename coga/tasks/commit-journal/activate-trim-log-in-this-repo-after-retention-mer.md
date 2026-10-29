---
title: Activate trim-log in this repo after retention merges
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 2 (evaluate-design)
agent: claude
launch_generation: 12175f57-aac3-44a7-b59a-4c36100535d0
---

## Description

Activate audit retention in this repository after the compatible implementation
from PR #1129 reaches current main; that PR closes
`v1/39-trim-the-audit-log`, while this ticket owns the operational
rollout and its cleanup. After owner review of the rollout plan, quiesce and
upgrade every participating writer, run the documented interpreter-resolved
`python -m coga_edge.trim_log --install`, review and publish its five repo
artifacts, and remove the staging copy and temporary packaging exception
through a reviewed cleanup PR. Done means the compatible writers can resume,
the intended weekly job is discoverable on control with existing retention
settings preserved, the effective log merge attribute is unset, all five live
artifacts match their packaged copies, and the cleanup has merged with the
required checks passing. Do not trim the live log manually or force a
production maintenance run to demonstrate activation.

### Acceptance criteria

- [ ] Fresh `origin/main` contains PR #1129's merged implementation, verified
  by ancestry and the installed sources/resources, not the old branch name or
  package version alone. The owner has approved the writer inventory,
  maintenance window, manual checkout procedure, reviewed wheel provenance,
  publication order, recovery and resumption at `review-design`.
- [ ] Every participating writer is stopped before replacement and upgraded
  before any enabling files are installed. Evidence names each checkout,
  launcher/interpreter, old/new source revision and wheel SHA-256, stopped
  session/worker or scheduler, and restart disposition. Unknown writers remain
  an owner prerequisite; excluded installations stay disabled. Long-running
  processes restart under the verified installation before resumption.
- [ ] On fresh control, the documented resolved-interpreter installer changes
  only the five listed artifacts. A second invocation with the same wheel,
  before editorial changes, is a no-op. Shared/local configuration, including
  an explicit retention `0`, unrelated attributes, parked jobs, local forks,
  phone-home state and existing period state are preserved. Refusals are
  resolved with the owner rather than overwritten.
- [ ] Activation and cleanup reach control together in one reviewed PR merge:
  all five live/package pairs exist and match, `ticket.py` is executable,
  `rollout/trim-log/` is gone, and the `coga/.gitattributes` divergence exception
  and staging-only test/link fallbacks are gone. No earlier Coga sweep publishes
  the branch's recurring files. The runbook and seeded fixture describe the
  adopted layout, with no remaining operative staging instructions.
- [ ] Fresh control reports `coga/log.md: merge: unset` from
  `git check-attr merge -- coga/log.md`; the retire-worklist attribute remains
  unchanged. Read-only discovery finds `trim-log`, schedule `0 4 * * 1`,
  `scope: repo`, `run_when_inactive: true`, and workflow `trim-log/run`.
  Effective retention equals the recorded pre-adoption value (currently the
  implicit 30-day default); configuration bytes are unchanged.
- [ ] Packaging, installed-wheel adoption, scoped validation and the full
  workflow-required suite pass on the final reviewed tree, with exact commands,
  interpreter/platform, counts and head/base revisions recorded. Required PR
  checks pass; unavailable platform evidence is disclosed, not inferred from
  another interpreter. The merged revision is rechecked before resumption.
- [ ] The owner has the merged PR/revision, wheel receipts, verification and
  compatible recovery instructions, and records which writers/schedulers
  resumed or remain stopped. No live log/cursor rewrite, forced period,
  production trim or phone-home delivery is used as activation proof.

### Proposed shape

**Publication decision: one adoption-and-cleanup PR, using manual code steps.**
Do not publish installer output separately. A normal launched handoff on the
feature branch would sweep committed recurring files before the cleanup PR;
committing those files alone does not solve the problem. At `review-design`,
approve running `implement` and `peer-review` as manual/API sessions under
`coga/checkouts/manual`, outside a launch/megalaunch supervisor. Each session
starts and ends on current clean control and bumps only from control. Do not
change the frozen workflow or disable publication in config. If a future
runtime notice says launch prepared the branch, resolve that mismatch before
creating adoption files; do not override launch's return protocol mid-session.

1. **Approve and establish the maintenance window.** Recheck PR #1129 and
   control, refresh the blackboard inventory, and obtain the owner's answers
   below. Stop recurring launchers, ordinary launches, megalaunch/chat sessions,
   script workers and other publishers in every participating checkout. Keep
   schedulers, including autoclose, stopped through final verification; task
   status and this sandbox's process list do not establish quiescence. Upgrade
   each participating installation using its environment manager and the
   interpreter-resolution procedure. Retain old artifact/source evidence and
   record the reviewed compatible wheel hash and revision. The deployment
   controller must use a non-editable wheel, with no source-path override, so
   switching the repository branch cannot change its loaded implementation.
   Only freshly started, verified deployment/review controllers may perform
   the necessary workflow publications during this window, from clean control.
2. **Capture installer output on control without publishing it.** Following
   the manual checkout procedure, create/record the implementation branch and
   strictly publish that ticket linkage while still on clean `main`, before
   installing anything. Snapshot the five targets' prior existence, bytes and
   modes plus configuration and phone-home/period state. Run
   `"$COGA_PY" -m coga_edge.trim_log --install`, inspect the exact allowlist diff,
   effective attribute and preservation evidence, then repeat for idempotence.
   Save and byte/mode-verify the generated files and preimages outside both
   Coga roots. Restore only this operation's exact unpublished target changes
   to their preimages, removing only verified newly created targets; do not
   restore a whole tree or touch the log. Require clean current control again.
   Run no sweeping Coga command while these files are installed on control.
   This capture is preparation for the PR, not a published adoption.
3. **Build the combined branch.** Switch to the recorded feature branch,
   reapply the captured five artifacts, and perform the cleanup below. Stage
   exact paths and commit the entire bundle together; never include this task
   or `coga/log.md`. Run the required tests, freshen against main, verify all
   twins again and push. While this branch is checked out, use Git, tests and
   read-only inspection only: no Coga lifecycle/publication commands, launch,
   recurring sweep, or supervisor teardown. Preserve work and return to clean
   current `main` by the manual procedure before writing the blackboard and
   bumping. Keep controller notes outside swept roots until that return.
4. **Review and publish together.** The independent `peer-review` session
   follows the same manual isolation and return order, including any fixes,
   final rebase and tests. `open-pr` runs from control as usual, with the
   reviewed branch recorded on the ticket. Before every state handoff, verify
   that control still has its pre-adoption files and no activation dirt.
   Obtain owner review and merge the complete PR as one control update. This
   lands the new attribute with removal of its exception, and the live runbook
   with its packaged edit. Do not split these across a state publication and
   a later code merge. If control changes materially, preserve the bundle,
   reconcile and renew review/check evidence rather than overwrite it.
5. **Verify, then resume.** Refresh all participating checkouts to the reviewed
   compatible revision without discarding unique work. If repeating the
   installer after the runbook edit, first install the wheel built from that
   matching reviewed tree; an older installed resource will correctly refuse
   the new runbook. Record any replacement wheel's hash/revision per writer.
   Verify the published five pairs, attributes, discovery, retention and
   checks below. Restart only verified upgraded writers, then release the
   approved schedulers and record resumption. The first ordinary sweep may
   service the latest past Monday immediately: approval includes that normal
   behavior, not a promise to wait until the next Monday. Do not fabricate
   ledger state or force a run. Complete the owner-held final step only after
   merged-tree verification and the resumption record are available.

The cleanup edits are bounded:

- Delete the five staged files under `rollout/trim-log/` after their live
  replacements are in the same branch diff.
- In `tests/test_packaging.py`, remove only the `coga/.gitattributes` entry
  from `INTENTIONALLY_DIVERGENT_TWINS`, remove the trim-log staging fallback
  from `_context_link_problems`, and replace
  `test_staged_trim_log_rollout_matches_packaged_files` with an explicit
  five-artifact live/package existence and identity check. Keep generic twin,
  navigation and installed-wheel coverage. Explicit existence matters because
  generic twin discovery skips a missing non-context live counterpart.
- Replace the obsolete staging paragraph in the new live
  `coga/recurring/trim-log/operations.md` and its packaged twin. Keep the
  generic adoption/refusal/recovery instructions; describe the completed repo
  handoff without directing future operators to staging files. Apply the same
  editorial update to
  `tests/fixtures/seeded-repo/coga/recurring/trim-log/operations.md`.
- Search current code, runbooks, contexts and fixtures for remaining operative
  staging references, excluding `docs/archive/**`. Update affected canonical
  and packaged twins together. Historical notes in other task blackboards
  are evidence, not instructions to rewrite for this rollout.

### Verification and recovery

During implementation, run focused
`python -m pytest tests/test_packaging.py tests/test_trim_log.py tests/test_edge_distribution.py`,
then the workflow-required `python -m pytest` with the checkout's test
interpreter and absolute checkout `PYTHONPATH` where needed. Existing fixture
tests already exercise installed adoption, opt-out `0`, refusal and recovery;
production execution adds no required evidence. Check wheel packaging from a
pristine scratch clone as required by `coga-dev/packaging`; do not use that
test checkout as another production writer. Record final source and artifact
hashes, not just the distribution version.

Run `git diff --check`, scoped
`coga validate --task commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json`,
and fixture validation from `tests/fixtures/seeded-repo/coga` with
`SLACK_WEBHOOK_URL` unset. Use read-only `coga recurring list` and
`src/coga/recurring.py`, `Template.load`/`list_templates`, for template fields
and discoverability; there need not be a materialized period yet. Record the
actual scheduler timezone. Load configuration read-only through
`src/coga/config.py`, `load_config`, to compare effective retention and preserve
the original config bytes. Capture individual byte comparisons for all five
pairs, script mode, effective Git attribute, PR merge OID and check results.
Repeat the artifact/attribute/discovery checks on fresh merged control before
resuming; do not re-run the full suite solely because the PR merged unless
the tested tree changed.

Before publication, a refusal or interrupted installer capture leaves writers
stopped. Preserve generated files and preimages, inspect any partial writes,
and restore only verified operation-owned edits or seek owner resolution;
the install loop is not a crash-atomic five-file transaction. Abort/defer the
unmerged branch while retaining its work. After publication, stop affected
writers again and use a reviewed forward repair or compatible wheel/repo pair.
Do not restore the old union attribute or downgrade to a pre-retention writer
as a shortcut, and never roll back audit history, cursor identity/counters or
lifecycle state. Retained trim receipts and native Git conflicts use the
runbook's recovery sections; do not delete receipts or replay transitions.

### Out of scope

Retention-policy/algorithm changes, core installer/publication redesign,
configuration edits, other repositories, migration of unreviewed forks,
cleanup of unrelated clones/tasks, changing the CI cadence, manual log/cursor
rewrites and production maintenance/delivery tests. This design step writes
only the ticket; it does not install a wheel, stop a writer, enable files,
create a branch, or open a PR.

## Context

### Rollout plan and prerequisite

[PR #1129](https://github.com/FastJVM/coga/pull/1129) merged at
2026-10-28T22:57:03Z as `42d1b30a47e30bb642f9e610d950681acdacd595`.
That commit is an ancestor of design-time `origin/main`
`1f67e8ad65e300b95313f5be1561b1b3641dd950`; the remote feature branch has been
deleted. Inspect current control for the references below and recheck ancestry
and content before adoption. The source ticket's lifecycle status is separate
from merge evidence; this ticket does not close it.

The blackboard records a partial local inventory, not authorization or proof
of quiescence. The owner resolves external visibility and maintenance choices
at `review-design`; unavailable answers do not prevent this planning step.
Implementation cannot start the rollout with those answers outstanding.
Read `coga/checkouts/manual` (`docs/contexts/coga/checkouts/manual/SKILL.md`),
"Procedure" and "Publish pre-branch ticket edits", for the manual code-step
handoffs selected above. This topic is cited rather than attached.

### Runbook and installer

Required read: `coga/recurring/trim-log/operations.md`, "Adoption after the
compatible wheel upgrade" and recovery sections; before adoption it lives at
`rollout/trim-log/coga/recurring/trim-log/operations.md`. Resolve `COGA_PY` using
`docs/contexts/coga/edge-code/edge-code-upgrades.md`, `migration:interpreter`,
preserving the launcher's interpreter environment. On fresh control, run
`"$COGA_PY" -m coga_edge.trim_log --install`; review these five possible edits:

- `coga/recurring/trim-log/ticket.md`
- `coga/recurring/trim-log/ticket.py`
- `coga/recurring/trim-log/operations.md`
- `coga/workflows/trim-log/run.md`
- `coga/.gitattributes`

`src/coga_edge/trim_log.py`, `install` and `_attribute_plan`, own the bounded
installer. `main` routes exact `--install` directly to `install`, bypassing
`run_reported` and the maintenance/bump path. `install` reads the four resource
files with `src/coga/paths.py`, `packaged_template_path`, checks all planned
targets and calls `_attribute_plan` before writing; `_attribute_plan` checks
the effective proposed rule with a temporary Git index. Thus the running
wheel's resources, not an arbitrary source checkout, define idempotence.
`src/coga_edge/trim_log.py`, `_phone_compatible`, checks installed/frozen
phone-home shims during maintenance, not installation: a successful installer
does not prove that a custom phone-home fork is ready.

### Publication, cleanup and proof

Coordinate adoption with removal of `rollout/trim-log/` and the
`coga/.gitattributes` exception in `tests/test_packaging.py`,
`INTENTIONALLY_DIVERGENT_TWINS`: installation makes that exception invalid
immediately, so publishing adoption first would break packaging checks.
Design must resolve this ordering before owner approval. Remove obsolete
staging assertions/fallbacks while retaining live/package coverage, and update
the runbook's staging paragraph and remaining staging references with their
packaged twins under `src/coga/resources/templates/coga/`.

Verify installer idempotence before editorial runbook cleanup, or upgrade to
the matching reviewed wheel before repeating it: `trim_log.install` compares
against its installed package, not this source tree. Verify the five published
twins, `git check-attr merge -- coga/log.md` reports `unset`, and the Monday
04:00 local-time schedule and preserved retention setting are discoverable.
Record writer/resumption evidence, published revisions, packaging checks,
scoped Coga validation and workflow-required tests; production trimming is
not required.

`coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`) is cited
rather than attached: read "Canonical copies and twins". Its mapping and
exception rules are enforced by `tests/test_packaging.py`,
`_discover_live_packaged_twins` and
`test_intentional_divergences_stay_real_and_explained`.
The former only adds existing live counterparts; the latter rejects an
exception as soon as its live bytes equal the package. This is why the bundle
needs both explicit live-file coverage and one publication boundary.
`coga/state-publication` (`docs/contexts/coga/state-publication/SKILL.md`) is
cited rather than attached: read "When Coga publishes", "Control versus
feature checkouts" and "Strict publication on demand". Dirty Coga files and
eligible committed recurring state can publish ahead of a PR; a feature
branch alone does not prevent activation.

`coga/recurring/scheduling`
(`docs/contexts/coga/recurring/scheduling/SKILL.md`) is cited rather than
attached: read "Periods and the serviced-period ledger" for retroactive first
firing. `src/coga/commands/recurring.py`, `list_recurring`, calls
`src/coga/recurring.py`, `list_templates`, for a read-only view; it does not
call the creating/launching sweep. `src/coga/config.py`, `load_config`, uses
`_parse_log` to supply 30 when shared `[log]` is absent and preserves `0`.

`coga-dev/testing` (`docs/contexts/coga-dev/testing/SKILL.md`) is cited rather
than attached: read "Which code you are actually testing" and "CI posture and
receipts". The documented Test workflow is paused; local workflow checks
remain required, and this rollout does not authorize re-enabling CI. Recheck
actual PR requirements at publication. `tests/test_trim_log.py`,
`test_install_idempotence_and_exact_allowlist` and
`test_install_validates_all_files_before_writing`, cover the installer plan.
`tests/test_edge_distribution.py`,
`test_installed_trim_log_adoption_and_headless_period`, tests installed
resources and opt-out preservation in isolated fixtures, and
`test_documented_trim_adoption_uses_resolved_interpreter` exercises the
documented command. Keep these relationships intact during cleanup.

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

## Design handoff

2026-10-28 local / 2026-10-29 UTC — Codex design investigation. No branch,
code, installation, live activation or PR created. The spec selects one merged
adoption/cleanup bundle and manual code-step returns to control so no feature
handoff sweeps recurring files early. Owner approval is still pending.

Evidence at `1f67e8ad65e300b95313f5be1561b1b3641dd950`:

- Started clean on `main`; fetched and fast-forward checked `origin/main`.
  GitHub and ancestry confirm PR #1129 merged as
  `42d1b30a47e30bb642f9e610d950681acdacd595`. Its former branch is absent
  remotely. `v1/39-trim-the-audit-log` still records `in_progress`, step 7
  (`review`); no lifecycle correction performed for that other task.
- All five staged files byte-match the package. Live trim-log template,
  workflow, parked template and period are absent. The effective live log
  merge attribute is `union`. Shared `[log]` is absent; `load_config` returns
  retention 30. No config edit is needed.
- Live phone-home `ticket.py` is the stock packaged shim; no `_phone-home`
  parent or frozen phone-home period script was found in this checkout.
  State was not changed. Re-inventory at the maintenance window.

## Writer inventory — partial, requires owner confirmation

| Checkout / installation | Observed revision and state | Rollout disposition |
| --- | --- | --- |
| `/home/n/Code/coga` | Clean `main`, `1f67e8ad65e300b95313f5be1561b1b3641dd950`; sole registered worktree | Proposed deployment control; recheck before use. |
| `/home/n/.local/bin/coga` | Direct shebang `/home/n/.local/share/uv/tools/coga/bin/python`; metadata 0.4.1, editable import from `/home/n/Code/coga/src` | Actual current CLI. A fresh import sees retention; this does not prove the existing supervisor has reloaded it. Replace with verified compatible non-editable wheel for deployment. |
| `/home/n/Code/coga/.venv/bin/python` | Metadata 0.4.1, editable primary source | Test environment; owner must confirm whether it also launches writers. |
| `/home/n/Code/codex/coga` and `.venv/bin/python` | Clean `main`, `638478541ff4bc0d7264f7a7d71897463875148d`; metadata 0.3.2, editable local source | Potential writer; no upgrade/resumption proof. |
| `/home/n/Code/claude/coga` and `.venv/bin/python` | Clean `main`, `9c4e73e6c1de8733aa176fdfbeae7aca0b72a58e`; metadata 0.4.1, editable local source | Potential writer; version is not compatibility proof. |
| `/home/n/Code/claude/.dream-retro-20261026T172253Z/dream-ops` | Linked to the Claude clone; branch `dream/ops-20261026T172253Z`, `2796d89b0e208ce10c35584489510fd846608d37`; dirty `coga/log.md` and `coga/tasks/recurring/dream/ticket.md` | Occupied/retained state: owner must identify the session and preserve/reconcile its writes before upgrade. Left untouched. |
| `/home/n/Code/coga/.coga/worktrees/build-week-readme.IcnXYp` | Independent same-origin clone; clean `agent/build-week-readme`, `8a0d6ece3a091dbda35b42997b8005eab5a27f10`; no checkout venv found | Potential old writer; confirm exclusion or upgrade, do not delete. |

The prompt identifies a live megalaunch session. `/proc` inspection exposed
only this sandbox's process namespace, not a trustworthy host-wide session or
worker inventory. No Coga references were found in readable user systemd units
or `/etc/cron.{d,hourly,daily}`; user crontab access was denied. Broader local
discovery also had unreadable unrelated paths. No absence claim covers cron,
other users, remote hosts, CI, agent-app schedulers or additional clones.
This environment reports PST/PDT with no `TZ` override; confirm the actual
sweeper's timezone independently. No reviewed wheel artifact/hash has been
selected or installed by this step.

## Open Questions

For the owner at `review-design`, before any rollout work:

1. Which of the listed clones/interpreters still publish, who owns the dirty
   Retro checkout, and what other hosts, users, launchers, timers or CI can
   write this repository? Confirm each writer as upgraded-and-participating
   or explicitly stopped/excluded, including the current megalaunch.
2. Approve the single-PR publication order and manual/API `implement` and
   `peer-review` sessions, with no supervisor or sweeping command on the
   adoption branch. Name the deployment controller and a maintenance window
   that keeps schedulers stopped through review, merge and final checks.
3. Which reviewed wheel artifact(s)/source revisions and SHA-256 receipts
   will be used for every participating environment, and who can replace
   those installations and restart their sessions? Preserve a compatible
   recovery pair; the observed editable versions are not upgrade receipts.
4. Approve the resumption order and normal first-sweep catch-up, confirm the
   sweeper timezone, and identify who verifies the merged tree before
   releasing schedulers and final task completion. Existing retention,
   including any opt-out found during recheck, remains unchanged.

## Verification

- `coga validate --task commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json`
  passed: one valid task, no fixes or issues.
- `git diff --check` passed. A direct `compose_prompt_report` check under
  `/home/n/.local/share/uv/tools/coga/bin/python` confirmed all spec subsections
  and owner questions compose, the body has only Description/Context level-two
  sections, the sole blackboard fence is intact, and frontmatter and the ticket
  guide are byte-unchanged. Source citations use symbols rather than line numbers.
- Final `git fetch origin main` found no intervening commits: HEAD and
  `origin/main` are both `1f67e8ad65e300b95313f5be1561b1b3641dd950`; only this
  ticket has local edits. No code tests or production maintenance were run for
  this design-only change. Implementation checks above are requirements, not
  claimed results. Next workflow step: independent `evaluate-design`, then
  the owner resolves Open Questions at `review-design`.
