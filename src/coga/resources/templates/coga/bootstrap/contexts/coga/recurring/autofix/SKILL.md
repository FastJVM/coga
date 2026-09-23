---
name: coga/recurring/autofix
description: The post-sweep autofix loop — the built run record, the one-shot text-only analyst, autofix tickets, template-damage detection, operator knobs, and why the loop never changes the sweep's exit code.
---

# Recurring autofix loop

Under cron nobody reads the sweep's console, so every `coga recurring` sweep —
and every `coga recurring launch <name>` (hence `coga dream`, `coga autoclose`,
`coga skill-update`) — ends with one analysis of what happened
(`src/coga/recurring_autofix.py`). It runs after a sweep with nothing due and
after one that died partway. A gate that refused to launch (closed or parked
template, period already handled on control) is not a run and is not analyzed.
The console output is unchanged.

## The loop

1. **The run record is built, not scraped.** Per period task: how the launch
   ended (clean, timed out, failing `ticket.py`, unfinished, refused by
   `--force`, or `damaged-template`), the status afterwards, and the period
   **blackboard**, plus templates that failed to load and sweep notes. Tee-ing
   fd 1 would make `isatty` false and break every agent launch, so the
   blackboard — the only durable per-run channel — is what carries detail.
   Successful runs contribute a report only if they write one; failures follow
   the reporting contract in [templates](../templates/SKILL.md).
2. **One one-shot agent call reads it** and answers `ok`, `duplicate`, or
   `problem` plus a ticket body. It is the only place Coga spawns an agent
   without a PTY: text in, text out, no REPL, no lifecycle, told not to mutate
   anything; Coga performs every write. Open `autofix/` tickets are included in
   the prompt so a nightly failure answers `duplicate` instead of minting a
   ticket a night.
3. **A `problem` becomes an `active` ticket** under `coga/tasks/autofix/` on the
   `code/with-self-review` workflow, with the run record committed beside it as
   `run-log.md`. The next `coga megalaunch` picks it up; the human gate is the
   workflow's owner PR review, and a transient finding closes through the
   already-satisfied path.

Two properties keep a broken analyst from breaking the sweep:

- **It never changes the sweep's exit code.** A timeout, non-zero exit or
  missing CLI is loud on stderr and nothing more.
- **It fails toward surfacing.** An unparseable reply is treated as a problem
  carrying the raw text.

Whatever a run writes to its period blackboard travels verbatim into the prompt
and possibly a committed `run-log.md`; never write a secret there.

## Template damage

Independent of the analyst: immediately before dispatch the runner snapshots
the template's Description (bytes above its single blackboard fence) and
compares after the firing. A change, or a template no longer readable with
exactly one fence, records `damaged-template` and prints a stderr warning even
with `COGA_AUTOFIX=0`. `coga validate` separately reports
`recurring-template-fence`. Repair from git history before the next firing and
keep cross-run notes below the single fence; merely appending a fence would turn
the last run's output into the next run's instructions.

## Operating it

- `COGA_AUTOFIX=0` (or `false`/`off`/`no`) disables analysis and ticketing, not
  the damage warning or validation. `COGA_AUTOFIX_TIMEOUT` (seconds, default
  300, `<= 0` disarms) is one deadline shared by the first call, the auth probe
  and any retry.
- Every run record is written to gitignored `.coga/recurring-runs/<stamp>.md`,
  ticketed or not; temp-control scans copy it back to the durable workspace.
- `coga run autofix-analyze [<run-log.md>] [--dry-run]` re-analyzes a record
  (default: the newest).
- Analyst agent: `--agent` on `coga recurring` or `autofix-analyze`, else the
  shared-only `[autofix] agent` key in `coga.toml` (must name a configured
  type; validated at config load), else the first-declared `[agents.*]` table.
- The one-shot argv is built in for `claude` and `codex`; another CLI needs
  `[agents.<name>].analyze` (e.g. `"-p {prompt}"`) or the loop skips loudly.
- The analyst's stdin is `/dev/null` (`codex exec` would append piped stdin).
  A non-zero exit is reported with both `stdout:` and `stderr:` tails.
- If an ambient `ANTHROPIC_API_KEY` call fails for authentication or billing,
  and `claude auth status` (with the key removed) confirms a first-party Pro,
  Max, Team or Enterprise login permitted by local policy, the analyst makes one
  announced subscription retry. Not for a custom `analyze` argv,
  `ANTHROPIC_BASE_URL` or `ANTHROPIC_CUSTOM_HEADERS`, other CLIs, or unrelated
  failures.
