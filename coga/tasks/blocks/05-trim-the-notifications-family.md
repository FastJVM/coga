---
title: 05 Trim the notifications family
status: in_progress
owner: nicktoper
contexts:
- coga/knowledge
- coga-dev/packaging
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

Apply the audit verdicts to coga/notifications, notifications/producers and important; split notifications/failures into a user summary and a coga-dev internals page. See `coga/tasks/blocks/README.md`.

## Context

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

### Scope and acceptance

Read `coga/tasks/blocks/README.md` first: it holds the test, the rules every
ticket in this group follows, and the audit rows for these topics. The audit
verdicts are recommendations; re-check each against current main and record
any disagreement on the blackboard for the owner before departing from it.

Done when: the notifications rows in the README table are applied, `notifications/failures` is split and deleted, and Slack configuration is documented once (the shipped `coga.toml`); both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `notifications/producers` stays a user topic: `workflows/blocker-reminders/run.md`
  and `bootstrap/skills/coga/blockers/remind/SKILL.md` cite it.
- New coga-dev page: `internals/notifications` (failures internals, caller
  columns, message format, accounting rule, "Adding a notifying command").
- Repoint links to `notifications/failures` from `sync`, `important`,
  `notifications`, `producers`.


<!-- coga:blackboard -->

## Dev

branch: coga/blocks-05-trim-the-notifications-family

## Implementation

Claude Code / Claude Opus 5.5 implemented the audit in `db0ef105b` (rebased
to `78f581157`). The notifications, producers and important topics are
trimmed; failures is split into the user summary and local internals; Slack
configuration lives in shipped TOML comments. The new internals topic is
indexed and the deleted topic's registration and non-ticket links are removed.
No disagreement with the audit. The repo-specific usage-report exception and
its rationale remain in the local developer topic.

## Peer review

**Direct review completed** by Codex in this fresh peer session, independently
of Claude's implementation. The complete final diff covers head
`b5668d59a8800e676e420761ac7a43931a1a145c` against base `13b702f1770b7b47c5bdbdd74cfb8589346bb891`.
The branch was unconditionally rebased onto fetched main before review;
the final freshness fetch found no further movement. Codex applied the fixes
in `b5668d59a`, then re-read the final diff and self-checked those corrections.
No nested reviewer CLI or subagent ran.

Fixed findings:

- The condensed failure section overstated preflight coverage and lost the
  explicit-send failure outcome. It now distinguishes `coga slack` exit 1,
  best-effort announcements after writes, and the named pre-write gates;
  it notes the log exception through the producer inventory.
- Repointing sync's numbered developer procedure made a shipped instruction
  require an unshipped topic. The procedure now lives in
  `coga-dev/patterns#sync-for-new-commands`; sync keeps optional navigation.
  This pulls forward that one passage from the blocks/06 audit scope.
- Completed the configuration-owner cleanup by removing the remaining
  owner-map setup duplication; kept the `pinging-the-owner` anchor and the
  repo-specific report decision's rationale.

The original implementation and the fixes were checked against notification
dispatch, Slack failure/redaction code, preflight callers, config parsing,
and validate probing. No remaining change-specific finding. No live Slack or
TTY exercise was applicable because this diff changes documentation/comments
and the packaging registry, not rendered messages or interactive behavior.

Verification on the final head (Python 3.12.12):

- `.venv/bin/python -m pytest -q`: **3 failed, 3952 passed, 7 skipped in 356.79s (0:05:56)**.
  Failures are `test_live_and_packaged_copies_stay_identical`,
  `test_context_distribution_is_complete`, and
  `test_context_navigation_has_no_broken_links` in `tests/test_packaging.py`.
- `coga validate --json`: exit 0, 151 checks OK, **0 errors / 47 warnings**.
- `.venv/bin/python /tmp/coga-blocks05-doc-audit.py`: four touched twin pairs
  identical, both failures copies deleted, no notification link errors across
  361 non-archive/non-task Markdown sources, no new global navigation or
  distribution errors, no prohibited shipped developer refs, and identical
  parsed TOML settings. Old task prose/audit mentions were inspected and kept
  under the group's old-ticket exception.
- `git diff --check main...HEAD`: passed.
- An unchanged detached main clone at `13b702f1770b7b47c5bdbdd74cfb8589346bb891` reproduces all three
  packaging failures (3 failed in 8.59s; exact command in the PR receipts).
  Remaining drift is 14 unrelated twin pairs plus the coga/code package,
  required-context entry, and three dangling links. Open PR #1081 contains
  those repairs. Baseline log: `/tmp/coga-blocks05-main-packaging.log`.

The reviewed branch is committed and pushed, but the required suite is not
green. **Do not bump yet.** Dependency:
`blocks/02-delete-the-code-topic-and-remove-coga-repo-only` / PR #1081.
After it merges, rebase this branch, preserve this family's important-topic
cleanup in any overlap, recheck twins and the final diff, rerun the suite and
validation, and refresh these receipts before advancing. The current review
completed; any later head/base needs a new receipt.

## PR

```yaml
title: Trim notification topics and separate user guidance from internals
author: claude
author_evidence: The implementation handoff and original commit db0ef105b identify Claude Code / Claude
  Opus 5.5. That commit rebased to 78f581157. Codex independently reviewed it in this session and authored
  the review corrections in b5668d59a.
head: b5668d59a8800e676e420761ac7a43931a1a145c
base: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
depth: deep
rationale: 'The documentation changes are bounded and directly reviewed, but the mandatory full suite
  still fails three packaging checks reproduced on unchanged main. PR #1081 must land and this branch
  must be reconciled and reverified before this step can advance.'
implementation: Trim notifications, producers, and important; replace notifications/failures with a user
  summary and local notification internals; centralize Slack setup in shipped TOML comments; repair links
  and twins. Review fixes clarify explicit-send versus post-transition failure behavior and move sync
  implementation instructions into coga-dev/patterns.
deviations: No audit disagreement or runtime behavior change. The sync design-rule move scheduled for
  the blocks/06 family was pulled forward because repointing its required reading to unshipped internals
  would violate the audience boundary. Old ticket prose and audit history remain outside the link cleanup,
  as the group instructions allow.
limitations: 'Blocked on blocks/02-delete-the-code-topic-and-remove-coga-repo-only (PR #1081), which owns
  main packaging drift and the leftover coga/code registration/links. No live Slack send or interactive
  TTY check was needed: runtime messages and terminal behavior are unchanged. Tests ran on Python 3.12.12;
  no Python 3.11 run is claimed.'
files:
  docs/README.md: Remove the deleted notifications/failures navigation entry.
  docs/contexts/coga-dev/internals/SKILL.md: Index the new notification internals owner.
  docs/contexts/coga-dev/internals/notifications/SKILL.md: Own failure internals, producer callers, accounting,
    message format, and the repo-specific usage-report decision.
  docs/contexts/coga-dev/patterns/SKILL.md: Receive the developer-only sync design procedure so shipped
    guidance does not require an unshipped topic.
  docs/contexts/coga-dev/testing/SKILL.md: Point notification setup guidance at the shipped configuration
    comments.
  docs/contexts/coga/important/SKILL.md: Remove the repo-specific report exception and repoint failure
    and configuration guidance.
  docs/contexts/coga/notifications/SKILL.md: Retain the user contract and accurate failure summary; move
    setup and developer details to their owners.
  docs/contexts/coga/notifications/failures/SKILL.md: Delete the split topic after moving user guidance
    and internals.
  docs/contexts/coga/notifications/producers/SKILL.md: Keep the user-visible event/destination inventory
    and move caller/accounting detail to developer guidance.
  docs/contexts/coga/sync/SKILL.md: Repoint failures navigation and replace the developer procedure with
    optional navigation.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md: Keep the packaged important
    topic byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md: Keep the packaged
    notification topic byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/failures/SKILL.md: Delete the
    packaged twin of the split failures topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md: Keep the
    packaged producer inventory byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md: Keep the packaged sync overview
    byte-identical to its canonical owner.
  src/coga/resources/templates/coga/coga.toml: Own the moved Slack configuration comments without changing
    parsed settings.
  tests/test_packaging.py: Remove the retired failures topic from required bootstrap contexts.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: b5668d59a8800e676e420761ac7a43931a1a145c
  base: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
  detail: Direct review completed on the final diff after rebase and fixes. Codex was independent of the
    Claude implementation; Codex applied and self-checked its review corrections. Failure-summary accuracy
    and a shipped procedure requiring local developer reading were fixed; the remaining owner-mapping
    setup duplicate was removed and the usage-report rationale preserved. No unresolved change-specific
    finding. The mandatory test failure is separately recorded and blocks advancement. No nested reviewer
    CLI or subagent was used.
checks:
- command: .venv/bin/python -m pytest -q
  status: failed
  head: b5668d59a8800e676e420761ac7a43931a1a145c
  base: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
  detail: 'Python 3.12.12: 3 failed, 3952 passed, 7 skipped in 356.79s (0:05:56). Only the three packaging
    tests listed in Peer review fail; baseline reproduction confirms they predate this branch. Log: /tmp/coga-blocks05-peer-pytest.log.'
- command: coga validate --json
  status: passed
  head: b5668d59a8800e676e420761ac7a43931a1a145c
  base: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
  detail: Exit 0; 151 checks OK, 0 errors, 47 existing warnings (20 stuck-in-progress, 19 unfrozen-workflow,
    7 empty-description, 1 large-blackboard).
- command: .venv/bin/python /tmp/coga-blocks05-doc-audit.py
  status: passed
  head: b5668d59a8800e676e420761ac7a43931a1a145c
  base: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
  detail: Four surviving touched context pairs are byte-identical; both failures copies are absent; all
    361 scanned Markdown sources outside archives/tasks/log have no notification link errors; no new global
    navigation or distribution errors; shipped developer-reference check passes; parsed TOML values are
    unchanged. Task-reference scan found only existing task instructions/history and the family audit,
    excluded by scope.
- command: git diff --check main...HEAD
  status: passed
  head: b5668d59a8800e676e420761ac7a43931a1a145c
  base: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
  detail: No whitespace errors on the complete reviewed branch diff.
- command: PYTHONPATH=/tmp/coga-blocks05-main-review-13b702f17/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest -q tests/test_packaging.py::test_live_and_packaged_copies_stay_identical tests/test_packaging.py::test_context_distribution_is_complete
    tests/test_packaging.py::test_context_navigation_has_no_broken_links
  status: failed
  head: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
  base: 13b702f1770b7b47c5bdbdd74cfb8589346bb891
  detail: 'Baseline-only reproduction in an unchanged detached clone of main: the same 3 packaging tests
    fail in 8.59s. This is evidence of pre-existing failures, not verification of the feature head.'
```

---

## Blockers

- [x] [2026-10-21 18:01] [agent:codex] id=20261021T180105 Merge PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only to repair the three required packaging-test failures reproduced on main. Then rebase the pushed branch, rerun pytest and validation, and refresh the final review receipts before bumping. Direct review and documentation fixes are complete at b5668d59a; validation passes.
  resolved: [2026-10-21 21:55] [human:nicktoper] The owner confirmed clearing this dependency blocker and resuming review. PR #1081 merged as a1a3f5049b5dd2457f531a4d81b79b6a6425bb9f and is present on fetched origin/main. Rebase the branch, preserve notification cleanup through overlaps, rerun the full suite and validation, and refresh final review receipts before bumping.
