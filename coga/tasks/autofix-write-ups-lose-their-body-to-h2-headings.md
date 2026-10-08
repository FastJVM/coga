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
step: 1 (implement)
launch_generation: 3af3b48d-d587-40ea-b6e7-91ba56a54b15
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
