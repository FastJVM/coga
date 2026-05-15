---
name: relay-calendar-reminder
description: Create, verify, update, or delete Google Calendar events that fire a relay ticket on a recurring schedule. Use whenever a relay ticket needs a manual-launch reminder and relay's native recurring-task scheduling hasn't shipped yet — the calendar event is the stopgap. Also use when the user asks for a "monthly nudge", "yearly reminder", "calendar trigger", or wants to attach a temporary schedule to a ticket. Required before calling Google Calendar directly to schedule a ticket; this skill encodes the title, description, timezone, reminders, and frontmatter conventions so every reminder event has the same shape and can be torn down cleanly.
---

# relay/calendar-reminder

Manages Google Calendar events that serve as **temporary triggers**
for relay tickets. A reminder fires on a recurring schedule (monthly,
annually, etc.), the human sees it, the human launches the ticket.
The event is operational scaffolding — when relay's native
recurring-task machinery ships, every reminder event created through
this skill gets deleted in one pass.

The skill encodes the event-shape convention (title, description,
timezone, reminders) and records the resulting event ID into the
ticket's frontmatter, so future `verify` / `update` / `delete`
operations can find the event without out-of-band state.

## Backend: `gws` CLI

All Calendar API calls go through the `gws` (Google Workspace CLI)
binary on the local machine — not via MCP. Invoke via Bash. Tested
against `gws 0.22.5`.

### Setup on a new machine

1. **Install via Homebrew:**

   ```bash
   brew install googleworkspace-cli
   ```

   Note: the formula is `googleworkspace-cli`, **not** `gws`. The
   binary it installs is named `gws`, but `brew install gws` would
   install an unrelated git-workspace-manager tool — wrong package.

   Verify: `gws --version` → `gws 0.22.5` (or newer).

2. **Get the shared OAuth client.** Ask Zach for the
   `Manycore Admin Automation` `client_secret.json`. One OAuth client
   is shared across machines; each user does their own browser
   consent and ends up with their own user token. Save the file to:

   ```
   ~/.config/gws/client_secret.json
   ```

3. **Authenticate:**

   ```bash
   gws auth login
   ```

   Browser flow — sign in with your `@fastjvm.com` account and
   approve the requested scopes. The token is cached per-machine
   under `~/.config/gws/` (encrypted, backed by the macOS keyring).

4. **Verify:**

   ```bash
   gws auth status
   ```

   Look for `https://www.googleapis.com/auth/calendar.events` in the
   `scopes` array. If it's missing after a successful login, the
   OAuth client doesn't have the calendar scope enabled in GCP
   Console — ask Zach to add it, then re-run `gws auth login` to
   pick up the broader scope on your token.

5. **Grant macOS Desktop folder access** to the app running the
   agent (Terminal and/or the Claude Code desktop app). This repo
   lives under `~/Desktop/admin/`, and macOS gates Desktop access
   per-app.

   System Settings → Privacy & Security → **Files and Folders** →
   find the entry for the running app → toggle **Desktop Folder**
   ON. Alternatively, grant **Full Disk Access** to the same app
   (broader but works). Then **quit and relaunch** the app — macOS
   requires the relaunch for the permission to take effect.

   Symptom if missing: `Read`/`Bash` tool calls against
   `/Users/<you>/Desktop/...` return `Operation not permitted`
   while `/tmp` and the home dir work fine.

### Why `gws` instead of MCP

gws runs on the same machine as the relay agent, so the same auth
works for both interactive and unattended use (cron). See
[[project-relay-calendar-reminder-auth-revisit]] for the SA+DWD
upgrade path when unattended use lands.

## When to use this skill

- A relay ticket needs to be manually launched on a schedule and
  there's no other scheduling mechanism wired up.
- The user says "remind me monthly to do X", "set a yearly reminder
  for Y", or "add a calendar nudge for this ticket".
- The agent is about to call `gws calendar events insert` for a
  relay-related recurring reminder — route through this skill
  instead so the convention stays consistent.
- Relay's recurring-task machinery has shipped and existing reminder
  events need to be torn down.

## When NOT to use this skill

- One-off appointments, meetings with attendees, or anything that
  isn't a relay-ticket trigger — call `gws calendar events insert`
  directly.
- Events that need invites, locations, or attendee lists.

## Operations

Four operations, each delegating to a `gws calendar events` method
after assembling the request per this skill's conventions.

| Operation | When to use | Underlying call |
|---|---|---|
| `create` | Setting up a new reminder for a ticket | `gws calendar events insert` |
| `verify` | Confirming an event still exists with the expected schedule | `gws calendar events get` |
| `update` | Schedule or content needs to change | `gws calendar events patch` |
| `delete` | Recurring machinery taking over, or ticket retiring | `gws calendar events delete` |

### create

Gather these inputs before calling gws:

1. **Ticket name** — e.g. `brex-automation`. Used to derive the
   default event title and to locate the `ticket.md` (or
   `recurring/<name>.md`) for writing the event ID into frontmatter.
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

  Relay ticket: <relative path to the ticket or recurring file>
  Launch: see the ticket / recurring entry for the canonical invocation.

  Temporary — delete this event once relay's recurring-task machinery lands and the ticket can fire on its own cron.
  ```

- **reminders.overrides**:
  - Monthly: `[{"method": "popup", "minutes": 10}]`.
  - Annual: `[{"method": "popup", "minutes": 10}, {"method": "email", "minutes": 1440}]` (24 hours of email lead time for events that fire only once a year).
- **reminders.useDefault** — always `false` when overrides are set.

Call shape (monthly reminder, primary calendar):

```bash
gws calendar events insert \
  --params '{"calendarId": "primary"}' \
  --json '{
    "summary": "Brex — review Missing GL Account charges",
    "description": "Review the report and assign GL accounts in Brex.\n\nRelay ticket: relay-os/tasks/brex-automation/ticket.md\nLaunch: see the ticket / recurring entry for the canonical invocation.\n\nTemporary — delete this event once relay'\''s recurring-task machinery lands and the ticket can fire on its own cron.",
    "start": {"dateTime": "2026-06-01T09:00:00", "timeZone": "America/Los_Angeles"},
    "end":   {"dateTime": "2026-06-01T10:00:00", "timeZone": "America/Los_Angeles"},
    "recurrence": ["RRULE:FREQ=MONTHLY;BYMONTHDAY=1"],
    "reminders": {"useDefault": false, "overrides": [{"method": "popup", "minutes": 10}]}
  }'
```

The response is JSON. Extract the `id` field — that's the event ID.

After the call returns:

- Open `relay-os/tasks/<ticket-name>/ticket.md`
  (or `relay-os/recurring/<name>.md` if the artifact is a recurring
  entry, not a ticket).
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
   gws calendar events get \
     --params '{"calendarId": "primary", "eventId": "<id>"}'
   ```
3. Confirm: `status` is `confirmed`, `recurrence` matches what the
   ticket implies, `start.timeZone` is `America/Los_Angeles`, and the
   description contains the "Temporary — delete this event…" line.
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
   gws calendar events patch \
     --params '{"calendarId": "primary", "eventId": "<id>"}' \
     --json '{ <only the fields that changed> }'
   ```
   `patch` merges; only include keys that differ. If the schedule
   changed, include the full `recurrence`, `start`, and `end` —
   those three move together.
4. Run a follow-up `verify` to confirm.

### delete

Use when relay's recurring machinery has shipped (so the reminder is
no longer needed) or when a ticket is being retired entirely.

1. Read `calendar_reminder_event_id` from the ticket's frontmatter.
2. Call:
   ```bash
   gws calendar events delete \
     --params '{"calendarId": "primary", "eventId": "<id>"}'
   ```
   A successful delete returns an empty body (HTTP 204).
3. Open the ticket/recurring file and **remove** the
   `calendar_reminder_event_id` line from the frontmatter.
4. If the deletion is part of a machinery-shipping migration, add
   one line to the blackboard:
   `Calendar reminder <event-id> deleted on <date> — recurring machinery now drives this ticket.`

## Convention: where the event ID lives

In the ticket's frontmatter as a top-level field:

```yaml
---
title: Brex Automation
status: active
mode: interactive
owner: zach
assignee: claude1
contexts:
  - owner-manual
workflow: brex-missing-gl
calendar_reminder_event_id: j3lt2meocjfetlbl6ga27jvvh8
---
```

For recurring entries (no `ticket.md`), the field goes in the
recurring file's frontmatter instead:

```yaml
---
schedule: "0 9 5 1 *"
schedule_comment: "January 5 at 9am — annually..."
title: "Download previous year's Gusto payroll tax forms"
mode: interactive
owner: zach
assignee: zach
calendar_reminder_event_id: 0vhr5me50sbohsq9afo7jf85qg
---
```

Why this location:

- Anyone reading the ticket immediately sees there's an external
  reminder.
- The skill locates the event without an external registry.
- A future `relay init --update` that strips unknown frontmatter
  would remove the line — that's recoverable; the skill can re-emit
  it on the next `verify` or recreate the event.

Tickets without a `calendar_reminder_event_id` field have no active
reminder. That's the truth source — don't infer reminders from the
ticket body.

## Existing events (to be migrated)

Four calendar events were created via direct MCP calls before this
skill existed. The event IDs are valid regardless of which client
created them — `gws calendar events get` will return them. Migration
plan: for each artifact, confirm the `calendar_reminder_event_id`
frontmatter field is present, then run `verify` to confirm the event
still matches the convention.

| Artifact | Event ID | Schedule | First fire |
|---|---|---|---|
| `relay-os/tasks/brex-automation/ticket.md` | `j3lt2meocjfetlbl6ga27jvvh8` | Monthly, 1st 9 AM PT | 2026-06-01 |
| `relay-os/tasks/xero-reconciliation/ticket.md` | `ns2of8i93mke579aedr927cv8k` | Monthly, 1st 9 AM PT | 2026-06-01 |
| `relay-os/recurring/gusto-tax-forms-download.md` | `0vhr5me50sbohsq9afo7jf85qg` | Yearly, Jan 5 9 AM PT | 2027-01-05 |
| `relay-os/tasks/insurance-payment-reminder/ticket.md` | `4jqgrfutdf6rctja3fo9kujrb0` | Yearly, May 1 9 AM PT | 2027-05-01 |

After migration, the prose "Triggering (temporary)" bullets currently
in each ticket can be removed — the frontmatter line is the only
ticket-side record going forward.

## Cleanup when relay recurring ships

When relay's native recurring-task scheduling is shipped and firing
each ticket reliably:

1. For every artifact with a `calendar_reminder_event_id`, run the
   `delete` operation.
2. This skill becomes unused, but keep it in the repo — the next
   "we don't have machinery for X yet" stopgap will want the same
   shape.

## Bundled scripts

None — pure orchestration over the `gws` CLI via Bash.
