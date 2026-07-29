---
name: coga/show
description: Explain the read-only `coga show` view, which renders one task's ticket and log history.
---

# Show a task

Use `coga show <task>` to render a task's frontmatter, body, blackboard, and
append-only log history. The command is a thin Typer head; the reusable,
unit-tested implementation lives in `coga.views.render_show`.

This is a read-only view. It does not mutate task state.
