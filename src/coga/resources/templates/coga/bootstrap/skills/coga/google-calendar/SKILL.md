---
name: coga/google-calendar
description: Reusable Google Calendar capability — create/read/update/delete events via a service account, so skills don't depend on a per-host gws/gcloud binary. Other skills shell to this skill's gcal.py.
---

# Google Calendar capability

The calendar analogue of `coga slack`: a shared, bootstrapped capability any
coga skill can use to write Google Calendar events, without a per-machine
`gws`/`gcloud` binary or interactive login. The logic lives in `gcal.py`,
a self-contained script other skills shell to.

## Invocation

```
python /resolved/coga/google-calendar/gcal.py get \
    --calendar-id <id> --event-id <id>
python .../gcal.py create --calendar-id <id> --body '<json event resource>'
python .../gcal.py update --calendar-id <id> --event-id <id> --body '<json>'
python .../gcal.py delete --calendar-id <id> --event-id <id>
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

`/resolved/coga/google-calendar/` stands for this skill's resolved
directory: the repo's local `coga/skills/coga/google-calendar/` override
if one exists, else the installed bundled skill (resolution as in
`coga/checkouts/sandbox-clone`, "What a fresh checkout lacks"). Bundled
skills are not copied into the repo, so
`$COGA_COGA_OS_ROOT/skills/coga/google-calendar/` exists only for a local
override.

## Auth — service account

Credentials are a Google **service-account JSON key**. `gcal.py` reads its
path from a `[calendar]` table in `coga.local.toml` (found via
`COGA_COGA_OS_ROOT`, else by walking up from the working directory):

```toml
[calendar]
service_account_file = "/path/to/service-account.json"   # or "env:GCAL_SA_KEY"
```

`gcal.py` itself resolves an `env:VAR` value from the process environment.
A service account authenticates headlessly — the point, for an unattended cron.

**Known gap.** Coga's config loader rejects unknown top-level sections in
`coga.local.toml`, and `[calendar]` is not an accepted section, so adding this
table makes every `coga` command in that checkout fail with a `ConfigError`.
Coga does not yet define a supported home for this credential (the free-form
`[extensions]` table is accepted only in the shared `coga.toml`, which must not
hold machine-local credential paths). Until that is settled, there is no
supported configuration that keeps `coga` working in the same checkout.

**Important limitation.** A service account is a robot identity. On a personal
(non-Workspace) Google account there is no domain-wide delegation, so it can
only read/write a calendar that has been **shared with the service account's
email** — it can **never** reach a human's `primary` calendar. Targeting
`primary` (or any calendar the SA isn't a member of) returns a 403/404, which
this skill surfaces with a "share the calendar with the SA's email" hint.

Setup once:
1. Create a service account + JSON key in Google Cloud, enable the Calendar API.
2. Share the target calendar (e.g. a dedicated reminders calendar) with
   the service account's email, granting "Make changes to events".
3. Point `[calendar].service_account_file` at the key (subject to the known
   gap above).

(A durable auth-hardening story — rotation, alternative backends — is tracked
as a separate ticket.)

## Dependencies

`requirements.txt` declares `google-api-python-client` and `google-auth`.
Coga installs nothing for a skill — run `python -m pip install -r
requirements.txt` from this skill's resolved dir, using the same Python
that runs `gcal.py`.

## Out of scope

USPTO/patent domain logic, calendar-id resolution policy, and `## Calendar sync
state` bookkeeping all stay in the consuming skill (e.g.
`patent-lifecycle-calendar`). This skill only does the four event operations.
