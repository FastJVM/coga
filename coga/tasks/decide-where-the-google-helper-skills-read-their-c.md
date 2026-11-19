---
title: Decide where the Google helper skills read their credentials from
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 3 (open-pr)
agent: claude
launch_generation: pending:1a2aee91-551e-4dd6-b875-d223d7d77f04
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6, from the open decision in proposal PR #1263 (Google capability skills drift; Phase 3 shard ca-09, Phase 2 shard ks-28). The packaged helpers src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/gcal.py and coga/gmail/gmail.py read [calendar] and [gmail] tables from coga.local.toml, but Coga's config loader rejects those tables (any coga command in that checkout fails with ConfigError), and [extensions] is accepted only in shared coga.toml. PR #1263 documents this as a known gap without changing helper code. Options: allow [extensions] in coga.local.toml; a machine-local config directory (see parked _v2/add-a-first-class-relay-config-directory-for-machi); or per-ticket secrets: (env:VAR / op://) the helpers read from the environment (see coga/secrets). Decide, then change the helpers and the skills' setup docs together.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

branch: google-helpers-read-env-credentials

## Decision (implement step)

Helpers read credentials from **environment variables**, delivered by the consuming
ticket's `secrets:` (`env:VAR` or `op://`) per `coga/secrets`, or exported by the
operator for a manual run. Reasons: it is the existing credential model ("tickets
carry pointers, the machine carries values, config carries almost nothing"); it needs
no core change (microkernel: helpers stay at the edge); allowing `[extensions]` in
`coga.local.toml` would put literal tokens in config and widen the loader for one
consumer pair; the config-directory option is a parked `_v2` draft. Non-secret calendar
ids stay in shared `coga.toml` `[extensions.<ns>]`.

## Implement handoff

Done on `google-helpers-read-env-credentials` (pushed, head `087ea084e`, contains origin/main).

- `gcal.py`: `resolve_service_account_info()` reads `GCAL_SERVICE_ACCOUNT_JSON` (key
  contents; wins) else `GCAL_SERVICE_ACCOUNT_FILE` (path); builds creds with
  `from_service_account_info`. `tomllib`/`_coga_os_root` removed.
- `gmail.py`: `resolve_gmail_config()` reads `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`,
  `GMAIL_REFRESH_TOKEN`, `GMAIL_USER`, naming every missing var. `authorize` now prints
  `GMAIL_*=<value>` lines plus storage guidance instead of a `[gmail]` TOML block.
- Setup docs (`coga/google-calendar`, `coga/gmail`, `coga/calendar-reminder`) show the
  `secrets:` declarations; calendar-reminder now resolves the (non-secret) calendar id
  from shared `coga.toml` `[extensions.<ns>]` instead of a rejected `[calendar]` table.
- New `tests/test_google_helpers.py` (6 tests) covers env resolution, precedence, and that
  a `coga.local.toml` with the retired tables is ignored.
- No core change, no seeded-fixture change (helpers are edge skill attachments).

Adjacent, not fixed here (separate Dream findings ks-28/ks-29 in
`coga/tasks/recurring/dream/ticket.md`): the skills still tell callers to run
`$COGA_COGA_OS_ROOT/skills/coga/<skill>/<script>.py`, a path that no longer exists after
the package-definition cutover, and to `pip install` "from this skill's dir". No open
ticket owns that yet; retro should carry it.

## Peer review

Codex completed direct review of the final diff at `75d599dc9db16291ba6f0db7a79474a702a647c2` against
`25b98b15f137099c6a537db19af92e5ad0e54118`. Claude authored the implementation. Codex independently reviewed
that work and self-reviewed the follow-up commit.

- Fixed a Calendar credential-file decoding error that escaped the helper's
  diagnostic. Added regression coverage for non-UTF-8 files.
- Added migration instructions so operators can reuse their values and remove
  the retired local config tables.
- Parsed both documented `secrets:` examples with Coga's parser. Ran both
  helper commands in a PTY with their credential variables unset. Each named
  its missing variables and exited 1.
- 5011 passed and 33 skipped in 840.35 seconds. No unresolved findings within the credential migration scope.

## PR

```yaml
title: Read Google helper credentials from ticket secrets
author: claude
author_evidence: "Implement session ran as Claude Code (claude-opus-5-5) under megalaunch."
head: 75d599dc9db16291ba6f0db7a79474a702a647c2
base: 25b98b15f137099c6a537db19af92e5ad0e54118
depth: skim
rationale: "Bounded change to the shipped Google helpers and setup instructions. Existing installations\
  \ need to migrate credentials out of the retired local tables. Credential resolution and CLI\
  \ error handling were verified locally."
implementation: "Calendar reads GCAL_SERVICE_ACCOUNT_JSON or GCAL_SERVICE_ACCOUNT_FILE and reports\
  \ unreadable or non-UTF-8 key files. Gmail reads four GMAIL_* variables and authorize prints\
  \ the corresponding values. The setup instructions explain ticket secret declarations and\
  \ migration, and calendar reminders take the calendar ID from shared configuration."
deviations: "The implementation chose per-ticket secrets over expanding local configuration.\
  \ Codex added the Calendar file error handling and the migration instructions during review."
limitations: "No live Google API, OAuth browser flow, or 1Password call was exercised. The pre-existing\
  \ helper invocation path drift is tracked in the implement handoff."
files:
  src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/gcal.py: "Read the\
    \ service-account key from GCAL_SERVICE_ACCOUNT_JSON or GCAL_SERVICE_ACCOUNT_FILE."
  src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py: "Read OAuth credentials\
    \ from GMAIL_* env vars; authorize prints them."
  src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/SKILL.md: "Document\
    \ the env vars and secrets declaration."
  src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/SKILL.md: "Document the env\
    \ vars and secrets declaration."
  src/coga/resources/templates/coga/bootstrap/skills/coga/calendar-reminder/SKILL.md: "Point\
    \ setup at secrets and calendar id at [extensions]."
  tests/test_google_helpers.py: "Exercise environment credential resolution, precedence, retired\
    \ tables and unreadable key encoding."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 75d599dc9db16291ba6f0db7a79474a702a647c2
  base: 25b98b15f137099c6a537db19af92e5ad0e54118
  detail: "Codex completed direct review of Claude's implementation and checked the final rebased\
    \ diff. Codex authored and self-reviewed the follow-up error handling and migration instructions.\
    \ No unresolved findings within the credential migration scope."
checks:
- command: .venv/bin/python -m pytest -q
  status: passed
  head: 75d599dc9db16291ba6f0db7a79474a702a647c2
  base: 25b98b15f137099c6a537db19af92e5ad0e54118
  detail: "5011 passed and 33 skipped in 840.35 seconds."
- command: .venv/bin/python -m pytest -q tests/test_google_helpers.py
  status: passed
  head: 75d599dc9db16291ba6f0db7a79474a702a647c2
  base: 25b98b15f137099c6a537db19af92e5ad0e54118
  detail: "7 passed."
- command: git diff --check origin/main...HEAD
  status: passed
  head: 75d599dc9db16291ba6f0db7a79474a702a647c2
  base: 25b98b15f137099c6a537db19af92e5ad0e54118
  detail: "No whitespace errors."
- command: env -u GCAL_SERVICE_ACCOUNT_JSON -u GCAL_SERVICE_ACCOUNT_FILE .venv/bin/python src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/gcal.py
    get --calendar-id example --event-id example
  status: passed
  head: 75d599dc9db16291ba6f0db7a79474a702a647c2
  base: 25b98b15f137099c6a537db19af92e5ad0e54118
  detail: "In a PTY, stderr named both unset variables and the CLI exited 1."
- command: env -u GMAIL_CLIENT_ID -u GMAIL_CLIENT_SECRET -u GMAIL_REFRESH_TOKEN -u GMAIL_USER
    .venv/bin/python src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py
    search --query example
  status: passed
  head: 75d599dc9db16291ba6f0db7a79474a702a647c2
  base: 25b98b15f137099c6a537db19af92e5ad0e54118
  detail: "In a PTY, stderr named all four unset variables and the CLI exited 1."
```
