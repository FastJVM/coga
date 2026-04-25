---
# `name` matches the directory path under skills/. Always namespaced.
name: infra/testing-conventions
# `description` is what create-suggest matches against when a new task
# needs a workflow step skill. One sentence; concrete.
description: How we write and run tests in this codebase.
---

# Testing conventions

<!--
A skill is *process knowledge* — how to do something. It attaches to a
workflow step, not to a ticket. Keep it short and declarative — agents
do better with bullet points than long prose.
-->

- Tests live next to the code they test, in `*_test.py` files.
- Use pytest. Prefer fixtures over setup/teardown.
- Every bug fix gets a regression test first — make it fail, then fix.
- Integration tests hit a real Postgres via `docker compose up test-db`.
- Don't mock the database in integration tests.

<!--
If this skill ships with scripts, drop them next to SKILL.md and
describe when they run. The agent invokes them directly during
interactive/auto sessions; for `mode: script` tasks, `relay launch`
runs the first executable script with secrets injected as env vars.
-->
