---
title: Provide a Google Calendar capability so skills don't depend on a local gws
  binary
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Relay skills that need to write to Google Calendar currently have no
shared way to do it. The patents repo's `patent-lifecycle-calendar`
skill (its calendar sync + the monthly REM cron) reaches Google
Calendar by shelling out to the `gws` (`googleworkspace-cli`) binary.
That binary is not installed on the host — and no Google CLI is
(`gws`, `gcloud`, `gcalcli`, `gam` all absent). So the live calendar
sync has **never actually been able to run**: `--sync` fails loudly
with "gws not found", and the monthly cron would do the same.

Note the dead-end we ruled out: `google-agents-cli` / `agents-cli`
(the Google ADK) is installed-adjacent in the skills tree but is an
*agent publishing/deployment* tool — it cannot create calendar events.
The Workspace tool (`gws`) and the ADK tool (`agents-cli`) are
unrelated despite both starting with "google".

This ticket asks relay to provide a **first-class, reusable Google
Calendar capability** — the analogue of `relay slack` /
`RelaySlackSink`, which skills already use for notifications — so any
skill can create / patch / delete calendar events without depending on
a per-machine binary that isn't there.

Decide and implement the backend. Candidate approaches (the
implementing agent should pick one and justify it):

1. **Relay-provided calendar command/sink** — e.g. `relay calendar`
   or a `RelayCalendarSink`, backed by the Google Calendar API via a
   service account or stored OAuth creds (`env:`-referenced in
   `relay.toml`). Skills call relay, not a local CLI. Most robust for
   unattended cron.
2. **Manage `gws` as a declared dependency** — install
   `googleworkspace-cli` via the skill `requires.install` mechanism and
   document `gws auth login`. Smallest change, but still a per-host
   binary + interactive auth, awkward for headless cron.
3. **Direct Calendar API in the consuming skill** — swap `gws` for
   `google-api-python-client`. Keeps it in the patents repo and skips
   the relay abstraction, but every future calendar skill re-solves
   auth.

Whatever is chosen, the patents `patent-lifecycle-calendar` skill must
end up able to run its `--sync` unattended (monthly cron), with the
calendar-id resolution it already has and full `## Calendar sync state`
bookkeeping preserved.

## Context

- Consumer skill (separate repo): `~/Code/patents/relay-os/skills/relay/patent-lifecycle-calendar/`
  — see `GwsCalendarClient` in `~/Code/patents/relay-os/lib/patents/calendar.py`
  (it builds `["gws", "calendar", "events", ...]` via `subprocess.run`).
- Precedent to mirror: `RelaySlackSink` in that same file shells to
  `relay slack` — a calendar capability should sit at the same layer.
- Auth that *does* exist today: the Claude Google Calendar connector
  (MCP), which is session-scoped, not something an unattended cron can
  use. A durable backend (service account / stored OAuth) is the gap.
- Related/just-merged: patents PR #53 added a today-or-future filter to
  the sync path; it does not address the missing backend. This ticket
  is the backend.
- Out of scope: USPTO/patent domain logic, fee payment, Slack deadline
  escalation, and the Google ADK (`agents-cli`).
