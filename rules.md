# Global rules

Rules inlined into every task prompt at launch time. Keep this file short,
stable, and universal — rules that apply to every kind of work in every
project. Project-specific rules belong in `<project>/.relay/context.md`,
domain-specific rules belong in `contexts/`.

## Secrets

- Never write secrets to files. Credentials live in env vars, referenced
  from `relay.local.toml` and injected by `relay launch`.
- Never echo secrets to the blackboard, the log, or stdout.

## Files

- Prefer editing existing files over creating new ones.
- Never edit `log.md` directly. It is written by CLI commands only.
- In `ticket.md`, only edit the `contexts` field. Status, assignee, step,
  and workflow changes happen through CLI commands or direct human edits.

## Blackboard

- Write early, write often. An agent that writes to the blackboard is
  recoverable across sessions; one that does not is not.
- When in doubt, write a finding. Future sessions will thank you.

## Escalation

- If you are blocked and cannot proceed, call `relay panic` with a concrete
  reason. Do not loop, do not speculate, do not leave questions in the
  blackboard hoping someone will see them.
