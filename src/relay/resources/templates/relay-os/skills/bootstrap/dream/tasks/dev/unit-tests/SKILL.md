---
name: bootstrap/dream/tasks/dev/unit-tests
description: Run the repo-declared unit test command for dev/code work and summarize exact failures without creating noisy passing PRs.
---

# Dev Unit Tests

This is a project-specific Dream worker template for code repos and dev/code
task surfaces. It runs the repo's declared unit test command, records exact
results, and proposes follow-up only when there is actionable evidence.

Do not run this worker for non-engineering Dream work. Dream can bootstrap this
template into a project, but the worker is active only when that project is a
code repo that declares a unit test command.

## Project Convention

Each code repo that wants this worker must declare the command in
`relay.toml`:

```toml
[dream.dev.unit_tests]
command = "python -m pytest"
# Optional: markdown file listing accepted baseline failures by test name,
# failure heading, or stable issue link.
known_failures = "docs/known-test-failures.md"
```

The command is project-specific. Do not substitute Relay's own Python test
command, and do not guess from files such as `pyproject.toml`, `package.json`,
or `pom.xml`. If the repo needs environment setup, declare a wrapper command
owned by the repo, for example `command = "scripts/test-unit"`.

If `known_failures` is present, read it before running the tests. If the file is
missing, report that as configuration drift and continue to label failures
`unknown` rather than `known`.

## Missing Configuration

If `[dream.dev.unit_tests].command` is missing or empty, fail loud and stop.
Append this section to the Dream run blackboard:

```
## Dream Worker: dev/unit-tests
Status: human-needed

Missing configured unit test command.
Add this to relay.toml for code repos that want this dev worker:

[dream.dev.unit_tests]
command = "<repo-specific unit test command>"

This worker is dev/code-only; non-engineering Dream work does not need a unit
test command.
```

Do not run a default test command.

## Running Tests

Run the configured command from the repo root. Record the exact command before
running it and preserve the exit code.

```
<configured command>
```

If the command needs secrets, production data, or a non-local service, stop and
ask the human. Unit tests should be local and deterministic enough for a Dream
maintenance run.

## Failure Classification

Summarize every failure with exact evidence:

- failing test name or runner heading
- file path and line number when the runner reports one
- failure message or assertion heading
- exact command
- exit code
- classification: `known`, `new`, or `unknown`
- evidence for the classification

Classification rules:

- `known` — the failure matches the configured `known_failures` file or another
  explicit project-owned baseline referenced from that file.
- `new` — the failure does not match known-failure evidence and there is a
  recent passing Dream, CI, or release baseline for the same command.
- `unknown` — no trustworthy baseline exists. Do not call a failure new just
  because this worker has not seen it before.

When the runner output is too large, keep the stable failure headings and the
smallest output slice needed to identify each failure. Do not paste the entire
test log into the blackboard.

## Output

Append a section to the Dream run blackboard:

```
## Dream Worker: dev/unit-tests
Generated: <timestamp>
Scope: dev/code only
Command: <configured command>
Exit code: <exit-code>
Known-failures source: <path or none>

### Result
passed | failed | human-needed

### Failures
<one item per failing test with exact name, file/line if available, message,
classification, and classification evidence>

### Commands Run
<exact command and relevant output>

### Proposal
<follow-up ticket, PR recommendation, or no-op>
```

For a passing run, write a concise no-op result and do not open a PR just to
report success:

```
### Result
passed

### Proposal
No action. Unit tests passed.
```

For failures, propose the smallest useful next action:

- create or update a ticket when the failures need human prioritization
- open a PR only when the worker also made a repo-owned fix or fixture update
- leave a no-op note when every failure is known and already tracked

Do not hide failures by updating the known-failures file. That file is
project-owned baseline evidence, not an agent escape hatch.
