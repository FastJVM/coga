---
name: coga-calendar-reminder
description: Create, verify, update, or delete Google Calendar events that fire a coga ticket on a recurring schedule. Use whenever a human should be nudged to launch a coga ticket on a schedule — for example a repo with no cron host running `coga recurring`, or work a human must start by hand. Also use when the user asks for a "monthly nudge", "yearly reminder", "calendar trigger", or wants to attach a calendar schedule to a ticket. Required before calling Google Calendar directly to schedule a ticket; this skill encodes the title, description, timezone, reminders, and frontmatter conventions so every reminder event has the same shape and can be torn down cleanly.
---

# coga/calendar-reminder

Manages Google Calendar events that serve as **human-facing
triggers** for coga tickets. A reminder fires on a recurring schedule
(monthly, annually, etc.), the human sees it, the human launches the
ticket.

Coga's own recurring scheduling is a recurring template
(`coga/recurring/<name>/ticket.md` with a `schedule:` cron) swept by
`coga recurring`; Coga installs no scheduler, so that needs an operator
cron entry (see `coga/recurring`). A calendar reminder is the optional
alternative when no cron host runs `coga recurring`, or when a human
should decide each time whether to launch. When a ticket moves onto a
recurring template that cron drives, delete its reminder event.

The skill encodes the event-shape convention (title, description,
timezone, reminders) and records the resulting event ID into the
ticket's frontmatter, so future `verify` / `update` / `delete`
operations can find the event without out-of-band state.

## Backend: the `coga/google-calendar` skill

All Calendar API calls go through the bundled **`coga/google-calendar`**
skill — its `gcal.py` script — not a local `gws`/`gcloud` binary and
not MCP. That skill owns auth (a Google service account) and the four
event operations; this skill only assembles the request bodies per the
conventions below and shells out. Invoke via Bash:

```bash
python /resolved/coga/google-calendar/gcal.py <verb> ...
```

`/resolved/coga/google-calendar/` stands for that skill's resolved
directory: the repo's local `coga/skills/coga/google-calendar/` override
if one exists, else the installed bundled skill (resolution as in
`coga/sandboxes`). The
call shapes below use the same placeholder.

The script speaks the Google event resource as JSON in and out. Exit
codes: `0` ok, `1` config/auth/API error (message on stderr), `3` event
not found (so `verify`/`delete` can tell "already gone" from "broken").

### Setup

One-time service-account setup lives in the `coga/google-calendar`
SKILL.md — read it. In short: create a Google service account + JSON
key, enable the Calendar API, **share the reminders calendar with the
service account's email** (grant "Make changes to events"), and declare
the key as `GCAL_SERVICE_ACCOUNT_JSON` (or `GCAL_SERVICE_ACCOUNT_FILE`) in
the reminder ticket's `secrets:` frontmatter. Install the
Google client libs yourself: `python -m pip install -r requirements.txt` from
the `coga/google-calendar` skill's dir.

### Calendar target — NOT `primary`

A service account is a robot identity; on a personal (non-Workspace)
Google account it **cannot write to a human's `primary` calendar**.
Reminder events must target a calendar that has been **shared with the
service account's email** — e.g. a dedicated "Coga reminders" calendar.
Resolve the calendar id from the repo's free-form `coga.toml`
`[extensions.calendar]` table (`calendar_id = "..."`; a calendar id is not a
secret) when the repo records one there, or ask the human which shared
calendar to use. Do not add a top-level `[calendar]` table: Coga's config
loader rejects unknown sections. **Never pass `primary`** — it returns 403/404.

Throughout the call shapes below, `<calendar-id>` means that shared
calendar id, never `primary`.

## When to use this skill

- A coga ticket needs to be manually launched on a schedule and no
  cron host runs `coga recurring` for it.
- The user says "remind me monthly to do X", "set a yearly reminder
  for Y", or "add a calendar nudge for this ticket".
- The agent is about to create a Google Calendar event for a
  coga-related recurring reminder — route through this skill
  instead so the convention stays consistent.
- A ticket has moved onto a cron-driven recurring template and its
  reminder event needs to be torn down.

## When NOT to use this skill

- One-off appointments, meetings with attendees, or anything that
  isn't a coga-ticket trigger — call the `coga/google-calendar`
  skill directly.
- Events that need invites, locations, or attendee lists.

## Operations

Four operations, each delegating to the `coga/google-calendar` skill
after assembling the request per this skill's conventions.

| Operation | When to use | Underlying call |
|---|---|---|
| `create` | Setting up a new reminder for a ticket | `gcal.py create` |
| `verify` | Confirming an event still exists with the expected schedule | `gcal.py get` |
| `update` | Schedule or content needs to change | `gcal.py update` |
| `delete` | Cron-driven recurring template taking over, or ticket retiring | `gcal.py delete` |

### create

Gather these inputs before calling the backend:

1. **Ticket name** — e.g. `brex-automation`. Used to derive the
   default event title and to locate the `ticket.md` (or
   `recurring/<name>/ticket.md`) for writing the event ID into
   frontmatter.
2. **Schedule** — RRULE fragment without the `RRULE:` prefix.
   Examples: `FREQ=MONTHLY;BYMONTHDAY=1`,
   `FREQ=YEARLY;BYMONTH=5;BYMONTHDAY=1`.
3. **First fire datetime** — ISO 8601 in `America/Los_Angeles`. If
   the cadence already happened this year (e.g. monthly cadence,
   today is the 12th), skip ahead to the next occurrence so the
   first fire isn't in the past.
4. **Description body** — one or two sentences telling the human
   what to do when the reminder fires.
5. **Optional title override** — if the auto-derived title isn't
   right.

Convention applied to the event body:

- **summary (title)** — if the user provided an override, use it.
  Otherwise derive from the ticket name in human-readable form
  (e.g. `brex-automation` → "Brex — review Missing GL Account
  charges"). When deriving, ask the user before committing — the
  derivation can be wrong.
- **start / end** — 60-minute block at 9:00 AM PT by default on the
  first-fire date. The hour is intentional — these events only need
  to be notification triggers, but a larger block is more visible in
  the calendar. Adjust only if the user asks.
- **timeZone** — `America/Los_Angeles`.
- **recurrence** — `["RRULE:<the-schedule-fragment>"]`.
- **description** — assembled from this template:

  ```
  <description body>

  Coga ticket: <relative path to the ticket or recurring template>
  Launch: see the ticket / recurring entry for the canonical invocation.

  Calendar reminder managed by coga/calendar-reminder — delete this event if the ticket moves to a cron-driven recurring template.
  ```

- **reminders.overrides**:
  - Monthly: `[{"method": "popup", "minutes": 10}]`.
  - Annual: `[{"method": "popup", "minutes": 10}, {"method": "email", "minutes": 1440}]` (24 hours of email lead time for events that fire only once a year).
- **reminders.useDefault** — always `false` when overrides are set.

Call shape (monthly reminder, shared reminders calendar):

```bash
python /resolved/coga/google-calendar/gcal.py create \
  --calendar-id "<calendar-id>" \
  --body '{
    "summary": "Brex — review Missing GL Account charges",
    "description": "Review the report and assign GL accounts in Brex.\n\nCoga ticket: coga/tasks/brex-automation/ticket.md\nLaunch: see the ticket / recurring entry for the canonical invocation.\n\nCalendar reminder managed by coga/calendar-reminder — delete this event if the ticket moves to a cron-driven recurring template.",
    "start": {"dateTime": "2026-06-01T09:00:00", "timeZone": "America/Los_Angeles"},
    "end":   {"dateTime": "2026-06-01T10:00:00", "timeZone": "America/Los_Angeles"},
    "recurrence": ["RRULE:FREQ=MONTHLY;BYMONTHDAY=1"],
    "reminders": {"useDefault": false, "overrides": [{"method": "popup", "minutes": 10}]}
  }'
```

The response is the created event as JSON. Extract the `id` field —
that's the event ID.

After the call returns:

- Open `coga/tasks/<ticket-name>/ticket.md`
  (or `coga/recurring/<name>/ticket.md` if the artifact is a
  recurring template, not a ticket).
- Add `calendar_reminder_event_id: <event-id>` to the frontmatter,
  alongside `title:`, `status:`, etc.
- Save. Don't commit unless the user asks — they may want to bundle
  the change with other edits.

### verify

Use when the user asks "is the X reminder still set up?" or before
acting on an assumption that the event exists.

1. Read `calendar_reminder_event_id` from the ticket's frontmatter.
2. Call:
   ```bash
   python /resolved/coga/google-calendar/gcal.py get \
     --calendar-id "<calendar-id>" --event-id "<id>"
   ```
   Exit code `3` means the event is gone — surface that and offer to
   recreate it via `create`.
3. Confirm: `status` is `confirmed`, `recurrence` matches what the
   ticket implies, `start.timeZone` is `America/Los_Angeles`, and the
   description contains the "Calendar reminder managed by
   coga/calendar-reminder…" line.
   If any of those drift, the event was edited manually outside
   the skill — surface this and offer to bring it back into
   convention via `update`.
4. Report next-fire date and the `htmlLink` back to the user.

### update

Use when the schedule, title, or description needs to change (e.g.
"move the monthly nudge from the 1st to the 5th").

1. Read `calendar_reminder_event_id` from the ticket's frontmatter.
2. Re-apply the create convention with the new inputs.
3. Call:
   ```bash
   python /resolved/coga/google-calendar/gcal.py update \
     --calendar-id "<calendar-id>" --event-id "<id>" \
     --body '{ <only the fields that changed> }'
   ```
   `update` is a partial merge (Google `patch`); only include keys
   that differ. If the schedule changed, include the full
   `recurrence`, `start`, and `end` — those three move together.
4. Run a follow-up `verify` to confirm.

### delete

Use when a cron-driven recurring template now fires the ticket (so
the reminder is no longer needed) or when a ticket is being retired
entirely.

1. Read `calendar_reminder_event_id` from the ticket's frontmatter.
2. Call:
   ```bash
   python /resolved/coga/google-calendar/gcal.py delete \
     --calendar-id "<calendar-id>" --event-id "<id>"
   ```
   A successful delete prints `{}` (exit `0`). Exit `3` means the
   event was already gone — treat that as success for cleanup.
3. Open the ticket/recurring file and **remove** the
   `calendar_reminder_event_id` line from the frontmatter.
4. If the deletion is part of a move onto a cron-driven recurring
   template, add one line to the blackboard:
   `Calendar reminder <event-id> deleted on <date> — coga recurring now drives this ticket.`

## Convention: where the event ID lives

In the ticket's frontmatter as a top-level field:

```yaml
---
title: Brex Automation
status: draft
owner: zach
agent: claude
contexts:
  - owner-manual
workflow: brex-missing-gl
calendar_reminder_event_id: j3lt2meocjfetlbl6ga27jvvh8
---
```

For recurring templates, the field goes in
`coga/recurring/<name>/ticket.md` frontmatter instead:

```yaml
---
schedule: "0 9 5 1 *"
schedule_comment: "January 5 at 9am — annually..."
title: "Download previous year's Gusto payroll tax forms"
owner: zach
calendar_reminder_event_id: 0vhr5me50sbohsq9afo7jf85qg
---
```

`owner:` names the accountable human. An optional `agent:` chooses the main
agent; workflow step roles derive who acts. If the recurring work needs a human
handoff, choose a workflow with an `assignee: owner` step rather than adding
top-level assignment metadata.

Why this location:

- Anyone reading the ticket immediately sees there's an external
  reminder.
- The skill locates the event without an external registry.
- A future migration that strips unknown frontmatter
  would remove the line — that's recoverable; the skill can re-emit
  it on the next `verify` or recreate the event.

Tickets without a `calendar_reminder_event_id` field have no active
reminder. That's the truth source — don't infer reminders from the
ticket body.

`calendar_reminder_event_id` is not part of the canonical ticket
schema: `coga validate` reports it as a warn-level `orphan-extension`
unless the repo declares it under `[ticket.fields]` in `coga.toml`
(see `coga/configuration`). Note that a declared field is also written
into every freshly created ticket, so a repo may prefer to accept the
warning.

## Bundled scripts

None — pure orchestration over the `coga/google-calendar` skill via Bash.
