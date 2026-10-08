---
title: Autofix tickets launch without their write-up when the analyst uses H2 headings
status: in_progress
owner: nicktoper
agent: codex
contexts:
- coga/testing
- coga/packaging
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
step: 4 (review)
---

## Description

**Scope expanded by the owner on 2026-10-07:** cover all ticket authors and
creation paths, not just autofix. Prevent required ticket intent from silently
vanishing at H2 boundaries, and add at least an actionable validate warning
for unsupported body sections even when Description starts with nonempty prose.
Keep this existing ref and its earlier evidence; the title reflects its original
autofix report.

Most autofix tickets launch with an empty or truncated Description. The
agent picking one up never sees the analyst's diagnosis, evidence, or fix
outline. The analyst writes its body with `##` headings (`## What broke`,
`## Evidence`, `## What a fix has to do`). `create_autofix_ticket` puts that
body under `## Description`. `compose._extract_section` then ends the
Description at the first of those headings, so everything from it down is
outside both `## Description` and `## Context` and is never composed.

This happens to upstream's own autofix tickets: all three under
`coga/tasks/autofix/` on `origin/main` (2026-09-22) have H2s inside their
Description. It also happens in the downstream admin repo, where 13 of 14 do.
The `empty-description` warning in `coga validate` is only the visible part. It
fires only when the body *opens* with an H2. A body that opens with prose
passes validate but still loses every H2 section after that prose.

Done when a newly generated autofix ticket composes its full analyst body into
the `task_description` layer (`coga launch <slug> --prompt-report`) whatever
headings the analyst chose, and a test pins that.

Additional acceptance criteria for the broader scope:

- Reproduce a manually authored ticket containing Description, Context,
  Acceptance Criteria and Proposed Shape, plus an H2 after introductory
  Description prose. Assert on actual composed text, not merely layer counts.
- Ensure omitted intent cannot pass validation silently: at minimum name each
  unsupported heading and explain the repair. Empty-description alone is not
  sufficient. Account for fenced Markdown examples, blackboard contents, and
  deliberately separate operational sections such as legacy PR preparation.
- Choose and document whether additional intent sections compose or authors
  must move them under supported sections; preserve the separation of ticket
  intent from operational/PR material. Do not blindly include every H2.
- Retain the original autofix full-body acceptance case. An autofix-only
  heading normalizer does not satisfy the expanded ticket.
- Update the owning ticket/composition contracts, validator guidance, affected
  authoring instructions, and packaged twins; pin the behavior with focused
  composer, validator, and autofix regressions.

## Context

### Additional report — 2026-10-07

Another AI, relayed by the owner, created a ticket with Acceptance Criteria
and Proposed Shape and reports that only Description, Context, and blackboard
were represented by --prompt-report, while validate said “All good.” An H2
inside Description also truncated that section. Intake confirms the current
`compose._extract_section` boundary and the documented two-section contract;
the supplied manual reproduction itself has not been rerun here. A layer report
is not a full prompt dump, so verify omissions against composed text.

Read coga/tickets (`docs/contexts/coga/tickets/SKILL.md`, Body regions) and
coga/prompt-composition (`docs/contexts/coga/prompt-composition/SKILL.md`), cited
rather than attached because they are editing targets. The original options
below describe the narrower September autofix proposal; they are insufficient
on their own for the expanded scope and do not waive the validator warning.

This ticket runs `code/with-review`, which has no design step. The `implement`
step therefore makes the compose-vs-relocate contract decision itself. Record
the choice and its reasons on the blackboard before writing code, and spell it
out in the PR so the `peer-review` step and the owner can check it.

The authoring instructions that currently name the extra sections as
first-class spec regions all need reconciling with whatever contract is chosen:

- `code/design` (`coga/skills/code/design/SKILL.md` and its packaged twin):
  already says to put the spec as `###` subsections under Description.
- `code/review-design` (`coga/skills/code/review-design/SKILL.md` and twin):
  reviews "Description, Acceptance Criteria, Proposed Shape, and Out of Scope"
  as if they were sections.
- The bundled `code/design-then-implement` workflow's `review-design` section
  (`src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`)
  lists the same four names.
- `bootstrap/ticket` already forbids a separate `## Acceptance Criteria` section.
- `docs/contexts/coga/tickets/SKILL.md` already documents the silent drop
  (search "Acceptance Criteria"). It owns this contract.

### Mechanism (verified against `origin/main` c2268b05, 2026-09-22)

- `compose._extract_section` matches `_SECTION_HEADING_RE`
  (`^##\s+(.+?)\s*$`) and ends a section at the next match. `_template/ticket.md`
  states the contract: only `## Description` and `## Context` carry over, and
  any other heading above the fence is not composed.
- Each surface that reads body sections loses the content:
  - `compose`: the `task_description` and `task_context` layers.
    The agent's prompt loses the write-up.
  - `validate`: the `empty-description` check. Title-only is reported only
    when the body opens with an H2.
  - `open_pr`: in the HEAD 4f52ff407 re-check, `open_pr` was found to have its
    own `open_pr._sections` parser, which skips headings inside code fences.
    `compose._extract_section` does not skip them. `open_pr._pr_body` always
    adds a "Ticket as requested" snapshot built from Description and Context.
    That snapshot is truncated by H2s the same way, through the second parser.
- `commands/create.py` already rejects `## ` lines in `--description`
  (`_SECTION_HEADING_LINE_RE`). That makes a third heading parser. "All
  creation paths" includes it.
- Because there are several divergent parsers, the fenced-Markdown acceptance
  criterion depends on them. Decide whether compose, validate and open_pr share
  one fence-aware section parser, and say so in the PR. Define the intended
  behaviour for each of these cases and pin it in tests:
  - a heading inside a code fence;
  - a heading below the blackboard fence;
  - a legacy `## PR` section above the fence.
- `recurring_autofix`'s analyst prompt asks for a free-form
  "markdown body … Write it as the Description of a ticket". It gives no
  constraint on heading level. `parse_analysis` strips the `---` separator and
  passes the body through unchanged. `_ticket_description` appends the trailer
  and hands it to `create_autofix_ticket` as the description.
- Hand-authors already work around this. `recurring-sweep-wedges-on-the-ticket-py-it-copies`
  says "Everything below is `###` on purpose". The analyst has no such
  instruction.

### Evidence

- Re-counted at HEAD 4f52ff407 (2026-10-07): a naive count (one that does not
  skip code fences) finds H2s inside Description in all 8 tickets under
  `coga/tasks/autofix/`.
- Original report, upstream `origin/main` 2026-09-22: `report-per-skill-outcomes-from-gh-skill-update-in`
  (4 H2s inside Description), `stop-one-failing-ticket-py-from-starving-the-rest`
  (3), `treat-non-requestexception-slack-send-errors-as-de` (3).
- Downstream: Dream 2026-W39's validate-drift flagged two active autofix tickets
  as title-only. Each actually had a full write-up under H2s. A third ticket
  opened with prose, so validate passed it, but it still lost three H2 sections.
  After those H2s were demoted to `###` by hand, `coga validate` reported no
  `empty-description`, and `--prompt-report` showed a 4.9–5.4 KiB
  `task_description` layer for each ticket.

### Fix options (historical, September autofix-only proposal)

These options predate the 2026-10-07 scope expansion. They are input, not the
plan: (a) on its own does not satisfy the acceptance criteria above.

- **(a) Originally recommended: normalise headings in `parse_analysis`.** Shift the whole
  body's headings down so the shallowest one is `###`, keeping their relative
  depth. Skip fenced code blocks. Also tell the analyst prompt to use `###`
  or deeper, but do not rely on that alone, because the analyst does not always
  follow formatting instructions. A unit test on `parse_analysis` with an
  H2-headed reply covers it.
- **(b) Rejected: relax only `validate` to accept a leading H2.** That silences
  the warning while prompts and PR bodies keep losing the content.
- **(c) Optional, independent of (a):** have the `empty-description` warning
  name the H2 it found right after `## Description`, for example "Description
  is empty — the next line is `## What broke`, which ends the section; demote
  it to `###`". Then the next person does not have to trace this again.

Existing tickets are not rewritten by (a). Demoting the H2s inside
Description of non-terminal autofix tickets to `###` fixes them. That is a
one-line-per-heading edit, and the downstream repo has done it for its own.
Upstream's are yours to decide. Repairing existing tickets was not settled at
authoring time. If the implementer leaves it out, name it in the PR as a
follow-up for the owner, not a silent omission.

### Authoring review notes

The cold review flagged risks that the owner accepted at authoring:

- `code/with-review` has no owner gate before code is written.
- The scope could be split into three tickets: the section contract plus
  validator, the autofix analyst body, and repair of existing tickets.

Because of that, keep the change focused, and make the contract decision and
its tradeoffs prominent in the PR so peer-review and the owner can judge them.

Filed from the downstream admin repo
(`admin/validate-drift-empty-description-two-cli-created-a`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/980
branch: ticket-body-sections

## Contract decision (implement, 2026-10-08)

**Relocate, not compose.** Only `## Description` and `## Context` compose; any
other `##` above the fence is *uncomposed* and must move under one of them as
`###` (or below the fence). Reasons: it is already the documented contract
(coga/tickets, `_template/ticket.md`, `bootstrap/ticket`, `code/design`); an
allowlist of "intent" names (Acceptance Criteria, Proposed Shape, Out of
Scope, ...) would need a growing vocabulary (the live tree uses ~40 distinct
H2s above the fence) and still drop the next new one; composing every H2
would pull operational material (`## PR`) into intent. Tradeoff: existing
tickets need a one-line-per-heading demote; the new warning names each one.

Making the drop non-silent:
- One shared fence-aware parser `taskfile.body_sections` used by compose,
  validate, `open_pr` (replaces `open_pr._sections`) and the create-time
  description check. Headings inside backtick/tilde code fences are text;
  below the blackboard fence is never inspected (split_body first).
- `coga validate` warns `uncomposed-section` (warn, non-terminal tickets),
  naming every heading and the repair. `## PR` is exempt (legacy
  operational PR preparation read by `open_pr`).
- `coga launch` (spawn + `--prompt-report`) prints the same warning.
- `create_task` rejects a section heading in `description` (all callers), not
  only the CLI.
- Autofix: `parse_analysis` shifts analyst headings so the shallowest is
  `###` (fence-aware), plus a prompt instruction.
- Existing upstream tickets are NOT rewritten here: follow-up for the owner.

## Implement handoff (2026-10-08)

Pushed `ticket-body-sections` (5ab6c9cdd on 7d7ff3309). Implemented the plan
above as recorded; no deviations from the contract decision.

- Shared parser: `taskfile.body_sections` / `markdown_lines` (fence rules match
  `blackboard._without_superseded_designs`: backtick opener info may not hold a
  backtick; closer is same char, >= length, no tail). Replaces
  `compose._SECTION_HEADING_RE`, `open_pr._sections`' own loop (now a thin
  wrapper; last duplicate still wins there, first wins in compose as before),
  `commands/create._SECTION_HEADING_LINE_RE`, and `create_task`'s
  `## Context` regex. Behavior deltas: a fenced `##` in `--description` is now
  allowed; a bare `##` line ends an `open_pr` section (it already did in
  compose).
- Cases pinned: fenced heading = text (compose, validate, create tests);
  below-fence heading never a body section (compose blackboard + validate
  `## Dev`); legacy `## PR` above the fence exempt from the warning and still
  read by `open_pr` (existing open_pr tests unchanged/green).
- `empty-description` now says "see `uncomposed-section`" instead of
  "title-only / cancel" when the body has uncomposed sections; Dream
  validate-drift classifies `uncomposed-section` as pr-proposal (demote) and
  tells the `empty-description` handler to check for it first.
- Existing tickets NOT rewritten (follow-up for owner). At this head, repo
  `coga validate` flags one live ticket:
  `autofix/name-cross-repo-retire-follow-ups-with-the-repo-th`.
- Not done: text *before* the first `##` above the fence is also uncomposed and
  still unwarned; left out to keep scope.
- 3.11 gap: `python3.11` exists here but has no deps (no yaml/pytest), so all
  receipts are 3.12.12.


## Peer review (2026-10-08)

Rebased onto origin/main 86f073660 first (only ticket bookkeeping ahead;
clean) -> 41201ccb0. Claude Code `/code-review` (default effort, forked
agent, same model as the implementer, so self-review, not independent) ran
on `main...ticket-body-sections` at 41201ccb0 and **returned** 8 findings:

- FIXED #1/#2: an unclosed code fence hid every later heading, so `## Context`
  (including the one `create_task` appends after a description ending in an
  open fence) folded into Description. `markdown_lines` now treats an opener
  never closed as plain text (re-scans with it ignored).
- FIXED #6: `## Description ##` and 1-3 space indented headings are now
  parsed per CommonMark.
- FIXED #5: Dream got both a pr-proposal (uncomposed-section) and a
  human-needed escalation (empty-description) for the autofix shape. Validate
  now omits empty-description while uncomposed sections exist; it resurfaces
  after the demote if Description really is empty. Doc + twin updated.
- NOT FIXED #3 (nit): a bare `##` line now ends an `open_pr` section; it
  renders as an empty heading, so this matches Markdown.
- NOT FIXED #4 (out of scope): `workflow._parse_inline_sections` still
  splits on a fence-unaware `##` regex. Follow-up candidate for the owner.
- NOT FIXED #7/#8 (nits): the CLI runs the description check twice
  (pre-check and inside create_task); compose hard-codes Description/Context
  instead of reading `taskfile.COMPOSED_SECTIONS`.

The fixes landed in 939c4813f after the review; that delta (taskfile parser,
validate, dream remediation, docs twin, tests) was self-reviewed in-session
only, not re-run through /code-review. No TTY/rendered surface is touched
beyond CLI warning text, which tests assert.
Note: the review agent switched the checkout to main mid-way through a suite
run; that run was discarded and the suite was rerun from a clean state.

## PR

```yaml
title: "Warn on and stop losing ticket sections at H2 boundaries"
author: "claude"
author_evidence: "Implement and peer-review sessions ran as Claude Code (claude-opus-5-5) under megalaunch; see implement handoff and peer review."
head: "939c4813fc4eed5161be591e8c880b1623f2ee59"
base: "86f073660a107948b0a527d88f5f088b31796e8d"
depth: "deep"
rationale: "Changes a core ticket contract surface (compose, validate, open_pr snapshot, create guard, launch warning) and makes the relocate-vs-compose decision; review was self-review by the implementing model, and the final fix commit was not re-run through a review tool, so the owner should check the decision and the shared fence-aware parser."
implementation: "Keeps the two-section compose contract (relocate, not compose) and makes the drop loud. One fence-aware parser taskfile.body_sections feeds compose, validate, open_pr and create; an unclosed fence is not a fence, and headings follow CommonMark indent and closing-sequence rules. coga validate warns uncomposed-section naming each extra `##` above the fence (## PR exempt as operational), and reports it instead of empty-description when both apply; launch and --prompt-report print it. create_task rejects a `##` description line for every caller. Autofix parse_analysis demotes analyst headings so the shallowest is ### (fenced code untouched) and the analyst prompt asks for ###."
deviations: "None from the blackboard contract decision. Peer review changed empty-description from a redirect message to suppression while uncomposed sections exist, so Dream does not escalate the same ticket to a human."
limitations: "Existing tickets are not rewritten (one live ticket, autofix/name-cross-repo-retire-follow-ups-with-the-repo-th, now warns; owner follow-up). Prose before the first `##` heading is also uncomposed but is not warned. workflow._parse_inline_sections still uses a fence-unaware `##` splitter (follow-up). No Python 3.11 run (interpreter present without dependencies)."
files:
  src/coga/taskfile.py: "Shared fence-aware body_sections/markdown_lines parser (unclosed fences are text; CommonMark heading indent and closing run) plus uncomposed-section helpers and wording."
  src/coga/compose.py: "_extract_section reads the shared parser; drops its own regex."
  src/coga/validate.py: "New uncomposed-section warning; empty-description only when no uncomposed sections exist."
  src/coga/open_pr.py: "_sections delegates to the shared parser so the PR snapshot matches the prompt."
  src/coga/create.py: "description_structure_problem guard moved into create_task for every caller; Context detection via shared parser."
  src/coga/commands/create.py: "CLI reuses the moved guard."
  src/coga/commands/launch.py: "Prints the uncomposed-section warning at spawn and --prompt-report."
  src/coga/recurring_autofix.py: "demote_headings in parse_analysis and an analyst prompt instruction to use ###."
  src/coga/dream_validate_drift.py: "Classify uncomposed-section as a PR proposal; empty-description remediation names it."
  docs/contexts/coga/tickets/SKILL.md: "Owns the relocate contract, the warning, and the shared parser rules."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: "Packaged twin."
  docs/contexts/coga/prompt-composition/SKILL.md: "Composition reads the fence-aware parser and warns instead of dropping silently."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: "Packaged twin."
  docs/contexts/coga/codebase/gotchas/SKILL.md: "create_task now guards description for every caller."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/gotchas/SKILL.md: "Packaged twin."
  docs/contexts/coga/recurring/autofix/SKILL.md: "Documents analyst heading demotion."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: "Packaged twin."
  coga/skills/code/design/SKILL.md: "Names the validate warning for sibling spec sections."
  src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md: "Packaged twin."
  coga/skills/code/review-design/SKILL.md: "Reviews spec as ### subsections under Description; separate ## is a must-fix."
  src/coga/resources/templates/coga/bootstrap/skills/code/review-design/SKILL.md: "Packaged twin."
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: "review-design section names spec subsections, not sections."
  coga/tasks/_template/ticket.md: "Template explains ### subsections and the warning."
  src/coga/resources/templates/coga/tasks/_template/ticket.md: "Packaged twin."
  tests/test_taskfile.py: "Parser regressions for unclosed fences, CommonMark indent/closing run, and `## C#` text."
  tests/test_compose.py: "Manual spec ticket composes exact Description/Context text, fenced ## kept, extra sections excluded; ### repair composes."
  tests/test_validate.py: "uncomposed-section names each heading, ignores fenced/blackboard/## PR; replaces empty-description; terminal silence."
  tests/test_create.py: "Fenced ## allowed in --description; create_task rejects ## for programmatic callers; unclosed fence keeps a real Context."
  tests/test_recurring_autofix.py: "parse_analysis demotion; H2-headed analyst reply composes in full into task_description."
  tests/test_launch.py: "--prompt-report prints the uncomposed-section warning."
  tests/test_dream_validate_drift.py: "uncomposed-section classified as pr-proposal."
review:
  reviewer: "claude"
  kind: "self"
  status: "failed"
  head: "41201ccb03834458e248770bd3a414285b6cedb4"
  base: "86f073660a107948b0a527d88f5f088b31796e8d"
  detail: "Claude Code /code-review (claude-opus-5-5, forked agent, same model as implementer). Review returned with findings at the recorded historical head (failed); 8 findings; #1/#2/#5/#6 fixed in 939c4813fc4eed5161be591e8c880b1623f2ee59; #3/#4/#7/#8 left as nits/follow-ups. The receipt covers 41201ccb0, not the final head; the fix delta was self-reviewed in-session only."
checks:
  - command: "PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider  (Python 3.12.12)"
    status: "passed"
    head: "939c4813fc4eed5161be591e8c880b1623f2ee59"
    base: "86f073660a107948b0a527d88f5f088b31796e8d"
    detail: "3419 passed in 368.82s."
  - command: "cd example/coga && env -u SLACK_WEBHOOK_URL coga validate --json  (PYTHONPATH=$PWD/src)"
    status: "passed"
    head: "939c4813fc4eed5161be591e8c880b1623f2ee59"
    base: "86f073660a107948b0a527d88f5f088b31796e8d"
    detail: "ok_count 4, no issues."
  - command: "python3.11 -m pytest"
    status: "not-run"
    detail: "python3.11 is installed but has no yaml/pytest; no 3.11 environment available."
```

## Open PR handoff (2026-10-08)

Publication preflight accepted the branch: control advanced only through
non-overlapping task/log state. Corrected the preparation record to the
supported review kind `self` and status `failed` for the historical review
that returned eight findings; its later fixes and final-head review limits
remain explicit. Quoted YAML scalar values to preserve literal heading and
finding markers. No new review or test execution is claimed by this step.

Opened and verified https://github.com/FastJVM/coga/pull/980 against `main`
from `ticket-body-sections`; `pr:` is recorded under Dev. The generated PR
retains the full ticket snapshot, prior check receipts, and historical
self-review limitations with a deep-review recommendation. Ready for the
owner review gate.
