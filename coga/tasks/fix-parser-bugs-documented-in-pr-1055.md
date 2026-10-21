---
title: Fix parser bugs documented in PR 1055
status: done
owner: nicktoper
contexts:
- coga/code
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
- Read `coga-dev/codebase`, `docs/contexts/coga-dev/codebase/SKILL.md`, before editing source; follow `coga-dev/testing`, `docs/contexts/coga-dev/testing/SKILL.md`, for the checkout-specific test environment and verification receipts, and `coga-dev/packaging`, `docs/contexts/coga-dev/packaging/SKILL.md`, for canonical/package twin mapping.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1075
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

## Implementation handoff

Historical implement-stage handoff; the current reviewed and pushed revision is
recorded under `## Peer review` below.

All three parser/diagnostic defects are implemented and pushed on
`codex/fix-parser-boundaries` at
`94f07acae799800aaf6f6b4fa5eea3d7d225c976`, based on main at that handoff
`34bcb221b4a7e4b7e53ca8c30b6665764a399234`.

- Blocker readers reuse the exact archive projection, then ignore closed fenced
  examples and example resolutions. Direct, launch, queue, and composed-preamble
  regressions preserve genuine live/resolved/legacy entries.
- Inline workflows use the shared H2 parser, retaining fenced headings and
  subsequent prose. Real headings still bound sections; skill-backed steps
  still compose their skills. Unmatched-fence behavior is explicit in tests.
- Launch/prompt-report and validation share omitted-preamble diagnostics.
  Description/Context composition and terminal-validation policy are unchanged.
- The three owning topics, packaged twins, and seeded lifecycle examples are
  updated. PR #1055 remains closed and unmerged at
  `14d6863ce33bd4aef747af26a4ccd2e7aa630050`; this branch supplies corrected
  contract text for its overlapping topics. Mention that overlap when opening
  the implementation PR. No PR was opened in implement.

The owner requested fixing the six baseline usage-report failures on 2026-10-20.
Main had already landed the exact test-only repair in
`34bcb221b4a7e4b7e53ca8c30b6665764a399234`: the mock targets `requests.post`
instead of the obsolete `coga.notification.slack.requests.post` module path.
This branch was rebased onto that repair; no duplicate feature change was needed.
All 84 usage-report/notification tests and the full suite now pass.

Implement-stage verification used `/home/n/Code/codex/coga/.venv/bin/python`
(Python 3.12.12/Linux) with absolute `PYTHONPATH=/home/n/Code/codex/coga/src`
at the historical head/base recorded above:
73 focused regression/packaging checks pass; full suite 3855 passed, 7 skipped
(2 Windows job-object and 5 native Windows PowerShell cases); repository
validation has 0 errors/46 warnings, and seeded validation has 0 errors/warnings.
The branch was clean throughout final checks; the final fetch found no new main
commits. Code review had not run at that handoff; its completed result is now below.

### Regression and earlier verification evidence

Before source fixes, the focused reproduction selection gave 29 failed,
17 passed, 603 deselected; after fixes the same selection gave 46 passed,
603 deselected. The command was:

```sh
PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q tests/test_blackboard.py tests/test_taskfile.py tests/test_compose.py tests/test_validate.py tests/test_launch.py tests/test_megalaunch.py -k 'blocker_examples or blocker_resolution_examples or blockers_archive or blockers_unclosed or workflow_fenced or workflow_unclosed or workflow_skill_backed or preamble' --tb=short
```

The earlier broader focused run (including primitives, smoke, and packaging)
gave 692 passed in 40.85s on committed tree
`cb47acb8d65ca40bdb5181a91d02d2b01684fd6d` at
`2d6806a3db2288837fd9365e177d67ec2350c740`; index/worktree equality and
`git write-tree == HEAD^{tree}` associated the pre-commit run with that commit.

The first full suite at `aea91aeab20b1e1248827b4f8e618d66c68ed183` gave
6 failed, 3849 passed, 7 skipped in 303.09s. All six were the usage-report
mock-target failure above; an unchanged exported main snapshot at
`3aa78632ab161b9f7cbeb03b98b4ff5362b4f136` reproduced the same six failures
with 15 passing tests using:

```sh
cd /tmp/coga-parser-main-baseline-_jy12of1
PYTHONPATH=/tmp/coga-parser-main-baseline-_jy12of1/src /home/n/Code/codex/coga/.venv/bin/python -m pytest -q tests/test_usage_report.py --tb=short
```

Historical logs: `/tmp/coga-parser-regressions-before.txt`,
`/tmp/coga-parser-focused.txt`, `/tmp/coga-parser-full.txt`, and
`/tmp/coga-parser-usage-main.txt`. These failed/historical checks are superseded
by fresh final verification below, not relabeled as passes.

## Peer review

Direct review **completed** on 2026-10-20 in this fresh Codex (GPT-6) session,
covering head `137026dac302b998bdb5d648c7125f02c7845634` against base
`fee99cdd1b5e30f009033a47fd50804fe6826016`. Actual implementation was also Codex,
so this is **self-review**, not independent review; the configured Claude
assignment does not change that identity. No child reviewer was launched.

No must-fix findings; no source or test changes were needed. Reviewed all 19
changed paths and the affected callers. Closed example blockers and resolutions
are inert; genuine live/resolved/legacy entries remain readable. The exact
archive projection is unchanged, including unmatched fences extending to EOF;
the shared live-line/section reader still treats unmatched openers as text.
Workflow boundaries, skill-backed steps, Description/Context composition, and
terminal-ticket validation policy remain consistent with their owning topics.
The separate unchanged unblock-writer issue remains recorded under Adjacent finding.

Surface check: read-only composition of the seeded triage ticket produced zero
open blockers and no blocker-preamble layer, omitted the archived ask, and kept
the fenced example as literal blackboard text. The seeded workflow retained its
fenced H2 and following instruction. The preamble diagnostic named the omitted
region and directed relocation to Description or Context; whitespace-only
preamble produced no warning. Plain CLI diagnostic output is covered by launch
and prompt-report capture regressions. No raw-terminal loop, pager, TTY prompt,
or rendered Slack surface changed, so an interactive surface trial did not apply.

Freshness: started on clean `main` at `fee99cdd1b5e30f009033a47fd50804fe6826016`,
matching origin. Switched to the feature branch, fetched origin/main and rebased
unconditionally. `git range-diff` proved the patch unchanged; the final diff was
reviewed after rebase. The final fetch found no additional main movement.
`git push --force-with-lease origin codex/fix-parser-boundaries` published the
reviewed head. The branch remains one implementation commit ahead of main.
PR #1055 was rechecked through GitHub: closed, unmerged, still at
`14d6863ce33bd4aef747af26a4ccd2e7aa630050`; its context overlap remains disclosed
in the implementation PR preparation.

Fresh verification: 73 focused/packaging checks passed; full suite 3855 passed,
7 Windows-only skips in 291.17s; repository validation 0 errors/46 warnings;
seeded validation 0 errors/warnings; whitespace check clean. The exact commands,
interpreter, logs, and tested head/base are in `## PR`. Recommend `skim` with the
self-review and platform/writer limitations disclosed. No PR was opened here.
The read-only PR formatter accepted all 19 file explanations and current receipts
without evidence gaps; preview: `/tmp/coga-parser-peer-pr-preview.md`.
Task-scoped validation after the handoff edit also passed with no warnings.
Launch owns checkout return (`COGA_LAUNCH_RETURNS_CHECKOUT=1`); handoff stays on
the feature branch, using the ticket refreshed from origin/main before this note.

## PR

```yaml
title: Fix blocker and workflow parsing and warn on omitted preambles
author: codex
author_evidence: The implementation handoff records Codex (GPT-6) in the attended implement
  session, overriding the configured Claude agent. This fresh peer-review session also used
  Codex (GPT-6); the review is recorded as self-review. No subagents or external review tool
  were used.
head: 137026dac302b998bdb5d648c7125f02c7845634
base: fee99cdd1b5e30f009033a47fd50804fe6826016
depth: skim
rationale: Bounded parser and diagnostic fixes reuse the existing Markdown helpers. Direct
  Codex self-review completed on this final head/base without must-fix findings; focused regressions,
  packaging checks, the full suite, and validation passed. Read the description for self-review
  disclosure, the preserved difference in unmatched-fence handling, and the separate pre-existing
  writer limitation.
implementation: Blocker readers apply the existing archive projection and skip closed fenced
  examples, including example resolutions. Inline workflow content uses the shared H2 parser,
  preserving fenced examples and following prose while keeping skill-backed steps unchanged.
  Launch and validate share a diagnostic for non-whitespace preamble omitted from the unchanged
  Description/Context composition contract. Owning contexts, packaged twins, and seeded examples
  accompany the fixes.
deviations: 'The owner requested repair of the six baseline usage-report failures. Main had
  already landed the exact test-only requests.post mock correction at 34bcb221b4a7e4b7e53ca8c30b6665764a399234;
  rebasing includes it without a duplicate feature diff. PR #1055 remains closed without merge
  at 14d6863ce33bd4aef747af26a4ccd2e7aa630050; this change overlaps its three context topics
  and twins with corrected behavior.'
limitations: 'No independent review: both the actual implementer and this fresh reviewer are
  Codex (GPT-6), despite the ticket configuring Claude as its main agent. Verified on Python
  3.12.12/Linux, with no separate Python 3.11 or native Windows execution. The separate pre-existing
  resolve_open_blockers writer bug remains: with a real live ask present it can rewrite archived/fenced
  examples. Its writer loop is unchanged by this patch; retain the finding for follow-up.'
files:
  docs/contexts/coga/blackboard/SKILL.md: Define live blocker interpretation and the preserved
    unmatched-fence/archive rules.
  docs/contexts/coga/tickets/SKILL.md: Document omitted preamble diagnostics and unchanged
    composition and terminal-validation policy.
  docs/contexts/coga/workflows/SKILL.md: Document shared fence-aware inline section parsing
    and real heading boundaries.
  src/coga/blackboard.py: Filter archived and fenced examples before interpreting blockers
    or resolutions.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Ship the
    byte-identical blackboard contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Ship the byte-identical
    ticket contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Ship the byte-identical
    workflow contract.
  src/coga/taskfile.py: Share preamble and uncomposed-section diagnostics without altering
    body section composition.
  src/coga/validate.py: Use the shared omitted-body diagnostic and avoid duplicate empty-description
    warnings.
  src/coga/workflow.py: Replace the fence-unaware heading regex with existing body_sections
    parsing.
  tests/fixtures/seeded-repo/coga/tasks/auto/triage-inbound-email.md: Exercise archived and
    fenced blocker examples in the seeded task.
  tests/fixtures/seeded-repo/coga/workflows/code/with-review.md: Exercise a fenced H2 and
    subsequent inline instructions in the seeded workflow.
  tests/test_blackboard.py: Cover direct readers, resolution isolation, legacy/live entries,
    exact/duplicate archives, and unmatched fences.
  tests/test_compose.py: Cover blocker preambles and inline workflow fences, real boundaries,
    and skill-backed behavior.
  tests/test_launch.py: Cover actual launch and prompt-report preamble diagnostics and inert
    blocker examples.
  tests/test_megalaunch.py: Prove queue eligibility ignores examples while real asks still
    block.
  tests/test_smoke.py: Verify seeded blocker examples and inline workflow instructions through
    the lifecycle.
  tests/test_taskfile.py: Cover preamble/section boundaries, whitespace, prose-only bodies,
    and combined warnings.
  tests/test_validate.py: Cover shared preamble warnings, suppression of duplicate empty-description
    warnings, and terminal policy.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: Direct review completed in this fresh Codex (GPT-6) peer-review session. Reviewed
    all 19 changed paths, shared Markdown/archive helpers, blocker resolution parsing, launch/queue/prompt
    consumers, warning policy, workflow composition, regression tests, and canonical/package
    contracts on the final rebased revision. No must-fix findings or code fixes. Read-only
    fixture composition confirmed no blocker preamble from examples, retained fenced workflow
    headings and following prose, and the omitted-preamble repair text. No raw-terminal, pager,
    TTY-prompt, or Slack-rendering behavior changed.
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q tests/test_blackboard.py
    tests/test_taskfile.py tests/test_compose.py tests/test_validate.py tests/test_launch.py
    tests/test_megalaunch.py tests/test_packaging.py -k 'blocker_examples or blocker_resolution_examples
    or blockers_archive or blockers_unclosed or workflow_fenced or workflow_unclosed or workflow_skill_backed
    or preamble or packaging' > /tmp/coga-parser-peer-focused.txt 2>&1
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: 73 passed, 603 deselected in 10.84s. Includes all packaging checks; the three changed
    canonical/package topic pairs were also compared byte-for-byte. Python 3.12.12/Linux,
    checkout .venv interpreter, absolute checkout PYTHONPATH.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q -rs > /tmp/coga-parser-peer-full.txt
    2>&1
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: 3855 passed, 7 skipped in 291.17s. Two Windows job-object integration cases and
    five native Windows PowerShell 5.1 cases skipped on Linux. Python 3.12.12, /home/n/Code/codex/coga/.venv/bin/python;
    import verified at /home/n/Code/codex/coga/src/coga/__init__.py. Clean committed tree
    throughout the run.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.validate --json
    > /tmp/coga-parser-peer-repo-validation.json
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: 'Exit 0; 125 tasks OK, 0 errors and 46 warnings: 20 stuck-in-progress, 18 unfrozen-workflow,
    1 uncomposed-section, and 7 empty-description.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python
    -m coga.validate --json > /tmp/coga-parser-peer-fixture-validation.json
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: Run with cwd /home/n/Code/codex/coga/tests/fixtures/seeded-repo/coga. Exit 0; 4
    tasks OK, 0 errors or warnings.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: Exit 0; no whitespace errors. Repeated after the final fetch, which left origin/main
    unchanged.
- command: git range-diff 34bcb221b4a7e4b7e53ca8c30b6665764a399234..94f07acae799800aaf6f6b4fa5eea3d7d225c976
    origin/main..HEAD
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: Exit 0; the single implementation commit is patch-identical after rebase (94f07acae
    = 137026dac). Main drift consisted only of this ticket and coga/log.md.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.validate --task
    fix-parser-bugs-documented-in-pr-1055 --json
  status: passed
  head: 137026dac302b998bdb5d648c7125f02c7845634
  base: fee99cdd1b5e30f009033a47fd50804fe6826016
  detail: 'Post-handoff check with the updated blackboard still uncommitted for Coga publication:
    exit 0, 1 task OK, no errors or warnings. Product source remains the reviewed committed
    head.'
```
