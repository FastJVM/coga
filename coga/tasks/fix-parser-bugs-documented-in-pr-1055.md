---
title: Fix parser bugs documented in PR 1055
status: in_progress
owner: nicktoper
contexts:
- dev/code
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
---

## Description

Fix the three unresolved parser and diagnostic defects documented by https://github.com/FastJVM/coga/pull/1055. The owner requested actual bug fixes after reviewing that documentation-only PR. Deliver code, regression tests, and the corrected behavior contracts together.

### Defects and reproduction evidence

1. False blockers from examples and superseded designs. In `src/coga/blackboard.py`, `parse_blockers_text` scans every stored line without code-fence or archive awareness; `open_blockers` exposes these results to launch and megalaunch eligibility checks. The line `- [ ] [2026-09-18 12:00] [human:marc] id=old Historical example ask` is currently treated as an open blocker even inside a fenced example or under the exact `## Superseded designs` section. The prompt projection can omit that history while the pre-composition gate still refuses work.

2. Truncated workflow instructions. `src/coga/workflow.py::_parse_inline_sections` uses a fence-unaware heading regex. In a skill-less step's `## implement` section, put a closed fenced Markdown example containing `## Example`, then ordinary instructions after the example. The example heading ends the step's instructions prematurely, even when "Example" is not a step name. A fenced heading matching another step can also supply bogus instructions for that step.

3. Missing warning for uncomposed preamble. Put substantive prose before `## Description`, followed by otherwise valid Description and Context sections. `taskfile.body_sections` returns only headed sections, so composition omits that prose and `uncomposed_sections` reports nothing about it. Preserve the existing Description/Context composition boundary; warn about the lost prose and explain where to move it.

These code paths were inspected on main at `27e384504067548a6ea8b1b020559f5f25cfe70a` on 2026-10-20. PR #1055 was still open at head `14d6863ce33bd4aef747af26a4ccd2e7aa630050` and changed only contexts, packaged twins, and source-ticket deletion. This ticket records source-inspection evidence, not a completed runtime test.

### Acceptance criteria

- Fenced blocker examples and every exact Superseded designs section are inert for blocker reading, launch, megalaunch, and the composed blocker preamble. Preserve the documented archive boundaries and all genuine live blockers, resolved entries, and supported legacy entries. Examples must not alter a live blocker's resolution state. Exercise both direct readers and a launch/queue consumer.
- Inline workflow instructions retain fenced H2 lines and all subsequent prose through the next real section boundary. Fenced headings cannot create another step's instructions. Cover backtick and tilde fences, non-step headings, and headings matching another real step; preserve skill-backed step behavior.
- Validate and launch/prompt-report consistently warn when substantive pre-heading prose will be omitted. The warning identifies the omitted region and directs the author to Description or Context. Test a nonempty Description after the preamble, a prose-only body, and whitespace-only preambles. Preserve terminal-ticket warning policy and normal composed-section behavior. Do not silently expand the composition contract.
- Use the existing shared Markdown helpers where they fit. Confirm the handling of unmatched fences and archive boundaries explicitly; do not introduce a competing Markdown parser or accidentally change the archive projection contract.
- Add regression tests that fail on the current behavior and pass with the fixes, including negative controls proving real blockers and real workflow headings still work.
- Update the owning blackboard, tickets, and workflows contexts and their packaged twins in the same PR. Check #1055's current merge state: replace its known-gap workarounds if they have landed, otherwise document the corrected behavior against current main and identify the overlap in the implementation PR.
- Verify focused regressions, packaging twins, and the full suite using the checkout's own source, and run repository validation. Record exact commands, interpreter, and results.

### Scope

This is one parser/diagnostics bug-fix ticket. Changes to Retro's general follow-up policy, automatic composition of extra ticket text, a general Markdown redesign, and unrelated historical-ticket rewrites are outside its scope. PR #1055's documentation cleanup does not resolve these defects.

### Verification starting points

Read and extend the relevant coverage in `tests/test_blackboard.py`, `tests/test_compose.py`, `tests/test_taskfile.py`, `tests/test_validate.py`, `tests/test_launch.py`, and `tests/test_megalaunch.py`; `tests/test_packaging.py` checks the canonical/package twins. Keep the regression coverage focused on the user-visible failures above.

## Context

The following topics are cited rather than attached. Read their named sections before implementation, and update the owning topic and its packaged twin when its behavior changes:

- `coga/blackboard`, `docs/contexts/coga/blackboard/SKILL.md`, "Section regimes" and "Superseded designs": `blackboard._without_superseded_designs` owns the exact archive projection; `parse_blockers_text` and `open_blockers` currently read the unfiltered stored region.
- `coga/tickets`, `docs/contexts/coga/tickets/SKILL.md`, "Body regions": `taskfile.body_sections` and `uncomposed_sections` define the existing section and warning boundaries; `compose._extract_section` reads the same section parser. Preamble diagnostics must preserve that composition contract.
- `coga/workflows`, `docs/contexts/coga/workflows/SKILL.md`, "Definition format" and "Frozen snapshot, live content": `Workflow.load` reads `_parse_inline_sections`; a skill-less step's live inline content reaches the prompt, while a skill-backed step uses its skills.
- Read `coga/codebase`, `docs/contexts/coga/codebase/SKILL.md`, before editing source; follow `coga/testing`, `docs/contexts/coga/testing/SKILL.md`, for the checkout-specific test environment and verification receipts, and `coga/packaging`, `docs/contexts/coga/packaging/SKILL.md`, for canonical/package twin mapping.

PR #1055 preserves findings from the completed `exclude-superseded-designs-from-launch-prompts` and `autofix-write-ups-lose-their-body-to-h2-headings` tickets. The reproduction details above remain usable after those source tickets are deleted. Recheck current main and that PR before implementation and publication.

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
implementation and evidence, never placeholders; coga/internals/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/fix-parser-boundaries

## Implementation plan

Owner confirmed the plan in the attended Codex session on 2026-10-20:
add failing regressions, reuse the shared Markdown helpers for blocker reading
and workflow sections, and warn about uncomposed preamble without expanding
composition. Preserve the archive projection's exact boundaries and unmatched
fence behavior; update the three owning topics and packaged twins.

Entry: clean main at 631c876982432c7b8dc3b92f32d1a1955a46b182,
matching freshly fetched origin/main; launch owns checkout return.
PR #1055 is CLOSED without merge (mergedAt null), head
14d6863ce33bd4aef747af26a4ccd2e7aa630050. Its workaround documentation
has not landed; this branch will document the corrected behavior directly.
The later implementation PR should identify the overlap with #1055.

Actual implementing agent: Codex (GPT-6), overriding the ticket's configured
Claude agent. Verification uses this checkout's .venv Python 3.12.12 and an
absolute PYTHONPATH pointing at this checkout's src.

## Adjacent finding

`src/coga/blackboard.py` `resolve_open_blockers` independently scans stored
lines when rewriting unresolved entries. With a real live blocker present,
it can rewrite fenced or archived examples too. This ticket fixes the readers
and eligibility/prompt consumers; the writer issue remains outside that scope.
No existing follow-up identified yet; retain this finding for review/Retro.

## Implementation verification — awaiting suite-failure decision

Parser fixes, regressions, three context owners and packaged twins, and seeded
smoke examples are committed on `codex/fix-parser-boundaries` at
`aea91aeab20b1e1248827b4f8e618d66c68ed183`, rebased onto current main
`3aa78632ab161b9f7cbeb03b98b4ff5362b4f136`. No implementation PR opened.
The feature branch is pushed to origin at that head. Implementation has not
bumped; the attending owner's suite-failure decision below is still pending.

All commands use `/home/n/Code/codex/coga/.venv/bin/python` (3.12.12) with
`PYTHONPATH=/home/n/Code/codex/coga/src` unless explicitly noted:

- Initial seven-file baseline: 621 passed in 37.12s.
- Regression selection before source changes: 29 failed, 17 passed,
  603 deselected in 9.95s, reproducing all three defects. After fixes:
  46 passed, 603 deselected in 1.73s. Logs:
  `/tmp/coga-parser-regressions-before.txt`.
- Broader focused run including primitives, seeded smoke, and packaging:
  692 passed in 40.85s before rebase. Committed tree
  `cb47acb8d65ca40bdb5181a91d02d2b01684fd6d` at
  `2d6806a3db2288837fd9365e177d67ec2350c740` exactly matches that tested tree
  (index/worktree clean and `git write-tree` equals `HEAD^{tree}`).
- After rebase, focused regressions plus packaging:
  73 passed, 603 deselected in 4.98s; log
  `/tmp/coga-parser-final-focused.txt`.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q`:
  **6 failed, 3849 passed, 7 skipped in 303.09s**;
  `/tmp/coga-parser-full.txt`.
- Repository `python -m coga.validate --json`: exit 0, 125 tasks counted OK,
  0 errors, 46 warnings (20 stuck-in-progress, 18 unfrozen-workflow,
  1 uncomposed-section, 7 empty-description).
- Seeded fixture validation with `env -u SLACK_WEBHOOK_URL`, absolute
  PYTHONPATH, and the same interpreter: exit 0, 4 tasks counted OK,
  no errors or warnings.

All six full-suite failures are parametrizations of
`tests/test_usage_report.py` `test_period_task_posts_with_project_and_owner_before_bumping`.
The test patches `coga.notification.slack.requests.post`, but
`src/coga/notification/slack.py` `SlackChannel.send` imports `requests`
locally; the module attribute does not exist. These files are unchanged by
this branch. A standalone run on this branch gives 6 failed, 15 passed in
7.70s. A clean exported snapshot of main at the OID above reproduces the
same six failures (15 passed in 0.79s):

```sh
cd /tmp/coga-parser-main-baseline-_jy12of1
PYTHONPATH=/tmp/coga-parser-main-baseline-_jy12of1/src /home/n/Code/codex/coga/.venv/bin/python -m pytest -q tests/test_usage_report.py --tb=short
```

Baseline log: `/tmp/coga-parser-usage-main.txt`. Awaiting the attending
owner's decision per code/implement: hand off the parser change with these
pre-existing failures documented, or include the small test-only mock repair.

The separate `resolve_open_blockers` writer issue above was also reproduced
in a temporary ticket: resolving a live ask changed an archived checkbox to
resolved. No writer fix was included.

## PR

```yaml
title: Fix blocker and workflow parsing and warn on omitted preambles
author: codex
author_evidence: Implementation ran in this attended Codex (GPT-6) session, overriding
  the ticket's configured Claude agent; no subagents or external reviewer were used.
head: aea91aeab20b1e1248827b4f8e618d66c68ed183
base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
depth: deep
rationale: Three bounded parser/diagnostic corrections with direct and consumer regressions.
  Full suite has six usage-report mock-target failures reproduced on unchanged main,
  and independent review is pending; inspect the diff and these limits.
implementation: Blocker readers apply the existing archive projection and skip closed
  fenced examples, including example resolutions. Inline workflow content uses the
  shared H2 parser, preserving fenced examples and following prose while keeping skill-backed
  steps unchanged. Launch and validate share a diagnostic for non-whitespace preamble
  omitted from the unchanged Description/Context composition contract. Owning contexts,
  packaged twins, and seeded examples accompany the fixes.
deviations: 'No scope expansion. PR #1055 is closed without merge at 14d6863ce33bd4aef747af26a4ccd2e7aa630050:
  its proposed known-gap/workaround text did not land. This change overlaps its three
  context topics and twins with corrected behavior, without deleting its source tickets.'
limitations: 'Verification uses Python 3.12.12 on Linux, not a separate Python 3.11
  or native Windows run. Adjacent pre-existing resolve_open_blockers writer bug remains:
  with a real live ask present it can rewrite archived/fenced examples; reproduced
  separately and retained below for follow-up. Full suite currently reports six pre-existing
  usage-report test failures: obsolete coga.notification.slack.requests.post monkeypatch
  target after requests became a local import. Same six failures reproduce on main.'
files:
  docs/contexts/coga/blackboard/SKILL.md: Define live blocker interpretation and the
    preserved unmatched-fence/archive rules.
  docs/contexts/coga/tickets/SKILL.md: Document omitted preamble diagnostics and unchanged
    composition and terminal-validation policy.
  docs/contexts/coga/workflows/SKILL.md: Document shared fence-aware inline section
    parsing and real heading boundaries.
  src/coga/blackboard.py: Filter archived and fenced examples before interpreting
    blockers or resolutions.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Ship
    the byte-identical blackboard contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Ship
    the byte-identical ticket contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Ship
    the byte-identical workflow contract.
  src/coga/taskfile.py: Share preamble and uncomposed-section diagnostics without
    altering body section composition.
  src/coga/validate.py: Use the shared omitted-body diagnostic and avoid duplicate
    empty-description warnings.
  src/coga/workflow.py: Replace the fence-unaware heading regex with existing body_sections
    parsing.
  tests/fixtures/seeded-repo/coga/tasks/auto/triage-inbound-email.md: Exercise archived
    and fenced blocker examples in the seeded task.
  tests/fixtures/seeded-repo/coga/workflows/code/with-review.md: Exercise a fenced
    H2 and subsequent inline instructions in the seeded workflow.
  tests/test_blackboard.py: Cover direct readers, resolution isolation, legacy/live
    entries, exact/duplicate archives, and unmatched fences.
  tests/test_compose.py: Cover blocker preambles and inline workflow fences, real
    boundaries, and skill-backed behavior.
  tests/test_launch.py: Cover actual launch and prompt-report preamble diagnostics
    and inert blocker examples.
  tests/test_megalaunch.py: Prove queue eligibility ignores examples while real asks
    still block.
  tests/test_smoke.py: Verify seeded blocker examples and inline workflow instructions
    through the lifecycle.
  tests/test_taskfile.py: Cover preamble/section boundaries, whitespace, prose-only
    bodies, and combined warnings.
  tests/test_validate.py: Cover shared preamble warnings, suppression of duplicate
    empty-description warnings, and terminal policy.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step only. Independent code review belongs to the next peer-review
    step; owner approval of the implementation plan is not code review.
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q tests/test_blackboard.py
    tests/test_taskfile.py tests/test_compose.py tests/test_validate.py tests/test_launch.py
    tests/test_megalaunch.py tests/test_packaging.py -k 'blocker_examples or blocker_resolution_examples
    or blockers_archive or blockers_unclosed or workflow_fenced or workflow_unclosed
    or workflow_skill_backed or preamble or packaging'
  status: passed
  head: aea91aeab20b1e1248827b4f8e618d66c68ed183
  base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  detail: 73 passed, 603 deselected in 4.98s. Python 3.12.12; checkout source; all
    packaging tests included.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q
  status: failed
  head: aea91aeab20b1e1248827b4f8e618d66c68ed183
  base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  detail: '6 failed, 3849 passed, 7 skipped in 303.09s. Failures are six parametrizations
    in test_usage_report.py due to a pre-existing stale mock target; 7 native Windows
    tests skipped on Linux. Log: /tmp/coga-parser-full.txt.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.validate
    --json
  status: passed
  head: aea91aeab20b1e1248827b4f8e618d66c68ed183
  base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  detail: 'Exit 0; 125 tasks OK; 0 errors, 46 warnings: 20 stuck-in-progress, 18 unfrozen-workflow,
    1 uncomposed-section, 7 empty-description. Log: /tmp/coga-parser-repo-validation.json.'
- command: cd /home/n/Code/codex/coga/tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL
    PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python
    -m coga.validate --json
  status: passed
  head: aea91aeab20b1e1248827b4f8e618d66c68ed183
  base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  detail: 'Exit 0; 4 tasks OK; 0 errors or warnings. Log: /tmp/coga-parser-fixture-validation.json.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q tests/test_usage_report.py
    --tb=short
  status: failed
  head: aea91aeab20b1e1248827b4f8e618d66c68ed183
  base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  detail: '6 failed, 15 passed in 7.70s; same stale mock target in isolation. Log:
    /tmp/coga-parser-usage-isolated.txt.'
- command: cd /tmp/coga-parser-main-baseline-_jy12of1 && PYTHONPATH=/tmp/coga-parser-main-baseline-_jy12of1/src
    /home/n/Code/codex/coga/.venv/bin/python -m pytest -q tests/test_usage_report.py
    --tb=short
  status: failed
  head: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  detail: 'Unchanged exported main snapshot: 6 failed, 15 passed in 0.79s, proving
    baseline failures. Log: /tmp/coga-parser-usage-main.txt.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: aea91aeab20b1e1248827b4f8e618d66c68ed183
  base: 3aa78632ab161b9f7cbeb03b98b4ff5362b4f136
  detail: Exit 0; no whitespace errors.
```
