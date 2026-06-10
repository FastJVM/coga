The blackboard is a notepad to be written to often as the human and agent works through a task.


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
