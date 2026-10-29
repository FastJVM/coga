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
step: 3 (open-pr)
agent: claude
launch_generation: pending:da861d48-e1b6-47ae-8601-25cd52149361
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

## Implement handoff — 2026-10-29

Actual implementer: Codex. Pushed `codex/v1-33-doc-acceptance` at
`bd72b19d2a13972005285252b53df7504350bbc7`, based on fetched main
`381f8206a230d99fc042750ce21fc5609ad47cdb`. Two docs-only commits; no runtime,
fixture, config, or workflow edits. Returned this checkout to clean current
`main` before writing the handoff. No PR opened and no owner acceptance claimed.

Changes: README distinguishes Git/agent authentication from optional tools,
shows new-repo creation and Git identity, explains clone setup, gives explicit
Codex entry commands, states PR/peer requirements, and links uninstall.
First-task/configuration explain the single-agent alternative and interviewer
selection. Init's clone install-offer ordering now matches source. README and
install distinguish PyPI's native Windows import failure from development's
agent-session refusal. A working Windows first-task path cannot yet be promised.

The link audit found trim-log guidance pointing to absent live files. Corrected
all 11 occurrences in 10 canonical topics to the existing packaged ticket and
runbook, including their user-topic twins. This changes navigation only; it
does not activate the pending retention rollout. All other edited user topics
also match their packaged twins. Coga-dev remains local-only.

### Candidate and verification receipts

- Candidate: `bd72b19d2a13972005285252b53df7504350bbc7`.
- Pristine verification clone: `/tmp/coga-v1-33-candidate`, clean before and
  after the wheel build; no linked worktree. Wheel:
  `coga-0.4.1-py3-none-any.whl`, SHA256
  `bccf26b653fe092d05ae04b592e5ef896cabcc548bcbcaff89b480e4db5bae08`.
  This unreleased candidate shares the 0.4.1 version label with PyPI; the hash
  and commit distinguish them. It was not uploaded.
- README SHA256:
  `06d489a6c03e90462009bdb9f4083de6c871ad44c77816c21b9824654a239914`.
  `[project].readme` still selects `README.md`; wheel METADATA description is
  byte-identical UTF-8 and `Description-Content-Type: text/markdown`. All six
  reviewed user topics match their installed wheel resources.
- Fully reviewed: `README.md`, `docs/README.md`, and `docs/contexts/coga/`
  `{install,init,first-task,launch,configuration,uninstall}/SKILL.md`.
  Narrow navigation checks additionally cover architecture, edge-code,
  prompt-composition, script-tickets, state-publication, usage, and
  coga-dev/internals/spool-merge. No context restructuring or archive content
  review occurred.
- Source checks: init `_repo_is_empty`, `_offer_agent_cli`,
  `_setup_initialized_clone`; dependency/agent install manifests;
  launch `agent_sessions_supported`/preflight/chaining; create/ticket/validate
  options; configuration allowlists/default routing; uninstall plan, backup,
  and installer selection; shipped code workflows and annotated config.
- Environment: Linux x86_64, Python 3.12.12, Git 2.43.0, uv 0.13.6.
  No fresh Python 3.11/macOS/Windows execution and no authenticated agent run.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_packaging.py`
  — **31 passed** after the final navigation changes. Full suite omitted for
  this docs-only diff.
- In the pristine clone:
  `/home/n/Code/coga/.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/coga-v1-33-evidence/dist .`
  — built the wheel above.
- `/tmp/coga-v1-33-render-env/bin/python -m twine check --strict /tmp/coga-v1-33-evidence/dist/coga-0.4.1-py3-none-any.whl`
  — passed. `readme_renderer` 46.0 rendered the wheel description without warnings.
- `/tmp/coga-v1-33-render-env/bin/python /tmp/coga-v1-33-evidence/check_docs.py /tmp/coga-v1-33-candidate /tmp/coga-v1-33-evidence/dist/coga-0.4.1-py3-none-any.whl`
  — 177 link occurrences checked across the eight full-review pages;
  162 candidate-local targets exist, 13 local fragments resolve, all 24 README
  URLs are HTTPS, and all 32 distinct HTTP targets returned 200. The external
  Thinkpick pause anchor also resolves. Five archive paths in the docs index
  were checked for existence only; no archive contents read.
- `/tmp/coga-v1-33-render-env/bin/python /tmp/coga-v1-33-evidence/check_commands.py`
  — 39 expected command exits using the installed candidate. Checked version,
  documented built-in help, init/validate/status in new and populated repos,
  create/show/task validation, composition via the read-only Python API,
  initialized-clone setup without a commit, and uninstall preserving the
  disposable project's file. New repo seeds onboarding; populated repo does
  not. No nested launch, authentication, remote PR, or global purge executed.
- `/tmp/coga-v1-33-render-env/bin/python /tmp/coga-v1-33-evidence/render_docs.py`
  — live [candidate GitHub README](https://github.com/FastJVM/coga/blob/bd72b19d2a13972005285252b53df7504350bbc7/README.md)
  and local PyPI-renderer output checked at 1280×1000 and 390×1100. Inspected
  screenshots of prerequisites and init; text wraps, code scrolls within its
  block, and neither article overflows horizontally. Both DOMs retain 24
  destination links plus eight heading permalinks. The PyPI preview uses local
  styling, not a claim about the live PyPI page. Ticket 43 owns that release check.
- Scoped `coga validate --task v1/33-review-all-doc --json` — one valid task,
  no issues; `git diff --check origin/main...HEAD` — passed before returning.

Scripts, command outputs, HTML, screenshots, JSON receipts, and both wheels
are retained locally in `.coga/v1-33-doc-audit/20261029/` (ignored). The commands
above name their original `/tmp/coga-v1-33-evidence/` execution paths.

### Platform evidence and acceptance gates

| Claim / gate | Actual evidence and disposition |
| --- | --- |
| macOS prerequisite/install route | Ticket 29's `macos-walk-findings.md`, October 17, fresh macOS 26.6.2 arm64 and PyPI 0.4.0: five-line route reached `coga build`. No completed first-task receipt, exact wheel hash, or reliable Python receipt for that final walk; PR #1043 closed unmerged. Reuse its friction findings, not a candidate pass. Ticket 30 must supply current authenticated proof. |
| Linux/macOS × PyPI/main × both agents | `v1/30-complete-the-authenticated-clean-install-audit`: October 28 access check explicitly records no runs, despite approval of eight required completions. Still needs the owned Mac SSH target via `v1/28-affordable-macos-testing-on-owned-macs-and-per-min`; no AWS spend authorized. The old 0.2.0/0.3.2 login-blocked matrix and 0.4.0 smoke are not passes for this candidate. |
| Native Windows | `v1/14-interactive-coga-launch-on-native-windows` remains at owner review-design; candidate `launch.agent_sessions_supported` refuses native agent sessions. `v1/31-test-install-on-windows` has no attended walk receipt. The port must land, then that owner must test an identified unmodified candidate through `done`; documentation must be refreshed with it. |
| PyPI versus candidate | Read public PyPI metadata and downloaded unmodified 0.4.1 wheel (uploaded October 21), SHA256 `7e2a2cd1c22068e8dc789b8d6dbd64a8dd9dd22310d40bc559f251d329a8ae9c`. Its eager `fcntl` import remains; source/core-port progress cannot be presented as published Windows support. This was artifact inspection, not a native execution receipt. |
| README checks already owned by 32 | API confirms PR #1119 merged October 28 as `e38c1814fded1c80123e1610398bd66143d16d96`; that commit is included and ticket 32 is now done. Reused its demo verdict and pinned examples. Later main commits deliberately revised Thinkpick and removed batch-process details (`ce2e91d54`); preserved that direction instead of resurrecting its former megalaunch section. Current demo-removal rationale remains in coga-dev/current-direction. |
| Remaining installation owners | `v1/19-install-link-for-claude-code-yields-the-desktop-ap` still owns the stale CLI dependency URL/installer behavior; this branch fixes only the README/topic links. `v1/26-make-the-readme-install-section-the-only-install-p` still owns retiring/re-homing the install reference; its removal has not landed. `v1/27-link-uninstall-from-the-readme` can verify its README requirement on this branch after merge. Existing installer choices/fixes are not silently declared finished. |

Vendor CLI/login URLs were opened against current official Claude Code and
OpenAI documentation; uv's installer syntax was checked against Astral's
installation page. These source/link checks do not substitute for the owned
fresh-machine walks. Relevant code and installer behavior changed since the
old walk receipts, so tickets 30/31 must rerun against the eventual release
candidate. Their existing tickets receive this routing, not duplicate tasks.

**Acceptance: pending.** Peer review and PR publication are next. Missing
platform receipts and unfinished Windows/install work prevent v1 acceptance.
Do not merge/close as release-ready or hand an accepted record to
`v1/43-publish-coga-1-0-as-the-final-v1-step` until nicktoper explicitly accepts
the identified candidate and its completed evidence at the owner-held gate.
Broader context splitting, cosmetic prose cleanup, and a new demo stay deferred.

## Peer review

Completed direct Codex review on 2026-10-29. **No must-fix findings and no
content edits.** Both the implementation handoff and this session identify
Codex as the actual agent; this is **self-review**, despite the configured
Claude main agent and the peer-review step. No separate reviewer was invoked
and no review remains in flight.

Reviewed and pushed head: `45a5636ec810411996b6007bad90cd4b59ac0255`.
Reviewed diff base: `66431d634fddc327bc463099a67320790200220f`.
The checkout started clean on current main. No PR existed for the recorded
branch. Rebased both implementation commits onto fetched main; `git range-diff`
confirms both patches are unchanged. Intervening main changes were task/log
state only. Pushed with an explicit lease against the prior remote head,
then returned to clean, current main before writing this handoff.

Review covered the full README, docs index, and install, init, first-task,
launch, configuration and uninstall topics, plus every changed paragraph in
the seven additional navigation topics and all ten packaged user-topic twins.
Checked the load-bearing claims against init's empty-repo detector, agent
offers and clone setup, authoring and launch routing, shipped workflows and
config, dependency manifests, and uninstall behavior. The broader trim-log
changes repair links to the shipped contract/runbook without enabling a repo
schedule or changing retention behavior. No runtime, fixture, config or
workflow files are in the feature diff.

Read the actual ticket 29 Mac receipt, ticket 30's October 28 access check,
ticket 31's absent walk evidence, ticket 14's remaining owner design gate,
and ticket 32's checks/demo verdict. GitHub confirms PR #1119 merged as
`e38c1814fded1c80123e1610398bd66143d16d96`, which is an ancestor of this
candidate. The old demo decision and later main's Thinkpick direction remain
intact. The public 0.4.1 wheel still imports `fcntl` eagerly in launch and
related modules; the candidate's native Windows agent refusal remains in
source. These are artifact/source checks, not Windows execution.

Verification on Linux/Python 3.12.12:

- Required packaging checks: **31 passed in 6.80s**. Full pytest omitted for
  the prose-only diff; the ticket specifically requires the packaging checks.
- A new pristine clone at `/tmp/coga-v1-33-peer-candidate` built
  `coga-0.4.1-py3-none-any.whl`, SHA256
  `bccf26b653fe092d05ae04b592e5ef896cabcc548bcbcaff89b480e4db5bae08`,
  with a clean tree before and after. It is byte-identical to the implement
  artifact. All ten changed user topics equal their source and wheel twins;
  no Coga-dev context ships.
- README SHA256 remains
  `06d489a6c03e90462009bdb9f4083de6c871ad44c77816c21b9824654a239914`.
  `[project].readme`, UTF-8 description bytes and `text/markdown` metadata
  agree. Strict Twine validation and warning-free `readme_renderer` rendering
  passed for the rebuilt wheel.
- Extended the link check to **15 pages / 251 link occurrences**: 236 local
  targets exist, 19 local anchors resolve, all 24 README destinations are
  HTTPS, and all 37 distinct HTTP targets returned 200. The external Thinkpick
  pause anchor resolves. The five docs-index archive targets were checked for
  existence only; no archive contents were read.
- Inspected the saved GitHub desktop/mobile and PyPI-renderer desktop/mobile
  screenshots of prerequisites and init. Text wraps and code stays in its
  scroll area. Those captures and the 39 successful command receipts belong
  to the original implementation head; verified identical README and wheel
  bytes instead of claiming a fresh browser capture or command walk. The
  GitHub capture is live-site evidence; the styled PyPI preview is not a
  live PyPI page. Original head/base are retained in the PR receipts.
- Scoped task validation: one valid task, no issues. Whitespace check passed.

New scripts, HTML, link results, artifact comparison and wheel are retained
in `.coga/v1-33-doc-audit/peer-review-20261029/` (ignored), with original
execution paths under `/tmp/coga-v1-33-peer-evidence/`. Earlier command and
rendering evidence remains under the implementation evidence directory above.

**Next: open-pr. Advisory review depth: deep.** Documentation review passed;
final first-user documentation acceptance has not. The existing installer
owners and `v1/14-interactive-coga-launch-on-native-windows`,
`v1/30-complete-the-authenticated-clean-install-audit`, and
`v1/31-test-install-on-windows` still own their missing fixes/receipts.
Refresh the documentation against the eventual tested candidate, then obtain
nicktoper's explicit acceptance at the owner-held review gate. Do not merge,
close, or give ticket 43 an accepted release record on this review alone.
No fresh platform walk, authenticated agent session, PR publication, or owner
acceptance occurred in this step.

The read-only PR formatter accepted the preparation below as
`[deep · A:codex R:codex(self)]`, with all 22 diff paths covered and current
review/check head/base values. Only the two deliberately retained original
command/rendering receipts display as historical. Scoped validation also
passed after this handoff; ticket intent and lifecycle frontmatter are unchanged.

## PR

```yaml
title: Clarify first-user setup and repair documentation links
author: codex
author_evidence: >-
  The implementation handoff identifies Codex as the actual implementer despite
  the configured Claude main agent. This Codex review made no content edits.
head: 45a5636ec810411996b6007bad90cd4b59ac0255
base: 66431d634fddc327bc463099a67320790200220f
depth: deep
rationale: >-
  The documentation diff has no must-fix findings, and packaging, metadata and
  links pass. Inspect the current platform limits and pending acceptance gates:
  native Windows agent work and authenticated first-task evidence are unfinished.
  Both sessions used Codex, so this is self-review. The original command and
  screenshot receipts remain historical, with identical artifact bytes verified.
implementation: >-
  Clarifies Git and agent prerequisites, new-repo and initialized-clone setup,
  explicit Codex entry commands, single-agent versus peer-review workflows,
  optional GitHub/1Password tools, and uninstall navigation. Distinguishes PyPI
  0.4.1's native Windows import failure from the candidate's agent-session
  refusal. Repairs trim-log links to existing packaged guidance and synchronizes
  every changed user topic with its packaged twin.
deviations: >-
  Documentation work can proceed before the owned platform walks, but this is
  not final release acceptance. The install reference remains until ticket 26
  retires and re-homes it. The link audit expanded only to repair navigation
  into the shipped trim-log ticket/runbook; no retention rollout was activated.
limitations: >-
  No fresh Python 3.11, macOS, native Windows, or authenticated first-task run.
  Ticket 30 still lacks its eight approved completions and ticket 31 lacks its
  attended Windows receipt after ticket 14 lands. Existing installer fixes and
  nicktoper's explicit acceptance remain required before merge/closure. Visual
  review used saved GitHub and locally styled PyPI-renderer screenshots of the
  byte-identical README; no new browser capture or live PyPI publication check.
  Ticket 43 owns the latter after release. No independent agent review occurred.
files:
  README.md: Clarify prerequisites, setup paths, agent choice, platform limits and uninstall.
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: Repair the trim-log operations link; keep this development topic local-only.
  docs/contexts/coga/architecture/SKILL.md: Point retention navigation to the shipped ticket.
  docs/contexts/coga/configuration/SKILL.md: Explain default-agent versus interviewer selection and repair retention links.
  docs/contexts/coga/edge-code/SKILL.md: Repair navigation to the shipped retention adoption runbook.
  docs/contexts/coga/first-task/SKILL.md: Explain PR readiness, one-agent versus peer review, agent choice and actual completion.
  docs/contexts/coga/init/SKILL.md: Correct clone install-offer ordering and repair the retention adoption link.
  docs/contexts/coga/install/SKILL.md: Clarify artifact/platform limits, authentication, Python prerequisites and verification scope.
  docs/contexts/coga/prompt-composition/SKILL.md: Repair the retention ticket link.
  docs/contexts/coga/script-tickets/SKILL.md: Repair the trim-log recovery runbook link.
  docs/contexts/coga/state-publication/SKILL.md: Repair the trim-log recovery runbook link.
  docs/contexts/coga/usage/SKILL.md: Repair navigation to the retention ticket.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Keep the shipped fallback byte-identical to its canonical topic.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 45a5636ec810411996b6007bad90cd4b59ac0255
  base: 66431d634fddc327bc463099a67320790200220f
  detail: >-
    Direct review completed on 2026-10-29 with no must-fix findings and no
    content edits. Reviewed all changed Markdown, required user topics,
    load-bearing source/contracts, actual platform receipts, navigation and
    packaged twins. No review tool remains in flight. Final release acceptance
    remains pending; this review does not supply the missing platform evidence.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_packaging.py
    status: passed
    head: 45a5636ec810411996b6007bad90cd4b59ac0255
    base: 66431d634fddc327bc463099a67320790200220f
    detail: 31 passed in 6.80s on Linux/Python 3.12.12; the ticket explicitly requires these packaging checks.
  - command: /home/n/Code/coga/.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/coga-v1-33-peer-evidence/dist .
    status: passed
    head: 45a5636ec810411996b6007bad90cd4b59ac0255
    base: 66431d634fddc327bc463099a67320790200220f
    detail: >-
      Built in pristine /tmp/coga-v1-33-peer-candidate, clean before and after.
      coga-0.4.1-py3-none-any.whl SHA256
      bccf26b653fe092d05ae04b592e5ef896cabcc548bcbcaff89b480e4db5bae08 is
      byte-identical to the implement artifact. No upload.
  - command: /tmp/coga-v1-33-render-env/bin/python -m twine check --strict /tmp/coga-v1-33-peer-evidence/dist/coga-0.4.1-py3-none-any.whl
    status: passed
    head: 45a5636ec810411996b6007bad90cd4b59ac0255
    base: 66431d634fddc327bc463099a67320790200220f
    detail: Strict distribution-description validation passed.
  - command: /tmp/coga-v1-33-render-env/bin/python /tmp/coga-v1-33-peer-evidence/check_docs.py /tmp/coga-v1-33-peer-candidate /tmp/coga-v1-33-peer-evidence/dist/coga-0.4.1-py3-none-any.whl
    status: passed
    head: 45a5636ec810411996b6007bad90cd4b59ac0255
    base: 66431d634fddc327bc463099a67320790200220f
    detail: >-
      251 link occurrences across 15 pages; 236 local targets and 19 local
      anchors resolve, 37 HTTP targets return 200, and the Thinkpick pause
      anchor resolves. All 24 README destinations are HTTPS. Five archive
      targets checked for existence only. Wheel description equals README,
      uses text/markdown and renders without warnings; all reviewed user
      topics equal wheel resources. All ten changed topic twins also match
      and no Coga-dev topic ships. README SHA256
      06d489a6c03e90462009bdb9f4083de6c871ad44c77816c21b9824654a239914.
  - command: git range-diff 381f8206a230d99fc042750ce21fc5609ad47cdb..bd72b19d2a13972005285252b53df7504350bbc7 origin/main..HEAD
    status: passed
    head: 45a5636ec810411996b6007bad90cd4b59ac0255
    base: 66431d634fddc327bc463099a67320790200220f
    detail: Both implementation patches are unchanged after rebase; main added task/log state only.
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/33-review-all-doc --json
    status: passed
    head: 45a5636ec810411996b6007bad90cd4b59ac0255
    base: 66431d634fddc327bc463099a67320790200220f
    detail: One valid task, no fixes or issues, on the reviewed feature checkout.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 45a5636ec810411996b6007bad90cd4b59ac0255
    base: 66431d634fddc327bc463099a67320790200220f
    detail: Passed after final fetch before pushing the rebased branch.
  - command: /tmp/coga-v1-33-render-env/bin/python /tmp/coga-v1-33-evidence/check_commands.py
    status: passed
    head: bd72b19d2a13972005285252b53df7504350bbc7
    base: 381f8206a230d99fc042750ce21fc5609ad47cdb
    detail: >-
      Historical implement receipt inspected during review, not rerun or
      re-stamped. All 39 recorded commands exited as expected: help, version,
      new/populated init, validation, task creation, read-only composition,
      clone setup without a commit and disposable-repo uninstall. The new
      wheel is byte-identical. No authenticated agent task was run.
  - command: /tmp/coga-v1-33-render-env/bin/python /tmp/coga-v1-33-evidence/render_docs.py
    status: passed
    head: bd72b19d2a13972005285252b53df7504350bbc7
    base: 381f8206a230d99fc042750ce21fc5609ad47cdb
    detail: >-
      Historical captures at 1280x1000 and 390x1100. Reviewer inspected saved
      prerequisites/init screenshots from live GitHub and local PyPI-renderer
      output: readable wrapping and contained code blocks. The current README
      bytes are identical. No fresh browser capture or live PyPI check claimed.
  - command: python -m pytest
    status: not-run
    detail: Pure prose/navigation diff with no runtime code or fixture edits; required packaging checks ran separately.
```
