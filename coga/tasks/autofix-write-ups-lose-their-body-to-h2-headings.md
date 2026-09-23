---
title: Autofix tickets launch without their write-up when the analyst uses H2 headings
status: draft
owner: nicktoper
workflow: null
---

## Description

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

## Context

### Mechanism (verified against `origin/main` c2268b05, 2026-09-22)

- `compose._extract_section` matches `_SECTION_HEADING_RE`
  (`^##\s+(.+?)\s*$`) and ends a section at the next match. `_template/ticket.md`
  states the contract: only `## Description` and `## Context` carry over, and
  any other heading above the fence is not composed.
- `_extract_section` has three consumers, and each one loses the content:
  - `compose`: the `task_description` and `task_context` layers.
    The agent's prompt loses the write-up.
  - `validate`: the `empty-description` check. Title-only is reported only
    when the body opens with an H2.
  - `open_pr`: when there is no `## PR` section it falls back to the
    Description, so a PR body opened from such a ticket is truncated too.
- `recurring_autofix`'s analyst prompt asks for a free-form
  "markdown body … Write it as the Description of a ticket". It gives no
  constraint on heading level. `parse_analysis` strips the `---` separator and
  passes the body through unchanged. `_ticket_description` appends the trailer
  and hands it to `create_autofix_ticket` as the description.
- Hand-authors already work around this. `recurring-sweep-wedges-on-the-ticket-py-it-copies`
  says "Everything below is `###` on purpose". The analyst has no such
  instruction.

### Evidence

- Upstream `origin/main`: `report-per-skill-outcomes-from-gh-skill-update-in`
  (4 H2s inside Description), `stop-one-failing-ticket-py-from-starving-the-rest`
  (3), `treat-non-requestexception-slack-send-errors-as-de` (3).
- Downstream: Dream 2026-W39's validate-drift flagged two active autofix tickets
  as title-only. Each actually had a full write-up under H2s. A third ticket
  opened with prose, so validate passed it, but it still lost three H2 sections.
  After those H2s were demoted to `###` by hand, `coga validate` reported no
  `empty-description`, and `--prompt-report` showed a 4.9–5.4 KiB
  `task_description` layer for each ticket.

### Fix options

- **(a) Recommended: normalise headings in `parse_analysis`.** Shift the whole
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
Upstream's three are yours to decide.

Filed from the downstream admin repo
(`admin/validate-drift-empty-description-two-cli-created-a`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
