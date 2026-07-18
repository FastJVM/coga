---
slug: make-ticket-script-form-works
title: make ticket script form works
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Extend the `bootstrap/ticket` interview skill so it can author **script-backed
tickets**. The launch runtime already fully supports them — `script: inline` (a
fenced block in a `## Script` body section, kept as a single-file task) and
`script: <file>` (a sibling script file in directory form) both resolve and run
today. What's missing is an *authoring path*: `coga create` exposes only title
and workflow, and this interview never asks about scripts, so the only thing
that currently produces a script ticket is recurring templates.

Add an interview step that asks whether the ticket should run a script and, if
so, helps author it: choose **inline vs sibling-file** by the script's
size/nature, set the `script:` frontmatter accordingly, and write the
`## Script` block (inline) or create the sibling script file and convert the
draft to directory form (sibling). Done = running `coga ticket` on a new title
can produce a valid script ticket that `coga launch` then executes as a script.

## Context

**Scope:** interview skill only. We are *not* adding a `coga create --script`
CLI flag — the interview agent edits ticket files directly, so it doesn't need
one. A CLI flag, if ever wanted, is a separate ticket.

**Edit target (source of truth):**
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
This skill is a bundled battery — there is **no** live `coga/skills/bootstrap/
ticket/` copy to keep in sync. The `.venv/.../coga/resources/...` copy is an
install mirror; do not edit it.

**Runtime contract to target (already implemented — do not change it):**
- `script:` is three-way (`src/coga/ticket.py:137`, `Ticket.script`):
  `inline` → fenced block in the body's `## Script` section, task stays a single
  `tasks/<slug>.md` file; a filename (`run.sh`, `run.py`) → sibling file in a
  `tasks/<slug>/` directory next to `ticket.md`; `null`/absent → agent task.
- Resolution + dispatch live in `src/coga/commands/launch_script.py`
  (`is_script_launch`, `_resolve_ticket_script`, `_resolve_inline_script`).
- `create.py:145` (`needs_dir`) already branches: an inline script keeps
  file-form, a named script file forces directory-form. `create_task()` accepts
  a `script` arg; the interview agent can mirror that logic by editing files.
- Script command selection (`build_script_command`, launch_script.py:108): a
  `.py` runs under the active interpreter, an executable file runs directly,
  else `sh`. The inline `## Script` fence language should reflect this.

**Inline case needs a new section:** `coga/tasks/_template/ticket.md` has **no
`## Script` section** today, so the skill must instruct the agent to add one to
the body (above the blackboard fence) — that's exactly where
`_resolve_inline_script` reads the fenced block from.

**Directory-conversion subtlety (sibling-file path is the fiddly one):** a draft
scaffolded as a bare `tasks/<slug>.md` must be moved to `tasks/<slug>/ticket.md`
with the script as a sibling when the human picks a sibling-file script. Inline
scripts need no move. Because the interview agent hand-edits files (it does not
reuse `create_task`'s directory logic — that would need the deferred CLI flag),
arm the skill with these safety nets:
- Run `coga validate` after the conversion to catch a malformed move.
- Executable-bit: `build_script_command` runs `.py` under the interpreter and a
  non-executable file under `sh`. A bare `run` file with no extension needs
  `chmod +x` (or it won't dispatch as intended) — call this out.
- The `slug:` frontmatter does **not** change on the bare-file → directory move
  (the id_slug is the leaf either way), so tell the agent not to "fix" it.

**Fit the existing interview shape:** fold this into the current steps (around
the step-3 workflow / step-5 context questions) rather than bolting on a heavy
new phase — the interview is meant to stay short (4–6 questions). Only ask about
scripts when the task actually looks script-shaped.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
