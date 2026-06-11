The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: dev-testing-contract
worktree: /home/n/Code/codex/relay-dev-testing-contract

## Implement plan (2026-06-10, confirmed by nick)

1. New skill `relay-os/skills/dev/testing-setup/SKILL.md` — establishment
   procedure only: discover conventions (CI config, manifests, Makefile,
   docs), never invent commands, write the contract as a project-local
   context `dev/testing` with five declared sections (unit-test command,
   validation commands, fixture/external-service rules, known-failure
   policy with must-surface wording, CI parity) plus consumption rules.
2. Dogfood: write Relay's own contract at
   `relay-os/contexts/dev/testing/SKILL.md` (nick: yes).
3. Update consumers `code/implement`, `code/implement-and-pr`,
   `code/self-qa` to read the contract instead of hard-coded
   `python -m pytest`, with exact-results reporting (nick: yes).

Discovery findings for Relay's contract: pytest (ini `pythonpath=["src"]`),
`relay validate --json`, packaging test skips without hatchling (dev/test
extra), seeded `example/` fixture, **no CI exists** — local commands are the
only gate. Python 3.11+ required (tomllib).


## Rescope + merge (2026-06-10)

Nick asked whether this ticket was stale. Findings: no `dev/` skill ever
shipped; sibling `add-dev-unit-test-writing-skill` (done, PR #331) decided
generic test-process skills are boilerplate and folded suite-conformance into
`code/implement`; the "imported testing skills" premise never materialized.

Decision (nick): rescope this ticket to the testing-contract piece and merge
the `add-dev-test-run-skill` draft into it.

- Ticket body rewritten: scope is now a minimal `dev/testing-setup` skill
  whose only output is a project-local testing contract (declared commands,
  fixture rules, known-failure policy, CI parity). No standalone runner
  skill; test-run's durable requirements survive as consumption rules
  (read the contract, report exact results).
- `add-dev-test-run-skill` deleted via `relay delete` (recovery: git
  restore). Its prior-art pointers are preserved in this ticket's Context.
- Dropped `relay/current-direction` from contexts — broad; nothing from it
  is needed for this scope.
