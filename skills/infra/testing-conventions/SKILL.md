---
name: infra/testing-conventions
description: Use when writing or modifying tests. Covers framework choices, file layout, naming, coverage expectations, and what to mock vs. hit for real.
---

# Testing conventions

Write tests before you consider a change done. Keep tests close to the
code they cover. Prefer integration tests that exercise real behavior
over mocks that pass for the wrong reason.

## Layout

- Unit tests live next to the code: `foo.ts` → `foo.test.ts`.
- Integration tests live in `tests/integration/<domain>/`.
- Fixtures live in `tests/fixtures/` — never in the unit test files.

## Mocking policy

- **Do not mock the database in integration tests.** Hit a real ephemeral
  instance. Mocked tests have passed in the past while the real migration
  was broken — we lost a weekend to that once, and we are not doing it
  again.
- External HTTP APIs: mock at the network layer (intercept requests),
  not by stubbing the client library. This catches client changes.
- Time: mock explicitly with a clock injection. Do not `Date.now()`
  directly in testable code.

## Naming

Descriptive, not implementation-detail. Good: "retries Stripe 429 with
exponential backoff". Bad: "test_retry_handler_case_3".

## Coverage

No hard percentage threshold. The question is "would a reasonable change
to this code break a test?" If no, write more tests. If yes, you are
done.
