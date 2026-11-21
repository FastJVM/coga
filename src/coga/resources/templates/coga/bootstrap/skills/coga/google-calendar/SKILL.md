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

## Resolving the helper directory

`/resolved/coga/google-calendar/` stands for this skill's resolved
directory. This section owns how to resolve it. Sibling Google skills
(`coga/gmail`, `coga/calendar-reminder`) link here. Check for the repo's local
override first, then fall back to the installed bundled skill:

```bash
dir="${COGA_COGA_OS_ROOT:-$(git rev-parse --show-toplevel)/coga}/skills/coga/google-calendar"
[ -f "$dir/gcal.py" ] || dir="$(python -c 'from coga.paths import packaged_template_path; print(packaged_template_path("bootstrap", "skills", "coga", "google-calendar"))')"
python -m pip install -r "$dir/requirements.txt"   # once per Python
python "$dir/gcal.py" get --calendar-id <id> --event-id <id>
```

- **Override first.** The first line names `<coga-dir>/skills/coga/google-calendar/`,
  where `<coga-dir>` is `$COGA_COGA_OS_ROOT` inside a launch and the checkout's
  `coga/` directory outside one. Bundled skills are not copied into the repo,
  so that directory exists only when the repo deliberately overrides the skill.
- **Package fallback.** The second line needs a `python` that imports `coga`. For
  a `uv tool` or `pipx` install, that is the tool environment's interpreter
  (the `coga` launcher's shebang), not necessarily the shell's `python`. In
  Windows `cmd.exe`, single quotes do not quote; swap them:
  `python -c "from coga.paths import packaged_template_path; print(packaged_template_path('bootstrap', 'skills', 'coga', 'google-calendar'))"`.
- **Which Python runs the helper.** `gcal.py` is self-contained and never
  imports `coga`, so the Python that runs it need not be the one that
  resolved the path. Install `requirements.txt` into the same Python
  that runs `gcal.py`. Because the command gives the requirements file by
  absolute path (`"$dir/requirements.txt"`), it works from any working
  directory.

## Auth — service account

Credentials are a Google **service-account JSON key**, read from the
environment — never from Coga config:

| variable | value |
|----------|-------|
| `GCAL_SERVICE_ACCOUNT_JSON` | the key's JSON contents (wins when both are set) |
| `GCAL_SERVICE_ACCOUNT_FILE` | a path to the key file |

The consuming ticket declares one of them in its `secrets:` frontmatter, and
launch resolves it into the child environment (`coga/secrets`):

```yaml
secrets:
  - GCAL_SERVICE_ACCOUNT_JSON: op://<automation-vault>/<item>/<field>
```

Store the key's contents in the automation vault for headless runs, or map
`GCAL_SERVICE_ACCOUNT_FILE: env:<VAR>` to a path the operator already exports.
A manual run outside launch exports either variable itself. A service account
authenticates headlessly — the point, for an unattended cron.

To migrate an existing `[calendar]` entry, export its key path as
`GCAL_SERVICE_ACCOUNT_FILE` or store the key contents in the automation vault,
then remove the retired table from `coga.local.toml` so Coga can load the repo.

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
3. Store the key as above and declare it in the consuming ticket's `secrets:`.

(A durable auth-hardening story — rotation, alternative backends — is tracked
as a separate ticket.)

## Dependencies

`requirements.txt` declares `google-api-python-client` and `google-auth`.
Coga installs nothing for a skill. Install them yourself with
`python -m pip install -r "$dir/requirements.txt"`, using the same Python that
runs `gcal.py` (see "Resolving the helper directory").

## Out of scope

USPTO/patent domain logic, calendar-id resolution policy, and `## Calendar sync
state` bookkeeping all stay in the consuming skill (e.g.
`patent-lifecycle-calendar`). This skill only does the four event operations.
