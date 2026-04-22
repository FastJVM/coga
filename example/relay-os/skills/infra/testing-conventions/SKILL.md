---
name: infra/testing-conventions
description: How we write and run tests in this codebase.
---

# Testing conventions

- Tests live next to the code they test, in `*_test.py` files.
- Use pytest. Prefer fixtures over setup/teardown.
- Every bug fix gets a regression test first — make it fail, then fix.
- Integration tests hit a real Postgres via `docker compose up test-db`.
- Don't mock the database in integration tests.
