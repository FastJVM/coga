---
slug: wire-eval-ticket-diagnostic-into-ticket-step6
title: Finish eval/ticket-diagnostic and route bootstrap/ticket Step 6 through it
status: draft
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- dev/code
- coga/codebase
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

The `eval/ticket-diagnostic` skill is an unfinished stub: its Eval axes are
good, but its Process section is a placeholder and it is never actually invoked.
Meanwhile `bootstrap/ticket` Step 6 ("Run the evaluator review") carries its own
bespoke inline ticket-critique — a second, hand-maintained copy of "how to
evaluate a ticket." Finish the diagnostic so it evaluates the **composed** launch
prompt (via `coga launch --prompt-report`), then route Step 6 through it as a
**hybrid**: delegate the rubric to the diagnostic *and* keep an open
"anything else worth questioning?" catch-all. Result: one source of truth for
the evaluation rubric, evaluated against the real composed prompt.

## Context

Current state (verified against source 2026-07-18):

- `eval/ticket-diagnostic` lives **only** in the packaged tree at
  `src/coga/resources/templates/coga/bootstrap/skills/eval/ticket-diagnostic/SKILL.md`
  (no live `coga/skills/eval/ticket-diagnostic/` copy exists). Its Process
  section is a stub — it literally contains the line
  `- Compose the ticket calling coga launch without launching it <<YOU NEED TO BE MORE SPECIFIC HERE>>`
  (~line 21). Its frontmatter `description:` is just "Ticket evaluation tool".
- `bootstrap/ticket` Step 6 ("Run the evaluator review",
  `.../skills/bootstrap/ticket/SKILL.md`, ~lines 275-299) spawns a fresh
  subagent handed the ticket **path** plus six ad-hoc questions, and writes the
  result to a `## Evaluator review` blackboard section. This duplicates the
  diagnostic's rubric — a DRY problem per CLAUDE.md ("Do not leave the durable
  explanation only in chat/PR/task notes when it belongs in a context,
  template, README, or spec").

The concrete "compose without launching" primitive the stub is gesturing at:

- `coga launch <slug> --prompt-report` (option defined at
  `src/coga/commands/launch.py:98`; report path 160-174) composes the full
  prompt layers + approximate token counts and **exits without launching**
  (`compose_prompt_report` / `_format_prompt_report`). Evaluating this — not the
  raw ticket — is the point: attached contexts are inlined here, so the
  Knowledge/bloat axis can only be judged honestly against it.
- The token estimate is chars/4 (`src/coga/compose.py:estimate_tokens`), fine
  for relative bloat comparison, not exact tokenizer parity (the report says so).
- `--prompt-report` **bails on script tasks** with "script tasks do not compose
  an agent prompt" (`launch.py:162`). The diagnostic must detect that and
  evaluate the ticket file alone in that case.

Proposed change (grounded in an A/B eval run on 3 tickets — review stage plus a
downstream two-agent "would they agree on done?" proxy):

1. **Finish `eval/ticket-diagnostic` Process.** Run in a fresh subagent; get the
   composed prompt via `coga launch <slug> --prompt-report`; evaluate *that*
   against the existing axes (Objective/Done/Scope/Knowledge/Workflow fit/
   Safety); handle the script-task bail by evaluating the ticket file alone;
   output the already-specified `### <Axis> — GAP` + `Recommendation:` shape.
   Also give the frontmatter `description:` a real one-line summary.
2. **Route Step 6 through it, as a hybrid.** Replace Step 6's bespoke inline
   critique with "run `eval/ticket-diagnostic` against this ticket via a fresh
   subagent; write its output verbatim to `## Evaluator review`." **Keep** an
   open "anything else worth questioning?" line.

Why hybrid, not pure substitution (eval evidence): the diagnostic's fixed axes
reliably add value the inline review missed — e.g. its Done axis caught a
concrete factual error (a ticket emitting a field that does not exist on the
target data structure) that propagated into the implementer's plan, and its
composed-prompt Knowledge check produces precise "drop this specific context"
bloat cuts. But the inline review's open "assumptions to question" catch-all
uniquely caught off-axis gaps a fixed rubric skips (e.g. a missing canonical
context). Adopt the axes + composed-prompt check AND keep the open question.

Live/packaged sync (per CLAUDE.md): shipped coga OS skills exist in both the
live `coga/` tree and the packaged `src/coga/resources/templates/coga/` tree;
edits must keep both in sync. `eval/ticket-diagnostic` currently has only a
packaged copy — decide during implementation whether to add a live
`coga/skills/eval/ticket-diagnostic/` copy. Verify whether `bootstrap/ticket`
has a live copy that also needs the Step 6 edit.

Out of scope: changing the axis rubric itself (it is fine as written); and the
deeper eval-methodology idea of having probe agents implement a stub and diff
the results (a separate improvement to how we measure ticket quality, not this
change).

Scope note: this ticket was authored by hand because the filer is on Windows and
the `coga` CLI cannot run there (see `fix-windows-cli-import-crash`). It was not
run through `coga validate`; a teammate on Unix (or the filer in WSL) should
`coga validate --task wire-eval-ticket-diagnostic-into-ticket-step6` before
launch. No code or skill files were changed in creating this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
