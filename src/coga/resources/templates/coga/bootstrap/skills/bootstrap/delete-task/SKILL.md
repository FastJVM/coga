---
name: bootstrap/delete-task
description: Remove a task directory from the working tree — the contract behind `coga delete` and the `delete-task` registered recipe.
---

# Delete a task

Use `coga delete <slug>` or the `delete-task` recipe to remove the local
ticket file or its owned directory and attachments. Check the resolved task
before deleting it. A previously committed ticket can be recovered with
`git restore`. Commit the deletion when you want it to travel with other
changes.
