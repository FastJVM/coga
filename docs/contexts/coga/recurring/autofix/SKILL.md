---
name: coga/recurring/autofix
description: The post-sweep autofix loop — the built run record, the one-shot text-only analyst, autofix tickets, template-damage detection, operator knobs, and why the loop never changes the sweep's exit code.
---

# Recurring autofix loop

Under cron nobody reads the sweep's console, so every `coga recurring` sweep —
and every `coga recurring launch <name>` (hence `coga dream`, `coga autoclose`,
`coga skill-update`) — ends with one analysis of what happened. It runs after a sweep with nothing due and
after one that died partway. A gate that refused to launch (closed or parked
template, period already handled on control) is not a run and is not analyzed.
Neither is a sweep on an inactive repo that launched nothing; the
[inactivity](../scheduling/inactivity/SKILL.md) topic owns when autofix runs
there.
The console output is unchanged.

## The loop

1. **The run record is built, not scraped.** Per period task: how the launch
   ended (clean, timed out, failing `ticket.py`, unfinished, refused by
   `--force`, or `damaged-template`), the status afterwards, and the period
   **blackboard**, plus templates that failed to load, failures observed
   outside the launch loop (on a `coga recurring` sweep: failed create syncs,
   periods created but never launched, watchdog pauses) under
   `## Unresolved recurring failures`, and sweep notes. Console output is not
   captured, so the blackboard — the only durable per-run channel — is what
   carries detail.
   A launch that refuses before `ticket.py` runs leaves that blackboard
   blank, so the record carries the refusal's message as the outcome's note.
   Successful runs contribute a report only if they write one; failures follow
   the reporting contract in [templates](../templates/SKILL.md).
2. **One one-shot agent call reads it** and answers `ok`, `duplicate`, or
   `problem` plus a ticket body. It is the only place Coga spawns an agent
   without a PTY: text in, text out, no REPL, no lifecycle, told not to mutate
   anything; Coga performs every write. Open `autofix/` tickets are included in
   the prompt so a nightly failure answers `duplicate` instead of minting a
   ticket a night.
3. **A `problem` becomes an `active` ticket** under `coga/tasks/autofix/` on the
   `code/with-review` workflow, so the main agent's peer reviews the code,
   with the run record committed beside it as `run-log.md` and the repo's
   configured default contexts attached (see Operating it below). When no
   `other-agent` peer resolves for the default agent at creation (a
   single-agent install), the ticket uses `code/with-self-review` instead and
   the sweep says so on stderr, rather than minting a ticket that would stall
   at `unresolvable-step-assignee`. Coga supplies this metadata; the analyst
   supplies the finding. The analyst's body becomes the ticket's `## Description`, with
   headings demoted so the shallowest is `###`, because a `##` would end that
   section and drop the rest of the write-up from every launch prompt
   ([coga/tickets](../../tickets/SKILL.md), Body regions). The next
   `coga megalaunch` picks it up; the human gate is the
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
  type; validated at config load), else `Config.default_agent()`: the
  `default_agent` key (local over shared), else the first-declared
  `[agents.*]` table.
- Generated-ticket contexts: optional shared-only `[autofix] contexts` in
  `coga.toml`, a list of non-empty context refs, for example
  `contexts = ["coga/upstream", "team/triage"]`. Coga attaches them in
  declaration order to every newly generated `autofix/` ticket; existing
  tickets keep their contexts. An absent table/key or `contexts = []` attaches
  none, and a contexts-only table keeps the agent fallback above. Non-string
  or blank entries fail config loading. Errors for these defaults name
  `[autofix].contexts` and the offending value or ref, including invalid local
  overrides under a relocated root. Every ref must resolve at config load
  through the [context layout](../../context-layout/SKILL.md): the
  effective local root (including `[layout] contexts`) first, bundled fallback
  only when the local artifact is absent. An invalid local override is an
  error even when a bundled copy exists. A missing ref deliberately stops
  every config-loading command, surfacing bad policy before an unattended
  sweep. These defaults express the repo's triage policy; the text-only
  analyst does not choose contexts or mutate tickets.
- The one-shot argv is built in for `claude` and `codex`; another CLI needs
  `[agents.<name>].analyze` (e.g. `"-p {prompt}"`) or the loop skips loudly.
- A non-zero analyst exit is reported with both `stdout:` and `stderr:` tails.
- A `claude` analyst whose ambient `ANTHROPIC_API_KEY` fails for
  authentication or billing makes one announced retry on a confirmed
  subscription login. Spawn and retry details are in
  [recurring-autofix](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-autofix/SKILL.md).
