---
name: coga/show
description: Render one task's ticket (frontmatter + body + blackboard) and its log history — the script-shaped home for the read-only `coga show` view.
script: run.py
---

# Show a task

This skill is the script-shaped home for `coga show`. The `coga show <task>`
command stays a thin Typer head that keeps the operand at the command layer; the
render itself lives in `coga.views.render_show` so it is reusable and
unit-tested. This skill exposes that same render in script-step shape.

The script imports `coga.views.render_show_from_env` and calls it directly, so
it does not depend on `coga` being on `PATH` inside the script environment.

Required environment:

- `COGA_VIEW_TARGET`: the task ref to render (a task ID, id-slug, or
  `bootstrap/<name>`) — the single operand `coga show` takes as `<task>`.
