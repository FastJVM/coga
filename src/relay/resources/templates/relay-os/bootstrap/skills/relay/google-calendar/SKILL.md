---
name: relay/google-calendar
description: Reusable Google Calendar capability — create/read/update/delete events via a service account, so skills don't depend on a per-host gws/gcloud binary. Other skills shell to this skill's calendar.py.
---

# Google Calendar capability

The calendar analogue of `relay slack`: a shared, bootstrapped capability any
relay skill can use to write Google Calendar events, without a per-machine
`gws`/`gcloud` binary or interactive login. The logic lives in `calendar.py`,
a self-contained script other skills shell to.

## Invocation

```
python <relay-os>/skills/relay/google-calendar/calendar.py get \
    --calendar-id <id> --event-id <id>
python .../calendar.py create --calendar-id <id> --body '<json event resource>'
python .../calendar.py update --calendar-id <id> --event-id <id> --body '<json>'
python .../calendar.py delete --calendar-id <id> --event-id <id>
```

`get`/`create`/`update` print the Google event resource as JSON on stdout;
`delete` prints `{}`. Verbs mirror the Google Calendar API (`update` is a
partial `patch`), so a consuming client is a thin shim.

Exit codes are the contract:

| code | meaning |
|------|---------|
| 0 | ok |
| 1 | config / auth / API error (message on stderr) |
| 3 | event not found (caller can distinguish "gone" from "broken") |

Locate the script via `RELAY_RELAY_OS_ROOT` (set during skill/script launches)
so it resolves regardless of the consuming repo.

## Auth — service account

Credentials are a Google **service-account JSON key**. Its path is read from
`relay.local.toml`:

```toml
[calendar]
service_account_file = "/path/to/service-account.json"   # or "env:GCAL_SA_KEY"
```

`env:VAR` indirection is supported (same convention as relay's `[secrets]`).
A service account authenticates headlessly — the point, for an unattended cron.

**Important limitation.** A service account is a robot identity. On a personal
(non-Workspace) Google account there is no domain-wide delegation, so it can
only read/write a calendar that has been **shared with the service account's
email** — it can **never** reach a human's `primary` calendar. Targeting
`primary` (or any calendar the SA isn't a member of) returns a 403/404, which
this skill surfaces with a "share the calendar with the SA's email" hint.

Setup once:
1. Create a service account + JSON key in Google Cloud, enable the Calendar API.
2. Share the target calendar (e.g. a dedicated "FastJVM Patent" calendar) with
   the service account's email, granting "Make changes to events".
3. Point `[calendar].service_account_file` at the key.

(A durable auth-hardening story — rotation, alternative backends — is tracked
as a separate ticket.)

## Dependencies

`requirements.txt` declares `google-api-python-client` and `google-auth`.
Relay's bootstrap installs every `relay-os/skills/**/requirements.txt` into
`.relay/.venv` (during `relay init` / `relay init --update`), so a bootstrapped
skill brings its own deps. If they're missing, run `relay init --update`.

## Out of scope

USPTO/patent domain logic, calendar-id resolution policy, and `## Calendar sync
state` bookkeeping all stay in the consuming skill (e.g.
`patent-lifecycle-calendar`). This skill only does the four event operations.
